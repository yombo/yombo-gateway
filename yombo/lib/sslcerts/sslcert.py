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
import glob
from hashlib import sha256
import json
from OpenSSL import crypto
import os
import os.path
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
import yombo.core.settings as settings
from yombo.utils import save_file, read_file, bytes_to_unicode, sha256_compact, unicode_to_bytes

import collections

logger = get_logger("library.sslcerts.sslcert")


def human_state(valid):
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


class SSLCert(Entity):
    """
    A class representing a single cert.
    """
    # @property
    # def current_status(self):
    #     return human_state(self.current_is_valid)
    #
    # @property
    # def next_status(self):
    #     return human_state(self.next_is_valid)

    def __str__(self):
        """
        Returns the name of the library.

        :return: Name of the library
        :rtype: string
        """
        return f"Yombo SSLCert: {self._sslname} with status: {self.current_status}"

    def __init__(self, _parent_library, source, sslcert):
        """
        Setup basic properties and populate values from the "sslcert" incoming argument.

        :param source: *(source)* - One of: "sql", "sslcerts", or "sqldict"
        :param sslcert: *(dictionary)* - A dictionary of the attributes to setup the class.
        :ivar sslname: *(string)* - The name of base file. The archive name will be based off this.
        :ivar key_size: *(int)* - Size of the key in bits.
        :ivar key_type: *(string)* - Either rsa or dsa.
        """
        self._Entity_type = "SSL Certificate"
        self._Entity_label_attribute = "sslname"

        super().__init__(_parent_library)
        self.source = source
        self.working_dir = settings.arguments["working_dir"]

        self.sslname = sslcert.sslname
        self.cn = sslcert.cn
        self.sans = sslcert.sans

        self.update_callback = None
        self.update_callback_type = None
        self.update_callback_component = None
        self.update_callback_function = None

        self.key_size = None
        self.key_type = None

        self.current_status = None       # new / signed
        self.current_status_msg = None   # new / signed / whatever from yombo servers
        self.current_csr_hash = None     # sha256(compact) hash of csr
        self.current_cert = None         # The signed cert from Lets Encrypt (or self signed)
        self.current_cert_crypt = None   # A ready to use crypto key
        self.current_chain = None        # Additional certs to complete the chain
        self.current_chain_crypt = None  # A ready to use crypto key
        self.current_key = None          # The private key - keep this a secret!
        self.current_key_crypt = None    #
        self.current_created_at = None   # WHen the cert was created
        self.current_expires_at = None   # The when signature expires
        self.current_signed_at = None    # When it was signed at
        self.current_submitted_at = None # When it was sent to Yombo server for signing by Lets Encrypt
        self.current_fqdn = None         # The fqdn of the cert
        self.current_is_valid = None     # If the cert is still valid.

        self.next_status = None
        self.next_status_msg = None
        self.next_csr = None             # cert sign request
        self.next_csr_hash = None        # hash of the csr
        self.next_cert = None
        self.next_chain = None
        self.next_key = None
        self.next_created_at = None
        self.next_expires_at = None
        self.next_signed_at = None
        self.next_submitted_at = None
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
        if self.source != "sqldict":
            yield self.sync_from_filesystem()

        self.check_is_valid()
        # print("status: %s" % self.__dict__)

        # check if we need to generate csr, sign csr, or rotate next with current.
        yield self.check_if_rotate_needed()

    @inlineCallbacks
    def stop(self):
        """
        Saves the cert meta data to disk...if it"s dirty.

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
        if "update_callback" in attributes:
            self.update_callback = attributes["update_callback"]
        if "update_callback_type" in attributes:
            self.update_callback_type = attributes["update_callback_type"]
        if "update_callback_component" in attributes:
            self.update_callback_component = attributes["update_callback_component"]
        if "update_callback_function" in attributes:
            self.update_callback_function = attributes["update_callback_function"]

        if "key_size" in attributes:
            self.key_size = int(attributes["key_size"]) if attributes["key_size"] else None
        if "key_type" in attributes:
            self.key_type = attributes["key_type"]

        if "current_cert" in attributes:
            self.current_cert = attributes["current_cert"]
        if "current_chain" in attributes:
            self.current_chain = attributes["current_chain"]
        if "current_key" in attributes:
            self.current_key = attributes["current_key"]
        self.set_crypto()

        if "current_status" in attributes:
            self.current_status = attributes["current_status"]
        if "current_status_msg" in attributes:
            self.current_status_msg = attributes["current_status_msg"]
        if "current_csr_hash" in attributes:
            self.current_csr_hash = attributes["current_csr_hash"]
        if "current_created_at" in attributes:
            self.current_created_at = int(attributes["current_created_at"]) if attributes["current_created_at"] else None
        if "current_expires_at" in attributes:
            self.current_expires_at = int(attributes["current_expires_at"]) if attributes["current_expires_at"] else None
        if "current_signed_at" in attributes:
            self.current_signed_at = int(attributes["current_signed_at"]) if attributes["current_signed_at"] else None
        if "current_submitted_at" in attributes:
            self.current_submitted_at = int(attributes["current_submitted_at"]) if attributes["current_submitted_at"] else None
        if "current_fqdn" in attributes:
            self.current_fqdn = attributes["current_fqdn"]
        if "current_is_valid" in attributes:
            self.current_is_valid = attributes["current_is_valid"]

        if "next_status" in attributes:
            self.next_status = attributes["next_status"]
        if "next_status_msg" in attributes:
            self.next_status_msg = attributes["next_status_msg"]
        if "next_csr_hash" in attributes:
            self.next_csr_hash = attributes["next_csr_hash"]
        if "next_csr" in attributes:
            self.next_csr = attributes["next_csr"]
        if "next_cert" in attributes:
            self.next_cert = attributes["next_cert"]
        if "next_chain" in attributes:
            self.next_chain = attributes["next_chain"]
        if "next_key" in attributes:
            self.next_key = attributes["next_key"]
        if "next_created_at" in attributes:
            self.next_created_at = int(attributes["next_created_at"]) if attributes["next_created_at"] else None
        if "next_expires_at" in attributes:
            self.next_expires_at = int(attributes["next_expires_at"]) if attributes["next_expires_at"] else None
        if "next_signed_at" in attributes:
            self.next_signed_at = int(attributes["next_signed_at"]) if attributes["next_signed_at"] else None
        if "next_submitted_at" in attributes:
            self.next_submitted_at = int(attributes["next_submitted_at"]) if attributes["next_submitted_at"] else None
        if "next_fqdn" in attributes:
            self.next_fqdn = attributes["next_fqdn"]
        if "next_is_valid" in attributes:
            self.next_is_valid = attributes["next_is_valid"]

        # do some back checks.
        if self.next_csr is not None and self.next_csr_hash is None:
            self.next_csr_hash = sha256_compact(unicode_to_bytes(self.next_csr))
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
                self.current_expires_at is None or \
                int(self.current_expires_at) < int(time() + (86400*30)):
            if self.next_is_valid is True:
                self.make_next_be_current()  # Migrate the next key to the current key.
            else:  # next is not valid
                if self.next_csr is not None and self.next_key is not None:
                    self.submit_csr()
                else:
                    yield self.request_new_csr(submit=True)
                    new_cert_requested = True

        # Prepare a next cert if it's missing and one hasn't already been requested.
        if self.next_csr is None and new_cert_requested is False:
            yield self.request_new_csr(submit=False)

        if self.dirty:
            yield self.sync_to_filesystem()

    def make_next_be_current(self):
        """
        Makes the next cert become the current cert. Then calls "clean_section()".

        :return:
        """
        self.current_status = self.next_status
        self.current_status_msg = self.next_status_msg
        self.current_csr_hash = self.next_csr_hash
        self.current_cert = self.next_cert
        self.current_chain = self.next_chain
        self.current_key = self.next_key
        self.current_key_crypt = None,
        self.current_cert_crypt = None,
        self.current_chain_crypt = None,
        # self.current_chain_crypt = [crypto.load_certificate(crypto.FILETYPE_PEM, self.current_chain)],
        # if isinstance(self.current_chain_crypt, tuple):
        #     self.current_chain_crypt = self.current_chain_crypt[0]
        self.current_created_at = self.next_created_at
        self.current_expires_at = self.next_expires_at
        self.current_signed_at = self.next_signed_at
        self.current_submitted_at = self.next_submitted_at
        self.current_fqdn = self.next_fqdn
        self.current_is_valid = self.next_is_valid
        self.clean_section("next")
        self.set_crypto()

    def clean_section(self, label):
        """
        Used wipe out either "next", or "current". This allows to make room or something new.

        :param label:
        :return:
        """
        if label == "next":
            self.next_csr = None
            self.next_csr_generation_error_count = 0

        setattr(self, f"{label}_status", None)
        setattr(self, f"{label}_status_msg", None)
        setattr(self, f"{label}_cert", None)
        setattr(self, f"{label}_chain", None)
        setattr(self, f"{label}_key", None)
        setattr(self, f"{label}_created_at", None)
        setattr(self, f"{label}_expires_at", None)
        setattr(self, f"{label}_signed_at", None)
        setattr(self, f"{label}_submitted_at", None)
        setattr(self, f"{label}_fqdn", None)
        setattr(self, f"{label}_is_valid", None)

        # now the the variables are deleted, lets delete the matching files
        for file_to_delete in glob.glob("%s/etc/certs/%s.%s.*" % (self.working_dir, self.sslname, label)):
            logger.debug("Removing ssl file file: {file}", file=file_to_delete)
            os.remove(file_to_delete)

        self.dirty = True

    def check_if_fqdn_updated(self):
        """
        Checks if the system's fqdn dns name changed and doesn't match the requested
        certificate, then we will mark any requested certs as being bad/empty.
        :return: 
        """
        logger.warn("check_if_fqdn_updated")
        system_fqdn = self._Parent.local_gateway.dns_name
        print(f"system_fqdn: {system_fqdn}")
        print(f"current_fqdn: {self.current_fqdn}")
        print(f"next_fqdn: {self.next_fqdn}")
        if system_fqdn != self.current_fqdn and self.current_fqdn is not None:
            logger.warn("System FQDN doesn't match current requested cert for: {sslname}", sslname=self.sslname)
            self.current_is_valid = None
            self.dirty = True

        if system_fqdn != self.next_fqdn and self.next_fqdn is not None:
            logger.warn("System FQDN doesn't match next requested cert for: {sslname}", sslname=self.sslname)
            self.clean_section("next")

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
            labels = ["current", "next"]
        else:
            labels = [label]

        for label in labels:
            if getattr(self, f"{label}_expires_at") is not None and \
                    int(getattr(self, f"{label}_expires_at")) > int(time()) and \
                    getattr(self, f"{label}_signed_at") is not None and \
                    getattr(self, f"{label}_key") is not None and \
                    getattr(self, f"{label}_cert") is not None and \
                    getattr(self, f"{label}_chain") is not None:
                setattr(self, f"{label}_is_valid", True)
            else:
                setattr(self, f"{label}_is_valid", False)
                if label != "next":
                    if getattr(self, f"{label}_key") is None or \
                            getattr(self, f"{label}_cert") is None or \
                            getattr(self, f"{label}_chain") is None or \
                            getattr(self, f"{label}_created_at") is None:
                        self.clean_section(label)
                else:
                    if getattr(self, f"{label}_key") is None or \
                            getattr(self, f"{label}_csr") is None or \
                            getattr(self, f"{label}_created_at") is None:
                        self.clean_section(label)

        self.dirty = True

    def set_crypto(self):
        if self.current_cert is not None:
            self.current_cert_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self.current_cert),
            if isinstance(self.current_cert_crypt, tuple):
                self.current_cert_crypt = self.current_cert_crypt[0]
        else:
            self.current_cert_crypt = None

        if self.current_chain is not None:
            self.current_chain_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self.current_chain),
            if isinstance(self.current_chain_crypt, tuple):
                self.current_chain_crypt = self.current_chain_crypt[0]
        else:
            self.current_chain_crypt = None

        if self.current_key is not None:
            self.current_key_crypt = crypto.load_privatekey(crypto.FILETYPE_PEM, self.current_key),
            if isinstance(self.current_key_crypt, tuple):
                self.current_key_crypt = self.current_key_crypt[0]
        else:
            self.current_key_crypt = None

    @inlineCallbacks
    def sync_from_filesystem(self):
        """
        Reads meta data and items from the file system. This allows us to restore data incase the database
        goes south. This is important since only the gateway has the private key and cannot be recovered.

        :return:
        """
        logger.debug("Inspecting file system for certs, and loading them for: {name}", name=self.sslname)

        for label in ["current", "next"]:
            setattr(self, f"{label}_is_valid", None)

            if os.path.exists(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.meta"):
                logger.debug("SSL Meta found for: {label} - {sslname}", label=label, sslname=self.sslname)
                file_content = yield read_file(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.meta")
                meta = json.loads(file_content)
                csr_read = False
                if label == "next":
                    logger.debug("Looking for 'next' information.")
                    if os.path.exists(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.csr.pem"):
                        if getattr(self, f"{label}_csr") is None:
                            csr = yield read_file(
                                f"{self.working_dir}/etc/certs/{self.sslname}.{label}.csr.pem",
                                True,
                            )
                            if sha256(str(csr).encode("utf-8")).hexdigest() == meta["csr"]:
                                csr_read = True
                            else:
                                logger.warn("Appears that the file system has bad meta signatures (csr). Purging.")
                                for file_to_delete in glob.glob(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.*"):
                                    logger.warn("Removing bad file: {file}", file=file_to_delete)
                                    os.remove(file_to_delete)
                                continue

                cert_read = False
                if getattr(self, f"{label}_cert") is None:
                    if os.path.exists(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.cert.pem"):
                        # print("setting cert!!!")
                        cert = yield read_file(
                            f"{self.working_dir}/etc/certs/{self.sslname}.{label}.cert.pem",
                            True
                        )
                        cert_read = True
                        # print("testing with this cert: %s" % cert)
                        if sha256(str(cert).encode("utf-8")).hexdigest() != meta["cert"]:
                            # print("%s != %s" % (sha256(str(cert).encode("utf-8")).hexdigest(), meta["cert"]))
                            logger.warn("Appears that the file system has bad meta signatures (cert). Purging.")
                            for file_to_delete in glob.glob(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.*"):
                                logger.warn("Removing bad file: {file}", file=file_to_delete)
                                os.remove(file_to_delete)
                            continue

                chain_read = False
                if getattr(self, f"{label}_chain") is None:
                    if os.path.exists(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.chain.pem"):
                        # print("setting chain!!!")
                        chain = yield read_file(
                            f"{self.working_dir}/etc/certs/{self.sslname}.{label}.chain.pem",
                            True
                        )
                        chain_read = True
                        if sha256(str(chain).encode("utf-8")).hexdigest() != meta["chain"]:
                            logger.warn("Appears that the file system has bad meta signatures (chain). Purging.")
                            for file_to_delete in glob.glob(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.*"):
                                logger.warn("Removing bad file: {file}", file=file_to_delete)
                                os.remove(file_to_delete)
                            continue

                key_read = False
                if getattr(self, f"{label}_key") is None:
                    if os.path.exists(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.key.pem"):
                        key = yield read_file(
                            f"{self.working_dir}/etc/certs/{self.sslname}.{label}.key.pem",
                            True
                        )
                        key_read = True
                        if sha256(str(key).encode("utf-8")).hexdigest() != meta["key"]:
                            logger.warn("Appears that the file system has bad meta signatures (key). Purging.")
                            for file_to_delete in glob.glob(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.*"):
                                logger.warn("Removing bad file: {file}", file=file_to_delete)
                                os.remove(file_to_delete)
                            continue

                logger.debug("Reading meta file for cert: {label}", label=label)

                def return_int(the_input):
                    try:
                        return int(the_input)
                    except Exception as e:
                        return the_input

                if csr_read:
                    setattr(self, f"{label}_csr", csr)
                if cert_read:
                    setattr(self, f"{label}_cert", cert)
                if chain_read:
                    setattr(self, f"{label}_chain", chain)
                if key_read:
                    setattr(self, f"{label}_key", key)
                setattr(self, f"{label}_status", return_int(meta["status"]))
                setattr(self, f"{label}_status_msg", return_int(meta["status_msg"]))
                setattr(self, f"{label}_expires_at", return_int(meta["expires_at"]))
                setattr(self, f"{label}_created_at", return_int(meta["created_at"]))
                setattr(self, f"{label}_signed_at", return_int(meta["signed_at"]))
                setattr(self, f"{label}_submitted_at", return_int(meta["submitted_at"]))
                setattr(self, f"{label}_fqdn", return_int(meta["fqdn"]))

                self.check_is_valid(label)
            else:
                setattr(self, f"{label}_is_valid", False)
        self.set_crypto()

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
        for label in ["current", "next"]:

            meta = {
                "status": getattr(self, f"{label}_status"),
                "status_msg": getattr(self, f"{label}_status_msg"),
                "created_at": getattr(self, f"{label}_created_at"),
                "expires_at": getattr(self, f"{label}_expires_at"),
                "signed_at": getattr(self, f"{label}_signed_at"),
                "submitted_at": getattr(self, f"{label}_submitted_at"),
                "fqdn": getattr(self, f"{label}_fqdn"),
                "key_type": self.key_type,
                "key_size": self.key_size,
            }

            if getattr(self, f"{label}_cert") is None:
                meta["cert"] = None
                file = f"{self.working_dir}/etc/certs/{self.sslname}.{label}.cert.pem"
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta["cert"] = sha256(str(getattr(self, f"{label}_cert")).encode("utf-8")).hexdigest()
                yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.cert.pem",
                                getattr(self, f"{label}_cert"))

            if getattr(self, f"{label}_chain") is None:
                meta["chain"] = None
                file = f"{self.working_dir}/etc/certs/{self.sslname}.{label}.chain.pem"
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta["chain"] = sha256(str(getattr(self, f"{label}_chain")).encode("utf-8")).hexdigest()
                yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.chain.pem",
                                getattr(self, f"{label}_chain"))

            if getattr(self, f"{label}_key") is None:
                meta["key"] = None
                file = f"{self.working_dir}/etc/certs/{self.sslname}.{label}.key.pem"
                if os.path.exists(file):
                    os.remove(file)
            else:
                meta["key"] = sha256(str(getattr(self, f"{label}_key")).encode("utf-8")).hexdigest()
                yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.key.pem",
                                getattr(self, f"{label}_key"))

            if label == "next":
                if getattr(self, f"{label}_csr") is None:
                    meta["csr"] = None
                    file = f"{self.working_dir}/etc/certs/{self.sslname}.{label}.csr.pem"
                    if os.path.exists(file):
                        os.remove(file)
                else:
                    meta["csr"] = sha256(str(getattr(self, f"{label}_csr")).encode("utf-8")).hexdigest()
                    yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.csr.pem",
                                    getattr(self, f"{label}_csr"))

            yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.{label}.meta",
                            json.dumps(meta, indent=4))

            yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.meta",
                            json.dumps({
                                "sans": self.sans,
                                "cn": self.cn,
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
            self.clean_section("next")
        else:
            self.check_is_valid("next")

        if self.next_is_valid is not None:
            if submit is True:
                if self.next_csr_generation_in_progress is True:
                    self.next_csr_submit_after_generation = True
                else:
                    self.submit_csr()
            else:
                logger.info("Was asked to generate CSR, but we don't need it for: {sslname}", sslname=self.sslname)
            return

        logger.debug("generate_new_csr: {sslname}.  Submit: {submit}", sslname=self.sslname, submit=submit)
        # End local functions.
        request = {
            "sslname": self.sslname,
            "key_size": self.key_size,
            "key_type": self.key_type,
            "cn": self.cn,
            "sans": self.sans
        }
        logger.debug("request_new_csr: request: {request}", request=request)

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
            self.next_fqdn = self._Parent.local_gateway.dns_name
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
        self.next_status = "new"
        self.next_status_msg = "Created but unsent for signing. Will send when previous cert nears expiration."
        self.next_csr = results["csr"]
        self.next_csr_hash = results["csr_hash"]
        self.next_key = results["key"]
        # print("request_new_csr csr: %s " % self.next_csr)
        yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.next.csr.pem", self.next_csr)
        yield save_file(f"{self.working_dir}/etc/certs/{self.sslname}.next.key.pem", self.next_key)
        self.next_created_at = int(time())
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
        if self._Parent._Loader.operating_mode != "run":
            return

        missing = []
        if self.next_csr is None:
            missing.append("CSR")
        if self.next_key is None:
            missing.append("KEY")

        # print("sslcert:submit_csr - csr_text: %s" % self.next_csr)
        if len(missing) == 0:
            request = self._Parent.send_csr_request(self.next_csr, self.sslname)
            logger.debug("Sending CSR Request from instance. Correlation id: {correlation_id}",
                         correlation_id=request["properties"]["correlation_id"])
            self.next_submitted_at = int(time())
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
        logger.debug("TLS cert body: {body}", body=body)
        if "csr_hash" not in body:
            logger.warn("'csr_hash' is missing from incoming amqp TLS key.")
            return
        csr_hash = body["csr_hash"]
        if csr_hash != self.next_csr_hash:
            logger.warn("Incoming TLS (SSL) key hash is mismatched. Discarding. "
                        "Have: {next_csr_hash}, received: {csr_hash}",
                        next_csr_hash=self.next_csr_hash, csr_hash=csr_hash)
            return

        self.next_status = body["status"]
        self.next_status_msg = body["status_msg"]
        if body["status"] == "signed":
            self.next_chain = body["chain_text"]
            self.next_cert = body["cert_signed"]
            self.next_signed_at = body["cert_signed_at"]
            self.next_expires_at = body["cert_expires_at"]
            self.next_is_valid = True
            self.dirty = True
            yield self.check_if_rotate_needed()  # this will rotate next into current

        method = None
        if self.current_is_valid is not True:
            logger.warn("Received a new cert and rotated, but the new cert doesn't seem to be valid.")
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
                logger.warn("Invalid update_callback information provided: {e}", e=e)

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
            logger.debug("Returning a signed cert to caller for cert: {sslname}", sslname=self.sslname)
            return {
                "key": self.current_key,
                "key_crypt": self.current_key_crypt,
                "cert": self.current_cert,
                "cert_crypt": self.current_cert_crypt,
                "chain": self.current_chain,
                "chain_crypt": [self.current_chain_crypt],
                "expires_at": self.current_expires_at,
                "created_at": self.current_created_at,
                "signed_at": self.current_signed_at,
                "self_signed": False,
                "cert_file": self._Parent._Atoms.get("working_dir") + f"/etc/certs/{self.sslname}.current.cert.pem",
                "key_file": self._Parent._Atoms.get("working_dir") + f"/etc/certs/{self.sslname}.current.key.pem",
                "chain_file": self._Parent._Atoms.get("working_dir") + f"/etc/certs/{self.sslname}.current.chain.pem",
            }
        else:
            logger.debug("Sending SELF SIGNED cert details for {sslname}", sslname=self.sslname)
            if self._Parent.self_signed_created_at is None:
                raise YomboWarning("Self signed cert not avail. Try restarting gateway.")
            else:
                return self._Parent.get_self_signed()

    def asdict(self):
        """
        Returns a dictionary of the current attributes. This should only be used internally.

        :return:
        """
        return {
            "sslname": self.sslname,
            "cn": self.cn,
            "sans": self.sans,
            "update_callback_type": self.update_callback_type,
            "update_callback_component": self.update_callback_component,
            "update_callback_function": self.update_callback_function,
            "key_size": int(self.key_size),
            "key_type": self.key_type,
            "current_status": self.current_status,
            "current_status_msg": self.current_status_msg,
            "current_csr_hash": self.current_csr_hash,
            "current_cert": self.current_cert,
            "current_chain": self.current_chain,
            "current_key": self.current_key,
            "current_created_at": None if self.current_created_at is None else int(self.current_created_at),
            "current_expires_at": None if self.current_expires_at is None else int(self.current_expires_at),
            "current_signed_at": self.current_signed_at,
            "current_submitted_at": self.current_submitted_at,
            "current_fqdn": self.current_fqdn,
            "current_is_valid": self.current_is_valid,
            "next_status": self.next_status,
            "next_status_msg": self.next_status_msg,
            "next_csr": self.next_csr,
            "next_csr_hash": self.next_csr_hash,
            "next_cert": self.next_cert,
            "next_chain": self.next_chain,
            "next_key": self.next_key,
            "next_created_at": None if self.next_created_at is None else int(self.next_created_at),
            "next_expires_at": None if self.next_expires_at is None else int(self.next_expires_at),
            "next_signed_at": self.next_signed_at,
            "next_submitted_at": self.next_submitted_at,
            "next_fqdn": self.next_fqdn,
            "next_is_valid": self.next_is_valid,
        }
