-- Silver may only drop rows whose metrics duplicate another row for the same
-- provider/segment. Totals of distinct metric rows must match bronze exactly.
with bronze_distinct as (
    select distinct
        trim(rendering_npi), trim(delivery_system), trim(provider_type), trim(age_group)
        {%- for metric in ['adv', 'prev', 'txmt', 'exam'] %},
        {{ metric }}_user_cnt, {{ metric }}_svc_cnt,
        {{ metric }}_user_annotation_code, {{ metric }}_svc_annotation_code
        {%- endfor %}
    from {{ ref('bronze_denti_cal_utilization') }}
)
select 'row_count_mismatch' as failure
where (select count(*) from bronze_distinct)
   <> (select count(*) from {{ ref('silver_provider_utilization') }})
