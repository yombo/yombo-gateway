from yombo.lib.webinterface.auth import require_auth

def route_configs(webapp):
    with webapp.subroute("/configs") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_configs(webinterface, request, session):
            return webinterface.redirect(request, '/configs/basic')

        @webapp.route('/basic', methods=['GET'])
        @require_auth()
        def page_configs_basic_get(webinterface, request, session):
            configs = webinterface._Configs.get("*", "*")

            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/basic.html')
            return page.render(alerts=webinterface.get_alerts(),
                               config=configs,
                               )

        @webapp.route('/basic', methods=['POST'])
        @require_auth()
        def page_configs_basic_post(webinterface, request, session):

            valid_submit = True
            # more checks to come, just doing basic for now.
            try:
                submitted_core_label = request.args.get('core_label')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Label.")

            try:
                submitted_core_description = request.args.get('core_description')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Description.")

            try:
                submitted_location_searchtext = request.args.get('location_searchtext')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Location Search Entry.")

            try:
                submitted_location_latitude = request.args.get('location_latitude')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Lattitude.")

            try:
                submitted_location_longitude = request.args.get('location_longitude')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Longitude.")

            try:
                submitted_location_elevation = request.args.get('location_elevation')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Elevation.")


            try:
                submitted_webinterface_enabled = request.args.get('webinterface_enabled')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Webinterface Enabled/Disabled value.")

            try:
                submitted_webinterface_localhost_only = request.args.get('webinterface_localhost_only')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Webinterface Localhost Only Selection.")

            try:
                submitted_webinterface_nonsecure_port = request.args.get('webinterface_nonsecure_port')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid webinterface non_secure port.")

            try:
                submitted_webinterface_secure_port = request.args.get('webinterface_secure_port')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid webinterface secure port.")

            if valid_submit is True:
                webinterface._Configs.set('core', 'label', submitted_core_label)
                webinterface._Configs.set('core', 'description', submitted_core_description)
                webinterface._Configs.set('location', 'searchbox', submitted_location_searchtext)
                webinterface._Configs.set('location', 'latitude', submitted_location_latitude)
                webinterface._Configs.set('location', 'longitude', submitted_location_longitude)
                webinterface._Configs.set('location', 'elevation', submitted_location_elevation)
                webinterface._Configs.set('webinterface', 'enabled', submitted_webinterface_enabled)
                webinterface._Configs.set('webinterface', 'localhost-only', submitted_webinterface_localhost_only)
                webinterface._Configs.set('webinterface', 'nonsecure-port', submitted_webinterface_nonsecure_port)
                webinterface._Configs.set('webinterface', 'secure-port', submitted_webinterface_secure_port)

            configs = webinterface._Configs.get("*", "*")


            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/basic.html')
            return page.render(alerts=webinterface.get_alerts(),
                               config=configs,
                               )

        @webapp.route('/yombo_ini')
        @require_auth()
        def page_configs_yombo_ini(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/yombo_ini.html')
            return page.render(alerts=webinterface.get_alerts(),
                               configs=webinterface._Libraries['configuration'].configs
                               )

        @webapp.route('/gpg_keys')
        def page_gpg_keys_index(webinterface, request):
            print "################## gogogogogogogpgpgpgppgpg "
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/gpg_index.html')
            return page.render()

        @webapp.route('/gpg_keys/generate_key')
        def page_gpg_keys_generate_key(webinterface, request):
            request_id = yombo.utils.random_string(length=16)
    #        self._Libraries['gpg'].generate_key(request_id)
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/gpg_generate_key_started.html')
            return page.render(request_id=request_id, getattr=getattr, type=type)

        @webapp.route('/gpg_keys/genrate_key_status')
        def page_gpg_keys_generate_key_status(webinterface, request):
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/gpg_generate_key_status.html')
            return page.render(atoms=self._Libraries['atoms'].get_atoms(), getattr=getattr, type=type)
