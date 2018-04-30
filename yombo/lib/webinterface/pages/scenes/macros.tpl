{% macro display_device(scene, action_id, action) %}
<tr class="highlight-device">
<td>
  <strong>Device:</strong>
  {% set device = _devices[action['device_machine_label']] -%}
  {% set command = _commands[action['command_machine_label']] -%}
  {{device.full_label}}<br>
  <strong>Command:</strong>
  {{_commands[action['command_machine_label']].label}}<br>
</td>
<td> {{action['weight']}} </td>
<td>
  <strong>Inputs:</strong><br>
  {%- set available_commands = device.available_commands() -%}
  {%- set inputs = available_commands[command.command_id]['inputs'] -%}
  {% if action['inputs']|length == 0 %}No inputs
  {%- else -%}
  {%- for input_id, value in action['inputs'].items() -%}
  <i>{{ inputs[input_id]['label'] }}:</i> {{value}} <br>
  {%- endfor -%}
  {%- endif -%}
</td>
<td>
{{edit_link('edit_device', scene.scene_id, action_id)}}
{{delete_link('delete_device', scene.scene_id, action_id)}}
{{up_link(scene.scene_id, action_id)}}
{{down_link(scene.scene_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_generic(scene, action_id, action) %}
{% set data = _scenes.get_scene_type_column_data(scene, action) %}
<tr class="highlight-pause">
<td> {{ data.action_type }} </td>
<td> {{action['weight']}} </td>
<td> {{ data.attributes }}
</td>
<td>
{{edit_link_full(data['edit_url'], scene.scene_id, action_id)}}
{{delete_link_full(data['delete_url'], scene.scene_id, action_id)}}
{{up_link(scene.scene_id, action_id)}}
{{down_link(scene.scene_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_pause(scene, action_id, action) %}
<tr class="highlight-pause">
<td> <strong>Pause</strong></td>
<td> {{action['weight']}} </td>
<td>
  <strong>Duration:</strong><br> {{action['duration']}} seconds<br>
</td>
<td>
{{edit_link('edit_pause', scene.scene_id, action_id)}}
{{delete_link('delete_pause', scene.scene_id, action_id)}}
{{up_link(scene.scene_id, action_id)}}
{{down_link(scene.scene_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_scene(scene, action_id, action) %}
<tr class="highlight-scene">
<td> <strong>Scene:</strong> {{_scenes[action['scene_machine_label']].label}}</td>
<td> {{action['weight']}} </td>
<td>
  <strong>Action:</strong><br> {{action['scene_action']}}<br>
</td>
<td>
{{edit_link('edit_scene', scene.scene_id, action_id)}}
{{delete_link('delete_scene', scene.scene_id, action_id)}}
{{up_link(scene.scene_id, action_id)}}
{{down_link(scene.scene_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro display_template(scene, action_id, action) %}
<tr class="highlight-template">
<td> <strong>Template</strong></td>
<td> {{action['weight']}} </td>
<td>
  <strong>Description:</strong><br> {{action['description']}}<br>
</td>
<td>
{{edit_link('edit_template', scene.scene_id, action_id)}}
{{delete_link('delete_template', scene.scene_id, action_id)}}
{{up_link(scene.scene_id, action_id)}}
{{down_link(scene.scene_id, action_id)}}
</td>
</tr>
{%- endmacro %}

{% macro edit_link(action, scene_id, action_id) %}
<a href="/scenes/{{scene_id}}/{{action}}/{{action_id}}" title="Edit action"><i class="fas fa-pencil-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro delete_link(action, scene_id, action_id) %}
<a href="/scenes/{{scene_id}}/{{action}}/{{action_id}}" title="Delete action"><i class="fas fa-trash-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro up_link(scene_id, action_id) %}
<a href="/scenes/{{scene_id}}/move_up/{{action_id}}" title="Move up"><i class="fas fa-arrow-up fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro down_link(scene_id, action_id) %}
<a href="/scenes/{{scene_id}}/move_down/{{action_id}}" title="Move down"><i class="fas fa-arrow-down fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro edit_link_full(url, scene_id, action_id) %}
<a href="{{url}}" title="Edit action"><i class="fas fa-pencil-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}

{% macro delete_link_full(url, scene_id, action_id) %}
<a href="{{url}}" title="Delete action"><i class="fas fa-trash-alt fa-lg"></i></a>&nbsp;&nbsp;
{%- endmacro %}
