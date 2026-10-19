-- Cleaned, typed provider utilization at the grain
-- (rendering_npi, delivery_system, provider_type, age_group, provider_legal_name).
--
-- Key decisions (see docs/data-audit.md):
--   * Suppressed counts (annotation code present, value blank) become NULL, never 0.
--   * PREV/TXMT/EXAM are subsets of ADV ("annual dental visit" = any dental service),
--     so ADV is the total. Nothing is summed across categories.
--   * The source repeats some rows that differ only by the spelling of the provider
--     name, with identical metrics. Those copies are dropped; true variants are kept.

with typed as (

    select
        trim(rendering_npi)                                  as rendering_npi,
        regexp_replace(trim(provider_legal_name), ',\s*$', '') as provider_legal_name,
        cast(calendar_year as integer)                       as calendar_year,
        trim(delivery_system)                                as delivery_system,
        trim(provider_type)                                  as provider_type,
        trim(age_group)                                      as age_group_raw,

        {% for metric in ['adv', 'prev', 'txmt', 'exam'] %}
        try_cast(nullif(trim({{ metric }}_user_cnt), '') as bigint)              as {{ metric }}_users,
        try_cast(nullif(trim({{ metric }}_user_annotation_code), '') as integer) as {{ metric }}_users_annotation,
        try_cast(nullif(trim({{ metric }}_svc_cnt), '') as bigint)               as {{ metric }}_services,
        try_cast(nullif(trim({{ metric }}_svc_annotation_code), '') as integer)  as {{ metric }}_services_annotation,
        {% endfor %}

        _source_row
    from {{ ref('bronze_denti_cal_utilization') }}

),

deduplicated as (

    select
        *,
        count(*) over (
            partition by rendering_npi, delivery_system, provider_type, age_group_raw
        ) as name_variant_count,
        row_number() over (
            partition by
                rendering_npi, delivery_system, provider_type, age_group_raw,
                adv_users, adv_services, prev_users, prev_services,
                txmt_users, txmt_services, exam_users, exam_services,
                adv_users_annotation, adv_services_annotation
            order by length(provider_legal_name) desc, _source_row
        ) as metric_copy_rank
    from typed

)

select
    md5(concat_ws('|', rendering_npi, delivery_system, provider_type, age_group_raw, provider_legal_name))
        as utilization_key,
    rendering_npi,
    provider_legal_name,
    calendar_year,

    delivery_system,
    case delivery_system
        when 'FFS' then 'Fee-for-Service'
        when 'GMC' then 'Geographic Managed Care'
        when 'PHP' then 'Prepaid Health Plan'
    end as delivery_system_name,

    provider_type,
    provider_type = 'RENDERING SNC' as is_safety_net_clinic,

    case age_group_raw
        when 'AGE 0-20' then '0-20'
        when 'AGE 21+' then '21+'
    end as age_group,

    {% for metric in ['adv', 'prev', 'txmt', 'exam'] %}
    {{ metric }}_users,
    {{ metric }}_services,
    {{ metric }}_users_annotation,
    {{ metric }}_services_annotation,
    {{ metric }}_users is null and {{ metric }}_users_annotation is not null as {{ metric }}_users_suppressed,
    {% endfor %}

    -- Row-level rates; NULL whenever an input is suppressed.
    {{ safe_divide('adv_services', 'adv_users') }}  as services_per_patient,
    {{ safe_divide('prev_users', 'adv_users') }}    as preventive_coverage,
    {{ safe_divide('txmt_users', 'adv_users') }}    as treatment_coverage,
    {{ safe_divide('exam_users', 'adv_users') }}    as exam_coverage,

    name_variant_count > 1 as has_name_variants,
    _source_row
from deduplicated
where metric_copy_rank = 1
