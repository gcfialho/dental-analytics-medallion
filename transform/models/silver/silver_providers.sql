-- One row per rendering provider (NPI) with a canonical display name.
-- The most frequent spelling wins; ties go to the longest (most complete) name.
-- The source has a provider published with no name at all; it is shown by NPI.

with name_counts as (

    select
        rendering_npi,
        provider_legal_name,
        count(*) as occurrences
    from {{ ref('silver_provider_utilization') }}
    group by all

),

ranked_names as (

    select
        rendering_npi,
        provider_legal_name,
        row_number() over (
            partition by rendering_npi
            order by occurrences desc, length(provider_legal_name) desc, provider_legal_name
        ) as name_rank,
        count(*) over (partition by rendering_npi) as name_variants
    from name_counts

)

select
    n.rendering_npi,
    coalesce(n.provider_legal_name, 'Unnamed provider (NPI ' || n.rendering_npi || ')') as provider_name,
    n.provider_legal_name is null                                                   as is_name_missing,
    n.name_variants,
    list_sort(list_distinct(list(u.delivery_system))) as delivery_systems,
    bool_or(u.is_safety_net_clinic)                   as works_at_safety_net_clinic
from ranked_names as n
inner join {{ ref('silver_provider_utilization') }} as u using (rendering_npi)
where n.name_rank = 1
group by n.rendering_npi, n.provider_legal_name, n.name_variants
