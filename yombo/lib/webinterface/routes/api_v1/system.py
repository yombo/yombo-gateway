# Import python libraries
import os
from time import time

from yombo.constants import VERSION
from yombo.lib.webinterface.auth import require_auth
from yombo.utils import random_string


def route_api_v1_system(webapp):
    with webapp.subroute("/api/v1/system") as webapp:

        @webapp.route("/awake", methods=["GET"])
        def apiv1_system_awake(webinterface, request):
            """
            A non-authed method of checking if the system is fully booted and ready to go.
            """
            if webinterface.web_interface_fully_started is False:
                # print("auth get session: api request")
                return webinterface.render_api_error(request, None,
                                                     code="booting-other",
                                                     title="Still loading",
                                                     detail="Gateway is not ready to process API requests.",
                                                     response_code=503)

            request.setHeader("Access-Control-Allow-Origin", "*")
            return webinterface.render_api(request, None,
                                           data_type="system_awake",
                                           id=int(webinterface._Atoms["running_since"]),
                                           attributes={"id": int(webinterface._Atoms["running_since"])},
                                           )

        @webapp.route("/backup_info", methods=["GET"])
        @require_auth(api=True)
        def apiv1_system_backup_info(webinterface, request, session):
            """ Returns details about backing up the gateway. """
            has_access = session.has_access("system_options", "*", "backup")
            print(type(webinterface._Gateways.local_id))
            print(type(os.path.getsize(f"{webinterface.working_dir}/etc/yombo.sqlite3")))
            if has_access is False:
                return webinterface.render_api(request, session,
                                               data_type="backup_info",
                                               id=webinterface._Gateways.local_id,
                                               attributes={"access": False},
                                               )

            return webinterface.render_api(request, session,
                                           data_type="backup_info",
                                           id=webinterface._Gateways.local_id,
                                           attributes={
                                               "access": True,
                                               "db_size":
                                                   os.path.getsize(f"{webinterface.working_dir}/etc/yombo.sqlite3"),
                                            },
                                           )

        @webapp.route("/info", methods=["GET"])
        @require_auth(api=True)
        def apiv1_system_info(webinterface, request, session):
            """ Various details about the gateway. """
            gateway = webinterface._Gateways.local
            attributes = {**gateway.asdict(), **{
                             "gateway_id": str(webinterface._Gateways.local_id),
                             "operating_mode": str(webinterface._Loader.operating_mode)
                            }
                          }

            attributes["running_since"] = int(webinterface._Atoms["running_since"])
            attributes["uptime"] = int(time() - attributes["running_since"])
            attributes["version"] = VERSION
            return webinterface.render_api(request, session,
                                           data_type="system_info",
                                           id=gateway.gateway_id,
                                           attributes=attributes,
                                           )

        @webapp.route("/ping", methods=["GET"])
        @require_auth(api=True)
        def apiv1_system_tools_ping(webinterface, request, session):
            """
            Responds to a simple ping. This allows frontend client to judge how far away the gateway is.
            """
            try:
                request_id = request.args.get("id")[0]
            except Exception as e:
                request_id = random_string(length=12)

            return webinterface.render_api(request, session,
                                           data_type="system_ping",
                                           attributes={
                                               "id": request_id,
                                               "time": float(time()),
                                               }
                                           )

        @webapp.route("/uptime", methods=["GET"])
        @require_auth(api=True)
        def apiv1_system_status_uptime(webinterface, request, session):
            """ Returns the system uptime. """
            try:
                timeonly = str(request.args.get("timeonly")[0])
                if timeonly == "1":
                    return str(webinterface._Atoms["running_since"])
            except Exception as e:
                pass

            return webinterface.render_api(request, session,
                                           data_type="system_uptime",
                                           attributes={
                                               "start_time": str(webinterface._Atoms["running_since"])
                                               }
                                           )


