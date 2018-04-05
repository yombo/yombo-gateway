{% macro display_state(scene, item_id, item) %}
<tr class="highlight-state">
<td> <strong>State:</strong> {{item['name']}}</td>
<td> {{item['weight']}} </td>
<td>
  Set Value: {{item['value']}}<br>
</td>
<td>
 <a href="/scenes/{{scene.scene_id}}/edit_state/{{item_id}}">Edit</a>
 <a href="/scenes/{{scene.scene_id}}/delete_state/{{item_id}}">Delete</a>
</td>
</tr>
{%- endmacro %}

{% macro display_device(scene, item_id, item) %}
<tr class="highlight-device">
<td>
  <strong>Device:</strong>
  {{_devices[item['device_id']].label}}<br>
  <strong>Command:</strong>
  {{_commands[item['command_id']].label}}<br>
</td>
<td> {{item['weight']}} </td>
<td>
  <strong>Inputs:</strong><br>
  {% if item['inputs']|length == 0 %}No inputs
  {%- else -%}
  {%- for input_id, value in item['inputs'].items() -%}
  <i>{{ _inputtypes[input_id].label }}:</i> value <br>
  {%- endfor -%}
  {%- endif -%}
</td>
<td>
 <a href="/scenes/{{scene.scene_id}}/edit_state/{{item_id}}">Edit</a>
 <a href="/scenes/{{scene.scene_id}}/delete_state/{{item_id}}">Delete</a>
</td>
</tr>
{%- endmacro %}
