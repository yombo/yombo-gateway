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

:copyright: Copyright 2017-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/sslcerts/sslcert.html>`_
"""
import glob
import json
from OpenSSL import crypto
import os
import os.path
from time import time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Union

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
from yombo.utils import bytes_to_unicode, encode_binary
from yombo.utils.caller import caller_string
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


class SSLCert(Entity, ChildStorageAccessorsMixin):
    """
    A class representing a single cert.
    """
    _Entity_type: ClassVar[str] = "SSLCert"
    _Entity_label_attribute: ClassVar[str] = "sslname"

    _additional_to_dict_fields: ClassVar[list] = ["sslname", "cn", "sans", "update_callback_type",
                                                  "update_callback_component", "update_callback_function", "key_size",
                                                  "key_type", "current_status", "current_status_msg",
                                                  "current_csr_hash", "current_cert", "current_chain", "current_chain",
                                                  "current_created_at", "current_expires_at", "current_signed_at",
                                                  "current_submitted_at", "current_fqdn", "current_is_valid",
                                                  "next_status", "next_status_msg", "next_cs_textr", "next_csr_hash",
                                                  "next_cert_text", "next_chain_text", "next_key_text",
                                                  "next_created_at", "next_expires_at", "next_signed_at",
                                                  "next_submitted_at", "next_fqdn", "next_is_valid"]

    def __str__(self):
        """
        Returns the name of the library.

        :return: Name of the library
        :rtype: string
        """
        return f"Yombo SSLCert: {self.sslname} with status: {self.current_status}"

    def __init__(self, parent, incoming: dict, load_source: str):
        """
        Setup basic properties and populate values from the "incoming" incoming argument.

        :param incoming: A dictionary of the attributes to setup the class.
        :param load_source: One of: "sql", "incomings", or "sqldicts"
        :ivar sslname: *(string)* - The name of base file. The archive name will be based off this.
        :ivar key_size: *(int)* - Size of the key in bits.
        :ivar key_type: *(string)* - Either rsa or dsa.
        """
        super().__init__(parent)
        self.load_source = load_source

        self.sslname = incoming["sslname"] if "sslname" in incoming else None

        # These are target values. If things change from the current/next, we'll regenerate and resubmit.
        self.cn = incoming["cn"] if "cn" in incoming else None
        self.sans = incoming["sans"] if "sans" in incoming else None
        self.key_size = None
        self.key_type = None

        self.update_callback = None
        self.update_callback_type = None
        self.update_callback_component = None
        self.update_callback_function = None


        self.current_status = None        # new / signed
        self.current_status_msg = None    # new / signed / whatever from yombo servers
        self.current_csr_hash = None      # sha256(compact) hash of csr
        self.current_csr_text = None      # sha256(compact) hash of csr
        self.current_cert_text = None          # The signed cert from Lets Encrypt (or self signed)
        self.current_cert_crypt = None    # A ready to use crypto key
        self.current_chain_text = None         # Additional certs to complete the chain
        self.current_chain_crypt = None   # A ready to use crypto key
        self.current_key_text = None      # The private key - keep this a secret!
        self.current_key_crypt = None     #
        self.current_created_at = None    # WHen the cert was created
        self.current_expires_at = None    # The when signature expires
        self.current_signed_at = None     # When it was signed at
        self.current_submitted_at = None  # When it was sent to Yombo server for signing by Lets Encrypt
        self.current_fqdn = None          # The fqdn of the cert
        self.current_is_valid = None      # If the cert is still valid.
        self.current_csr_generation_error_count = 0
        self.current_cn = None
        self.current_sans = None
        self.current_key_size = None
        self.current_key_type = None

        self.next_status = None
        self.next_status_msg = None
        self.next_csr_hash = None
        self.next_csr_text = None        # cert sign request
        self.next_cert_text = None
        self.next_chain_text = None
        self.next_key_text = None
        self.next_created_at = None
        self.next_expires_at = None
        self.next_signed_at = None
        self.next_submitted_at = None
        self.next_fqdn = None
        self.next_is_valid = None
        self.next_csr_generation_error_count = 0
        self.next_csr_generation_in_progress = False
        self.next_csr_submit_after_generation = False
        self.next_cn = None
        self.next_sans = None
        self.next_key_size = None
        self.next_key_type = None

        self.update(incoming)
        self.sync_to_filesystem_working = False
        if self.load_source != "file":
            self.dirty = False

        self.check_messages_of_the_unknown()

    @inlineCallbacks
    def _start_(self):
        """
        Called by the parent, SSLCerts, to load any data from the filesystem and then validate
        if the cert if valid.

        :return:
        """
        # Attempt to load cert data from disk.
        yield self.sync_from_filesystem()
        # check if we need to generate csr, sign csr, or rotate next with current.
        yield self.check_if_rotate_needed()

    @inlineCallbacks
    def _stop_(self):
        """
        Saves the cert meta data to disk...if it"s dirty.

        :return:
        """
        yield self.sync_to_filesystem()
        self.dirty = False

    def update(self, attributes):
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

        if "current_status" in attributes:
            self.current_status = attributes["current_status"]
        if "current_status_msg" in attributes:
            self.current_status_msg = attributes["current_status_msg"]
        if "current_csr_hash" in attributes:
            self.current_csr_hash = attributes["current_csr_hash"]
        if "current_csr_text" in attributes:
            self.current_csr_text = attributes["current_csr_text"]
        if "current_cert_text" in attributes:
            self.current_cert_text = attributes["current_cert_text"]
        if "current_chain_text" in attributes:
            self.current_chain_text = attributes["current_chain_text"]
        if "current_key_text" in attributes:
            self.current_key_text = attributes["current_key_text"]
        self.set_crypto()

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
        if "current_csr_generation_error_count" in attributes:
            self.current_csr_generation_error_count = attributes["current_csr_generation_error_count"]
        if "current_cn" in attributes:
            self.current_cn = attributes["current_cn"]
        if "current_sans" in attributes:
            self.current_sans = attributes["current_sans"]
        if "current_key_size" in attributes:
            self.current_key_size = attributes["current_key_size"]
        if "current_key_type" in attributes:
            self.current_key_type = attributes["current_key_type"]

        if "next_status" in attributes:
            self.next_status = attributes["next_status"]
        if "next_status_msg" in attributes:
            self.next_status_msg = attributes["next_status_msg"]
        if "next_csr_hash" in attributes:
            self.next_csr_hash = attributes["next_csr_hash"]
        if "next_csr_text" in attributes:
            self.next_csr_text = attributes["next_csr_text"]
        if "next_cert_text" in attributes:
            self.next_cert_text = attributes["next_cert_text"]
        if "next_chain_text" in attributes:
            self.next_chain_text = attributes["next_chain_text"]
        if "next_key_text" in attributes:
            self.current_key_text = attributes["current_key_text"]
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
        if "next_csr_generation_error_count" in attributes:
            self.next_csr_generation_error_count = attributes["next_csr_generation_error_count"]
        if "next_cn" in attributes:
            self.next_cn = attributes["next_cn"]
        if "next_sans" in attributes:
            self.next_sans = attributes["next_sans"]
        if "next_key_size" in attributes:
            self.next_key_size = attributes["next_key_size"]
        if "next_key_type" in attributes:
            self.next_key_type = attributes["next_key_type"]

        # do some back checks.
        if self.next_csr_text is not None and self.next_csr_hash is None:
            self.next_csr_hash = self._Hash.sha224_compact(self.next_csr, encoder="base62")[:20]
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
                self.current_key_text is None or \
                self.current_expires_at is None or \
                int(self.current_expires_at) < int(time() + (86400*30)):
            if self.next_is_valid is True:
                self.make_next_be_current()  # Migrate the next key to the current key.
            else:  # next is not valid
                if self.next_csr_text is not None and self.next_key_text is not None:
                    self.submit_csr()
                else:
                    yield self.request_new_csr(submit=True)
                    new_cert_requested = True

        # Prepare a next cert if it's missing and one hasn't already been requested.
        if self.next_csr_text is None and new_cert_requested is False:
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
        self.current_csr_text = self.next_csr_text
        self.current_cert_text = self.next_cert_text
        self.current_chain_text = self.next_chain_text
        self.current_key_text = self.next_key_text
        self.current_key_crypt = None,
        self.current_cert_crypt = None,
        self.current_chain_crypt = None,
        self.current_created_at = self.next_created_at
        self.current_expires_at = self.next_expires_at
        self.current_signed_at = self.next_signed_at
        self.current_submitted_at = self.next_submitted_at
        self.current_fqdn = self.next_fqdn
        self.current_is_valid = self.next_is_valid
        self.current_csr_generation_error_count = self.next_csr_generation_error_count
        self.current_cn = self.next_cn
        self.current_sans = self.next_sans
        self.current_key_size = self.next_key_size
        self.current_key_type = self.next_key_type

        self.clean_section("next")
        self.set_crypto()

    @inlineCallbacks
    def clean_section(self, version):
        """
        Used wipe out either "next", or "current". This allows to make room or something new.

        :param label:
        :return:
        """
        setattr(self, f"{version}_status", None)
        setattr(self, f"{version}_status_msg", None)
        setattr(self, f"{version}_csr_generation_error_count", 0)
        setattr(self, f"{version}_csr_hash", None)
        setattr(self, f"{version}_csr_text", None)
        setattr(self, f"{version}_cert_text", None)
        setattr(self, f"{version}_chain_text", None)
        setattr(self, f"{version}_key_text", None)
        setattr(self, f"{version}_key_crypt", None)
        setattr(self, f"{version}_cert_crypt", None)
        setattr(self, f"{version}_chain_crypt", None)
        setattr(self, f"{version}_created_at", None)
        setattr(self, f"{version}_expires_at", None)
        setattr(self, f"{version}_signed_at", None)
        setattr(self, f"{version}_submitted_at", None)
        setattr(self, f"{version}_fqdn", None)
        setattr(self, f"{version}_is_valid", None)
        setattr(self, f"{version}_cn", None)
        setattr(self, f"{version}_sans", None)
        setattr(self, f"{version}_key_size", None)
        setattr(self, f"{version}_key_type", None)

        if version == "next":
            self.next_csr_generation_in_progress = False
            self.next_csr_submit_after_generation = False

        # now that the variables are deleted, lets delete the matching files
        yield self.purge_cert_files(version)
        self.dirty = True

    def check_if_fqdn_updated(self):
        """
        Checks if the system's fqdn dns name changed and doesn't match the requested
        certificate, then we will mark any requested certs as being bad/empty.
        :return:
        """
        logger.warn("check_if_fqdn_updated")
        system_fqdn = self._Parent.local_gateway.dns_name
        # print(f"system_fqdn: {system_fqdn}")
        # print(f"current_fqdn: {self.current_fqdn}")
        # print(f"next_fqdn: {self.next_fqdn}")
        if system_fqdn != self.current_fqdn and self.current_fqdn is not None:
            logger.warn("System FQDN doesn't match current requested cert for: {sslname}", sslname=self.sslname)
            self.clean_section("current")

        if system_fqdn != self.next_fqdn and self.next_fqdn is not None:
            logger.warn("System FQDN doesn't match next requested cert for: {sslname}", sslname=self.sslname)
            # print("calling clean section check_if_fqdn_updated")
            self.clean_section("next")

    def check_messages_of_the_unknown(self):
        if self.sslname in self._Parent.received_message_for_unknown:
            logger.warn("We have messages for us. TODO: Implement this.")

    def check_is_valid(self, version: Optional[str] = None):
        """
        Used to validate if a give cert (next or current) is valid. If no version
        is provided, then both will checked.

        :param version:
        :return:
        """
        if version is None:
            versions = ["current", "next"]
        else:
            versions = [version]

        for version in versions:
            if getattr(self, f"{version}_expires_at") is not None and \
                    int(getattr(self, f"{version}_expires_at")) > int(time()) and \
                    getattr(self, f"{version}_signed_at") is not None and \
                    getattr(self, f"{version}_key_text") is not None and \
                    getattr(self, f"{version}_cert_text") is not None and \
                    getattr(self, f"{version}_chain_text") is not None:
                setattr(self, f"{version}_is_valid", True)
            else:
                setattr(self, f"{version}_is_valid", False)
                if version == "current":
                    if getattr(self, f"{version}_key_text") is None or \
                            getattr(self, f"{version}_cert_text") is None or \
                            getattr(self, f"{version}_chain_text") is None or \
                            getattr(self, f"{version}_created_at") is None:
                        self.clean_section(version)
                else:
                    if getattr(self, f"{version}_key_text") is None or \
                            getattr(self, f"{version}_csr_text") is None or \
                            getattr(self, f"{version}_created_at") is None:
                        self.clean_section(version)
        self.dirty = True

    def set_crypto(self):
        if self.current_cert_text is not None:
            self.current_cert_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self.current_cert_text),
            if isinstance(self.current_cert_crypt, tuple):
                self.current_cert_crypt = self.current_cert_crypt[0]

        if self.current_chain_text is not None:
            self.current_chain_crypt = crypto.load_certificate(crypto.FILETYPE_PEM, self.current_chain_text),
            if isinstance(self.current_chain_crypt, tuple):
                self.current_chain_crypt = self.current_chain_crypt[0]

        if self.current_key_text is not None:
            self.current_key_crypt = crypto.load_privatekey(crypto.FILETYPE_PEM, self.current_key_text),
            if isinstance(self.current_key_crypt, tuple):
                self.current_key_crypt = self.current_key_crypt[0]

    @inlineCallbacks
    def purge_cert_files(self, file_version: str):
        """
        Delete cert files for either current or next.

        :param file_version: Either current or next.
        :return:
        """
        for file_to_delete in glob.glob(f"{self._working_dir}/etc/certs/{self.sslname}.{file_version}.*"):
            logger.warn("Removing bad file: {file}", file=file_to_delete)
            yield self._Files.delete(file_to_delete)

    @inlineCallbacks
    def sync_from_filesystem(self):
        """
        Reads meta data and various cert items from the file system.

        :return:
        """
        logger.debug("Inspecting file system for certs, and loading them for: {name}", name=self.sslname)

        meta_exists = yield self._Files.exists(f"{self._working_dir}/etc/certs/{self.sslname}.meta")
        if meta_exists is False:  # No files to read. Meta data file is required!
            return

        master_meta = yield self._Files.read(f"{self._working_dir}/etc/certs/{self.sslname}.meta", unpickle="json")

        def return_int(the_input):
            try:
                return int(the_input)
            except Exception as e:
                return the_input

        for version in ["current", "next"]:
            try:
                setattr(self, f"{version}_is_valid", None)
                setattr(self, f"{version}_csr_hash", master_meta.get(f"{version}_csr_hash", None))
                setattr(self, f"{version}_csr_text", master_meta.get(f"{version}_csr_text", None))
                setattr(self, f"{version}_cert_text", master_meta.get(f"{version}_cert_text", None))
                setattr(self, f"{version}_chain_text", master_meta.get(f"{version}_chain_text", None))
                setattr(self, f"{version}_key_text", master_meta.get(f"{version}_key_text", None))
                setattr(self, f"{version}_status", master_meta[f"{version}_status"])
                setattr(self, f"{version}_status_msg", master_meta[f"{version}_status_msg"])
                setattr(self, f"{version}_expires_at", return_int(master_meta[f"{version}_expires_at"]))
                setattr(self, f"{version}_created_at", return_int(master_meta[f"{version}_created_at"]))
                setattr(self, f"{version}_signed_at", return_int(master_meta[f"{version}_signed_at"]))
                setattr(self, f"{version}_submitted_at", return_int(master_meta[f"{version}_submitted_at"]))
                setattr(self, f"{version}_fqdn", master_meta[f"{version}_fqdn"])
                setattr(self, f"{version}_is_valid", master_meta[f"{version}_is_valid"])
                setattr(self, f"{version}_cn", master_meta[f"{version}_cn"])
                setattr(self, f"{version}_sans", master_meta[f"{version}_sans"])
                setattr(self, f"{version}_fqdn", master_meta[f"{version}_fqdn"])
                setattr(self, f"{version}_key_size", master_meta[f"{version}_key_size"])
                setattr(self, f"{version}_key_type", master_meta[f"{version}_key_type"])
                logger.warn("Done validating: {name} - {version}", name=self.sslname, version=version)

            except Exception as e:
                logger.warn("Error loading cert from meta file: {e}", e=e)
                logger.info("-----------------==(Traceback)==-----------------------")
                logger.info("{trace}", trace=traceback.format_exc())
                logger.info("--------------------------------------------------------")
                self.purge_cert_files(version)
                yield self.clean_section(version)
                continue
        else:
            setattr(self, f"{version}_is_valid", False)

        self.check_is_valid()

        if getattr(self, f"{version}_is_valid") is True:
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
        master_meta = {
            "cn": self.cn,
            "sans": self.sans,
            "key_size": self.key_size,
            "key_type": self.key_type,
            "sslname": self.sslname,
        }

        self.check_is_valid()
        for version in ["current", "next"]:
            yield self.purge_cert_files(version)
            master_meta.update({
                f"{version}_csr_hash": None,
                f"{version}_csr_path": f"{self._working_dir}/etc/certs/{self.sslname}.{version}.csr.pem",
                f"{version}_cert_path": f"{self._working_dir}/etc/certs/{self.sslname}.{version}.cert.pem",
                f"{version}_key_path": f"{self._working_dir}/etc/certs/{self.sslname}.{version}.key.pem",
                f"{version}_chain_path": f"{self._working_dir}/etc/certs/{self.sslname}.{version}.chain.pem",
                f"{version}_csr_text": getattr(self, f"{version}_csr_text"),
                f"{version}_cert_text": getattr(self, f"{version}_cert_text"),
                f"{version}_chain_text": getattr(self, f"{version}_chain_text"),
                f"{version}_key_text": getattr(self, f"{version}_key_text"),

                f"{version}_status": getattr(self, f"{version}_status"),
                f"{version}_status_msg": getattr(self, f"{version}_status_msg"),
                f"{version}_created_at": getattr(self, f"{version}_created_at"),
                f"{version}_expires_at": getattr(self, f"{version}_expires_at"),
                f"{version}_signed_at": getattr(self, f"{version}_signed_at"),
                f"{version}_submitted_at": getattr(self, f"{version}_submitted_at"),
                f"{version}_fqdn": getattr(self, f"{version}_fqdn"),
                f"{version}_is_valid": getattr(self, f"{version}_is_valid"),
                f"{version}_cn": getattr(self, f"{version}_cn"),
                f"{version}_sans": getattr(self, f"{version}_sans"),
                f"{version}_key_type": self.key_type,
                f"{version}_key_size": self.key_size,
            })

            if getattr(self, f"{version}_cert_text") is not None:
                yield self._Files.save(master_meta[f"{version}_cert_path"], getattr(self, f"{version}_cert_text"))

            if getattr(self, f"{version}_chain_text") is not None:
                yield self._Files.save(master_meta[f"{version}_chain_path"], getattr(self, f"{version}_chain_text"))

            if getattr(self, f"{version}_key_text") is not None:
                yield self._Files.save(master_meta[f"{version}_key_path"], getattr(self, f"{version}_key_text"))

            if getattr(self, f"{version}_csr_text") is not None:
                master_meta[f"{version}_csr_hash"] = self._Hash.sha224_compact(getattr(self, f"{version}_csr_text"),
                                                                               encoder="base62")[:20]
                yield self._Files.save(master_meta[f"{version}_csr_path"], getattr(self, f"{version}_csr_text"))

        yield self._Files.save(f"{self._working_dir}/etc/certs/{self.sslname}.meta",
                               json.dumps(master_meta, indent=4))

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
            yield self.clean_section("next")
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
        self.next_csr_text = results["csr_text"]
        self.next_csr_hash = results["csr_hash"]
        self.next_key_text = results["key_text"]
        # print("request_new_csr csr: %s " % self.next_csr_text)
        # yield self._Files.save(f"{self._working_dir}/etc/certs/{self.sslname}.next.csr.pem", self.next_csr_text)
        # yield self._Files.save(f"{self._working_dir}/etc/certs/{self.sslname}.next.key.pem", self.next_key_text)
        self.next_created_at = int(time())
        self.dirty = True
        yield self.sync_to_filesystem()
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
        if self.next_csr_text is None:
            missing.append("CSR")
        if self.next_key_text is None:
            missing.append("KEY")

        # print("sslcert:submit_csr - csr_text: %s" % self.next_csr_text)
        if len(missing) == 0:
            request = self._Parent.send_csr_request(self.next_csr_text, self.sslname)
            logger.debug("Sending CSR Request from instance. Correlation id: {correlation_id}",
                         correlation_id=request["properties"]["correlation_id"])
            self.next_submitted_at = int(time())
        else:
            logger.warn("Requested to submit CSR, but these are missing: {missing}", missing=".".join(missing))
            raise YomboWarning("Unable to submit CSR.")

        self.dirty = True

    @inlineCallbacks
    def amqp_incoming_response_to_csr_request(self, message=None, properties=None, correlation_info=None, **kwargs):
        """
        A response from a CSR request has been received. Lets process it.

        :param properties: Properties of the AQMP message.
        :param body: The message itself.
        :param correlation: Any correlation data regarding the AQMP message. We can check for timing, etc.
        :return:
        """
        logger.info("Received a signed SSL/TLS certificate for: {sslname}", sslname=self.sslname)
        print("sslcert: processing 2")

        logger.info("TLS cert body: {message}", message=message)
        print("sslcert: processing 3")

        if "csr_hash" not in message:
            print("sslcert: processing 4")

            logger.warn("'csr_hash' is missing from incoming amqp TLS key.")
            print("sslcert: processing 5")

            return
        print("sslcert: processing 10")

        csr_hash = message["csr_hash"]
        print("sslcert: processing 10")
        if csr_hash != self.next_csr_hash:
            print("sslcert: processing 10")
            logger.warn("Incoming TLS (SSL) key hash is mismatched. Discarding. "
                        "Have: {next_csr_hash}, received: {csr_hash}",
                        next_csr_hash=self.next_csr_hash, csr_hash=csr_hash)
            return
        print("sslcert: processing 20")

        self.next_status = message["status"]
        self.next_status_msg = message["status_msg"]
        if message["status"] == "signed":
            self.next_chain_text = message["chain_text"]
            self.next_cert_text = message["cert_text"]
            self.next_signed_at = message["cert_signed_at"]
            self.next_expires_at = message["cert_expires_at"]
            self.next_is_valid = True
            self.dirty = True
            yield self.check_if_rotate_needed()  # this will rotate next into current

        print("sslcert: processing 30")
        method = None
        if self.current_is_valid is not True:
            logger.warn("Received a new cert and rotated, but the new cert doesn't seem to be valid.")
            return
        print("sslcert: processing 40")

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
        print("sslcert: processing 50")

        logger.info("Method to notify ssl requester that there's a new cert: {method}", method=method)

        if method is not None and isinstance(method, collections.Callable):
            logger.info("About to tell the SSL/TLS cert requester know we have a new cert, from: {sslname}",
                        sslname=self.sslname)

            print("sslcert: processing 60")

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
                "key_text": self.current_key_text,
                "key_crypt": self.current_key_crypt,
                "cert_text": self.current_cert,
                "cert_crypt": self.current_cert_crypt,
                "chain_text": self.current_chain_text,
                "chain_crypt": [self.current_chain_crypt],
                "expires_at": self.current_expires_at,
                "created_at": self.current_created_at,
                "signed_at": self.current_signed_at,
                "self_signed": False,
                "cert_path": self._Parent._Atoms.get("working_dir") + f"/etc/certs/{self.sslname}.current.cert.pem",
                "key_path": self._Parent._Atoms.get("working_dir") + f"/etc/certs/{self.sslname}.current.key.pem",
                "chain_path": self._Parent._Atoms.get("working_dir") + f"/etc/certs/{self.sslname}.current.chain.pem",
            }
        else:
            logger.debug("Sending SELF SIGNED cert details for {sslname}", sslname=self.sslname)
            if self._Parent.self_signed_created_at is None:
                raise YomboWarning("Self signed cert not avail. Try restarting gateway.")
            else:
                return self._Parent.get_self_signed()

    # def asdict(self):
    #     """
    #     Returns a dictionary of the current attributes. This should only be used internally.
    #
    #     :return:
    #     """
    #     return {
    #         "sslname": self.sslname,
    #         "cn": self.cn,
    #         "sans": self.sans,
    #         "update_callback_type": self.update_callback_type,
    #         "update_callback_component": self.update_callback_component,
    #         "update_callback_function": self.update_callback_function,
    #         "key_size": int(self.key_size),
    #         "key_type": self.key_type,
    #         "current_status": self.current_status,
    #         "current_status_msg": self.current_status_msg,
    #         "current_csr_hash": self.current_csr_hash,
    #         "current_cert": self.current_cert,
    #         "current_chain": self.current_chain,
    #         "current_key": self.current_chain,
    #         "current_created_at": None if self.current_created_at is None else int(self.current_created_at),
    #         "current_expires_at": None if self.current_expires_at is None else int(self.current_expires_at),
    #         "current_signed_at": self.current_signed_at,
    #         "current_submitted_at": self.current_submitted_at,
    #         "current_fqdn": self.current_fqdn,
    #         "current_is_valid": self.current_is_valid,
    #         "next_status": self.next_status,
    #         "next_status_msg": self.next_status_msg,
    #         "next_csr": self.next_csr_text,
    #         "next_csr_hash": self.next_csr_hash,
    #         "next_cert": self.next_cert_text,
    #         "next_chain": self.next_chain_text,
    #         "next_key": self.next_key_text,
    #         "next_created_at": None if self.next_created_at is None else int(self.next_created_at),
    #         "next_expires_at": None if self.next_expires_at is None else int(self.next_expires_at),
    #         "next_signed_at": self.next_signed_at,
    #         "next_submitted_at": self.next_submitted_at,
    #         "next_fqdn": self.next_fqdn,
    #         "next_is_valid": self.next_is_valid,
    #     }
    #
