-- Every patient counted received at least one service.
select utilization_key
from {{ ref('silver_provider_utilization') }}
where adv_users > adv_services
   or prev_users > prev_services
   or txmt_users > txmt_services
   or exam_users > exam_services
