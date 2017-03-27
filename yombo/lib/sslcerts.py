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

from time import time
import os
import re
import os.path
from hashlib import sha256

from time import gmtime, mktime, time
from os.path import exists, join
from socket import gethostname

# Import 3rd-party libs
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet import threads
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.utils import save_file, random_string

from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import read_file, split, global_invoke_all, string_to_number, global_invoke_all
from yombo.utils.dictobject import DictObject

logger = get_logger('library.sslcerts')


class SSLCerts(YomboLibrary):
    """
    Responsible for managing various certificates for Yombo.
    """
    @inlineCallbacks
    def _init_(self):
        """
        On startup, various libraries will need certs (webinterface, MQTT) will need at least a basic cert.
        This module loads previously created certs. Then, after things settle, it will request new certs
        as needed.

        If a cert isn't avail for the requested sslname, it will receive a sign-signed certificate.
        :return:
        """
        self._LocalDB = self._Libraries['localdb']
        self.hostname = gethostname()

        self.gwid = self._Configs.get("core", "gwid")

        self.self_signed_cert_file = self._Atoms.get('yombo.path') + "/usr/etc/certs/sslcert_selfsigned.cert.pem"
        self.self_signed_key_file = self._Atoms.get('yombo.path') + "/usr/etc/certs/sslcert_selfsigned.key.pem"

        self.sslcert_get_failed = {}  # calls where we had to send self-signed certs back, when avail, lets send a real one

        if not exists(self.self_signed_cert_file) \
                or not exists(self.self_signed_key_file):
            logger.warn("Self signed cert is missing, will create another. This can take a few moments.")
            yield self._create_self_signed_cert()

        self.self_signed_cert = read_file(self.self_signed_cert_file)
        self.self_signed_key = read_file(self.self_signed_key_file)

        self.send_request_ids = yield self._SQLDict.get(self, "send_request_ids")

        self.managed_certs = {}
        managed_certs = yield self._SQLDict.get(self, "managed_certs", self.sslcert_serializer)
        for key, item in managed_certs.iteritems():
            self.managed_certs['key'] = SSLCert('sqldict', DictObject(item), self)

    #     print("testing loader function.")
    #     afunction = self._Loader.find_function('library', 'SSLCerts', 'testit')
    #     afunction()
    #
    # def testit(self):
    #     print("I WAS CALLED!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1")

    def sslcert_serializer(self, item):
        raise YomboWarning("Nothing to save yet!")
        return item.dump()

    def load_a_cert(self, record):
        """
        Creates a cert instance from a cert record

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        """
        cert_id = record.id
        self.managed_certs[cert_id] = SSLCert('sql', DictObject(record), self)
        self.managed_certs[cert_id]._init_()

    def _module_started_(self):
        """
        Called before the modules have their preload called.

        In turn, calls the hook "sslcerts" to gather requirements to manage certs.

        :return:
        """
        # get all certs required.
        # gerneate and request new certs
        # delte old certs
        # delete certs from database where there is a newer cert, but keep last 2 certs, keep non-expired

        # print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        sslcerts = global_invoke_all('_sslcerts_', called_by=self)
        # logger.error("sslcerts_system: {sslcerts_system}", sslcerts_system=sslcerts)
        for component_name, item in sslcerts.iteritems():
            if 'sslname' not in item:
                logger.warn("Discarding SSL Cert request, required attribute 'sslname' is missing.")
                continue

            if 'key_type' in item:
                if item['key_type'] not in ('rsa', 'dsa'):
                    raise YomboWarning("key_type must be rsa or dsa")
            else:
                item['key_type'] = 'rsa'

            item['key_size'] = 4096

            if item['sslname'] in self.managed_certs:
                self.managed_certs.update_attributes(DictObject(item, True, None))
            else:
                self.managed_certs = SSLCert('sslcerts', DictObject(item), self)

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
            self.sslcert_get_failed[sslname_requested] = True
            return {
                'key': self.self_signed_key,
                'cert': self.self_signed_cert,
            }

    @inlineCallbacks
    def generate_csr(self, **kwargs):
        """
        Requests certs to be made. Will return right away with a request ID. A callback can be set to return
        the cert once it's complete.

        :param sans: List of Subject Alternative Names
        :return:
        """
        print("in generate_csr: %s" % kwargs)

        if 'sans' not in kwargs:
            kwargs['sans'] = None

        if 'key_type' in kwargs:
            if kwargs['key_type'] not in ('rsa', 'dsa'):
                raise YomboWarning("key_type must be rsa or dsa")
        else:
            kwargs['key_type'] = 'rsa'

        if kwargs['key_type'] == 'rsa':
            kwargs['key_type'] = crypto.TYPE_RSA
        else:
            kwargs['key_type'] = crypto.TYPE_DSA

        kwargs['key_size'] = 4096

        if 'csr_file' not in kwargs:
            kwargs['csr_file'] = None

        if 'key_file' not in kwargs:
            kwargs['key_file'] = None

            #    csr_file = 'host.csr'
            #     priavet_key_file = 'host.key'

        req = crypto.X509Req()
        req.get_subject().CN = self.gwid
        req.get_subject().countryName = 'US'
        req.get_subject().stateOrProvinceName = 'California'
        req.get_subject().localityName = 'Sacramento'
        req.get_subject().organizationName = 'Yombo Gateway'
        req.get_subject().organizationalUnitName = 'Gateway'

        # Appends SAN to have 'DNS:'
        if kwargs['sans'] is not None:
            san_string = []
            for i in kwargs['sans']:
                san_string.append("DNS: %s" % i)
            san_string = ", ".join(san_string)

            x509_extensions = [crypto.X509Extension("subjectAltName", False, san_string)]
            req.add_extensions(x509_extensions)

        key = yield threads.deferToThread(self._generate_key, **{'key_type': kwargs['key_type'], 'key_size': kwargs['key_size']})
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
        cn = "%s %s" % (self.gwid, self.hostname)
        req.get_subject().CN = cn[0:63]
        req.get_subject().countryName = 'US'
        req.get_subject().stateOrProvinceName = 'California'
        req.get_subject().localityName = 'Sacramento'
        req.get_subject().organizationName = 'Yombo Gateway'
        req.get_subject().organizationalUnitName = 'Gateway'

        req.set_serial_number(int(time()))
        req.gmtime_adj_notBefore(0)
        req.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
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


    def yombo_csr_send_request(self, csr_text):
        body = { 'csr_text': csr_text}

        headers= {
            "request_type": "sslcert",
            "ssl_item": "csr_request",
        }
        request = self.generate_sslrequest_request(headers, body, self.yombo_csr_response)

        self._AMQPYombo.publish(**request)
        return int(time())

    def yombo_csr_response(self, properties, msg, correlation):
        print("yombo_csr_response %s" % msg)
        # print("pong props: %s" % properties)
        # print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!singing response from server: %s" % msg)

    def amqp_incoming(self, properties, msg, correlation):
        """
        Messages will be delivered here if
        :param properties:
        :param msg:
        :param correlation:
        :return:
        """

    def validate_csr_private_certs_match(self, csr_text, key_text):
        csr = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr_text)
        key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_text)
        return csr.verify(key)

    def generate_sslrequest_request(self, headers, request_data="", callback=None):
        """
        Generate a request specific to this library - configs!

        :param headers:
        :param request_data:
        :return:
        """
        request_msg = self._AMQPYombo.generate_message_request('ysrv.e.gw_sslcerts', 'yombo.gateway.lib.sslcerts',
                                                    "yombo.server.sslcerts", headers, request_data, callback)
        request_msg['routing_key'] = '*'
        logger.debug("response: {request_msg}", request_msg=request_msg)
        return request_msg


