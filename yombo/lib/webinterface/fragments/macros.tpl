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

{% macro select_device(devices, item, field, name, id, value) -%}
    <select class="selectpicker show-tick form-control" lass="selectpicker show-tick" title="Select..." name="{{name}}" id="{{id}}">
        <option value="" data-subtext="No device selected">None</option>
    {%- for device_id, device in devices.iteritems() %}
        <option value="{{device_id}}"{% if value == device_id %} selected{% endif %} data-subtext="{{device.machine_label}}">{{device.label}}</option>
    {%- endfor %}
    </select>
{%- endmacro %}

{% macro form_input_type(items, item, input_types, field, name, id, value="") -%}
    {%- if input_types[field.input_type_id].machine_label == "yombo_device" %}
    {{select_device(items, item, field, name, id, value)}}
    {%- else -%}
    <input type="text" class="form-control" name="{{name}}" id="{{id}}" value="{{value}}"
    {%- if field.required %} required{% endif %}>
    {%- endif -%}
{%- endmacro %}

{% macro edit_item_variables(items, item, input_types, variables) -%}
    {%- if variables|length != 0 -%}
        {%- for group_name, group in variables.iteritems() %}
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
                    {% for field_name, field in group.fields.iteritems() %}
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
                            {%- for data_id, data in field.data.iteritems() %}
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