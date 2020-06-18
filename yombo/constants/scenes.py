from voluptuous import Schema, Required, All, Length, Range, ALLOW_EXTRA

SCENE_DATA_COMPONENTS = ["configs", "triggers", "conditions", "actions"]

REQUIRED_ADDON_TRIGGER_KEYS = ["trigger_type", "description", "match_scene_trigger"]
REQUIRED_ADDON_CONDITION_KEYS = ["condition_type", "description"]  # Not implemented yet.
REQUIRED_ADDON_ACTION_KEYS = ["action_type", "description", "validate_scene_action", "handle_scene_action", "generate_scene_action_data_options"]

# REQUIRED_ACTION_RENDER_TABLE_COLUMNS = ["action_type", "attributes", "edit_url", "delete_url"]
#
# REQUIRED_RULE_FIELDS = ["trigger", "actions"]
# REQUIRED_TRIGGER_FIELDS = ["template"]
# REQUIRED_CONDITION_FIELDS = ["template"]
# REQUIRED_ACTION_FIELDS = ["action_type"]
#
# REQUIRED_SOURCE_FIELDS = ["platform"]
# REQUIRED_FILTER_FIELDS = ["platform"]

CONDITION_TYPE_AND = "and"
CONDITION_TYPE_OR = "or"

ACTION_DEVICE_SCHEMA = Schema({
    Required('device_machine_label'): All(str, Length(min=2)),
    Required('command_machine_label'): All(int, Length(min=2)),
    Required('command_machine_label'): All(int, Length(min=2)),
    Required('inputs'): Schema({}, extra=ALLOW_EXTRA),
    Required('weight'): All(int, Range(min=0)),
})

ACTION_PAUSE_SCHEMA = Schema({
    Required('weight'): All(int, Range(min=0)),
    Required('duration'): All(int, Range(min=0)),
})

ACTION_SCENE_SCHEMA = Schema({
    Required('scene_machine_label'): All(str, Length(min=2)),
    Required('scene_action'): ['enable', 'disable', 'start', 'stop'],
    Required('weight'): All(int, Range(min=0)),
})

ACTION_TEMPLATE_SCHEMA = Schema({
    Required('description'): All(str, Length(min=2)),
    Required('template'): All(str, Length(min=2)),
    Required('weight'): All(int, Range(min=0, max=500000)),
})

