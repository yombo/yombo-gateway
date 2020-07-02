"""

This handles the gateway initial configuration. These routes are only enabled when the gateway
is being bootstrapped.

.. versionadded:: 0.19.0
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/modules.html>`_
"""
from urllib.parse import urlencode

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import get_session
from yombo.utils import is_true_false
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.setup_wizard")


def route_setup_wizard(webapp):
    with webapp.subroute("/setup_wizard") as webapp:

        @webapp.route("/", methods=["GET"])
        def page_setup_wizard_home(webinterface, request, session):
            """ Catches routes to the root setup wizard directory. """
            return webinterface.redirect(request, f"/setup_wizard/start?{urlencode(request.args)}")

        @webapp.route("/start")
        @get_session(auth_required=True)
        def page_setup_wizard_start(webinterface, request, session):
            """
            Displayed when the gateway is new and needs to be installed. Presents the user with the option
            to run the setup wizard or restore a configuration file backup.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            return webinterface.render_template(request, webinterface.wi_dir + "/pages/setup_wizard/start.html")

        @webapp.route("/select_gateway")
        @get_session(auth_required=True)
        @inlineCallbacks
        def page_setup_wizard_select_gateway(webinterface, request, session):
            """ Prompts the user to setup a new gateway or recover an existing gateway. """
            if session.get("setup_wizard_done", False) is True:
                return webinterface.redirect(request, f"/setup_wizard/{session['setup_wizard_last_step']}")
            session["setup_wizard_last_step"] = "select_gateway"

            try:
                auth_header = yield session.authorization_header(request)
                response = yield webinterface._YomboAPI.request("GET",
                                                                "/v1/gateways",
                                                                authorization_header=auth_header)
            except YomboWarning as e:
                logger.warn("Unable to get list of gateways: {e}", e=e)
                for error in e.errors:
                    session.add_alert(f"Unable to get list of gateways, Yombo API responded with: ({error['code']}) {error['title']} - {error['detail']}", "warning")
                return webinterface.redirect(request, "/")

            available_gateways = {}
            data = response.content["data"]

            for item in data:
                gateway = item["attributes"]
                available_gateways[gateway["id"]] = gateway

            available_gateways_sorted = dict(sorted(available_gateways.items(), key=lambda x: x[1]["label"].lower()))
            session.set("available_gateways", available_gateways_sorted)

            return webinterface.render_template(request,
                                                webinterface.wi_dir + "/pages/setup_wizard/select_gateway.html",
                                                available_gateways=available_gateways_sorted,
                                                selected_gateway=session.get("setup_wizard_gateway_id", "new"),
                                                )

        @webapp.route("/basic_settings", methods=["GET"])
        @get_session(auth_required=True)
        @inlineCallbacks
        def page_setup_wizard_basic_settings_get(webinterface, request, session):
            """ Get the basic settings. Only used if the user does something weird or clicks back. """
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

            if session["setup_wizard_gateway_id"] != "new" and \
                    session["setup_wizard_gateway_id"] not in available_gateways:
                session.add_alert("Selected gateway not found. Try again. (Error: 04)")
                session["setup_wizard_last_step"] = "basic_settings"
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            output = yield page_setup_wizard_basic_settings_show_form(webinterface,
                                                                      request,
                                                                      session["setup_wizard_gateway_id"],
                                                                      available_gateways,
                                                                      session)
            return output

        @webapp.route("/basic_settings", methods=["POST"])
        @get_session(auth_required=True)
        def page_setup_wizard_basic_settings_post(webinterface, request, session):
            """ Receives selected gateway, and then displays basic settings. """
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

        def page_setup_wizard_basic_settings_show_form(webinterface, request, wizard_gateway_id, available_gateways,
                                                       session):
            """ Shows the form for basic settings. """
            settings = {}
            if "location" not in settings:
                settings["location"] = {}

            if "setup_wizard_gateway_location_search" in session:
                settings["location"]["location_search"] = {"data": session["setup_wizard_gateway_location_search"]}
            else:
                if "latitude" not in settings["location"]:
                    default_search = f"{webinterface._Configs.detected_location_info['city']}, " \
                                     f"{webinterface._Configs.detected_location_info['region_name']} " \
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
            return webinterface.render_template(request,
                webinterface.wi_dir + "/pages/setup_wizard/basic_settings.html",
                gw_fields=fields,
                settings=settings,
                setup_wizard_map_js=webinterface.setup_wizard_map_js
                )

        @webapp.route("/advanced_settings", methods=["GET"])
        @get_session(auth_required=True)
        def page_setup_wizard_advanced_settings_get(webinterface, request, session):
            """ Gets the advanced settings pages. Only used if the user does something weird or they click
            the back button. """
            if session.get("setup_wizard_done", False) is True:
                return webinterface.redirect(request, f"/setup_wizard/{session['setup_wizard_last_step']}")
            if session.get("setup_wizard_last_step", 1) not in ("basic_settings", "advanced_settings"):
                session.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            return page_setup_wizard_advanced_settings_show_form(webinterface, request, session)

        @webapp.route("/advanced_settings", methods=["POST"])
        @get_session(auth_required=True)
        def page_setup_wizard_advanced_settings_post(webinterface, request, session):
            """ Receives the basic settings form and displays the advanced settings form. """
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
            """ Displays the advanced settings form. """
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
                "status": session.get("setup_wizard_security_send_device_states", "1"),
                "send_private_stats": session.get("setup_wizard_security_send_private_stats", "1"),
                "send_anon_stats": session.get("setup_wizard_security_send_anon_stats", "1"),
                }

            session["setup_wizard_last_step"] = "advanced_settings"
            return webinterface.render_template(request,
                                                webinterface.wi_dir + "/pages/setup_wizard/advanced_settings.html",
                                                security_items=security_items,
                                                available_gateways=session.get("available_gateways")
                                                )

        @webapp.route("/dns", methods=["GET"])
        @get_session(auth_required=True)
        @inlineCallbacks
        def page_setup_wizard_dns_get(webinterface, request, session):
            """ Gets the DNS settings pages. Only used if the user does something weird or they click
            the back button. """
            if session.get("setup_wizard_last_step", 1) not in ("advanced_settings", "dns", "finished"):
                session.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, "/setup_wizard/select_gateway")

            session["setup_wizard_last_step"] = "dns"
            results = yield form_setup_wizard_dns(webinterface, request, session)
            return results

        @webapp.route("/dns", methods=["POST"])
        @get_session(auth_required=True)
        @inlineCallbacks
        def page_setup_wizard_dns_post(webinterface, request, session):
            """
            Receives the advanced settings form and displays the DNS form.

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
                submitted_security_send_device_states = request.args.get("security-send-device-states")[0]
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
            session["setup_wizard_security_send_device_states"] = submitted_security_send_device_states
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
                    response = yield webinterface._YomboAPI.request("POST",
                                                                    "/v1/gateways",
                                                                    body=data,
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
                        "PATCH",
                        f"/v1/gateways/{session['setup_wizard_gateway_id']}",
                        body=data,
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
                        "GET",
                        f"/v1/gateways/{session['setup_wizard_gateway_id']}/reset_authentication",
                        authorization_header=auth_header)
                except YomboWarning as e:
                    for error in e.errors:
                        session.add_alert(
                            f"Unable to setup gateway, Yombo API responded with: ({error['code']}) {error['title']} -"
                            f" {error['detail']}",
                            "warning")
                        return webinterface.redirect(request, "/setup_wizard/dns")

            new_auth = response.content["data"]["attributes"]
            webinterface._Configs.set("core.gwid", new_auth["id"], ref_source=webinterface)
            webinterface._Configs.set("core.oauth_secret", new_auth["oauth_secret"], ref_source=webinterface)
            webinterface._Configs.set("core.gwhash", new_auth["hash"], ref_source=webinterface)
            webinterface._Configs.set("core.machine_label", session["setup_wizard_gateway_machine_label"],
                                      ref_source=webinterface)
            webinterface._Configs.set("core.label", session["setup_wizard_gateway_label"], ref_source=webinterface)
            webinterface._Configs.set("core.description", session["setup_wizard_gateway_description"],
                                      ref_source=webinterface)
            webinterface._Configs.set("core.is_master", is_true_false(session["setup_wizard_gateway_is_master"]),
                                      ref_source=webinterface)
            webinterface._Configs.set("core.master_gateway_id", session["setup_wizard_gateway_master_gateway_id"],
                                      ref_source=webinterface)
            webinterface._Configs.set("security.amqp.send_device_states",
                                      is_true_false(session["setup_wizard_security_send_device_states"]),
                                      ref_source=webinterface)
            webinterface._Configs.set("security.amqp.send_private_stats",
                                      is_true_false(session["setup_wizard_security_send_private_stats"]),
                                      ref_source=webinterface)
            webinterface._Configs.set("security.amqp.send_anon_stats",
                                      is_true_false(session["setup_wizard_security_send_anon_stats"]),
                                      ref_source=webinterface)
            webinterface._Configs.set("location.latitude", session["setup_wizard_gateway_latitude"],
                                      ref_source=webinterface)
            webinterface._Configs.set("location.longitude", session["setup_wizard_gateway_longitude"],
                                      ref_source=webinterface)
            webinterface._Configs.set("location.elevation", session["setup_wizard_gateway_elevation"],
                                      ref_source=webinterface)
            webinterface._Configs.set("core.first_run", False, ref_source=webinterface)

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
            """ Displays teh DNS form. """
            try:
                auth_header = yield session.authorization_header(request)
                response = yield webinterface._YomboAPI.request(
                    "GET",
                    f"/v1/gateways/{webinterface._Configs.get('core.gwid')}/dns",
                    authorization_header=auth_header)
            except YomboWarning as e:
                response = e.meta
                webinterface._Configs.set("dns.name", None, ref_source=webinterface)
                webinterface._Configs.set("dns.domain", None, ref_source=webinterface)
                webinterface._Configs.set("dns.domain_id", None, ref_source=webinterface)
                webinterface._Configs.set("dns.allow_change_at", 0, ref_source=webinterface)
                webinterface._Configs.set("dns.fqdn", None, ref_source=webinterface)
                if response.response_code != 404:
                    for error in e.errors:
                        session.add_alert(
                            f"Unable to setup gateway DNS, Yombo API responded with: ({error['code']}) {error['title']} -"
                            f" {error['detail']}",
                            "warning")
                    return webinterface.redirect(request, "/setup_wizard/dns")
            else:
                # print(f"dns results: {response.content}")
                dns_data = response.content["data"]["attributes"]
                # {'data': {'type': 'dns_gateway_names', 'id': 'oNaPqdWN0AuJhPW6byQLAr',
                #           'attributes': {'id': 'oNaPqdWN0AuJhPW6byQLAr',
                #                          'gateway_id': 'gn16m4W7z9t9cZOx4Apyar',
                #                          'dns_domain_id': 'dQEBy2NBGkFotjeN2LWZ0M',
                #                          'name': 'henry2',
                #                          'created_at': 1489874336,
                #                          'updated_at': 1552233516,
                #                          'allow_change_at': 1554825516,
                #                          'domain': 'yombo.me'},
                #           'links': {'self': 'https://api.yombo.net/api/v1/dns_domains/oNaPqdWN0AuJhPW6byQLAr'}},
                #  'links': {'self': 'https://api.yombo.net/api/v1/gateways/gn16m4W7z9t9cZOx4Apyar/dns'},
                #  'meta': {'includable': ['dns_domains']}}

                webinterface._Configs.set("dns.fqdn", f'{dns_data["name"]}.{dns_data["domain"]}',
                                          ref_source=webinterface)
                webinterface._Configs.set("dns.name", dns_data["name"], ref_source=webinterface)
                webinterface._Configs.set("dns.domain", dns_data["domain"], ref_source=webinterface)
                webinterface._Configs.set("dns.domain_id", dns_data["dns_domain_id"], ref_source=webinterface)
                webinterface._Configs.set("dns.allow_change_at", dns_data["allow_change_at"], ref_source=webinterface)

            dns_fqdn = webinterface._Configs.get("dns.fqdn", None)
            dns_name = webinterface._Configs.get("dns.name", None)
            dns_domain = webinterface._Configs.get("dns.domain", None)
            allow_change = webinterface._Configs.get("dns.allow_change_at", 0)
            return webinterface.render_template(request,
                                                webinterface.wi_dir + "/pages/setup_wizard/dns.html",
                                                dns_fqdn=dns_fqdn,
                                                dns_name=dns_name,
                                                dns_domain=dns_domain,
                                                allow_change=allow_change,
                                                )

        @webapp.route("/finished", methods=["GET"])
        @get_session(auth_required=True)
        def page_setup_wizard_finished_get(webinterface, request, session):
            """ Displays the setup wizard form. """
            session["setup_wizard_last_step"] = "finished"
            return webinterface.render_template(request,
                                                webinterface.wi_dir + "/pages/setup_wizard/finished.html",
                                                )

        @webapp.route("/finished", methods=["POST"])
        @get_session(auth_required=True)
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
                "name": submitted_dns_name,
                "domain_id": submitted_dns_domain,
            }

            auth_header = yield session.authorization_header(request)

            try:
                response = yield webinterface._YomboAPI.request(
                    "POST",
                    f"/v1/gateways/{webinterface._Configs.get('core.gwid')}/dns",
                    body=data,
                    authorization_header=auth_header)
            except YomboWarning as e:
                for error in e.errors:
                    session.add_alert(
                        f"Unable to setup gateway DNS, Yombo API responded with: ({error['code']}) {error['title']} -"
                        f" {error['detail']}",
                        "warning")
                return webinterface.redirect(request, "/setup_wizard/dns")
            else:
                dns_data = response.content["data"]["attributes"]
                webinterface._Configs.set("dns.fqdn", f'{dns_data["name"]}.{dns_data["domain"]}', ref_source=webinterface)
                webinterface._Configs.set("dns.name", dns_data["name"], ref_source=webinterface)
                webinterface._Configs.set("dns.domain", dns_data["domain"], ref_source=webinterface)
                webinterface._Configs.set("dns.domain_id", dns_data["dns_domain_id"], ref_source=webinterface)
                webinterface._Configs.set("dns.allow_change_at", dns_data["allow_change_at"], ref_source=webinterface)

            session["setup_wizard_last_step"] = "finished"

            webinterface._Configs.set("core.first_run", False, ref_source=webinterface)
            return webinterface.render_template(request,
                                                webinterface.wi_dir + "/pages/setup_wizard/finished.html",
                                                )

        @webapp.route("/finished_restart", methods=["GET"])
        @get_session(auth_required=True)
        def page_setup_wizard_finished_restart(webinterface, request, session):
            """ Restarts the gateway. """
            webinterface._Configs.set("core.first_run", False, ref_source=webinterface)
            return webinterface.restart(request, message="The first restart after setup may take a little while.")
