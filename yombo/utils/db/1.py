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
def new_db_file(Registry, **kwargs):
    yield create_table_schema_version(Registry)
    yield create_table_categories(Registry)
    yield create_table_commands(Registry)
    yield create_table_devices(Registry)
    yield create_table_device_commands(Registry)
    yield create_table_device_command_inputs(Registry)
    yield create_table_device_status(Registry)
    yield create_table_device_types(Registry)
    yield create_table_device_type_commands(Registry)
    yield create_table_gateways(Registry)
    yield create_table_gpg_keys(Registry)
    yield create_table_input_types(Registry)
    yield create_table_locations(Registry)
    # yield create_table_logs(Registry)
    # yield create_table_meta(Registry)
    yield create_table_modules(Registry)
    yield create_table_module_device_types(Registry)
    yield create_table_module_installed(Registry)
    yield create_table_nodes(Registry)
    yield create_table_notifications(Registry)
    yield create_table_permissions(Registry)
    yield create_table_sqldict(Registry)
    yield create_table_states(Registry)
    yield create_table_statistics(Registry)
    yield create_table_tasks(Registry)
    yield create_table_users(Registry)
    yield create_table_user_permission(Registry)
    yield create_table_webinterface_sessions(Registry)
    yield create_table_webinterface_logs(Registry)
    yield create_table_variable_groups(Registry)
    yield create_table_variable_fields(Registry)
    yield create_table_variable_data(Registry)
    yield create_view_devices_view(Registry)
    yield create_view_modules_view(Registry)
    yield create_view_module_device_types_view(Registry)
    yield create_view_variable_field_data_view(Registry)
    yield create_view_variable_group_field_view(Registry)
    yield create_view_variable_group_field_data_view(Registry)
    yield create_view_addable_device_types_view(Registry)
    yield create_trigger_delete_device_variable_data(Registry)
    yield create_trigger_delete_module_variable_data(Registry)
    yield create_trigger_delete_variablegroups_variable_fields(Registry)
    yield create_trigger_delete_variablefields_variable_data(Registry)

@inlineCallbacks
def upgrade(Registry, **kwargs):
    yield new_db_file(Registry)

def downgrade(Registry, **kwargs):
    pass

@inlineCallbacks
def create_table_schema_version(Registry, **kwargs):
    """ Handles version tracking for the database schema """
    yield Registry.DBPOOL.runQuery('CREATE TABLE schema_version(table_name TEXT NOT NULL, version INTEGER NOT NULL, PRIMARY KEY(table_name))')
    yield Registry.DBPOOL.runQuery('INSERT INTO schema_version(table_name, version) VALUES ("core", 1)')

