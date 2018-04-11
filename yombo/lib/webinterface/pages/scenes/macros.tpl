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
{{edit_link('edit_device', scene.scene_id, item_id)}}
{{delete_link('delete_device', scene.scene_id, item_id)}}
{{up_link(scene.scene_id, item_id)}}
{{down_link(scene.scene_id, item_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_generic(scene, item_id, item) %}
{% set data = _scenes.get_scene_type_column_data(scene, item) %}
<tr class="highlight-pause">
<td> {{ data.type }} </td>
<td> {{item['weight']}} </td>
<td> {{ data.attributes }}
</td>
<td>
{{edit_link_full(data['edit_url'], scene.scene_id, item_id)}}
{{delete_link_full(data['delete_url'], scene.scene_id, item_id)}}
{{up_link(scene.scene_id, item_id)}}
{{down_link(scene.scene_id, item_id)}}
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
{{edit_link('edit_pause', scene.scene_id, item_id)}}
{{delete_link('delete_pause', scene.scene_id, item_id)}}
{{up_link(scene.scene_id, item_id)}}
{{down_link(scene.scene_id, item_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_scene(scene, item_id, item) %}
<tr class="highlight-scene">
<td> <strong>Scene:</strong> {{_scenes[item['machine_label']].label}}</td>
<td> {{item['weight']}} </td>
<td>
  <strong>Action:</strong><br> {{item['action']}}<br>
</td>
<td>
{{edit_link('edit_scene', scene.scene_id, item_id)}}
{{delete_link('delete_scene', scene.scene_id, item_id)}}
{{up_link(scene.scene_id, item_id)}}
{{down_link(scene.scene_id, item_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_template(scene, item_id, item) %}
<tr class="highlight-template">
<td> <strong>Template</strong></td>
<td> {{item['weight']}} </td>
<td>
  <strong>Description:</strong><br> {{item['description']}}<br>
</td>
<td>
{{edit_link('edit_template', scene.scene_id, item_id)}}
{{delete_link('delete_template', scene.scene_id, item_id)}}
{{up_link(scene.scene_id, item_id)}}
{{down_link(scene.scene_id, item_id)}}
</td>
</tr>
{%- endmacro %}

{% macro edit_link(action, scene_id, item_id) %}
<a href="/scenes/{{scene_id}}/{{action}}/{{item_id}}" title="Edit item"><i class="fas fa-pencil-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro delete_link(action, scene_id, item_id) %}
<a href="/scenes/{{scene_id}}/{{action}}/{{item_id}}" title="Delete item"><i class="fas fa-trash-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro up_link(scene_id, item_id) %}
<a href="/scenes/{{scene_id}}/move_up/{{item_id}}" title="Move up"><i class="fas fa-arrow-up fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro down_link(scene_id, item_id) %}
<a href="/scenes/{{scene_id}}/move_down/{{item_id}}" title="Move down"><i class="fas fa-arrow-down fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro edit_link_full(url, scene_id, item_id) %}
<a href="{{url}}" title="Edit item"><i class="fas fa-pencil-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro delete_link_full(url, scene_id, item_id) %}
<a href="{{url}}" title="Delete item"><i class="fas fa-trash-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}
