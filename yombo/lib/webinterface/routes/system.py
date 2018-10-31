import base64
import hashlib
import json
import os
import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.static import File

from yombo.lib.webinterface.auth import require_auth
from yombo.utils import read_file, bytes_to_unicode, unicode_to_bytes

def route_system(webapp):
    with webapp.subroute("/system") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_modules(webinterface, request, session):
            session.has_access('system_options', '*', 'status', raise_error=True)
            return webinterface.redirect(request, '/system/status')

        @webapp.route('/status')
        @require_auth()
        def page_system_index(webinterface, request, session):
            session.has_access('system_options', '*', 'status', raise_error=True)
            delayed_calls = reactor.getDelayedCalls()
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/system/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               delayed_calls=delayed_calls,
                               )

        @webapp.route('/backup')
        @require_auth()
        def page_system_backup(webinterface, request, session):
            session.has_access('system_options', '*', 'backup', raise_error=True)
            db_size = os.path.getsize("%s/etc/yombo.db" % webinterface.working_dir)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/system/backup.html')
            return page.render(alerts=webinterface.get_alerts(),
                               db_size=db_size
                               )

        @webapp.route('/backup/configuration', methods=['POST', 'GET'])
        @require_auth()
        @inlineCallbacks
        def page_system_backup_config(webinterface, request, session):
            session.has_access('system_options', '*', 'backup', raise_error=True)
            try:
                password1 = request.args.get('password1')[0]
                password2 = request.args.get('password2')[0]
                if password1 != password2:
                    webinterface.add_alert('Encryption passwords do not match.', 'danger')
                    db_size = os.path.getsize("%s/etc/yombo.db" % webinterface.working_dir)
                    page = webinterface.get_template(request, webinterface.wi_dir + '/pages/system/backup.html')
                    return page.render(alerts=webinterface.get_alerts(),
                                       db_size=db_size
                                       )
            except Exception:
                password1 = None

            # yombo_ini = yield read_file('yombo.ini')
            sslcerts = {}
            for sslname, cert in webinterface._SSLCerts.managed_certs.items():
                sslcerts[sslname] = cert.asdict()

            key = webinterface._GPG.gpg_key_full
            yombo_ini = yield webinterface._Configs.generate_yombo_ini()
            gpg_trust = yield webinterface._GPG.export_trust()
            core_output = {
                'yombo_ini': yombo_ini,
                'gateway_label': webinterface._Configs.get('core', 'label'),
                'gpg_fingerprint': key['fingerprint'],
                'gpg_keys': webinterface._GPG._gpg_keys,
                'gpg_trust': gpg_trust,
                'gw_id': webinterface.gateway_id(),
                'sslcerts': sslcerts,
                'configs': {
                    'dns': webinterface._Configs.get('dns', '*')
                }
            }
            # print("yombo_ini output: %s" % yombo_ini)
            output = json.dumps(bytes_to_unicode(core_output))
            encrypted = False
            if password1 is not None:
                output = yield webinterface._GPG.encrypt_aes(password1, output)
                encrypted = True

            encoded_output = base64.b64encode(unicode_to_bytes(output))
            final_out = {
                'gateway_label': webinterface._Configs.get('core', 'label'),
                'created': time.strftime("%c"),
                'file_type': 'yombo configuration backup',
                'encrypted': encrypted,
                'time': int(time.time()),
                'backup_version': 2,
                'hash': hashlib.sha256(encoded_output).hexdigest(),
                'data': encoded_output
            }

            request.setHeader('Content-Description', 'File Transfer')
            request.setHeader('Content-Type', 'text/text')
            request.setHeader('Content-Disposition', 'attachment; filename=yombo_configuration.ybo')
            request.setHeader('Content-Transfer-Encoding', 'binary')
            request.setHeader('Expires', '0')
            request.setHeader('Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
            request.setHeader('Pragma', 'public')
            return json.dumps(bytes_to_unicode(final_out))

        @webapp.route('/backup/database')
        @require_auth()
        def page_system_backup_database(webinterface, request, session):
            session.has_access('system_options', '*', 'backup', raise_error=True)
            request.setHeader('Content-Description', 'File Transfer')
            request.setHeader('Content-Type', 'application/octet-stream')
            request.setHeader('Content-Disposition', 'attachment; filename=yombo.db')
            request.setHeader('Content-Transfer-Encoding', 'binary')
            request.setHeader('Expires', '0')
            request.setHeader('Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
            request.setHeader('Pragma', 'public')
            # webinterface._LocalDB.make_backup()
            return File("%s/etc/yombo.db" % webinterface.working_path)

        @webapp.route('/control')
        @require_auth()
        def page_system_control(webinterface, request, session):
            session.has_access('system_options', '*', 'control', raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/system/control.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/control/restart')
        @require_auth()
        def page_system_control_restart(webinterface, request, session):
            session.has_access('system_options', '*', 'control', raise_error=True)
            return webinterface.restart(request)

        @webapp.route('/control/shutdown')
        @require_auth()
        def page_system_control_shutdown(webinterface, request, session):
            session.has_access('system_options', '*', 'control', raise_error=True)
            return webinterface.shutdown(request)