@inlineCallbacks
def create_table_categories(Registry, **kwargs):
    """ System categories """
    table = """CREATE TABLE `categories` (
        `id`            TEXT NOT NULL, /* commandUUID */
        `parent_id` TEXT NOT NULL,
        `category_type` TEXT NOT NULL,
        `machine_label` TEXT NOT NULL,
        `label`         TEXT NOT NULL,
        `description`   TEXT,
        `status`        INTEGER NOT NULL,
        `created_at`    INTEGER NOT NULL,
        `updated_at`    INTEGER NOT NULL,
        PRIMARY KEY(id) );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('categories', 'id', unique=True))
    # yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS categoires_type_machine_label_IDX ON categories (machine_label, category_type)")

@inlineCallbacks
def create_table_commands(Registry, **kwargs):
    """ Defines the commands table. Lists all possible commands a local or remote gateway can perform. """
    table = """CREATE TABLE `commands` (
        `id`            TEXT NOT NULL, /* commandUUID */
        `machine_label` TEXT NOT NULL,
        `voice_cmd`     TEXT,
        `label`         TEXT NOT NULL,
        `description`   TEXT,
        `always_load`   INTEGER DEFAULT 0,
        `public`        INTEGER NOT NULL,
        `status`        INTEGER NOT NULL,
        `created_at`    INTEGER NOT NULL,
        `updated_at`    INTEGER NOT NULL,
        PRIMARY KEY(id) );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('commands', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('commands', 'machine_label', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('commands', 'voice_cmd'))

@inlineCallbacks
def create_table_devices(Registry, **kwargs):
    """ Defines the devices table. Lists all possible devices for local gateway and related remote gateways. """
    table = """CREATE TABLE `devices` (
        `id`              TEXT NOT NULL,
        `gateway_id`      TEXT NOT NULL,
        `device_type_id`  TEXT NOT NULL,
        `location_id`     TEXT NOT NULL,
        `area_id`         TEXT NOT NULL,
        `machine_label`   TEXT NOT NULL,
        `label`           TEXT NOT NULL,
        `description`     TEXT,
        `statistic_label` TEXT,
        `statistic_lifetime` INTEGER DEFAULT 0,
        `notes`           TEXT,
        `attributes`      TEXT,
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
        `created_at`      INTEGER NOT NULL,
        `updated_at`      INTEGER NOT NULL,
/*     FOREIGN KEY(device_type_id) REFERENCES artist(device_types) */
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('devices', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('devices', 'device_type_id'))
    yield Registry.DBPOOL.runQuery(create_index('devices', 'gateway_id'))

@inlineCallbacks
def create_table_device_command_inputs(Registry, **kwargs):
    """ All possible inputs for a given device type/command/input. """
    table = """CREATE TABLE `device_command_inputs` (
        `id`             TEXT NOT NULL,
        `device_type_id` TEXT NOT NULL,
        `command_id`     TEXT NOT NULL,
        `input_type_id`  TEXT NOT NULL,
        `label`          TEXT NOT NULL,
        `machine_label`  TEXT NOT NULL,
        `live_update`    INTEGER NOT NULL,
        `value_required` INTEGER NOT NULL,
        `value_max`      INTEGER NOT NULL,
        `value_min`      INTEGER NOT NULL,
        `value_casing`   TEXT NOT NULL,
        `encryption`     TEXT NOT NULL,
        `notes`          TEXT,
        `always_load`    INTEGER DEFAULT 0,
        `updated_at`     INTEGER NOT NULL,
        `created_at`     INTEGER NOT NULL,
        UNIQUE (device_type_id, command_id, input_type_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_command_inputs', 'device_type_id'))

@inlineCallbacks
def create_table_device_commands(Registry, **kwargs):
    """ Defines the device command table to store command history and various info. """
    table = """CREATE TABLE `device_commands` (
        `id`                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `request_id`        TEXT NOT NULL,
        `source_gateway_id` TEXT NOT NULL,
        `device_id`         TEXT NOT NULL,
        `command_id`        TEXT NOT NULL,
        `inputs`            TEXT,
        `created_at`   FLOAT NOT NULL,
        `broadcast_at`    FLOAT,
        `sent_at`         FLOAT,
        `received_at`     FLOAT,
        `pending_at`      FLOAT,
        `finished_at`     FLOAT,
        `not_before_at`   FLOAT,
        `not_after_at`    FLOAT,
        `command_status_received` INT NOT NULL DEFAULT 0,
        `history`           TEXT NOT NULL,
        `status`            TEXT NOT NULL,
        `requested_by`      TEXT,
        `uploaded`          INTEGER NOT NULL DEFAULT 0,
        `uploadable`        INTEGER NOT NULL DEFAULT 0 /* For security, only items marked as 1 can be sent externally */
        );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_commands', 'request_id', unique=True))
    # yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS device_command_id_nottimes_idx ON device_command (device_id, not_before_at, not_after_at)")
    # yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS device_command_id_nottimes_idx ON device_command (device_id, not_before_at, not_after_at)")
    yield Registry.DBPOOL.runQuery(create_index('device_commands', 'finished_at'))
    # yield Registry.DBPOOL.runQuery(create_index('device_status', 'status'))

@inlineCallbacks
def create_table_device_status(Registry, **kwargs):
    """ Defines the device status table. Stores device status information. """
    table = """CREATE TABLE `device_status` (
        `id`                   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `device_id`            TEXT NOT NULL, /* device_id */
        `set_at`             REAL NOT NULL,
        `energy_usage`         INTEGER NOT NULL,
        `energy_type`          TEXT,
        `human_status`         TEXT NOT NULL,
        `human_message`        TEXT NOT NULL,
        `last_command`         TEXT,
        `machine_status`       TEXT NOT NULL,
        `machine_status_extra` TEXT,
        `requested_by`         TEXT NOT NULL,
        `reported_by`          TEXT NOT NULL,
        'request_id'           TEXT,
        `uploaded`             INTEGER NOT NULL DEFAULT 0,
        `uploadable`           INTEGER NOT NULL DEFAULT 0 /* For security, only items marked as 1 can be sent externally */
        );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'device_id'))
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'uploaded'))

