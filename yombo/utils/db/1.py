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
    table = """CREATE TABLE `commands` (
     `id`     TEXT NOT NULL, /* commandUUID */
     `uri`     TEXT,
     `machine_label`     TEXT NOT NULL,
     `voice_cmd`     TEXT,
     `label`     TEXT NOT NULL,
     `description`     TEXT,
     `input_type_id`     TEXT,
     `live_update`     INTEGER,
     `public`     INTEGER NOT NULL,
     `status`     INTEGER NOT NULL,
     `created`     INTEGER NOT NULL,
     `updated`     INTEGER NOT NULL,
     PRIMARY KEY(id) );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('commands', 'machine_label'))
    yield Registry.DBPOOL.runQuery(create_index('commands', 'voice_cmd'))

    # All possible commands for a given device type. For examples, appliances are on and off.
    table = """CREATE TABLE `command_device_types` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `device_type_id`     TEXT NOT NULL,
     `command_id`     TEXT NOT NULL,
     UNIQUE (device_type_id, command_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('command_device_types', 'command_id'))
    yield Registry.DBPOOL.runQuery(create_index('command_device_types', 'device_type_id'))
#    yield Registry.DBPOOL.runQuery("CREATE INDEX IF NOT EXISTS command_device_types_command_id_device_type_id_IDX ON command_device_types (command_id, device_type_id)")

    # Defines the config table for the local gateway.
    table = """CREATE TABLE `configs` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `config_path`     TEXT NOT NULL,
     `config_key`     TEXT NOT NULL,
     `config_value`     TEXT NOT NULL,
     `updated`     INTEGER NOT NULL);"""
#    yield Registry.DBPOOL.runQuery(table)
#    yield Registry.DBPOOL.runQuery(create_index('configs', 'config_path'))
#    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS configs_config_key_config_key_IDX ON configs (config_path, config_key)")

    # Defines the devices table. Lists all possible devices for local gateway and related remote gateways.
    table = """CREATE TABLE `devices` (
     `id`     TEXT NOT NULL,
     `uri`     TEXT,
     `label`     TEXT NOT NULL,
     `notes`     TEXT,
     `description`     TEXT,
     `gateway_id`     TEXT NOT NULL,
     `device_type_id`     TEXT NOT NULL,
     `voice_cmd`     TEXT,
     `voice_cmd_order`     TEXT,
     `Voice_cmd_src`     TEXT,
     `pin_code`     INTEGER,
     `pin_required`     INTEGER NOT NULL,
     `pin_timeout`     INTEGER DEFAULT 0,
     `created`     INTEGER NOT NULL,
     `updated`     INTEGER NOT NULL,
     `status`     INTEGER NOT NULL,
/*     FOREIGN KEY(device_type_id) REFERENCES artist(device_types) */
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('devices', 'device_type_id'))
    yield Registry.DBPOOL.runQuery(create_index('devices', 'gateway_id'))

    #  Defines the device status table. Stores device status information.
    table = """CREATE TABLE `device_status` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `device_id`     TEXT NOT NULL, /* device_id */
     `set_time`     REAL NOT NULL,
     `device_state`     REAL, /* Used for graphs. */
     `human_status`     TEXT NOT NULL,
     `machine_status`     TEXT NOT NULL,
     `machine_status_extra`     TEXT,
     `source`     TEXT NOT NULL,
     `uploaded`     INTEGER NOT NULL DEFAULT 0,
     `uploadable`     INTEGER NOT NULL DEFAULT 0 /* For security, only items marked as 1 can be sent externally */
     );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'device_id'))
    yield Registry.DBPOOL.runQuery(create_index('device_status', 'uploaded'))

    # Device types defines the features of a device. For example, all X10 appliances or Insteon Lamps.
    table = """CREATE TABLE `device_types` (
     `id`     TEXT NOT NULL,
     `uri`     TEXT,
     `machine_label`     TEXT NOT NULL,
     `label`     TEXT NOT NULL,
     `device_class`     TEXT,
     `description`     TEXT,
     `live_update`     TEXT,
     `public`     INTEGER,
     `status`     INTEGER,
     `created`     INTEGER,
     `updated`     INTEGER,
      UNIQUE (label) ON CONFLICT IGNORE,
      UNIQUE (machine_label) ON CONFLICT IGNORE,
      PRIMARY KEY(id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
#    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_machine_label_idx ON device_types (machine_label) ON CONFLICT IGNORE")
#    yield Registry.DBPOOL.runQuery("CREATE UNIQUE INDEX IF NOT EXISTS device_types_label_idx ON device_types (label) ON CONFLICT IGNORE")
#    yield Registry.DBPOOL.runQuery(create_index('device_types', 'machine_label', unique=True))
#    yield Registry.DBPOOL.runQuery(create_index('device_types', 'label', unique=True))

    # Maps devices to a module using deviceTypes.
    table = """CREATE TABLE `device_type_modules` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `device_type_id`  TEXT NOT NULL, /* device_type_id */
     `module_id`     TEXT NOT NULL,
     `priority`     INTEGER NOT NULL DEFAULT 0,
     UNIQUE (device_type_id, module_id) ON CONFLICT IGNORE);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('device_type_modules', 'module_id'))
