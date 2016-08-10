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
            return webinterface.redirect(request, '/configs/basic')

        @webapp.route('/basic')
        def page_configs_basic(webinterface, request):
            config = {"core": {}, "webinterface": {}, "times": {}}
            config['core']['label'] = webinterface._Configs.get('core', 'label', '', False)
            config['core']['description'] = webinterface._Configs.get('core', 'description', '', False)
            config['times']['twilighthorizon'] = webinterface._Configs.get('times', 'twilighthorizon')
            config['webinterface']['enabled'] = webinterface._Configs.get('webinterface', 'enabled')
            config['webinterface']['port'] = webinterface._Configs.get('webinterface', 'port')
    
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/basic.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               config=config,
                               )
    
        @webapp.route('/yombo_ini')
        def page_configs_yombo_ini(webinterface, request):
            page = webinterface.get_template(request, webinterface._dir + 'pages/configs/yombo_ini.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               data=webinterface.data,
                               alerts=webinterface.get_alerts(),
                               configs=webinterface._Libraries['configuration'].configs
                               )