@inlineCallbacks
def create_table_device_types(Registry, **kwargs):
    """ Device types defines the features of a device. For example, all X10 appliances or Insteon Lamps. """
    table = """CREATE TABLE `device_types` (
        `id`            TEXT NOT NULL,
        `machine_label` TEXT NOT NULL,
        `label`         TEXT NOT NULL,
        `description`   TEXT,
        `category_id`   TEXT,
        `platform`      TEXT,
        `public`        INTEGER,
        `status`        INTEGER,
        `always_load`   INTEGER DEFAULT 0,
        `created_at`    INTEGER,
        `updated_at`    INTEGER,
        UNIQUE (label) ON CONFLICT IGNORE,
        UNIQUE (machine_label) ON CONFLICT IGNORE,
        PRIMARY KEY(id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
#    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_machine_label_idx ON device_types (machine_label) ON CONFLICT IGNORE")
#    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_label_idx ON device_types (label) ON CONFLICT IGNORE")
    yield Registry.DBPOOL.runQuery(create_index('device_types', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('device_types', 'machine_label', unique=True))

@inlineCallbacks
def create_table_device_type_commands(Registry, **kwargs):
    """ All possible commands for a given device type. For examples, appliances are on and off. """
    table = """CREATE TABLE `device_type_commands` (
        `id`             TEXT NOT NULL,
        `device_type_id` TEXT NOT NULL,
        `command_id`     TEXT NOT NULL,
        `created_at`     INTEGER NOT NULL,
        UNIQUE (device_type_id, command_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_type_commands', 'device_type_id'))
    # yield Registry.DBPOOL.runQuery(create_index('command_device_types', 'command_id'))
    #    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS command_device_types_command_id_device_type_id_IDX ON command_device_types (command_id, device_type_id)")

@inlineCallbacks
def create_table_gateways(Registry, **kwargs):
    """ All gateways in the current cluster.  """
    table = """CREATE TABLE `gateways` (
            `id`                   TEXT NOT NULL,
            `is_master`            BOOLEAN,
            `master_gateway`       TEXT,
            `machine_label`        TEXT NOT NULL,
            `label`                TEXT NOT NULL,
            `description`          TEXT,
            `mqtt_auth`            TEXT,
            `mqtt_auth_prev`       TEXT,
            `mqtt_auth_next`       TEXT,
            `mqtt_auth_last_rotate` TEXT,
            `internal_ipv4`        TEXT,
            `external_ipv4`        TEXT,
            `internal_ipv6`        TEXT,
            `external_ipv6`        TEXT,
            `internal_port`        INTEGER,
            `external_port`        INTEGER,
            `internal_secure_port` INTEGER,
            `external_secure_port` INTEGER,
            `internal_mqtt`        INTEGER,
            `internal_mqtt_le`     INTEGER,
            `internal_mqtt_ss`     INTEGER,
            `internal_mqtt_ws`     INTEGER,
            `internal_mqtt_ws_le`  INTEGER,
            `internal_mqtt_ws_ss`  INTEGER,
            `external_mqtt`        INTEGER,
            `external_mqtt_le`     INTEGER,
            `external_mqtt_ss`     INTEGER,
            `external_mqtt_ws`     INTEGER,
            `external_mqtt_ws_le`  INTEGER,
            `external_mqtt_ws_ss`  INTEGER,
            `status`               INTEGER NOT NULL,
            `created_at`           INTEGER NOT NULL,
            `updated_at`           INTEGER NOT NULL,
         PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('gateways', 'id', unique=True))

@inlineCallbacks
def create_table_gpg_keys(Registry, **kwargs):
    """ Used for quick access to GPG keys instead of key ring. """
    table = """CREATE TABLE `gpg_keys` (
        `id`          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `notes`       TEXT,
        `endpoint`    TEXT NOT NULL,
        `keyid`       TEXT NOT NULL,
        `fingerprint` TEXT NOT NULL,
        `length`      INTEGER NOT NULL,
        `expires`     INTEGER NOT NULL,
        `publickey`   TEXT NOT NULL,
        `have_private` INTEGER NOT NULL,
        `created_at`   INTEGER NOT NULL
        );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('gpg_keys', 'endpoint'))
    yield Registry.DBPOOL.runQuery(create_index('gpg_keys', 'fingerprint'))

@inlineCallbacks
def create_table_input_types(Registry, **kwargs):
    """ Input types defines input filters and how input validation is handled. """
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
        `created_at`    INTEGER,
        `updated_at`    INTEGER,
        UNIQUE (label) ON CONFLICT IGNORE,
        UNIQUE (machine_label) ON CONFLICT IGNORE,
        PRIMARY KEY(id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)

@inlineCallbacks
def create_table_locations(Registry, **kwargs):
    """ All locations configured for an account. """
    table = """CREATE TABLE `locations` (
        `id`             TEXT NOT NULL,
        `location_type`  TEXT NOT NULL,
        `machine_label`  TEXT NOT NULL,
        `label`          TEXT NOT NULL,
        `description`    TEXT,
        `updated_at`     INTEGER NOT NULL,
        `created_at`     INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('locations', 'id'))
    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS locations_machinelabel_idx ON locations (location_type, machine_label)")
    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS locations_label_idx ON locations (location_type, label)")

# @inlineCallbacks
# def create_table_logs(Registry, **kwargs):
#     """  """
#     # To be completed
#     table = """CREATE TABLE `logs` (
#         `id`           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#         `type`         TEXT NOT NULL, /* system, user, etc */
#         `priority`     TEXT NOT NULL, /* debug, low, normal, high, urgent */
#         `source`       TEXT NOT NULL, /* where this message was created_at */
#         `message`      TEXT, /* Message data */
#         `meta`         TEXT, /* Any extra meta data. JSON format */
#         `created_at`   INTEGER NOT NULL);"""
#     yield Registry.DBPOOL.runQuery(table)

# @inlineCallbacks
# def create_table_meta(Registry, **kwargs):
#     """  """
#     # Defines the config table for the local gateway.
#     table = """CREATE TABLE `meta` (
#         `id`           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#         `meta_key`  TEXT NOT NULL,
#         `meta_value`   TEXT NOT NULL,
#         `created_at`    INTEGER NOT NULL,
#         `updated_at`   INTEGER NOT NULL);"""
#     #    yield Registry.DBPOOL.runQuery(table)
#     #    yield Registry.DBPOOL.runQuery(create_index('meta', 'meta_key'))
#     #    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS configs_config_key_config_key_IDX ON configs (config_path, config_key)")

@inlineCallbacks
def create_table_modules(Registry, **kwargs):
    """  """
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
        `created_at`     INTEGER NOT NULL,
        `updated_at`     INTEGER NOT NULL,
        PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('modules', 'machine_label'))

@inlineCallbacks
def create_table_module_device_types(Registry, **kwargs):
    """  """
    # All possible device types for a module
    table = """CREATE TABLE `module_device_types` (
        `id`             TEXT NOT NULL,
        `module_id`      TEXT NOT NULL,
        `device_type_id` TEXT NOT NULL,
        `created_at`     INTEGER NOT NULL,
        UNIQUE (module_id, device_type_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS module_device_types_module_dt_id_idx ON module_device_types (module_id, device_type_id)")
    # yield Registry.DBPOOL.runQuery(create_index('command_device_types', 'command_id'))
    #    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS command_device_types_command_id_device_type_id_IDX ON command_device_types (command_id, device_type_id)")

@inlineCallbacks
def create_table_module_installed(Registry, **kwargs):
    """  """
    # Tracks what versions of a module is installed, when it was installed, and last checked for new version.
    table = """CREATE TABLE `module_installed` (
        `id`                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `module_id`         TEXT NOT NULL, /* module.id */
        `installed_version` TEXT NOT NULL,
        `install_at`      INTEGER NOT NULL,
        `last_check`        INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('module_installed', 'module_id'))

@inlineCallbacks
def create_table_nodes(Registry, **kwargs):
    """  """
    #  Defines the statistics data table. Stores node items.
    table = """CREATE TABLE `nodes` (
        `id`             TEXT NOT NULL,
        `parent_id`      TEXT,
        `gateway_id`     TEXT NOT NULL,
        `node_type`      TEXT NOT NULL,
        `weight`         INTEGER NOT NULL,
        `label`          TEXT,
        `machine_label`  TEXT,
        `always_load`    INTEGER NOT NULL,
        `destination`    TEXT NOT NULL,
        `data`           BLOB,
        `data_content_type` TEXT NOT NULL,
        `status`         INTEGER NOT NULL, /* Timestemp when msg was ack'd by the user. */
        `updated_at`     INTEGER NOT NULL,
        `created_at`     INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('nodes', 'id'))
    yield Registry.DBPOOL.runQuery(create_index('nodes', 'parent_id'))

@inlineCallbacks
def create_table_notifications(Registry, **kwargs):
    """  """
    #  Defines the statistics data table. Stores statistics.
    table = """CREATE TABLE `notifications` (
        `id`           TEXT NOT NULL,
        `gateway_id`   TEXT NOT NULL,
        `type`         TEXT NOT NULL, /* system, user, etc */
        `priority`     TEXT NOT NULL, /* debug, low, normal, high, urgent */
        `source`       TEXT NOT NULL, /* where this message was created_at */
        `expire`       INTEGER, /* timestamp when msg should expire */
        `always_show`  INTEGER NOT NULL, /* If notification should always show until user clears it. */
        `always_show_allow_clear` INTEGER NOT NULL, /* User allowed to clear notification form always_show. */
        `acknowledged`            INTEGER NOT NULL, /* Timestemp when msg was ack'd by the user. */
        `acknowledged_at`       INTEGER, /* Timestemp when msg was ack'd by the user. */
        `user`         TEXT, /* Message data */
        `title`        TEXT, /* Message data */
        `message`      TEXT, /* Message data */
        `meta`         TEXT, /* Any extra meta data. JSON format */
        `created_at`   INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('notifications', 'id'))

@inlineCallbacks
def create_table_sqldict(Registry, **kwargs):
    """  """
    # Defines the SQL Dict table. Used by the :class:`SQLDict` class to maintain persistent dictionaries.
    table = """CREATE TABLE `sqldict` (
        `id`         INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `component`  TEXT NOT NULL,
        `dict_name`  INTEGER NOT NULL,
        `dict_data`  BLOB,
        `created_at` INTEGER NOT NULL,
        `updated_at` INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('sqldict', 'dict_name'))
    yield Registry.DBPOOL.runQuery(create_index('sqldict', 'component'))

@inlineCallbacks
def create_table_states(Registry, **kwargs):
    """  """
    # Defines the tables used to store state information.
    table = """CREATE TABLE `states` (
        `id`          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `gateway_id` TEXT NOT NULL,
        `name`        TEXT NOT NULL,
        `value_type`  TEXT,
        `value`       INTEGER NOT NULL,
        `live`        INTEGER NOT NULL,
        `created_at`  INTEGER NOT NULL,
        `updated_at`  INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS name_gateway_id_IDX ON states (name, gateway_id)")
    yield Registry.DBPOOL.runQuery(create_index('states', 'created_at'))

@inlineCallbacks
def create_table_statistics(Registry, **kwargs):
    """  """
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
        `updated_at`          INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('statistics', 'bucket_type'))
    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS table_b_t_IDX ON statistics (bucket_name, bucket_type, bucket_time)")
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS table_t_n_t_IDX ON statistics (finished, uploaded, anon)")

@inlineCallbacks
def create_table_tasks(Registry, **kwargs):
    """  """
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
        `created_at`     INTEGER NOT NULL
        );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('tasks', 'id'))

