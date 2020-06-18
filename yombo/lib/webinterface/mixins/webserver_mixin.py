"""
Responsible for starting/restarting/stopping the web server. This is a mixing class
to the :ref:`WebInterface <webinterface>` library.

Also requests the SSL cert from the sslcert library.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/mixins/webserver.html>`_
"""
# Import python libraries
from time import time

# Import twisted libraries
from twisted.internet import reactor, ssl
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.builddist")


class WebServerMixin:
    """
    Handles setting up, restarting, and stopping the webserver.
    """
    @inlineCallbacks
    def start_web_servers(self):
        """
        Start the web server that serves the webinterface and frontend application.

        :return:
        """
        if self.already_starting_web_servers is True:
            return
        self.already_starting_web_servers = True
        logger.debug("starting web servers")
        if self.web_server_started is False:
            if self.wi_port_nonsecure.value == 0:
                logger.warn("Non secure port has been disabled. With gateway stopped, edit yomobi.toml and change: webinterface->nonsecure_port")
            else:
                self.web_server_started = True
                port_attempts = 0
                while port_attempts < 100:
                    try:
                        self.web_interface_listener = reactor.listenTCP(self.wi_port_nonsecure.value+port_attempts,
                                                                        self.web_factory)
                        break
                    except Exception as e:
                        port_attempts += 1
                if port_attempts >= 100:
                    logger.warn("Unable to start web server, no available port could be found. Tried: {starting} - {ending}",
                                starting=self.wi_port_secure.value, ending=self.wi_port_secure.value+port_attempts)
                elif port_attempts > 0:
                    self._Configs.set("webinterface.nonsecure_port", self.wi_port_nonsecure.value+port_attempts)
                    logger.warn(
                        "Web interface is on a new port: {new_port}", new_port=self.wi_port_nonsecure.value+port_attempts)

        if self.web_server_ssl_started is False:
            if self.wi_port_secure.value == 0:
                logger.warn("Secure port has been disabled. With gateway stopped, edit yomobi.toml and change: webinterface->secure_port")
                return

            self.web_server_ssl_started = True
            cert = yield self._SSLCerts.get("lib_webinterface")

            if cert["key_crypt"] is None or cert["cert_crypt"] is None:
                logger.warn("Unable to start secure web interface, cert is not valid.")
                return

            contextFactory = ssl.CertificateOptions(privateKey=cert["key_crypt"],
                                                    certificate=cert["cert_crypt"],
                                                    extraCertChain=cert["chain_crypt"])
            port_attempts = 0
            # print("########### WEBINTER: about to start SSL port listener")

            while port_attempts < 100:
                try:
                    # print("about to start ssl listener on port: %s" % self.wi_port_secure.value)
                    self.web_interface_ssl_listener = reactor.listenSSL(self.wi_port_secure.value+port_attempts,
                                                                        self.web_factory,
                                                                        contextFactory)
                    break
                except Exception as e:
                    logger.warn(f"Unable to start secure web server: {e}", e=e)
                    port_attempts += 1
            if port_attempts >= 100:
                logger.warn("Unable to start secure web server, no available port could be found. Tried: {starting} - {ending}",
                            starting=self.wi_port_secure.value, ending=self.wi_port_secure.value+port_attempts)
            elif port_attempts > 0:
                self._Configs.set("webinterface.secure_port", self.wi_port_secure.value+port_attempts)
                logger.warn(
                    "Secure (tls/ssl) web interface is on a new port: {new_port}", new_port=self.wi_port_secure.value+port_attempts)

        logger.debug("done starting web servers")
        self.already_starting_web_servers = False

    @inlineCallbacks
    def change_ports(self, port_nonsecure=None, port_secure=None):
        if port_nonsecure is None and port_secure is None:
            logger.info("Asked to change ports, but nothing has changed.")
            return

        if port_nonsecure is not None:
            if port_nonsecure != self.wi_port_nonsecure.value:
                self.wi_port_nonsecure.set(port_nonsecure)
                logger.info("Changing port for the non-secure web interface: {port}", port=port_nonsecure)
                if self.web_server_started:
                    yield self.web_interface_listener.stopListening()
                    self.web_server_started = False

        if port_secure is not None:
            if port_secure != self.wi_port_secure.value:
                self.wi_port_secure.set(port_secure)
                logger.info("Changing port for the secure web interface: {port}", port=port_secure)
                if self.web_server_ssl_started:
                    yield self.web_interface_ssl_listener.stopListening()
                    self.web_server_ssl_started = False

        yield self.start_web_servers()

    def _sslcerts_(self, **kwargs):
        """
        Called to collect to ssl cert requirements.

        :param kwargs:
        :return:
        """
        if self.fqdn.value is None:
            logger.warn("Unable to create webinterface SSL cert: DNS not set properly.")
            return
        cert = {}
        cert["sslname"] = "lib_webinterface"
        # Todo: remove adding the time to the renewal
        cert["sans"] = ["internal", "external", str(int(time()))]
        cert["cn"] = cert["sans"][0]
        cert["update_callback"] = self.new_ssl_cert
        return cert

    @inlineCallbacks
    def new_ssl_cert(self, newcert, **kwargs):
        """
        Called when a requested certificate has been signed or updated. If needed, this function
        will function will restart the SSL service if the current certificate has expired or is
        a self-signed cert.

        :param kwargs:
        :return:
        """
        logger.info("Got a new cert! About to install it.")
        if self.web_server_ssl_started is not None:
            yield self.web_interface_ssl_listener.stopListening()
            self.web_server_ssl_started = False
        yield self.start_web_servers()

    def display_how_to_access(self):
        if self._display_how_to_access_at > int(time()) - 60:
            return
        self._display_how_to_access_at = int(time())

        print("###########################################################")
        print("#                                                         #")
        if self._Loader.operating_mode != "run":
            print("# The Yombo Gateway website is running in                 #")
            print("# configuration only mode.                                #")
            print("#                                                         #")

        if self.fqdn.value == "127.0.0.1" or self.fqdn.value is None:
            local_hostname = "127.0.0.1"
            internal_hostname = self._Configs.get("networking.localipaddress.v4")
            external_hostname = self._Configs.get("networking.externalipaddress.v4")
            local = f"http://{local_hostname}:{self.wi_port_nonsecure.value}"
            internal = f"http://{internal_hostname}:{self.wi_port_nonsecure.value}"
            print("# The gateway can be accessed from the following urls:    #")
            print("#                                                         #")
            print("# On local machine:                                       #")
            print(f"#  {local:<54} #")
            print("#                                                         #")
            print("# On local network:                                       #")
            print(f"#  {internal:<54} #")
            if external_hostname is not None:
                print("#                                                         #")
                external = f"https://{external_hostname}:{self.wi_port_secure.value}"
                print("# From external network (check port forwarding):          #")
                print(f"#  {external:<54} #")
        else:
            website_url = f"http://{self.fqdn.value}"
            print("# The gateway can be accessed from the following url:     #")
            print("#                                                         #")
            print("# From anywhere:                                          #")
            print(f"#  {website_url:<54} #")

        print("#                                                         #")
        print("#                                                         #")
        print("###########################################################")
