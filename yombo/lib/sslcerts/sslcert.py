# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Devices @ Module Development <https://yombo.net/docs/libraries/sslcerts>`_


This module provides support to the SSLCerts library. It's responsible for
maintaining itself and always ensuring an up to date signed cert if available
for use.

This library uses the file system to ('usr/etc/certs') to store certificates
and meta data. This allows other applications outside the Yombo Gateway to
to use the certificates for other uses. For example, the Mosquitto MQTT broker
will use the same certificate as the web interface library.

Developers can request a certifcate throug theh _sslcert_ hook to be generated
and then can find the certificate for use in the usr/etc/certs directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.13.0

:copyright: Copyright 2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/sslcerts.html>`_
"""
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

import glob
from hashlib import sha256
import os
import os.path
from time import time
from OpenSSL import crypto

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
import yombo.core.settings as settings
from yombo.utils import save_file, read_file, bytes_to_unicode
import collections

logger = get_logger('library.sslcerts.sslcert')


def human_status(valid):
    """
    Simply converts a next or current status to a human readable form
    :param valid:
    :return:
    """
    if valid is True:
        return "Valid"
    elif valid is False:
        return "Unsigned"
    elif valid is None:
        return "None"


class SSLCert(object):
    """
    A class representing a single cert.
    """
    @property
    def current_status(self):
        return human_status(self.current_is_valid)

    @property
    def next_status(self):
        return human_status(self.next_is_valid)

    def __str__(self):
        """
        Returns the name of the library.

        :return: Name of the library
        :rtype: string
        """
        return "Yombo SSLCert: %s with status: %s" % (self._sslname,
                                                      self.current_status)

    def __init__(self, source, sslcert, _parent_library):
        """
        Setup basic properties and populate values from the 'sslcert' incoming argument.

        :param source: *(source)* - One of: 'sql', 'sslcerts', or 'sqldict'
        :param sslcert: *(dictionary)* - A dictionary of the attributes to setup the class.
        :ivar sslname: *(string)* - The name of base file. The archive name will be based off this.
        :ivar key_size: *(int)* - Size of the key in bits.
        :ivar key_type: *(string)* - Either rsa or dsa.
        """
        self._FullName = 'yombo.gateway.lib.SSLCerts.SSLCert'
        self._Name = 'SSLCerts.SSLCert'
        self._Parent = _parent_library
        self.source = source
        self.working_dir = settings.arguments['working_dir']

        self.sslname = sslcert.sslname
        self.cn = sslcert.cn
        self.sans = sslcert.sans

        self.update_callback = None
        self.update_callback_type = None
        self.update_callback_component = None
        self.update_callback_function = None

        self.key_size = None
        self.key_type = None

        self.current_cert = None
        self.current_cert_crypt = None
        self.current_chain = None
        self.current_chain_crypt = None
        self.current_key = None
        self.current_key_crypt = None
        self.current_created = None
        self.current_expires = None
        self.current_signed = None
        self.current_submitted = None
        self.current_fqdn = None
        self.current_is_valid = None

        self.next_csr = None
        self.next_cert = None
        self.next_chain = None
        self.next_key = None
        self.next_created = None
        self.next_expires = None
        self.next_signed = None
        self.next_submitted = None
        self.next_fqdn = None
        self.next_is_valid = None
        self.next_csr_generation_error_count = 0
        self.next_csr_generation_in_progress = False
        self.next_csr_submit_after_generation = False

        self.update_attributes(sslcert)
        self.dirty = False
        self.sync_to_filesystem_working = False

        self.check_messages_of_the_unknown()

    @inlineCallbacks
    def start(self):
        """
        Called by the parent, SSLCerts, to load any data from the filesystem and then validate
        if the cert if valid.

        :return:
        """
        # SQLDict means it came from the database, so only scan the filesystem.
        if self.source != 'sqldict':
            yield self.sync_from_filesystem()

        self.check_is_valid()
        # print("status: %s" % self.__dict__)

        # check if we need to generate csr, sign csr, or rotate next with current.
        yield self.check_if_rotate_needed()

    @inlineCallbacks
    def stop(self):
        """
        Saves the cert meta data to disk...if it's dirty.

        :return:
        """
        yield self.sync_to_filesystem()
        self.dirty = False

    def update_attributes(self, attributes):
        """
        Update various attributes. Should only be used by the SQLCerts system when loading updated things from
        a library or module.

        The attributes have already been screened by the parent.

        :param attributes:
        :return:
        """
        if 'update_callback' in attributes:
            self.update_callback = attributes['update_callback']
        if 'update_callback_type' in attributes:
            self.update_callback_type = attributes['update_callback_type']
        if 'update_callback_component' in attributes:
            self.update_callback_component = attributes['update_callback_component']
        if 'update_callback_function' in attributes:
            self.update_callback_function = attributes['update_callback_function']

        if 'key_size' in attributes:
            self.key_size = int(attributes['key_size']) if attributes['key_size'] else None
        if 'key_type' in attributes:
            self.key_type = attributes['key_type']

        if 'current_cert' in attributes:
            self.current_cert = attributes['current_cert']
            if self.current_cert is not None:
                self.current_cert_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self.current_cert),
                if isinstance(self.current_cert_crypt, tuple):
                    self.current_cert_crypt = self.current_cert_crypt[0]
            else:
                self.current_cert_crypt = None
        if 'current_chain' in attributes:
            self.current_chain = attributes['current_chain']
            if self.current_chain is not None:
                self.current_chain_crypt = [crypto.load_certificate(crypto.FILETYPE_PEM, self.current_chain)],
                if isinstance(self.current_chain_crypt, tuple):
                    self.current_chain_crypt = self.current_chain_crypt[0]
            else:
                self.current_chain_crypt = None
        if 'current_key' in attributes:
            self.current_key = attributes['current_key']
            if self.current_key is not None:
                self.current_key_crypt = crypto.load_privatekey(crypto.FILETYPE_PEM, self.current_key),
                if isinstance(self.current_key_crypt, tuple):
                    self.current_key_crypt = self.current_key_crypt[0]
            else:
                self.current_key_crypt = None

        if 'current_created' in attributes:
            self.current_created = int(attributes['current_created']) if attributes['current_created'] else None
        if 'current_expires' in attributes:
            self.current_expires = int(attributes['current_expires']) if attributes['current_expires'] else None
        if 'current_signed' in attributes:
            self.current_signed = int(attributes['current_signed']) if attributes['current_signed'] else None
        if 'current_submitted' in attributes:
            self.current_submitted = int(attributes['current_submitted']) if attributes['current_submitted'] else None
        if 'current_fqdn' in attributes:
            self.current_fqdn = attributes['current_fqdn']
        if 'current_is_valid' in attributes:
            self.current_is_valid = attributes['current_is_valid']

        if 'next_csr' in attributes:
            self.next_csr = attributes['next_csr']
        if 'next_cert' in attributes:
            self.next_cert = attributes['next_cert']
        if 'next_chain' in attributes:
            self.next_chain = attributes['next_chain']
        if 'next_key' in attributes:
            self.next_key = attributes['next_key']
        if 'next_created' in attributes:
            self.next_created = int(attributes['next_created']) if attributes['next_created'] else None
        if 'next_expires' in attributes:
            self.next_expires = int(attributes['next_expires']) if attributes['next_expires'] else None
        if 'next_signed' in attributes:
            self.next_signed = int(attributes['next_signed']) if attributes['next_signed'] else None
        if 'next_submitted' in attributes:
            self.next_submitted = int(attributes['next_submitted']) if attributes['next_submitted'] else None
        if 'next_fqdn' in attributes:
            self.next_fqdn = attributes['next_fqdn']
        if 'next_is_valid' in attributes:
            self.next_is_valid = attributes['next_is_valid']

        self.dirty = True

    @inlineCallbacks
    def check_if_rotate_needed(self):
        """
        Always make sure the current key is valid. If it's expiring within 60 days, get a new cert.
        However, if the current cert is good, and not expiring soon, we should always have a fresh CSR
        ready to be signed when needed.

        :return:
        """
        logger.debug("Checking if I ({sslname}) need to be updated.", sslname=self.sslname)
        # Look for any tasks to do.
        self.check_if_fqdn_updated()  # if fqdn of cert doesn't match current, get new cert.

        new_cert_requested = False
        # if current is valid or will be expiring within the next 30 days, get a new cert
        if self.current_is_valid is not True or \
                self.current_key is None or \
                self.current_expires is None or \
                int(self.current_expires) < int(time() + (60*60*24*30)):
            if self.next_is_valid is True:
                self.make_next_be_current()  # Migrate the next key to the current key.
            else:  # next is not valid
                if self.next_csr is not None and self.next_key is not None:
                    self.submit_csr()
                else:
                    # print("requesting new cert....1")
                    yield self.request_new_csr(submit=True)
                    new_cert_requested = True

        # Prepare a next cert if it's missing and one hasn't already been requested.
        if self.next_csr is None and new_cert_requested is False:
            # print("requesting new cert....2")
            yield self.request_new_csr(submit=False)

        # print("check if rotated.... dirty: %s" % self.dirty)
        if self.dirty:
            yield self.sync_to_filesystem()

    def make_next_be_current(self):
        """
        Makes the next cert become the current cert. Then calls 'clean_section()'.

        :return:
        """
        self.current_cert = self.next_cert
        self.current_chain = self.next_chain
        self.current_key = self.next_key
        self.current_key_crypt = crypto.load_privatekey(crypto.FILETYPE_PEM, self.current_key),
        if isinstance(self.current_key_crypt, tuple):
            self.current_key_crypt = self.current_key_crypt[0]
        self.current_cert_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self.current_cert),
        if isinstance(self.current_cert_crypt, tuple):
            self.current_cert_crypt = self.current_cert_crypt[0]
        self.current_chain_crypt = [crypto.load_certificate(crypto.FILETYPE_PEM, self.current_chain)],
        if isinstance(self.current_chain_crypt, tuple):
            self.current_chain_crypt = self.current_chain_crypt[0]
        self.current_created = self.next_created
        self.current_expires = self.next_expires
        self.current_signed = self.next_signed
        self.current_submitted = self.next_submitted
        self.current_fqdn = self.next_fqdn
        self.current_is_valid = self.next_is_valid
        self.clean_section('next')

    def clean_section(self, label):
        """
        Used wipe out either 'next', or 'current'. This allows to make room or something new.

        :param label:
        :return:
        """
        # print("cleaning section: %s" % label)
        if label == 'next':
            self.next_csr = None
            self.next_csr_generation_error_count = 0

        setattr(self, "%s_cert" % label, None)
        setattr(self, "%s_chain" % label, None)
        setattr(self, "%s_key" % label, None)
        setattr(self, "%s_created" % label, None)
        setattr(self, "%s_expires" % label, None)
        setattr(self, "%s_signed" % label, None)
        setattr(self, "%s_submitted" % label, None)
        setattr(self, "%s_fqdn" % label, None)
        setattr(self, "%s_is_valid" % label, None)

        # now the the variables are deleted, lets delete the matching files
        for file_to_delete in glob.glob("%s/etc/certs/%s.%s.*" % (self.working_dir, self.sslname, label)):
            logger.debug("Removing ssl file file: %s" % file_to_delete)
            os.remove(file_to_delete)

        self.dirty = True

    def check_if_fqdn_updated(self):
        """
        Checks if the system's fqdn dns name changed and doesn't match the requested
        certificate, then we will mark any requested certs as being bad/empty.
        :return: 
        """
        system_fqdn = self._Parent.fqdn()
        if system_fqdn != self.current_fqdn and self.current_fqdn is not None:
            logger.warn("System FQDN doesn't match current requested cert for: {sslname}", sslname=self.sslname)
            # print("%s != %s"  %( system_fqdn, self.current_fqdn))
            self.current_is_valid = None
            self.dirty = True

        if system_fqdn != self.next_fqdn and self.next_fqdn is not None:
            logger.warn("System FQDN doesn't match next requested cert for: {sslname}", sslname=self.sslname)
            # print("%s != %s"  %( system_fqdn, self.next_fqdn))
            self.clean_section('next')

    def check_messages_of_the_unknown(self):
        if self.sslname in self._Parent.received_message_for_unknown:
            logger.warn("We have messages for us. TODO: Implement this.")

    def check_is_valid(self, label=None):
        """
        Used to validate if a give cert (next or current) is valid. If no label
        is provided, then both will checked.

        :param label: 
        :return: 
        """
        if label is None:
            labels = ['current', 'next']
        else:
            labels = [label]

        for label in labels:
            # print("check is valid for section: %s" % label)
            if getattr(self, "%s_expires" % label) is not None and \
                    int(getattr(self, "%s_expires" % label)) > int(time()) and \
                    getattr(self, "%s_signed" % label) is not None and \
                    getattr(self, "%s_key" % label) is not None and \
                    getattr(self, "%s_cert" % label) is not None and \
                    getattr(self, "%s_chain" % label) is not None:
                setattr(self, "%s_is_valid" % label, True)
            else:
                setattr(self, "%s_is_valid" % label, False)
                if label != "next":
                    if getattr(self, "%s_key" % label) is None or \
                            getattr(self, "%s_cert" % label) is None or \
                            getattr(self, "%s_chain" % label) is None or \
                            getattr(self, "%s_created" % label) is None:
                        self.clean_section(label)
                else:
                    # print("next_csr: %s" % getattr(self, "%s_csr" % label))
                    # print("next_created: %s" % getattr(self, "%s_created" % label))
                    if getattr(self, "%s_key" % label) is None or \
                            getattr(self, "%s_csr" % label) is None or \
                            getattr(self, "%s_created" % label) is None:
                        # print("calling clean section from check_is_valid_for NEXT")
                        self.clean_section(label)

        self.dirty = True

    @inlineCallbacks
    def sync_from_filesystem(self):
        """
        Reads meta data and items from the file system. This allows us to restore data incase the database
        goes south. This is important since only the gateway has the private key and cannot be recovered.

        :return:
        """
        logger.info("Inspecting file system for certs, and loading them.")

        for label in ['current', 'next']:
            setattr(self, "%s_is_valid" % label, None)

            if os.path.exists("%s/etc/certs/%s.%s.meta" % (self.working_dir, self.sslname, label)):
                logger.debug("SSL Meta found for: {label} - {sslname}", label=label, sslname=self.sslname)
                file_content = yield read_file("%s/etc/certs/%s.%s.meta" % (self.working_dir, self.sslname, label))
                meta = json.loads(file_content)
                # print("meta: %s" % meta)

                csr_read = False
                if label == 'next':
                    logger.debug("Looking for 'next' information.")
                    if os.path.exists("%s/etc/certs/%s.%s.csr.pem" % (self.working_dir, self.sslname, label)):
                        if getattr(self, "%s_csr" % label) is None:
                            csr = yield read_file(
                                "%s/etc/certs/%s.%s.csr.pem" % (self.working_dir, self.sslname, label),
                                True,
                            )
                            if sha256(str(csr).encode('utf-8')).hexdigest() == meta['csr']:
                                csr_read = True
                            else:
                                # print("%s = %s" % (
                                #     sha256(str(csr).encode('utf-8')).hexdigest(), meta['csr']
                                #     )
                                # )
                                logger.warn("Appears that the file system has bad meta signatures (csr). Purging.")
                                for file_to_delete in glob.glob("%s/etc/certs/%s.%s.*" % (self.working_dir, self.sslname, label)):
                                    logger.warn("Removing bad file: %s" % file_to_delete)
                                    os.remove(file_to_delete)
                                continue

                cert_read = False
                if getattr(self, "%s_cert" % label) is None:
                    if os.path.exists("%s/etc/certs/%s.%s.cert.pem" % (self.working_dir, self.sslname, label)):
                        # print("setting cert!!!")
                        cert = yield read_file(
                            "%s/etc/certs/%s.%s.cert.pem" % (self.working_dir, self.sslname, label),
                            True
                        )
                        cert_read = True
                        # print("testing with this cert: %s" % cert)
                        if sha256(str(cert).encode('utf-8')).hexdigest() != meta['cert']:
                            # print("%s != %s" % (sha256(str(cert).encode('utf-8')).hexdigest(), meta['cert']))
                            logger.warn("Appears that the file system has bad meta signatures (cert). Purging.")
                            for file_to_delete in glob.glob("%s/etc/certs/%s.%s.*" % (self.working_dir, self.sslname, label)):
                                logger.warn("Removing bad file: %s" % file_to_delete)
                                os.remove(file_to_delete)
                            continue

                chain_read = False
                if getattr(self, "%s_chain" % label) is None:
                    if os.path.exists("%s/etc/certs/%s.%s.chain.pem" % (self.working_dir, self.sslname, label)):
                        # print("setting chain!!!")
                        chain = yield read_file(
                            "%s/etc/certs/%s.%s.chain.pem" % (self.working_dir, self.sslname, label),
                            True
                        )
                        chain_read = True
                        if sha256(str(chain).encode('utf-8')).hexdigest() != meta['chain']:
                            logger.warn("Appears that the file system has bad meta signatures (chain). Purging.")
                            for file_to_delete in glob.glob("%s/etc/certs/%s.%s.*" % (self.working_dir, self.sslname, label)):
                                logger.warn("Removing bad file: %s" % file_to_delete)
                                os.remove(file_to_delete)
                            continue

                key_read = False
                if getattr(self, "%s_key" % label) is None:
                    if os.path.exists("%s/etc/certs/%s.%s.key.pem" % (self.working_dir, self.sslname, label)):
                        key = yield read_file(
                            "%s/etc/certs/%s.%s.key.pem" % self.working_dir, (self.sslname, label),
                            True
                        )
                        key_read = True
                        if sha256(str(key).encode('utf-8')).hexdigest() != meta['key']:
                            logger.warn("Appears that the file system has bad meta signatures (key). Purging.")
                            for file_to_delete in glob.glob("%s/etc/certs/%s.%s.*" % (self.working_dir, self.sslname, label)):
                                logger.warn("Removing bad file: %s" % file_to_delete)
                                os.remove(file_to_delete)
                            continue

                logger.debug("Reading meta file for cert: {label}", label=label)

                def return_int(the_input):
                    try:
                        return int(the_input)
                    except Exception as e:
                        return the_input

                if csr_read:
                    setattr(self, "%s_csr" % label, csr)
                if cert_read:
                    setattr(self, "%s_cert" % label, cert)
                if chain_read:
                    setattr(self, "%s_chain" % label, chain)
                if key_read:
                    setattr(self, "%s_key" % label, key)
                setattr(self, "%s_expires" % label, return_int(meta['expires']))
                setattr(self, "%s_created" % label, return_int(meta['created']))
                setattr(self, "%s_signed" % label, return_int(meta['signed']))
                setattr(self, "%s_submitted" % label, return_int(meta['submitted']))
                setattr(self, "%s_fqdn" % label, return_int(meta['fqdn']))

                self.check_is_valid(label)
            else:
                setattr(self, "%s_is_valid" % label, False)

    @inlineCallbacks
    def sync_to_filesystem(self):
        """
        Sync current data to the file system so other's can use the certs.

        :return:
        """
        logger.debug("Backing up SSL Certs to file system. Started")
        if self.sync_to_filesystem_working is True:
            return
        self.sync_to_filesystem_working = True
        self.dirty = False
        yield self._sync_to_filesystem()
        self.sync_to_filesystem_working = False

    @inlineCallbacks
    def _sync_to_filesystem(self):
        for label in ['current', 'next']:

            meta = {
                'created': getattr(self, "%s_created" % label),
                'expires': getattr(self, "%s_expires" % label),
                'signed': getattr(self, "%s_signed" % label),
                'submitted': getattr(self, "%s_submitted" % label),
                'fqdn': getattr(self, "%s_fqdn" % label),
                'key_type': self.key_type,
                'key_size': self.key_size,
            }

            if getattr(self, "%s_cert" % label) is None:
                meta['cert'] = None
                file = "%s/etc/certs/%s.%s.cert.pem" % (self.working_dir, self.sslname, label)
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta['cert'] = sha256(str(getattr(self, "%s_cert" % label)).encode('utf-8')).hexdigest()
                yield save_file("%s/etc/certs/%s.%s.cert.pem" % (self.working_dir, self.sslname, label),  getattr(self, "%s_cert" % label))

            if getattr(self, "%s_chain" % label) is None:
                meta['chain'] = None
                file = "%s/etc/certs/%s.%s.chain.pem" % (self.working_dir, self.sslname, label)
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta['chain'] = sha256(str(getattr(self, "%s_chain" % label)).encode('utf-8')).hexdigest()
                yield save_file("%s/etc/certs/%s.%s.chain.pem" % (self.working_dir, self.sslname, label), getattr(self, "%s_chain" % label))

            if getattr(self, "%s_key" % label) is None:
                meta['key'] = None
                file = "%s/etc/certs/%s.%s.key.pem" % (self.working_dir, self.sslname, label)
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta['key'] = sha256(str(getattr(self, "%s_key" % label)).encode('utf-8')).hexdigest()
                yield save_file("%s/etc/certs/%s.%s.key.pem" % (self.working_dir, self.sslname, label), getattr(self, "%s_key" % label))

            if label == 'next':
                if getattr(self, "%s_csr" % label) is None:
                    meta['csr'] = None
                    file = "%s/etc/certs/%s.%s.csr.pem" % (self.working_dir, self.sslname, label)
                    if os.path.exists(file):
                        os.remove(file)
                else:
                    meta['csr'] = sha256(str(getattr(self, "%s_csr" % label)).encode('utf-8')).hexdigest()
                    yield save_file("%s/etc/certs/%s.%s.csr.pem" % (self.working_dir, self.sslname, label), getattr(self, "%s_csr" % label))

            yield save_file("%s/etc/certs/%s.%s.meta" % (self.working_dir, self.sslname, label),
                            json.dumps(meta, indent=4))

            yield save_file("%s/etc/certs/%s.meta" % (self.working_dir, self.sslname),
                            json.dumps({
                                'sans': self.sans,
                                'cn': self.cn,
                            }, indent=4))

    @inlineCallbacks
    def request_new_csr(self, submit=False, force_new=False):
        """
        Requests a new csr to be generated. This uses the base class to do the heavy lifting.

        We usually don't submit the CSR at the time generation. This allows the CSR to be genearted ahead
        of when we actually need.

        :param submit: If true, will also submit the csr.
        :param force_new: Will create a new CSR regardless of the current state.
        :return:
        """
        self.dirty = True
        # print("1 calling local generate_new_csr. Name: %s Force: %s.  Is valid: %s" % (
        #     self.sslname, force_new, self.next_is_valid
        #     )
        # )
        if force_new is True:
            self.clean_section('next')
        else:
            self.check_is_valid('next')

        if self.next_is_valid is not None:
            if submit is True:
                if self.next_csr_generation_in_progress is True:
                    self.next_csr_submit_after_generation = True
                else:
                    self.submit_csr()
            else:
                logger.info("Was asked to generate CSR, but we don't need it for: {sslname}", sslname=self.sslname)
            return

        logger.warn("generate_new_csr: {sslname}.  Submit: {submit}", sslname=self.sslname, submit=submit)
        # End local functions.
        request = {
            'sslname': self.sslname,
            'key_size': self.key_size,
            'key_type': self.key_type,
            'cn': self.cn,
            'sans': self.sans
        }

        if self.next_csr_generation_in_progress is True:  # don't run twice!
            if submit is True:  # but if previously, we weren't going to submit it, we will now if requested.
                self.next_csr_submit_after_generation = True
            return

        self.next_csr_generation_in_progress = True
        self.next_csr_submit_after_generation = submit

        self.next_csr_generation_count = 0
        self.next_csr_generation_in_progress = True
        logger.debug("About to generate new csr request: {request}", request=request)

        try:
            the_job = yield self._Parent.generate_csr_queue.put(request)
            results = the_job.result
            self.next_fqdn = self._Parent.fqdn()
        except Exception as e:
            self.next_csr_generation_error_count += 1
            if self.next_csr_generation_error_count < 5:
                logger.warn("Error generating new CSR for '{sslname}'. Will retry in 15 seconds. Exception : {failure}",
                            sslname=self.sslname, failure=e)
                reactor.callLater(15, self.request_new_csr, submit, force_new)
            else:
                logger.error(
                    "Error generating new CSR for '{sslname}'. Too many retries, perhaps something wrong with our request. Exception : {failure}",
                    sslname=self.sslname, failure=e)
                self.next_csr_generation_in_progress = False
            return False

        logger.debug("request_new_csr: {sslname}", sslname=self.sslname)
        results = bytes_to_unicode(results)
        self.next_key = results['key']
        self.next_csr = results['csr']
        # print("request_new_csr csr: %s " % self.next_csr)
        yield save_file("%s/etc/certs/%s.next.csr.pem" % (self.working_dir, self.sslname), self.next_csr)
        yield save_file("%s/etc/certs/%s.next.key.pem" % (self.working_dir, self.sslname), self.next_key)
        self.next_created = int(time())
        self.dirty = True
        self.next_csr_generation_in_progress = False
        if submit is True:
            # print("calling submit_csr from generate_new_csr_done")
            self.submit_csr()

    def submit_csr(self):
        """
        Submit a CSR for signing, only if we have a CSR and KEY.
        :return:
        """
        if self._Parent._Loader.operating_mode != 'run':
            return

        # self.next_submitted = int(time())
        missing = []
        if self.next_csr is None:
            missing.append("CSR")
        if self.next_key is None:
            missing.append("KEY")

        # print("sslcert:submit_csr - csr_text: %s" % self.next_csr)
        if len(missing) == 0:
            request = self._Parent.send_csr_request(self.next_csr, self.sslname)
            logger.debug("Sending CSR Request from instance. Correlation id: {correlation_id}",
                         correlation_id=request['properties']['correlation_id'])
            self.next_submitted = int(time())
        else:
            logger.warn("Requested to submit CSR, but these are missing: {missing}", missing=".".join(missing))
            raise YomboWarning("Unable to submit CSR.")

        self.dirty = True

    @inlineCallbacks
    def amqp_incoming_response_to_csr_request(self, properties, body, correlation_info):
        """
        A response from a CSR request has been received. Lets process it.

        :param properties: Properties of the AQMP message.
        :param body: The message itself.
        :param correlation: Any correlation data regarding the AQMP message. We can check for timing, etc.
        :return:
        """
        logger.debug("Received a signed SSL/TLS certificate for: {sslname}", sslname=self.sslname)
        if body['status'] == "signed":
            self.next_chain = body['chain_text']
            self.next_cert = body['cert_text']
            self.next_signed = body['cert_signed']
            self.next_expires = body['cert_expires']
            self.next_is_valid = True
            self.dirty = True
            yield self.check_if_rotate_needed()  # this will rotate next into current


        method = None
        if self.current_is_valid is not True:
            logger.warn("Asked to update the requester or new cert, but current cert isn't valid!")
            return

        if self.update_callback is not None and isinstance(self.update_callback, collections.Callable):
            method = self.update_callback
        elif self.update_callback_type is not None and \
                self.update_callback_component is not None and \
                self.update_callback_function is not None:
            try:
                method = self._Parent._Loader.find_function(
                    self.update_callback_type,
                    self.update_callback_component,
                    self.update_callback_function,
                )
            except YomboWarning as e:
                logger.warn("Invalid update_callback information provided: %s" % e)

        logger.info("Method to notify ssl requester that there's a new cert: {method}", method=method)

        if method is not None and isinstance(method, collections.Callable):
            logger.info("About to tell the SSL/TLS cert requester know we have a new cert, from: {sslname}",
                        sslname=self.sslname)

            the_cert = self.get()
            d = Deferred()
            d.addCallback(lambda ignored: maybeDeferred(method, the_cert))
            d.addErrback(self.tell_requester_failure)
            d.callback(1)
            yield d

    def tell_requester_failure(self, failure):
        logger.error("Got failure when telling SSL/TLS dependents we have a cert: {failure}", failure=failure)

    def get(self):
        """
        Returns a signed cert, the key, and the chain.
        """
        if self.current_is_valid is True:
            logger.debug("Sending public signed cert details for {sslname}", sslname=self.sslname)
            return {
                'key': self.current_key,
                'key_crypt': self.current_key_crypt,
                'cert': self.current_cert,
                'cert_crypt': self.current_cert_crypt,
                'chain': self.current_chain,
                'chain_crypt': self.current_chain_crypt,
                'expires': self.current_expires,
                'created': self.current_created,
                'signed': self.current_signed,
                'self_signed': False,
                'cert_file': self._Parent._Atoms.get('working_dir') + "/etc/certs/%s.current.cert.pem" %
                            self.sslname,
                'key_file': self._Parent._Atoms.get('working_dir') + "/etc/certs/%s.current.key.pem" %
                            self.sslname,
                'chain_file': self._Parent._Atoms.get('working_dir') + "/etc/certs/%s.current.chain.pem" %
                            self.sslname,
            }
        else:
            logger.debug("Sending SELF SIGNED cert details for {sslname}", sslname=self.sslname)
            if self._Parent.self_signed_created is None:
                raise YomboWarning("Self signed cert not avail. Try restarting gateway.")
            else:
                key_crypt = crypto.load_privatekey(crypto.FILETYPE_PEM, self._Parent.self_signed_key)
                if isinstance(key_crypt, tuple):
                    key_crypt = key_crypt[0]
                cert_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self._Parent.self_signed_cert)
                if isinstance(cert_crypt, tuple):
                    cert_crypt = cert_crypt[0]
                return {
                    'key': self._Parent.self_signed_key,
                    'cert': self._Parent.self_signed_cert,
                    'chain': None,
                    'key_crypt': key_crypt, ####
                    'cert_crypt': cert_crypt,
                    'chain_crypt': None,
                    'expires': self._Parent.self_signed_expires,
                    'created': self._Parent.self_signed_created,
                    'signed': self._Parent.self_signed_created,
                    'self_signed': True,
                    'cert_file': self._Parent._Atoms.get('working_dir') + "/etc/certs/sslcert_selfsigned.cert.pem",
                    'key_file': self._Parent._Atoms.get('working_dir') + "/etc/certs/%sslcert_selfsigned.key.pem",
                    'chain_file': None,
                }

    def asdict(self):
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
            'key_size': int(self.key_size),
            'key_type': self.key_type,
            'current_cert': self.current_cert,
            'current_chain': self.current_chain,
            'current_key': self.current_key,
            'current_created': None if self.current_created is None else int(self.current_created),
            'current_expires': None if self.current_expires is None else int(self.current_expires),
            'current_signed': self.current_signed,
            'current_submitted': self.current_submitted,
            'current_fqdn': self.current_fqdn,
            'current_is_valid': self.current_is_valid,
            'next_csr': self.next_csr,
            'next_cert': self.next_cert,
            'next_chain': self.next_chain,
            'next_key': self.next_key,
            'next_created': None if self.next_created is None else int(self.next_created),
            'next_expires': None if self.next_expires is None else int(self.next_expires),
            'next_signed': self.next_signed,
            'next_submitted': self.next_submitted,
            'next_fqdn': self.next_fqdn,
            'next_is_valid': self.next_is_valid,
        }
