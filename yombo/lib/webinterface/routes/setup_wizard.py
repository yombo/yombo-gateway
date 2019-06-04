# from collections import OrderedDict
from urllib.parse import urlencode

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth, run_first
from yombo.utils import is_true_false, unicode_to_bytes, bytes_to_unicode, save_file
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.setup_wizard")


def route_setup_wizard(webapp):
    with webapp.subroute("/setup_wizard") as webapp:

        # def page_show_wizard_home(webinterface, request, session):
        #     page = webinterface.get_template(request, webinterface.wi_dir + "/pages/setup_wizard/basic_settings.html")
        #     return webinterface.render(request, session, webinterface.wi_dir + "/pages/setup_wizard/basic_settings.html")

        @webapp.route("/", methods=["GET"])
        def page_setup_wizard_home(webinterface, request, session):
            return webinterface.redirect(request, f"/setup_wizard/select_gateway?{urlencode(request.args)}")

        @webapp.route("/select_gateway")
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_select_gateway(webinterface, request, session):
            if session.get("setup_wizard_done", False) is True:
                return webinterface.redirect(request, f"/setup_wizard/{session['setup_wizard_last_step']}")
            session.set("setup_wizard_last_step", "select_gateway")

            try:
                auth_header = yield session.authorization_header(request)
                response = yield webinterface._YomboAPI.request("GET",
                                                                "/v1/gateways",
                                                                authorization_header=auth_header)

            except YomboWarning as e:
                logger.warn("Unable to get list of gateways: {e}", e=e)
                for error in e.errors:
                    print(f"Error: {error}")
                    session.add_alert(f"Unable to get list of gateways, Yombo API responded with: ({error['code']}) {error['title']} - {error['detail']}", "warning")
                return webinterface.redirect(request, "/")
            available_gateways = {}

            data = response.content["data"]

            for item in data:
                gateway = item["attributes"]
                available_gateways[gateway["id"]] = gateway

            available_gateways_sorted = dict(sorted(available_gateways.items(), key=lambda x: x[1]["label"]))
            session.set("available_gateways", available_gateways_sorted)

            session["setup_wizard_last_step"] = "select_gateway"
            return webinterface.render(request, session,
                                       webinterface.wi_dir + "/pages/setup_wizard/select_gateway.html",
                                       available_gateways=available_gateways_sorted,
                                       selected_gateway=session.get("setup_wizard_gateway_id", "new"),
                                       )

        @webapp.route("/basic_settings", methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_basic_settings_get(webinterface, request, session):
            if session.get("setup_wizard_done", False) is True:
                return webinterface.redirect(request, f"/setup_wizard/{session['setup_wizard_last_step']}")
            if session.get("setup_wizard_last_step", "select_gateway") not in ("select_gateway", "basic_settings", "advanced_settings"):
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            available_gateways = session.get("available_gateways", None)

            if available_gateways == None:
                session.add_alert("Selected gateway ID not found. Try again. (Error: 01)")
                session["setup_wizard_last_step"] = "basic_settings"
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            if "setup_wizard_gateway_id" not in session:
                session.add_alert("Selected gateway ID not found. Try again. (Error: 02)")
                session["setup_wizard_last_step"] = "basic_settings"
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            if session["setup_wizard_gateway_id"] != "new" and session["setup_wizard_gateway_id"] not in available_gateways:
                session.add_alert("Selected gateway not found. Try again. (Error: 04)")
                session["setup_wizard_last_step"] = "basic_settings"
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            output = yield page_setup_wizard_basic_settings_show_form(webinterface, request, session["setup_wizard_gateway_id"],
                                                         available_gateways, session)
            return output

        @webapp.route("/basic_settings", methods=["POST"])
        @require_auth()
        def page_setup_wizard_basic_settings_post(webinterface, request, session):
            if session.get("setup_wizard_done", False) is True:
                return webinterface.redirect(request, f"/setup_wizard/{session['setup_wizard_last_step']}")
            if session.get("setup_wizard_last_step", "basic_settings") not in ("select_gateway", "basic_settings", "advanced_settings"):
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            valid_submit = True
            try:
                submitted_gateway_id = request.args.get("gateway-id")[0]
            except:
                if "setup_wizard_gateway_id" not in session:
                    session.add_alert("Selected gateway ID not found. Try again. (Error: 02)")
                    session["setup_wizard_last_step"] = "basic_settings"
                    return webinterface.redirect(request, "/setup_wizard/select_gateway")
                submitted_gateway_id = session["setup_wizard_gateway_id"]

            if submitted_gateway_id == "" or valid_submit is False:
                session.add_alert("Invalid gateway selected. Try again.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            available_gateways = session.get("available_gateways")

            if submitted_gateway_id not in available_gateways and submitted_gateway_id != "new":
                session.add_alert("Selected gateway not found. Try again.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            output = page_setup_wizard_basic_settings_show_form(webinterface, request, submitted_gateway_id,
                                                                available_gateways, session)
            return output

        def page_setup_wizard_basic_settings_show_form(webinterface, request, wizard_gateway_id, available_gateways, session):
            settings = {}
            if "location" not in settings:
                settings["location"] = {}

            if "setup_wizard_gateway_location_search" in session:
                settings["location"]["location_search"] = {"data": session["setup_wizard_gateway_location_search"]}
            else:
                if "latitude" not in settings["location"]:
                    default_search = f"{webinterface._Configs.detected_location_info['city']}, " \
                                     f"{webinterface._Configs.detected_location_info['region_code']} " \
                                     f"{str(webinterface._Configs.detected_location_info['zip_code'])}, " \
                                     f"{str(webinterface._Configs.detected_location_info['country_code'])}"
                    settings["location"]["location_search"] = {"data": default_search}

            if "setup_wizard_gateway_latitude" in session:
                settings["location"]["latitude"] = {"data": str(session["setup_wizard_gateway_latitude"])}
            else:
                if "latitude" not in settings["location"]:
                    settings["location"]["latitude"] = \
                        {"data": str(webinterface._Configs.detected_location_info["latitude"])}

            if "setup_wizard_gateway_longitude" in session:
                settings["location"]["longitude"] = \
                    {"data": session["setup_wizard_gateway_longitude"]}
            else:
                if "longitude" not in settings["location"]:
                    settings["location"]["longitude"] = \
                        {"data": str(webinterface._Configs.detected_location_info["longitude"])}

            if "setup_wizard_gateway_elevation" in session:
                settings["location"]["elevation"] = {"data": session["setup_wizard_gateway_elevation"]}
            else:
                if "elevation" not in settings["location"]:
                    settings["location"]["elevation"] = \
                        {"data": str(webinterface._Configs.detected_location_info["elevation"])}

            if "times" not in settings:
                settings["times"] = {}
            if "twilighthorizon" not in settings["times"]:
                settings["times"]["twilighthorizon"] = {"data": "-6"}

            if "setup_wizard_gateway_id" not in session or session["setup_wizard_gateway_id"] != wizard_gateway_id:
                session["setup_wizard_gateway_id"] = wizard_gateway_id
                if session["setup_wizard_gateway_id"] == "new":
                    session["setup_wizard_gateway_machine_label"] = ""
                    session["setup_wizard_gateway_label"] = ""
                    session["setup_wizard_gateway_description"] = ""
                else:
                    session["setup_wizard_gateway_machine_label"] = available_gateways[wizard_gateway_id]["machine_label"]
                    session["setup_wizard_gateway_label"] = available_gateways[wizard_gateway_id]["label"]
                    session["setup_wizard_gateway_description"] = available_gateways[wizard_gateway_id]["description"]
            fields = {
                  "id": session["setup_wizard_gateway_id"],
                  "machine_label": session["setup_wizard_gateway_machine_label"],
                  "label": session["setup_wizard_gateway_label"],
                  "description": session["setup_wizard_gateway_description"],
            }

            session["setup_wizard_last_step"] = "basic_settings"
            return webinterface.render(request, session,
                                       webinterface.wi_dir + "/pages/setup_wizard/basic_settings.html",
                                       gw_fields=fields,
                                       settings=settings,
                                       )

        @webapp.route("/advanced_settings", methods=["GET"])
        @require_auth()
        def page_setup_wizard_advanced_settings_get(webinterface, request, session):
            if session.get("setup_wizard_done", False) is True:
                return webinterface.redirect(request, f"/setup_wizard/{session['setup_wizard_last_step']}")
            if session.get("setup_wizard_last_step", 1) not in ("basic_settings", "advanced_settings"):
                session.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            return page_setup_wizard_advanced_settings_show_form(webinterface, request, session)

        @webapp.route("/advanced_settings", methods=["POST"])
        @require_auth()
        def page_setup_wizard_advanced_settings_post(webinterface, request, session):
            if session.get("setup_wizard_done", False) is True:
                return webinterface.redirect(request, f"/setup_wizard/{session['setup_wizard_last_step']}")
            if session.get("setup_wizard_last_step", "advanced_settings") not in ("basic_settings", "advanced_settings"):
                session.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            valid_submit = True
            try:
                submitted_gateway_location_search = request.args.get("location_search")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Location Search.")

            try:
                submitted_gateway_label = request.args.get("gateway_label")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Label.")

            try:
                submitted_gateway_machine_label = request.args.get("gateway_machine_label")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Machine Label.")

            # Validate we have unique gateway label and machine_label:
            available_gateways = session.get("available_gateways", None)
            submitted_gateway_id = session["setup_wizard_gateway_id"]
            for gateway_id, gateway in available_gateways.items():
                if gateway_id == submitted_gateway_id:
                    continue
                if gateway['label'].lower() == submitted_gateway_label.lower():
                    valid_submit = False
                    session.add_alert("There's already a gateway with this label.")
                if gateway['machine_label'].lower() == submitted_gateway_machine_label.lower():
                    valid_submit = False
                    session.add_alert("There's already a gateway with this machine label.")

            try:
                submitted_gateway_description = request.args.get("gateway_description")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Description.")

            try:
                submitted_gateway_latitude = request.args.get("location_latitude")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Latitude.")

            try:
                submitted_gateway_longitude = request.args.get("location_longitude")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Longitude.")

            try:
                submitted_gateway_elevation = request.args.get("location_elevation")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Elevation.")

            if valid_submit is False:
                return webinterface.redirect(request, f"/setup_wizard/basic_settings")

            session["setup_wizard_gateway_machine_label"] = submitted_gateway_machine_label
            session["setup_wizard_gateway_label"] = submitted_gateway_label
            session["setup_wizard_gateway_description"] = submitted_gateway_description
            session["setup_wizard_gateway_location_search"] = submitted_gateway_location_search
            session["setup_wizard_gateway_latitude"] = submitted_gateway_latitude
            session["setup_wizard_gateway_longitude"] = submitted_gateway_longitude
            session["setup_wizard_gateway_elevation"] = submitted_gateway_elevation

            return page_setup_wizard_advanced_settings_show_form(webinterface, request, session)

        def page_setup_wizard_advanced_settings_show_form(webinterface, request, session):
            if "setup_wizard_gateway_is_master" in session and\
                            "setup_wizard_gateway_master_gateway_id" in session:
                is_master = session["setup_wizard_gateway_is_master"]
                master_gateway_id = session["setup_wizard_gateway_master_gateway_id"]
            else:
                available_gateways = session.get("available_gateways")
                if session["setup_wizard_gateway_id"] in available_gateways:
                    gw = available_gateways[session["setup_wizard_gateway_id"]]
                    is_master = gw["is_master"]
                    master_gateway_id = gw["master_gateway_id"]  # api just has master_gateway
                else:
                    is_master = 1
                    master_gateway_id = None

            security_items = {
                "is_master": is_master,
                "master_gateway_id": master_gateway_id,
                "status": session.get("setup_wizard_security_status", "1"),
                "send_private_stats": session.get("setup_wizard_security_send_private_stats", "1"),
                "send_anon_stats": session.get("setup_wizard_security_send_anon_stats", "1"),
                }

            session["setup_wizard_last_step"] = "advanced_settings"
            return webinterface.render(request, session,
                                       webinterface.wi_dir + "/pages/setup_wizard/advanced_settings.html",
                                       security_items=security_items,
                                       available_gateways=session.get("available_gateways"),
                                       )

        @webapp.route("/dns", methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_dns_get(webinterface, request, session):
            if session.get("setup_wizard_last_step", 1) not in ("advanced_settings", "dns", "finished"):
                session.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            session["setup_wizard_last_step"] = "dns"
            results = yield form_setup_wizard_dns(webinterface, request, session)
            return results

        @webapp.route("/dns", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_dns_post(webinterface, request, session):
            """
            Last step is to handle the DNS hostname.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            if session.get("setup_wizard_last_step", 1) not in ("advanced_settings", "dns", "finished"):
                session.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            valid_submit = True
            try:
                submitted_gateway_master_gateway_id = request.args.get("master-gateway-id")[0]
                if submitted_gateway_master_gateway_id == "local":
                    submitted_gateway_is_master = 1
                    submitted_gateway_master_gateway_id = None
                else:
                    submitted_gateway_is_master = 0
            except:
                valid_submit = False
                session.add_alert("Invalid Master Gateway.")

            try:
                submitted_security_status = request.args.get("security-status")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid Gateway Device Send Status.")

            if valid_submit is False:
                return webinterface.redirect(request, "/setup_wizard/advanced_settings")

            try:
                submitted_security_send_private_stats = request.args.get("security-send-private-stats")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid send private stats.")

            if valid_submit is False:
                return webinterface.redirect(request, "/setup_wizard/advanced_settings")

            try:
                submitted_security_send_anon_stats = request.args.get("security-send-anon-stats")[0]
            except:
                valid_submit = False
                session.add_alert("Invalid send anonymous statistics.")

            if valid_submit is False:
                return webinterface.redirect(request, "/setup_wizard/advanced_settings")

            session["setup_wizard_gateway_is_master"] = submitted_gateway_is_master
            session["setup_wizard_gateway_master_gateway_id"] = submitted_gateway_master_gateway_id
            session["setup_wizard_security_status"] = submitted_security_status
            session["setup_wizard_security_send_private_stats"] = submitted_security_send_private_stats
            session["setup_wizard_security_send_anon_stats"] = submitted_security_send_anon_stats

            auth_header = yield session.authorization_header(request)
            if session["setup_wizard_gateway_id"] == "new":
                data = {
                    "machine_label": session["setup_wizard_gateway_machine_label"],
                    "label": session["setup_wizard_gateway_label"],
                    "description": session["setup_wizard_gateway_description"],
                    "is_master": session["setup_wizard_gateway_is_master"],
                    "status": 1
                }
                if session["setup_wizard_gateway_master_gateway_id"] is not None:
                    data["master_gateway"] = session["setup_wizard_gateway_master_gateway_id"],

                try:
                    response = yield webinterface._YomboAPI.request("POST", "/v1/gateways",
                                                                    data,
                                                                    authorization_header=auth_header)
                except YomboWarning as e:
                    for error in e.errors:
                        session.add_alert(
                            f"Unable to add gateway, Yombo API responded with: ({error['code']}) {error['title']} - "
                            f"{error['detail']}",
                            "warning")
                    return webinterface.redirect(request, "/setup_wizard/basic_settings")
                # print(f"response.content: {response.content}")
                session["setup_wizard_gateway_id"] = response.content["data"]["attributes"]

            else:
                data = {
                    "label": session["setup_wizard_gateway_label"],
                    "description": session["setup_wizard_gateway_description"],
                }
                try:
                    response = yield webinterface._YomboAPI.request(
                        "PATCH", f"/v1/gateways/{session['setup_wizard_gateway_id']}",
                        data,
                        authorization_header=auth_header)
                except YomboWarning as e:
                    for error in e.errors:
                        session.add_alert(
                            f"Unable to setup gateway, Yombo API responded with: ({error['code']}) {error['title']} -"
                            f" {error['detail']}",
                            "warning")
                        return webinterface.redirect(request, "/setup_wizard/dns")

                try:
                    response = yield webinterface._YomboAPI.request(
                        "GET", f"/v1/gateways/{session['setup_wizard_gateway_id']}/reset_authentication",
                        authorization_header=auth_header)
                except YomboWarning as e:
                    for error in e.errors:
                        session.add_alert(
                            f"Unable to setup gateway, Yombo API responded with: ({error['code']}) {error['title']} -"
                            f" {error['detail']}",
                            "warning")
                        return webinterface.redirect(request, "/setup_wizard/dns")


            new_auth = response.content["data"]["attributes"]
            webinterface._Configs.set("core", "gwid", new_auth["id"])
            webinterface._Configs.set("core", "gwuuid", new_auth["uuid"])
            webinterface._Configs.set("core", "machine_label", session["setup_wizard_gateway_machine_label"])
            webinterface._Configs.set("core", "label", session["setup_wizard_gateway_label"])
            webinterface._Configs.set("core", "description", session["setup_wizard_gateway_description"])
            webinterface._Configs.set("core", "gwhash", new_auth["hash"])
            webinterface._Configs.set("core", "is_master", is_true_false(session["setup_wizard_gateway_is_master"]))
            webinterface._Configs.set("core", "master_gateway_id", session["setup_wizard_gateway_master_gateway_id"])
            webinterface._Configs.set("security", "amqpsenddevicestatus", session["setup_wizard_security_status"])
            webinterface._Configs.set("security", "amqpsendprivatestats", session["setup_wizard_security_send_private_stats"])
            webinterface._Configs.set("security", "amqpsendanonstats", session["setup_wizard_security_send_anon_stats"])
            webinterface._Configs.set("location", "latitude", session["setup_wizard_gateway_latitude"])
            webinterface._Configs.set("location", "longitude", session["setup_wizard_gateway_longitude"])
            webinterface._Configs.set("location", "elevation", session["setup_wizard_gateway_elevation"])
            webinterface._Configs.set("core", "first_run", False)

            # Remove wizard settings...
            for session_key in list(session.keys()):
                if session_key.startswith("setup_wizard_"):
                    del session[session_key]
            session["setup_wizard_done"] = True
            session["setup_wizard_last_step"] = "finished"

            logger.info("New gpg key will be generated on next restart.")

            session["setup_wizard_last_step"] = "dns"

            results = yield form_setup_wizard_dns(webinterface, request, session)
            return results

        @inlineCallbacks
        def form_setup_wizard_dns(webinterface, request, session):
            try:
                auth_header = yield session.authorization_header(request)
                response = yield webinterface._YomboAPI.request(
                    "GET",
                    f"/v1/gateways/{webinterface._Configs.get('core', 'gwid')}/dns",
                    authorization_header=auth_header)
            except YomboWarning as e:
                response = e.meta
                webinterface._Configs.set("dns", "name", None)
                webinterface._Configs.set("dns", "domain", None)
                webinterface._Configs.set("dns", "domain_id", None)
                webinterface._Configs.set("dns", "allow_change_at", 0)
                webinterface._Configs.set("dns", "fqdn", None)
                if response.response_code != 404:
                    for error in e.errors:
                        session.add_alert(
                            f"Unable to setup gateway DNS, Yombo API responded with: ({error['code']}) {error['title']} -"
                            f" {error['detail']}",
                            "warning")
                    return webinterface.redirect(request, "/setup_wizard/dns")
            else:
                dns_data = response.content["data"]["attributes"]
                webinterface._Configs.set("dns", "name", dns_data["name"])
                webinterface._Configs.set("dns", "domain", dns_data["domain"])
                webinterface._Configs.set("dns", "domain_id", dns_data["dns_domain_id"])
                webinterface._Configs.set("dns", "allow_change_at", dns_data["allow_change_at"])
                webinterface._Configs.set("dns", "fqdn", f'{dns_data["name"]}.{dns_data["domain"]}')

            dns_fqdn = webinterface._Configs.get("dns", "fqdn", None)
            dns_name = webinterface._Configs.get("dns", "dns_name", None)
            dns_domain = webinterface._Configs.get("dns", "dns_domain", None)
            allow_change = webinterface._Configs.get("dns", "allow_change_at", 0)
            return webinterface.render(request, session,
                                       webinterface.wi_dir + "/pages/setup_wizard/dns.html",
                                       dns_fqdn=dns_fqdn,
                                       dns_name=dns_name,
                                       dns_domain=dns_domain,
                                       allow_change=allow_change,
                                       )

        @webapp.route("/finished", methods=["GET"])
        @require_auth()
        def page_setup_wizard_finished_get(webinterface, request, session):
            session["setup_wizard_last_step"] = "finished"
            return webinterface.render(request, session,
                                       webinterface.wi_dir + "/pages/setup_wizard/finished.html",
                                       )

        @webapp.route("/finished", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_finished_post(webinterface, request, session):
            """
            Last step is to handle the DNS. Either create a new one, skip, or edit existing.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            try:
                submitted_dns_name = request.args.get("dns_name")[0]  # underscore here due to jquery
            except:
                session.add_alert("Select a valid dns name.")
                return webinterface.redirect(request, "/setup_wizard/dns")

            try:
                submitted_dns_domain = request.args.get("dns_domain_id")[0]  # underscore here due to jquery
            except:
                session.add_alert("Select a valid dns domain.")
                return webinterface.redirect(request, "/setup_wizard/dns")

            data = {
                "dns_name": submitted_dns_name,
                "dns_domain_id": submitted_dns_domain,
            }

            try:
                dns_results = yield webinterface._YomboAPI.request(
                    "POST",
                    f"/v1/gateways/{webinterface._Configs.get('core', 'gwid')}/dns",
                    data,
                    session=session["yomboapi_session"])
            except YomboWarning as e:
                for error in e.errors:
                    session.add_alert(
                        f"Unable to setup gateway DNS, Yombo API responded with: ({error['code']}) {error['title']} -"
                        f" {error['detail']}",
                        "warning")
                return webinterface.redirect(request, "pages/setup_wizard/dns")

            session["setup_wizard_last_step"] = "finished"

            return webinterface.render(request, session,
                                       webinterface.wi_dir + "/pages/setup_wizard/finished.html",
                                       )

        @webapp.route("/finished_restart", methods=["GET"])
        @require_auth()
        def page_setup_wizard_finished_restart(webinterface, request, session):
            webinterface._Configs.set("core", "first_run", False)
            return webinterface.restart(request)
