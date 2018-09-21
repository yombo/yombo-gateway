{%- macro item_label(platform, item) -%}
  {%- if platform == 'automation' %}
    {%- if item == "*" %}All automation rules
    {%- else %}
    {%- set automation = _automation[item] %}
<a href="/automation/{{automation.rule_id}}/details">{{ automation.label }}</a>
  {%- endif %}
  {%- elif platform == 'device' %}
    {%- if item == "*" %}All devices
    {%- else %}
      {%- set device = _devices[item] %}
<a href="/devices/{{device.device_id}}/details">{{ device.full_label }}</a>
  {%- endif %}
  {%- elif platform == 'scene' %}
    {%- if item == "*" %}All scenes
    {%- else %}
      {%- set scene = _scenes[item] -%}
<a href="/scenes/{{scene.scene_id}}/details">{{ scene.label }}</a>
    {%- endif %}
  {%- else %}{{ item }}
  {%- endif %}
{%- endmacro %}
