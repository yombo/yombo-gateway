import base64
import json
import os
import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.web.static import File

from yombo.lib.webinterface.auth import require_auth
from yombo.utils import read_file, bytes_to_unicode, unicode_to_bytes

def route_system(webapp):
    with webapp.subroute("/system") as webapp:
        @webapp.route('/')
        @require_auth()
        def page_modules(webinterface, request, session):
            return webinterface.redirect(request, '/system/index')

        @webapp.route('/index')
        @require_auth()
        def page_system_index(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/system/index.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/backup')
        @require_auth()
        def page_system_backup(webinterface, request, session):
            db_size = os.path.getsize("usr/etc/yombo.db")
            page = webinterface.get_template(request, webinterface._dir + 'pages/system/backup.html')
            return page.render(alerts=webinterface.get_alerts(),
                               db_size=db_size
                               )

        @webapp.route('/backup/configuration', methods=['POST', 'GET'])
        @require_auth()
        @inlineCallbacks
        def page_system_backup_config(webinterface, request, session):
            request.setHeader('Content-Description', 'File Transfer')
            request.setHeader('Content-Type', 'text/text')
            # request.setHeader('Content-Type', 'application/octet-stream')
            request.setHeader('Content-Disposition', 'attachment; filename=yombo_configuration.ybo')
            request.setHeader('Content-Transfer-Encoding', 'binary')
            request.setHeader('Expires', '0')
            request.setHeader('Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
            request.setHeader('Pragma', 'public')

            try:
                password1 = request.args.get('password1')[0]
                password2 = request.args.get('password2')[0]
                if password1 != password2:
                    webinterface.add_alert('Encryption passwords do not match.', 'warning')
                    db_size = os.path.getsize("usr/etc/yombo.db")
                    page = webinterface.get_template(request, webinterface._dir + 'pages/system/backup.html')
                    return page.render(alerts=webinterface.get_alerts(),
                                       db_size=db_size
                                       )
            except Exception:
                password1 = None

            yombo_ini = yield read_file('yombo.ini')
            key = webinterface._GPG.gpg_key_full
            sslcerts = {}
            for sslname, cert in webinterface._SSLCerts.managed_certs.items():
                sslcerts[sslname] = {
                    'current_cert': cert.current_cert,
                    'current_chain': cert.current_chain,
                    'current_key': cert.current_key,
                    'next_cert': cert.next_cert,
                    'next_chain': cert.next_chain,
                    'next_key': cert.next_key,
                }

            core_output = {
                'yombo.ini': yombo_ini,
                'gpg_pass': key['passphrase'],
                'gpg_private': key['privatekey'],
                'gpg_public': key['publickey'],
                'sslcerts': sslcerts,
            }
            output = json.dumps(bytes_to_unicode(core_output))
            encrypted = False
            if password1 is not None:
                output = yield webinterface._GPG.encrypt_aes(password1, output)
                encrypted = True

            encoded_output = base64.b64encode(unicode_to_bytes(output))
            final_out = {
                'encrypted': encrypted,
                'time': int(time.time()),
                'created:': time.strftime("%c"),
                'backup_version': 1,
                'data': encoded_output
            }
            return json.dumps(bytes_to_unicode(final_out))

        @webapp.route('/backup/database')
        @require_auth()
        def page_system_backup_database(webinterface, request, session):
            request.setHeader('Content-Description', 'File Transfer')
            request.setHeader('Content-Type', 'application/octet-stream')
            request.setHeader('Content-Disposition', 'attachment; filename=yombo.db')
            request.setHeader('Content-Transfer-Encoding', 'binary')
            request.setHeader('Expires', '0')
            request.setHeader('Cache-Control', 'must-revalidate, post-check=0, pre-check=0')
            request.setHeader('Pragma', 'public')
            # webinterface._LocalDB.make_backup()
            return File("%s/usr/etc/yombo.db" % webinterface._Atoms.get('yombo.path'))

        @webapp.route('/control')
        @require_auth()
        def page_system_control(webinterface, request, session):
            page = webinterface.get_template(request, webinterface._dir + 'pages/system/control.html')
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route('/control/restart')
        @require_auth()
        def page_system_control_restart(webinterface, request, session):
            return webinterface.restart(request)

        @webapp.route('/control/shutdown')
        @require_auth()
        def page_system_control_shutdown(webinterface, request, session):
            return webinterface.shutdown(request)

