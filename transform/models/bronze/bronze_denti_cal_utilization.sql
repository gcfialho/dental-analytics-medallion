-- Raw Denti-Cal extract exactly as published: every value kept as text, column
-- names normalized to snake_case, plus lineage columns. No business logic here.

with source as (

    select *
    from read_csv(
        '{{ var("raw_csv_path") }}',
        delim = ';',
        header = true,
        all_varchar = true,
        filename = true
    )

)

select
    "RENDERING_NPI"               as rendering_npi,
    "PROVIDER_LEGAL_NAME"         as provider_legal_name,
    "CALENDAR_YEAR"               as calendar_year,
    "DELIVERY_SYSTEM"             as delivery_system,
    "PROVIDER_TYPE"               as provider_type,
    "AGE_GROUP"                   as age_group,
    "ADV_USER_CNT"                as adv_user_cnt,
    "ADV_USER_ANNOTATION_CODE"    as adv_user_annotation_code,
    "ADV_SVC_CNT"                 as adv_svc_cnt,
    "ADV_SVC_ANNOTATION_CODE"     as adv_svc_annotation_code,
    "PREV_USER_CNT"               as prev_user_cnt,
    "PREV_USER_ANNOTATION_CODE"   as prev_user_annotation_code,
    "PREV_SVC_CNT"                as prev_svc_cnt,
    "PREV_SVC_ANNOTATION_CODE"    as prev_svc_annotation_code,
    "TXMT_USER_CNT"               as txmt_user_cnt,
    -- The published header contains a stray space: "TXMT_USER_ ANNOTATION_CODE".
    "TXMT_USER_ ANNOTATION_CODE"  as txmt_user_annotation_code,
    "TXMT_SVC_CNT"                as txmt_svc_cnt,
    "TXMT_SVC_ANNOTATION_CODE"    as txmt_svc_annotation_code,
    "EXAM_USER_CNT"               as exam_user_cnt,
    "EXAM_USER_ANNOTATION_CODE"   as exam_user_annotation_code,
    "EXAM_SVC_CNT"                as exam_svc_cnt,
    "EXAM_SVC_ANNOTATION_CODE"    as exam_svc_annotation_code,
    parse_filename(filename)      as _source_file,
    row_number() over ()          as _source_row
from source