@inlineCallbacks
def create_table_users(Registry, **kwargs):
    """  """
    table = """CREATE TABLE `users` (
        `id`         TEXT NOT NULL,
        `gateway_id` TEXT NOT NULL,
        `user_id`    TEXT NOT NULL,
        `email`      TEXT NOT NULL,
        `updated_at` INTEGER NOT NULL,
        `created_at` INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('users', 'id', unique=True))
    yield Registry.DBPOOL.runQuery(create_index('users', 'email'))

@inlineCallbacks
def create_table_user_permission(Registry, **kwargs):
    """  """
    table = """CREATE TABLE `user_permission` (
        `id`            TEXT NOT NULL,
        `user_id`       TEXT NOT NULL,
        `gateway_id`    TEXT NOT NULL,
        `permission_id` TEXT NOT NULL,
        `updated_at`    INTEGER NOT NULL,
        `created_at`    INTEGER NOT NULL,
    CONSTRAINT fk_user_permission
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('user_permission', 'id', unique=True))

@inlineCallbacks
def create_table_permissions(Registry, **kwargs):
    """  """
    table = """CREATE TABLE `permissions` (
        `id`         TEXT NOT NULL,
        `gateway_id` TEXT NOT NULL,
        `updated_at` INTEGER NOT NULL,
        `created_at` INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('permissions', 'id', unique=True))

@inlineCallbacks
def create_table_webinterface_sessions(Registry, **kwargs):
    """  """
    # Defines the web interface session store. Used by the :class:`WebInterface` class to maintain session information
    table = """CREATE TABLE `webinterface_sessions` (
        `id`           TEXT NOT NULL, /* moduleUUID */
        `is_valid`     INTEGER NOT NULL,
        `gateway_id`   TEXT NOT NULL,
        `session_data` TEXT NOT NULL,
        `created_at`   INTEGER NOT NULL,
        `last_access`  INTEGER NOT NULL,
        `updated_at`   INTEGER NOT NULL,
        PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('webinterface_sessions', 'created_at'))
    yield Registry.DBPOOL.runQuery(create_index('webinterface_sessions', 'updated_at'))

