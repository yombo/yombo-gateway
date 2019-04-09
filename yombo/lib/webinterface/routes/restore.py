"""
Handles pages relating to restoring gateway configurations.
"""
import base64
import json
import hashlib

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth, run_first
from yombo.core.log import get_logger
from yombo.utils import unicode_to_bytes, bytes_to_unicode

logger = get_logger("library.webinterface.routes.restore")


def route_restore(webapp):
    with webapp.subroute("/restore") as webapp:

        @webapp.route("/restore_details")
        @inlineCallbacks
        def page_restore_details(webinterface, request, session):
            """
            Prompts user to upload the configuration file to restore the gateway.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            try:
                restorefile = request.args.get("restorefile")[0]
                try:
                    restorefile = json.loads(restorefile)
                    logger.info("Received configuration backup file.")
                    try:
                        if restorefile["hash"] != hashlib.sha256(unicode_to_bytes(restorefile["data"])).hexdigest():
                            webinterface.add_alert("Backup file appears to be corrupt: Invalid checksum.")
                            return webinterface.redirect("/misc/gateway_setup")
                        restorefile["data"] = base64.b64decode(unicode_to_bytes(restorefile["data"]))
                    except Exception as e:
                        logger.warn("Unable to b64decode data: {e}", e=e)
                        webinterface.add_alert("Unable to properly decode pass 1 of data segment of restore file.")
                        return webinterface.redirect("/misc/gateway_setup")

                    session.set("restore_backup_file", restorefile)
                except Exception as e:
                    logger.warn("Unable to parse JSON phase 2: {e}", e=e)
                    webinterface.add_alert("Invalid restore file contents.")
                    return webinterface.redirect("/misc/gateway_setup")
            except Exception:
                restorefile = session.get("restore_backup_file", None)
                if restorefile is None:
                    webinterface.add_alert("No restore file found.")
                    return webinterface.redirect("/misc/gateway_setup")

            required_keys = ("encrypted", "time", "file_type", "created", "backup_version")
            if all(required in restorefile for required in required_keys) is False:
                webinterface.add_alert("Backup file appears to be missing important parts.")
                return webinterface.redirect("/misc/gateway_setup")

            if restorefile["encrypted"] is True:
                try:
                    password = request.args.get("password",)[0]
                except Exception:
                    password = session.get("restorepassword", None)

                if password is None:
                    page = webinterface.get_template(request, webinterface.wi_dir + "/pages/setup_wizard/restore_password.html")
                    return page.render(
                        alerts=session.get_alerts(),
                        restore=restorefile
                    )

                try:
                    decrypted = yield webinterface._GPG.decrypt_aes(password, restorefile["data"])
                    restorefile["data_processed"] = json.loads(bytes_to_unicode(decrypted))
                except Exception as e:
                    logger.warn("Unable to decrypt restoration file: {e}", e=e)
                    webinterface.add_alert("It appears the password is incorrect.", "danger")
                    page = webinterface.get_template(request, webinterface.wi_dir + "/pages/setup_wizard/restore_password.html")
                    return page.render(
                        alerts=session.get_alerts(),
                        restore=restorefile
                    )
            else:  #no password
                restorefile["data_processed"] = json.loads(bytes_to_unicode(restorefile["data"]))

            session.set("restore_backup_file", restorefile)

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/restore/restore_ready.html")
            return page.render(
                alerts=session.get_alerts(),
                restore=session.get("restore_backup_file")
            )

        @webapp.route("/restore_complete",)
        @inlineCallbacks
        def page_setup_wizard_restore_complete(webinterface, request, session):
            """
            Prompts user to upload the configuration file to restore the gateway.

            :param webinterface:
            :param request:
            :param session:
            :return:
            """
            restorefile = session.get("restore_backup_file", None)
            if restorefile is None:
                webinterface.add_alert("No restore data found.")
                return page_show_wizard_home(webinterface, request, session)

            working_path = webinterface._Atoms.get("working_path")
            data = restorefile["data_processed"]

            for section, options in data["configs"].items():
                for option, value in options.items():
                    webinterface._Configs.set(section, option, value)
            for fingerprint, key in data["gpg_keys"].items():
                if key["publickey"] != None:
                    yield webinterface._GPG.import_to_keyring(key["publickey"])
                if key["privatekey"] != None:
                    yield webinterface._GPG.import_to_keyring(key["privatekey"])
                if key["passphrase"] != None:

                    filename = f"{working_path}/etc/gpg/{key['fingerprint']}.pass"
                    yield save_file(filename, key["passphrase"])
                if data["gpg_fingerprint"] == key["fingerprint"]:
                    filename = f"{working_path}/etc/gpg/last.pass"
                    yield save_file(filename, key["passphrase"])

            for cert_name, cert in data["sslcerts"].items():
                webinterface._SSLCerts.add_sslcert(cert)

            webinterface._Configs.exit_config_file = data["yombo_ini"]
            yield webinterface._GPG.import_trust(data["gpg_trust"])

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/restart.html")
            reactor.callLater(0.4, webinterface.do_restart)
            return page.render(
                               alerts=session.get_alerts(),
                               message="Configuration restored."
                               )
