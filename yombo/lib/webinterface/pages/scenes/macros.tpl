{% macro display_device(scene, item_id, item) %}
<tr class="highlight-device">
<td>
  <strong>Device:</strong>
  {% set device = _devices[item['device_id']] -%}
  {{device.full_label}}<br>
  <strong>Command:</strong>
  {{_commands[item['command_id']].label}}<br>
</td>
<td> {{item['weight']}} </td>
<td>
  <strong>Inputs:</strong><br>
  {%- set available_commands = device.available_commands() -%}
  {%- set inputs = available_commands[item['command_id']]['inputs'] -%}
  {% if item['inputs']|length == 0 %}No inputs
  {%- else -%}
  {%- for input_id, value in item['inputs'].items() -%}
  <i>{{ inputs[input_id]['label'] }}:</i> {{value}} <br>
  {%- endfor -%}
  {%- endif -%}
</td>
<td>
 <a href="/scenes/{{scene.scene_id}}/edit_device/{{item_id}}">Edit</a>
 <a href="/scenes/{{scene.scene_id}}/delete_device/{{item_id}}">Delete</a>
</td>
</tr>
{%- endmacro %}

{% macro display_pause(scene, item_id, item) %}
<tr class="highlight-pause">
<td> <strong>Pause</strong></td>
<td> {{item['weight']}} </td>
<td>
  <strong>Duration:</strong><br> {{item['duration']}} seconds<br>
</td>
<td>
 <a href="/scenes/{{scene.scene_id}}/edit_pause/{{item_id}}">Edit</a>
 <a href="/scenes/{{scene.scene_id}}/delete_pause/{{item_id}}">Delete</a>
</td>
</tr>
{%- endmacro %}

{% macro display_state(scene, item_id, item) %}
<tr class="highlight-state">
<td> <strong>State:</strong> {{item['name']}}</td>
<td> {{item['weight']}} </td>
<td>
  <strong>Set Value:</strong><br> {{item['value']}}<br>
</td>
<td>
 <a href="/scenes/{{scene.scene_id}}/edit_state/{{item_id}}">Edit</a>
 <a href="/scenes/{{scene.scene_id}}/delete_state/{{item_id}}">Delete</a>
</td>
</tr>
{%- endmacro %}