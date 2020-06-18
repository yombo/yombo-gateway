"""
Create sql tables, base starting point.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/lib/localdb/migrations/sql/sql_1.html>`_
"""
from yombo.lib.localdb.migrations.sql import sql_create_index

migration_lines = [
      # System atoms
      """CREATE TABLE `atoms` (
        `id`              VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `gateway_id`      CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `value`           VARBINARY(8192),
        `value_human`     VARCHAR(8192) COLLATE utf8mb4_unicode_ci,
        `value_type`      VARCHAR(32) COLLATE latin1_general_cs,
        `request_by`       VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_by_type`  VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context` VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `last_access_at`  INTEGER UNSIGNED,
        `created_at`      INTEGER UNSIGNED NULL,
        `updated_at`      INTEGER UNSIGNED NULL,
        PRIMARY KEY(id));""",

      # Local authentication keys
      """CREATE TABLE `authkeys` (
        `id`               CHAR(43) COLLATE latin1_general_cs NOT NULL,
        `auth_key_id_full` CHAR(75) COLLATE latin1_general_cs,
        `preserve_key`     TINYINT UNSIGNED NOT NULL,
        `machine_label`    VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `label`            VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `description`      VARCHAR(2048) COLLATE utf8mb4_unicode_ci,
        `roles`            VARBINARY(10000) COLLATE latin1_general_ci,
        `request_by`       VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_by_type`  VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context`  VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `expired_at`       INTEGER UNSIGNED,
        `last_access_at`   INTEGER UNSIGNED,
        `status`           TINYINT UNSIGNED NOT NULL, /* disabled, enabled, deleted */
        `created_at`       INTEGER UNSIGNED NOT NULL,
        `updated_at`       INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id) );""",
      sql_create_index("authkeys", "id", unique=True),

      # System categories
      """CREATE TABLE `categories` (
        `id`                 CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `category_parent_id` CHAR(22) COLLATE latin1_general_cs,
        `category_type`      VARCHAR(15) COLLATE latin1_general_cs NOT NULL,
        `machine_label`      VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `label`              VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `description`        MEDIUMTEXT  COLLATE latin1_general_cs,
        `status`             TINYINT UNSIGNED NOT NULL,
        `created_at`         INTEGER UNSIGNED NOT NULL,
        `updated_at`         INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id) );""",

      # Defines the commands table. Lists all possible commands a local or remote gateway can perform.
      """CREATE TABLE `commands` (
        `id`               CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `user_id`          CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `original_user_id` CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `machine_label`    VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `label`            VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `description`      VARCHAR(8192) COLLATE latin1_general_cs,
        `public`           TINYINT NOT NULL,
        `status`           TINYINT NOT NULL,
        `created_at`       INTEGER UNSIGNED NOT NULL,
        `updated_at`       INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id) );""",
      sql_create_index("commands", "machine_label", unique=True),

      # Stores user defined crontabs.
      """CREATE TABLE `crontabs` (
        `id`            CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `minute`        VARCHAR(20) COLLATE latin1_general_cs NOT NULL,
        `hour`          VARCHAR(20) COLLATE latin1_general_cs NOT NULL,
        `day`           VARCHAR(20) COLLATE latin1_general_cs NOT NULL,
        `month`         VARCHAR(20) COLLATE latin1_general_cs NOT NULL,
        `dow`           VARCHAR(20) COLLATE latin1_general_cs NOT NULL,
        `machine_label` VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `label`         VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `enabled`       TINYINT NOT NULL,
        `args`          MEDIUMTEXT COLLATE utf8mb4_unicode_ci,
        `kwargs`        MEDIUMTEXT COLLATE utf8mb4_unicode_ci,
        `created_at`    INTEGER UNSIGNED NOT NULL,
        `updated_at`    INTEGER UNSIGNED NOT NULL,
       PRIMARY KEY(id));""",

      # Defines the devices table. Lists all possible devices for local gateway and related remote gateways.
      """CREATE TABLE `devices` (
        `id`                         CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `device_parent_id`           CHAR(22) COLLATE latin1_general_cs,
        `gateway_id`                 CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `user_id`                    CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `device_type_id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `machine_label`              VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `label`                      VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `description`                VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `location_id`                CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `area_id`                    CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `notes`                      MEDIUMTEXT COLLATE utf8mb4_unicode_ci,
        `attributes`                 VARCHAR(1024) COLLATE utf8mb4_unicode_ci,
        `intent_allow`               TINYINT UNSIGNED,
        `intent_text`                VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `pin_code`                   VARCHAR(100) COLLATE utf8mb4_unicode_ci,
        `pin_required`               TINYINT UNSIGNED NOT NULL,
        `pin_timeout`                INTEGER UNSIGNED DEFAULT 0,
        `statistic_label`            VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `statistic_lifetime`         INTEGER UNSIGNED DEFAULT 0,
        `statistic_type`             VARCHAR(40) COLLATE utf8mb4_unicode_ci,
        `statistic_bucket_size`      SMALLINT UNSIGNED,
        `energy_type`                VARCHAR(50) COLLATE utf8mb4_unicode_ci,
        `energy_tracker_source_type` VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `energy_tracker_source_id`   VARCHAR(32),
        `energy_map`                 VARCHAR(512) COLLATE latin1_general_ci,
        `scene_controllable`         TINYINT UNSIGNED DEFAULT 1,
        `allow_direct_control`       TINYINT UNSIGNED DEFAULT 1,
        `status`                     TINYINT UNSIGNED NOT NULL,
        `created_at`                 INTEGER UNSIGNED NOT NULL,
        `updated_at`                 INTEGER UNSIGNED NOT NULL,
       PRIMARY KEY(id));""",

      # Defines the device command table to store command history and various info.
      """CREATE TABLE `device_commands` (
        `id`                     CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `gateway_id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `persistent_request_id`  CHAR(38) COLLATE latin1_general_cs,
        `device_id`              CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `command_id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `inputs`                 BLOB,
        `created_at`             DECIMAL(13,4) NOT NULL,
        `broadcast_at`           DECIMAL(13,4),
        `accepted_at`            DECIMAL(13,4),
        `sent_at`                DECIMAL(13,4),
        `received_at`            DECIMAL(13,4),
        `pending_at`             DECIMAL(13,4),
        `finished_at`            DECIMAL(13,4),
        `not_before_at`          DECIMAL(13,4),
        `not_after_at`           DECIMAL(13,4),
        `history`                BLOB,
        `status`                 VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_by`             VARCHAR(43) COLLATE latin1_general_ci NOT NULL,
        `request_by_type`        VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context`        VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `idempotence`            VARCHAR(64) COLLATE latin1_general_ci,
        `uploaded`               TINYINT UNSIGNED NOT NULL DEFAULT 0,
        `uploadable`             TINYINT UNSIGNED NOT NULL DEFAULT 0, /* For security, only items marked as 1 can be sent externally */
        PRIMARY KEY(id));""",
      sql_create_index("device_commands", "finished_at"),

      # All possible inputs for a given device type/command/input.
      """CREATE TABLE `device_command_inputs` (
        `id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `device_type_id` CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `command_id`     CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `input_type_id`  CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `machine_label`  VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `label`          VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `live_update`    TINYINT UNSIGNED NOT NULL,
        `value_required` TINYINT UNSIGNED NOT NULL,
        `value_max`      INTEGER UNSIGNED NOT NULL,
        `value_min`      INTEGER UNSIGNED NOT NULL,
        `value_casing`   VARCHAR(30) COLLATE latin1_general_ci NOT NULL,
        `encryption`     VARCHAR(30) COLLATE latin1_general_ci NOT NULL,
        `notes`          VARCHAR(2048) COLLATE latin1_general_ci,
        `updated_at`     INTEGER UNSIGNED NOT NULL,
        `created_at`     INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id));""",
        # UNIQUE (id) ON CONFLICT IGNORE);""",
      sql_create_index("device_command_inputs", "id", unique=True),

      # Defines the device states table to store device state history
      """CREATE TABLE `device_states` (
        `id`                   CHAR(38) COLLATE latin1_general_ci NOT NULL,
        `gateway_id`           CHAR(22) COLLATE latin1_general_ci NOT NULL,
        `device_id`            CHAR(22) COLLATE latin1_general_ci NOT NULL,
        `command_id`           CHAR(22) COLLATE latin1_general_ci,
        `device_command_id`    CHAR(22) COLLATE latin1_general_ci,
        `energy_usage`         DECIMAL(7,6) NOT NULL,
        `energy_type`          VARCHAR(64) COLLATE latin1_general_ci,
        `human_state`          VARCHAR(1024) NOT NULL COLLATE utf8mb4_unicode_ci,
        `human_message`        VARCHAR(4096) NOT NULL COLLATE utf8mb4_unicode_ci,
        `machine_state`        VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `machine_state_extra`  VARBINARY(20000),
        `request_by`           VARCHAR(43) COLLATE latin1_general_ci NOT NULL,
        `request_by_type`      VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context`      VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `reporting_source`     VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `created_at`           INTEGER UNSIGNED NOT NULL,
        `uploaded`             TINYINT UNSIGNED NOT NULL DEFAULT 0,
        `uploadable`           TINYINT UNSIGNED NOT NULL DEFAULT 0, /* For security, only items marked as 1 can be sent externally */
        PRIMARY KEY(id));""",
      # sql_create_index("device_states", "id", unique=True),
      sql_create_index("device_states", "uploaded"),

      # Device types defines the features of a device. For example, all X10 appliances or Insteon lights.
      """CREATE TABLE `device_types` (
        `id`               CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `user_id`          CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `original_user_id` CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `category_id`      CHAR(22) COLLATE latin1_general_cs,
        `machine_label`    VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `label`            VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `description`      VARCHAR(8192) COLLATE latin1_general_ci,
        `public`           TINYINT UNSIGNED,
        `status`           TINYINT UNSIGNED,
        `created_at`       INTEGER UNSIGNED NOT NULL,
        `updated_at`       INTEGER UNSIGNED NOT NULL,
        UNIQUE (label) ON CONFLICT IGNORE,
        UNIQUE (machine_label) ON CONFLICT IGNORE,
        PRIMARY KEY(id) ON CONFLICT IGNORE);""",
      sql_create_index("device_types", "id", unique=True),

      # All possible commands for a given device type. For examples, appliances are on and off.
      """CREATE TABLE `device_type_commands` (
        `id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `device_type_id` CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `command_id`     CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `created_at`     INTEGER UNSIGNED NOT NULL,
        UNIQUE (device_type_id, command_id) ON CONFLICT IGNORE);""",
      sql_create_index("device_type_commands", "id", unique=True),

      # Discovered devices.
      """CREATE TABLE `discovery` (
        `id`               CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `gateway_id`       CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `device_id`        CHAR(22) COLLATE utf8mb4_unicode_ci,  /* if matched to a Yombo Device */
        `device_type_id`   CHAR(22) COLLATE utf8mb4_unicode_ci,
        `discovered_at`    INTEGER UNSIGNED NOT NULL,
        `last_seen_at`     INTEGER UNSIGNED NOT NULL,
        `mfr`              VARCHAR(128) COLLATE utf8mb4_unicode_ci NOT NULL,
        `model`            VARCHAR(128) COLLATE utf8mb4_unicode_ci NOT NULL,
        `serial`           VARCHAR(128) COLLATE utf8mb4_unicode_ci NOT NULL,
        `label`            VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `machine_label`    VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `description`      VARCHAR(1024) COLLATE utf8mb4_unicode_ci NOT NULL,
        `variables`        VARBINARY(15000),  /* msgpack+base85, only needs latin */
        `request_context`  VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `status`           TINYINT UNSIGNED NOT NULL,
        `created_at`       INTEGER UNSIGNED NOT NULL,
        `updated_at`       INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id));""",
      sql_create_index("discovery", "id", unique=True),

      # System events
      """CREATE TABLE `events` (
        `id`              INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTOINCREMENT,
        `event_type`      VARCHAR(32) COLLATE latin1_general_ci NOT NULL, /* audit, system, user, etc */
        `event_subtype`   VARCHAR(32) COLLATE latin1_general_ci NOT NULL, /* allow/deny */
        `priority`        VARCHAR(32) COLLATE latin1_general_ci NOT NULL, /* debug, low, normal, high, urgent */
        `request_by`      VARCHAR(43) COLLATE latin1_general_ci NOT NULL,
        `request_by_type` VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context` VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `attr1`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr2`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr3`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr4`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr5`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr6`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr7`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr8`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr9`           VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `attr10`          VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `meta`            VARBINARY(15000), /* Any extra meta data. MSGPACK format */
        `created_at`      INTEGER UNSIGNED NOT NULL);""",
      "CREATE INDEX IF NOT EXISTS event_type_idx ON events (event_type, event_subtype)",
      sql_create_index("events", "created_at"),

      # All gateways in the current cluster.
      """CREATE TABLE `gateways` (
        `id`                        CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `machine_label`             VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `label`                     VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `description`               VARCHAR(8192) COLLATE latin1_general_ci,
        `user_id`                   VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `mqtt_auth`                 VARCHAR(128) COLLATE latin1_general_cs,
        `mqtt_auth_next`            VARCHAR(128) COLLATE latin1_general_cs,
        `mqtt_auth_last_rotate_at`  INTEGER UNSIGNED,
        `internal_ipv4`             VARCHAR(64) COLLATE latin1_general_ci,
        `external_ipv4`             VARCHAR(64) COLLATE latin1_general_ci,
        `internal_ipv6`             VARCHAR(64) COLLATE latin1_general_ci,
        `external_ipv6`             VARCHAR(64) COLLATE latin1_general_ci,
        `internal_http_port`        SMALLINT UNSIGNED,
        `external_http_port`        SMALLINT UNSIGNED,
        `internal_http_secure_port` SMALLINT UNSIGNED,
        `external_http_secure_port` SMALLINT UNSIGNED,
        `internal_mqtt`             SMALLINT UNSIGNED,
        `internal_mqtt_le`          SMALLINT UNSIGNED,
        `internal_mqtt_ss`          SMALLINT UNSIGNED,
        `internal_mqtt_ws`          SMALLINT UNSIGNED,
        `internal_mqtt_ws_le`       SMALLINT UNSIGNED,
        `internal_mqtt_ws_ss`       SMALLINT UNSIGNED,
        `external_mqtt`             SMALLINT UNSIGNED,
        `external_mqtt_le`          SMALLINT UNSIGNED,
        `external_mqtt_ss`          SMALLINT UNSIGNED,
        `external_mqtt_ws`          SMALLINT UNSIGNED,
        `external_mqtt_ws_le`       SMALLINT UNSIGNED,
        `external_mqtt_ws_ss`       SMALLINT UNSIGNED,
        `is_master`                 TINYINT UNSIGNED,
        `master_gateway_id`         VARCHAR(32) COLLATE latin1_general_ci,
        `dns_name`                  VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `status`                    TINYINT UNSIGNED NOT NULL,
        `created_at`                INTEGER UNSIGNED NOT NULL,
        `updated_at`                INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",

      # Used for quick access to GPG keys instead of key ring.
      """CREATE TABLE `gpg_keys` (
        `id`            VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `fullname`      VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `comment`       VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `email`         VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `endpoint_id`   VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `endpoint_type` VARCHAR(256) COLLATE latin1_general_ci NOT NULL,
        `fingerprint`   VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `length`        SMALLINT UNSIGNED NULL,
        `expires_at`    INTEGER UNSIGNED NOT NULL,
        `sigs`          VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `subkeys`       VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `ownertrust`    VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `trust`         VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `algo`          VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `type`          VARCHAR(1024) COLLATE latin1_general_ci NOT NULL,
        `uids`          VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `publickey`     VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `have_private`  TINYINT UNSIGNED NOT NULL,
        `created_at`    INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id) );""",

      # Input types defines input filters and how input validation is handled.
      """CREATE TABLE `input_types` (
        `id`               CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `user_id`          CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `original_user_id` CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `category_id`      CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `machine_label`    VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `label`            VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `description`      VARCHAR(2048) COLLATE latin1_general_ci NOT NULL,
        `public`           TINYINT UNSIGNED NOT NULL,
        `status`           TINYINT UNSIGNED NOT NULL,
        `created_at`       INTEGER UNSIGNED NOT NULL,
        `updated_at`       INTEGER UNSIGNED NOT NULL,
        UNIQUE (label) ON CONFLICT IGNORE,
        UNIQUE (machine_label) ON CONFLICT IGNORE,
        PRIMARY KEY(id) ON CONFLICT IGNORE);""",
      sql_create_index("input_types", "id", unique=True),

      # All locations configured for an account.
      """CREATE TABLE `locations` (
        `id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `user_id`        CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `location_type`  VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `machine_label`  VARCHAR(20) COLLATE utf8mb4_unicode_ci NOT NULL,
        `label`          VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `description`    VARCHAR(2048) COLLATE utf8mb4_unicode_ci,
        `updated_at`     INTEGER UNSIGNED NOT NULL,
        `created_at`     INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id) );""",

      # Stores module information
      """CREATE TABLE `modules` (
        `id`                      CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `user_id`                 CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `original_user_id`        CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `module_type`             VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `machine_label`           VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `label`                   VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `short_description`       VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `medium_description`      VARCHAR(4096) COLLATE utf8mb4_unicode_ci NOT NULL,
        `description`             VARCHAR(15000) COLLATE utf8mb4_unicode_ci NOT NULL,
        `medium_description_html` VARCHAR(5120) COLLATE utf8mb4_unicode_ci,
        `description_html`        TEXT COLLATE utf8mb4_unicode_ci,
        `see_also`                TEXT COLLATE utf8mb4_unicode_ci,
        `repository_link`         VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `issue_tracker_link`      VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `install_count`           INTEGER UNSIGNED NOT NULL DEFAULT 0,
        `doc_link`                VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `git_link`                VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `git_auto_approve`        TINYINT UNSIGNED NOT NULL,
        `public`                  TINYINT NOT NULL,
        `status`                  TINYINT NOT NULL, /* disabled, enabled, deleted */
        `install_branch`          VARCHAR(64) COLLATE utf8mb4_unicode_ci NOT NULL,
        `require_approved`        TINYINT NOT NULL DEFAULT 1,
        `created_at`              INTEGER UNSIGNED NOT NULL,
        `updated_at`              INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id));""",
      sql_create_index("modules", "id", unique=True),
      sql_create_index("modules", "status"),

      #  Stores module installation information
      """CREATE TABLE `module_commits` (
        `id`            CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `module_id`     CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `branch`        VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `commit`        VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `committed_at`  INTEGER UNSIGNED NOT NULL,
        `approved`      TINYINT UNSIGNED,
        `approved_at`   INTEGER UNSIGNED NOT NULL,
        `created_at`    INTEGER UNSIGNED NOT NULL)""",
      """CREATE UNIQUE INDEX IF NOT EXISTS module_commits_id_idx
        ON module_commits ('module_id', 'branch', 'committed_at')""",
      sql_create_index("module_commits", "module_id"),
      sql_create_index("module_commits", "created_at"),

      # All possible device types for a module
      """CREATE TABLE `module_device_types` (
        `id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `module_id`      CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `device_type_id` CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `created_at`     INTEGER UNSIGNED NOT NULL,
        UNIQUE (module_id, device_type_id) ON CONFLICT IGNORE);""",
      sql_create_index("module_device_types", "id", unique=True),

      # Tracks what versions of a module is installed, when it was installed, and last checked for new version.
      """CREATE TABLE `modules_installed` (
        `id`                INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTOINCREMENT,
        `module_id`         CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `installed_branch`  VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `installed_commit`  VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `installed_at`      INTEGER UNSIGNED NOT NULL,
        `last_check_at`     INTEGER UNSIGNED NOT NULL);""",
      sql_create_index("modules_installed", "module_id", unique=True),

      # Stores local MQTT allowed users.
      """CREATE TABLE `mqtt_users` (
        `id`          INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTOINCREMENT,
        `gateway_id`  CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `password`    VARCHAR(100) COLLATE latin1_general_cs NOT NULL, /* system, user, etc */
        `description` VARCHAR(512) COLLATE latin1_general_ci NOT NULL,
        `topics`      VARBINARY(15000) NOT NULL,
        `updated_at`  INTEGER UNSIGNED NOT NULL,
        `created_at`  INTEGER UNSIGNED NOT NULL);""",

      # Defines the nodes data table. Stores node items.
      """CREATE TABLE `nodes` (
        `id`                CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `node_parent_id`    CHAR(22) COLLATE latin1_general_cs,
        `gateway_id`        CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `node_type`         VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `weight`            SMALLINT UNSIGNED NOT NULL,
        `machine_label`     VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `label`             VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `always_load`       SMALLINT DEFAULT 1,
        `destination`       VARCHAR(100) COLLATE latin1_general_cs,
        `data`              BLOB,
        `data_content_type` VARCHAR(35) COLLATE latin1_general_cs NOT NULL,
        `status`            TINYINT UNSIGNED NOT NULL, /* Timestemp when msg was ack'd by the user. */
        `updated_at`        INTEGER UNSIGNED NOT NULL,
        `created_at`        INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",
      # sql_create_index("nodes", "id", unique=True),
      sql_create_index("nodes", "node_parent_id"),

      # Defines the notifications data table. Stores notifications.
      """CREATE TABLE `notifications` (
        `id`                      CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `gateway_id`              CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `type`                    VARCHAR(20) COLLATE latin1_general_cs NOT NULL, /* system, user, etc */
        `title`                   VARCHAR(256) COLLATE latin1_general_ci NOT NULL,
        `message`                 VARCHAR(4096) COLLATE latin1_general_ci NOT NULL,
        `priority`                VARCHAR(10) COLLATE latin1_general_ci NOT NULL, /* debug, low, normal, high, urgent */
        `always_show`             TINYINT UNSIGNED NOT NULL, /* If notification should always show until user clears it. */
        `always_show_allow_clear` TINYINT UNSIGNED NOT NULL, /* User allowed to clear notification form always_show. */
        `request_by`              VARCHAR(43) COLLATE latin1_general_ci,
        `request_by_type`         VARCHAR(25) COLLATE latin1_general_ci,
        `request_context`         VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `acknowledged`            TINYINT UNSIGNED NOT NULL, /* Timestemp when msg was ack'd by the user. */
        `acknowledged_at`         INTEGER UNSIGNED, /* Timestemp when msg was ack'd by the user. */
        `meta`                    VARBINARY(10000), /* Any extra meta data. */
        `targets`                 VARBINARY(10000), /* Any extra meta data. JSON format */
        `local`                   TINYINT UNSIGNED,
        `expire_at`               INTEGER UNSIGNED, /* timestamp when msg should expire */
        `created_at`              INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",

      # Used to store access tokens
      """CREATE TABLE `oauth_access_tokens` (
        `id`         VARCHAR(38) COLLATE latin1_general_cs NOT NULL,
        `user_id`    CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `client_id`  VARCHAR(64) COLLATE latin1_general_cs NOT NULL,
        `dict_data`  BLOB,
        `created_at` INTEGER UNSIGNED NOT NULL,
        `updated_at` INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",

      # System permissions. For users and authkeys.
      """CREATE TABLE `permissions` (
        `id`              CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `attach_id`       VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `attach_type`     VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `machine_label`   VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `label`           VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `description`     VARCHAR(2048) COLLATE utf8mb4_unicode_ci,
        `policy`          VARCHAR(16384) COLLATE utf8mb4_unicode_ci,
        `request_by`      VARCHAR(43) COLLATE latin1_general_ci NOT NULL,
        `request_by_type` VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context` VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `created_at`      INTEGER UNSIGNED NOT NULL,
        `updated_at`      INTEGER UNSIGNED NULL,
        PRIMARY KEY(id) );""",

      # Roles are used to add permissions to and assign to users or authkeys
      """CREATE TABLE `roles` (
        `id`              CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `machine_label`   VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `label`           VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `description`     VARCHAR(1024) COLLATE latin1_general_cs NOT NULL,
        `request_by`      VARCHAR(43) COLLATE latin1_general_ci NOT NULL,
        `request_by_type` VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context` VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `updated_at`      INTEGER UNSIGNED NOT NULL,
        `created_at`      INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id));""",

      # Defines the SQL Dict table. Used by the :class:`SQLDict` class to maintain persistent dictionaries.
      """CREATE TABLE `sqldicts` (
        `id`         CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `component`  VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `dict_name`  VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `dict_data`  BLOB,
        `max_length` INTEGER UNSIGNED,
        `created_at` INTEGER UNSIGNED NOT NULL,
        `updated_at` INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",
      sql_create_index("sqldicts", "dict_name"),
      sql_create_index("sqldicts", "component"),

      # Defines the tables used to store state information.
      """CREATE TABLE `states` (
        `id`              VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `gateway_id`      CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `value`           VARBINARY(8192),
        `value_human`     VARCHAR(8192) COLLATE utf8mb4_unicode_ci,
        `value_type`      VARCHAR(32) COLLATE latin1_general_cs,
        `request_by`      VARCHAR(43) COLLATE latin1_general_ci NOT NULL,
        `request_by_type` VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context` VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `last_access_at`  INTEGER UNSIGNED,
        `created_at`      INTEGER UNSIGNED NULL,
        `updated_at`      INTEGER UNSIGNED NULL,
        PRIMARY KEY(id));""",

      # Defines the statistics data table. Stores statistics.
      """CREATE TABLE `statistics` (
        `id`                  INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTOINCREMENT,
        `bucket_time`         DECIMAL(13,4) NOT NULL,
        `bucket_size`         MEDIUMINT UNSIGNED NOT NULL,
        `bucket_lifetime`     MEDIUMINT UNSIGNED,
        `bucket_type`         VARCHAR(128) COLLATE utf8mb4_unicode_ci NOT NULL,
        `bucket_name`         VARCHAR(128) COLLATE utf8mb4_unicode_ci NOT NULL,
        `bucket_value`        DECIMAL(13,4) NOT NULL,
        `bucket_average_data` BLOB,
        `anon`                TINYINT NOT NULL DEFAULT 0, /* anon data */
        `uploaded`            TINYINT NOT NULL DEFAULT 0,
        `finished`            TINYINT NOT NULL DEFAULT 0,
        `updated_at`          INTEGER UNSIGNED NOT NULL);""",
      """CREATE UNIQUE INDEX IF NOT EXISTS table_b_t_IDX
       ON statistics (bucket_name, bucket_type, bucket_time)""",
      """CREATE INDEX IF NOT EXISTS table_t_n_t_IDX
       ON statistics (finished, uploaded, anon)""",
      sql_create_index("statistics", "bucket_type"),

      # Stores information about various stored data - user image uploaded places, etc.
      """CREATE TABLE `storage` (
        `id`                 VARCHAR(38) COLLATE latin1_general_cs NOT NULL,
        `gateway_id`      CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `scheme`             VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `username`           VARCHAR(64) COLLATE latin1_general_cs NOT NULL,
        `password`           VARCHAR(64) COLLATE latin1_general_cs NOT NULL,
        `netloc`             VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `port`               MEDIUMINT UNSIGNED,
        `path`               VARCHAR(256) COLLATE latin1_general_cs NOT NULL,
        `params`             VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `query`              VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `fragment`           VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `mangle_id`          VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `expires`            INTEGER UNSIGNED,
        `public`             TEXT,
        `internal_url`       VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `external_url`       VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `internal_thumb_url` VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `external_thumb_url` VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `content_type`       VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `charset`            VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `size`               INTEGER UNSIGNED,
        `file_path`          VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `file_path_thumb`    VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `variables`          VARBINARY(10000) COLLATE utf8mb4_unicode_ci NOT NULL,
        `request_by`         VARCHAR(43) COLLATE latin1_general_ci NOT NULL,
        `request_by_type`    VARCHAR(32) COLLATE latin1_general_ci NOT NULL,
        `request_context`    VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `created_at`         INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",
      sql_create_index("storage", "expires"),

      # Used by the tasks library to start various tasks.
      """CREATE TABLE `tasks` (
        `id`             INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTOINCREMENT,
        `run_section`    INTEGER NOT NULL,
        `run_once`       MEDIUMINT UNSIGNED,
        `run_interval`   MEDIUMINT UNSIGNED,
        `task_component` VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `task_name`      VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `task_arguments` BLOB,
        `source`         VARCHAR(2048) COLLATE utf8mb4_unicode_ci NOT NULL,
        `created_at`     INTEGER UNSIGNED NOT NULL
        );""",
      # sql_create_index("tasks", "id"),

      # Store users
      """CREATE TABLE `users` (
        `id`                 CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `gateway_id`         CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `email`              VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
        `name`               VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
        `access_code_string` VARCHAR(32) COLLATE utf8mb4_unicode_ci,
        `updated_at`         INTEGER UNSIGNED NOT NULL,
        `created_at`         INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",
      sql_create_index("users", "email"),

      # Maps users to roles, auth_keys, and more.
      """CREATE TABLE `user_access` (
        `id`              CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `user_id`         CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `attachment_type` VARCHAR(30) COLLATE latin1_general_cs NOT NULL,
        `attachment_id`   VARCHAR(60) COLLATE latin1_general_cs NOT NULL,
        `created_at`      INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id));""",
      # UNIQUE (id) ON CONFLICT IGNORE);""",
      sql_create_index("user_access", "user_id"),
      """CREATE INDEX IF NOT EXISTS user_access_attachment_idx
        ON user_access (attachment_type, attachment_id)""",

      # Stores the variable data. The format is defined in variable_fields (above).
      """CREATE TABLE `variable_data` (
        `id`                     CHAR(22) COLLATE latin1_general_cs NOT NULL,  /* variable_id */
        `user_id`                CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `gateway_id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `variable_field_id`      CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `variable_relation_id`   CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `variable_relation_type` VARCHAR(255) COLLATE latin1_general_cs NOT NULL,
        `data`                   MEDIUMTEXT COLLATE utf8mb4_unicode_ci NOT NULL,
        `data_content_type`      VARCHAR(35) COLLATE latin1_general_cs NOT NULL,
        `data_weight`            SMALLINT DEFAULT 0,
        `updated_at`             INTEGER UNSIGNED NOT NULL,
        `created_at`             INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",
      """CREATE INDEX IF NOT EXISTS variable_data_id_type_idx
        ON variable_data (variable_field_id, variable_relation_id, variable_relation_type)""",

      # Store variable fields. These define that actual variables.
      """CREATE TABLE `variable_fields` (
        `id`                  CHAR(22) COLLATE latin1_general_cs NOT NULL, /* variable_field_id */
        `user_id`             CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `variable_group_id`   CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `field_machine_label` VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `field_label`         VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `field_description`   VARCHAR(1024) COLLATE utf8mb4_unicode_ci NOT NULL,
        `field_weight`        SMALLINT DEFAULT 0,
        `value_required`      TINYINT NOT NULL,
        `value_max`           MEDIUMINT,
        `value_min`           MEDIUMINT,
        `value_casing`        VARCHAR(60) COLLATE latin1_general_ci NOT NULL,
        `encryption`          VARCHAR(60) COLLATE latin1_general_ci NOT NULL,
        `input_type_id`       VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `default_value`       VARCHAR(1000) COLLATE latin1_general_cs NOT NULL,
        `field_help_text`     VARCHAR(4000) COLLATE latin1_general_cs NOT NULL,
        `multiple`            TINYINT NOT NULL,
        `updated_at`          INTEGER UNSIGNED NOT NULL,
        `created_at`          INTEGER UNSIGNED NOT NULL,
         PRIMARY KEY(id));""",
      sql_create_index("variable_fields", "variable_group_id"),

      # The following three tables and following views manages the variables set for devices and modules.
      """CREATE TABLE `variable_groups` (
        `id`                  CHAR(22) COLLATE latin1_general_cs NOT NULL, /* group_id */
        `group_relation_id`   CHAR(22) COLLATE latin1_general_cs NOT NULL,
        `group_relation_type` VARCHAR(60) COLLATE latin1_general_cs NOT NULL,
        `group_machine_label` VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `group_label`         VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
        `group_description`   VARCHAR(1024) COLLATE utf8mb4_unicode_ci NOT NULL,
        `group_weight`        SMALLINT DEFAULT 0,
        `status`              TINYINT UNSIGNED NOT NULL, /* disabled, enabled, deleted */
        `updated_at`          INTEGER UNSIGNED NOT NULL,
        `created_at`          INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id));""",
      """CREATE INDEX IF NOT EXISTS variable_groups_relation_id_type_idx
       ON variable_groups (group_relation_id, group_relation_type, group_machine_label)""",

      # Used by the tasks library to start various tasks.
      """CREATE TABLE `web_logs` (
        `id`                INTEGER UNSIGNED NOT NULL PRIMARY KEY AUTOINCREMENT,
        `request_at`        INTEGER UNSIGNED,
        `request_id`        CHAR(20) COLLATE latin1_general_cs NOT NULL,
        `request_protocol`  VARCHAR(32) COLLATE latin1_general_cs NOT NULL,
        `referrer`          VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `agent`             VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `ip`                VARCHAR(64) COLLATE latin1_general_cs NOT NULL,
        `hostname`          VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `method`            VARCHAR(10) COLLATE latin1_general_cs NOT NULL,
        `path`              VARCHAR(128) COLLATE latin1_general_cs NOT NULL,
        `secure`            BOOL NOT NULL,
        `request_by`        VARCHAR(43) COLLATE latin1_general_ci,
        `request_by_type`   VARCHAR(32) COLLATE latin1_general_ci,
        `request_context`   VARCHAR(256) COLLATE utf8mb4_unicode_ci,
        `response_code`     INTEGER NOT NULL,
        `response_size`     INTEGER NOT NULL,
        `uploadable`        BOOL DEFAULT 1,
        `uploaded`          BOOL DEFAULT 0
        );""",

      # Defines the web interface session store. Used by the :class:`WebInterface` class to maintain session information
      """CREATE TABLE `web_sessions` (
        `id`                       CHAR(38) COLLATE latin1_general_cs NOT NULL,
        `user_id`                  CHAR(22) COLLATE latin1_general_cs,
        `auth_at`                  INTEGER UNSIGNED,
        `auth_data`                VARBINARY(5000),
        `refresh_token`            VARBINARY(500),
        `access_token`             VARBINARY(250),
        `refresh_token_expires_at` INTEGER UNSIGNED,
        `access_token_expires_at`  INTEGER UNSIGNED,
        `status`                   TINYINT UNSIGNED NOT NULL, /* disabled, enabled, deleted */
        `last_access_at`           INTEGER UNSIGNED NOT NULL,
        `expired_at`               INTEGER UNSIGNED,
        `created_at`               INTEGER UNSIGNED NOT NULL,
        `updated_at`               INTEGER UNSIGNED NOT NULL,
        PRIMARY KEY(id));""",
      sql_create_index("web_sessions", "last_access_at"),


      #########################
      ##      Triggers       ##
      #########################
      # Delete variable information for a device when a device is deleted.
      """CREATE TRIGGER delete_device_variable_data
         AFTER DELETE ON devices
         FOR EACH ROW
         BEGIN
           DELETE FROM variable_data WHERE variable_field_id = OLD.id and variable_field_id = "device";
         END""",

      # Delete variable information for a module when a module is deleted.
      """CREATE TRIGGER delete_module_variable_data
         AFTER DELETE ON modules
         FOR EACH ROW
         BEGIN
           DELETE FROM module_device_types WHERE module_id = OLD.id;
           /* DELETE FROM module_installed WHERE module_id = OLD.id; */
           DELETE FROM variable_data WHERE variable_field_id = OLD.id and variable_relation_type = "module";
         END""",

      # Delete variable fields when variable groups are removed.
      """CREATE TRIGGER delete_variablegroups_variable_fields
         AFTER DELETE ON variable_groups
         FOR EACH ROW
         BEGIN
           DELETE FROM variable_fields WHERE variable_group_id = OLD.id;
         END""",

      # If a variable field is deleted, delete it's matching data.
      """CREATE TRIGGER delete_variablefields_variable_data
         AFTER DELETE ON variable_fields
         FOR EACH ROW
         BEGIN
           DELETE FROM variable_data WHERE variable_field_id = OLD.id;
         END""",


      #########################
      ##        Views        ##
      #########################
      # Modules view helper.
      """CREATE VIEW modules_view AS
         SELECT modules.*, modules_installed.installed_branch, modules_installed.installed_commit,
         modules_installed.last_check_at, modules_installed. installed_at, modules_installed.last_check_at
         FROM modules LEFT OUTER JOIN modules_installed ON modules.id = modules_installed.module_id""",
]
