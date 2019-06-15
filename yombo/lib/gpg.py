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

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/gpg.html>`_
"""

# Import python libraries
import yombo.ext.gnupg as gnupg
import os.path
from subprocess import Popen, PIPE
from Crypto import Random
from Crypto.Cipher import AES
import hashlib
import re
from time import time

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical
from yombo.core.library import YomboLibrary
import yombo.core.settings as settings
from yombo.utils import random_string, bytes_to_unicode, unicode_to_bytes, read_file, save_file, random_int

from yombo.core.log import get_logger
logger = get_logger("library.gpg")


class GPG(YomboLibrary):
    """
    Manage all GPG functions.
    """
    @property
    def public_key(self):
        return self._gpg_keys[self.myfingerprint()]["publickey"]

    @public_key.setter
    def public_key(self, val):
        return

    @property
    def gpg_key_id(self):
        return self.myfingerprint()

    @gpg_key_id.setter
    def gpg_key_id(self, val):
        return

    @property
    def gpg_key_full(self):
        return self._gpg_keys[self.myfingerprint()]

    @gpg_key_full.setter
    def gpg_key_full(self, val):
        return

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Get the GnuPG subsystem up and loaded.
        """
        self.key_generation_status = None
        self._generating_key = False
        self._gpg_keys = {}
        self._generating_key_deferred = None
        self.sks_pools = [  # Send to a few to ensure we get our key seeded
            "ipv4.pool.sks-keyservers.net",
            "na.pool.sks-keyservers.net",
            "eu.pool.sks-keyservers.net",
            "oc.pool.sks-keyservers.net",
            "pool.sks-keyservers.net",
            "ha.pool.sks-keyservers.net"
        ]
        self.working_dir = settings.arguments["working_dir"]
        self.gpg = gnupg.GPG(gnupghome=f"{self.working_dir}/etc/gpg")

        self.__mypassphrase = None  # will be loaded by sync_keyring_to_db() calls

        secret_file = f"{self.working_dir}/etc/gpg/last.pass"
        if os.path.exists(secret_file):
            phrase = yield read_file(secret_file)
            self.__mypassphrase = bytes_to_unicode(phrase)

    @inlineCallbacks
    def _init_from_atoms_(self, **kwargs):
        """
        Solving a chicken and the egg thing. Configurations use gpg, gpg uses configs. Have to partially
        load GPG, then load configs, then finish loading GPG _AFTER_ startup library determines run state.

        :param kwargs:
        :return:
        """
        self.gwuuid = self._Configs.get2("core", "gwuuid", None, False)
        self.myfingerprint = self._Configs.get2("gpg", "fingerprint", None, False)
        self.debug_mode = self._Configs.get("debug", "testing", False, False)
        self.mykey_last_sent_yombo = self._Configs.get2("gpg", "last_sent_yombo", None, False)
        self.mykey_last_sent_keyserver = self._Configs.get2("gpg", "last_sent_keyserver", None, False)
        self.mykey_last_received_keyserver = self._Configs.get2("gpg", "last_received_keyserver", None, False)

        if self._Loader.operating_mode == "run":
            yield self.sync_keyring_to_db()  # must sync first. Loads various data.
            yield self.validate_gpg_ready()

        # This feature isn"t working in the GNUPG library, or library alternatives.
        # print("checking if gpg key is old... %s" % self.myfingerprint())
        # print("checking if gpg key is old..  %s < %s " % (self.gpg_key_full["expires_at"], (time() - (60*60*24*90))))
        # if self.gpg_key_full["expires_at"] < (time() + (60*60*24*90)):
        #     print("GPG key is older, going to renew.")
        #     yield self.renew_expiration()

    def _start_(self, **kwargs):
        """
        We don't do anything, but "pass" so we don't generate an exception.
        """
        self.remote_get_root_key()
        self.send_my_gpg_key_loop = LoopingCall(self.send_my_gpg_key)
        self.send_my_gpg_key_loop.start(random_int(60 * 60 * 2, .2))

    def _stop_(self, **kwargs):
        """
        We don't do anything, but "pass" so we don't generate an exception.
        """
        if self._generating_key is True:
            self._generating_key_deferred = Deferred
            return self._generating_key_deferred

    def _unload_(self, **kwargs):
        """
        Do nothing
        """
        pass

    @inlineCallbacks
    def load_passphrase(self, fingerprint=None):
        if fingerprint is None:
            fingerprint = self.myfingerprint()
        if fingerprint is not None:
            secret_file = f"{self.working_dir}/etc/gpg/{fingerprint}.pass"
            if os.path.exists(secret_file):
                phrase = yield read_file(secret_file)
                phrase = bytes_to_unicode(phrase)
                if fingerprint == self.myfingerprint():
                    self.__mypassphrase = phrase
                return phrase
        return None

    @inlineCallbacks
    def validate_gpg_ready(self):
        """
        Validate that the gateway has a GPG key for encrypting data. If not, create one.

        :return:
        """
        valid = True
        myfingerprint = self.myfingerprint()
        if myfingerprint is None:
            valid = False
            logger.warn("No GPG fingerprint found! Unable to process GPG items.")
        if self.__mypassphrase is None:
            valid = False
            logger.warn("No GPG passphrase found! Unable to process GPG items.")
        if myfingerprint not in self._gpg_keys:
            valid = False
            logger.warn("Cannot find my GPG key!")
        if myfingerprint in self._gpg_keys and self.gateway_id != self._gpg_keys[myfingerprint]["endpoint_id"]:
                valid = False
                logger.warn("Local gateway_id '{gateway_id}' doesn't match my GPG endpoint id '{endpoint_id}'",
                            gateway_id=self.gateway_id, endpoint_id=self._gpg_keys[myfingerprint]["endpoint_id"])
        if valid is False:
            logger.info("Gateway doesn't have GPG key, creating one...")
            yield self.generate_key()

    @inlineCallbacks
    def send_my_gpg_key(self):
        """
        Periodically is called to send our GPG key to Yombo server and the SKS
        key pool.

        However, we don't always send when requested. We only send to each destination once every
        30 days. We also collect any new signatures once every 10 days.
        :return:
        """
        if self.myfingerprint() is None:
            logger.warn("Unable to send GPG - no valid local key exists.")
            return

        # print("elf.mykey_last_sent_yombo(): %s" % type(self.mykey_last_sent_yombo()))
        # print("elf.mykey_last_sent_yombo(): %s" % self.mykey_last_sent_yombo())
        if self.mykey_last_sent_yombo() is None:
            yield self.send_my_gpg_key_to_yombo()
        elif self.mykey_last_sent_yombo() < int(time()) - (60*60*24*30):
            yield self.send_my_gpg_key_to_yombo()

        # print(f"mykey_last_sent_keyserver: {self.mykey_last_sent_keyserver()}")

        if self.mykey_last_sent_keyserver() is None:
            yield self.send_my_gpg_key_to_keyserver()
        elif self.mykey_last_sent_keyserver() < int(time()) - (60*60*24*30):
            yield self.send_my_gpg_key_to_keyserver()
            if self.mykey_last_received_keyserver() is None and \
                    self.mykey_last_sent_keyserver() < int(time()) - (60*60*6):
                yield self.get_my_gpg_key_from_keyserver()
            elif self.mykey_last_received_keyserver() < int(time()) - (60*60*24*10) and \
                    self.mykey_last_sent_keyserver() < int(time()) - (60*60*1):
                yield self.get_my_gpg_key_from_keyserver()

    @inlineCallbacks
    def send_my_gpg_key_to_yombo(self):
        """
        Send my gpg key to the yombo server.

        :return:
        """
        # print("starting: send_my_gpg_key_to_yombo")

        mykey = self.gpg_key_full
        body = {
            "keyid": mykey["fingerprint"],
            "publickey_ascii": mykey["publickey"],
        }

        logger.debug("Sending my public GPG key to Yombo.")
        logger.debug("sending gpg information: {body}", body=body)
        gwid = self.gateway_id
        try:
            response = yield self._YomboAPI.request(
                "POST", f"/v1/gateways/{gwid}/gpg",
                body)

        except YomboWarning as e:
            logger.warn("Unable to send GPG key to Yombo: {e}", e=e)
            return
        self._Configs.set("gpg", "last_sent_yombo", int(time()))

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
        self._Configs.set("gpg", "last_sent_keyserver", int(time()))

    def _send_my_gpg_key_to_keyserver(self, server, gpg_key_id):
        print(f"sending key to server: {gpg_key_id} -> {server}")
        # return self.gpg.send_keys(f"hkp://{server}", gpg_key_id)

    def get_my_gpg_key_from_keyserver(self):
        """
        Send my gpg key to the key server pool.

        :return:
        """
        # print("starting: get_my_gpg_key_from_keyserver")
        yield threads.deferToThread(self._get_my_gpg_key_from_keyserver,
                                    self.sks_pools[0],
                                    self.gpg_key_id)
        results = self.gpg.recv_keys("hkp://gpg.nebrwesleyan.edu", self.gpg_key_id)
        logger.info("Asking GPG key servers for any updates.")

        self._Configs.set("gpg", "last_received_keyserver", int(time()))

    def _get_my_gpg_key_from_keyserver(self, server, gpg_key_id):
        return self.gpg.recv_keys(f"hkp://{server}", gpg_key_id)

    ##########################
    #### Key management  #####
    ##########################
    @inlineCallbacks
    def sync_keyring_to_db(self):
        """
        Adds any keys found in the GPG keyring to the Yombo Database

        :return:
        """
        if self._Loader.operating_mode == "first_run":
            logger.info("Not syncing GPG keys to database on first run.")

        db_keys = yield self._LocalDB.get_gpg_key()
        gpg_public_keys = yield self.get_keyring_keys()
        gpg_private_keys = yield self.get_keyring_keys(True)
        logger.debug("gpg_public_keys: {gpg_keys}", gpg_keys=gpg_public_keys)

        for fingerprint, data in gpg_public_keys.items():
            data["passphrase"] = None
            data["privatekey"] = None
            data["publickey"] = None
            if int(data["length"]) < 2048:
                logger.error("Not adding key ({length}) due to length being less then 2048. Key is unusable",
                             length=gpg_public_keys[fingerprint]["length"])
                continue
            if fingerprint in db_keys:
                data["publickey"] = db_keys[fingerprint]["publickey"]

            data["publickey"] = self.gpg.export_keys(data["fingerprint"])
            if data["fingerprint"] in gpg_private_keys:
                # print("private key found: %s" % data["fingerprint"])
                data["have_private"] = 1
            else:
                data["have_private"] = 0
            if data["have_private"] == 1:
                try:
                    passphrase = yield self.load_passphrase(data["fingerprint"])
                    # print("have a loaded passphrase: %s" % passphrase)
                    data["privatekey"] = self.gpg.export_keys(data["fingerprint"],
                                                              secret=True,
                                                              passphrase=passphrase,
                                                              expect_passphrase=True)
                    data["passphrase"] = passphrase
                except Exception as e:
                    logger.warn("Error was trying to get private key ({fingerprint}): {e}",
                                fingerprint=data["fingerprint"], e=e)
                    data["have_private"] = 0
            else:
                try:
                    data["privatekey"] = self.gpg.export_keys(data["fingerprint"],
                                                              secret=True,
                                                              expect_passphrase=False)
                except Exception as e:
                    data["have_private"] = 0

            # sync to local cache
            self._gpg_keys[data["fingerprint"]] = data

            # sync to database
            if fingerprint not in db_keys:
                yield self._LocalDB.insert_gpg_key(data)
            else:
                del db_keys[fingerprint]

        for fingerprint in list(db_keys):
            yield self._LocalDB.delete_gpg_key(fingerprint)

    def remote_get_key(self, key_hash, request_id=None):
        """
        Send a request to Yombo server to fetch a key.

        :param keyHash:
        :return:
        """
        if self._Loader.check_component_status("AMQPYombo", "_start_"):
            content = {"id": key_hash}
            amqp_message = self._AMQP.generate_message_request("ysrv.e.gw_config", "yombo.gateway.lib.gpg", "yombo.server.configs", content, self.amqp_response_get_key)
            self._AMQP.publish(amqp_message)

    def remote_get_root_key(self):
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        if self._Loader.check_component_status("AMQPYombo", "_start_"):
            content = {"id": "root"}
            amqp_message = self._AMQP.generate_message_request("ysrv.e.gw_config", "yombo.gateway.lib.gpg", "yombo.server.configs", content, self.amqp_response_get_key)
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

        if key_has_been_found is False:  # If not found, lets add the key to gpg keyring
            import_result = yield self._add_to_keyring(key_to_import)
            # print(f"import results: {import_result}")
            if import_result["status"] == "Failed":
                raise YomboWarning("Unable to import GPG key.")

    @inlineCallbacks
    def set_key_trust(self, fingerprint, trust_level=5):
        """
        Sets the trust of a key.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        trust_string = f"{fingerprint}:{trust_level:d}:\n"
        yield self.import_trust(trust_string)

        gpg_public_keys = yield self.get_keyring_keys()
        for have_key in gpg_public_keys:
            if have_key == fingerprint:
                if trust_level == 2 and self._gpg_keys[have_key]["ownertrust"] != "q":
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 3 and self._gpg_keys[have_key]["ownertrust"] != "n":
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 4 and self._gpg_keys[have_key]["ownertrust"] != "m":
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 5 and self._gpg_keys[have_key]["ownertrust"] != "f":
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 6 and self._gpg_keys[have_key]["ownertrust"] != "u":
                    self.set_key_trust(fingerprint, trust_level)
                break

    @inlineCallbacks
    def import_trust(self, trust_string):
        """
        Sets the trust of a key.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        # print("SEtting trust level: %s" % trust_string)
        p = yield Popen([f"gpg --import-ownertrust --homedir {self.working_dir}/etc/gpg"], shell=True,
                        stdin=PIPE, stdout=PIPE, close_fds=True)
        (child_stdout, child_stdin) = (p.stdout, p.stdin)
        child_stdin.write(unicode_to_bytes(f"{trust_string}\n"))
        child_stdin.close()
        result = child_stdout.read()
        logger.info("GPG Trust change: {result}", result=result)

    @inlineCallbacks
    def export_trust(self):
        """
        Exports the trust keys.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        # print("Getting trust levels")
        p = yield Popen([f"gpg --export-ownertrust --homedir {self.working_dir}/etc/gpg"], shell=True,
                        stdin=PIPE, stdout=PIPE, close_fds=True)
        (child_stdout, child_stdin) = (p.stdout, p.stdin)
        child_stdin.close()
        result = child_stdout.read()
        logger.info("GPG Export trust: {result}", result=result)
        return result

    @inlineCallbacks
    def check_key_trust(self, fingerprint):
        """
        Returns the trust level of a given fingerprint

        :param fingerprint: fingerprint to check.
        :type fingerprint: string
        :return: Level of trust.
        :rtype: string
        """
        gpg_public_keys = yield self.get_keyring_keys()

        for key in gpg_public_keys:
            if fingerprint == key["fingerprint"]:
                return key["ownertrust"]

    def _add_to_keyring(self, key_to_add):
        """
        Helper function to actually add the keyring.

        :param key_to_add:
        :return:
        """
        # print("doing actual import now..%s" % key_to_add)
        importResults = self.gpg.import_keys(key_to_add)
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

    @inlineCallbacks
    def renew_expiration(self, expire_time="1y"):
        """
        Renew the expiration time of the certificate

        """
        logger.info(f"Extending GPG key: +{expire_time}")
        fingerprint = self.myfingerprint()
        yield threads.deferToThread(self._renew_expiration, fingerprint, expire_time, passphrase=self.__mypassphrase)
        yield self.send_my_gpg_key_to_keyserver()

    def _renew_expiration(self, fingerprint, expire_time, passphrase):
        # print("fingerprint: (%s) %s" % (fingerprint, type(fingerprint)))
        # print("expire_time: (%s) %s" % (expire_time, type(expire_time)))
        # print("passphrase: (%s) %s" % (passphrase, type(passphrase)))
        return self.gpg.expire(fingerprint, "6", passphrase)

    ##########################
    ###  Helper Functions  ###
    ##########################

    @inlineCallbacks
    def get_keyring_keys(self, secret=False):
        """
        Gets the keys in the keyring and formats it nicely.

        Formats the results of gnupg.list_keys() into a more usable form.
        :param keys:
        :return:
        """
        input_keys = yield self.gpg.list_keys(secret=secret)

        output_key = {}

        for record in input_keys:
            uid = record["uids"][0]
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
                logger.warn("Skipping GPG key due to invalid UID: {uid}", uid=uid)
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
                endpoint_type = "unknown"
            endpoint_id = email_parts[0]

            # key_comment = uid[uid.find("(")+1:uid.find(")")]
            key = {
                "fullname": uid_results["name"],
                "comment": uid_results["comment"],
                "email": uid_results["email"],
                "endpoint_id": endpoint_id,
                "endpoint_type": endpoint_type,
                "keyid": record["keyid"],
                "fingerprint": record["fingerprint"],
                "expires_at": int(record["expires"]),
                "sigs": record["sigs"],
                "subkeys": record["subkeys"],
                "length": int(record["length"]),
                "ownertrust": record["ownertrust"],
                "algo": record["algo"],
                "created_at": int(record["date"]),
                "trust": record["trust"],
                "type": record["type"],
                "uids": record["uids"],
            }
            key = bytes_to_unicode(key)
            output_key[record["fingerprint"]] = key
        return output_key

    @inlineCallbacks
    def generate_key(self, sync_when_done = None):
        """
        Generates a new GPG key pair. Updates yombo.ini and marks it to be sent when gateway
        connects to server again.
        """
        operating_mode = self._Loader.operating_mode
        if operating_mode != "run":
            logger.info("Not creating GPG key, in wrong run mode: {mode}", mode=operating_mode)

        if self._generating_key is True:
            return
        self._generating_key = True
        gwid = self.gateway_id
        gwuuid = self.gwuuid()
        if gwid is "local" or gwuuid is None:
            self.key_generation_status = "failed: gateway not setup, gateway id or uuid is missing"
            self._generating_key = False
            return
        passphrase = random_string(length=random_int(200, .1), char_set="extended")
        expire_date = "5y"
        # if self.debug_mode is True:
        #     logger.warn("Setting GPG key to expire in one day due to debug mode.")
        #     expire_date = "1d"
        input_data = self.gpg.gen_key_input(
            name_email=f"{gwid}@gw.gpg.yombo.net",
            name_real="Yombo Gateway",
            name_comment="Created by https://Yombo.net",
            key_type="RSA",
            key_length=4096,
            expire_date=expire_date,
            preferences="SHA512 SHA384 SHA256 SHA224 AES256 AES192 AES CAST5 ZLIB BZIP2 ZIP Uncompressed",
            keyserver="hkp://gpg.nebrwesleyan.edu",
            revoker="1:9C69E1F8A7C39961C223C485BCEAA0E429FA3EF8",
            passphrase=passphrase)

        self.key_generation_status = "working"
        newkey = yield threads.deferToThread(self.do_generate_key, input_data)
        # print("bb 3: newkey: %s" % newkey)
        # print("bb 3: newkey: %s" % newkey.__dict__)
        # print("bb 3: newkey: %s" % type(newkey))
        self.key_generation_status = "done"

        if str(newkey) == "":
            logger.error("ERROR: Unable to generate GPG keys.... Is GPG installed and configured? Is it in your path?")
            self._generating_key = False
            raise YomboCritical("Error with python GPG interface.  Is it installed?")

        private_keys = yield self.get_keyring_keys(True)
        newfingerprint = ""

        for existing_key_id, key_data in private_keys.items():
            # print("inspecting key: %s" % existing_key_id)
            if key_data["fingerprint"] == str(newkey):
                newfingerprint = key_data["fingerprint"]
                break
        asciiArmoredPublicKey = self.gpg.export_keys(newfingerprint)
        print(f"saving new gpg fingerprint: {newfingerprint}")
        self._Configs.set("gpg", "fingerprint", newfingerprint)
        secret_file = f"{self._Atoms.get('working_dir')}/etc/gpg/{newfingerprint}.pass"
        # print("saveing pass to : %s" % secret_file)
        yield save_file(secret_file, passphrase)
        secret_file = f"{self._Atoms.get('working_dir')}/etc/gpg/last.pass"
        yield save_file(secret_file, passphrase)
        self.__mypassphrase = passphrase

        self._Configs.set("gpg", "last_sent_yombo", None)
        self._Configs.set("gpg", "last_sent_keyserver", None)
        self._Configs.set("gpg", "last_received_keyserver", None)

        yield self.sync_keyring_to_db()
        # self.send_my_gpg_key()
        #
        # gpg_keys = yield self.gpg.get_keyring_keys(keys=fingerprint)
        #
        # # print("keys: %s" % type(keys))
        # # print("newkey1: %s" % newkey)
        # print("newkey2: %s" % str(newkey))
        # print("keys: %s" % gpg_keys)
        #
        # mykey = gpg_keys[fingerprint]
        # mykey["publickey"] = asciiArmoredPublicKey
        # mykey["notes"] = "Autogenerated."
        # mykey["have_private"] = 1

        self._generating_key = False

        if self._generating_key_deferred is not None and self._generating_key_deferred.called is False:
            self._generating_key_deferred.callback(1)

    def do_generate_key(self, input_data):
        logger.warn("Generating new system GPG key. This can take a little while on slower systems.")
        return self.gpg.gen_key(input_data)

    def get_key(self, fingerprint=None):
        if fingerprint is None:
            fingerprint = self.myfingerprint()
        key = None
        if fingerprint in self._gpg_keys:
            key = self._gpg_keys[fingerprint].copy()
        # else:
        #     for key_id, data in self._gpg_keys.items():
        #         if data[""]

        if key is None:
            return

        if "privatekey" in key:
            del key["privatekey"]
        if "passphrase" in key:
            del key["passphrase"]
        return key

    # def get_key(self, fingerprint):
    #     asciiArmoredPublicKey = self.gpg.export_keys(fingerprint)
    #     return asciiArmoredPublicKey

    def display_encrypted(self, in_text):
        """
        Makes an input field friend version of an input. If encrypted, returns
        "-----ENCRYPTED DATA-----", otherwise returns the text unchanged.

        :param in_text:
        :return:
        """
        in_text_search = unicode_to_bytes(in_text)
        if in_text_search.startswith(b"-----BEGIN PGP MESSAGE-----"):
            return "-----ENCRYPTED DATA-----"
        else:
            return in_text

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
        if in_text.startswith("-----BEGIN PGP MESSAGE-----"):
            return in_text

        if hasattr(self, "myfingerprint") is False:
            return in_text

        if destination is None:
            destination = self.myfingerprint()

        # print("gpg encrypt destination: %s" % destination)
        try:
            # output = self.gpg.encrypt(in_text, destination, sign=self.myfingerprint())
            output = yield threads.deferToThread(self._gpg_encrypt, in_text, destination)
            # output = self.gpg.encrypt(in_text, destination)
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
        return self.gpg.encrypt(data, destination)

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
        if in_text.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
            verify = yield self.verify_asymmetric(in_text)
            return verify
        elif in_text.startswith("-----BEGIN PGP MESSAGE-----"):
            try:
                output = yield threads.deferToThread(self._gpg_decrypt, in_text, self.__mypassphrase)
                if output.status == "decryption ok":
                    if unicode is False:
                        return output.data
                    return bytes_to_unicode(output.data)

                # print("Trying more GPG keys.")

                myfingerprint = self.myfingerprint()
                for fingerprint, data in self._gpg_keys.items():
                    if data["have_private"] == 0:
                        continue
                    if fingerprint == myfingerprint:
                        continue
                    output = yield threads.deferToThread(self._gpg_decrypt, in_text, data["passphrase"])
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
        return self.gpg.decrypt(data, passphrase=passphrase)

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
            signed = self.gpg.sign(in_text, fingerprint=self.myfingerprint(), clearsign=asciiarmor)
            return signed
        except Exception as e:
            raise YomboWarning(e)


    def verify_asymmetric(self, in_text):
        """
        Verifys a signature. Returns the data if valid, otherwise False.
        """
        if type(in_text) is str and in_text.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
            try:
                verified = self.gpg.verify(in_text)
                if verified.status == "signature valid":
                    if verified.stderr.find("TRUST_ULTIMATE") > 0:
                        pass
                    elif verified.stderr.find("TRUST_FULLY") > 0:
                        pass
                    else:
                        raise YomboWarning("Encryption not from trusted source!")
                    out = self.gpg.decrypt(in_text)
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

    @staticmethod
    def aes_str_to_bytes(data):
        u_type = type(b"".decode("utf8"))
        if isinstance(data, u_type):
            return data.encode("utf8")
        return data

    def aes_pad(self, key, size):
        """
        Ensures the aes key is properly padded.

        :param key:
        :param size:
        :return:
        """
        return key + (size - len(key) % size) * self.aes_str_to_bytes(chr(size - len(key) % size))

    @staticmethod
    def aes_unpad(s):
        return s[:-ord(s[len(s)-1:])]

    @inlineCallbacks
    def encrypt_aes(self, key, raw, size=128):
        """
        Encrypt something using AES 128, 192, 256 (very strong).

        Modified from: https://gist.github.com/mguezuraga/257a662a51dcde53a267e838e4d387cd

        :param key: A password
        :type key: string
        :param raw: Any type of data can be encrypted. Text, binary.
        :type key: string
        :param size: AES key size, one of: 128, 192, 256
        :type size: int
        :return: String containing the encrypted content.
        """
        if size not in (128, 192, 256):
            raise YomboWarning("encrypt_aes size must be one of: 128, 192, or 256")
        key = hashlib.sha256(key.encode("utf-8")).digest()
        key_size = int(size/8)
        raw = self.aes_pad(self.aes_str_to_bytes(raw), key_size)
        results = yield threads.deferToThread(self._encrypt_aes, key, raw)
        return results

    def _encrypt_aes(self, key, raw):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(raw)
        # return base64.b85encode(iv + cipher.encrypt(raw)).decode("utf-8")

    @inlineCallbacks
    def decrypt_aes(self, key, encoded):
        key = hashlib.sha256(key.encode("utf-8")).digest()
        results = yield threads.deferToThread(self._decrypt_aes, key, encoded)
        data = self.aes_unpad(results)
        return data

    def _decrypt_aes(self, key, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        results = cipher.decrypt(enc[AES.block_size:])
        try:
            results = results.decode("utf-8")
        except:
            pass
        return results
