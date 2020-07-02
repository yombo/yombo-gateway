# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `GPG @ Library Documentation <https://yombo.net/docs/libraries/gpg>`_

This library handles encrypting and decrypting content. This library allows data at rest to be encrypted, which
means any passwords or sensitive data will be encrypted before it is saved to disk. This library doesn't
attempt to manage data in memory or saved in a swap file.

The gateway starts up, any variables that are encryptes (such as passwords), we passed to this library for
decryption. A decrypted version of the data is stored in memory. This allows modules to access the data as needed.

It's important to note that any module within the Yombo system will have access to this data, unencumbered.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0 Moved AES encryption to it's own library: :ref:`Encryption <encryption>`

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/gpg/__init__.html>`_
"""
# Import python libraries
import json
import os.path
import re
from time import time
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

import yombo.ext.gnupg as gnupg

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.constants.gpg import *
from yombo.core.exceptions import YomboWarning, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
from yombo.utils import random_string, bytes_to_unicode, unicode_to_bytes, random_int, sleep

from .gpgkey import GPGKey

logger = get_logger("library.gpg")


class GPG(YomboLibrary, ParentStorageAccessorsMixin, LibrarySearchMixin):
    """
    Manage all GPG functions.
    """
    gpg_keys: ClassVar[dict] = {}
    device_commands: ClassVar[dict] = {}  # tracks commands being sent to devices. Also tracks if a command is delayed.
    _startup_queue: ClassVar[dict] = {}  # Any device commands sent before the system is ready will be stored here.
    _generating_key: ClassVar[bool] = False
    _generating_key_deferred: ClassVar = None

    # The remaining attributes are used by various mixins.
    _storage_primary_length: ClassVar[int] = 25
    _storage_attribute_name: ClassVar[str] = "gpg_keys"
    _storage_label_name: ClassVar[str] = "gpg_key"
    _storage_class_reference: ClassVar = GPGKey
    # _storage_schema: ClassVar = AtomSchema()
    _storage_search_fields: ClassVar[List[str]] = [
        "gpgkey_id", "fullname", "email", "endpoint_id", "fingerprint",
    ]
    _storage_attribute_sort_key: ClassVar[str] = "date"
    _storage_attribute_sort_key_order: ClassVar[str] = "desc"

    @property
    def public_key(self):
        return self.gpg_keys[self.myfingerprint.value]["publickey"]

    @public_key.setter
    def public_key(self, val):
        return

    @property
    def gpg_key_id(self):
        return self.myfingerprint.value

    @gpg_key_id.setter
    def gpg_key_id(self, val):
        return

    @property
    def gpg_key(self):
        return self.gpg_keys[self.myfingerprint.value]

    @gpg_key.setter
    def gpg_key(self, val):
        return

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Get the GnuPG subsystem up and loaded.
        """
        aes_key_path = f"{self._working_dir}/etc/gpg/aes.key"
        self.send_my_gpg_key_loop = LoopingCall(self.send_my_gpg_key)
        self.send_my_gpg_key_loop.start(random_int(60 * 60 * 6, .2), now=False)

        self.key_generation_status = None
        self.sks_pools = [  # Send to a few to ensure we get our key seeded
            "pgp.mit.edu",  # as of AUg 2019, SKS key pool was down to 23 members. Need a better host!
        ]
        self.gpg_module = gnupg.GPG(gnupghome=f"{self._working_dir}/etc/gpg")

        self.myfingerprint = self._Configs.get("gpg.fingerprint", None, False, instance=True)
        self.mykey_last_sent_yombo = self._Configs.get("gpg.last_sent_yombo", 0, True, instance=True)
        self.mykey_last_sent_keyserver = self._Configs.get("gpg.last_sent_keyserver", 0, True, instance=True)
        self.mykey_last_received_keyserver = self._Configs.get("gpg.last_received_keyserver", 0, True, instance=True)

        if self._Loader.operating_mode != "run":
            return
        yield self.load_keys()  # Loads keys from the key store.
        yield self.validate_gpg_ready()  # Ensure we have a GPG keypair for use.

        # self.get_root_key()

    def _stop_(self, **kwargs):
        """
        If we are still generating a key, lets wait for it to finish. Return the deferred.
        """
        if self.send_my_gpg_key_loop is not None and self.send_my_gpg_key_loop.running:
            self.send_my_gpg_key_loop.stop()
        if self._generating_key is True:
            self._generating_key_deferred = Deferred
            return self._generating_key_deferred

    @inlineCallbacks
    def validate_gpg_ready(self):
        """
        Validate that the gateway has a GPG key for encrypting data. If not, create one.

        :return:
        """
        if self.myfingerprint.value is None:
            logger.warn("No GPG fingerprint found! Unable to process GPG items.")
            yield self.generate_key()
            return
        fingerprint = self.myfingerprint.value
        if fingerprint not in self.gpg_keys:
            logger.warn("Cannot find my GPG key!")
            yield self.generate_key()
            return
        mykey = self.gpg_keys[fingerprint]
        if mykey.has_private is False:
            logger.warn("I don't have my own private gpg key.")
            yield self.generate_key()
            return
        if mykey.passphrase is None:
            logger.warn("I don't have the passphrase for my own key.")
            yield self.generate_key()
            return
        if self._gateway_id != self.gpg_keys[fingerprint].uid_endpoint_id:
                self.myfingerprint.value = False
                logger.warn("Local gateway_id '{gateway_id}' doesn't match my GPG endpoint id '{endpoint_id}'",
                            gateway_id=self._gateway_id, endpoint_id=self.gpg_keys[fingerprint].uid_endpoint_id)

    @inlineCallbacks
    def load_keys(self):
        """
        Loads keys from the GPG keyring and create gpg key instances. This function can be called multiple
        times to refresh loaded keys.

        :return:
        """
        # a = [{'type': 'pub',
        #       'trust': 'u',
        #       'length': '4096',
        #       'algo': '1',
        #       'keyid': '111761DC577FE6F8',
        #       'date': '1556065469',
        #       'expires': '1713745469',
        #       'dummy': '',
        #       'ownertrust': 'u',
        #       'sig': '',
        #       'cap': 'escaESCA',
        #       'issuer': '',
        #       'flag': '',
        #       'token': '',
        #       'hash': '',
        #       'curve': '',
        #       'compliance': '23',
        #       'updated': '',
        #       'origin': '0',
        #       'uids': ['Yombo Gateway (Created by https://Yombo.net) <N6kyowXmRlgULv0MjZ1A@gw.gpg.yombo.net>'],
        #       'sigs': [('111761DC577FE6F8',
        #                 'Yombo Gateway (Created by https\\x3a//Yombo.net) <N6kyowXmRlgULv0MjZ1A@gw.gpg.yombo.net>',
        #                 '1fx'),
        #                ('111761DC577FE6F8',
        #                          'Yombo Gateway (Created by https\\x3a//Yombo.net) <N6kyowXmRlgULv0MjZ1A@gw.gpg.yombo.net>',
        #                          '13x')
        #                ],
        #       'subkeys': [],
        #       'fingerprint': '8758988A056C0F8C151E83AE111761DC577FE6F8'}]

        self.gpg_keys.clear()
        # Load keys, then load any private keys + key passphrases.
        public_keys = yield self.gpg_module.list_keys()
        private_keys = yield self.gpg_module.list_keys(secret=True)
        logger.debug("gpg_public_keys: {gpg_keys}", gpg_keys=public_keys)

        keys = {}
        for key in public_keys:
            if int(key["length"]) < 2048:
                logger.error("Not adding key ({fingerprint}) due to length being less then 2048 (it's {length}). Key is not safe.",
                             fingerprint=key["fingerprint"],
                             length=key["length"])
                logger.warn("Additional key details: {uids}",
                            uids=json.dumps(key["uids"])
                            )
                continue
            key["has_private"] = False
            key["passphrase"] = None
            key["passphrase"] = None
            key["uid_endpoint_id"] = None
            key["uid_endpoint_type"] = None
            key["publickey"] = self.gpg_module.export_keys(key["fingerprint"])

            uids = []
            for uid in key["uids"]:
                # split the string by ( or )
                uid_list = re.split(r"\(|\)", uid)
                # strip whitespaces and replace < or > by empty space ""
                uid_list = list(map(lambda x: re.sub(r"<|>", "", x.strip()), uid_list))

                uid_results = {
                    "name": uid_list[0],
                    "comment": uid_list[1],
                    "email": uid_list[2],
                }

                email_parts = uid_results["email"].split("@")
                if len(email_parts) > 2:
                    logger.warn("Skipping GPG key due to invalid UID: {uid}  Fingerprint: {fingerprint}",
                                uid=uid,
                                fingerprint=key["fingerprint"])
                    continue
                if email_parts[1] == "gw.gpg.yombo.net":
                    endpoint_type = "gw"
                elif email_parts[1] == "root.gpg.yombo.net":
                    endpoint_type = "root"
                elif email_parts[1] == "issuing.gpg.yombo.net":
                    endpoint_type = "root"
                elif email_parts[1] == "server.gpg.yombo.net":
                    endpoint_type = "server"
                else:
                    endpoint_type = None
                endpoint_id = email_parts[0]

                if endpoint_type is not None and key["uid_endpoint_type"] is None:
                    key["uid_endpoint_type"] = endpoint_type
                    key["uid_endpoint_id"] = endpoint_id

                uids.append({
                    "name": uid_list[0],
                    "comment": uid_list[1],
                    "email": uid_list[2],
                    "endpoint_id": endpoint_id,
                    "endpoint_type": endpoint_type,
                    "original": uid
                })
            key["uids"] = uids
            keys[key["fingerprint"]] = key

        for key in private_keys:
            if key["fingerprint"] in keys:
                try:
                    passphrase = yield self.load_pass_phrase(key["fingerprint"])
                except IOError:
                    continue
                keys[key["fingerprint"]]["has_private"] = True
                keys[key["fingerprint"]]["passphrase"] = passphrase

        for fingerprint, key in keys.items():
            self.gpg_keys[fingerprint] = GPGKey(self, key)

        logger.debug("gpg_public_keys load done: {gpg_keys}", gpg_keys=self.gpg_keys)

    @inlineCallbacks
    def load_pass_phrase(self, fingerprint):
        secret_file = f"{self._working_dir}/etc/gpg/{fingerprint}.pass"
        if os.path.exists(secret_file):
            phrase = yield self._Files.read(secret_file)
            passphrase = bytes_to_unicode(phrase)
            return passphrase
        return IOError(f"Unable to read gpg file for fingerprint: {fingerprint}")

    @inlineCallbacks
    def set_key_trust(self, fingerprint: str, trust_level: int):
        """
        Sets the trust of a key. The trust level should be one of:
        0 - No trust level.
        1 - Never trust this key
        2 - Marginally trusted
        3 - Fully trusted
        4 - Ultimately trusted (only used on your own key!)

        :param fingerprint: The fingerprint to edit the trust level for.
        :param trust_level: A trust level, 0 thru 4.
        """
        if trust_level not in TRUST_LEVELS:
            raise YomboWarning(f"Unknown trust level: {trust_level}")

        yield self.load_keys()
        if fingerprint in self.gpg_keys:
            if trust_level == TRUST_UNDEFINED and self.gpg_keys[fingerprint]["ownertrust"] == "q":
                return
            elif trust_level == TRUST_NEVER and self.gpg_keys[fingerprint]["ownertrust"] != "n":
                return
            elif trust_level == TRUST_MARGINAL and self.gpg_keys[fingerprint]["ownertrust"] != "m":
                return
            elif trust_level == TRUST_FULLY and self.gpg_keys[fingerprint]["ownertrust"] != "f":
                return
            elif trust_level == TRUST_ULTIMATE and self.gpg_keys[fingerprint]["ownertrust"] != "u":
                return

        @inlineCallbacks
        def do_set_key_trust(gpg, x_finger, x_trust):
            gpg.trust_keys(x_finger, x_trust)
        yield threads.deferToThread(do_set_key_trust, self.gpg_module, fingerprint, trust_level)

        yield self.load_keys()

    @inlineCallbacks
    def send_my_gpg_key(self):
        """
        Periodically is called to send our GPG key to Yombo server and the SKS
        key pool.

        However, we don't always send when requested. We only send to each destination once every
        30 days. We also collect any new signatures once every 10 days.
        :return:
        """
        if self.myfingerprint.value is None:
            logger.warn("Unable to send GPG - no valid local key exists.")
            return

        # print("###################################################2")
        # print(self._Configs.configs)

        if self.mykey_last_sent_yombo.value is None or \
                self.mykey_last_sent_yombo.value < int(time()) - (60*60*24*30):
            yield self.send_my_gpg_key_to_yombo()

        if self.mykey_last_sent_keyserver.value is None or \
                self.mykey_last_sent_keyserver.value < int(time()) - (60*60*24*30):
            yield self.send_my_gpg_key_to_keyserver()
            yield self.get_my_gpg_key_from_keyserver()

        if self.mykey_last_received_keyserver.value is None or \
                self.mykey_last_sent_keyserver.value < int(time()) - (60*60*1):
            yield self.get_my_gpg_key_from_keyserver()

    @inlineCallbacks
    def send_my_gpg_key_to_yombo(self):
        """
        Send my gpg key to the yombo server.

        :return:
        """
        # print("starting: send_my_gpg_key_to_yombo")

        mykey = self.gpg_key
        body = {
            "keyid": mykey.fingerprint,
            "publickey_ascii": mykey.publickey,
        }

        logger.debug("Sending my public GPG key to Yombo.")
        logger.debug("sending gpg information: {body}", body=body)
        gwid = self._gateway_id
        try:
            response = yield self._YomboAPI.request(
                "POST",
                f"/v1/gateways/{gwid}/gpg",
                body=body)

        except YomboWarning as e:
            logger.warn("Unable to send GPG key to Yombo: {e}", e=e)
            return
        self._Configs.set("gpg.last_sent_yombo", int(time()), ref_source=self)

    @inlineCallbacks
    def send_my_gpg_key_to_keyserver(self):
        """
        Send my gpg key to the key server pool.

        :return:
        """
        # print("starting: send_my_gpg_key_to_keyserver")
        logger.info("Sending my public GPG key to key servers.")
        for server in self.sks_pools:
            yield threads.deferToThread(self._send_my_gpg_key_to_keyserver,
                                        server,
                                        self.gpg_key_id)
        self._Configs.set("gpg.last_sent_keyserver", int(time()), ref_source=self)

    def _send_my_gpg_key_to_keyserver(self, server, gpg_key_id):
        print(f"sending key to server: {gpg_key_id} -> {server}")
        # return self.gpg_module.send_keys(f"hkp://{server}", gpg_key_id)

    def get_my_gpg_key_from_keyserver(self):
        """
        Get my gpg key from the keyserver. Sometimes Yombo servers will sign known good GPG keys
        for gateways and other clients to help others know which keys are valid. This function is
        allows those signatures to be updated locally.

        :return:
        """
        # print("starting: get_my_gpg_key_from_keyserver")
        logger.info("Asking GPG key servers for any updates.")
        for fingerprint, key in self.gpg_keys.items:
            yield threads.deferToThread(self._get_my_gpg_key_from_keyserver,
                                        self.sks_pools[0],
                                        fingerprint)
            yield sleep(0.5)
        self._Configs.set("gpg.last_received_keyserver", int(time()), ref_source=self)

    def _get_my_gpg_key_from_keyserver(self, server, gpg_key_id):
        return self.gpg.recv_keys(f"hkp://{server}", gpg_key_id)

    def remote_get_key(self, key_hash, request_id=None):
        """
        Send a request to Yombo server to fetch a key.

        :param keyHash:
        :return:
        """
        if self._Loader.check_component_status("AMQPYombo", "_start_"):
            content = {"id": key_hash}
            amqp_message = self._AMQP.generate_message_request("ysrv.e.gw_config",
                                                               "yombo.gateway.lib.gpg",
                                                               "yombo.server.configs",
                                                               content,
                                                               self.amqp_response_get_key)
            self._AMQP.publish(amqp_message)

    def get_root_key(self):  #todo: change to API
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        if self._Loader.check_component_status("AMQPYombo", "_start_"):
            content = {"id": "root"}
            amqp_message = self._AMQP.generate_message_request("ysrv.e.gw_config",
                                                               "yombo.gateway.lib.gpg",
                                                               "yombo.server.configs",
                                                               content,
                                                               self.amqp_response_get_key)
            self._AMQP.publish(amqp_message)

    def amqp_response_get_key(self, send_info, deliver, properties, message):
        """
        Receives keys as a response from remote_get_key

        :param deliver:
        :param properties:
        :param message:
        :return:
        """
        #        logger.warn("deliver: {deliver}, properties: {properties}, message: {message}", deliver=deliver, properties=properties, message=message)
        self.add_key(message["fingerprint"], message["public_key"])

    def add_key(self, fingerprint, public_key, trust_level=None):
        """
        Used as a shortcut to call import_to_keyring and sync_keyring_to_db

        :param new_key:
        :param trust_level:
        :return:
        """
        trust_level = trust_level or 2
        self.import_to_keyring(public_key)
        if trust_level is not None:
            self.set_key_trust(fingerprint, trust_level)
        self.sync_keyring_to_db()

    @inlineCallbacks
    def import_to_keyring(self, key_to_import):
        """
        Imports a new key. First, it checks if we already have the key imported, if so, we set the trust level.

        If the key isn't in the keyring, it'll add it and set the trust.
        """
        key_has_been_found = False

        yield self.load_keys()
        if key_has_been_found is False:  # If not found, lets add the key to gpg keyring
            import_result = yield self._add_to_keyring(key_to_import)
            if import_result["status"] == "Failed":
                raise YomboWarning("Unable to import GPG key.")

    def _add_to_keyring(self, key_to_add):
        """
        Helper function to actually add the keyring.

        :param key_to_add:
        :return:
        """
        # print("doing actual import now..%s" % key_to_add)
        importResults = self.gpg_module.import_keys(key_to_add)
        results = importResults.results
        logger.info("Result size: {length}", length=len(results))
        # print("import results: %s" % results)
        if (len(results) >= 1):
            results = {"status": "Ok"}
            # results = results[0]
            # results["status"] = results["status"].replace("\n", "")
        else:
            results = {"status": "Failed"}
        return results

    def check_key_trust(self, fingerprint: str) -> str:
        """
        Returns the trust level of a given fingerprint

        :param fingerprint: fingerprint to check.
        :type fingerprint: string
        :return: Level of trust.
        :rtype: string
        """
        if fingerprint in self.gpg_keys:
            return TRUST_MAP[self.gpg_module[fingerprint]["ownertrust"]]

    ##########################
    ###  Helper Functions  ###
    ##########################

    # @inlineCallbacks
    # def get_keyring_keys(self, secret=False):
    #     """
    #     Gets the keys in the keyring and formats it nicely.
    #
    #     Formats the results of gnupg.list_keys() into a more usable form.
    #     :param keys:
    #     :return:
    #     """
    #     input_keys = yield self.gpg_module.list_keys(secret=secret)
    #
    #     output_key = {}
    #
    #     for record in input_keys:
    #         uid = record["uids"][0]
    #         # split the string by ( or )
    #         uid_list = re.split(r"\(|\)", uid)
    #         # strip whitespaces and replace < or > by empty space ""
    #         uid_list = list(map(lambda x: re.sub(r"<|>", "", x.strip()), uid_list))
    #
    #         uid_results = {
    #             "name": uid_list[0],
    #             "comment": uid_list[1],
    #             "email": uid_list[2],
    #         }
    #
    #         email_parts = uid_results["email"].split("@")
    #         if len(email_parts) > 2:
    #             logger.warn("Skipping GPG key due to invalid UID: {uid}", uid=uid)
    #             continue
    #         if email_parts[1] == "gw.gpg.yombo.net":
    #             endpoint_type = "gw"
    #         elif email_parts[1] == "root.gpg.yombo.net":
    #             endpoint_type = "root"
    #         elif email_parts[1] == "issuing.gpg.yombo.net":
    #             endpoint_type = "root"
    #         elif email_parts[1] == "server.gpg.yombo.net":
    #             endpoint_type = "server"
    #         else:
    #             endpoint_type = "unknown"
    #         endpoint_id = email_parts[0]
    #
    #         # key_comment = uid[uid.find("(")+1:uid.find(")")]
    #         key = {
    #             "fullname": uid_results["name"],
    #             "comment": uid_results["comment"],
    #             "email": uid_results["email"],
    #             "endpoint_id": endpoint_id,
    #             "endpoint_type": endpoint_type,
    #             "keyid": record["keyid"],
    #             "fingerprint": record["fingerprint"],
    #             "expires_at": int(record["expires"]),
    #             "sigs": record["sigs"],
    #             "subkeys": record["subkeys"],
    #             "length": int(record["length"]),
    #             "ownertrust": record["ownertrust"],
    #             "algo": record["algo"],
    #             "created_at": int(record["date"]),
    #             "trust": record["trust"],
    #             "type": record["type"],
    #             "uids": record["uids"],
    #         }
    #         key = bytes_to_unicode(key)
    #         output_key[record["fingerprint"]] = key
    #     return output_key

    @inlineCallbacks
    def generate_key(self, sync_when_done = None):
        """
        Generates a new GPG key pair. Updates yombo.toml and marks it to be sent when gateway
        connects to server again.
        """
        operating_mode = self._Loader.operating_mode
        if operating_mode != "run":
            logger.info("Not creating GPG key, in wrong run mode: {mode}", mode=operating_mode)

        if self._generating_key is True:
            return
        self._generating_key = True
        gwid = self._gateway_id
        if gwid is "local":
            self.key_generation_status = "failed: gateway not setup, gateway id is missing"
            self._generating_key = False
            return
        passphrase = random_string(length=random_int(200, .1), char_set="extended")
        expire_date = "10y"
        # if self.debug_mode is True:
        #     logger.warn("Setting GPG key to expire in one day due to debug mode.")
        #     expire_date = "1d"
        user_prefix = self._Configs.get("core.system_user_prefix")
        input_data = self.gpg_module.gen_key_input(
            name_email=f"{gwid}@{user_prefix}.gpg.yombo.net",
            name_real="Yombo Gateway",
            name_comment="Created by https://Yombo.net",
            key_type="RSA",
            key_length=4096,
            expire_date=expire_date,
            preferences="SHA512 SHA384 SHA256 SHA224 AES256 AES192 AES CAST5 ZLIB BZIP2 ZIP Uncompressed",
            keyserver="hkp://pgp.mit.edu",
            revoker="1:9C69E1F8A7C39961C223C485BCEAA0E429FA3EF8",
            passphrase=passphrase)

        self.key_generation_status = "working"

        def do_generate_key():
            logger.warn("Generating new system GPG key. This can take a little while on slower systems.")
            return self.gpg_module.gen_key(input_data)

        newkey = yield threads.deferToThread(do_generate_key)
        # print("bb 3: newkey: %s" % newkey)
        # print("bb 3: newkey: %s" % newkey.__dict__)
        # print("bb 3: newkey: %s" % type(newkey))
        self.key_generation_status = "done"

        if str(newkey) == "":
            logger.error("ERROR: Unable to generate GPG keys.... Is GPG installed and configured? Is it in your path?")
            self._generating_key = False
            raise YomboCritical("Error with python GPG interface.  Is it installed?")

        newfingerprint = newkey.fingerprint

        self._Configs.set("gpg.fingerprint", newfingerprint, ref_source=self)
        secret_file = f"{self._working_dir}/etc/gpg/{newfingerprint}.pass"
        yield self._Files.save(secret_file, passphrase)
        secret_file = f"{self._working_dir}/etc/gpg/last.pass"
        yield self._Files.save(secret_file, passphrase)

        yield self.load_keys()

        if newfingerprint not in self.gpg_keys:
            raise YomboWarning(f"Unable to find newly generated key: {newfingerprint}")

        self._Configs.set("gpg.last_sent_yombo", None, ref_source=self)
        self._Configs.set("gpg.last_sent_keyserver", None, ref_source=self)
        self._Configs.set("gpg.last_received_keyserver", None, ref_source=self)

        # self.send_my_gpg_key()
        self._generating_key = False

        if self._generating_key_deferred is not None and self._generating_key_deferred.called is False:
            self._generating_key_deferred.callback(1)

    ###########################################
    ###  Encrypt / Decrypt / Sign / Verify  ###
    ###########################################
    @inlineCallbacks
    def encrypt(self, in_text, destination=None, unicode=None):
        """
        Encrypt text and output as ascii armor text.

        :param in_text: Plain text to encrypt.
        :type in_text: string
        :param destination: Key id of the destination.
        :type destination: string
        :return: Ascii armored text.
        :rtype: string
        :raises: YomboException - If encryption failed.
        """
        if in_text is None:
            raise YomboWarning("Cannot encrypt NoneType.")

        if in_text.startswith("-----BEGIN PGP MESSAGE-----"):
            return in_text

        if hasattr(self, "myfingerprint") is False:
            return in_text

        if destination is None:
            destination = self.myfingerprint.value

        # print("gpg encrypt destination: %s" % destination)
        try:
            # output = self.gpg_module.encrypt(in_text, destination, sign=self.myfingerprint())
            output = yield threads.deferToThread(self._gpg_encrypt, in_text, destination)
            # output = self.gpg_module.encrypt(in_text, destination)
            # print("gpg output: %s" % output)
            # print("gpg %s: %s" % (in_text, output.status))
            if output.status != "encryption ok":
                raise YomboWarning("Unable to encrypt string. Error 1.")
            if unicode is False:
                return output.data
            return bytes_to_unicode(output.data)
        except Exception as e:
            raise YomboWarning(f"Unable to encrypt string. Error 2.: {e}")

    def _gpg_encrypt(self, data, destination):
        """
        Does the actual encryption. Just specify the email address of the destination, such as
        "gatewayid123@gw.gpg.yombo.net".

        This function is blocking and is called in a separate thread.

        :param data:
        :param destination:
        :return:
        """
        return self.gpg_module.encrypt(data, destination)

    @inlineCallbacks
    def decrypt(self, in_text, unicode=None):
        """
        Decrypt a PGP / GPG ascii armor text.  If passed in string/text is not detected as encrypted,
        will simply return the input.

        :param in_text: Ascii armored encoded text.
        :type in_text: string
        :return: Decoded string.
        :rtype: string
        :raises: YomboException - If decoding failed.
        """
        if in_text is None:
            raise YomboWarning("Cannot decrypt NoneType.")

        if in_text.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
            verify = yield self.verify_asymmetric(in_text)
            return verify
        elif in_text.startswith("-----BEGIN PGP MESSAGE-----"):
            try:
                output = yield threads.deferToThread(self._gpg_decrypt, in_text, self.gpg_key.passphrase)
                if output.status == "decryption ok":
                    if unicode is False:
                        return output.data
                    return bytes_to_unicode(output.data)

                # print("Trying more GPG keys.")

                for fingerprint, data in self.gpg_keys.items():
                    if not data.have_private:
                        continue
                    if fingerprint == self.myfingerprint.value:
                        continue
                    output = yield threads.deferToThread(self._gpg_decrypt, in_text, data.passphrase)
                    if output.status == "decryption ok":
                        # print("GPG decryption ok with key: %s" % data["email"])
                        if unicode is False:
                            return output.data
                        return bytes_to_unicode(output.data)
                raise YomboWarning("No more GPG keys to try.")
            except Exception as e:
                raise YomboWarning(f"Unable to decrypt string. Reason: {e}")
        return in_text

    def _gpg_decrypt(self, data, passphrase):
        """
        Does the actual decrypt. This function is blocking and is called in a separate thread.

        :param data:
        :param passphrase:
        :return:
        """
        return self.gpg_module.decrypt(data, passphrase=passphrase)

    def sign(self, in_text, asciiarmor=True):
        """
        Signs in_text and returns the signature.
        """
        if type(in_text) is str:
            try:
                signed = yield threads.deferToThread(self._gpg_sign, in_text)
                return signed.data
            except Exception as e:
                raise YomboWarning("Error with GPG system. Unable to sign your message: {e}", e=e)
        return False

    def _gpg_sign(self, in_text, asciiarmor=True):
        """
        Does the actual signing of text. This function is blocking and should be called in a separate thread.
        """
        try:
            signed = self.gpg_module.sign(in_text, fingerprint=self.myfingerprint.value, clearsign=asciiarmor)
            return signed
        except Exception as e:
            raise YomboWarning(e)

    def verify_asymmetric(self, in_text):
        """
        Verifys a signature. Returns the data if valid, otherwise False.
        """
        if in_text is None:
            return False

        if type(in_text) is str and in_text.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
            try:
                verified = self.gpg_module.verify(in_text)
                if verified.status == "signature valid":
                    if verified.stderr.find("TRUST_ULTIMATE") > 0:
                        pass
                    elif verified.stderr.find("TRUST_FULLY") > 0:
                        pass
                    else:
                        raise YomboWarning("Encryption not from trusted source!")
                    out = self.gpg_module.decrypt(in_text)
                    return out.data
                else:
                    return False
            except Exception as e:
                raise YomboWarning("Error with GPG system. Unable to verify signed text: {e}", e=e)
        return False

    def verify_destination(self, destination):
        """
        Validate that we have a key for the given destination.  If not, try to
        fetch the given key and add it to the key ring. Then revalidate.

        .. todo::

           This function is mostly a place holder. Function doesn't work or return anything useful.

        :param destination: The destination key to check for.
        :type destination: string
        :return: True if destination is valid, otherwise false.
        :rtype: bool
        """
        # Pseudocode
        #
        # Determine if gateway
        # Ask yombo service for fingerprint of gateway
        #   Can just ask keys.yombo.net for it since gateway
        #   may have multiple keys - which one to use?
        # Wait for yombo service to give us the key id
        # Ask gnupg to fetch the key
        # Retyrn true if good.
        pass
