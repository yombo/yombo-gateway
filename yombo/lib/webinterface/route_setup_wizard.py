from twisted.internet.defer import inlineCallbacks, returnValue

from yombo.core.exceptions import YomboWarningCredentails

from yombo.lib.webinterface.auth import require_auth_pin, require_auth, get_session, needs_web_pin

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

def route_setup_wizard(webapp):
    with webapp.subroute("/setup_wizard") as webapp:
        @webapp.route('/1')
        @require_auth_pin(login_redirect="/setup_wizard/1")
        @get_session()
        def page_setup_wizard_1(webinterface, request, session):
            """
            Displays the welcome page. Doesn't do much.
            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            # print "webinterface = %s" % webinterface
            # print "request = %s" % request
            # print "session = %s" % session
            print "session : %s" % session
            webinterface.sessions.set(request, 'setup_wizard_last_step', 1)
            if session is not False:
                if session.get('setup_wizard_done') is True:
                    return webinterface.redirect(request, '/setup_wizard/6')
            page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/1.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                               )

        @webapp.route('/2')
        @require_auth(login_redirect="/setup_wizard/2")
        @inlineCallbacks
        def page_setup_wizard_2(webinterface, request, session):
            print "session = %s" % session
            print "wiz step: %s" % webinterface.sessions.get(request, 'setup_wizard_ last_step')
            if session is not None:
                if session.get('setup_wizard_done') is True:
                    returnValue(webinterface.redirect(request, '/setup_wizard/6'))
                if session.get('setup_wizard_last_step') not in (None, 1, 2, 3):
                    webinterface.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
                    returnValue(webinterface.redirect(request, '/setup_wizard/1'))

            # auth = webinterface.require_auth(request)  # Notice difference. Now we want to log the user in.
            # if auth is not None:
            #     return auth

    #        print "selected gateawy: %s" % webinterface.sessions.get(request, 'setup_wizard_gateway_id')

            # simulate fetching possible gateways:
#            webinterface.gateway()
            try:
                results = yield webinterface.api.gateway_index()
            except YomboWarningCredentails:
                webinterface.add_alert("System credentails appear to be invalid. Please login as the gateway owner.")
                session['auth'] = False
                returnValue(webinterface.redirect(request, '/setup_wizard/2'))
            available_gateways = {};

            for gateway in results['data']:
                # print "gateway: %s " % gateway
                available_gateways[gateway['id']] = gateway
            session.set('available_gateways', available_gateways)
            # print "available_gateways: %s" % available_gateways

            session['setup_wizard_last_step'] = 2
            page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/2.html')
            output = page.render(func=webinterface.functions,
                               _=_,  # translations
                               alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                               available_gateways=available_gateways,
                               selected_gateway=webinterface.sessions.get(request, 'setup_wizard_gateway_id'),
                               )
            returnValue(output)

        @webapp.route('/3', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_3_get(webinterface, request, session):
            if session.get('setup_wizard_done') is True:
                returnValue(webinterface.redirect(request, '/setup_wizard/6'))
            if session.get('setup_wizard_last_step') not in (2, 3, 4):
                # print "wiz step: %s" % webinterface.sessions.get(request, 'setup_wizard_last_step')
                returnValue(webinterface.redirect(request, '/setup_wizard/1'))

            available_gateways = session.get('available_gateways')

            submitted_gateway_id = webinterface.sessions.get(request, 'setup_wizard_gateway_id')
            if submitted_gateway_id == None:
                webinterface.add_alert("Selected gateway ID not found. Try again.")
                returnValue(webinterface.redirect(request, "/setup_wizard/2"))

            if submitted_gateway_id not in available_gateways:
                webinterface.add_alert("Selected gateway not found. Try again.")
                webinterface.redirect(request, '/setup_wizard/2')

            output = yield page_setup_wizard_3_show_form(webinterface, request, submitted_gateway_id, available_gateways, session)
            returnValue(output)

        @webapp.route('/3', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_3_post(webinterface, request, session):
            if session.get('setup_wizard_done') is True:
                returnValue(webinterface.redirect(request, '/setup_wizard/6'))
            if session.get('setup_wizard_last_step') not in (2, 3, 4):
                # print "wiz step: %s" % webinterface.sessions.get(request, 'setup_wizard_last_step')
                returnValue(webinterface.redirect(request, '/setup_wizard/1'))

            valid_submit = True
            try:
                submitted_gateway_id = request.args.get('gateway-id')[0]
            except:
                valid_submit = False

            if submitted_gateway_id == "" or valid_submit == False:
                webinterface.add_alert("Invalid gateway selected. Try again.")
                returnValue(webinterface.redirect(request, '/setup_wizard/2'))

            available_gateways = session.get('available_gateways')

            if submitted_gateway_id not in available_gateways and submitted_gateway_id != 'new':
                webinterface.add_alert("Selected gateway not found. Try again.")
                returnValue(webinterface.redirect(request, "/setup_wizard/2"))

            output = yield page_setup_wizard_3_show_form(webinterface, request, submitted_gateway_id, available_gateways, session)
            returnValue(output)

        @inlineCallbacks
        def page_setup_wizard_3_show_form(webinterface, request, wizard_gateway_id, available_gateways, session):
            settings = {}
            if wizard_gateway_id != 'new':
                results = yield webinterface.api.gateway_config_index(wizard_gateway_id)
                for config in results['data']:
                    if config['section'] not in settings:
                        settings[config['section']] = {}
                    settings[config['section']][config['option']] = config

            if 'location' not in settings:
                settings['location'] = {}
            if 'latitude' not in settings['location']:
                settings['location']['latitude'] = { 'data' : '37.757'}
            if 'longitude' not in settings['location']:
                settings['location']['longitude'] = { 'data' : '-122.437'}
            if 'elevation' not in settings['location']:
                settings['location']['elevation'] = { 'data' : '90'}

            if 'times' not in settings:
                settings['times'] = {}
            if 'twilighthorizon' not in settings['times']:
                settings['times']['twilighthorizon'] = { 'data' : '-6'}

            print "settings: %s" % settings

            # session['setup_wizard_gateway_latitude'] = available_gateways[wizard_gateway_id]['variables']['latitude']
            # session['setup_wizard_gateway_longitude'] = available_gateways[wizard_gateway_id]['variables']['longitude']
            # session['setup_wizard_gateway_elevation'] = available_gateways[wizard_gateway_id]['variables']['elevation']

            if 'setup_wizard_gateway_id' not in session or session['setup_wizard_gateway_id'] != wizard_gateway_id:
                session['setup_wizard_gateway_id'] = wizard_gateway_id
                if session['setup_wizard_gateway_id'] == 'new':
                    session['setup_wizard_gateway_machine_label'] = ''
                    session['setup_wizard_gateway_label'] = ''
                    session['setup_wizard_gateway_description'] = ''
                else:
                    session['setup_wizard_gateway_machine_label'] = available_gateways[wizard_gateway_id]['machine_label']
                    session['setup_wizard_gateway_label'] = available_gateways[wizard_gateway_id]['label']
                    session['setup_wizard_gateway_description'] = available_gateways[wizard_gateway_id]['description']
            print "session: %s" % session
            print "gateway_id: %s" % wizard_gateway_id
            fields = {
                  'id' : session['setup_wizard_gateway_id'],
                  'machine_label': session['setup_wizard_gateway_machine_label'],
                  'label': session['setup_wizard_gateway_label'],
                  'description': session['setup_wizard_gateway_description'],
            }

            print "gw_fields: %s" % fields

            session['setup_wizard_last_step'] = 3
            page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/3.html')
            output = page.render(func=webinterface.functions,
                               _=_,  # translations
                               alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                               gw_fields=fields,
                               settings=settings,
                               )
            returnValue(output)

        @webapp.route('/4', methods=['GET'])
        @require_auth()
        def page_setup_wizard_4_get(webinterface, request, session):
            if session.get('setup_wizard_done') is True:
                return webinterface.redirect(request, '/setup_wizard/6')
            if session.get('setup_wizard_last_step') not in (3, 4, 5):
                webinterface.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            auth = webinterface.require_auth(request)  # Notice difference. Now we want to log the user in.
            if auth is not None:
                return auth

            return webinterface.page_setup_wizard_4_show_form(request, session)

        @webapp.route('/4', methods=['POST'])
        @require_auth()
        def page_setup_wizard_4_post(webinterface, request, session):
            if webinterface.sessions.get(request, 'setup_wizard_done') is True:
                return webinterface.redirect(request, '/setup_wizard/6')
            if webinterface.sessions.get(request, 'setup_wizard_last_step') not in (3, 4, 5):
                webinterface.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            valid_submit = True
            try:
                submitted_gateway_label = request.args.get('gateway_label')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Label.")

            try:
                submitted_gateway_machine_label = request.args.get('gateway_machine_label')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Machine Label.")

            try:
                submitted_gateway_description = request.args.get('gateway_description')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Description.")

            try:
                submitted_gateway_latitude = request.args.get('location_latitude')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Latitude.")

            try:
                submitted_gateway_longitude = request.args.get('location_longitude')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Longitude.")

            try:
                submitted_gateway_elevation = request.args.get('location_elevation')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Elevation.")

            if valid_submit is False:
                return page_setup_wizard_3_get(webinterface, request)
                page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/3.html')
                return page.render(alerts=webinterface.get_alerts(),
                                   data=webinterface.data,
                                   )
            session = webinterface.sessions.load(request)

            session['setup_wizard_gateway_machine_label'] = submitted_gateway_machine_label
            session['setup_wizard_gateway_label'] = submitted_gateway_label
            session['setup_wizard_gateway_description'] = submitted_gateway_description
            session['setup_wizard_gateway_latitude'] = submitted_gateway_latitude
            session['setup_wizard_gateway_longitude'] = submitted_gateway_longitude
            session['setup_wizard_gateway_elevation'] = submitted_gateway_elevation

            return page_setup_wizard_4_show_form(webinterface, request, session)

        def page_setup_wizard_4_show_form(webinterface, request, session):
            security_items = {
                'status': session.get('setup_wizard_security_status', '1'),
                'gps_status': session.get('setup_wizard_security_gps_status', '1'),
            }

            print "security_items: %s" % security_items

            session['setup_wizard_last_step'] = 4
            page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/4.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               alerts={},
                               data=webinterface.data,
                               security_items=security_items,
                               )

        @webapp.route('/5', methods=['GET'])
        @require_auth()
        def page_setup_wizard_5_get(webinterface, request, session):
            if session.get('setup_wizard_done') is True:
                return webinterface.redirect(request, '/setup_wizard/6')
            if session.get('setup_wizard_last_step') not in (4, 5, 6):
                webinterface.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            return page_setup_wizard_5_show_form(webinterface, request, session)

        @webapp.route('/5', methods=['POST'])
        @require_auth()
        def page_setup_wizard_5_post(webinterface, request, session):
            if session.get('setup_wizard_done') is True:
                return webinterface.redirect(request, '/setup_wizard/6')
            if session.get('setup_wizard_last_step') not in (4, 5, 6):
                webinterface.add_alert("Invalid wizard state. Please don't use the forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            valid_submit = True
            try:
                submitted_security_status = request.args.get('security-status')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Device Send Status.")


            try:
                submitted_security_gps_status = request.args.get('security-gps-status')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway GPS Locations Send Status.")

            if valid_submit is False:
                return webinterface.redirect(request, '/setup_wizard/4')

            session['setup_wizard_security_status'] = submitted_security_status
            session['setup_wizard_security_gps_status'] = submitted_security_gps_status

            return page_setup_wizard_5_show_form(webinterface, request, session)

        def page_setup_wizard_5_show_form(webinterface, request, session):
            gpg_selected = "new"

            session.set('setup_wizard_last_step', 5)
            page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/5.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                               gpg_selected=gpg_selected
                               )

        @webapp.route('/5_gpg_section')
        @require_auth()
        def page_setup_wizard_5_gpg_section(webinterface, request, session):

            if webinterface.sessions.get(request, 'setup_wizard_last_step') != 5:
                return "Invalid wizard state. No content found."

            available_keys = {} # simulate getting available keys from GPG library.

            valid_submit = True
            try:
                submitted_gpg_action = request.args.get('gpg_action')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Label.")

            if valid_submit is False:
                return "invalid submit"

            if submitted_gpg_action == "new":
                page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/5_gpg_new.html')
                return page.render(func=webinterface.functions,
                                   _=_,  # translations
                                   alerts=webinterface.get_alerts(),
                                   data=webinterface.data,
                                   )
            elif submitted_gpg_action == "import":
                page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/5_gpg_import.html')
                return page.render(func=webinterface.functions,
                                   _=_,  # translations
                                   alerts=webinterface.get_alerts(),
                                   data=webinterface.data,
                                   )
            elif submitted_gpg_action in available_keys:
                page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/5_gpg_existing.html')
                return page.render(func=webinterface.functions,
                                   _=_,  # translations
                                   alerts=webinterface.get_alerts(),
                                   data=webinterface.data,
                                   )
            else:
                return "Invalid GPG selection."

        @webapp.route('/6', methods=['GET'])
        @require_auth()
        def page_setup_wizard_6_get(webinterface, request, session):
            auth = webinterface.require_auth(request)  # Notice difference. Now we want to log the user in.
            if auth is not None:
                return auth

            if webinterface.sessions.get(request, 'setup_wizard_done') is not True:
                webinterface.redirect(request, '/setup_wizard/5')

            page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/6.html')
            return page.render(func=webinterface.functions,
                               _=_,  # translations
                               alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                               )

        @webapp.route('/6', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_6_post(webinterface, request, session):
            print "111"
            if webinterface.sessions.get(request, 'setup_wizard_done') is True:
                print "aaa"
                returnValue(webinterface.redirect(request, '/setup_wizard/6'))

            valid_submit = True
            try:
                submitted_gpg_actions = request.args.get('gpg_action')[0]  # underscore here due to jquery
            except:
                valid_submit = False
                webinterface.add_alert("Please select an appropriate GPG/PGP Key action.")

            if submitted_gpg_actions == 'import':  # make GPG keys!
                try:
                    submitted_gpg_private = request.args.get('gpg-private-key')[0]
                except:
                    valid_submit = False
                    webinterface.add_alert("When importing, must have a valid private GPG/PGP key.")

                try:
                    submitted_gpg_public = request.args.get('gpg-public-key')[0]
                except:
                    valid_submit = False
                    webinterface.add_alert("When importing, must have a valid public GPG/PGP key.")

            if valid_submit is False:
                returnValue(webinterface.redirect('/setup_wizard/5'))


            if submitted_gpg_actions == 'new':  # make GPG keys!
    #            gpg-make-new key here...
                pass
            elif submitted_gpg_actions == 'import':  # make GPG keys!
    #            gpg-import-new-key-here...
                pass
            elif submitted_gpg_actions == 'existing':  # make GPG keys!
    #            gpg-import-new-key-here...
                pass

            gpg_info = {  # will be returned from the GPG import/create/select existing funciton
                'keyid': '63EE4EA472E49634',
                'keypublicascii': """-----BEGIN PGP PUBLIC KEY BLOCK-----
    Version: GnuPG v1.4.12 (GNU/Linux)
    mI0ETyeLqwEEANsXSCvR9H5eSqRDusnqZpaxIj9uKanS+/R8yj23Yo2fl0r1BCwv
    EnYF8h2tnowFQb59fuv821ZH7LoT4HZeDpNL8WGjaBSYpnxfGK3GBahM65a2WISb
    nA+lkCuh7C6MA1zrNuKp5splsi/fg7hm7kaax5H2NJAUSuT3xsmLpZUTABEBAAG0
    P0dlbmVyYXRlZCBieSBBSFggKGdwZ19nZW5lcmF0ZWtleXMucHkpIDxTRldFenA0
    M1l6TEpmUERAYWh4Lm1lPoi4BBMBAgAiBQJPJ4urAhsvBgsJCAcDAgYVCAIJCgsE
    FgIDAQIeAQIXgAAKCRBj7k6kcuSWNOs8A/4qTI+gw4SLwarGEVt0APFhKHQncXim
    XRIV0dpHp6fX4JBN2yGFfAFP9dl+/xBJnOklRlnEvIb7D0cjwtRHSbNntKQb3pWT
    v2WF64dX9flI/lICvwfTsaE7FPaFHiG6flXfizYYyQttNB9RFF6AZqV0t6+1/FHC
    46JXipvbzmtNJQ==
    =NXHA
    -----END PGP PUBLIC KEY BLOCK-----""",
            }
    #        if gpg_ok is False:
    #            return webinterface.redirect('/setup_wizard/5')



            # Call Yombo API to save Gateway. Will get back all the goodies we need!
            # Everything is done! Lets save all the configs!

            session = webinterface.sessions.load(request)
            if session['setup_wizard_gateway_id'] == 'new':
                data = {
                    'machine_label': session['setup_wizard_gateway_machine_label'],
                    'label': session['setup_wizard_gateway_label'],
                    'description': session['setup_wizard_gateway_description'],
                }
                results = yield webinterface.api.request('POST', '/v1/gateway', data)

            else:
                data = {
                    'label': session['setup_wizard_gateway_label'],
                    'description': session['setup_wizard_gateway_description'],
                }
                results = yield webinterface.api.request('PATCH', '/v1/gateway/%s' % session['setup_wizard_gateway_id'])
                results = yield webinterface.api.request('GET', '/v1/gateway/%s/new_hash' % session['setup_wizard_gateway_id'])

            print "id: %s" % session['setup_wizard_gateway_id']
            print "data: %s" % data
            print results
            webinterface._Configs.set('core', 'updated', results['data']['updated_at'])
            webinterface._Configs.set('core', 'created', results['data']['created_at'])
            webinterface._Configs.set('core', 'gwid', results['data']['id'])
            webinterface._Configs.set('core', 'gwuuid', results['data']['uuid'])
            webinterface._Configs.set('core', 'machine_label', session['setup_wizard_gateway_machine_label'])
            webinterface._Configs.set('core', 'label', session['setup_wizard_gateway_label'])
            webinterface._Configs.set('core', 'description', session['setup_wizard_gateway_description'])
            webinterface._Configs.set('core', 'gwhash', results['data']['hash'])
            webinterface._Configs.set('gpg', 'keyid', gpg_info['keyid'])
            webinterface._Configs.set('gpg', 'keypublicascii', gpg_info['keypublicascii'])
            webinterface._Configs.set('security', 'amqpsendstatus', session['setup_wizard_security_status'])
            webinterface._Configs.set('security', 'amqpsendgpsstatus', session['setup_wizard_security_gps_status'])
            webinterface._Configs.set('location', 'latitude', session['setup_wizard_gateway_latitude'])
            webinterface._Configs.set('location', 'longitude', session['setup_wizard_gateway_longitude'])
            webinterface._Configs.set('location', 'elevation', session['setup_wizard_gateway_elevation'])
            webinterface._Configs.set('core', 'firstrun', False)

            # Remove wizard settings...
            for k in session.keys():
                if k.startswith('setup_wizard_'):
                    session.pop(k)
            session['setup_wizard_done'] = True
            session['setup_wizard_last_step'] = 6

            page = webinterface.get_template(request, webinterface._dir + 'pages/setup_wizard/6.html')
            returnValue(page.render(func=webinterface.functions,
                               _=_,  # translations
                               alerts=webinterface.get_alerts(),
                               data=webinterface.data,
                               ) )


        @webapp.route('/6_restart', methods=['GET'])
        @require_auth()
        def page_setup_wizard_6_restart(webinterface, request, session):
            return webinterface.restart(request)
    #        auth = webinterface.require_auth(request)  # Notice difference. Now we want to log the user in.
    #        if auth is not None:
    #            return auth

    #        if webinterface.sessions.get(request, 'setup_wizard_done') is not True:
    #            return webinterface.redirect(request, '/setup_wizard/5')

        @webapp.route('/setup_wizard/static/', branch=True)
        def setup_wizard_static(self, request):
            return File(self._current_dir + "/lib/webinterface/pages/setup_wizard/static")
