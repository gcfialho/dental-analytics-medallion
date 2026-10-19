-- PREV/TXMT/EXAM are subsets of ADV (any dental service). If this ever fails, the
-- "ADV is the total" assumption behind every rate in gold is wrong.
select utilization_key
from {{ ref('silver_provider_utilization') }}
where prev_users > adv_users
   or txmt_users > adv_users
   or exam_users > adv_users
   or prev_services > adv_services
   or txmt_services > adv_services
   or exam_services > adv_services
