# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Devices @ Module Development <https://yombo.net/docs/sslcerts/>`_

This library is responsible for managing SSL/TLS certs. It utilizes openssl to
generate keys and signing requests. It then forwards any signing requests (CSRs)
to Yombo for signing.

This library utilizes hooks to request what certs needs to be managed. A library or module
needs to return several things:

* sslname (required) - String - The name of a file to expect to load a key from.
* key_size (optional) - Int - Accepts a size of 2048 and 4096, default is 4096.
* key_type (optional) - String - Either "rsa" or "dsa", default is rsa.
* sans (optional) - List - A list of SAN (Subject Alternative Names)
* type (optional) - String - Either 'client' or 'server'. (not implemented)

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function

try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
from OpenSSL import crypto

import os
import os.path
from hashlib import sha256
import glob

from time import time
from socket import gethostname

# Import 3rd-party libs
#import yombo.ext.six as six

# Import twisted libraries
from twisted.internet import threads
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.ext.expiringdict import ExpiringDict
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import save_file, read_file, global_invoke_all
from yombo.utils.dictobject import DictObject

logger = get_logger('library.sslcerts')


class SSLCerts(YomboLibrary):
    """
    Responsible for managing various certificates for Yombo.
    """

    managed_certs = {}

    @inlineCallbacks
    def _init_(self):
        """
        On startup, various libraries will need certs (webinterface, MQTT) will need at least a basic cert.
        This module loads previously created certs. Then, after things settle, it will request new certs
        as needed.

        If a cert isn't avail for the requested sslname, it will receive a sign-signed certificate.

        :return:
        """
        self.hostname = gethostname()

        self.gwid = self._Configs.get("core", "gwid")
        self.fqdn = self._Configs.get('dns', 'fqdn', None, False)

        self.recieved_message_for_unknown = ExpiringDict(100, 600)
        self.self_signed_cert_file = self._Atoms.get('yombo.path') + "/usr/etc/certs/sslcert_selfsigned.cert.pem"
        self.self_signed_key_file = self._Atoms.get('yombo.path') + "/usr/etc/certs/sslcert_selfsigned.key.pem"
        self.self_signed_expires = self._Configs.get("sslcerts", "self_signed_expires", None, False)
        self.self_signed_created = self._Configs.get("sslcerts", "self_signed_created", None, False)

        if os.path.exists(self.self_signed_cert_file) is False or \
                self.self_signed_expires is None or \
                self.self_signed_expires < int(time()) or \
                self.self_signed_created is None or \
                not os.path.exists(self.self_signed_key_file) or \
                not os.path.exists(self.self_signed_cert_file):
            logger.info("Generating a self signed cert for SSL. This can take a few moments.")
            yield self._create_self_signed_cert()

        self.self_signed_cert = read_file(self.self_signed_cert_file)
        self.self_signed_key = read_file(self.self_signed_key_file)

        self.managed_certs = yield self._SQLDict.get(self, "managed_certs", serializer=self.sslcert_serializer,
                                                     unserializer=self.sslcert_unserializer)
        # print("startup: managed_certs: %s" % self.managed_certs)

        self.check_if_certs_need_update_loop = None

    def _load_(self):
        """
        Starts the loop to save data to SQL every so often.
        :return:
        """
        self.check_if_certs_need_update_loop = LoopingCall(self.check_if_certs_need_update)
        self.check_if_certs_need_update_loop.start(self._Configs.get('sqldict', 'save_interval', 60*60*24, False))

    def _stop_(self):
        """
        Simply stop any loops, tell all the certs to save themselves to disk as a backup.
        :return:
        """
        if self.check_if_certs_need_update_loop is not None and self.check_if_certs_need_update_loop.running:
            self.check_if_certs_need_update_loop.stop()

        for sslname, cert in self.managed_certs.iteritems():
            cert.stop()

    def check_if_certs_need_update(self):
        """
        Called periodically to see if any certs need to be updated. Once a day is enough, we have 30 days to get this
        done.
        """
        for sslname, cert in self.managed_certs.iteritems():
            cert.check_if_rotate_needed()

    def _configuration_set_(self, **kwargs):
        """
        Receive configuruation updates and adjust as needed.

        :param kwargs: section, option(key), value
        :return:
        """
        section = kwargs['section']
        option = kwargs['option']
        value = kwargs['value']

        if section == 'dns':
            if option == 'fqdn':
                self.fqdn = value
                for sslname, cert in self.managed_certs.iteritems():
                    cert.check_updated_fqdn()
                    # Now all our signed certs are invalid. Time to update them.

    def _modules_inited_(self):
        """
        Called before the modules have their preload called, after their _init_.

        In turn, calls the hook "sslcerts" to gather requirements to manage certs.

        :return:
        """
        # get all certs required.
        # gerneate and request new certs
        # delte old certs
        # delete certs from database where there is a newer cert, but keep last 2 certs, keep non-expired

        sslcerts = global_invoke_all('_sslcerts_', called_by=self)
        for component_name, item in sslcerts.iteritems():
            # print("mod started, from: %s item: %s" % (component_name, item))
            try:
                item = self.check_csr_input(item)  # Clean up module developers input.
            except YomboWarning, e:
                logger.warn("Cannot add cert from hook: %s" % e)
                continue
            if item['sslname'] in self.managed_certs:
                self.managed_certs[item['sslname']].update_attributes(item)
            else:
                self.managed_certs[item['sslname']] = SSLCert('sslcerts', DictObject(item), self)

    def sslcert_serializer(self, item):
        """
        Used to hydrate the list of certs. Somethings shouldn't be stored in the SQLDict.
        :param item:
        :return:
        """
        return item._dump()

    def sslcert_unserializer(self, item):
        """
        Used by SQLDict to hydrate an item stored.

        :param item:
        :return:
        """
        return SSLCert('sqldict', DictObject(item), self)

    def get(self, sslname_requested):
        """
        Gets a cert for the request name. A callback can be specified if a self-signed
        cert needed to be returned and later a real cert is available.

        .. note::

           self._SSLCerts('library_webinterface', self.have_updated_ssl_cert)
        """
        logger.debug("looking for: {sslname_requested}", sslname_requested=sslname_requested)
        if sslname_requested in self.managed_certs:
            logger.debug("found by cert! {cert_requested}", sslname_requested=sslname_requested)
            return self.managed_certs[sslname_requested].get()
        else:
            logger.info("Could not find cert for '{sslname}', sending self signed. Library or module should implement _sslcerts_ with a callback method.", sslname=sslname_requested)
            return {
                'key': self.self_signed_key,
                'cert': self.self_signed_cert,
                'chain': None,
                'expires': self.self_signed_expires,
                'created': self.self_signed_created,
                'signed': self.self_signed_created,
                'self_signed': True,
            }

    def check_csr_input(self, csr_request):
        results = {}

        if 'sslname' not in csr_request:
            raise YomboWarning("'sslname' is required.")
        results['sslname'] = csr_request['sslname']

        if self.fqdn is None:
            raise YomboWarning("Unable to create SSL Certs, no system domain set.")

        if 'cn' not in csr_request:
            raise YomboWarning("'cn' must be included, and must end with our local FQDN: %s" % self.fqdn)
        elif csr_request['cn'].endswith(self.fqdn) is False:
            raise YomboWarning("'cn' must end with our FQDN: %s" % self.fqdn)
        else:
            results['cn'] = csr_request['cn']

        if 'sans' not in csr_request:
            results['sans'] = None
        else:
            results['sans'] = csr_request['sans']

        # if 'key_type' in csr_request:  # allow changing default, might change in the future.
        #     if csr_request['key_type'] != 'rsa':
        #         raise YomboWarning("key_type must be 'rsa', received: %s" % csr_request['key_type'])
        #     results['key_type'] = csr_request['key_type']
        # else:
        #
        results['key_type'] = 'rsa'
        results['key_size'] = 4096

        if 'csr_file' not in csr_request:
            csr_request['csr_file'] = None
        results['csr_file'] = csr_request['csr_file']

        if 'key_file' not in csr_request:
            csr_request['key_file'] = None
        results['key_file'] = csr_request['key_file']

        if 'callback' in csr_request:
            results['update_callback'] = csr_request['callback']
        elif 'update_callback' in csr_request:
            results['update_callback'] = csr_request['update_callback']

        if 'callback_type' in csr_request:
            results['update_callback_type'] = csr_request['callback_type']
        elif 'update_callback_type' in csr_request:
            results['update_callback_type'] = csr_request['update_callback_type']

        if 'callback_component' in csr_request:
            results['update_callback_component'] = csr_request['callback_component']
        elif 'update_callback_component' in csr_request:
            results['update_callback_component'] = csr_request['update_callback_component']

        if 'callback_function' in csr_request:
            results['update_callback_function'] = csr_request['callback_function']
        elif 'update_callback_function' in csr_request:
            results['update_callback_function'] = csr_request['update_callback_function']
        return results

    @inlineCallbacks
    def generate_csr(self, **kwargs):
        """
        Requests certs to be made. Will return right away with a request ID. A callback can be set to return
        the cert once it's complete.

        :return:
        """
        kwargs = self.check_csr_input(kwargs)

        if kwargs['key_type'] == 'rsa':
            kwargs['key_type'] = crypto.TYPE_RSA
        else:
            kwargs['key_type'] = crypto.TYPE_DSA

        gwid = "gw_%s" % self.gwid[0:10]
        req = crypto.X509Req()
        req.get_subject().CN = kwargs['cn']
        req.get_subject().countryName = 'US'
        req.get_subject().stateOrProvinceName = 'California'
        req.get_subject().localityName = 'Sacramento'
        req.get_subject().organizationName = 'Yombo'
        req.get_subject().organizationalUnitName = gwid

        # Appends SAN to have 'DNS:'
        if kwargs['sans'] is not None:
            sans_list = None
            for san in kwargs['sans']:
                sans_list = [str(s + "." + self.fqdn) for s in kwargs['sans']]  # dbl checked at server

            san_string = []
            for i in sans_list:
                san_string.append("DNS: %s" % i)
            san_string = ", ".join(san_string)

            x509_extensions = [crypto.X509Extension("subjectAltName", False, san_string)]
            req.add_extensions(x509_extensions)

        key = yield threads.deferToThread(
            self._generate_key,
            **{'key_type': kwargs['key_type'], 'key_size': kwargs['key_size']}
        )
        req.set_pubkey(key)

        req.sign(key, "sha256")

        csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        key_file = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

        if kwargs['csr_file'] is not None:
            save_file(kwargs['csr_file'], csr)
        if kwargs['key_file'] is not None:
            save_file(kwargs['key_file'], key_file)

        returnValue({'csr': csr, 'key': key_file})

    @inlineCallbacks
    def _create_self_signed_cert(self):
        """
        If datacard.crt and datacard.key don't exist in cert_dir, create a new
        self-signed cert and keypair and write them into that directory.
        """
        req = crypto.X509()
        gwid = "%s %s" % (self.gwid, self.hostname)
        req.get_subject().CN = 'localhost'
        req.get_subject().countryName = 'US'
        req.get_subject().stateOrProvinceName = 'California'
        req.get_subject().localityName = 'Sacramento'
        req.get_subject().organizationName = 'Yombo'
        req.get_subject().organizationalUnitName = gwid[0:63]

        req.set_serial_number(int(time()))
        req.gmtime_adj_notBefore(0)
        req.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
        self.self_signed_expires = time() + (10 * 365 * 24 * 60 * 60)
        self.self_signed_created = time()
        self._Configs.set("sslcerts", "self_signed_expires", self.self_signed_expires)
        self._Configs.set("sslcerts", "self_signed_created", self.self_signed_created)
        req.set_issuer(req.get_subject())
        key = yield threads.deferToThread(self._generate_key, **{'key_type': crypto.TYPE_RSA, 'key_size': 4096})
        req.set_pubkey(key)
        req.sign(key, 'sha256')

        csr_key = crypto.dump_certificate(crypto.FILETYPE_PEM, req)
        key_file = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

        save_file(self.self_signed_cert_file, csr_key)
        save_file(self.self_signed_key_file, key_file)
        returnValue({'csr_key': csr_key, 'key': key_file})

    def _generate_key(self, **kwargs):
        """
        Responsible for generating a key and csr.

        :return:
        """
        key = crypto.PKey()
        key.generate_key(kwargs['key_type'], kwargs['key_size'])
        return key

    def send_csr_request(self, csr_text, sslname):
        """
        Submit CSR request to Yombo. The sslname we send will be returned to use exactly. A simple tracker.
        :param csr_text: CSR request text
        :param sslname: Name of the ssl for tracking.
        :return:
        """
        logger.debug("send_csr_request, preparing to send CSR.")
        if len(sslname) > 100:
            raise YomboWarning("'sslname' too long, limit is 100 characters.")

        body = {
            'csr_text': csr_text,
            'sslname': sslname,
        }

        headers = {
            "request_type": "sslcert",
            "ssl_item": "csr_request",
        }
        request = self.generate_sslrequest_request(headers, body, self.yombo_csr_response)

        self._AMQPYombo.publish(**request)
        return request

    def yombo_csr_response(self, properties, msg, correlation):
        # print("########################yombo_csr_response %s" % msg)

        if 'sslname' not in msg:
            logger.warn("Discarding response, doesn't have an sslname attached.") # can't raise exception due to AMPQ processing.
            return
        sslname = msg['sslname'].encode('ascii','ignore')
        # print("sslname: %s" % sslname)
        # print("sslname: %s" % type(sslname))
        # print("managed_certs: %s" % self.managed_certs)
        # print("managed_certs: %s" % type(self.managed_certs))
        if sslname not in self.managed_certs:
            logger.warn("It doesn't appear we have a managed cert for the given SSL name. Lets store it for a few minutes.")
            if sslname in self.recieved_message_for_unknown:
                self.recieved_message_for_unknown[sslname].append(msg)
            else:
                self.recieved_message_for_unknown[sslname] = [msg]

        self.managed_certs[sslname].yombo_csr_response(properties, msg, correlation)

    def amqp_incoming(self, properties, msg, correlation):
        """
        Currently unused... Will be in the future.

        :param properties:
        :param msg:
        :param correlation:
        :return:
        """
        pass

    def validate_csr_private_certs_match(self, csr_text, key_text):
        csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_text)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_text)
        return csr.verify(key)

    def generate_sslrequest_request(self, headers, request_data=None, callback=None):
        """
        Generate a request specific to this library - configs!

        :param headers:
        :param request_data:
        :return:
        """
        if request_data is None:
            request_data = {}

        request_msg = self._AMQPYombo.generate_message_request('ysrv.e.gw_sslcerts', 'yombo.gateway.lib.sslcerts',
                                                    "yombo.server.sslcerts", headers, request_data, callback)
        request_msg['routing_key'] = '*'
        logger.debug("response: {request_msg}", request_msg=request_msg)
        return request_msg

    def __contains__(self, cert_requested):
        """
        Looks for an sslkey with the given sslname.

            >>> if 'webinterface' in self._SSLCerts['library_webinterface']:  #by uuid

        :param cert_requested: The ssl cert sslname to search for.
        :type cert_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        if cert_requested in self.managed_certs:
            return True
        else:
            return False

    def __str__(self):
        return "Manages SSL Cert for yombo gateway"


class SSLCert(object):
    """
    A class representing a single cert.
    """
    def __init__(self, source, sslcert, _ParentLibrary):
        """
        :param source: *(source)* - One of: 'sql', 'sslcerts', or 'sqldict'
        :param sslcert: *(dictionary)* - A dictionary of the attributes to setup the class.
        :ivar sslname: *(string)* - The name of base file. The archive name will be based off this.
        :ivar key_size: *(int)* - Size of the key in bits.
        :ivar key_type: *(string)* - Either rsa or dsa.
        """
        self._FullName = 'yombo.gateway.lib.SSLCerts.SSLCert'
        self._Name = 'SSLCerts.SSLCert'
        self._ParentLibrary = _ParentLibrary

        # print("sslcert: %s" % sslcert)

        self.sslname = sslcert.sslname
        self.cn = sslcert.cn
        self.sans = sslcert.sans
        self.cert_fqdn = self._ParentLibrary.fqdn

        self.update_callback = sslcert.get('update_callback', None)
        self.update_callback_type = sslcert.get('update_callback_type', None)
        self.update_callback_component = sslcert.get('update_callback_component', None)
        self.update_callback_function = sslcert.get('update_callback_function', None)

        self.key_size = int(sslcert.get('key_size', None))
        self.key_type = sslcert.get('key_type', None)

        self.cert_previous = sslcert.get('cert_previous', None)
        self.chain_previous = sslcert.get('chain_previous', None)
        self.key_previous = sslcert.get('key_previous', None)
        self.previous_expires = sslcert.get('previous_expires', None)
        self.previous_created = sslcert.get('previous_created', None)
        self.previous_signed = sslcert.get('previous_signed', None)
        self.previous_submitted = sslcert.get('previous_submitted', None)
        self.previous_is_valid = None

        self.cert_current = sslcert.get('cert_current', None)
        self.chain_current = sslcert.get('chain_current', None)
        self.key_current = sslcert.get('key_current', None)
        self.current_created = sslcert.get('current_created', None)
        self.current_expires = sslcert.get('current_expires', None)
        self.current_signed = sslcert.get('current_signed', None)
        self.current_submitted = sslcert.get('current_submitted', None)
        self.current_is_valid = None

        self.csr_next = sslcert.get('csr_next', None)
        self.cert_next = sslcert.get('cert_next', None)
        self.chain_next = sslcert.get('chain_next', None)
        self.key_next = sslcert.get('key_next', None)
        self.next_created = sslcert.get('next_created', None)
        self.next_expires = sslcert.get('next_expires', None)
        self.next_signed = sslcert.get('next_signed', None)
        self.next_submitted = sslcert.get('next_submitted', None)
        self.next_is_valid = None
        self.next_csr_generation_error_count = 0
        self.next_csr_generation_in_progress = False
        self.next_csr_submit_after_generation = False

        self.sync_to_file_calllater = None

        self.check_messages_of_the_unknown()

        if source != 'sqldict':  # we only trust SQLDict or the filesystem for data.
            self.sync_from_filesystem()

        self.check_is_valid()
        # print("status: %s" % self.__dict__)

        # check if we need to generate csr, sign csr, or rotate next with current.
        self.check_if_rotate_needed()


    def stop(self):
        self._sync_to_file()

    def check_if_rotate_needed(self):
        """
        Our methodology is to always make sure a next key is avail. If we are due for signing, lets
        get it signed and rotate into use.

        These checks for the next cert include checks for the current cert, including invalid,
        non-existent, or expired.
        :return:
        """
        # Look for any tasks to do.
        self.check_updated_fqdn()

        # 1) See if we need to generate a new cert.
        if self.csr_next is None or self.next_is_valid is None:
            if self.current_is_valid is not True or \
                    self.key_current is None or \
                    self.current_expires is None or \
                    self.current_expires < int(time() + (30 * 24 * 60 * 60)):  # our current cert if bad...lets get a new one ASAP.
                # print("aaaaa")
                # print("self.current_is_valid: (should be not True): %s" % self.current_is_valid)
                # print("self.key_current: (should be None): %s" % self.key_current)
                # print("self.current_expires: (should be not NOne): %s" % self.current_expires)
                # print("int(time() + (30 * 24 * 60 * 60)): (should be less then above number): %s" % int(time() + (30 * 24 * 60 * 60)))
                self.generate_new_csr(submit=True)
            else: # just generate the CSR, no need to sign just yet.  Too soon.
                # print("bbbbb")
                self.generate_new_csr(submit=False)
        # 2) If next is valid, then lets rotate into current, doesn't matter if current is good, expired, etc. Just use the next cert.
        elif self.next_is_valid is True:
            self.make_next_be_current()
            # we not have ran for a long time, lets check if we need to submit CSR right away:
            if self.current_is_valid is not True or \
                    self.key_current is None or \
                    self.current_expires is None or \
                    self.current_expires < int(time() + (30 * 24 * 60 * 60)):  # our current cert if bad...lets get a new one ASAP.
                # print("cccc")
                self.generate_new_csr(submit=True)
            else:
                # print("ddddd")
                self.generate_new_csr(submit=False)
        # 3) Next cert might be half generated, half signed, maybe waited to be signed, etc. Lets inspect.
        elif self.next_is_valid is False:
            if self.current_is_valid is not True or \
                    self.key_current is None or \
                    self.current_expires is None or \
                    self.current_expires < int(time() + (30 * 24 * 60 * 60)):  # our current cert if bad...lets get a new one ASAP.
                # print("eeeee")
                # print("self.current_is_valid: (should be not True): %s" % self.current_is_valid)
                # print("self.key_current: (should be None): %s" % self.key_current)
                # print("self.current_expires: (should be not NOne): %s" % self.current_expires)
                # print("int(time() + (30 * 24 * 60 * 60)): (should be less then above number): %s" % int(time() + (30 * 24 * 60 * 60)))
                self.submit_csr()
        else:
            raise YomboWarning("next_is_valid is in an unknowns state.")

    def make_next_be_current(self):
        self.migrate_keys("current", "previous")
        self.migrate_keys("next", "current")
        self.update_requester()

    def update_requester(self):
        """
        Used to notify the library or module that requested this certificate that we have an updated
        cert for usage. However, most time, the system will need to be recycled to take affect - we
        leave that up the library or module to ask/notify to recycle the system.

        :return:
        """
        logger.debug("Update any requesters about new certs...")

        method = None
        if self.current_is_valid is not True:
            logger.warn("Asked to update the requester or new cert, but current cert isn't valid!")
            return

        if self.update_callback is not None and callable(self.update_callback):
            method = self.update_callback
        elif self.update_callback_type is not None and \
               self.update_callback_component is not None and \
               self.update_callback_function is not None:
            try:
                method = self._ParentLibrary._Loader.find_function(self.update_callback_type,
                           self.update_callback_component,
                           self.update_callback_function)
            except YomboWarning, e:
                logger.warn("Invalid update_callback information provided: %s" % e)

        if method is not None:
            method(self.get())  # tell the requester that they have a new cert. YAY

    def migrate_keys(self, from_label, to_label):
        if from_label == 'next':
            self.csr_next = None

        setattr(self, "cert_%s" % to_label, getattr(self, "cert_%s" % from_label))
        setattr(self, "chain_%s" % to_label, getattr(self, "chain_%s" % from_label))
        setattr(self, "key_%s" % to_label, getattr(self, "key_%s" % from_label))
        setattr(self, "%s_created" % to_label, getattr(self, "%s_created" % from_label))
        setattr(self, "%s_expires" % to_label, getattr(self, "%s_expires" % from_label))
        setattr(self, "%s_signed" % to_label, getattr(self, "%s_signed" % from_label))
        setattr(self, "%s_submitted" % to_label, getattr(self, "%s_submitted" % from_label))
        setattr(self, "%s_is_valid" % to_label, getattr(self, "%s_is_valid" % from_label))

        setattr(self, "cert_%s" % from_label, None)
        setattr(self, "chain_%s" % from_label, None)
        setattr(self, "key_%s" % from_label, None)
        setattr(self, "%s_created" % from_label, None)
        setattr(self, "%s_expires" % from_label, None)
        setattr(self, "%s_signed" % from_label, None)
        setattr(self, "%s_submitted" % from_label, None)
        setattr(self, "%s_is_valid" % from_label, None)
        self.sync_to_file()

    def clean_section(self, label):
        """
        Used wipe out either 'previous', 'next', or 'current'. This allows to make room or something new.
        :param label:
        :return:
        """
        if label == 'next':
            self.csr_next = None
            self.next_csr_generation_error_count

        setattr(self, "cert_%s" % label, None)
        setattr(self, "chain_%s" % label, None)
        setattr(self, "key_%s" % label, None)
        setattr(self, "%s_created" % label, None)
        setattr(self, "%s_expires" % label, None)
        setattr(self, "%s_signed" % label, None)
        setattr(self, "%s_submitted" % label, None)
        setattr(self, "%s_is_valid" % label, None)
        self.sync_to_file() # this will remove the data file, and make a nearly empty meta file.

    def check_messages_of_the_unknown(self):
        if self.sslname in self._ParentLibrary.recieved_message_for_unknown:
            logger.warn("We have messages for us.  TODO: Implement this.")

    def sync_from_filesystem(self):
        """
        Reads meta data and items from the file system. This allows us to restore data incase the database
        goes south. This is important since only the gateway has the private key and cannot be recovered.

        :return:
        """
        logger.debug("Inspecting file system for certs.")

        for label in ['previous', 'current', 'next']:
            setattr(self, "%s_is_valid" % label, None)

            if os.path.exists('usr/etc/certs/%s.%s.meta' % (self.sslname, label)):
                logger.debug("SSL Meta found for: {label}", label=label)
                meta = json.loads(read_file('usr/etc/certs/%s.%s.meta' % (self.sslname, label)))
                # print("meta: %s" % meta)

                csr_read = False
                if label == 'next':
                    logger.debug("Looking for 'next' information.")
                    if os.path.exists('usr/etc/certs/%s.%s.csr.pem' % (self.sslname, label)):
                        if getattr(self, "csr_%s" % label) is None:
                            csr = read_file('usr/etc/certs/%s.%s.csr.pem' % (self.sslname, label))
                            if sha256(csr).hexdigest() == meta['csr']:
                                csr_read = True
                            else:
                                logger.warn("Appears that the file system has bad meta signatures (csr). Purging.")
                                for file_to_delete in glob.glob("usr/etc/certs/%s.%s.*" % (self.sslname, label)):
                                    logger.warn("Removing bad file: %s" % file_to_delete)
                                    os.remove(file_to_delete)
                                continue

                cert_read = False
                if getattr(self, "cert_%s" % label) is None:
                    if os.path.exists('usr/etc/certs/%s.%s.cert.pem' % (self.sslname, label)):
                        # print("setting cert!!!")
                        cert = read_file('usr/etc/certs/%s.%s.cert.pem' % (self.sslname, label))
                        cert_read = True
                        if sha256(cert).hexdigest() != meta['cert']:
                            logger.warn("Appears that the file system has bad meta signatures (cert). Purging.")
                            for file_to_delete in glob.glob("usr/etc/certs/%s.%s.*" % (self.sslname, label)):
                                logger.warn("Removing bad file: %s" % file_to_delete)
                                os.remove(file_to_delete)
                            continue

                chain_read = False
                if getattr(self, "chain_%s" % label) is None:
                    if os.path.exists('usr/etc/certs/%s.%s.chain.pem' % (self.sslname, label)):
                        # print("setting chain!!!")
                        chain = read_file('usr/etc/certs/%s.%s.chain.pem' % (self.sslname, label))
                        chain_read = True
                        if sha256(chain).hexdigest() != meta['chain']:
                            logger.warn("Appears that the file system has bad meta signatures (chain). Purging.")
                            for file_to_delete in glob.glob("usr/etc/certs/%s.%s.*" % (self.sslname, label)):
                                logger.warn("Removing bad file: %s" % file_to_delete)
                                os.remove(file_to_delete)
                            continue

                key_read = False
                if getattr(self, "key_%s" % label) is None:
                    if os.path.exists('usr/etc/certs/%s.%s.key.pem' % (self.sslname, label)):
                        key = read_file('usr/etc/certs/%s.%s.key.pem' % (self.sslname, label))
                        key_read = True
                        if sha256(key).hexdigest() != meta['key']:
                            logger.warn("Appears that the file system has bad meta signatures (key). Purging.")
                            for file_to_delete in glob.glob("usr/etc/certs/%s.%s.*" % (self.sslname, label)):
                                logger.warn("Removing bad file: %s" % file_to_delete)
                                os.remove(file_to_delete)
                            continue

                logger.debug("Reading meta file for cert: {label}", label=label)

                if csr_read:
                    setattr(self, "csr_%s" % label, csr)
                if cert_read:
                    setattr(self, "cert_%s" % label, cert)
                if chain_read:
                    setattr(self, "chain_%s" % label, chain)
                if key_read:
                    setattr(self, "key_%s" % label, key)
                setattr(self, "%s_expires" % label, meta['expires'])
                setattr(self, "%s_created" % label, meta['created'])
                setattr(self, "%s_signed" % label, meta['signed'])
                setattr(self, "%s_submitted" % label, meta['submitted'])
                setattr(self, "%s_needs" % label, None)

                self.check_is_valid(label)
            else:
                setattr(self, "%s_is_valid" % label, None)

    def check_is_valid(self, label=None):
        if label is None:
            labels = ['previous', 'current', 'next']
        else:
            labels = [label]

        for label in labels:
            if getattr(self, "%s_expires" % label) is not None and \
                    int(getattr(self, "%s_expires" % label)) > int(time()) and \
                    getattr(self, "%s_signed" % label) is not None and \
                    getattr(self, "key_%s" % label) is not None and \
                    getattr(self, "cert_%s" % label) is not None and \
                    getattr(self, "chain_%s" % label) is not None:
                setattr(self, "%s_is_valid" % label, True)
            else:
                # print("Setting %s_is_valid to false" % label)
                # print("expires: %s" % getattr(self, "%s_expires" % label))
                # print("time   : %s" % int(time()))
                # print("signed: %s" % getattr(self, "%s_signed" % label))
                # print("key_: %s" % getattr(self, "key_%s" % label))
                # print("cert_: %s" % getattr(self, "cert_%s" % label))
                # print("chain_: %s" % getattr(self, "chain_%s" % label))
                setattr(self, "%s_is_valid" % label, False)


    def sync_to_file(self):
        if self.sync_to_file_calllater is None:
            logger.debug("Will backup certs in a bit.")
            self.sync_to_file_calllater = reactor.callLater(180, self._sync_to_file)
        elif self.sync_to_file_calllater.active() is False:
            self.sync_to_file_calllater = reactor.callLater(180, self._sync_to_file)
        elif self.sync_to_file_calllater.active() is True:
            self.sync_to_file_calllater.reset(180)
        else:
            logger.warn("sync to file in an unknown state. Will just save now. {state}", state=self.sync_to_file_calllater)
            self.sync_to_file_calllater = None
            self._sync_to_file()

    def _sync_to_file(self):
        """
        Sync current data to the file system. This allows for quick recovery if the database goes bad.
        :return:
        """
        logger.info("Backing up SSL Certs to file system.")

        for label in ['previous', 'current', 'next']:

            meta = {
                'expires': getattr(self, "%s_expires" % label),
                'created': getattr(self, "%s_created" % label),
                'signed': getattr(self, "%s_signed" % label),
                'submitted': getattr(self, "%s_submitted" % label),
            }

            if getattr(self, "cert_%s" % label) is None:
                meta['cert'] = None
                file = 'usr/etc/certs/%s.%s.cert.pem' % (self.sslname, label)
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta['cert'] = sha256(getattr(self, "cert_%s" % label)).hexdigest()
                save_file('usr/etc/certs/%s.%s.cert.pem' % (self.sslname, label),  getattr(self, "cert_%s" % label))

            if getattr(self, "chain_%s" % label) is None:
                meta['chain'] = None
                file = 'usr/etc/certs/%s.%s.chain.pem' % (self.sslname, label)
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta['chain'] = sha256(getattr(self, "chain_%s" % label)).hexdigest()
                save_file('usr/etc/certs/%s.%s.chain.pem' % (self.sslname, label), getattr(self, "chain_%s" % label))

            if getattr(self, "key_%s" % label) is None:
                meta['key'] = None
                file = 'usr/etc/certs/%s.%s.key.pem' % (self.sslname, label)
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta['key'] = sha256(getattr(self, "key_%s" % label)).hexdigest()
                save_file('usr/etc/certs/%s.%s.key.pem' % (self.sslname, label), getattr(self, "key_%s" % label))

            if label == 'next':
                if getattr(self, "csr_%s" % label) is None:
                    meta['csr'] = None
                    file = 'usr/etc/certs/%s.%s.csr.pem' % (self.sslname, label)
                    if os.path.exists(file):
                        os.remove(file)
                else:
                    meta['csr'] = sha256(getattr(self, "csr_%s" % label)).hexdigest()
                    save_file('usr/etc/certs/%s.%s.csr.pem' % (self.sslname, label), getattr(self, "csr_%s" % label))

            save_file('usr/etc/certs/%s.%s.meta' % (self.sslname, label), json.dumps(meta, separators=(',',':')))

    def check_updated_fqdn(self):
        if self._ParentLibrary.fqdn != self.cert_fqdn:
            logger.warn("FQDN changed for cert, will get new one: {sslname}", sslname=self.sslname)
            self.next_is_valid = None
            self.current_is_valid = None
            self.generate_new_csr(submit=True)

    def generate_new_csr(self, submit=False):
        """
        Requests a new csr to be generated. This uses the base class to do the heavy lifting.

        We usually don't submit the CSR at the time generation. This allows the CSR to be genearted ahead
        of when we actually need.

        :param submit: If true, will also submit the csr.
        :return:
        """
        self.clean_section('next')

        logger.debug("generate_new_csr: {sslname}.  Submit: {submit}", sslname=self.sslname, submit=submit)
        def generate_new_csr_error(failure, self):
            """
            Report any errors during the certificate generation.
            :param failure:
            :param self:
            :return:
            """
            self.next_csr_generation_error_count += 1
            if self.next_csr_generation_error_count < 5:
                logger.warn("Error generating new CSR for '{sslname}'. Will retry in 15 seconds. Exception : {failure}", sslname=self.sslname, failure=failure)
                reactor.callLater(15, self.generate_new_csr)
            else:
                logger.error("Error generating new CSR for '{sslname}'. Too many retries, perhaps something wrong with our request. Exception : {failure}", sslname=self.sslname, failure=failure)
                self.next_csr_generation_in_progress = False
            return 500

        def generate_new_csr_done(results, self):
            """
            Our CSR has been generated. Lets save it, and maybe subit it.

            :param results: The CSR and KEY.
            :param self: Pointer to the SSLCert class.
            :param submit: True if we should submit it to yombo for signing.
            :return:
            """
            logger.debug("generate_new_csr_done: {sslname}", sslname=self.sslname)
            self.key_next = results['key']
            self.csr_next = results['csr']
            save_file('usr/etc/certs/%s.next.csr.pem' % self.sslname, self.csr_next)
            save_file('usr/etc/certs/%s.next.key.pem' % self.sslname, self.key_next)
            self.next_created = int(time())
            self.sync_to_file()
            self.next_csr_generation_in_progress = False
            if self.next_csr_submit_after_generation is True:
                self.submit_csr()

        # End local functions.
        request = {
            'sslname': self.sslname,
            'key_size': self.key_size,
            'key_type': self.key_type,
            'cn': self.cn,
            'sans': self.sans
        }
        # end local function defs

        if self.next_csr_generation_in_progress is True: # don't run twice!
            if submit is True:  # but if previously, we weren't going to submit it, we will now if requested.
                self.next_csr_submit_after_generation = True
            return

        self.next_csr_generation_in_progress = True
        self.next_csr_submit_after_generation = submit

        self.next_csr_generation_count = 0
        self.next_csr_generation_in_progress = True
        logger.debug("About to generate new csr request: {request}", request=request)
        d = self._ParentLibrary.generate_csr(**request)
        d.addCallback(generate_new_csr_done, self)
        d.addErrback(generate_new_csr_error, self)

    def submit_csr(self):
        """
        Submit a CSR for signing, only if we have a CSR and KEY.
        :return:
        """
        self.next_submitted = int(time())
        missing = []
        if self.csr_next is None:
            missing.append("CSR")
        if self.key_next is None:
            missing.append("KEY")

        # print("sslcert:submit_csr - csr_text: %s" % self.csr_next)
        if len(missing) == 0:
            request = self._ParentLibrary.send_csr_request(self.csr_next, self.sslname)
            self.next_submitted = int(time())
        else:
            logger.warn("Requested to submit CSR, but these are missing: {missing}", missing=".".join(missing))
            raise YomboWarning("Unable to submit CSR.")
        logger.debug("Sending CSR Request from instance. Correlation id: {correlation_id}", correlation_id=request['properties']['correlation_id'])

    def yombo_csr_response(self, properties, msg, correlation):
        """
        A response from a CSR request has been received. Lets process it.

        :param properties: Properties of the AQMP message.
        :param msg: The message itself.
        :param correlation: Any correlation data regarding the AQMP message. We can check for timing, etc.
        :return:
        """
        if msg['status'] == "signed":
            self.chain_next = msg['chain_text']
            self.cert_next = msg['cert_text']
            self.next_signed = msg['cert_signed']
            self.next_expires = msg['cert_expires']
            self.next_is_valid = True
            self.sync_to_file()
            self.check_if_rotate_needed()
        # print("status: %s" % self.__dict__)

    def update_attributes(self, attributes):
        """
        Update various attributes. Should only be used by the SQLCerts system when loading updated things from
        a library or module.

        The attributes have already been screened by the parent.

        :param attributes:
        :return:
        """
        self.manage_requested = True
        for key, value in attributes.iteritems():
            if hasattr(self, key):
                setattr(self, key, value)

    def get_key(self):
        self.requested_locally = True
        return self.key

    # @inlineCallbacks
    # def delete(self):
    #     yield self._ParentLibrary._LocalDB.delete_sslcerts()
    #
    #     cert_path = self._Atoms.get('yombo.path') + "/usr/etc/certs/"
    #     cert_archive_path = self._Atoms.get('yombo.path') + "/usr/etc/certs/"
    #     pattern = "*_" + self.sslname + ".pem"
    #     for root, dirs, files in os.walk(cert_archive_path):
    #         for file in filter(lambda x: re.match(pattern, x), files):
    #             logger.debug("Removing file: {path}/{file}", path=cert_archive_path, file=file)
    #             # os.remove(os.path.join(root, file))
    #
    #     print("removing current cert file: %s" % self.filepath)
    #     # os.remove(self.filepath)
    #     if self.active_request is not None:
    #         #TODO: tell yombo we don't need this cert anymore.
    #         self.active_request = None
    #         del self._ParentLibrary.active_requests[self.sslname]

    def get(self):
        """
        Returns a signed cert, the key, and the chain.
        """
        if self.current_is_valid is True:
            logger.debug("Sending public signed cert details for {sslname}", sslname=self.sslname)
            return {
                'key': self.key_current,
                'cert': self.cert_current,
                'chain': self.chain_current,
                'expires': self.current_expires,
                'created': self.current_created,
                'signed': self.current_signed,
                'self_signed': False,
            }
        else:
            logger.info("Sending SELF SIGNED cert details for {sslname}", sslname=self.sslname)
            if self._ParentLibrary.self_signed_created is None:
                raise YomboWarning("Self signed cert not avail. Try restarting gateway.")
            else:
                return {
                    'key': self._ParentLibrary.self_signed_key,
                    'cert': self._ParentLibrary.self_signed_cert,
                    'chain': None,
                    'expires': self._ParentLibrary.self_signed_expires,
                    'created': self._ParentLibrary.self_signed_created,
                    'signed': self._ParentLibrary.self_signed_created,
                    'self_signed': True,
                }

    def _dump(self):
        """
        Returns a dictionary of the current attributes. This should only be used internally.

        :return:
        """
        return {
            'sslname': self.sslname,
            'cn': self.cn,
            'sans': self.sans,
            'update_callback_type': self.update_callback_type,
            'update_callback_component': self.update_callback_component,
            'update_callback_function': self.update_callback_function,
            'key_size': self.key_size,
            'key_type': self.key_type,
            'cert_previous': self.cert_previous,
            'chain_previous': self.chain_previous,
            'key_previous': self.key_previous,
            'previous_expires': self.previous_expires,
            'previous_created': self.previous_created,
            'previous_signed': self.previous_signed,
            'previous_submitted': self.previous_submitted,
            'previous_is_valid': self.previous_is_valid,
            'cert_current': self.cert_current,
            'chain_current': self.chain_current,
            'key_current': self.key_current,
            'key_current': self.key_current,
            'current_created': self.current_created,
            'current_expires': self.current_expires,
            'current_signed': self.current_signed,
            'current_submitted': self.current_submitted,
            'current_is_valid': self.current_is_valid,
            'csr_next': self.csr_next,
            'cert_next': self.cert_next,
            'chain_next': self.chain_next,
            'key_next': self.key_next,
            'next_created': self.next_created,
            'next_expires': self.next_expires,
            'next_signed': self.next_signed,
            'next_submitted': self.next_submitted,
            'next_is_valid': self.next_is_valid,
        }

    def __str__(self):
        """
        Print the sslname for the sslcert when printing this cert instance.
        """
        return self.sslname
