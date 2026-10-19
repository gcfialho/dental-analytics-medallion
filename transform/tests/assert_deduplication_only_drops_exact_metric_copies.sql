-- Silver may only drop rows whose metrics duplicate another row for the same
-- provider/segment. Totals of distinct metric rows must match bronze exactly.
with bronze_distinct as (
    select distinct
        trim(rendering_npi), trim(delivery_system), trim(provider_type), trim(age_group),
        adv_user_cnt, adv_svc_cnt, prev_user_cnt, prev_svc_cnt,
        txmt_user_cnt, txmt_svc_cnt, exam_user_cnt, exam_svc_cnt,
        adv_user_annotation_code, adv_svc_annotation_code
    from {{ ref('bronze_denti_cal_utilization') }}
)
select 'row_count_mismatch' as failure
where (select count(*) from bronze_distinct)
   <> (select count(*) from {{ ref('silver_provider_utilization') }})
