{% macro display_state(scene, item_id, item) -%}
<td> State: {{item['name']}}</td>
<td> {{item['weight']}} </td>
<td>
  Set Value: {{item['value']}}<br>
</td>
<td>
 <a href="/scenes/{{scene.scene_id}}/edit_state/{{item_id}}">Edit</a>
 <a href="/scenes/{{scene.scene_id}}/edit_delete/{{item_id}}">Delete</a>
</td>

{%- endmacro %}

{% macro display_device(scene, item_id, item) -%}
<div class="row">
    <div class="col-lg-12">
        <div class="panel panel-default">
            <div class="panel-body">
                <label style="margin-top: 0px; margin-bottom: 0px">Item Type: </label><br>
                State<br>
                <label style="margin-top: 15px; margin-bottom: 0px">Item Weight: </label><br>
                {{ item['weight'] }}<br>
                <label style="margin-top: 15px; margin-bottom: 0px">State Name: </label><br>
                {{ item['name'] }}<br>
                <label style="margin-top: 15px; margin-bottom: 0px">Set Value: </label><br>
                {{ item['value'] }}<br>
            </div>
        </div>
    </div>
</div>
{%- endmacro %}