@inlineCallbacks
def create_table_webinterface_logs(Registry, **kwargs):
    """  """
    # Used by the tasks library to start various tasks.
    table = """CREATE TABLE `webinterface_logs` (
        `id`             INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `request_at`      INTEGER,
        `request_protocol`  TEXT NOT NULL,
        `referrer`          TEXT NOT NULL,
        `agent`             TEXT NOT NULL,
        `ip`                INTEGER NOT NULL,
        `hostname`          TEXT NOT NULL,
        `method`            TEXT NOT NULL,
        `path`              TEXT NOT NULL,
        `secure`            BOOL NOT NULL,
        `response_code`     INTEGER NOT NULL,
        `response_size`     INTEGER NOT NULL,
        `uploadable`        INTEGER DEFAULT 1,
        `uploaded`          INTEGER DEFAULT 0
        );"""
    yield Registry.DBPOOL.runQuery(table)

@inlineCallbacks
def create_table_variable_groups(Registry, **kwargs):
    """  """
    # The following three tables and following views manages the variables set for devices and modules.
    table = """CREATE TABLE `variable_groups` (
        `id`                  TEXT NOT NULL, /* group_id */
        `group_relation_id`   TEXT NOT NULL,
        `group_relation_type` TEXT NOT NULL,
        `group_machine_label` TEXT NOT NULL,
        `group_label`         TEXT NOT NULL,
        `group_description`   TEXT NOT NULL,
        `group_weight`        INTEGER DEFAULT 0,
        `status`              INTEGER NOT NULL, /* disabled, enabled, deleted */
        `updated_at`          INTEGER NOT NULL,
        `created_at`          INTEGER NOT NULL,
        PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS variable_groups_relation_id_type_idx ON variable_groups (group_relation_id, group_relation_type, group_machine_label)")

@inlineCallbacks
def create_table_variable_fields(Registry, **kwargs):
    """  """
    table = """CREATE TABLE `variable_fields` (
        `id`                  TEXT NOT NULL, /* field_id */
        `group_id`            TEXT NOT NULL,
        `field_machine_label` TEXT NOT NULL,
        `field_label`         TEXT NOT NULL,
        `field_description`   TEXT NOT NULL,
        `field_help_text`     TEXT NOT NULL,
        `field_weight`        INTEGER DEFAULT 0,
        `value_required`      INTEGER NOT NULL,
        `value_max`           INTEGER,
        `value_min`           INTEGER,
        `value_casing`        TEXT NOT NULL,
        `encryption`          TEXT NOT NULL,
        `input_type_id`       TEXT NOT NULL,
        `default_value`       TEXT NOT NULL,
        `multiple`            INTEGER NOT NULL,
        `updated_at`          INTEGER NOT NULL,
        `created_at`          INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('variable_fields', 'group_id'))
    #    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_machine_label_idx ON device_types (machine_label) ON CONFLICT IGNORE")

