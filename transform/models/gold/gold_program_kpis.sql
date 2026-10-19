-- Headline program metrics (one row).
-- Patient counts are unique *per provider row*: a beneficiary seen by two providers is
-- counted twice. Totals are therefore provider-level patient counts, not distinct
-- beneficiaries. Suppressed patient counts (1-10 each) are reported as bounds.

with utilization as (

    select * from {{ ref('silver_provider_utilization') }}

)

select
    min(calendar_year)                                         as calendar_year,
    count(distinct rendering_npi)                              as providers,
    count(*)                                                   as provider_rows,

    sum(adv_users)                                             as provider_patients_observed,
    count(*) filter (where adv_users_suppressed)               as suppressed_patient_rows,
    sum(adv_users)
        + {{ var('suppression_min') }} * count(*) filter (where adv_users_suppressed)
                                                               as provider_patients_lower_bound,
    sum(adv_users)
        + {{ var('suppression_max') }} * count(*) filter (where adv_users_suppressed)
                                                               as provider_patients_upper_bound,

    sum(adv_services)                                          as services_observed,
    {{ safe_divide(
        'sum(adv_services) filter (where adv_services is not null and adv_users is not null)',
        'sum(adv_users) filter (where adv_services is not null and adv_users is not null)'
    ) }}                                                       as services_per_patient,

    {% for metric, label in [('prev', 'preventive'), ('txmt', 'treatment'), ('exam', 'exam')] %}
    {{ safe_divide(
        'sum(' ~ metric ~ '_users) filter (where ' ~ metric ~ '_users is not null and adv_users is not null)',
        'sum(adv_users) filter (where ' ~ metric ~ '_users is not null and adv_users is not null)'
    ) }}                                                       as {{ label }}_coverage,
    {% endfor %}

    {{ safe_divide('count(*) filter (where adv_users_suppressed)', 'count(*)') }}
                                                               as suppressed_row_share
from utilization
