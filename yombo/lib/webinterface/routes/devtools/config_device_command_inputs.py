from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning


def route_devtools_config_device_command_inputs(webapp):
    with webapp.subroute("/devtools") as webapp:

        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/devtools/config/", "Config Tools")
            webinterface.add_breadcrumb(request, "/devtools/config/device_types/index", "Device Types", True)

        @webapp.route(
            "/config/device_command_inputs/details/<string:device_command_input_id>/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>/<string:input_type_id>",
            methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_details_get(webinterface, request, session,
                                                                 device_command_input_id,
                                                                 device_type_command_id,
                                                                 device_type_id,
                                                                 command_id,
                                                                 input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request("GET",
                                                                           f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                command_results = yield webinterface._YomboAPI.request("GET",
                                                                       f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                input_type_results = yield webinterface._YomboAPI.request("GET",
                                                                          f"/v1/input_type/{input_type_id}",
                                                                          session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                device_command_input_results = yield webinterface._YomboAPI.request(
                    "GET",
                    "/v1/device_command_input/{device_command_input_id}",
                    session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            page = webinterface.get_template(request,
                                             webinterface.wi_dir + "/pages/devtools/config/device_command_inputs/details.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request, f"/devtools/config/device_type_commands/{device_type_command_id}/details",
                                        str(command_results["data"]["label"]))
            webinterface.add_breadcrumb(request, "/devtools/config/device_command_inputs/edit",
                                        "Input Command Details")
            return page.render(alerts=webinterface.get_alerts(),
                               device_type_command_id=device_type_command_id,
                               device_type=device_type_results["data"],
                               command=command_results["data"],
                               device_command_input=device_command_input_results["data"],
                               input_type=input_type_results["data"],
                               )

        @webapp.route(
            "/config/device_command_inputs/add/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>",
            methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_add_list_get(webinterface, request, session,
                                                                  device_type_command_id,
                                                                  device_type_id,
                                                                  command_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request("GET",
                                                                           f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                command_results = yield webinterface._YomboAPI.request("GET",
                                                                       f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")


            page = webinterface.get_template(request,
                                             webinterface.wi_dir + "/pages/devtools/config/device_command_inputs/add.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request, f"/devtools/config/device_type_commands/{device_type_command_id}/details",
                                        str(command_results["data"]["label"]))
            webinterface.add_breadcrumb(request, "/devtools/config/device_command_inputs/edit",
                                        "Inputs available")
            return page.render(alerts=webinterface.get_alerts(),
                               device_type_command_id=device_type_command_id,
                               device_type=device_type_results["data"],
                               command=command_results["data"],
                               )

        @webapp.route("/config/device_command_inputs/add/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>/<string:input_type_id>",
                      methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_command_inputs_add_get(webinterface, request, session,
                                                        device_type_command_id,
                                                        device_type_id,
                                                        command_id,
                                                        input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request("GET", f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request,
                                        f"/devtools/config/device_types/{device_type_id}/command/{command_id}/details",
                                        "Command")
            webinterface.add_breadcrumb(request,
                                        f"/devtools/config/device_types/{device_type_id}/command/{command_id}/add_input",
                                        "Associate input")

            try:
                command_results = yield webinterface._YomboAPI.request("GET", f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                input_type_results = yield webinterface._YomboAPI.request("GET", f"/v1/input_type/{input_type_id}",
                                                                          session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")
            webinterface.add_breadcrumb(
                request, f"/devtools/config/device_types/{device_type_id}/command/{command_id}/input/{input_type_id}/add_input",
                input_type_results["data"]["label"]
            )

            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "machine_label": webinterface.request_get_default(request, "machine_label", ""),
                "live_update": webinterface.request_get_default(request, "live_update", ""),
                "notes": webinterface.request_get_default(request, "notes", ""),
                "value_required": webinterface.request_get_default(request, "value_required", 0),
                "value_min": webinterface.request_get_default(request, "value_min", ""),
                "value_max": webinterface.request_get_default(request, "value_max", ""),
                "value_casing": webinterface.request_get_default(request, "value_casing", "none"),
                "encryption": webinterface.request_get_default(request, "encryption", "nosuggestion"),
            }
            return page_devtools_device_command_inputs_form(webinterface,
                                                            request,
                                                            session,
                                                            "add",
                                                            device_type_command_id,
                                                            data,
                                                            device_type_results["data"],
                                                            command_results["data"],
                                                            input_type_results["data"],
                                                            "Associate input type to command")

        @webapp.route(
            "/config/device_command_inputs/add/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>/<string:input_type_id>",
            methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_command_inputs_add_post(webinterface, request, session,
                                                         device_type_command_id,
                                                         device_type_id,
                                                         command_id,
                                                         input_type_id):
            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "machine_label": webinterface.request_get_default(request, "machine_label", ""),
                "live_update": webinterface.request_get_default(request, "live_update", ""),
                "notes": webinterface.request_get_default(request, "notes", ""),
                "value_required": webinterface.request_get_default(request, "value_required", 0),
                "value_min": webinterface.request_get_default(request, "value_min", ""),
                "value_max": webinterface.request_get_default(request, "value_max", ""),
                "value_casing": webinterface.request_get_default(request, "value_casing", "none"),
                "encryption": webinterface.request_get_default(request, "encryption", "nosuggestion"),
            }

            results = yield webinterface._DeviceTypes.dev_command_input_add(device_type_id,
                                                                            command_id,
                                                                            input_type_id,
                                                                            data,
                                                                            session=session["yomboapi_session"])

            try:
                command_results = yield webinterface._YomboAPI.request("GET",
                                                                       f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                input_type_results = yield webinterface._YomboAPI.request("GET",
                                                                          f"/v1/input_type/{input_type_id}",
                                                                          session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                device_type_results = yield webinterface._YomboAPI.request("GET",
                                                                           f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request, f"/devtools/config/device_type_commands/{device_type_command_id}/details",
                                        str(command_results["data"]["label"]))
            webinterface.add_breadcrumb(request, "/devtools/config/device_command_inputs/edit",
                                        "Associate input")

            # print("results:status: %s" % results["status"])
            if results["status"] == "failed":
                webinterface.add_alert(results["apimsghtml"], "warning")
                return page_devtools_device_command_inputs_form(
                    webinterface,
                    request,
                    session,
                    "add",
                    device_type_command_id,
                    data,
                    device_type_results["data"],
                    command_results["data"],
                    input_type_results["data"],
                    "Associate input type to command")

            msg = {
                "header": "Input Associated",
                "label": "Input has been associated to the command successfully",
                "description": "<p>The input has been associated to the device type command.</p>"
                               "<p>Continue to <ul>"
                               '<li><a href="/devtools/config/device_types/index">Device types index</a></li>'
                               f'<li><a href="/devtools/config/device_types/{device_type_id}/details">View the device type</a></li>'
                               f'<li><strong><a href="/devtools/config/device_type_commands/{device_type_command_id}/details">View device type command</a></strong></li>'
                               "</p>"
            }

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )

        @webapp.route(
            "/config/device_command_inputs/edit/<string:device_command_input_id>/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>/<string:input_type_id>",
            methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_command_inputs_edit_get(webinterface, request, session,
                                                         device_command_input_id,
                                                         device_type_command_id,
                                                         device_type_id,
                                                         command_id,
                                                         input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request("GET",
                                                                           f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                command_results = yield webinterface._YomboAPI.request("GET",
                                                                       f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                input_type_results = yield webinterface._YomboAPI.request("GET",
                                                                          f"/v1/input_type/{input_type_id}",
                                                                          session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                device_command_input_results = yield webinterface._YomboAPI.request(
                    "GET",
                    f"/v1/device_command_input/{device_command_input_id}",
                    session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            # data = {
            #     "machine_label": webinterface.request_get_default(request, "machine_label", ""),
            #     "live_update": webinterface.request_get_default(request, "live_update", ""),
            #     "notes": webinterface.request_get_default(request, "notes", ""),
            #     "value_required": webinterface.request_get_default(request, "value_required", ""),
            #     "value_min": webinterface.request_get_default(request, "value_min", ""),
            #     "value_max": webinterface.request_get_default(request, "value_max", ""),
            #     "value_casing": webinterface.request_get_default(request, "value_casing", "none"),
            #     "encryption": webinterface.request_get_default(request, "encryption", "nosuggestion"),
            # }
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request, f"/devtools/config/device_type_commands/{device_type_command_id}/details",
                                        str(command_results["data"]["label"]))
            webinterface.add_breadcrumb(request, "/devtools/config/device_command_inputs/edit",
                                        "Edit input")
            return page_devtools_device_command_inputs_form(webinterface, request, session,
                                                            "edit",
                                                            device_type_command_id,
                                                            device_command_input_results["data"],
                                                            device_type_results["data"],
                                                            command_results["data"],
                                                            input_type_results["data"],
                                                            "Associate input type to command")

        @webapp.route(
            "/config/device_command_inputs/edit/<string:device_command_input_id>/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>/<string:input_type_id>",
            methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_edit_post(webinterface, request, session,
                                                               device_command_input_id,
                                                               device_type_command_id,
                                                               device_type_id,
                                                               command_id,
                                                               input_type_id):
            data = {
                "label": webinterface.request_get_default(request, "label", ""),
                "machine_label": webinterface.request_get_default(request, "machine_label", ""),
                "live_update": webinterface.request_get_default(request, "live_update", ""),
                "notes": webinterface.request_get_default(request, "notes", ""),
                "value_required": webinterface.request_get_default(request, "value_required", ""),
                "value_min": webinterface.request_get_default(request, "value_min", ""),
                "value_max": webinterface.request_get_default(request, "value_max", ""),
                "value_casing": webinterface.request_get_default(request, "value_casing", "none"),
                "encryption": webinterface.request_get_default(request, "encryption", "nosuggestion"),
            }

            results = yield webinterface._DeviceTypes.dev_command_input_edit(
                device_command_input_id,
                data, session=session["yomboapi_session"]
            )

            try:
                command_results = yield webinterface._YomboAPI.request("GET",
                                                                       f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                input_type_results = yield webinterface._YomboAPI.request("GET",
                                                                          f"/v1/input_type/{input_type_id}",
                                                                          session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                device_type_results = yield webinterface._YomboAPI.request("GET",
                                                                           f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            if results["status"] == "failed":
                webinterface.add_alert(results["apimsghtml"], "warning")
                return page_devtools_device_command_inputs_form(webinterface, request, session,
                                                                "add",
                                                                device_type_command_id,
                                                                data,
                                                                device_type_results["data"],
                                                                command_results["data"],
                                                                input_type_results["data"],
                                                                "Associate input type to command")

            msg = {
                "header": "Input Associated",
                "label": "Input has been associated to the command successfully",
                "description": "<p>The input has been associated to the device type command.</p>"
                               "<p>Continue to <ul>"
                               '<li><a href="/devtools/config/device_types/index">Device types index</a></li>'
                               f'<li><a href="/devtools/config/device_types/{device_type_id}/details">View the device type</a></li>'
                               f'<li><strong><a href="/devtools/config/device_type_commands/{device_type_command_id}/details">View device type command</a></strong></li>'
                               "</p>"
            }

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request,
                                        f"/devtools/config/device_type_commands/{device_type_command_id}/details",
                                        str(command_results["data"]["label"]))
            webinterface.add_breadcrumb(request, "/devtools/config/device_command_inputs/edit",
                                        "Edit input")
            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )


        def page_devtools_device_command_inputs_form(webinterface, request, session,
                                                     action_type,
                                                     device_type_command_id,
                                                     command_input,
                                                     device_type,
                                                     command,
                                                     input_type,
                                                     header_label):
            page = webinterface.get_template(request,
                                             webinterface.wi_dir + "/pages/devtools/config/device_command_inputs/form.html")
            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               device_type=device_type,
                               command=command,
                               command_input=command_input,
                               input_type=input_type,
                               action_type=action_type,
                               device_type_command_id=device_type_command_id,
                               )

        @webapp.route(
            "/config/device_command_inputs/remove/<string:device_command_input_id>/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>/<string:input_type_id>",
            methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_delete_get(webinterface, request, session,
                                                                device_command_input_id,
                                                                device_type_command_id,
                                                                device_type_id,
                                                                command_id,
                                                                input_type_id):
            try:
                device_type_results = yield webinterface._YomboAPI.request("GET",
                                                                           f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                command_results = yield webinterface._YomboAPI.request("GET",
                                                                       f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                input_type_results = yield webinterface._YomboAPI.request("GET",
                                                                          f"/v1/input_type/{input_type_id}",
                                                                          session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            page = webinterface.get_template(request,
                                             webinterface.wi_dir + "/pages/devtools/config/device_command_inputs/remove.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request, f"/devtools/config/device_type_commands/{device_type_command_id}/details",
                                        str(command_results["data"]["label"]))
            webinterface.add_breadcrumb(request, "/devtools/config/device_command_inputs/edit",
                                        "Remove input")
            return page.render(alerts=webinterface.get_alerts(),
                               device_type=device_type_results["data"],
                               input_type=input_type_results["data"],
                               command=command_results["data"],
                               )

        @webapp.route(
            "/config/device_command_inputs/remove/<string:device_command_input_id>/<string:device_type_command_id>/<string:device_type_id>/<string:command_id>/<string:input_type_id>",
            methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_devtools_device_types_command_input_delete_post(webinterface, request, session,
                                                                 device_command_input_id,
                                                                 device_type_command_id,
                                                                 device_type_id,
                                                                 command_id,
                                                                 input_type_id):
            try:
                confirm = request.args.get("confirm")[0]
            except:
                return webinterface.redirect(request,
                                             f"/devtools/config/device_types/{device_type_id}/details")

            if confirm != "remove":
                webinterface.add_alert("Must enter 'delete' in the confirmation box to delete the device type.",
                                       "warning")
                return webinterface.redirect(
                    request,
                    f"/devtools/config/device_types/{device_type_id}/command/{command_id}/input/{input_type_id}/remove_input")

            results = yield webinterface._DeviceTypes.dev_command_input_remove(device_command_input_id,
                                                                               session=session["yomboapi_session"])
            if results["status"] == "failed":
                webinterface.add_alert(results["apimsghtml"], "warning")
                return webinterface.redirect(request,
                                             f"/devtools/config/device_types/{device_type_id}/details")

            try:
                device_type_results = yield webinterface._YomboAPI.request("GET",
                                                                           f"/v1/device_type/{device_type_id}",
                                                                           session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            try:
                command_results = yield webinterface._YomboAPI.request("GET",
                                                                       f"/v1/command/{command_id}",
                                                                       session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devtools/config/device_types/index")

            msg = {
                "header": "Device Type Deleted",
                "label": "Device Type deleted successfully",
                "description": "<p>The device type has been deleted.</p>"
                               "<p>Continue to:"
                               "<ul>"
                               '<li><a href="/devtools/config/device_types/index">Device type index</a></li>'
                               f'<li><a href="/devtools/config/device_types/{device_type_id}/details">View the device type</a></li>'
                               f'<li><strong><a href="/devtools/config/device_type_commands/{device_type_command_id}/details">View device type command</a></strong></li>'
                               "</p>"
            }

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/display_notice.html")
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])


            webinterface.add_breadcrumb(request, f"/devtools/config/device_types/{device_type_id}/details",
                                        device_type_results["data"]["label"])
            webinterface.add_breadcrumb(request, f"/devtools/config/device_type_commands/{device_type_command_id}/details",
                                        str(command_results["data"]["label"]))
            webinterface.add_breadcrumb(request, "/devtools/config/device_command_inputs/edit",
                                        "Remove input")

            return page.render(alerts=webinterface.get_alerts(),
                               msg=msg,
                               )
