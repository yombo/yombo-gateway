"""
Handles system requests
"""
import os
import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import get_session


def route_system(webapp):
    with webapp.subroute("/system") as webapp:

        @webapp.route("/backup", methods=["GET"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_system_backup(webinterface, request, session):
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
            arguments = request.args
            session.is_allowed("system_options", "backup", "*")
            if "password1" in arguments:
                if "password2" not in arguments:
                    raise YomboWarning("Must supply password 2 if password 1 is supplied.")
                password1 = request.args.get("password1")[0]
                password2 = request.args.get("password2")[0]
                if password1 != password2:
                    raise YomboWarning(f"Backup encryption passwords do no match.")
                    # db_size = os.path.getsize(f"{webinterface._working_dir}/etc/yombo.sqlite3")
                    # page = webinterface.get_template(request, webinterface.wi_dir + "/pages/system/backup.html")
                    # return page.render(alerts=webinterface.get_alerts(),
                    #                    db_size=db_size
                    #                    )

            yombo_toml, yombo_meta_toml = webinterface._Configs.generate_yombo_toml()

            data_output = {
                "core": {
                    "aeskey": webinterface._GPG._GPG__aes_key,
                    "yombo_toml": yombo_toml,
                    "yombo_meta_toml": yombo_meta_toml,
                },
                "database:": {
                },
            }
            del yombo_toml
            del yombo_meta_toml

            # data_output["database"]["authkeys"] = webinterface._AuthKeys.to_database_all()
            # data_output["database"]["crontabs"] = webinterface._CronTab.to_database_all()
            # data_output["database"]["mqtt_users"] = webinterface._MQTTUsers.to_database_all()
            # data_output["database"]["permissions"] = webinterface._Permissions.to_database_all()
            # data_output["database"]["roles"] = webinterface._Roles.to_database_all()
            # data_output["database"]["sslcerts"] = webinterface._SSLCerts.to_database_all()
            # data_output["database"]["storage"] = webinterface._Storage.to_database_all()

            #data_output["database"]["user_access"] = webinterface._SSLCerts.to_database_all() Get FROM???

            if password1 is not None:
                encrypted_data_output = yield webinterface._Tools.data_pickle(data_output,
                                                                              "msgpack_aes256_zip_base85",
                                                                              passphrase=password1)
                encrypted = True
            else:
                # data_output_string = webinterface._Tools.data_pickle(data_output, "msgpack_zip")
                data_output_string = webinterface._Tools.data_pickle(data_output, "json")

            data_output_string = webinterface._Tools.data_pickle(data_output_string, "base85")
            final_out = {
                "gateway_label": webinterface._Configs.get("core.label"),
                "created": time.strftime("%c"),
                "file_type": "yombo configuration backup",
                "encrypted": encrypted,
                "time": int(time.time()),
                "backup_version": 3,
                "hash": webinterface._Hash.sha256_compact(data_output_string),
                "data": encrypted_data_output
            }

            request.setHeader("Content-Description", "File Transfer")
            request.setHeader("Content-Type", "application/octet-stream")
            request.setHeader("Content-Length", len(final_out))
            request.setHeader("Content-Disposition", "attachment; filename=yombo_backup.ybo")
            request.setHeader("Content-Transfer-Encoding", "binary")
            request.setHeader("Expires", "0")
            request.setHeader("Cache-Control", "must-revalidate, post-check=0, pre-check=0")
            request.setHeader("Pragma", "public")
            return final_out

        @webapp.route("/restart", methods=["GET"])
        @get_session(auth_required=True)
        def page_system_gateway_restart(webinterface, request, session):
            """
            Restart the gateway. Called be called by the route /system/restart

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            return webinterface.restart(request)

        @webapp.route("/shutdown", methods=["GET"])
        @get_session(auth_required=True)
        def page_system_gateway_shutdown(webinterface, request, session):
            """
            Shutdown the gateway.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            return webinterface.shutdown(request)
