# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `GPG @ Module Development <https://yombo.net/docs/libraries/gpg>`_


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
# import gnupg
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
from yombo.utils import random_string, bytes_to_unicode, unicode_to_bytes, read_file, save_file, random_int

from yombo.core.log import get_logger
logger = get_logger('library.gpg')


class GPG(YomboLibrary):
    """
    Manage all GPG functions.
    """
    @property
    def public_key(self):
        return self._gpg_keys[self.myfingerprint()]['publickey']

    @public_key.setter
    def public_key(self, val):
        return

    @property
    def gpg_key_id(self):
        return self.myfingerprint()

    @gpg_key_id.setter
    def public_key_id(self, val):
        return

    @property
    def gpg_key_full(self):
        # print("my key id: %s" % self.myfingerprint())
        # print("my keys:%s " % self._gpg_keys)
        return self._gpg_keys[self.myfingerprint()]

    @gpg_key_full.setter
    def gpg_key_full(self, val):
        return

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Get the GnuPG subsystem up and loaded.
        """
        self.aes_blocksize = 32
        self.key_generation_status = None
        self._generating_key = False
        self._gpg_keys = {}
        self._generating_key_deferred = None
        self.sks_pools = [  # Send to a few to ensure we get our key seeded
            'gpg.nebrwesleyan.edu',
            'na.pool.sks-keyservers.net',
            'eu.pool.sks-keyservers.net',
            'oc.pool.sks-keyservers.net',
            'pool.sks-keyservers.net',
        ]
        self.working_dir = self._Loader.command_line_arguments['working_dir']
        self.gpg = gnupg.GPG(gnupghome="%s/etc/gpg" % self.working_dir)

        self.__mypassphrase = None  # will be loaded by sync_keyring_to_db() calls

        secret_file = "%s/etc/gpg/last.pass" % self.working_dir
        if os.path.exists(secret_file):
            phrase = yield read_file(secret_file)
            self.__mypassphrase = bytes_to_unicode(phrase)

    @inlineCallbacks
    def _init_from_atoms_(self, **kwargs):
        self.gateway_id = self._Configs.get2('core', 'gwid', 'local', False)
        self.gwuuid = self._Configs.get2('core', 'gwuuid', None, False)
        self.myfingerprint = self._Configs.get2('gpg', 'fingerprint', None, False)
        self.debug_mode = self._Configs.get('debug', 'testing', False, False)
        self.mykey_last_sent_yombo = self._Configs.get2('gpg', 'last_sent_yombo', None, False)
        self.mykey_last_sent_keyserver = self._Configs.get2('gpg', 'last_sent_keyserver', None, False)
        self.mykey_last_received_keyserver = self._Configs.get2('gpg', 'last_received_keyserver', None, False)

        yield self.sync_keyring_to_db()  # must sync first. Loads various data.
        if self._Loader.operating_mode == 'run':
            yield self.validate_gpg_ready()

        # This feature isn't working in the GNUPG library, or library alternatives.
        # print("checking if gpg key is old... %s" % self.myfingerprint())
        # print("checking if gpg key is old..  %s < %s " % (self.gpg_key_full['expires_at'], (time() - (60*60*24*90))))
        # if self.gpg_key_full['expires_at'] < (time() + (60*60*24*90)):
        #     print("GPG key is older, going to renew.")
        #     yield self.renew_expiration()

    def _start_(self, **kwargs):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        if self._Loader.operating_mode != 'run':
            return

        self.remote_get_root_key()
        self.send_my_gpg_key_loop = LoopingCall(self.send_my_gpg_key)
        self.send_my_gpg_key_loop.start(random_int(60 * 60 * 2, .2))

    def _stop_(self, **kwargs):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        if self._generating_key is True:
            self._generating_key_deferred = Deferred
            return self._generating_key_deferred

    def _unload_(self, **kwargs):
        """
        Do nothing
        """
        pass

    def _done_init(self):
        self.initDefer.callback(10)

    @inlineCallbacks
    def load_passphrase(self, fingerprint=None):
        if fingerprint is None:
            fingerprint = self.myfingerprint()
        if fingerprint is not None:
            secret_file = "%s/etc/gpg/%s.pass" % (self.working_dir, fingerprint)
            if os.path.exists(secret_file):
                phrase = yield read_file(secret_file)
                phrase = bytes_to_unicode(phrase)
                if fingerprint == self.myfingerprint():
                    self.__mypassphrase = phrase
                return phrase
        return None

    @inlineCallbacks
    def validate_gpg_ready(self):
        valid = True
        if self.myfingerprint is None:
            valid = False
            logger.warn("No GPG fingerprint found! Unable to process GPG items.")
        if self.__mypassphrase is None:
            valid = False
            logger.warn("No GPG passphrase found! Unable to process GPG items.")
        if valid is False:
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
        if self.myfingerprint is None:
            logger.warn("Unable to send GPG - no valid local key exists.")
            return

        if self.mykey_last_sent_yombo() is None:
            self.send_my_gpg_key_to_yombo()
        elif self.mykey_last_sent_yombo() < int(time()) - (60*60*24*30):
            self.send_my_gpg_key_to_yombo()

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

    def send_my_gpg_key_to_yombo(self):
        """
        Send my gpg key to the yombo server.

        :return:
        """
        # print("starting: send_my_gpg_key_to_yombo")

        mykey = self.gpg_key_full
        body = {
            "fingerprint": mykey['fingerprint'],
            "publickey": mykey['publickey'],
        }

        # logger.info("sending local information: {body}", body=body)

        requestmsg = self._AMQPYombo.generate_message_request(
            exchange_name='ysrv.e.gw_system',
            source='yombo.gateway.lib.gpg',
            destination='yombo.server.gw_system',
            body=body,
            request_type="gw_gpg_update",
            callback=None,
        )
        logger.info("Sending my public GPG key to Yombo.")
        self._AMQPYombo.publish(**requestmsg)
        self._Configs.set('gpg', 'last_sent_yombo', int(time()))

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
        self._Configs.set('gpg', 'last_sent_keyserver', int(time()))

    def _send_my_gpg_key_to_keyserver(self, server, gpg_key_id):
        print("sending key to server: %s -> %s" % (gpg_key_id, server))
        # return self.gpg.send_keys("hkp://%s" % server, gpg_key_id)

    def get_my_gpg_key_from_keyserver(self):
        """
        Send my gpg key to the key server pool.

        :return:
        """
        # print("starting: get_my_gpg_key_from_keyserver")
        yield threads.deferToThread(self._get_my_gpg_key_from_keyserver,
                                    self.sks_pools[0],
                                    self.gpg_key_id)
        results = self.gpg.recv_keys('hkp://gpg.nebrwesleyan.edu', self.gpg_key_id)
        logger.info("Asking GPG key servers for any updates.")

        self._Configs.set('gpg', 'last_received_keyserver', int(time()))

    def _get_my_gpg_key_from_keyserver(self, server, gpg_key_id):
        return self.gpg.recv_keys("hkp://%s" % server, gpg_key_id)

    ##########################
    #### Key management  #####
    ##########################
    @inlineCallbacks
    def sync_keyring_to_db(self):
        """
        Adds any keys found in the GPG keyring to the Yombo Database

        :return:
        """
        if self._Loader.operating_mode == 'first_run':
            logger.info("Not syncing GPG keys to database on first run.")

        db_keys = yield self._LocalDB.get_gpg_key()
        # logger.debug("db_keys: {db_keys}", db_keys=db_keys)
        gpg_public_keys = yield self.get_keyring_keys()
        gpg_private_keys = yield self.get_keyring_keys(True)
        # print("keys: %s" % gpg_public_keys)
        logger.debug("2gpg_public_keys: {gpg_keys}", gpg_keys=gpg_public_keys)
        # logger.debug("2gpg_private_keys: {gpg_keys}", gpg_keys=gpg_private_keys)

        for fingerprint in list(gpg_public_keys):
            data = gpg_public_keys[fingerprint]
            data['passphrase'] = None
            data['privatekey'] = None
            data['publickey'] = None
            if int(gpg_public_keys[fingerprint]['length']) < 2048:
                logger.error("Not adding key ({length}) due to length being less then 2048. Key is unusable",
                             length=gpg_public_keys[fingerprint]['length'])
                continue
            # print("data: %s" % data)
            data['publickey'] = self.gpg.export_keys(data['fingerprint'])
            if data['fingerprint'] in gpg_private_keys:
                # print("private key found: %s" % data['fingerprint'])
                data['have_private'] = 1
            else:
                data['have_private'] = 0
            if data['have_private'] == 1:
                try:
                    passphrase = yield self.load_passphrase(data['fingerprint'])
                    # print("have a loaded passphrase: %s" % passphrase)
                    data['privatekey'] = self.gpg.export_keys(data['fingerprint'],
                                                              secret=True,
                                                              passphrase=passphrase,
                                                              expect_passphrase=True)
                    data['passphrase'] = passphrase
                except Exception as e:
                    logger.warn("Error will trying to get private key ({fingerprint}): {e}",
                                fingerprint=data['fingerprint'], e=e)
                    data['have_private'] = 0
            else:
                try:
                    data['privatekey'] = self.gpg.export_keys(data['fingerprint'],
                                                              secret=True,
                                                              expect_passphrase=False)
                except Exception as e:
                    data['have_private'] = 0

            # sync to local cache
            # print("adding key to cache: %s" % data['fingerprint'])
            self._gpg_keys[data['fingerprint']] = data

            # sync to database
            if fingerprint not in db_keys:
                yield self._LocalDB.insert_gpg_key(data)
            else:
                del db_keys[fingerprint]
            # del gpg_public_keys[fingerprint]

        # print("final gpg keys: %s" % self._gpg_keys)
        # logger.debug("db_keys: {gpg_keys}", gpg_keys=db_keys.keys())
        # logger.debug("gpg_public_keys: {gpg_keys}", gpg_keys=gpg_public_keys.keys())

        for fingerprint in list(db_keys):
            yield self._LocalDB.delete_gpg_key(fingerprint)

    def remote_get_key(self, key_hash, request_id=None):
        """
        Send a request to Yombo server to fetch a key.

        :param keyHash:
        :return:
        """
        if request_id is None:
            request_id = random_string()
        if self._Loader.check_component_status('AMQPYombo', '_start_'):
            content = {'id': key_hash}
            amqp_message = self._AMQP.generate_message_request('ysrv.e.gw_config', 'yombo.gateway.lib.gpg', 'yombo.server.configs', content, self.amqp_response_get_key)
            self._AMQP.publish(amqp_message)

    def remote_get_root_key(self):
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        if self._Loader.check_component_status('AMQPYombo', '_start_'):
            content = {'id': 'root'}
            amqp_message = self._AMQP.generate_message_request('ysrv.e.gw_config', 'yombo.gateway.lib.gpg', 'yombo.server.configs', content, self.amqp_response_get_key)
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
        self.add_key(message['fingerprint'], message['public_key'])

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
            print("import results: %s" % import_result)
            if import_result['status'] == "Failed":
                raise YomboWarning("Unable to import GPG key.")

    @inlineCallbacks
    def set_key_trust(self, fingerprint, trust_level=5):
        """
        Sets the trust of a key.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        trust_string = "%s:%d:\n" % (fingerprint, trust_level)
        yield self.import_trust(trust_string)

        gpg_public_keys = yield self.get_keyring_keys()
        for have_key in gpg_public_keys:
            if have_key == fingerprint:
                if trust_level == 2 and self._gpg_keys[have_key]['ownertrust'] != 'q':
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 3 and self._gpg_keys[have_key]['ownertrust'] != 'n':
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 4 and self._gpg_keys[have_key]['ownertrust'] != 'm':
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 5 and self._gpg_keys[have_key]['ownertrust'] != 'f':
                    self.set_key_trust(fingerprint, trust_level)
                elif trust_level == 6 and self._gpg_keys[have_key]['ownertrust'] != 'u':
                    self.set_key_trust(fingerprint, trust_level)
                break

    @inlineCallbacks
    def import_trust(self, trust_string):
        """
        Sets the trust of a key.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        # print("SEtting trust level: %s" % trust_string)
        p = yield Popen(["gpg --import-ownertrust --homedir %s/etc/gpg" % self.working_dir], shell=True,
                        stdin=PIPE, stdout=PIPE, close_fds=True)
        (child_stdout, child_stdin) = (p.stdout, p.stdin)
        child_stdin.write(unicode_to_bytes("%s\n" % trust_string))
        child_stdin.close()
        result = child_stdout.read()
        logger.info("GPG Trust change: {result}", result=result)

    @inlineCallbacks
    def export_trust(self):
        """
        Exports the trust keys.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        print("Getting trust levels")
        p = yield Popen(["gpg --export-ownertrust --homedir %s/etc/gpg" % self.working_dir], shell=True,
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
            if fingerprint == key['fingerprint']:
                return key['ownertrust']

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
        print("import results: %s" % results)
        if (len(results) >= 1):
            results = {'status': 'Ok'}
            # results = results[0]
            # results['status'] = results['status'].replace("\n", "")
        else:
            results = {'status': 'Failed'}
        return results

    @inlineCallbacks
    def renew_expiration(self, expire_time='1y'):
        """
        Renew the expiration time of the certificate

        """
        logger.info("Extending GPG key: +%s" % expire_time)
        fingerprint = self.myfingerprint()
        yield threads.deferToThread(self._renew_expiration, fingerprint, expire_time, passphrase=self.__mypassphrase)
        yield self.send_my_gpg_key_to_keyserver()

    def _renew_expiration(self, fingerprint, expire_time, passphrase):
        # print("fingerprint: (%s) %s" % (fingerprint, type(fingerprint)))
        # print("expire_time: (%s) %s" % (expire_time, type(expire_time)))
        # print("passphrase: (%s) %s" % (passphrase, type(passphrase)))
        return self.gpg.expire(fingerprint, '6', passphrase)

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
            # print "list keys: %s" % record
            uid = record['uids'][0]
            # split the string by ( or )
            uid_list = re.split(r'\(|\)', uid)
            # strip whitespaces and replace < or > by empty space ''
            uid_list = list(map(lambda x: re.sub(r'<|>', '', x.strip()), uid_list))

            uid_results = {
                'name': uid_list[0],
                'comment': uid_list[1],
                'email': uid_list[2],
            }

            endpoint_type = None
            email_parts = uid_results['email'].split('@')
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

            key_comment = uid[uid.find("(")+1:uid.find(")")]
            key = {
                'fullname': uid_results['name'],
                'comment': uid_results['comment'],
                'email': uid_results['email'],
                'endpoint_id': endpoint_id,
                'endpoint_type': endpoint_type,
                'keyid': record['keyid'],
                'fingerprint': record['fingerprint'],
                'expires_at': int(record['expires']),
                'sigs': record['sigs'],
                'subkeys': record['subkeys'],
                'length': int(record['length']),
                'ownertrust': record['ownertrust'],
                'algo': record['algo'],
                'created_at': int(record['date']),
                'trust': record['trust'],
                'type': record['type'],
                'uids': record['uids'],
            }
            key = bytes_to_unicode(key)
            output_key[record['fingerprint']] = key
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
        gwid = self.gateway_id()
        gwuuid = self.gwuuid()
        if gwid is 'local' or gwuuid is None:
            self.key_generation_status = 'failed-gateway not setup'
            self._generating_key = False
            return
        passphrase = random_string(length=random_int(80, .3))
        expire_date = '5y'
        # if self.debug_mode is True:
        #     logger.warn('Setting GPG key to expire in one day due to debug mode.')
        #     expire_date = '1d'
        input_data = self.gpg.gen_key_input(
            name_email="%s@gw.gpg.yombo.net" % gwuuid,
            name_real="Yombo Gateway",
            name_comment="Created by https://Yombo.net Automation",
            key_type='RSA',
            key_length=4096,
            expire_date=expire_date,
            preferences='SHA512 SHA384 SHA256 SHA224 AES256 AES192 AES CAST5 ZLIB BZIP2 ZIP Uncompressed',
            keyserver='hkp://gpg.nebrwesleyan.edu',
            revoker="1:9C69E1F8A7C39961C223C485BCEAA0E429FA3EF8",
            passphrase=passphrase)

        self.key_generation_status = 'working'
        newkey = yield threads.deferToThread(self.do_generate_key, input_data)
        # print("bb 3: newkey: %s" % newkey)
        # print("bb 3: newkey: %s" % newkey.__dict__)
        # print("bb 3: newkey: %s" % type(newkey))
        self.key_generation_status = 'done'

        if str(newkey) == '':
            logger.error("ERROR: Unable to generate GPG keys.... Is GPG installed and configured? Is it in your path?")
            self._generating_key = False
            raise YomboCritical("Error with python GPG interface.  Is it installed?")

        private_keys = yield self.get_keyring_keys(True)
        newfingerprint = ''

        for existing_key_id, key_data in private_keys.items():
            # print("inspecting key: %s" % existing_key_id)
            if key_data['fingerprint'] == str(newkey):
                newfingerprint = key_data['fingerprint']
                break
        asciiArmoredPublicKey = self.gpg.export_keys(newfingerprint)
        self._Configs.set('gpg', 'fingerprint', newfingerprint)
        secret_file = "%s/etc/gpg/%s.pass" % (self._Atoms.get('working_dir'), newfingerprint)
        # print("saveing pass to : %s" % secret_file)
        yield save_file(secret_file, passphrase)
        secret_file = "%s/etc/gpg/last.pass" % self._Atoms.get('working_dir')
        yield save_file(secret_file, passphrase)
        self.__mypassphrase = passphrase

        self._Configs.set('gpg', 'last_sent_yombo', None)
        self._Configs.set('gpg', 'last_sent_keyserver', None)
        self._Configs.set('gpg', 'last_received_keyserver', None)

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
        # mykey['publickey'] = asciiArmoredPublicKey
        # mykey['notes'] = 'Autogenerated.'
        # mykey['have_private'] = 1

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
        #         if data['']

        if key is None:
            return

        if 'privatekey' in key:
            del key['privatekey']
        if 'passphrase' in key:
            del key['passphrase']
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
        if in_text_search.startswith(b'-----BEGIN PGP MESSAGE-----'):
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
        if in_text.startswith('-----BEGIN PGP MESSAGE-----'):
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
            raise YomboWarning("Unable to encrypt string. Error 2.: %s" % e)

    def _gpg_encrypt(self, data, destination):
        return self.gpg.encrypt(data, destination)

    @inlineCallbacks
    def decrypt(self, in_text, unicode=None):
        """
        Decrypt a PGP / GPG ascii armor text.  If passed in string/text is not detected as encrypted,
        will simply return the input.

        #TODO: parse STDERR to make sure the key id is ours. Validates trust.

        :param in_text: Ascii armored encoded text.
        :type in_text: string
        :return: Decoded string.
        :rtype: string
        :raises: YomboException - If decoding failed.
        """
        if in_text.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
            verify = yield self.verify_asymmetric(in_text)
            return verify
        elif in_text.startswith('-----BEGIN PGP MESSAGE-----'):
            try:
                output = yield threads.deferToThread(self._gpg_decrypt, in_text)
                if unicode is False:
                    return output.data
                return bytes_to_unicode(output.data)
            except Exception as e:
                raise YomboWarning("Unable to decrypt string. Reason: {e}", e)
        return in_text

    def _gpg_decrypt(self, data):
        return self.gpg.decrypt(data, passphrase=self.__mypassphrase)

    def sign(self, in_text, asciiarmor=True):
        """
        Signs in_text and returns the signature.
        """
        #cache the gpg/pgp key locally.
        if type(in_text) is str or type(in_text) is str:
            try:
                signed = self.gpg.sign(in_text, fingerprint=self.myfingerprint(), clearsign=asciiarmor)
                return signed.data
            except Exception as e:
                raise YomboWarning("Error with GPG system. Unable to sign your message: {e}", e=e)
        return False

    def verify_asymmetric(self, in_text):
        """
        Verifys a signature. Returns the data if valid, otherwise False.
        """
        if type(in_text) is str and in_text.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
            try:
                verified = self.gpg.verify(in_text)
                if verified.status == "signature valid":
                    if verified.stderr.find('TRUST_ULTIMATE') > 0:
                        pass
                    elif verified.stderr.find('TRUST_FULLY') > 0:
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
        u_type = type(b''.decode('utf8'))
        if isinstance(data, u_type):
            return data.encode('utf8')
        return data

    def aes_pad(self, s):
        return s + (self.aes_blocksize - len(s) % self.aes_blocksize) * self.aes_str_to_bytes(chr(self.aes_blocksize - len(s) % self.aes_blocksize))

    @staticmethod
    def aes_unpad(s):
        return s[:-ord(s[len(s)-1:])]

    @inlineCallbacks
    def encrypt_aes(self, key, raw):
        """
        Encrypt something using AES 256 (very strong).

        Modified from: https://gist.github.com/mguezuraga/257a662a51dcde53a267e838e4d387cd

        :param key: A password
        :type key: string
        :param data: Any type of data can be encrypted. Text, binary.
        :return: String containing the encrypted content.
        """
        key = hashlib.sha256(key.encode('utf-8')).digest()
        raw = self.aes_pad(self.aes_str_to_bytes(raw))
        results = yield threads.deferToThread(self._encrypt_aes, key, raw)
        return results

    def _encrypt_aes(self, key, raw):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return iv + cipher.encrypt(raw)
        # return base64.b85encode(iv + cipher.encrypt(raw)).decode('utf-8')

    @inlineCallbacks
    def decrypt_aes(self, key, enc):
        key = hashlib.sha256(key.encode('utf-8')).digest()
        # enc = base64.b85decode(enc)
        results = yield threads.deferToThread(self._decrypt_aes, key, enc)
        data = self.aes_unpad(results)
        return data

    def _decrypt_aes(self, key, enc):
        iv = enc[:AES.block_size]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        results = cipher.decrypt(enc[AES.block_size:])
        try:
            results = results.decode('utf-8')
        except:
            pass
        return results
