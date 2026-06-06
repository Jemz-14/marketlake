{#
  Build models into the schema named in `+schema` (e.g. silver, gold) directly,
  rather than dbt's default of prefixing it with the target schema
  (which would give silver -> <target>_silver). Keeps the medallion layer names
  clean in the warehouse.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
