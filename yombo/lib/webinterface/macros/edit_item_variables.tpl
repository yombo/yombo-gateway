{% import "lib/webinterface/fragments/macros.tpl" as macros%}

{% macro edit_item_variables(device_variables) -%}
{%- if device_variables|length != 0 -%}
    {%- for group_name, group in device_variables.iteritems() %}
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
                        {% set modalID = "modalfieldhelp" + field.id %}
                        {{ macros.modal(modalID, field.field_label, field.field_help_text) }}
                        <a href="#" data-toggle="modal" data-target="#{{modalID}}"><i class="fa fa-question fa-lg"></i></a>
                        {%- endif %}
                        <br>{{ field.field_description }}
                    </td>
                    <td>{%- if field.data|length > 0 %}
                        {%- for data_id, data in field.data.iteritems() %}
                            <input type="text" class="form-control" name="vars[{{ field.id }}][{{ data_id }}][input]" id="vars[{{ field.id }}][{{ data.id }}][input]" value="{{ data.value|display_encrypted }}"
                            {% if field.required %} required{% endif %}>
                            <input type="hidden" name="vars[{{ field.id }}][{{ data_id }}][orig]" id="vars[{{ field.id }}][{{ data.id }}][orig]" value="{{ data.value }}">
                        {%- endfor %}
                        {%- endif %}
                        {%- if field.multiple or field.data|length == 0%}
                            <input type="text" class="form-control" name="vars[{{ field.id }}][new_2]" id="vars[{{ field.id }}][new_1]" value=""
                            {% if field.required %} required{% endif %}>
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