@inlineCallbacks
def create_table_variable_data(Registry, **kwargs):
    """  """
    table = """CREATE TABLE `variable_data` (
        `id`            TEXT NOT NULL,  /* field_id */
        `gateway_id`    TEXT DEFAULT 0,
        `field_id`      TEXT NOT NULL,
        `data_relation_id`   TEXT NOT NULL,
        `data_relation_type` TEXT NOT NULL,
        `data`          TEXT NOT NULL,
        `data_weight`   INTEGER DEFAULT 0,
        `updated_at`    INTEGER NOT NULL,
        `created_at`    INTEGER NOT NULL,
        PRIMARY KEY(id))
        ;"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS variable_data_id_type_idx ON variable_data (field_id, data_relation_id, data_relation_type)")

# @inlineCallbacks
# def create_trigger_delete_device_status(Registry, **kwargs):
#     """  """
    ## Create triggers ##
    # trigger = """CREATE TRIGGER delete_device_status
    # AFTER DELETE ON devices
    # FOR EACH ROW
    # BEGIN
    #     DELETE FROM device_status WHERE device_id = OLD.id;
    # END"""
    # yield Registry.DBPOOL.runQuery(trigger)

@inlineCallbacks
def create_trigger_delete_device_variable_data(Registry, **kwargs):
    """  """
    trigger = """CREATE TRIGGER delete_device_variable_data
    AFTER DELETE ON devices
    FOR EACH ROW
    BEGIN
        DELETE FROM variable_data WHERE data_relation_id = OLD.id and data_relation_type = "device";
    END"""
    yield Registry.DBPOOL.runQuery(trigger)

