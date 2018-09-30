import base64
from collections import OrderedDict
import hashlib
import json
from time import time

from twisted.internet.defer import inlineCallbacks
from twisted.internet import reactor

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth_pin, require_auth
from yombo.utils import is_true_false, unicode_to_bytes, bytes_to_unicode, save_file
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.setup_wizard")


def route_setup_wizard(webapp):
    with webapp.subroute("/setup_wizard") as webapp:

        def page_show_wizard_home(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/1.html')
            return page.render(
                               alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/', methods=['GET'])
        @require_auth_pin(login_redirect="/setup_wizard/1")
        def page_setup_wizard_home(webinterface, request, session):
            return webinterface.redirect(request, '/setup_wizard/1')

        @webapp.route('/restore_details',)
        @require_auth_pin(login_redirect="/setup_wizard/restore")
        @inlineCallbacks
        def page_setup_wizard_restore_details(webinterface, request, session):
            """
            Prompts user to upload the configuration file to restore the gateway.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            try:
                restorfile = request.args.get('restorefile')[0]
                try:
                    restorefile = json.loads(restorfile)
                    logger.info("Received configuration backup file.")
                    try:
                        if restorefile['hash'] != hashlib.sha256(unicode_to_bytes(restorefile['data'])).hexdigest():
                            webinterface.add_alert("Backup file appears to be corrupt: Invalid checksum.")
                            return page_show_wizard_home(webinterface, request, session)
                        restorefile['data'] = base64.b64decode(unicode_to_bytes(restorefile['data']))
                    except Exception as e:
                        logger.warn("Unable to b64decode data: {e}", e=e)
                        webinterface.add_alert("Unable to properly decode pass 1 of data segment of restore file.")
                        return page_show_wizard_home(webinterface, request, session)

                    session.set('restore_backup_file', restorefile)
                except Exception as e:
                    logger.warn("Unable to parse JSON phase 2: {e}", e=e)
                    webinterface.add_alert("Invalid restore file contents.")
                    return page_show_wizard_home(webinterface, request, session)
            except Exception:
                restorefile = session.get('restore_backup_file', None)
                if restorefile is None:
                    webinterface.add_alert("No restore file found.")
                    return page_show_wizard_home(webinterface, request, session)

            required_keys = ('encrypted', 'time', 'file_type', 'created', 'backup_version')
            if all(required in restorefile for required in required_keys) is False:
                webinterface.add_alert("Backup file appears to be missing important parts.")
                return page_show_wizard_home(webinterface, request, session)

            if restorefile['encrypted'] is True:
                try:
                    password = request.args.get('password',)[0]
                except Exception:
                    password = session.get('restorepassword', None)

                if password is None:
                    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/restore_password.html')
                    return page.render(
                        alerts=webinterface.get_alerts(),
                        restore=restorefile
                    )

                try:
                    decrypted = yield webinterface._GPG.decrypt_aes(password, restorefile['data'])
                    restorefile['data_processed'] = json.loads(bytes_to_unicode(decrypted))
                except Exception as e:
                    logger.warn("Unable to decrypt restoration file: {e}", e=e)
                    webinterface.add_alert("It appears the password is incorrect.", 'danger')
                    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/restore_password.html')
                    return page.render(
                        alerts=webinterface.get_alerts(),
                        restore=restorefile
                    )
            else:  #no password
                restorefile['data_processed'] = json.loads(bytes_to_unicode(restorefile['data']))

            session.set('restore_backup_file', restorefile)

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/restore_ready.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                restore=session.get('restore_backup_file')
            )

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/restore_complete.html')
            return page.render(
                               alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/restore_complete',)
        @require_auth_pin(login_redirect="/setup_wizard/restore")
        @inlineCallbacks
        def page_setup_wizard_restore_complete(webinterface, request, session):
            """
            Prompts user to upload the configuration file to restore the gateway.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            restorefile = session.get('restore_backup_file', None)
            if restorefile is None:
                webinterface.add_alert("No restore data found.")
                return page_show_wizard_home(webinterface, request, session)

            working_path = webinterface._Atoms.get('working_path')
            data = restorefile['data_processed']

            for section, options in data['configs'].items():
                for option, value in options.items():
                    webinterface._Configs.set(section, option, value)
            for fingerprint, key in data['gpg_keys'].items():
                if key['publickey'] != None:
                    yield webinterface._GPG.import_to_keyring(key['publickey'])
                if key['privatekey'] != None:
                    yield webinterface._GPG.import_to_keyring(key['privatekey'])
                if key['passphrase'] != None:

                    filename = "%s/etc/gpg/%s.pass" % (working_path, key['fingerprint'])
                    yield save_file(filename, key['passphrase'])
                if data['gpg_fingerprint'] == key['fingerprint']:
                    filename = "%s/etc/gpg/last.pass" % (working_path)
                    yield save_file(filename, key['passphrase'])

            for cert_name, cert in data['sslcerts'].items():
                webinterface._SSLCerts.import_cert(cert_name, cert)

            webinterface._Configs.exit_config_file = data['yombo_ini']
            yield webinterface._GPG.import_trust(data['gpg_trust'])

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/restart.html')
            reactor.callLater(0.4, webinterface.do_restart)
            return page.render(
                               alerts=webinterface.get_alerts(),
                               message="Configuration restored."
                               )

        @webapp.route('/1')
        @require_auth_pin(login_redirect="/setup_wizard/1")
        def page_setup_wizard_1(webinterface, request, session):
            """
            Displays the welcome page. Doesn't do much.
            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            if session is not None:
                session.delete('restore_backup_file')
            if session is not None and session is not False:
                if session.get('setup_wizard_done', False) is True:
                    return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])

            if session is not None:
                session.set('setup_wizard_last_step', 1)
                if session.get('setup_wizard_done', False) is True:
                    return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/1.html')
            return page.render(
                               alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/2')
        @require_auth(login_redirect="/setup_wizard/2")
        @inlineCallbacks
        def page_setup_wizard_2(webinterface, request, session):
            if session is not None:
                if session.get('setup_wizard_done', False) is True:
                    return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
                if session.get('setup_wizard_last_step', 1) not in (None, 1, 2, 3):
                    webinterface.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                    return webinterface.redirect(request, '/setup_wizard/1')

            try:
                results = yield webinterface._YomboAPI.request('GET',
                                                               '/v1/gateway/',
                                                               None,
                                                               session['yomboapi_session'])
            except YomboWarning as e:
                webinterface.add_alert("System credentials appear to be invalid. Please login as the gateway owner.")
                session['auth'] = False
                return webinterface.redirect(request, '/setup_wizard/2')
            available_gateways = {}

            for gateway in results['data']:
                available_gateways[gateway['id']] = gateway

            available_gateways_sorted = OrderedDict(sorted(available_gateways.items(), key=lambda x: x[1]['label']))
            # print("available_gateways_sorted: %s" % available_gateways_sorted)

            session.set('available_gateways', available_gateways_sorted)

            session['setup_wizard_last_step'] = 2
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/2.html')
            # print("session: %s" % session.auth_data)

            output = page.render(
                               alerts=webinterface.get_alerts(),
                               available_gateways=available_gateways_sorted,
                               selected_gateway=session.get('setup_wizard_gateway_id', 'new'),
                               )
            return output

        @webapp.route('/3', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_3_get(webinterface, request, session):
            if session.get('setup_wizard_done', False) is True:
                return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
            if session.get('setup_wizard_last_step', 1) not in (2, 3, 4):
                return webinterface.redirect(request, '/setup_wizard/1')

            available_gateways = session.get('available_gateways', None)
            if available_gateways == None:
                webinterface.add_alert("Selected gateway ID not found. Try again. (Error: 01)")
                session['setup_wizard_last_step'] = 2
                return webinterface.redirect(request, "/setup_wizard/2")

            if 'setup_wizard_gateway_id' not in session:
                webinterface.add_alert("Selected gateway ID not found. Try again. (Error: 02)")
                session['setup_wizard_last_step'] = 2
                return webinterface.redirect(request, "/setup_wizard/2")

            if session['setup_wizard_gateway_id'] != 'new' and session['setup_wizard_gateway_id'] not in available_gateways:
                webinterface.add_alert("Selected gateway not found. Try again. (Error: 04)")
                session['setup_wizard_last_step'] = 2
                return webinterface.redirect(request, '/setup_wizard/2')

            output = yield page_setup_wizard_3_show_form(webinterface, request, session['setup_wizard_gateway_id'],
                                                         available_gateways, session)
            return output

        @webapp.route('/3', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_3_post(webinterface, request, session):
            if session.get('setup_wizard_done', False) is True:
                return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
            if session.get('setup_wizard_last_step', 1) not in (2, 3, 4):
                # print("wiz step: %s" % session.get('setup_wizard_last_step'))
                return webinterface.redirect(request, '/setup_wizard/1')

            valid_submit = True
            try:
                submitted_gateway_id = request.args.get('gateway-id')[0]
            except:
                valid_submit = False

            if submitted_gateway_id == "" or valid_submit == False:
                webinterface.add_alert("Invalid gateway selected. Try again.")
                return webinterface.redirect(request, '/setup_wizard/2')

            available_gateways = session.get('available_gateways')

            if submitted_gateway_id not in available_gateways and submitted_gateway_id != 'new':
                webinterface.add_alert("Selected gateway not found. Try again.")
                return webinterface.redirect(request, "/setup_wizard/2")

            output = yield page_setup_wizard_3_show_form(webinterface, request, submitted_gateway_id,
                                                         available_gateways, session)
            return output

        @inlineCallbacks
        def page_setup_wizard_3_show_form(webinterface, request, wizard_gateway_id, available_gateways, session):
            settings = {}
            if wizard_gateway_id != 'new':
                try:
                    results = yield webinterface._YomboAPI.request("GET",
                                                                   "/v1/gateway/%s/config" % wizard_gateway_id,
                                                                   None,
                                                                   session['yomboapi_session'])
                except YomboWarning as e:
                    pass
                for config in results['data']:
                    if config['section'] not in settings:
                        settings[config['section']] = {}
                    settings[config['section']][config['option_name']] = config

            if 'location' not in settings:
                settings['location'] = {}

            if 'setup_wizard_gateway_location_search' in session:
                settings['location']['location_search'] = {'data': session['setup_wizard_gateway_location_search']}
            else:
                if 'latitude' not in settings['location']:
                    settings['location']['location_search'] = {'data': 'San Francisco, CA, USA'}

            if 'setup_wizard_gateway_latitude' in session:
                settings['location']['latitude'] = {'data': session['setup_wizard_gateway_latitude']}
            else:
                if 'latitude' not in settings['location']:
                    settings['location']['latitude'] = {'data': '37.757'}

            if 'setup_wizard_gateway_longitude' in session:
                settings['location']['longitude'] = {'data': session['setup_wizard_gateway_longitude']}
            else:
                if 'longitude' not in settings['location']:
                    settings['location']['longitude'] = {'data': '-122.437'}

            if 'setup_wizard_gateway_elevation' in session:
                settings['location']['elevation'] = {'data': session['setup_wizard_gateway_elevation']}
            else:
                if 'elevation' not in settings['location']:
                    settings['location']['elevation'] = {'data': '90'}
            #
            # if 'latitude' not in settings['location']:
            #     settings['location']['latitude'] = { 'data' : '37.757'}
            # if 'longitude' not in settings['location']:
            #     settings['location']['longitude'] = { 'data' : '-122.437'}
            # if 'elevation' not in settings['location']:
            #     settings['location']['elevation'] = { 'data' : '90'}

            if 'times' not in settings:
                settings['times'] = {}
            if 'twilighthorizon' not in settings['times']:
                settings['times']['twilighthorizon'] = { 'data' : '-6'}

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
            fields = {
                  'id': session['setup_wizard_gateway_id'],
                  'machine_label': session['setup_wizard_gateway_machine_label'],
                  'label': session['setup_wizard_gateway_label'],
                  'description': session['setup_wizard_gateway_description'],
            }

            session['setup_wizard_last_step'] = 3
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/3.html')
            output = page.render(
                                 alerts=webinterface.get_alerts(),
                                 gw_fields=fields,
                                 settings=settings,
                                )
            return output

        @webapp.route('/4', methods=['GET'])
        @require_auth()
        def page_setup_wizard_4_get(webinterface, request, session):
            if session.get('setup_wizard_done', False) is True:
                return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
            if session.get('setup_wizard_last_step', 1) not in (3, 4, 5):
                webinterface.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            return page_setup_wizard_4_show_form(webinterface, request, session)

        @webapp.route('/4', methods=['POST'])
        @require_auth()
        def page_setup_wizard_4_post(webinterface, request, session):
            if session.get('setup_wizard_done', False) is True:
                return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
            if session.get('setup_wizard_last_step', 1) not in (3, 4, 5):
                webinterface.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            valid_submit = True
            try:
                submitted_gateway_location_search = request.args.get('location_search')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Location Search.")

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

            session['setup_wizard_gateway_machine_label'] = submitted_gateway_machine_label
            session['setup_wizard_gateway_label'] = submitted_gateway_label
            session['setup_wizard_gateway_description'] = submitted_gateway_description
            session['setup_wizard_gateway_location_search'] = submitted_gateway_location_search
            session['setup_wizard_gateway_latitude'] = submitted_gateway_latitude
            session['setup_wizard_gateway_longitude'] = submitted_gateway_longitude
            session['setup_wizard_gateway_elevation'] = submitted_gateway_elevation

            return page_setup_wizard_4_show_form(webinterface, request, session)

        def page_setup_wizard_4_show_form(webinterface, request, session):
            if 'setup_wizard_gateway_is_master' in session and\
                            'setup_wizard_gateway_master_gateway_id' in session:
                is_master = session['setup_wizard_gateway_is_master']
                master_gateway_id = session['setup_wizard_gateway_master_gateway_id']
            else:
                available_gateways = session.get('available_gateways')
                if session['setup_wizard_gateway_id'] in available_gateways:
                    gw = available_gateways[session['setup_wizard_gateway_id']]
                    is_master = gw['is_master']
                    master_gateway_id = gw['master_gateway']  # api just has master_gateway
                else:
                    is_master = 1
                    master_gateway_id = None

            security_items = {
                'is_master': is_master,
                'master_gateway_id': master_gateway_id,
                'status': session.get('setup_wizard_security_status', '1'),
                'gps_status': session.get('setup_wizard_security_gps_status', '1'),
                'send_private_stats': session.get('setup_wizard_security_send_private_stats', '1'),
                'send_anon_stats': session.get('setup_wizard_security_send_anon_stats', '1'),
                }


            session['setup_wizard_last_step'] = 4
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/4.html')
            return page.render(
                               alerts=webinterface.get_alerts(),
                               security_items=security_items,
                               available_gateways=session.get('available_gateways'),
                               )

        @webapp.route('/5', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_5_get(webinterface, request, session):
            if session.get('setup_wizard_done', False) is True:
                return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
            if session.get('setup_wizard_last_step', 1) not in (4, 5):
                webinterface.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            page = yield page_setup_wizard_5_show_form(webinterface, request, session)
            return page

        @webapp.route('/5', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_5_post(webinterface, request, session):
            if session.get('setup_wizard_done', False) is True:
                return webinterface.redirect(request, '/setup_wizard/%s' % session['setup_wizard_last_step'])
            if session.get('setup_wizard_last_step', 1) not in (4, 5):
                webinterface.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            valid_submit = True
            try:
                submitted_gateway_master_gateway_id = request.args.get('master-gateway-id')[0]
                if submitted_gateway_master_gateway_id == 'local':
                    submitted_gateway_is_master = 1
                    submitted_gateway_master_gateway_id = None
                else:
                    submitted_gateway_is_master = 0
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Master Gateway.")

            # print("b13: %s - %s" % (submitted_gateway_is_master, submitted_gateway_master_gateway_id))
            # print("valid: %s" % valid_submit)
            try:
                submitted_security_status = request.args.get('security-status')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid Gateway Device Send Status.")

            # print("b14")
            # print("valid: %s" % valid_submit)
            try:
                submitted_security_gps_status = request.args.get('security-gps-status')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid GPS Location Send Status value.")

            if valid_submit is False:
                return webinterface.redirect(request, '/setup_wizard/4')

            # print("b15")
            # print("valid: %s" % valid_submit)
            try:
                submitted_security_send_private_stats = request.args.get('security-send-private-stats')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid send private stats.")

            # print("b16")
            # print("valid: %s" % valid_submit)
            if valid_submit is False:
                return webinterface.redirect(request, '/setup_wizard/4')

            try:
                submitted_security_send_anon_stats = request.args.get('security-send-anon-stats')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid send anonymous statistics.")

            # print("b17")
            # print("valid: %s" % valid_submit)
            if valid_submit is False:
                print("ccc")
                return webinterface.redirect(request, '/setup_wizard/4')

            session['setup_wizard_gateway_is_master'] = submitted_gateway_is_master
            session['setup_wizard_gateway_master_gateway_id'] = submitted_gateway_master_gateway_id
            session['setup_wizard_security_status'] = submitted_security_status
            session['setup_wizard_security_gps_status'] = submitted_security_gps_status
            session['setup_wizard_security_send_private_stats'] = submitted_security_send_private_stats
            session['setup_wizard_security_send_anon_stats'] = submitted_security_send_anon_stats

            # print("22222 %s" % session['setup_wizard_security_send_private_stats'])
            # print("33333 %s" % session['setup_wizard_security_send_anon_stats'])
            page = yield page_setup_wizard_5_show_form(webinterface, request, session)
            return page

        @inlineCallbacks
        def page_setup_wizard_5_show_form(webinterface, request, session):
            def first(s):
                return next(iter(s.items()))

            gpg_selected = session.get("gpg_selected", "new")
            # i18n = webinterface.i18n(request)
            session.set('setup_wizard_last_step', 5)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/5.html')
            gpg_existing = yield webinterface._LocalDB.get_gpg_key()
            gpg_existing_sorted = OrderedDict(sorted(gpg_existing.items(), key=lambda x: x[1]['created_at']))
            if len(gpg_existing_sorted) > 0:
                print(first(gpg_existing_sorted)[0])
                gpg_selected = first(gpg_existing_sorted)[0]

            return page.render(
                gpg_selected=gpg_selected,
                gpg_existing=gpg_existing_sorted,
                # _=i18n,
                )

        @webapp.route('/5_gpg_section')
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_5_gpg_section(webinterface, request, session):

            if session.get('setup_wizard_last_step') != 5:
                return "Invalid wizard state. No content found."

            gpg_existing = yield webinterface._LocalDB.get_gpg_key()

            valid_submit = True
            try:
                submitted_gpg_action = request.args.get('gpg_action')[0]
            except:
                valid_submit = False
                webinterface.add_alert("Invalid GPG action.")

            if valid_submit is False:
                return "invalid submit"

            if submitted_gpg_action == "new":
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/5_gpg_new.html')
                return page.render(
                                   alerts=webinterface.get_alerts(),
                                   )

            elif submitted_gpg_action == "import":
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/5_gpg_import.html')
                return page.render(
                                   alerts=webinterface.get_alerts(),
                                   )
            elif submitted_gpg_action in gpg_existing:
                page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/5_gpg_existing.html')
                return page.render(
                                   alerts=webinterface.get_alerts(),
                                   key=gpg_existing[submitted_gpg_action]
                                   )
            else:
                return "Invalid GPG selection."

        @webapp.route('/6', methods=['GET'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_6_get(webinterface, request, session):
            if session.get('setup_wizard_last_step', 1) not in (5, 6, 7):
                webinterface.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            session['setup_wizard_last_step'] = 6
            results = yield form_setup_wizard_6(webinterface, request, session)
            return results

        @webapp.route('/6', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_6_post(webinterface, request, session):
            """
            Last step is to handle the GPG key. One of: create a new one, import one, or select an existing one.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            result_output = ""
            if session.get('setup_wizard_last_step', 1) not in (5, 6):
                webinterface.add_alert("Invalid wizard state. Please don't use the browser forward or back buttons.")
                return webinterface.redirect(request, '/setup_wizard/1')

            session.set('setup_wizard_6_post', 1)
            try:
                submitted_gpg_action = request.args.get('gpg_action')[0]  # underscore here due to jquery
            except:
                webinterface.add_alert("Please select an appropriate GPG/PGP Key action.")
                return webinterface.redirect(request, '/setup_wizard/5')

            if session['setup_wizard_gateway_id'] == 'new':
                data = {
                    'machine_label': session['setup_wizard_gateway_machine_label'],
                    'label': session['setup_wizard_gateway_label'],
                    'description': session['setup_wizard_gateway_description'],
                }
                try:
                    results = yield webinterface._YomboAPI.request('POST', '/v1/gateway',
                                                                   data,
                                                                   session['yomboapi_session'])
                except YomboWarning as e:
                    webinterface.add_alert(e.html_message, 'warning')
                    return webinterface.redirect(request, '/setup_wizard/3')
                session['setup_wizard_gateway_id'] = results['data']['id']

            else:
                data = {
                    'label': session['setup_wizard_gateway_label'],
                    'description': session['setup_wizard_gateway_description'],
                }
                results = yield webinterface._YomboAPI.request(
                    'PATCH', '/v1/gateway/%s' % session['setup_wizard_gateway_id'],
                    data,
                    session=session['yomboapi_session'])
                if results['code'] > 299:
                    webinterface.add_alert(results['content']['html_message'], 'warning')
                    return webinterface.redirect(request, '/setup_wizard/5')

                results = yield webinterface._YomboAPI.request('GET', '/v1/gateway/%s/new_hash' % session['setup_wizard_gateway_id'],
                                                               session=session['yomboapi_session'])
                if results['code'] > 299:
                    webinterface.add_alert(results['content']['html_message'], 'warning')
                    return webinterface.redirect(request, '/setup_wizard/5')

            # webinterface._Configs.set('core', 'updated', results['data']['updated_at'])
            # webinterface._Configs.set('core', 'created', results['data']['created_at'])
            # print("new gwid: %s" % results['data']['id'])
            # print("got gwid before set: %s" % webinterface._Configs.get('core', 'gwid'))
            webinterface._Configs.set('core', 'gwid', results['data']['id'])
            webinterface._Configs.set('core', 'gwuuid', results['data']['uuid'])
            webinterface._Configs.set('core', 'api_auth', results['data']['api_auth'])
            webinterface._Configs.set('core', 'machine_label', session['setup_wizard_gateway_machine_label'])
            webinterface._Configs.set('core', 'label', session['setup_wizard_gateway_label'])
            webinterface._Configs.set('core', 'description', session['setup_wizard_gateway_description'])
            webinterface._Configs.set('core', 'gwhash', results['data']['hash'])
            webinterface._Configs.set('core', 'is_master', is_true_false(session['setup_wizard_gateway_is_master']))
            webinterface._Configs.set('core', 'master_gateway_id', session['setup_wizard_gateway_master_gateway_id'])
            webinterface._Configs.set('security', 'amqpsenddevicestatus', session['setup_wizard_security_status'])
            webinterface._Configs.set('security', 'amqpsendgpsstatus', session['setup_wizard_security_gps_status'])
            webinterface._Configs.set('security', 'amqpsendprivatestats', session['setup_wizard_security_send_private_stats'])
            webinterface._Configs.set('security', 'amqpsendanonstats', session['setup_wizard_security_send_anon_stats'])
            webinterface._Configs.set('location', 'latitude', session['setup_wizard_gateway_latitude'])
            webinterface._Configs.set('location', 'longitude', session['setup_wizard_gateway_longitude'])
            webinterface._Configs.set('location', 'elevation', session['setup_wizard_gateway_elevation'])
            webinterface._Configs.set('core', 'first_run', False)

            # Remove wizard settings...
            for session_key in list(session.keys()):
                if session_key.startswith('setup_wizard_'):
                    del session[session_key]
            session['setup_wizard_done'] = True
            session['setup_wizard_last_step'] = 7

            if submitted_gpg_action == 'new':  # make GPG keys!
                logger.info("New gpg key will be generated on next restart.")
            elif submitted_gpg_action == 'import':  # make GPG keys!
                try:
                    submitted_gpg_private = request.args.get('gpg-private-key')[0]
                except:
                    webinterface.add_alert("When importing, must have a valid private GPG/PGP key.")
                    return webinterface.redirect(request, '/setup_wizard/5')
                try:
                    submitted_gpg_public = request.args.get('gpg-public-key')[0]
                except:
                    webinterface.add_alert("When importing, must have a valid public GPG/PGP key.")
                    return webinterface.redirect(request, '/setup_wizard/5')
            else:
                gpg_existing = yield webinterface._LocalDB.get_gpg_key()
                if submitted_gpg_action in gpg_existing:
                    key_ascii = webinterface._GPG.get_key(submitted_gpg_action)
                    webinterface._Configs.set('gpg', 'keyid', submitted_gpg_action)
                    webinterface._Configs.set('gpg', 'keyascii', key_ascii)
                else:
                    webinterface.add_alert("Existing GPG/PGP key not fount.")
                    return webinterface.redirect(request, '/setup_wizard/5')

            session['gpg_selected'] = submitted_gpg_action
            session['setup_wizard_last_step'] = 6

            results = yield form_setup_wizard_6(webinterface, request, session)
            return results

        @inlineCallbacks
        def form_setup_wizard_6(webinterface, request, session):
            try:
                dns_results = yield webinterface._YomboAPI.request('GET',
                                                                   '/v1/gateway/%s/dns_name' % webinterface._Configs.get(
                                                                       'core', 'gwid'),
                                                                   session=session['yomboapi_session'])
            except YomboWarning as e:
                # webinterface.add_alert(e.html_message, 'warning')
                # webinterface.add_alert(dns_results['content']['html_message'], 'warning')
                webinterface._Configs.set('dns', 'dns_name', None)
                webinterface._Configs.set('dns', 'dns_domain', None)
                webinterface._Configs.set('dns', 'dns_domain_id', None)
                webinterface._Configs.set('dns', 'allow_change_at', 0)
                webinterface._Configs.set('dns', 'fqdn', None)
            else:
                webinterface._Configs.set('dns', 'dns_name', dns_results['data']['dns_name'])
                webinterface._Configs.set('dns', 'dns_domain', dns_results['data']['dns_domain'])
                webinterface._Configs.set('dns', 'dns_domain_id', dns_results['data']['dns_domain_id'])
                webinterface._Configs.set('dns', 'allow_change_at', dns_results['data']['allow_change_at'])
                webinterface._Configs.set('dns', 'fqdn', dns_results['data']['fqdn'])

            dns_fqdn = webinterface._Configs.get('dns', 'fqdn', None)
            dns_name = webinterface._Configs.get('dns', 'dns_name', None)
            dns_domain = webinterface._Configs.get('dns', 'dns_domain', None)
            allow_change = webinterface._Configs.get('dns', 'allow_change_at', 0)
            fqdn = webinterface._Configs.get('dns', 'fqdn', None, False)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/6.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                dns_fqdn=dns_fqdn,
                dns_name=dns_name,
                dns_domain=dns_domain,
                allow_change=allow_change,
                fqdn=fqdn,
                current_time=time()
            )

        @webapp.route('/7', methods=['GET'])
        @require_auth()
        def page_setup_wizard_7_get(webinterface, request, session):
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/7.html')

            session['setup_wizard_last_step'] = 7
            return page.render(
                alerts=webinterface.get_alerts(),
            )

        @webapp.route('/7', methods=['POST'])
        @require_auth()
        @inlineCallbacks
        def page_setup_wizard_7_post(webinterface, request, session):
            """
            Last step is to handle the DNS. Either create a new one, skip, or edit existing.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            try:
                submitted_dns_name = request.args.get('dns_name')[0]  # underscore here due to jquery
            except:
                webinterface.add_alert("Select a valid dns name.")
                return webinterface.redirect(request, '/setup_wizard/6')

            try:
                submitted_dns_domain = request.args.get('dns_domain_id')[0]  # underscore here due to jquery
            except:
                print("SW7 - 6")
                webinterface.add_alert("Select a valid dns domain.")
                return webinterface.redirect(request, '/setup_wizard/6')
            print("SW7 - 7")

            data = {
                'dns_name': submitted_dns_name,
                'dns_domain_id': submitted_dns_domain,
            }
            print("SW7 - 10: %s" % data)

            try:
                dns_results = yield webinterface._YomboAPI.request('POST',
                                                                   '/v1/gateway/%s/dns_name' % webinterface._Configs.get(
                                                                       'core', 'gwid'),
                                                                   data,
                                                                   session=session['yomboapi_session'])
                print("SW7 - 11: %s" % dns_results)
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, 'warning')
                return webinterface.redirect(request, 'pages/setup_wizard/6')

            print("SW7 - 12")

            session['setup_wizard_last_step'] = 7
            print("SW7 - 13")

            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/setup_wizard/7.html')
            return page.render(
                               alerts=webinterface.get_alerts(),
                               )


        @webapp.route('/7_restart', methods=['GET'])
        @require_auth()
        def page_setup_wizard_7_restart(webinterface, request, session):
            webinterface._Configs.set('core', 'first_run', False)
            return webinterface.restart(request)
    #        auth = webinterface.require_auth(request)  # Notice difference. Now we want to log the user in.
    #        if auth is not None:
    #            return auth

    #        if webinterface._WebSessions.get(request, 'setup_wizard_done') is not True:
    #            return webinterface.redirect(request, '/setup_wizard/5')

    #     @webapp.route('/setup_wizard/static/', branch=True)
    #     def setup_wizard_static(self, request):
    #         return File(self._current_dir + "/lib/webinterface/pages/setup_wizard/static")
