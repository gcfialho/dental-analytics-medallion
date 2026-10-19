{% macro safe_divide(numerator, denominator) -%}
    ({{ numerator }})::double / nullif({{ denominator }}, 0)
{%- endmacro %}
