simulate_gw = {
              'new':{
                  'label': '',
                  'description': '',
                  'variables': {
                      'elevation': '75',
                      'latitude': '37.758',
                      'longitude': '-122.438'
                      }
                  },
              'xyz1':{
                  'label': 'Home',
                  'description': 'Main house gateway',
                  'variables': {
                      'latitude': 38.576,
                      'longitude': -121.276,
                      'elevation': 100,
                      }
                  },
              'abc2':{
                  'label': 'Garage',
                  'description': 'The garage',
                  'variables': {
                      'latitude': 37.791,
                      'longitude': -121.858,
                      'elevation': 50,
                      }
                  },
              'mno3':{
                  'label': 'Shed',
                  'description': 'In the shed!',
                  'variables': {
                      'latitude': 37.259,
                      'longitude': -122.177,
                      'elevation': 25,
                      }
                  },
              }

def route_configs(webapp):
    with webapp.subroute("/configs") as webapp:
        @webapp.route('/')
        def page_configs(webinterface, request):
            auth = webinterface.require_auth(request)
            if auth is not None:
                return auth
            return webinterface.redirect(request, '/configs/basic')

        @webapp.route('/basic', methods=['GET'])
        def page_configs_basic_get(webinterface, request):
            auth = webinterface.require_auth(request)
            if auth is not None:
                return auth

            configs = webinterface._Configs.get("*", "*")

            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/basic.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               config=configs,
                               )

        @webapp.route('/basic', methods=['POST'])
        def page_configs_basic_post(webinterface, request):
            auth = webinterface.require_auth(request)
            if auth is not None:
                return auth

            valid_submit = True
            # more checks to come, just doing basic for now.
            try:
                submitted_core_label = request.args.get('core-label')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Label.")

            try:
                submitted_core_description = request.args.get('core-description')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Description.")

            submitted_location_latitude = request.args.get('location-latitude')[0]
            try:
                submitted_location_latitude = request.args.get('location-latitude')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Latitude222.")

            try:
                submitted_location_longitude = request.args.get('location-longitude')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Longitude333.")

            try:
                submitted_location_elevation = request.args.get('location-elevation')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Elevation.")


            try:
                submitted_webinterface_enabled = request.args.get('webinterface-enabled')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Webinterface Enabled/Disabled value.")

            try:
                submitted_webinterface_localhost_only = request.args.get('webinterface-localhost-only')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Webinterface Localhost Only Selection.")

            try:
                submitted_webinterface_nonsecure_port = request.args.get('webinterface-nonsecure-port')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid webinterface non-secure port.")

            try:
                submitted_webinterface_secure_port = request.args.get('webinterface-secure-port')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid webinterface secure port.")

            if valid_submit is True:
                webinterface._Configs.set('core', 'label', submitted_core_label)
                webinterface._Configs.set('core', 'description', submitted_core_description)
                webinterface._Configs.set('location', 'latitude', submitted_location_latitude)
                webinterface._Configs.set('location', 'longitude', submitted_location_longitude)
                webinterface._Configs.set('location', 'elevation', submitted_location_elevation)
                webinterface._Configs.set('webinterface', 'enabled', submitted_webinterface_enabled)
                webinterface._Configs.set('webinterface', 'localhost-only', submitted_webinterface_localhost_only)
                webinterface._Configs.set('webinterface', 'nonsecure-port', submitted_webinterface_nonsecure_port)
                webinterface._Configs.set('webinterface', 'secure-port', submitted_webinterface_secure_port)

            configs = webinterface._Configs.get("*", "*")


            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/basic.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               config=configs,
                               )

        @webapp.route('/yombo_ini')
        def page_configs_yombo_ini(webinterface, request):
            auth = webinterface.require_auth(request)
            if auth is not None:
                return auth

            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/yombo_ini.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               configs=webinterface._Libraries['configuration'].configs
                               )




