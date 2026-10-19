{% test exactly_one_row(model) %}
select count(*) as row_count from {{ model }} having count(*) <> 1
{% endtest %}
