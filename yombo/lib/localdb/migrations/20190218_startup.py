# Setup the Yombo database.

from yoyo import group, step

from yombo.lib.localdb.migrations import create_index

print("Creating new database file. This will take a bit of time on Raspberry Pi like devices.")
steps = [
   group([
      # Nearly the same as webinterface_sessions, but for auth keys
      step("""CREATE TABLE `auth_keys` (
        `id`              TEXT NOT NULL,
        `label`           TEXT NOT NULL,
        `description`     TEXT NOT NULL,
        `enabled`         INTEGER NOT NULL,
        `roles`           TEXT,
        `auth_data`       TEXT NOT NULL,
        `created_by`      INTEGER NOT NULL,
        `created_by_type` INTEGER NOT NULL,
        `created_at`      INTEGER NOT NULL,
        `last_access_at`  INTEGER NOT NULL,
        `updated_at`      INTEGER NOT NULL,
        PRIMARY KEY(id));"""),
      step(create_index("auth_keys", "created_at")),

      # System categories
      step("""CREATE TABLE `categories` (
        `id`            TEXT NOT NULL,
        `parent_id`     TEXT NOT NULL,
        `category_type` TEXT NOT NULL,
        `machine_label` TEXT NOT NULL,
        `label`         TEXT NOT NULL,
        `description`   TEXT,
        `status`        INTEGER NOT NULL,
        `created_at`    INTEGER NOT NULL,
        `updated_at`    INTEGER NOT NULL,
        PRIMARY KEY(id) );"""),
      step(create_index("categories", "id", unique=True)),

      # Defines the commands table. Lists all possible commands a local or remote gateway can perform.
      step("""CREATE TABLE `commands` (
        `id`            TEXT NOT NULL,
        `voice_cmd`     TEXT,
        `machine_label` TEXT NOT NULL,
        `label`         TEXT NOT NULL,
        `description`   TEXT,
        `public`        INTEGER NOT NULL,
        `status`        INTEGER NOT NULL,
        `created_at`    INTEGER NOT NULL,
        `updated_at`    INTEGER NOT NULL,
        PRIMARY KEY(id) );"""),
      step(create_index("commands", "id", unique=True)),
      step(create_index("commands", "machine_label", unique=True)),
      step(create_index("commands", "id", unique=True)),

      # Defines the devices table. Lists all possible devices for local gateway and related remote gateways.
      step("""CREATE TABLE `devices` (
        `id`                     TEXT NOT NULL,
        `gateway_id`             TEXT NOT NULL,
        `user_id`                TEXT NOT NULL,
        `device_type_id`         TEXT NOT NULL,
        `machine_label`          TEXT NOT NULL,
        `label`                  TEXT NOT NULL,
        `description`            TEXT,
        `location_id`            TEXT NOT NULL,
        `area_id`                TEXT NOT NULL,
        `notes`                  TEXT,
        `attributes`             TEXT,
        `intent_allow`           INTEGER,
        `intent_text`            TEXT,
        `pin_code`               TEXT,
        `pin_required`           INTEGER NOT NULL,
        `pin_timeout`            INTEGER DEFAULT 0,
        `statistic_label`        TEXT,
        `statistic_lifetime`     INTEGER DEFAULT 0,
        `statistic_type`         TEXT,
        `statistic_bucket_size`  TEXT,
        `energy_type`            TEXT,
        `energy_tracker_source`  TEXT,
        `energy_tracker_device`  TEXT,
        `energy_map`             TEXT,
        `controllable`           INTEGER DEFAULT 1,
        `allow_direct_control`   INTEGER DEFAULT 1,
        `status`                 INTEGER NOT NULL,
        `created_at`             INTEGER NOT NULL,
        `updated_at`             INTEGER NOT NULL,
/*     FOREIGN KEY(device_type_id) REFERENCES artist(device_types) */
     PRIMARY KEY(id));"""),
      step(create_index("devices", "id", unique=True)),
      step(create_index("devices", "device_type_id")),
      step(create_index("devices", "gateway_id")),

      # All possible inputs for a given device type/command/input.
      step("""CREATE TABLE `device_command_inputs` (
        `id`             TEXT NOT NULL,
        `device_type_id` TEXT NOT NULL,
        `command_id`     TEXT NOT NULL,
        `input_type_id`  TEXT NOT NULL,
        `machine_label`  TEXT NOT NULL,
        `label`          TEXT NOT NULL,
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
        UNIQUE (device_type_id, command_id, input_type_id) ON CONFLICT IGNORE);"""),
      step(create_index("device_command_inputs", "device_type_id")),

      # Defines the device command table to store command history and various info.
      step("""CREATE TABLE `device_commands` (
        `id`                    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `request_id`            TEXT NOT NULL,
        `persistent_request_id` TEXT,
        `source_gateway_id`     TEXT NOT NULL,
        `device_id`             TEXT NOT NULL,
        `command_id`            TEXT NOT NULL,
        `inputs`                TEXT,
        `created_at`            FLOAT NOT NULL,
        `broadcast_at`          FLOAT,
        `accepted_at`           FLOAT,
        `sent_at`               FLOAT,
        `received_at`           FLOAT,
        `pending_at`            FLOAT,
        `finished_at`           FLOAT,
        `not_before_at`         FLOAT,
        `not_after_at`          FLOAT,
        `command_status_received` INT NOT NULL DEFAULT 0,
        `history`               TEXT NOT NULL,
        `status`                TEXT NOT NULL,
        `auth_id`               TEXT NOT NULL,
        `requesting_source`     TEXT NOT NULL,
        `idempotence`           TEXT,
        `uploaded`              INTEGER NOT NULL DEFAULT 0,
        `uploadable`            INTEGER NOT NULL DEFAULT 0 /* For security, only items marked as 1 can be sent externally */
        );"""),
      step(create_index("device_commands", "request_id", unique=True)),
      step(create_index("device_commands", "finished_at")),

      # Stores user defined crontabs.
      step("""CREATE TABLE `crontab` (
        `id`           TEXT NOT NULL,
        `minute`       TEXT NOT NULL,
        `hour`         TEXT,
        `day`          TEXT NOT NULL,
        `month`        TEXT NOT NULL,
        `dow`          TEXT NOT NULL,
        `label`        TEXT,
        `enabled`      TEXT,
        `args`         TEXT,
        `kwargs`       FLOAT,
        `created_at`   FLOAT,
        `updated_at`   FLOAT
        );"""),
      # step(create_index("crontab", "id")),

      # Defines the device status table. Stores device status information.
      step("""CREATE TABLE `device_status` (
        `id`                   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `status_id`            TEXT NOT NULL,
        `device_id`            TEXT NOT NULL, /* device_id */
        `command_id`           TEXT,
        `request_id`           TEXT,
        `set_at`               REAL NOT NULL,
        `energy_usage`         INTEGER NOT NULL,
        `energy_type`          TEXT,
        `human_status`         TEXT NOT NULL,
        `human_message`        TEXT NOT NULL,
        `machine_status`       TEXT NOT NULL,
        `machine_status_extra` TEXT,
        `auth_id`              TEXT NOT NULL,
        `requesting_source`    TEXT,
        `reporting_source`     TEXT NOT NULL,
        `uploaded`             INTEGER NOT NULL DEFAULT 0,
        `uploadable`           INTEGER NOT NULL DEFAULT 0 /* For security, only items marked as 1 can be sent externally */
        );"""),
      step(create_index("device_status", "status_id", unique=True)),
      step(create_index("device_status", "uploaded")),

      # Device types defines the features of a device. For example, all X10 appliances or Insteon Lamps.
      step("""CREATE TABLE `device_types` (
        `id`            TEXT NOT NULL,
        `category_id`   TEXT,
        `machine_label` TEXT NOT NULL,
        `label`         TEXT NOT NULL,
        `description`   TEXT,
        `platform`      TEXT,
        `public`        INTEGER,
        `status`        INTEGER,
        `always_load`   INTEGER DEFAULT 0,
        `created_at`    INTEGER,
        `updated_at`    INTEGER,
        UNIQUE (label) ON CONFLICT IGNORE,
        UNIQUE (machine_label) ON CONFLICT IGNORE,
        PRIMARY KEY(id) ON CONFLICT IGNORE);"""),
      step(create_index("device_types", "id", unique=True)),

      # All possible commands for a given device type. For examples, appliances are on and off.
      step("""CREATE TABLE `device_type_commands` (
        `id`             TEXT NOT NULL,
        `device_type_id` TEXT NOT NULL,
        `command_id`     TEXT NOT NULL,
        `created_at`     INTEGER NOT NULL,
        UNIQUE (device_type_id, command_id) ON CONFLICT IGNORE);"""),
      step(create_index("device_type_commands", "device_type_id")),

      # System events
      step("""CREATE TABLE `events` (
        `id`            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `event_type`    TEXT NOT NULL, /* audit, system, user, etc */
        `event_subtype` TEXT NOT NULL, /* allow/deny */
        `priority`      TEXT NOT NULL, /* debug, low, normal, high, urgent */
        `source`        TEXT NOT NULL, /* where this message was created lib.states::method() */
        `auth_id`       TEXT,
        `attr1`         TEXT,
        `attr2`         TEXT,
        `attr3`         TEXT,
        `attr4`         TEXT,
        `attr5`         TEXT,
        `attr6`         TEXT,
        `attr7`         TEXT,
        `attr8`         TEXT,
        `attr9`         TEXT,
        `attr10`        TEXT,
        `meta`          TEXT, /* Any extra meta data. MSGPACK format */
        `created_at`    INTEGER NOT NULL);"""),
      step("CREATE INDEX IF NOT EXISTS event_type_idx ON events (event_type, event_subtype)"),
      step(create_index("events", "created_at")),

      # All gateways in the current cluster.
      step("""CREATE TABLE `gateways` (
        `id`                    TEXT NOT NULL,
        `machine_label`         TEXT NOT NULL,
        `label`                 TEXT NOT NULL,
        `description`           TEXT,
        `mqtt_auth`             TEXT,
        `mqtt_auth_next`        TEXT,
        `mqtt_auth_last_rotate_at` TEXT,
        `internal_ipv4`         TEXT,
        `external_ipv4`         TEXT,
        `internal_ipv6`         TEXT,
        `external_ipv6`         TEXT,
        `internal_port`         INTEGER,
        `external_port`         INTEGER,
        `internal_secure_port`  INTEGER,
        `external_secure_port`  INTEGER,
        `internal_mqtt`         INTEGER,
        `internal_mqtt_le`      INTEGER,
        `internal_mqtt_ss`      INTEGER,
        `internal_mqtt_ws`      INTEGER,
        `internal_mqtt_ws_le`   INTEGER,
        `internal_mqtt_ws_ss`   INTEGER,
        `external_mqtt`         INTEGER,
        `external_mqtt_le`      INTEGER,
        `external_mqtt_ss`      INTEGER,
        `external_mqtt_ws`      INTEGER,
        `external_mqtt_ws_le`   INTEGER,
        `external_mqtt_ws_ss`   INTEGER,
        `is_master`             BOOLEAN,
        `master_gateway_id`     TEXT,
        `dns_name`              TEXT,
        `status`                INTEGER NOT NULL,
        `created_at`            INTEGER NOT NULL,
        `updated_at`            INTEGER NOT NULL,
         PRIMARY KEY(id));"""),
      step(create_index("gateways", "id", unique=True)),

      # Used for quick access to GPG keys instead of key ring.
      step("""CREATE TABLE `gpg_keys` (
        `keyid`          TEXT NOT NULL,
        `fullname`      TEXT,
        `comment`       TEXT,
        `email`         TEXT NOT NULL,
        `endpoint_id`   TEXT NOT NULL,
        `endpoint_type` TEXT NOT NULL,
        `fingerprint`   TEXT NOT NULL,
        `length`        INTEGER NOT NULL,
        `expires_at`    INTEGER NOT NULL,
        `sigs`          TEXT,
        `subkeys`       TEXT,
        `ownertrust`    TEXT NOT NULL,
        `trust`         TEXT NOT NULL,
        `algo`          TEXT NOT NULL,
        `type`          TEXT NOT NULL,
        `uids`          TEXT,
        `publickey`     TEXT NOT NULL,
        `have_private`  INTEGER NOT NULL,
        `created_at`    INTEGER NOT NULL
        );"""),
      step(create_index("gpg_keys", "keyid")),

      # Input types defines input filters and how input validation is handled.
      step("""CREATE TABLE `input_types` (
        `id`            TEXT NOT NULL,
        `category_id`   TEXT NOT NULL,
        `machine_label` TEXT NOT NULL,
        `label`         TEXT NOT NULL,
        `description`   TEXT,
        `public`        INTEGER,
        `always_load`   INTEGER DEFAULT 0,
        `status`        INTEGER,
        `created_at`    INTEGER,
        `updated_at`    INTEGER,
        UNIQUE (label) ON CONFLICT IGNORE,
        UNIQUE (machine_label) ON CONFLICT IGNORE,
        PRIMARY KEY(id) ON CONFLICT IGNORE);"""),

      # All locations configured for an account.
      step("""CREATE TABLE `locations` (
        `id`             TEXT NOT NULL,
        `location_type`  TEXT NOT NULL,
        `machine_label`  TEXT NOT NULL,
        `environment`    TEXT,
        `label`          TEXT NOT NULL,
        `description`    TEXT,
        `updated_at`     INTEGER NOT NULL,
        `created_at`     INTEGER NOT NULL);"""),
      step(create_index("locations", "id")),

      # Stores module information
      step("""CREATE TABLE `modules` (
        `id`                 TEXT NOT NULL, /* module ID */
        `gateway_id`         TEXT NOT NULL,
        `machine_label`      TEXT NOT NULL,
        `module_type`        TEXT NOT NULL,
        `label`              TEXT NOT NULL,
        `short_description`  TEXT,
        `medium_description` TEXT,
        `description`        TEXT,
        `medium_description_html` TEXT,
        `description_html`   TEXT,
        `see_also`           TEXT,
        `repository_link`    TEXT,
        `issue_tracker_link` TEXT,
        `install_count`      INTEGER DEFAULT 0,
        `doc_link`           TEXT,
        `git_link`           TEXT,
        `install_branch`     TEXT NOT NULL,
        `require_approved`   INTEGER NOT NULL DEFAULT 1,
        `public`             INTEGER NOT NULL,
        `status`             INTEGER NOT NULL, /* disabled, enabled, deleted */
        `created_at`         INTEGER NOT NULL,
        `updated_at`         INTEGER NOT NULL,
        PRIMARY KEY(id));"""),
      step(create_index("modules", "status")),

      #  Stores module installation information
      step("""CREATE TABLE `module_commits` (
        `id`            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `module_id`     TEXT NOT NULL,
        `branch`        TEXT NOT NULL,
        `commit`        TEXT NOT NULL,
        `committed_at`  INTEGER NOT NULL,
        `approved`      INTEGER,
        `created_at`    INTEGER NOT NULL)"""),
      step("""CREATE UNIQUE INDEX IF NOT EXISTS module_commits_id_idx
        ON module_commits ('module_id', 'branch', 'committed_at')"""),
      step(create_index("module_commits", "commit")),

      # All possible device types for a module
      step("""CREATE TABLE `module_device_types` (
        `id`             TEXT NOT NULL,
        `module_id`      TEXT NOT NULL,
        `device_type_id` TEXT NOT NULL,
        `created_at`     INTEGER NOT NULL,
        UNIQUE (module_id, device_type_id) ON CONFLICT IGNORE);"""),

      # Tracks what versions of a module is installed, when it was installed, and last checked for new version.
      step("""CREATE TABLE `module_installed` (
        `id`                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `module_id`         TEXT NOT NULL, /* module.id */
        `installed_branch`  TEXT NOT NULL,
        `installed_commit`  TEXT NOT NULL,
        `install_at`        INTEGER NOT NULL,
        `last_check_at`     INTEGER NOT NULL);"""),
      step(create_index("module_installed", "module_id", unique=True)),

      # Defines the nodes data table. Stores node items.
      step("""CREATE TABLE `nodes` (
        `id`                TEXT NOT NULL,
        `parent_id`         TEXT,
        `gateway_id`        TEXT,
        `node_type`         TEXT NOT NULL,
        `weight`            INTEGER NOT NULL,
        `label`             TEXT,
        `machine_label`     TEXT,
        `always_load`       INTEGER,
        `destination`       TEXT,
        `data`              BLOB,
        `data_content_type` TEXT NOT NULL,
        `status`            INTEGER NOT NULL, /* Timestemp when msg was ack'd by the user. */
        `updated_at`        INTEGER NOT NULL,
        `created_at`        INTEGER NOT NULL );"""),
      step(create_index("nodes", "id")),
      step(create_index("nodes", "parent_id")),

      # Defines the notifications data table. Stores notifications.
      step("""CREATE TABLE `notifications` (
        `id`                      TEXT NOT NULL,
        `gateway_id`              TEXT NOT NULL,
        `type`                    TEXT NOT NULL, /* system, user, etc */
        `priority`                TEXT NOT NULL, /* debug, low, normal, high, urgent */
        `source`                  TEXT NOT NULL, /* where this message was created_at */
        `always_show`             INTEGER NOT NULL, /* If notification should always show until user clears it. */
        `always_show_allow_clear` INTEGER NOT NULL, /* User allowed to clear notification form always_show. */
        `acknowledged`            INTEGER NOT NULL, /* Timestemp when msg was ack'd by the user. */
        `acknowledged_at`         INTEGER, /* Timestemp when msg was ack'd by the user. */
        `user`                    TEXT,
        `title`                   TEXT,
        `message`                 TEXT,
        `meta`                    TEXT, /* Any extra meta data. JSON format */
        `targets`                 TEXT, /* Any extra meta data. JSON format */
        `local`                   BOOL,
        `expire_at`               INTEGER, /* timestamp when msg should expire */
        `created_at`              INTEGER NOT NULL);"""),
      # step(create_index("notifications", "id")),

      # Used to store access tokens
      step("""CREATE TABLE `oauth_access_tokens` (
        `id`         TEXT NOT NULL,
        `user_id`    TEXT NOT NULL,
        `client_id`  INTEGER NOT NULL,
        `dict_data`  BLOB,
        `created_at` INTEGER NOT NULL,
        `updated_at` INTEGER NOT NULL);"""),

      # Defines the SQL Dict table. Used by the :class:`SQLDict` class to maintain persistent dictionaries.
      step("""CREATE TABLE `sqldict` (
        `id`         INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `component`  TEXT NOT NULL,
        `dict_name`  INTEGER NOT NULL,
        `dict_data`  BLOB,
        `created_at` INTEGER NOT NULL,
        `updated_at` INTEGER NOT NULL);"""),
      step(create_index("sqldict", "dict_name")),
      step(create_index("sqldict", "component")),

      # Defines the tables used to store state information.
      step("""CREATE TABLE `states` (
        `id`          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `gateway_id`  TEXT NOT NULL,
        `name`        TEXT NOT NULL,
        `value_type`  TEXT,
        `value`       INTEGER,
        `live`        INTEGER NOT NULL,
        `created_at`  INTEGER NOT NULL);"""),
      step("""CREATE INDEX IF NOT EXISTS name_gateway_id_IDX
       ON states (name, gateway_id)"""),
      step(create_index("states", "created_at")),

      # Defines the statistics data table. Stores statistics.
      step("""CREATE TABLE `statistics` (
        `id`                  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `bucket_time`         DECIMAL(13,3) NOT NULL,
        `bucket_size`         INTEGER NOT NULL,
        `bucket_lifetime`     INTEGER,
        `bucket_type`         TEXT NOT NULL,
        `bucket_name`         TEXT NOT NULL,
        `bucket_value`        REAL NOT NULL,
        `bucket_average_data` TEXT,
        `anon`                INTEGER NOT NULL DEFAULT 0, /* anon data */
        `uploaded`            INTEGER NOT NULL DEFAULT 0,
        `finished`            INTEGER NOT NULL DEFAULT 0,
        `updated_at`          INTEGER NOT NULL);"""),
      step("""CREATE UNIQUE INDEX IF NOT EXISTS table_b_t_IDX
       ON statistics (bucket_name, bucket_type, bucket_time)"""),
      step("""CREATE INDEX IF NOT EXISTS table_t_n_t_IDX
       ON statistics (finished, uploaded, anon)"""),
      step(create_index("statistics", "bucket_type")),

      # Stores information about various stored data - user image uploaded places, etc.
      step("""CREATE TABLE `storage` (
        `id`                 TEXT,
        `scheme`             TEXT,
        `username`           TEXT,
        `password`           TEXT,
        `netloc`             TEXT,
        `port`               INTEGER,
        `path`               TEXT,
        `params`             TEXT,
        `query`              TEXT,
        `fragment`           TEXT,
        `mangle_id`          TEXT,
        `expires`            INTEGER,
        `public`             TEXT,
        `internal_url`       TEXT,
        `external_url`       TEXT,
        `internal_thumb_url` TEXT,
        `external_thumb_url` TEXT,
        `content_type`       TEXT,
        `charset`            TEXT,
        `size`               TEXT,
        `file_path`          TEXT,
        `file_path_thumb`    TEXT,
        `variables`          TEXT,
        `created_at`         INTEGER NOT NULL);"""),
      step(create_index("storage", "id")),
      step(create_index("storage", "expires")),

      # Used by the tasks library to start various tasks.
      step("""CREATE TABLE `tasks` (
        `id`             INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `run_section`    INTEGER NOT NULL,
        `run_once`       INTEGER,
        `run_interval`   INTEGER,
        `task_component` TEXT NOT NULL,
        `task_name`      TEXT NOT NULL,
        `task_arguments` BLOB,
        `source`         TEXT NOT NULL,
        `created_at`     INTEGER NOT NULL
        );"""),
      step(create_index("tasks", "id")),

      # Store users
      step("""CREATE TABLE `users` (
        `id`                 TEXT NOT NULL,
        `email`              TEXT NOT NULL,
        `name`               TEXT NOT NULL,
        `access_code_digits` TEXT,
        `access_code_string` TEXT,
        `updated_at`         INTEGER NOT NULL,
        `created_at`         INTEGER NOT NULL );"""),
      step(create_index("users", "id", unique=True)),
      step(create_index("users", "email")),

      # Defines the web interface session store. Used by the :class:`WebInterface` class to maintain session information
      step("""CREATE TABLE `webinterface_sessions` (
        `id`             TEXT NOT NULL,
        `enabled`        INTEGER NOT NULL,
        `gateway_id`     TEXT NOT NULL,
        `user_id`        TEXT NOT NULL,
        `auth_data`      TEXT NOT NULL,
        `created_at`     INTEGER NOT NULL,
        `last_access_at` INTEGER NOT NULL,
        `updated_at`     INTEGER NOT NULL,
        PRIMARY KEY(id));"""),
      step(create_index("webinterface_sessions", "id")),
      step(create_index("webinterface_sessions", "last_access_at")),

      # Used by the tasks library to start various tasks.
      step("""CREATE TABLE `webinterface_logs` (
        `id`                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        `request_at`        INTEGER,
        `request_protocol`  TEXT NOT NULL,
        `referrer`          TEXT NOT NULL,
        `agent`             TEXT NOT NULL,
        `ip`                INTEGER NOT NULL,
        `hostname`          TEXT NOT NULL,
        `method`            TEXT NOT NULL,
        `path`              TEXT NOT NULL,
        `secure`            BOOL NOT NULL,
        `auth_id`           TEXT,
        `response_code`     INTEGER NOT NULL,
        `response_size`     INTEGER NOT NULL,
        `uploadable`        BOOL DEFAULT 1,
        `uploaded`          BOOL DEFAULT 0
        );"""),

      # The following three tables and following views manages the variables set for devices and modules.
      step("""CREATE TABLE `variable_groups` (
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
        PRIMARY KEY(id));"""),
      step("""CREATE INDEX IF NOT EXISTS variable_groups_relation_id_type_idx
       ON variable_groups (group_relation_id, group_relation_type, group_machine_label)"""),

      # Store variable fields. These define that actual variables.
      step("""CREATE TABLE `variable_fields` (
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
        `created_at`          INTEGER NOT NULL);"""),
      step(create_index("variable_fields", "group_id")),

      # Stores the variable data. The format is defined in variable_fields (above).
      step("""CREATE TABLE `variable_data` (
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
        ;"""),
      step("""CREATE INDEX IF NOT EXISTS variable_data_id_type_idx 
        ON variable_data (field_id, data_relation_id, data_relation_type)"""),

      #########################
      ##      Triggers       ##
      #########################
      # Delete variable information for a device when a device is deleted.
      step("""CREATE TRIGGER delete_device_variable_data
         AFTER DELETE ON devices
         FOR EACH ROW
         BEGIN
           DELETE FROM variable_data WHERE data_relation_id = OLD.id and data_relation_type = "device";
         END"""),

      # Delete variable information for a module when a module is deleted.
      step("""CREATE TRIGGER delete_module_variable_data
         AFTER DELETE ON modules
         FOR EACH ROW
         BEGIN
           DELETE FROM module_device_types WHERE module_id = OLD.id;
           /* DELETE FROM module_installed WHERE module_id = OLD.id; */
           DELETE FROM variable_data WHERE data_relation_id = OLD.id and data_relation_type = "module";
         END"""),

      # Delete variable fields when variable groups are removed.
      step("""CREATE TRIGGER delete_variablegroups_variable_fields
         AFTER DELETE ON variable_groups
         FOR EACH ROW
         BEGIN
           DELETE FROM variable_fields WHERE group_id = OLD.id;
         END"""),

      # If a variable field is deleted, delete it's matching data.
      step("""CREATE TRIGGER delete_variablefields_variable_data
         AFTER DELETE ON variable_fields
         FOR EACH ROW
         BEGIN
           DELETE FROM variable_data WHERE field_id = OLD.id;
         END"""),

      #########################
      ##        Views        ##
      #########################
      # Create a devices view helper
      step("""CREATE VIEW devices_view AS
         SELECT devices.*, device_types.machine_label AS device_type_machine_label,
           categories.machine_label AS category_machine_label
         FROM devices
         JOIN device_types ON devices.device_type_id = device_types.id
         JOIN categories ON device_types.category_id = categories.id"""),

      #
      step("""CREATE VIEW modules_view AS
         SELECT modules.*, module_installed.installed_branch, module_installed.installed_commit,
         module_installed.last_check_at, module_installed. install_at, module_installed.last_check_at
         FROM modules LEFT OUTER JOIN module_installed ON modules.id = module_installed.module_id"""),

      #
      step("""CREATE VIEW module_device_types_view AS
         SELECT device_types.*, module_device_types.module_id
         FROM module_device_types
         JOIN device_types ON module_device_types.device_type_id = device_types.id"""),

      #
      step("""CREATE VIEW variable_field_data_view AS
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
         JOIN variable_groups ON variable_fields.group_id = variable_groups.id"""),

      #
      step("""CREATE VIEW variable_group_field_view AS
         SELECT  variable_fields.id as field_id, variable_fields.field_machine_label,variable_fields.field_label,
         variable_fields.field_description, variable_fields.field_weight,
         variable_fields.encryption, variable_fields.input_type_id, variable_fields. default_value, variable_fields.field_help_text,
         variable_fields.value_required, variable_fields.value_min, variable_fields.value_max,variable_fields.value_casing,
         variable_fields.multiple, variable_fields.created_at as field_created_at, variable_fields.updated_at as field_updated_at,
         variable_groups.id as group_id, variable_groups.group_label, variable_groups.group_machine_label,variable_groups.group_description,
         variable_groups.group_weight, variable_groups.status as group_status, variable_groups.group_relation_type,
         variable_groups.group_relation_id
         FROM variable_groups
         JOIN variable_fields ON variable_fields.group_id = variable_groups.id"""),

      #
      step("""CREATE VIEW variable_group_field_data_view AS
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
         JOIN variable_groups ON variable_fields.group_id = variable_groups.id"""),

      #
      step("""CREATE VIEW addable_device_types_view AS
         SELECT DISTINCT device_types.*
         FROM module_device_types
         JOIN device_types ON module_device_types.device_type_id = device_types.id
         ORDER BY device_types.label"""),

   ])
]