# @inlineCallbacks
# def create_trigger_delete_module_module_installed(Registry, **kwargs):
#     """  """
    # trigger = """CREATE TRIGGER delete_module_module_installed
    # AFTER DELETE ON modules
    # FOR EACH ROW
    # BEGIN
    #     DELETE FROM module_installed WHERE module_id = OLD.id;
    # END"""
    # yield Registry.DBPOOL.runQuery(trigger)

@inlineCallbacks
def create_trigger_delete_module_variable_data(Registry, **kwargs):
    """  """
    trigger = """CREATE TRIGGER delete_module_variable_data
    AFTER DELETE ON modules
    FOR EACH ROW
    BEGIN
        DELETE FROM module_device_types WHERE module_id = OLD.id;
        /* DELETE FROM module_installed WHERE module_id = OLD.id; */
        DELETE FROM variable_data WHERE data_relation_id = OLD.id and data_relation_type = "module";
    END"""
    yield Registry.DBPOOL.runQuery(trigger)

@inlineCallbacks
def create_trigger_delete_variablegroups_variable_fields(Registry, **kwargs):
    """  """
    trigger = """CREATE TRIGGER delete_variablegroups_variable_fields
    AFTER DELETE ON variable_groups
    FOR EACH ROW
    BEGIN
        DELETE FROM variable_fields WHERE group_id = OLD.id;
    END"""
    yield Registry.DBPOOL.runQuery(trigger)

@inlineCallbacks
def create_trigger_delete_variablefields_variable_data(Registry, **kwargs):
    """  """
    trigger = """CREATE TRIGGER delete_variablefields_variable_data
    AFTER DELETE ON variable_fields
    FOR EACH ROW
    BEGIN
        DELETE FROM variable_data WHERE field_id = OLD.id;
    END"""
    yield Registry.DBPOOL.runQuery(trigger)


##################
## Create views ##
##################


@inlineCallbacks
def create_view_devices_view(Registry, **kwargs):
    """  """
    view = """CREATE VIEW devices_view AS
    SELECT devices.*, device_types.machine_label AS device_type_machine_label, categories.machine_label as category_machine_label
    FROM devices
    JOIN device_types ON devices.device_type_id = device_types.id
    JOIN categories ON device_types.category_id = categories.id
    """
    yield Registry.DBPOOL.runQuery(view)

@inlineCallbacks
def create_view_modules_view(Registry, **kwargs):
    """  """
    ## Create view for modules ##
    view = """CREATE VIEW modules_view AS
    SELECT modules.*, module_installed.installed_version, module_installed. install_at, module_installed.last_check
    FROM modules LEFT OUTER JOIN module_installed ON modules.id = module_installed.module_id"""
    yield Registry.DBPOOL.runQuery(view)

@inlineCallbacks
def create_view_module_device_types_view(Registry, **kwargs):
    """  """
    view = """CREATE VIEW module_device_types_view AS
    SELECT device_types.*, module_device_types.module_id
    FROM module_device_types
    JOIN device_types ON module_device_types.device_type_id = device_types.id
    """
    yield Registry.DBPOOL.runQuery(view)

