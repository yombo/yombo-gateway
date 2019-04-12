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

        @webapp.route("/status")
        @require_auth()
        def page_system_index(webinterface, request, session):
            session.has_access("system_options", "*", "status", raise_error=True)
            delayed_calls = reactor.getDelayedCalls()
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/system/index.html")
            return page.render(alerts=webinterface.get_alerts(),
                               delayed_calls=delayed_calls,
                               )

        @webapp.route("/backup/database")
        @require_auth()
        def page_system_backup_database(webinterface, request, session):
            session.has_access("system_options", "*", "backup", raise_error=True)
            request.setHeader("Content-Description", "File Transfer")
            request.setHeader("Content-Type", "application/octet-stream")
            request.setHeader("Content-Disposition", "attachment; filename=yombo.sqlite3")
            request.setHeader("Content-Transfer-Encoding", "binary")
            request.setHeader("Expires", "0")
            request.setHeader("Cache-Control", "must-revalidate, post-check=0, pre-check=0")
            request.setHeader("Pragma", "public")
            # webinterface._LocalDB.make_backup()
            return File(f"{webinterface.working_path}/etc/yombo.sqlite3")

        @webapp.route("/control")
        @require_auth()
        def page_system_control(webinterface, request, session):
            session.has_access("system_options", "*", "control", raise_error=True)
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/system/control.html")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route("/control/restart")
        @require_auth()
        def page_system_control_restart(webinterface, request, session):
            session.has_access("system_options", "*", "control", raise_error=True)
            return webinterface.restart(request)

        @webapp.route("/control/shutdown")
        @require_auth()
        def page_system_control_shutdown(webinterface, request, session):
            session.has_access("system_options", "*", "control", raise_error=True)
            return webinterface.shutdown(request)

