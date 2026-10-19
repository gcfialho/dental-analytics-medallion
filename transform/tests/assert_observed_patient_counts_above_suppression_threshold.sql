-- Published patient counts must be above the small-cell threshold; smaller values
-- are withheld at the source. Validates the bounds used in gold_program_kpis.
{% set metrics = ['adv', 'prev', 'txmt', 'exam'] %}
select utilization_key
from {{ ref('silver_provider_utilization') }}
where
{% for m in metrics %}
    {{ m }}_users <= {{ var('suppression_max') }}
    {{ "or" if not loop.last }}
{% endfor %}
