-- Published patient counts are either a true zero or above the small-cell threshold;
-- values from 1 to 10 are withheld at the source. Validates the bounds used in
-- gold_program_kpis and confirms that a published 0 is a real zero, not a suppression.
{% set metrics = ['adv', 'prev', 'txmt', 'exam'] %}
select utilization_key
from {{ ref('silver_provider_utilization') }}
where
{% for m in metrics %}
    {{ m }}_users between {{ var('suppression_min') }} and {{ var('suppression_max') }}
    {{ "or" if not loop.last }}
{% endfor %}
