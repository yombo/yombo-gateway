"""
Handles various system API calls.
"""

# Import python libraries
import os
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.classes.jsonapi import JSONApi
from yombo.constants import VERSION
from yombo.constants.permissions import AUTH_PLATFORM_SYSTEM_OPTION
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import get_session
from yombo.utils import random_string
from yombo.lib.webinterface.routes.api_v1 import request_args


def route_api_v1_system(webapp):
    with webapp.subroute("/api/v1/system") as webapp:

        @webapp.route("/awake", methods=["GET"])
        @get_session(api=True)
        def apiv1_system_awake(webinterface, request, session):
            """
            A non-authed method of checking if the system is fully booted and ready to go.
            """
            return webinterface.render_api(request,
                                           data=JSONApi(data={
                                               "id": int(webinterface._Atoms["gateway.running_since"]),
                                               "type": "system_awake",
                                               "attributes": {
                                                   "id": int(webinterface._Atoms["gateway.running_since"]),
                                               }
                                           }),
                                           data_type="system_awake"
                                           )

        @webapp.route("/backup/configs", methods=["GET"])
        @get_session(api=True)
        @inlineCallbacks
        def apiv1_system_backup_configs(webinterface, request, session):
            """
            A non-authed method of checking if the system is fully booted and ready to go.
            """
            """
            Generate a backup file. The backup file should be encrypted since it contains all the secrets.

            Items included in the backup:
            Files:
                yombo.toml
                yombo.meta.toml
                aes key

            Database:
                authkeys
                crontabs
                mqttusers
                oauth_access_tokens (not implemented yet)
                permissions
                roles
                storage
                user_access

            """
            session.is_allowed("system_options", "backup", "*")
            arguments = request_args(webinterface, request)
            password1 = None
            if "password1" in arguments:
                if "password2" not in arguments:
                    raise YomboWarning("Missing password2, must be supplied with password1 to encrypt the data.",
                                       title="Error with supplied passwords")
                password1 = arguments["password1"]
                password2 = arguments["password2"]
                if password1 != password2:
                    raise YomboWarning("Backup encryption passwords do no match.",
                                       title="Error with supplied passwords")
            password_hint = None
            if "password_hint" in arguments:
                password_hint = arguments["password_hint"]

            # db_size = os.path.getsize(f"{webinterface._working_dir}/etc/yombo.sqlite3")

            yombo_toml, yombo_meta_toml = webinterface._Configs.generate_yombo_toml()

            backup_data = {
                "gateway_label": webinterface._Configs.get("core.label"),
                "created": round(time(), 3),
                "file_type": "Yombo configuration backup",
                "encrypted": None,
                "backup_version": 3,
                "hash": None,
                "password_hint": password_hint,
                "data": {
                    "aeskey": webinterface._Encryption._Encryption__aes_key,
                    "yombo_toml": yombo_toml,
                    "yombo_meta_toml": yombo_meta_toml,
                    "database": {
                    },
                }
            }

            del yombo_toml, yombo_meta_toml

            backup_data["data"]["database"]["authkeys"] = webinterface._AuthKeys.to_database_all()
            backup_data["data"]["database"]["crontabs"] = webinterface._CronTabs.to_database_all()
            backup_data["data"]["database"]["mqtt_users"] = webinterface._MQTTUsers.to_database_all()
            backup_data["data"]["database"]["permissions"] = webinterface._Permissions.to_database_all()
            backup_data["data"]["database"]["roles"] = webinterface._Roles.to_database_all()
            # backup_data["data"]["database"]["storage"] = webinterface._Storage.to_database_all()
            # backup_data["data"]["database"]["user_access"] = webinterface._SSLCerts.to_database_all() Get FROM???

            if password1 is not None:
                backup_data["encrypted"] = True
                backup_data["data"] = yield webinterface._Tools.data_pickle(backup_data["data"],
                                                                            "msgpack_aes256_zip_base85",
                                                                            passphrase=password1)
            else:
                backup_data["encrypted"] = False
                backup_data["data"] = webinterface._Tools.data_pickle(backup_data["data"], "msgpack_zip_base85")

            backup_data["hash"] = webinterface._Hash.sha256_compact(backup_data["data"])

            output = webinterface._Tools.data_pickle(backup_data, "json")
            request.setHeader("Content-Description", "File Transfer")
            request.setHeader("Content-Type", "application/octet-stream")
            request.setHeader("Content-Disposition", "attachment; filename=yombo_backup.ybo")
            request.setHeader("Content-Transfer-Encoding", "binary")
            request.setHeader("Expires", "0")
            request.setHeader("Cache-Control", "must-revalidate, post-check=0, pre-check=0")
            request.setHeader("Pragma", "no-cache")
            return output

        @webapp.route("/backup_info", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_system_backup_info(webinterface, request, session):
            """ Returns details about backing up the gateway. """
            session.is_allowed(AUTH_PLATFORM_SYSTEM_OPTION, "backup")
            return webinterface.render_api(request,
                                           data=JSONApi(data={
                                               "id": webinterface._gateway_id,
                                               "type": "system_awake",
                                               "attributes": {
                                                   "id": webinterface._gateway_id,
                                                   "db_size":
                                                       os.path.getsize(f"{webinterface._working_dir}/etc/yombo.sqlite3"),
                                               }
                                           }),
                                           data_type="system_awake",
                                           )

        @webapp.route("/info", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_system_info(webinterface, request, session):
            """ Various details about the gateway. """
            session.is_allowed(AUTH_PLATFORM_SYSTEM_OPTION, "backup")
            gateway = webinterface._Gateways.local
            attributes = {**gateway.to_dict(include_meta=False),
                          **{
                             "gateway_id": str(gateway.gateway_id),
                             "operating_mode": str(webinterface._Loader.operating_mode)
                            }
                          }
            attributes["running_since"] = int(webinterface._Atoms["gateway.running_since"])
            attributes["uptime"] = int(webinterface._States["gateway.uptime"])
            attributes["version"] = VERSION
            attributes["id"] = gateway.gateway_id
            return webinterface.render_api(request,
                                           data=JSONApi(data={
                                               "id": gateway.gateway_id,
                                               "type": "system_info",
                                               "attributes": attributes,
                                               }),
                                           data_type="system_info",
                                           )

        @webapp.route("/ping", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_system_tools_ping(webinterface, request, session):
            """
            Responds to a simple ping. This allows frontend client to judge how far away the gateway is.
            """
            try:
                request_id = request.args.get("id")[0]
            except Exception as e:
                request_id = random_string(length=12)

            return webinterface.render_api(request,
                                           data=JSONApi(data={
                                               "id": request_id,
                                               "type": "system_ping",
                                               "attributes": {
                                                   "id": request_id,
                                                   "time": float(time()),
                                                   },
                                               }),
                                           data_type="system_ping",
                                           )

        @webapp.route("/uptime", methods=["GET"])
        @get_session(auth_required=True, api=True)
        def apiv1_system_status_uptime(webinterface, request, session):
            """ Returns the system uptime. """
            try:
                timeonly = str(request.args.get("timeonly")[0])
                if timeonly == "1":
                    return str(webinterface._Atoms["gateway.running_since"])
            except Exception as e:
                pass

            return webinterface.render_api(request,
                                           data=JSONApi(data={
                                               "id": str(webinterface._Atoms["gateway.running_since"]),
                                               "type": "system_uptime",
                                               "attributes": {
                                                   "id": str(webinterface._Atoms["gateway.running_since"]),
                                                   "time": float(time()),
                                                   },
                                               }),
                                           data_type="system_uptime",
                                           )


