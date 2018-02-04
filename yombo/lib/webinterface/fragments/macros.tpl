{% macro modal(id='the_id', label='Modal Label', content='Modal Content') -%}
<div class="modal fade" id="{{ id }}" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h4 class="modal-title" id="ModalLabel-{{ id }}">{{ label }}</h4>
            </div>
            <div class="modal-body">{{ content }}</div>
            <div class="modal-footer">
                <button type="button" class="btn btn-primary" data-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>
{%- endmacro %}

{% macro modalfast(id='the_id', label='Modal Label', content='Modal Content') -%}
<div class="modal" id="{{ id }}" tabindex="-1" role="dialog" aria-labelledby="myModalLabel">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                <h4 class="modal-title" id="ModalLabel-{{ id }}">{{ label }}</h4>
            </div>
            <div class="modal-body">
                  {{ content }}
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-primary" data-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>
{%- endmacro %}

{% macro form_select_state(states, input_name, input_id, selected_item) -%}
    <select class="selectpicker show-tick form-control" lass="selectpicker show-tick" title="Select..." name="{{input_name}}" id="{{input_id}}">
        <option value="" data-subtext="No state selected">None</option>
    {%- for state_id, state in states.items() %}
        <option value="{{state_id}}"{% if selected_item == state_id %} selected{% endif %} data-subtext="{{state['value_human']}}">{{state_id}}</option>
    {%- endfor %}
    </select>
{%- endmacro %}

{% macro form_select_device(devices, input_name, input_id, selected_item) -%}
    <select class="selectpicker show-tick form-control" lass="selectpicker show-tick" title="Select..." name="{{input_name}}" id="{{input_id}}">
        <option value="" data-subtext="No device selected">None</option>
    {%- for device_id, device in devices.items() %}
        <option value="{{device_id}}"{% if selected_item == device_id %} selected{% endif %} data-subtext="{{device.machine_label}}">{{device.full_label}}</option>
    {%- endfor %}
    </select>
{%- endmacro %}

{% macro form_select_users(users, input_name, input_id, selected_item) -%}
    <select class="selectpicker show-tick form-control" lass="selectpicker show-tick" title="Select..." name="{{input_name}}" id="{{input_id}}">
        <option value="" data-subtext="No user selected">None</option>
    {%- for user_id, user in users.items() %}
        <option value="{{user_id}}"{% if selected_item == user_id %} selected{% endif %} data-subtext="{{user.machine_label}}">{{device.full_label}}</option>
    {%- endfor %}
    </select>
{%- endmacro %}

{% macro form_input_type(items, item, input_types, field, input_name, input_id, value="") -%}
    {%- if input_types[field.input_type_id].machine_label == "yombo_device" %}
    {{form_select_device(items, input_name, input_id, value)}}
    {%- elif input_types[field.input_type_id].machine_label == "password" %}
    <input type="password" class="form-control" name="{{input_name}}" id="{{input_id}}" value="^^USE^ORIG^^"
    {%- else -%}
    <input type="text" class="form-control" name="{{input_name}}" id="{{input_id}}" value="{{value}}"
    {%- if field.required %} required{% endif %}>
    {%- endif -%}
{%- endmacro %}

{% macro edit_item_variables(items, item, input_types, variables) -%}
    {%- if variables|length != 0 -%}
        {%- for group_name, group in variables.items() %}
        <div class="panel panel-default">
            <div class="panel-heading">
                <h4>{{ group.group_label }}</h4>
                {{ group.group_description }}
            </div>
            <div class="panel-body">
                <table width="100%" class="table table-striped table-bordered table-hover" id="{{ group.id }}">
                    <thead>
                        <tr>
                            <th>Field Information</th><th>Value(s)</th>
                        </tr>
                    </thead>
                    <tbody>
                    {% for field_name, field in group.fields.items() %}
                    <tr>
                        <td><b>{{ field.field_label }}</b>
                            {%- if field.field_help_text|length > 0 %}
                            {%- set modalID = "modalfieldhelp" + field.id %}
                            {{ modal(modalID, field.field_label, field.field_help_text) }}
                            <a href="#" data-toggle="modal" data-target="#{{modalID}}"><i class="fa fa-question fa-lg"></i></a>
                            {%- endif %}
                            <br>{{ field.field_description }}
                        </td>
                        <td>{%- if field.data|length > 0 %}
                            {%- for data_id, data in field.data.items() %}
                            {{form_input_type(items, item, input_types, field, "vars[" ~ field.id ~ "][" ~ data_id ~ "][input]", "vars[" ~ field.id ~ "][" ~ data_id ~ "][input]",  data.value|display_encrypted)}}
                             <input type="hidden" name="vars[{{ field.id }}][{{ data_id }}][orig]" id="vars[{{ field.id }}][{{ data.id }}][orig]" value="{{ data.value }}">
                            {%- endfor %}
                            {%- endif %}
                            {%- if field.multiple or field.data|length == 0%}
                            {{form_input_type(items, item, input_types, field, "vars[" ~ field.id ~ "][new_2]", "vars[" ~ field.id ~ "][new_2]")}}
                            {%- endif %}
                        </td>
                     </tr>
                    {%- endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {%- endfor %}
    {% else %}
        <h4>No Variables</h4>
    {%- endif %}
{%- endmacro %}