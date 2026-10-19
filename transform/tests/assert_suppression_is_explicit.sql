-- A blank count must always carry an annotation code, and an annotated count must be
-- blank. Otherwise "NULL means suppressed" would silently mix in missing data.
{% set metrics = ['adv', 'prev', 'txmt', 'exam'] %}
select utilization_key
from {{ ref('silver_provider_utilization') }}
where
{% for m in metrics %}
    ({{ m }}_users is null) <> ({{ m }}_users_annotation is not null)
    or ({{ m }}_services is null) <> ({{ m }}_services_annotation is not null)
    {{ "or" if not loop.last }}
{% endfor %}