class SSLCert(object):
    """
    A class representing a single cert.
    """
    def __init__(self, source, sslcert, _ParentLibrary):
        """
        :param source: *(source)* - One of: 'sql', 'sslcerts', or 'sqldict'
        :param sslcert: *(dictionary)* - A dictionary of the attributes to setup the class.
        :ivar sslname: *(string)* - The name of base file. The archive name will be based off this.
        :ivar state: *(string)* - New (from _sslcerts_), existing (from sql)
        :ivar filepath: *(string)* - The full path to the pem file.
        :ivar key_size: *(int)* - Size of the key in bits.
        :ivar key_type: *(string)* - Either rsa or dsa.
        :ivar created: *(int)* - Time when cert was created.
        :ivar signed: *(int)* - Time when cert was signed.
        :ivar expires: *(int)* - Time when cert expires.
        :ivar history: *(list)* - A list of of events for this key.
        """
        self._FullName = 'yombo.gateway.lib.SSLCerts.SSLCert'
        self._Name = 'SSLCerts.SSLCert'
        self._ParentLibrary = _ParentLibrary

        print("sslcert: %s" % sslcert)

        self.sslname = sslcert.sslname
        self.sans = sslcert.sans
        self.filename = sslcert.get('filename', None)

        self.update_callback_type = sslcert.get('update_callback_type', None)
        self.update_callback_component = sslcert.get('update_callback_component', None)
        self.update_callback_function = sslcert.get('update_callback_function', None)

        self.key_size = int(sslcert.get('key_size', None))
        self.key_type = sslcert.get('key_type', None)

        self.csr_previous = sslcert.get('csr_previous', None)
        self.key_previous = sslcert.get('key_previous', None)
        self.cert_previous = sslcert.get('cert_previous', None)
        self.key_previous_created = sslcert.get('key_previous_created', None)
        self.key_previous_signed = sslcert.get('key_previous_signed', None)
        self.key_previous_submitted = sslcert.get('key_previous_submitted', None)

        self.csr_current = sslcert.get('csr_current', None)
        self.cert_current = sslcert.get('cert_current', None)
        self.key_current = sslcert.get('key_current', None)
        self.key_current_created = sslcert.get('key_current_created', None)
        self.key_current_expires = sslcert.get('key_current_expires', None)
        self.key_current_signed = sslcert.get('key_current_signed', None)
        self.key_current_submitted = sslcert.get('key_current_submitted', None)

        self.csr_next = sslcert.get('csr_previous', None)
        self.cert_next = sslcert.get('cert_next', None)
        self.key_next = sslcert.get('key_previous', None)
        self.key_next_created = sslcert.get('key_next_created', None)
        self.key_next_signed = sslcert.get('key_next_signed', None)
        self.key_next_submitted = sslcert.get('key_next_submitted', None)
        self.state = sslcert.get('state', 'new')

        # check if we need to do anything.

        print("state:%s" % self.state)
        if self.state == 'current':
            if self.key_current_expires > int(time() + (30*24*60*60)): # if expires in next 30 days, lets do something.
                self.generate_new_csr()

        if self.state == 'new' or self.state == 'generating':  # new or something died in middle, start over.
            self.generate_new_csr()

        if self.state == 'generated':
            self.submit_csr()

        if self.state == 'submitted_csr':
            self.ask_for_signed()

    def generate_new_csr(self):
        logger.info("generate_new_csr: {sslname}", sslname=self.sslname)
        def generate_new_csr_error(failure, self):
            logger.error("Error generating new CSR for '{sslname}'. Will retry in 15 seconds. Exception : {failure}", sslname=self.sslname, failure=failure)
            reactor.callLater(15, self.generate_new_csr)
            return 100

        def generate_new_csr_done(results, self):
            logger.info("generate_new_csr_done: {sslname}", sslname=self.sslname)
            self.state = 'generated'
            self.key_next = results['key']
            self.csr_next = results['csr']
            save_file('usr/etc/certs/%s.next.csr.pem' % self.sslname, self.csr_next)
            save_file('usr/etc/certs/%s.next.key.pem' % self.sslname, self.key_next)
            meta = {
                'time': int(time()),
                'key': sha256(self.key_next).hexdigest(),
                'csr': sha256(self.csr_next).hexdigest(),
            }
            save_file('usr/etc/certs/%s.next.meta' % self.sslname, json.dumps(meta, separators=(',',':')))
            self.key_next_created = int(time())
            self.submit_csr()

        request = {
            'key_size': self.key_size,
            'key_type': self.key_type,
            'sans': self.sans
        }

        have_csr = False
        have_key = False
        if self.key_next_created is None:
            print("nothing in memory, checking file system")
            if os.path.exists('usr/etc/certs/%s.next.meta' % self.sslname) and \
                os.path.exists('usr/etc/certs/%s.next.csr.pem' % self.sslname) and \
                os.path.exists('usr/etc/certs/%s.next.key.pem' % self.sslname):
                meta = json.loads(read_file('usr/etc/certs/%s.next.meta' % self.sslname))
                print("found private key in file: %s" % meta)

                return
            else:
                print("NOT found private key in file")

        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!generating new request....%s" % request)
        self.state = 'generating'
        d = self._ParentLibrary.generate_csr(**request)
        d.addCallback(generate_new_csr_done, self)
        d.addErrback(generate_new_csr_error, self)

        # d = self._DevicesLibrary._Libraries['localdb'].get_variables('device', self.device_id)
        # d.addErrback(gotException)
        # d.addCallback(set_variables)
        # d.addErrback(gotException)
        #
        # if self.test_device is False:
        #     d.addCallback(lambda ignored: self.load_history(35))
        # return d

    def submit_csr(self):
        logger.warn("Sending CSR Request from instance.")
        self.key_next_submitted = self._ParentLibrary.yombo_csr_send_request(self.csr_next)

    def update_attributes(self, attributes):
        self.manage_requested = True
        for key, value in attributes:
            if hasattr(self, key):
                setattr(self, key, value)

    def get_key(self):
        self.requested_locally = True
        return self.key

    @inlineCallbacks
    def delete(self):
        yield self._ParentLibrary._LocalDB.delete_sslcerts()

        cert_path = self._Atoms.get('yombo.path') + "/usr/etc/certs/"
        cert_archive_path = self._Atoms.get('yombo.path') + "/usr/etc/certs/"
        pattern = "*_" + self.sslname + ".pem"
        for root, dirs, files in os.walk(cert_archive_path):
            for file in filter(lambda x: re.match(pattern, x), files):
                print("Removing file: %s/%s" % (cert_archive_path, file))
                # os.remove(os.path.join(root, file))

        print("removing current cert file: %s" % self.filepath)
        # os.remove(self.filepath)
        if self.active_request is not None:
            #TODO: tell yombo we don't need this cert anymore.
            self.active_request = None
            del self._ParentLibrary.active_requests[self.sslname]

    def dump(self):
        return None

    def __str__(self):
        """
        Print the sslname for the sslcert when printing this cert instance.
        """
        return self.sslname