@inlineCallbacks
def create_view_variable_field_data_view(Registry, **kwargs):
    """  """
    view = """CREATE VIEW variable_field_data_view AS
    SELECT variable_data.id as data_id, variable_data.gateway_id, variable_data.field_id,
    variable_data.data_relation_id, variable_data.data_relation_type, variable_data.data, variable_data.data_weight,
    variable_data.updated_at as data_updated_at, variable_data.created_at as data_created_at, variable_fields.field_machine_label,
    variable_fields.field_label, variable_fields.field_description, variable_fields.field_weight,
    variable_fields.encryption, variable_fields.input_type_id, variable_fields. default_value,
    variable_fields.field_help_text, variable_fields.value_required, variable_fields.value_min,
    variable_fields.value_max,variable_fields.value_casing, variable_fields.multiple,
    variable_fields.created_at as field_created_at, variable_fields.updated_at as field_updated_at,
    variable_groups.group_label, variable_groups.group_machine_label, variable_groups.id as group_id,
    variable_groups.group_relation_type, variable_groups.group_relation_id,
    variable_groups.group_description, variable_groups.group_weight, variable_groups.status as group_status
    FROM variable_fields
    LEFT OUTER JOIN variable_data ON variable_data.field_id = variable_fields.id
    JOIN variable_groups ON variable_fields.group_id = variable_groups.id"""
    yield Registry.DBPOOL.runQuery(view)

@inlineCallbacks
def create_view_variable_group_field_view(Registry, **kwargs):
    """  """
    view = """CREATE VIEW variable_group_field_view AS
    SELECT  variable_fields.id as field_id, variable_fields.field_machine_label,variable_fields.field_label,
    variable_fields.field_description, variable_fields.field_weight,
    variable_fields.encryption, variable_fields.input_type_id, variable_fields. default_value, variable_fields.field_help_text,
    variable_fields.value_required, variable_fields.value_min, variable_fields.value_max,variable_fields.value_casing,
    variable_fields.multiple, variable_fields.created_at as field_created_at, variable_fields.updated_at as field_updated_at,
    variable_groups.id as group_id, variable_groups.group_label, variable_groups.group_machine_label,variable_groups.group_description,
    variable_groups.group_weight, variable_groups.status as group_status, variable_groups.group_relation_type,
    variable_groups.group_relation_id
    FROM variable_groups
    JOIN variable_fields ON variable_fields.group_id = variable_groups.id"""
    yield Registry.DBPOOL.runQuery(view)

@inlineCallbacks
def create_view_variable_group_field_data_view(Registry, **kwargs):
    """  """
    view = """CREATE VIEW variable_group_field_data_view AS
    SELECT variable_data.id as data_id, variable_data.gateway_id, variable_data.field_id, variable_data.data_relation_id,
    variable_data.data_relation_type, variable_data.data, variable_data.data_weight,
    variable_data.updated_at as data_updated_at, variable_data.created_at as data_created_at,
    variable_fields.field_machine_label, variable_fields.field_label, variable_fields.field_description,
    variable_fields.field_weight, variable_fields.encryption, variable_fields.input_type_id,
    variable_fields. default_value, variable_fields.field_help_text, variable_fields.value_required,
    variable_fields.value_min, variable_fields.value_max,variable_fields.value_casing, variable_fields.multiple,
    variable_fields.created_at as field_created_at, variable_fields.updated_at as field_updated_at,
    variable_groups.id as group_id, variable_groups.group_label, variable_groups.group_machine_label,
    variable_groups.group_relation_type, variable_groups.group_relation_id,
    variable_groups.group_description, variable_groups.group_weight, variable_groups.status as group_status
    FROM variable_fields
    LEFT OUTER JOIN variable_data ON variable_data.field_id = variable_fields.id
    JOIN variable_groups ON variable_fields.group_id = variable_groups.id"""
    yield Registry.DBPOOL.runQuery(view)

@inlineCallbacks
def create_view_addable_device_types_view(Registry, **kwargs):
    """  """
    view = """CREATE VIEW addable_device_types_view AS
    SELECT DISTINCT device_types.*
    FROM module_device_types
    JOIN device_types ON module_device_types.device_type_id = device_types.id
    ORDER BY device_types.label"""
    yield Registry.DBPOOL.runQuery(view)
