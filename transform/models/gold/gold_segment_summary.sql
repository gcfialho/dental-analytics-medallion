-- Utilization by delivery system x age group, plus per-dimension and overall totals
-- (rows labelled 'ALL'). Rates are ratios of sums over rows where both numerator and
-- denominator are observed (not averages of per-row ratios, which overweight tiny
-- practices).

select
    coalesce(delivery_system, 'ALL')                           as delivery_system,
    coalesce(any_value(delivery_system_name) filter (where delivery_system is not null),
             'All delivery systems')                           as delivery_system_name,
    coalesce(age_group, 'ALL')                                 as age_group,
    count(distinct rendering_npi)                              as providers,
    count(*)                                                   as provider_rows,
    sum(adv_users)                                             as provider_patients_observed,
    sum(adv_services)                                          as services_observed,
    {{ safe_divide('count(*) filter (where adv_users_suppressed)', 'count(*)') }}
                                                               as suppressed_row_share,
    {{ safe_divide(
        'sum(adv_services) filter (where adv_services is not null and adv_users is not null)',
        'sum(adv_users) filter (where adv_services is not null and adv_users is not null)'
    ) }}                                                       as services_per_patient,
    {% for metric, label in [('prev', 'preventive'), ('txmt', 'treatment'), ('exam', 'exam')] %}
    {{ safe_divide(
        'sum(' ~ metric ~ '_users) filter (where ' ~ metric ~ '_users is not null and adv_users is not null)',
        'sum(adv_users) filter (where ' ~ metric ~ '_users is not null and adv_users is not null)'
    ) }}                                                       as {{ label }}_coverage{{ "," if not loop.last }}
    {% endfor %}
from {{ ref('silver_provider_utilization') }}
group by grouping sets ((delivery_system, age_group), (delivery_system), (age_group), ())
order by 1, 3