#    yield Registry.DBPOOL.runQuery("CREATE  INDEX IF NOT EXISTS device_type_modules_id_module_id_idx ON device_type_modules (device_type_id, module_id)")
    # TODO: Why doesn't unique work on the index????

    # Used for quick access to GPG keys instead of key ring.
    table = """CREATE TABLE `gpg_keys` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `endpoint`     TEXT NOT NULL,
     `fingerprint`     TEXT NOT NULL,
     `length`     INTEGER NOT NULL,
     `expires`     INTEGER NOT NULL,
     `created`     INTEGER NOT NULL
     );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('gpg_keys', 'endpoint'))
    yield Registry.DBPOOL.runQuery(create_index('gpg_keys', 'fingerprint'))

    # To be completed
    table = """CREATE TABLE `logs` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `created`     INTEGER NOT NULL,
     `log_line`     TEXT NOT NULL);"""

    # Stores module information
    table = """CREATE TABLE `modules` (
     `id`     TEXT NOT NULL, /* moduleUUID */
     `uri`     TEXT,
     `machine_label`     TEXT NOT NULL,
     `module_type`     TEXT NOT NULL,
     `label`     TEXT NOT NULL,
     `description`     TEXT,
     `instal_notes`     TEXT,
     `doc_link`     TEXT,
     `install_branch`     TEXT NOT NULL,
     `prod_version`     TEXT NOT NULL,
     `dev_version`     TEXT,
     `public`     INTEGER NOT NULL,
     `status`     INTEGER NOT NULL,
     `created`     INTEGER NOT NULL,
     `updated`     INTEGER NOT NULL,
     PRIMARY KEY(id));"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('modules', 'machine_label'))

    # Tracks what versions of a module is installed, when it was installed, and last checked for new version.
    table = """CREATE TABLE `module_installed` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `module_id`     TEXT NOT NULL, /* module.id */
     `installed_version`     TEXT NOT NULL,
     `install_time`     INTEGER NOT NULL,
     `last_check`     INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('module_installed', 'module_id'))

    ## Create view for modules ##
    view = """CREATE VIEW modules_view AS
    SELECT modules.*, module_installed.installed_version, module_installed. install_time, module_installed.last_check
    FROM modules LEFT OUTER JOIN module_installed ON modules.id = module_installed.module_id"""
    yield Registry.DBPOOL.runQuery(view)

    # Defines the SQL Dict table. Used by the :class:`SQLDict` class to maintain persistent dictionaries.
    table = """CREATE TABLE `sqldict` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `component` TEXT NOT NULL,
     `dict_name`    INTEGER NOT NULL,
     `dict_data`    BLOB,
     `created`     INTEGER NOT NULL,
     `updated`     INTEGER NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('sqldict', 'dict_name'))
    yield Registry.DBPOOL.runQuery(create_index('sqldict', 'component'))

    # To be completed
    table = """CREATE TABLE `users` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `username`     TEXT NOT NULL,
     `hash`     TEXT NOT NULL);"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery(create_index('users', 'username'))

    ## Create views ##
    view = """CREATE VIEW devices_view AS
    SELECT devices.*, device_types.machine_label AS device_type_machine_label, device_types.device_class as device_class
    FROM devices JOIN device_types ON devices.device_type_id = device_types.id"""
    yield Registry.DBPOOL.runQuery(view)

    # Stores variables for modules and devices. Variables are set by the server, and read here. Not a two-way sync (yet?).
    table = """CREATE TABLE `variables` (
     `id`     INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
     `variable_type`     TEXT NOT NULL,
     `foreign_id`     TEXT NOT NULL,
     `variable_id`     TEXT NOT NULL,
     `weight`     INTEGER DEFAULT 0,
     `data_weight`     INTEGER DEFAULT 0,
     `machine_label`     TEXT NOT NULL,
     `label`     TEXT NOT NULL,
     `value`     TEXT NOT NULL,
     `updated`     INTEGER NOT NULL,
     `created`     INTEGER NOT NULL );"""
    yield Registry.DBPOOL.runQuery(table)
    yield Registry.DBPOOL.runQuery("CREATE  INDEX IF NOT EXISTS variables_foreign_id_variable_type_idx ON variables (variable_type, foreign_id)")


    view = """CREATE VIEW module_routing_view AS
    SELECT dtm.device_type_id, MAX(priority) AS priority, dt.machine_label AS device_type_label,
    dtm.module_id, modules.machine_label as module_machine_label, modules.module_type
    FROM device_type_modules AS dtm
    JOIN device_types AS dt ON dtm.device_type_id = dt.id
    JOIN modules ON dtm.module_id = modules.id
    WHERE modules.module_type IN (SELECT distinct(modules.module_type) FROM device_type_modules)
    GROUP BY dtm.device_type_id, modules.module_type"""
    yield Registry.DBPOOL.runQuery(view)

def downgrade(Registry, **kwargs):
    pass