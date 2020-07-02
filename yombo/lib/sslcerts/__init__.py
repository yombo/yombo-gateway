# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `SSLCerts @ Library Documentation <https://yombo.net/docs/libraries/sslcerts>`_

This library is responsible for managing SSL/TLS certs. It utilizes openssl to
generate keys and signing requests. It then forwards any signing requests (CSRs)
to Yombo for signing.

This library utilizes hooks to request what certs needs to be managed. A library or module
needs to return several things:

* sslname (required) - String - The name of a file to expect to load a key from.
* key_size (optional) - Int - Accepts a size of 2048 and 4096, default is 2048.
* key_type (optional) - String - Either "rsa" or "dsa", default is rsa.
* sans (optional) - List - A list of SAN (Subject Alternative Names)
* type (optional) - String - Either "client" or "server". (not implemented)

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/sslcerts/__init__.html>`_
"""
# Import python libraries
from OpenSSL import crypto
from ipaddress import ip_address
import os
import os.path
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
from uuid import uuid4

from time import time
from socket import gethostname

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.classes.dictobject import DictObject
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.ext.expiringdict import ExpiringDict
from yombo.utils import random_int, unicode_to_bytes, bytes_to_unicode
from yombo.utils.hookinvoke import global_invoke_all

from .sslcert import SSLCert

logger = get_logger("library.sslcerts")


class SSLCerts(YomboLibrary):
    """
    Responsible for managing various encryption and TLS (SSL) certificates.
    """
    managed_certs: ClassVar[dict] = {}
    received_message_for_unknown = ExpiringDict(100, 600)

    def __contains__(self, cert_requested):
        """
        Looks for an sslkey with the given sslname.

            >>> if "webinterface" in self._SSLCerts["lib_web"]:

        :param cert_requested: The ssl cert sslname to search for.
        :type cert_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        if cert_requested in self.managed_certs:
            return True
        else:
            return False

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        On startup, various libraries will need certs (webinterface, MQTT) for encryption. This
        module stores certificates in a directory so other programs can use certs as well. It's
        working data is stored in the database, while a backup is kept in the file system as well
        and is only used if the data is missing from the database.

        If a cert isn't avail for the requested sslname, it will receive a self-signed certificate.

        :return:
        """
        # Since SSL generation can take some time on slower devices, we use a simple queue system.
        self.generate_csr_queue = self._Queue.new("library.sslcerts.generate_csr", self.generate_csr)
        self.hostname = gethostname()

        self.local_gateway = self._Gateways.local

        self.self_signed_cert_path = self._Atoms.get("working_dir") + "/etc/certs/sslcert_selfsigned.cert.pem"
        self.self_signed_key_path = self._Atoms.get("working_dir") + "/etc/certs/sslcert_selfsigned.key.pem"
        self.self_signed_expires_at = self._Configs.get("sslcerts.self_signed_expires_at", None, False)
        self.self_signed_created_at = self._Configs.get("sslcerts.self_signed_created_at", None, False)
        self.default_key_size = self._Configs.get("sslcerts.default_key_size", 2048)
        self.self_signed_cert = None
        self.self_signed_key = None
        self.full_self_signed_cert = None
        yield self.check_if_self_signed_cert_is_needed()
        yield self.load_self_signed_cert()

        self.check_if_certs_need_update_loop = None

    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Starts the loop to check if any certs need to be updated.

        :return:
        """
        self.check_if_certs_need_update_loop = LoopingCall(self.check_if_certs_need_update)
        self.check_if_certs_need_update_loop.start(self._Configs.get("sqldicts.save_interval",
                                                                     random_int(3600*24, .1),
                                                                     False),
                                                   False)

        # Check if any libraries or modules need certs.
        if self.local_gateway.dns_name is None:
            logger.warn("Unable to generate sign ssl/tls certs, gateway has no domain name.")
            return

        if self._Loader.operating_mode != "run":
            return
        sslcerts = yield global_invoke_all("_sslcerts_", called_by=self)
        for component_name, ssl_certs in sslcerts.items():
            logger.debug(f"Adding new managed certs from hook: {component_name}")
            if isinstance(ssl_certs, tuple) is False and isinstance(ssl_certs, list) is False:
                ssl_certs = [ssl_certs]
            for ssl_item in ssl_certs:
                yield self.add_sslcert(ssl_item)

    def _stop_(self, **kwargs):
        """
        Simply stop any loops, tell all the certs to save themselves to disk as a backup.
        :return:
        """
        if hasattr(self, "check_if_certs_need_update_loop"):
            if self.check_if_certs_need_update_loop is not None and self.check_if_certs_need_update_loop.running:
                self.check_if_certs_need_update_loop.stop()

        if hasattr(self, "managed_certs"):
            for sslname, cert in self.managed_certs.items():
                cert._stop_()

    @inlineCallbacks
    def check_if_certs_need_update(self):
        """
        Called periodically to see if any certs need to be updated. Once a day is enough, we have 30 days to get this
        done.
        """

        for sslname, cert in self.managed_certs.items():
            yield cert.check_if_rotate_needed()

    @inlineCallbacks
    def check_if_self_signed_cert_is_needed(self):
        self_signed_key_file_exists = yield self._Files.exists(self.self_signed_key_path)
        sign_signed_exists = yield self._Files.exists(self.self_signed_cert_path)
        if sign_signed_exists is False or \
                self.self_signed_expires_at is None or \
                self.self_signed_expires_at < int(time() + (3600*24*30)) or \
                self.self_signed_created_at is None or \
                self_signed_key_file_exists is False:
            logger.info("Generating a self signed cert for SSL. This can take a few moments.")
            yield self._create_self_signed_cert()

    @inlineCallbacks
    def add_sslcert(self, ssl_data: dict, load_source: Optional[str] = None):
        """
        Called when new SSL Certs need to be managed.
        
        :param sslcerts: Dictionary of details for the cert.
        :param load_source: Accepts: 'file', 'hook'. Default is hook.
        :return: 
        """
        if load_source is None:
            load_source = "hook"
        logger.debug("add_sslcert: {ssl_data}", ssl_data=ssl_data)
        if self.local_gateway.dns_name is None:
            logger.warn("Unable to generate sign ssl/tls certs, gateway has no domain name.")
            return

        try:
            ssl_data = self.check_csr_input(ssl_data)  # Clean up module developers input.
        except YomboWarning as e:
            logger.warn(f"Cannot add cert: {e}")
            return

        if ssl_data["sslname"] in self.managed_certs:
            self.managed_certs[ssl_data["sslname"]].update(ssl_data)
        else:
            sslcert = SSLCert(self, DictObject(ssl_data), load_source)
            self.managed_certs[ssl_data["sslname"]] = sslcert
            yield sslcert._start_()

    @inlineCallbacks
    def get(self, sslname_requested):
        """
        Gets a cert for the request name.

        .. note::

           self._SSLCerts("library_webinterface", self.have_updated_ssl_cert)
        """
        logger.debug("looking for: {sslname_requested}", sslname_requested=sslname_requested)
        if sslname_requested in self.managed_certs:
            # print(f"ssl cert get: {self.managed_certs}")
            # print(f"ssl cert get: {self.managed_certs[sslname_requested]}")
            tester = self.managed_certs[sslname_requested]
            # logger.debug("found by cert! {sslname_requested}", sslname_requested=sslname_requested)
            return self.managed_certs[sslname_requested].get()
        else:
            # Check if available from file system, otherwise return self signed.
            meta_exists = yield self._Files.exists(f"{self._working_dir}/etc/certs/{sslname_requested}.meta")
            if meta_exists:  # No files to read. Meta data file is required!
                master_meta = yield self._Files.read(f"{self._working_dir}/etc/certs/{self.sslname}.meta",
                                                     unpickle="json")
                yield self.add_sslcert(master_meta, "file")
                if sslname_requested in self.managed_certs:
                    logger.info("Tried to load cert, but failed: {sslname}   Sending self-signed.",
                                sslname=sslname_requested)
                    return self.managed_certs[sslname_requested].get()
        if sslname_requested != "selfsigned":
            logger.info("Could not find cert for '{sslname}', sending self signed. Library or module should implement _sslcerts_ with a callback method.", sslname=sslname_requested)
        return self.get_self_signed()

    @inlineCallbacks
    def load_self_signed_cert(self, csr_text: Optional[str] = None, key_text: Optional[str] = None):
        """
        Loads the self signed cert and prepares it for use internally.

        :param csr_text: The text of the csr
        :param key_text:
        :return:
        """
        if csr_text is None:
            self.self_signed_cert = yield self._Files.read(self.self_signed_cert_path)
        else:
            self.self_signed_cert = csr_text
        if key_text is None:
            self.self_signed_key = yield self._Files.read(self.self_signed_key_path)
        else:
            self.self_signed_key = key_text

    def get_self_signed(self):
        if self.full_self_signed_cert is None:
            key_crypt = crypto.load_privatekey(crypto.FILETYPE_PEM, self.self_signed_key)
            if isinstance(key_crypt, tuple):
                key_crypt = key_crypt[0]
            cert_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self.self_signed_cert)
            if isinstance(cert_crypt, tuple):
                cert_crypt = cert_crypt[0]
            self.full_self_signed_cert = {
                "key": self.self_signed_key,
                "cert": self.self_signed_cert,
                "chain": None,
                "key_crypt": key_crypt,
                "cert_crypt": cert_crypt,
                "chain_crypt": None,
                "expires_at": self.self_signed_expires_at,
                "created_at": self.self_signed_created_at,
                "signed_at": self.self_signed_created_at,
                "self_signed": True,
                "cert_path": self.self_signed_cert_path,
                "key_path": self.self_signed_key_path,
                "chain_path": None,
            }
        return self.full_self_signed_cert

    def check_csr_input(self, csr_request):
        results = {}

        if "sslname" not in csr_request:
            raise YomboWarning("'sslname' is required.")
        results["sslname"] = csr_request["sslname"]

        # print(f"Local_gateway: {self.local_gateway}")
        # print(f"Local_gateway.dns_name: {self.local_gateway.dns_name}")
        if self.local_gateway.dns_name is None:
            raise YomboWarning("Unable to create SSL Certs, no system domain set.")

        if "cn" not in csr_request:
            raise YomboWarning(f"'cn' must be included, and must end with our local FQDN: {self.local_gateway.dns_name}")
        elif csr_request["cn"].endswith(self.local_gateway.dns_name) is False:
            results["cn"] = csr_request["cn"] + "." + self.local_gateway.dns_name
        else:
            results["cn"] = csr_request["cn"]

        if "sans" not in csr_request:
            results["sans"] = None
        else:
            san_list = []
            for san in csr_request["sans"]:
                try:
                    ip_address(str(san))
                    is_address = True
                except ValueError:
                    is_address = False
                if san.endswith(self.local_gateway.dns_name) is False and is_address is False:
                    san_list.append(str(san + "." + self.local_gateway.dns_name))
                else:
                    san_list.append(str(san))

            results["sans"] = san_list

        # if "key_type" in csr_request:  # allow changing default, might change in the future.
        #     if csr_request["key_type"] != "rsa":
        #         raise YomboWarning("key_type must be 'rsa', received: %s" % csr_request["key_type"])
        #     results["key_type"] = csr_request["key_type"]
        # else:
        #
        if "key_size" in csr_request:
            if csr_request["key_size"] < 2048:
                csr_request["key_size"] = 2048
            if csr_request["key_size"] > 4096:
                csr_request["key_size"] = 4096
        else:
            csr_request["key_size"] = self.default_key_size
        results["key_type"] = "rsa"
        results["key_size"] = csr_request["key_size"]

        if "csr_path" not in csr_request:
            csr_request["csr_path"] = None
        results["csr_path"] = csr_request["csr_path"]

        if "key_path" not in csr_request:
            csr_request["key_path"] = None
        results["key_path"] = csr_request["key_path"]

        if "callback" in csr_request:
            results["update_callback"] = csr_request["callback"]
        elif "update_callback" in csr_request:
            results["update_callback"] = csr_request["update_callback"]

        if "callback_type" in csr_request:
            results["update_callback_type"] = csr_request["callback_type"]
        elif "update_callback_type" in csr_request:
            results["update_callback_type"] = csr_request["update_callback_type"]

        if "callback_component" in csr_request:
            results["update_callback_component"] = csr_request["callback_component"]
        elif "update_callback_component" in csr_request:
            results["update_callback_component"] = csr_request["update_callback_component"]

        if "callback_function" in csr_request:
            results["update_callback_function"] = csr_request["callback_function"]
        elif "update_callback_function" in csr_request:
            results["update_callback_function"] = csr_request["update_callback_function"]
        return results

    @inlineCallbacks
    def generate_csr(self, args):
        """
        This function shouldn't be called directly. Instead, use the queue
        "self.generate_csr_queue.put(request, callback, callback_args)" or
        "self._SSLCerts.generate_csr_queue.put()".
        
        Requests certs to be made. Will return right away with a request ID. A callback can be set to return
        the cert once it's complete.

        :return:
        """
        logger.debug("Generate_CSR called with args: {args}", args=args)
        kwargs = self.check_csr_input(args)

        if kwargs["key_type"] == "rsa":
            kwargs["key_type"] = crypto.TYPE_RSA
        else:
            kwargs["key_type"] = crypto.TYPE_DSA

        req = crypto.X509Req()
        req.get_subject().CN = kwargs["cn"]
        req.get_subject().countryName = "US"
        req.get_subject().stateOrProvinceName = "California"
        # req.get_subject().localityName = "Sacramento"
        req.get_subject().localityName = "Staging"
        req.get_subject().organizationName = "Yombo"
        print(f"!!!!!!!!!!!!!!!1 generating ssl cert: Gateway {self._gateway_id}")
        req.get_subject().organizationalUnitName = "Gateway " + self._gateway_id

        # Appends SAN to have "DNS:"
        if kwargs["sans"] is not None:
            san_string = []
            for i in kwargs["sans"]:
                san_string.append(f"DNS: {i}")
            san_string = ", ".join(san_string)
            x509_extensions = [crypto.X509Extension(b"subjectAltName", False, unicode_to_bytes(san_string))]
            req.add_extensions(x509_extensions)

        start = time()
        key = yield threads.deferToThread(
            self._generate_key,
            **{"key_type": kwargs["key_type"], "key_size": kwargs["key_size"]}
        )
        duration = round(float(time()) - start, 4)
        self._Events.new(event_type="sslcerts",
                         event_subtype="generate_new",
                         attributes=(args["sslname"], kwargs["cn"], san_string, duration),
                         _request_context=self._FullName,
                         _authentication=self.AUTH_USER
                         )

        req.set_pubkey(key)

        req.sign(key, "sha256")

        csr_text = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        key_text = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

        return {
                "csr_text": csr_text,
                "csr_hash": self._Hash.sha256_compact(csr_text),
                "key_text": key_text
               }

    @inlineCallbacks
    def _create_self_signed_cert(self):
        """
        Creates a self signed cert. Shouldn't be called directly except by this library for its own use.
        """
        logger.info("Creating self signed ssl/tls cert.")
        req = crypto.X509()

        req.get_subject().CN = "localhost"
        req.get_subject().countryName = "US"
        req.get_subject().stateOrProvinceName = "California"
        req.get_subject().localityName = "Self Signed"
        req.get_subject().organizationName = "Yombo"
        req.get_subject().organizationalUnitName = f"Gateway {self._gateway_id} Self Signed"

        req.set_serial_number(uuid4().int)
        req.gmtime_adj_notBefore(0)
        req.gmtime_adj_notAfter(3600 * 24 * 180)  # Expire after 180 days.
        self.self_signed_created_at = time()
        self.self_signed_expires_at = time() + (3600 * 24 * 180)
        self._Configs.set("sslcerts.self_signed_created_at", self.self_signed_created_at)
        self._Configs.set("sslcerts.self_signed_expires_at", self.self_signed_expires_at)
        req.set_issuer(req.get_subject())
        key = yield threads.deferToThread(self._generate_key, **{"key_type": crypto.TYPE_RSA, "key_size": self.default_key_size})
        req.set_pubkey(key)
        req.sign(key, "sha256")

        cert_text = crypto.dump_certificate(crypto.FILETYPE_PEM, req)
        key_text = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

        yield self._Files.save(self.self_signed_cert_path, cert_text)
        yield self._Files.save(self.self_signed_key_path, key_text)
        yield self.load_self_signed_cert(cert_text, key_text)
        self.full_self_signed_cert = None

    def _generate_key(self, **kwargs):
        """
        This is a blocking function and should only be called by the sslcerts library. This is called
        in a seperate thread.

        Responsible for generating a key and csr.

        :return:
        """
        # logger.debug("About to generate key: {kwargs}", kwargs=kwargs)
        key = crypto.PKey()
        key.generate_key(kwargs["key_type"], kwargs["key_size"])
        return key

    def send_csr_request(self, csr_text, sslname):
        """
        Submit CSR request to Yombo. The sslname is also sent to be used for tracking. This will be returned
        directly back to us. This allows us to get out signed cert back if we happen to restart
        between sending the CSR and getting the signed key back.
        
        :param csr_text: CSR request text
        :param sslname: Name of the ssl for tracking.
        :return:
        """
        logger.info("Sending CSR request for cert: {sslname}", sslname=sslname)
        if len(sslname) > 100:
            raise YomboWarning("'sslname' too long, limit is 100 characters.")

        body = {
            "csr_text": csr_text,
            "sslname": sslname,
        }

        request_msg = self._AMQPYombo.generate_message_request(
            exchange_name="ysrv.e.gw_sslcerts",
            source="yombo.gateway.lib.amqpyobo",
            destination="yombo.server.sslcerts",
            request_type="csr_request",
            body=body,
        )
        self._AMQPYombo.publish(**request_msg)
        return request_msg

    def amqp_incoming(self, **kwargs):
        """
        Signed SSL certs comes as requests, even though it's really a response. This avoids the requirement
        that all "responses" have a sent correlation ID.

        :param kwargs:
        :return:
        """
        request_type = kwargs["message_headers"]["request_type"]
        if request_type == "csr_response":
            self.amqp_incoming_response_to_csr_request(**kwargs)
        else:
            logger.warn("AMQP:Handler:Control - Received unknown request_type: {request_type}",
                        request_type=request_type)

    def amqp_incoming_response_to_csr_request(self, message=None, properties=None, correlation_info=None, **kwargs):
        """
        Called when we get a signed cert back from a CSR.
        
        :param message:
        :param message_headers:
        :param properties: 
        :param correlation_info: 
        :param kwargs: 
        :return: 
        """
        logger.info("Received CSR response message: {message}", message=message)
        if "sslname" not in message:
            logger.warn("Discarding response, doesn't have an sslname attached.") # can't raise exception due to AMPQ processing.
            return
        logger.info("Received a new signed SSL/TLS certificate for: {sslname}", sslname=message["sslname"])
        sslname = bytes_to_unicode(message["sslname"])
        if sslname not in self.managed_certs:
            logger.warn("It doesn't appear we have a managed cert for the given SSL name. Lets store it for a "
                        "few minutes: {sslname}",
                        sslname=sslname)
            if sslname in self.received_message_for_unknown:
                self.received_message_for_unknown[sslname].append(message)
            else:
                self.received_message_for_unknown[sslname] = [message]
        else:
            self.managed_certs[sslname].amqp_incoming_response_to_csr_request(message=message, properties=properties,
                                                                              correlation_info=correlation_info, **kwargs)

    def validate_csr_private_certs_match(self, csr_text, key_text):
        csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_text)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_text)
        return csr.verify(key)
