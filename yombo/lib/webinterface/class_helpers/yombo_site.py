"""
Responsible for running the website.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/class_helpers/yombo_site.html>`_
"""
# Import python libraries
from time import time

# Import twisted libraries
from twisted.web.server import Site
from twisted.internet.task import LoopingCall


class Yombo_Site(Site):

    def setup_log_queue(self, webinterface):
        self.save_log_queue_loop = LoopingCall(self.save_log_queue)
        self.save_log_queue_loop.start(31.7, False)

        self.log_queue = []

        self.webinterface = webinterface
        self.db_save_log = self.webinterface._LocalDB.webinterface_save_logs

    def _escape(self, s):
        """
        Return a string like python repr, but always escaped as if surrounding
        quotes were double quotes.
        @param s: The string to escape.
        @type s: L{bytes} or L{unicode}
        @return: An escaped string.
        @rtype: L{unicode}
        """
        if not isinstance(s, bytes):
            s = s.encode("ascii")

        r = repr(s)
        if not isinstance(r, str):
            r = r.decode("ascii")
        if r.startswith(u"b"):
            r = r[1:]
        if r.startswith(u"'"):
            return r[1:-1].replace(u'"', u'\\"').replace(u"\\'", u"'")
        return r[1:-1]

    def log(self, request):
        """
        This is magically called by the Twisted framework unicorn: twisted.web.http:Request.finish()

        :param request:
        :return:
        """
        ignored_extensions = (".png", ".js", ".css", ".jpg", ".jpeg", ".gif", ".ico", ".woff2", ".map",
                              "site.webmanifest")
        url_path = request.path.decode().strip()
        if any(url_path.endswith(ext) for ext in ignored_extensions):
            return

        if request.getClientIP() == "127.0.0.1" and url_path.startswith("/api/v1/mqtt/auth/"):
            return

        if hasattr(request, "auth"):
            if request.auth is None:
                user_id = None
            else:
                user_id = request.auth.safe_display
        else:
            # print(f"request has no auth! : {request}")
            user_id = None

        self.log_queue.append({
            "request_at": time(),
            "request_protocol": request.clientproto.decode().strip(),
            "referrer": self._escape(request.getHeader(b"referer") or b"-").strip(),
            "agent": self._escape(request.getHeader(b"user-agent") or b"-").strip(),
            "ip": request.getClientIP(),
            "hostname": request.getRequestHostname().decode().strip(),
            "method": request.method.decode().strip(),
            "path": url_path,
            "secure": request.isSecure(),
            "auth_id": user_id,
            "response_code": request.code,
            "response_size": request.sentLength,
            "uploadable": 1,
            "uploaded": 0,
            }
        )

    def save_log_queue(self):
        if len(self.log_queue) > 0:
            queue = self.log_queue
            self.log_queue = []
            self.db_save_log(queue)
