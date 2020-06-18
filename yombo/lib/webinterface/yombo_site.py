"""
Responsible for running the website.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/mixins/yombo_site.html>`_
"""
# Import python libraries
from time import time
from typing import ClassVar

# Import twisted libraries
from twisted.web.server import Site
from twisted.internet.task import LoopingCall

from yombo.core.entity import Entity
from yombo.utils import random_string


class YomboSite(Entity, Site):
    _Entity_type: ClassVar[str] = "YomboSite"

    def __init__(self, parent, *args, **kwargs):
        """
        Setup looping call to periodically save web logs to the database.

        :param incoming: A command containing required items to setup.
        :type incoming: dict
        :return: None
        """
        super().__init__(parent, *args, **kwargs)
        self.save_log_queue_loop = LoopingCall(self.save_log_queue)
        self.save_log_queue_loop.start(31.7, False)
        self.log_queue = []

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
        if hasattr(request, "request_id") is False:
            request.request_id = random_string(length=20)
        if hasattr(request, "request_context") is False:
            request.request_context = None
        ignored_extensions = (".png", ".js", ".css", ".jpg", ".jpeg", ".gif", ".ico", ".woff2", ".map",
                              "site.webmanifest")
        url_path = request.path.decode().strip()
        if any(url_path.endswith(ext) for ext in ignored_extensions):
            return

        if request.getClientIP() == "127.0.0.1" and url_path.startswith("/api/v1/mqtt/auth/"):
            return

        accessor_id = None
        accessor_type = None
        if hasattr(request, "auth") and request.auth is not None:
            accessor_id = request.auth.accessor_id
            accessor_type = request.auth.accessor_type

        self.log_queue.append({
            "request_at": round(time(), 4),
            "request_id": request.request_id,
            "request_protocol": request.clientproto.decode().strip(),
            "referrer": self._escape(request.getHeader(b"referer") or b"-").strip(),
            "agent": self._escape(request.getHeader(b"user-agent") or b"-").strip(),
            "ip": request.getClientIP(),
            "hostname": request.getRequestHostname().decode().strip(),
            "method": request.method.decode().strip(),
            "path": url_path,
            "secure": request.isSecure(),
            "request_by": accessor_id,
            "request_by_type": accessor_type,
            "request_context": request.request_context,
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
            self._LocalDB.database.db_insert("web_logs", queue)
