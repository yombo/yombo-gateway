"""
Database update file verion: 1

Details:
Setups the initial database schema.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

from yombo.utils.db import create_index

@inlineCallbacks
def upgrade(Registry, **kwargs):
    # Handles version tracking for the database schema
    yield Registry.DBPOOL.runQuery('CREATE TABLE schema_version(table_name TEXT NOT NULL, version INTEGER NOT NULL, PRIMARY KEY(table_name))')
    yield Registry.DBPOOL.runQuery('INSERT INTO schema_version(table_name, version) VALUES ("core", 1)')

    # Defines the commands table. Lists all possible commands a local or remote gateway can perform.
    table = """CREATE TABLE `categories` (
     `id`            TEXT NOT NULL, /* commandUUID */
     `parent_id` TEXT NOT NULL,
     `category_type` TEXT NOT NULL,
     `machine_label` TEXT NOT NULL,
     `label`         TEXT NOT NULL,
     `description`   TEXT,
     `status`        INTEGER NOT NULL,
     `created`       INTEGER NOT NULL,
     `updated`       INTEGER NOT NULL,
     PRIMARY KEY(id) );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('categories', 'id', unique=True))
    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS categoires_type_machine_label_IDX ON categories (machine_label, category_type)")

    # Defines the commands table. Lists all possible commands a local or remote gateway can perform.
    table = """CREATE TABLE `commands` (
     `id`            TEXT NOT NULL, /* commandUUID */
     `machine_label` TEXT NOT NULL,
     `voice_cmd`     TEXT,
     `label`         TEXT NOT NULL,
     `description`   TEXT,
     `always_load`   INTEGER DEFAULT 0,
     `public`        INTEGER NOT NULL,
     `status`        INTEGER NOT NULL,
     `created`       INTEGER NOT NULL,
     `updated_srv`   INTEGER DEFAULT 0,
     `updated`       INTEGER NOT NULL,
     PRIMARY KEY(id) );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('commands', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('commands', 'machine_label', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('commands', 'voice_cmd'))

    # Defines the devices table. Lists all possible devices for local gateway and related remote gateways.
    table = """CREATE TABLE `devices` (
     `id`              TEXT NOT NULL,
     `gateway_id`      TEXT NOT NULL,
     `device_type_id`  TEXT NOT NULL,
     `machine_label`   TEXT NOT NULL,
     `label`           TEXT NOT NULL,
     `description`     TEXT,
     `statistic_label` TEXT,
     `statistic_lifetime` INTEGER DEFAULT 0,
     `notes`           TEXT,
     `voice_cmd`       TEXT,
     `voice_cmd_order` TEXT,
     `voice_cmd_src`   TEXT,
     `energy_type`     TEXT,
     `energy_tracker_source` TEXT,
     `energy_tracker_device` TEXT,
     `energy_map`      TEXT,
     `pin_code`        TEXT,
     `pin_required`    INTEGER NOT NULL,
     `pin_timeout`     INTEGER DEFAULT 0,
     `status`          INTEGER NOT NULL,
     `created`         INTEGER NOT NULL,
     `updated_srv`     INTEGER DEFAULT 0,
     `updated`         INTEGER NOT NULL,
/*     FOREIGN KEY(device_type_id) REFERENCES artist(device_types) */
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('devices', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('devices', 'device_type_id'))
    yield Registry.DBPOOL.runQuery(create_index('devices', 'gateway_id'))

    # All possible inputs for a given device type/command/input.
    table = """CREATE TABLE `device_command_inputs` (
         `id`             TEXT NOT NULL,
         `device_type_id` TEXT NOT NULL,
         `command_id`     TEXT NOT NULL,
         `input_type_id`  TEXT NOT NULL,
         `live_update`    INTEGER NOT NULL,
         `value_required` INTEGER NOT NULL,
         `value_max`      INTEGER NOT NULL,
         `value_min`      INTEGER NOT NULL,
         `value_casing`   TEXT NOT NULL,
         `encryption`     TEXT NOT NULL,
         `notes`          TEXT,
         `always_load`    INTEGER DEFAULT 0,
         `updated`        INTEGER NOT NULL,
         `created`        INTEGER NOT NULL,
         UNIQUE (device_type_id, command_id, input_type_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_command_inputs', 'device_type_id'))

    #  Defines the device status table. Stores device status information.
    table = """CREATE TABLE `device_status` (
     `id`                   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `device_id`            TEXT NOT NULL, /* device_id */
     `set_time`             REAL NOT NULL,
     `energy_usage`         INTEGER NOT NULL,
     `human_status`         TEXT NOT NULL,
     `human_message`         TEXT NOT NULL,
     `machine_status`       TEXT NOT NULL,
     `machine_status_extra` TEXT,
     `requested_by`         TEXT NOT NULL,
     `source`               TEXT NOT NULL,
     `uploaded`             INTEGER NOT NULL DEFAULT 0,
     `uploadable`           INTEGER NOT NULL DEFAULT 0 /* For security, only items marked as 1 can be sent externally */
     );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'device_id'))
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'uploaded'))

    # Device types defines the features of a device. For example, all X10 appliances or Insteon Lamps.
    table = """CREATE TABLE `device_types` (
     `id`            TEXT NOT NULL,
     `machine_label` TEXT NOT NULL,
     `label`         TEXT NOT NULL,
     `description`   TEXT,
     `category_id`   TEXT,
     `public`        INTEGER,
     `status`        INTEGER,
     `always_load`   INTEGER DEFAULT 0,
     `created`       INTEGER,
     `updated_srv`   INTEGER DEFAULT 0,
     `updated`       INTEGER,
      UNIQUE (label) ON CONFLICT IGNORE,
      UNIQUE (machine_label) ON CONFLICT IGNORE,
      PRIMARY KEY(id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
#    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_machine_label_idx ON device_types (machine_label) ON CONFLICT IGNORE")
#    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_label_idx ON device_types (label) ON CONFLICT IGNORE")
    yield Registry.DBPOOL.runQuery(create_index('device_types', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('device_types', 'machine_label', unique=True))

    # All possible commands for a given device type. For examples, appliances are on and off.
    table = """CREATE TABLE `device_type_commands` (
         `id`             TEXT NOT NULL,
         `device_type_id` TEXT NOT NULL,
         `command_id`     TEXT NOT NULL,
         `created`        INTEGER NOT NULL,
         UNIQUE (device_type_id, command_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_type_commands', 'device_type_id'))
    # yield Registry.DBPOOL.runQuery(create_index('command_device_types', 'command_id'))
    #    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS command_device_types_command_id_device_type_id_IDX ON command_device_types (command_id, device_type_id)")

    # Used for quick access to GPG keys instead of key ring.
    table = """CREATE TABLE `gpg_keys` (
     `id`          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `notes`       TEXT,
     `endpoint`    TEXT NOT NULL,
     `keyid` TEXT NOT NULL,
     `fingerprint` TEXT NOT NULL,
     `length`      INTEGER NOT NULL,
     `expires`     INTEGER NOT NULL,
     `publickey`   TEXT NOT NULL,
     `have_private` INTEGER NOT NULL,
     `created`     INTEGER NOT NULL
     );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('gpg_keys', 'endpoint'))
    yield Registry.DBPOOL.runQuery(create_index('gpg_keys', 'fingerprint'))

    # Device types defines the features of a device. For example, all X10 appliances or Insteon Lamps.
    table = """CREATE TABLE `input_types` (
     `id`            TEXT NOT NULL,
     `category_id`   TEXT NOT NULL,
     `machine_label` TEXT NOT NULL,
     `label`         TEXT NOT NULL,
     `description`   TEXT,
     `input_regex`   TEXT,
     `public`        INTEGER,
     `always_load`   INTEGER DEFAULT 0,
     `status`        INTEGER,
     `created`       INTEGER,
     `updated_srv`   INTEGER DEFAULT 0,
     `updated`       INTEGER,
      UNIQUE (label) ON CONFLICT IGNORE,
      UNIQUE (machine_label) ON CONFLICT IGNORE,
      PRIMARY KEY(id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)

    # To be completed
    table = """CREATE TABLE `logs` (
     `id`           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `type`         TEXT NOT NULL, /* system, user, etc */
     `priority`     TEXT NOT NULL, /* debug, low, normal, high, urgent */
     `source`       TEXT NOT NULL, /* where this message was created */
     `message`      TEXT, /* Message data */
     `meta`         TEXT, /* Any extra meta data. JSON format */
     `created`      INTEGER NOT NULL);"""

    # Defines the config table for the local gateway.
    table = """CREATE TABLE `meta` (
         `id`           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
         `meta_key`  TEXT NOT NULL,
         `meta_value`   TEXT NOT NULL,
         `created`       INTEGER NOT NULL,
         `updated`      INTEGER NOT NULL);"""
    #    yield Registry.DBPOOL.runQuery(table)
    #    yield Registry.DBPOOL.runQuery(create_index('meta', 'meta_key'))
    #    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS configs_config_key_config_key_IDX ON configs (config_path, config_key)")

    # Stores module information
    table = """CREATE TABLE `modules` (
     `id`             TEXT NOT NULL, /* moduleUUID */
     `gateway_id`     TEXT NOT NULL,
     `machine_label`  TEXT NOT NULL,
     `module_type`    TEXT NOT NULL,
     `label`          TEXT NOT NULL,
     `short_description`       TEXT,
     `description`             TEXT,
     `description_formatting`  TEXT,
     `see_also`           TEXT,
     `repository_link`    TEXT,
     `issue_tracker_link` TEXT,
     `install_count`  INTEGER DEFAULT 0,
     `doc_link`       TEXT,
     `git_link`       TEXT,
     `install_branch` TEXT NOT NULL,
     `prod_branch`    TEXT NOT NULL,
     `dev_branch`     TEXT,
     `prod_version`   TEXT,
     `dev_version`    TEXT,
     `public`         INTEGER NOT NULL,
     `status`         INTEGER NOT NULL, /* disabled, enabled, deleted */
     `created`        INTEGER NOT NULL,
     `updated_srv`    INTEGER DEFAULT 0,
     `updated`        INTEGER NOT NULL,
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('modules', 'machine_label'))

    # All possible device types for a module
    table = """CREATE TABLE `module_device_types` (
         `id`             TEXT NOT NULL,
         `module_id`      TEXT NOT NULL,
         `device_type_id` TEXT NOT NULL,
         `created`        INTEGER NOT NULL,
         UNIQUE (module_id, device_type_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS module_device_types_module_dt_id_idx ON module_device_types (module_id, device_type_id)")
    # yield Registry.DBPOOL.runQuery(create_index('command_device_types', 'command_id'))
    #    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS command_device_types_command_id_device_type_id_IDX ON command_device_types (command_id, device_type_id)")

    # Tracks what versions of a module is installed, when it was installed, and last checked for new version.
    table = """CREATE TABLE `module_installed` (
     `id`                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `module_id`         TEXT NOT NULL, /* module.id */
     `installed_version` TEXT NOT NULL,
     `install_time`      INTEGER NOT NULL,
     `last_check`        INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('module_installed', 'module_id'))

    ## Create view for modules ##
    view = """CREATE VIEW modules_view AS
    SELECT modules.*, module_installed.installed_version, module_installed. install_time, module_installed.last_check
    FROM modules LEFT OUTER JOIN module_installed ON modules.id = module_installed.module_id"""
    yield Registry.DBPOOL.runQuery(view)

    #  Defines the statistics data table. Stores node items.
    table = """CREATE TABLE `nodes` (
     `id`             TEXT NOT NULL,
     `parent_id`      TEXT NOT NULL,
     `gateway_id`     TEXT NOT NULL,
     `node_type`      TEXT NOT NULL,
     `weight`         INTEGER NOT NULL,
     `machine_label`  TEXT NOT NULL,
     `gw_always_load` INTEGER NOT NULL,
     `destination`  TEXT NOT NULL,
     `data`           BLOB,
     `data_type`      TEXT NOT NULL,
     `status`         INTEGER NOT NULL, /* Timestemp when msg was ack'd by the user. */
     `updated`        INTEGER NOT NULL,
     `created`        INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('nodes', 'id'))
    yield Registry.DBPOOL.runQuery(create_index('nodes', 'parent_id'))

    #  Defines the statistics data table. Stores statistics.
    table = """CREATE TABLE `notifications` (
     `id`           TEXT NOT NULL,
     `type`         TEXT NOT NULL, /* system, user, etc */
     `priority`     TEXT NOT NULL, /* debug, low, normal, high, urgent */
     `source`       TEXT NOT NULL, /* where this message was created */
     `expire`       INTEGER NOT NULL, /* timestamp when msg should expire */
     `always_show`  INTEGER NOT NULL, /* If notification should always show until user clears it. */
     `always_show_allow_clear` INTEGER NOT NULL, /* User allowed to clear notification form always_show. */
     `acknowledged` INTEGER NOT NULL, /* Timestemp when msg was ack'd by the user. */
     `title`        TEXT, /* Message data */
     `message`      TEXT, /* Message data */
     `meta`         TEXT, /* Any extra meta data. JSON format */
     `created`      INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('notifications', 'id'))

    # Defines the SQL Dict table. Used by the :class:`SQLDict` class to maintain persistent dictionaries.
    table = """CREATE TABLE `sqldict` (
     `id`        INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `component` TEXT NOT NULL,
     `dict_name` INTEGER NOT NULL,
     `dict_data` BLOB,
     `created`   INTEGER NOT NULL,
     `updated`   INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('sqldict', 'dict_name'))
    yield Registry.DBPOOL.runQuery(create_index('sqldict', 'component'))

    # Defines the tables used to store state information.
    table = """CREATE TABLE `states` (
     `id`          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `name`    TEXT NOT NULL,
     `value_type` TEXT,
     `value`   INTEGER NOT NULL,
     `live`   INTEGER NOT NULL,
     `created` INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('states', 'name'))
    yield Registry.DBPOOL.runQuery(create_index('states', 'created'))

    #  Defines the statistics data table. Stores statistics.
    table = """CREATE TABLE `statistics` (
     `id`                  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `bucket_time`         DECIMAL(13,3) NOT NULL,
     `bucket_size`         INTEGER NOT NULL,
     `bucket_type`         TEXT NOT NULL,
     `bucket_name`         TEXT NOT NULL,
     `bucket_value`        REAL NOT NULL,
     `bucket_average_data` TEXT,
     `anon`                INTEGER NOT NULL DEFAULT 0, /* anon data */
     `uploaded`            INTEGER NOT NULL DEFAULT 0,
     `finished`            INTEGER NOT NULL DEFAULT 0,
     `updated`             INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('statistics', 'bucket_type'))
    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS table_b_t_IDX ON statistics (bucket_name, bucket_type, bucket_time)")
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS table_t_n_t_IDX ON statistics (finished, uploaded, anon)")

    # Used by the tasks library to start various tasks.
    table = """CREATE TABLE `tasks` (
     `id`             INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `run_section`    INTEGER NOT NULL,
     `run_once`       INTEGER,
     `run_interval`   INTEGER,
     `task_component` TEXT NOT NULL,
     `task_name`      TEXT NOT NULL,
     `task_arguments` BLOB,
     `source`         TEXT NOT NULL,
     `created`        INTEGER NOT NULL
     );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'device_id'))
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'uploaded'))

    table = """CREATE TABLE `users` (
     `id`         TEXT NOT NULL,
     `gateway_id` TEXT NOT NULL,
     `user_id`    TEXT NOT NULL,
     `email`      TEXT NOT NULL,
     `updated`    INTEGER NOT NULL,
     `created`    INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('users', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('users', 'email'))

    table = """CREATE TABLE `user_permission` (
     `id`            TEXT NOT NULL,
     `user_id`       TEXT NOT NULL,
     `gateway_id`    TEXT NOT NULL,
     `permission_id` TEXT NOT NULL,
     `updated`       INTEGER NOT NULL,
     `created`       INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('user_permission', 'id', unique=True))

    table = """CREATE TABLE `permissions` (
     `id`         TEXT NOT NULL,
     `gateway_id` TEXT NOT NULL,
     `updated`    INTEGER NOT NULL,
     `created`    INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('permissions', 'id', unique=True))

    # Defines the web interface session store. Used by the :class:`WebInterface` class to maintain session information
    table = """CREATE TABLE `webinterface_sessions` (
     `id`           TEXT NOT NULL, /* moduleUUID */
     `session_data` TEXT NOT NULL,
     `created`      INTEGER NOT NULL,
     `last_access`     INTEGER NOT NULL,
     `updated`      INTEGER NOT NULL,
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('webinterface_sessions', 'created'))
    yield Registry.DBPOOL.runQuery(create_index('webinterface_sessions', 'updated'))


    # The following three tables and following views manages the variables set for devices and modules.
    table = """ CREATE TABLE `variable_groups` (
     `id`                  TEXT NOT NULL, /* group_id */
     `group_relation_id`         TEXT NOT NULL,
     `group_relation_type`       TEXT NOT NULL,
     `group_machine_label` TEXT NOT NULL,
     `group_label`         TEXT NOT NULL,
     `group_description`   TEXT NOT NULL,
     `group_weight`        INTEGER DEFAULT 0,
     `status`              INTEGER NOT NULL, /* disabled, enabled, deleted */
     `updated_srv`         INTEGER DEFAULT 0,
     `updated`             INTEGER NOT NULL,
     `created`             INTEGER NOT NULL,
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS variable_groups_relation_id_type_idx ON variable_groups (group_relation_id, group_relation_type)")

    table = """ CREATE TABLE `variable_fields` (
     `id`                  TEXT NOT NULL, /* field_id */
     `group_id`            TEXT NOT NULL,
     `field_machine_label` TEXT NOT NULL,
     `field_label`         TEXT NOT NULL,
     `field_description`   TEXT NOT NULL,
     `field_weight`        INTEGER DEFAULT 0,
     `value_required`      INTEGER NOT NULL,
     `value_max`           INTEGER,
     `value_min`           INTEGER,
     `value_casing`        TEXT NOT NULL,
     `encryption`          TEXT NOT NULL,
     `input_type_id`       TEXT NOT NULL,
     `default_value`       TEXT NOT NULL,
     `help_text`           TEXT NOT NULL,
     `multiple`            INTEGER NOT NULL,
     `updated_srv`         INTEGER DEFAULT 0,
     `updated`             INTEGER NOT NULL,
     `created`             INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('variable_fields', 'group_id'))
    #    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_machine_label_idx ON device_types (machine_label) ON CONFLICT IGNORE")

    table = """ CREATE TABLE `variable_data` (
     `id`            TEXT NOT NULL,  /* field_id */
     `gateway_id`    TEXT DEFAULT 0,
     `field_id`      TEXT NOT NULL,
     `data_relation_id`   TEXT NOT NULL,
     `data_relation_type` TEXT NOT NULL,
     `data`          TEXT NOT NULL,
     `data_weight`   INTEGER DEFAULT 0,
     `updated_srv`   INTEGER DEFAULT 0,
     `updated`       INTEGER NOT NULL,
     `created`       INTEGER NOT NULL,
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS variable_data_id_type_idx ON variable_data (field_id, data_relation_id, data_relation_type)")

    ## Create view for easily consuming the above tables during gateway startup
    # view = """CREATE VIEW variables_view AS
    # SELECT modules.*, module_installed.installed_version, module_installed. install_time, module_installed.last_check
    # FROM modules LEFT OUTER JOIN module_installed ON modules.id = module_installed.module_id"""
    # yield Registry.DBPOOL.runQuery(view)


    # Stores variables for modules and devices. Variables are set by the server, and read here. Not a two-way sync (yet?).
    # table = """CREATE TABLE `variables` (
    #  `id`      TEXT NOT NULL, /* field_id */
    #  `variable_type` TEXT NOT NULL,
    #  `variable_id`    TEXT NOT NULL,
    #  `foreign_id`    TEXT NOT NULL,
    #  `weight`        INTEGER DEFAULT 0,
    #  `data_weight`   INTEGER DEFAULT 0,
    #  `machine_label` TEXT NOT NULL,
    #  `label`         TEXT NOT NULL,
    #  `value`         TEXT NOT NULL,
    #  `updated_srv`   INTEGER NOT NULL DEFAULT 0,
    #  `updated`       INTEGER NOT NULL,
    #  `created` INTEGER NOT NULL,
    #  PRIMARY KEY(id));"""
    # yield Registry.DBPOOL.runQuery(table)
    # yield Registry.DBPOOL.runQuery("CREATE  INDEX IF NOT EXISTS variables_foreign_id_variable_type_idx ON variables (variable_type, foreign_id)")

    ## Create views ##
    view = """CREATE VIEW devices_view AS
    SELECT devices.*, device_types.machine_label AS device_type_machine_label, categories.machine_label as category_machine_label
    FROM devices
    JOIN device_types ON devices.device_type_id = device_types.id
    JOIN categories ON device_types.category_id = categories.id
    """
    yield Registry.DBPOOL.runQuery(view)

    ## Create views ##
    view = """CREATE VIEW module_device_types_view AS
    SELECT device_types.*, module_device_types.module_id
    FROM module_device_types
    JOIN device_types ON module_device_types.device_type_id = device_types.id
    """
    yield Registry.DBPOOL.runQuery(view)

    view = """CREATE VIEW variable_field_data_view AS
    SELECT variable_data.id as data_id, variable_data.gateway_id, variable_data.field_id, variable_data.data_relation_id,
    variable_data.data_relation_type, variable_data.data, variable_data.data_weight,
    variable_data.updated as data_updated, variable_data.created as data_created, variable_fields.field_machine_label,
    variable_fields.field_label, variable_fields.field_description, variable_fields.field_weight,
    variable_fields.encryption, variable_fields.input_type_id, variable_fields. default_value, variable_fields.help_text,
    variable_fields.value_required, variable_fields.value_min, variable_fields.value_max,variable_fields.value_casing,
    variable_fields.multiple, variable_fields.created as field_created, variable_fields.updated as field_updated
    FROM variable_data
    JOIN variable_fields ON variable_data.field_id = variable_fields.id"""
    yield Registry.DBPOOL.runQuery(view)

    view = """CREATE VIEW variable_group_field_view AS
    SELECT  variable_fields.id as field_id, variable_fields.field_machine_label,variable_fields.field_label,
    variable_fields.field_description, variable_fields.field_weight,
    variable_fields.encryption, variable_fields.input_type_id, variable_fields. default_value, variable_fields.help_text,
    variable_fields.value_required, variable_fields.value_min, variable_fields.value_max,variable_fields.value_casing,
    variable_fields.multiple, variable_fields.created as field_created, variable_fields.updated as field_updated,
    variable_groups.id as group_id, variable_groups.group_machine_label,variable_groups.group_description,
    variable_groups.group_weight, variable_groups.status as group_status, variable_groups.group_relation_type,
    variable_groups.group_relation_id
    FROM variable_fields
    JOIN variable_groups ON variable_fields.group_id = variable_groups.id"""
    yield Registry.DBPOOL.runQuery(view)

    view = """CREATE VIEW variable_group_field_data_view AS
    SELECT variable_data.id as data_id, variable_data.gateway_id, variable_data.field_id, variable_data.data_relation_id,
    variable_data.data_relation_type, variable_data.data, variable_data.data_weight,
    variable_data.updated as data_updated, variable_data.created as data_created, variable_fields.field_machine_label,
    variable_fields.field_label, variable_fields.field_description, variable_fields.field_weight, variable_fields.encryption,
    variable_fields.input_type_id, variable_fields. default_value, variable_fields.help_text, variable_fields.value_required,
    variable_fields.value_min, variable_fields.value_max,variable_fields.value_casing, variable_fields.multiple,
    variable_fields.created as field_created, variable_fields.updated as field_updated, variable_groups.id as group_id,
    variable_groups.group_machine_label, variable_groups.group_relation_type, variable_groups.group_relation_id,
    variable_groups.group_description, variable_groups.group_weight, variable_groups.status as group_status
    FROM variable_data
    JOIN variable_fields ON variable_data.field_id = variable_fields.id
    JOIN variable_groups ON variable_fields.group_id = variable_groups.id"""
    yield Registry.DBPOOL.runQuery(view)


def downgrade(Registry, **kwargs):
    pass