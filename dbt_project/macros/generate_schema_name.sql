{#
  dbt's default behavior prefixes a model's custom `schema` config with the
  target's default schema (e.g. schema='gold' becomes 'main_gold'). We want
  the literal schema names configured on each model (gold, staging, etc.),
  so override with the standard verbatim-name macro from dbt's docs.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
