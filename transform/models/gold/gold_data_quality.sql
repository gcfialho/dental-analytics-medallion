-- Data-quality profile surfaced in the dashboard: how much of each measure is
-- suppressed, and how many source rows were removed or flagged in silver.

with bronze as (

    select count(*) as bronze_rows from {{ ref('bronze_denti_cal_utilization') }}

),

silver as (

    select * from {{ ref('silver_provider_utilization') }}

),

measures as (

    {% for metric, label in [('adv', 'Any dental service'), ('prev', 'Preventive'), ('txmt', 'Treatment'), ('exam', 'Exam')] %}
    {% for kind in ['users', 'services'] %}
    select
        '{{ label }}'                                                 as measure,
        '{{ kind }}'                                                  as count_type,
        count(*) filter (where {{ metric }}_{{ kind }} is null)       as suppressed_rows,
        {{ safe_divide('count(*) filter (where ' ~ metric ~ '_' ~ kind ~ ' is null)', 'count(*)') }}
                                                                      as suppressed_share
    from silver
    {{ "union all" if not loop.last }}
    {% endfor %}
    {{ "union all" if not loop.last }}
    {% endfor %}

)

select
    m.*,
    b.bronze_rows,
    (select count(*) from silver)                                     as silver_rows,
    b.bronze_rows - (select count(*) from silver)                     as duplicate_rows_removed,
    (select count(*) from silver where has_name_variants)             as rows_with_name_variants
from measures as m
cross join bronze as b
