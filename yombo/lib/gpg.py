# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `GPG @ Module Development <https://docs.yombo.net/Libraries/GPG>`_


This library handles encrypting and decrypting content. This library allows data at rest to be encrypted, which
means any passwords or sensitive data will be encrypted before it is saved to disk. This library doesn't
attempt to manage data in memory or saved in a swap file.

The gateway starts up, any variables that are encryptes (such as passwords), we passed to this library for
decryption. A decrypted version of the data is stored in memory. This allows modules to access the data as needed.

It's important to note that any module within the Yombo system will have access to this data, unencumbered.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://docs.yombo.net/gateway/html/current/_modules/yombo/lib/gpg.html>`_
"""

# Import python libraries
import yombo.ext.gnupg as gnupg
import os.path
from subprocess import Popen, PIPE
from Crypto import Random
from Crypto.Cipher import AES
import hashlib

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet import threads

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.utils import random_string, bytes_to_unicode, read_file, save_file

from yombo.core.log import get_logger
logger = get_logger('library.gpg')

class GPG(YomboLibrary):
    """
    Manage all GPG functions.
    """
    @property
    def public_key(self):
        # print("my keys:%s " % self.__gpg_keys)
        return self.__gpg_keys[self.mykeyid()]['publickey']

    @public_key.setter
    def public_key(self, val):
        return

    @property
    def public_key_id(self):
        # print("my keys:%s " % self.__gpg_keys)
        return self.__gpg_keys[self.mykeyid()]['keyid']

    @public_key_id.setter
    def public_key_id(self, val):
        return

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Get the GnuPG subsystem up and loaded.
        """
        self.aes_blocksize = 32
        self.key_generation_status = None
        self._generating_key = False
        self.__gpg_keys = {}
        self._generating_key_deferred = None

        self.gpg = gnupg.GPG(gnupghome="usr/etc/gpg")
        self.gateway_id = self._Configs.get2('core', 'gwid', 'local', False)
        self.gwuuid = self._Configs.get2('core', 'gwuuid', None, False)
        self.mykeyid = self._Configs.get2('gpg', 'keyid', None, False)
        # self.mypublickey = self._Configs.get2('gpg', 'publickey', None, False)
        # self.__myprivatekey = self._Configs.get2('gpg', 'privatekey', None, False)
        self.__mypassphrase = None  # will be loaded by sync_keyring_to_db() calls

        if self._Loader.operating_mode == 'run':
            yield self.sync_keyring_to_db()
            yield self.validate_gpg_ready()

    def _start_(self, **kwargs):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        self.remote_get_root_key()
        pass

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
    def load_passphrase(self, keyid=None):
        if keyid is None:
            keyid = self.mykeyid()
        if keyid is not None:
            secret_file = "%s/usr/etc/gpg/%s.pass" % (self._Atoms.get('yombo.path'), keyid)
            if os.path.exists(secret_file):
                phrase = yield read_file(secret_file)
                if keyid == self.mykeyid():
                    self.__mypassphrase = phrase
                return bytes_to_unicode(phrase)
        return None

    @inlineCallbacks
    def validate_gpg_ready(self):
        valid = True
        if self.mykeyid is None:
            valid = False
            logger.warn("No GPG keyid found! Unable to process GPG items.")
        if self.__mypassphrase is None:
            valid = False
            logger.warn("No GPG passphrase found! Unable to process GPG items.")
        if valid is False:
            yield self.generate_key()

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
        gpg_public_keys = yield self.gpg.list_keys()
        gpg_private_keys = yield self.gpg.list_keys(True)
        # logger.debug("1gpg_public_keys: {gpg_keys}", gpg_keys=gpg_public_keys)
        # logger.debug("1gpg_private_keys: {gpg_keys}", gpg_keys=gpg_private_keys)

        gpg_public_keys = self._format_list_keys(gpg_public_keys)
        gpg_private_keys = self._format_list_keys(gpg_private_keys)

        # logger.debug("2gpg_public_keys: {gpg_keys}", gpg_keys=gpg_public_keys)
        # logger.debug("2gpg_private_keys: {gpg_keys}", gpg_keys=gpg_private_keys)

        for fingerprint in list(gpg_public_keys):
            data = gpg_public_keys[fingerprint]
            if int(gpg_public_keys[fingerprint]['length']) < 2048:
                logger.error("Not adding key ({length}) due to length being less then 2048. Key is unusable",
                             length=gpg_public_keys[fingerprint]['length'])
                continue
            data['publickey'] = self.gpg.export_keys(data['fingerprint'])
            data['notes'] = 'GPG key loaded from keyring'
            if data['fingerprint'] in gpg_private_keys:
                data['have_private'] = 1
            else:
                data['have_private'] = 0
            if data['have_private'] == 1:
                try:
                    passphrase = yield self.load_passphrase(data['keyid'])
                    data['privatekey'] = self.gpg.export_keys(data['fingerprint'],
                                                              secret=True,
                                                              passphrase=passphrase,
                                                              expect_passphrase=True)
                    data['passphrase'] = passphrase
                except Exception as e:
                    data['have_private'] = 0
            else:
                try:
                    data['privatekey'] = self.gpg.export_keys(data['fingerprint'],
                                                              secret=True,
                                                              expect_passphrase=False)
                except Exception as e:
                    data['have_private'] = 0

            # sync to local cache
            self.__gpg_keys[data['keyid']] = data

            # sync to database
            if fingerprint not in db_keys:
                yield self._LocalDB.insert_gpg_key(data)
            else:
                del db_keys[fingerprint]
            # del gpg_public_keys[fingerprint]

        logger.debug("db_keys: {gpg_keys}", gpg_keys=db_keys.keys())
        logger.debug("gpg_public_keys: {gpg_keys}", gpg_keys=gpg_public_keys.keys())

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
        if message['key_type'] == "root":
            self.add_key(message['fingerprint'], message['public_key'], 6)
        else:
            self.add_key(message['fingerprint'], message['public_key'])

    def add_key(self, fingerprint, public_key, trust_level=3):
        """
        Used as a shortcut to call import_to_keyring and sync_keyring_to_db
        :param new_key:
        :param trust_level:
        :return:
        """
        self.import_to_keyring(fingerprint, public_key, trust_level)
        self.sync_keyring_to_db()

    @inlineCallbacks
    def import_to_keyring(self, fingerprint, public_key, trust_level=3):
        """
        Imports a new key. First, it checks if we already have the key imported, if so, we set the trust level.

        If the key isn't in the keyring, it'll add it and set the trust.
        """
        existing_keys = yield self.gpg.list_keys()
        key_has_been_found = False
        for have_key in existing_keys:
          if have_key['fingerprint'] == fingerprint:
#              logger.debug("key (%d) trust:: %s", trustLevel, key['ownertrust'])
              key_has_been_found = True
              if trust_level == 2 and have_key['ownertrust'] != 'q':
                self.set_trust_level(fingerprint, trust_level)
              elif trust_level == 3 and have_key['ownertrust'] != 'n':
                self.set_trust_level(fingerprint, trust_level)
              elif trust_level == 4 and have_key['ownertrust'] != 'm':
                self.set_trust_level(fingerprint, trust_level)
              elif trust_level == 5 and have_key['ownertrust'] != 'f':
                self.set_trust_level(fingerprint, trust_level)
              elif trust_level == 6 and have_key['ownertrust'] != 'u':
                self.set_trust_level(fingerprint, trust_level)
              break

        if key_has_been_found == False:  # If not found, lets add the key to gpg keyring
            importResult = yield self._add_to_keyring(public_key)
            if importResult['status'] != "Failed":
                self.set_trust_level(fingerprint, trust_level)

    @inlineCallbacks
    def set_trust_level(self, fingerprint, trust_level = 5):
        """
        Sets the trust of a key.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        p = yield Popen(["gpg --import-ownertrust --homedir usr/etc/gpg"], shell=True, stdin=PIPE, stdout=PIPE, close_fds=True)
        (child_stdout, child_stdin) = (p.stdout, p.stdin)
#        logger.info("%s:%d:\n" % (fingerprint, trustLevel))
        child_stdin.write("%s:%d:\n" % (fingerprint, trust_level))
        child_stdin.close()
        result = child_stdout.read()
        logger.info("GPG Trust change: {result}", result=result)

    def check_key_trust(self, keyid):
        """
        Returns the trust level of a given keyid

        :param keyid: keyID to check.
        :type keyid: string
        :return: Level of trust.
        :rtype: string
        """
        keys = self.gpg.list_keys()
        for key in keys:
          if keyid == key['keyid']:
              return key['ownertrust']

    def _add_to_keyring(self, key_to_add):
        """
        Helper function to actually add the keyring.

        :param key_to_add:
        :return:
        """
        importResults = self.gpg.import_keys(key_to_add)
        results = importResults.results
#        logger.debug("Result size: %s", len(results) )
        if (len(results) == 1):
            results = results[0]
            results['status'] = results['status'].replace("\n", "")
        else:
            results = {'status' : 'Failed'}
        return results

    ##########################
    ###  Helper Functions  ###
    ##########################

    def _format_list_keys(self, keys):
        """
        Formats the results of gnupg.list_keys() into a more usable form.
        :param keys:
        :return:
        """
        variables = {}
        # if isinstance(keys, dict):
        #     keys = [keys]

        for record in keys:
            # print "list keys: %s" % record
            uid = record['uids'][0]
            key_comment = uid[uid.find("(")+1:uid.find(")")]
            key = {
                'endpoint': key_comment,
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
            variables[record['fingerprint']] = key
        return variables
#[{'dummy': u'', 'keyid': u'CDAADDFAA405F78F', 'expires': u'1495090800', 'sigs': {u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>': []}, 'subkeys': [], 'length': u'4096',
#  'ownertrust': u'u', 'algo': u'1', 'fingerprint': u'F7ADD4CD09A0DC9CC5F63B5ACDAADDFAA405F78F', 'date': u'1463636545', 'trust': u'u', 'type': u'pub',
#  'uids': [u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>']},

    @inlineCallbacks
    def generate_key(self):
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
        passphrase = random_string(length=125)
        input_data = self.gpg.gen_key_input(
            name_email=gwuuid + "@yombo.net",
            name_real="Yombo Gateway",
            name_comment="gw_" + gwuuid,
            key_type='RSA',
            key_length=4096,
            expire_date='30y',
            passphrase=passphrase)

        self.key_generation_status = 'working'
        newkey = yield threads.deferToThread(self._gen_key, input_data)
        # print("bb 3: newkey: %s" % newkey)
        # print("bb 3: newkey: %s" % newkey.__dict__)
        # print("bb 3: newkey: %s" % type(newkey))
        self.key_generation_status = 'done'

        if newkey == '':
            logger.error("ERROR: Unable to generate GPG keys.... Is GPG installed and configured? Is it in your path?")
            self._generating_key = False
            raise YomboCritical("Error with python GPG interface.  Is it installed?")

        private_keys = self.gpg.list_keys(True)
        keyid = ''

        for key in private_keys:
            if str(key['fingerprint']) == str(newkey):
                keyid = key['keyid']
                # fingerprint = key['fingerprint']
        asciiArmoredPublicKey = self.gpg.export_keys(keyid)
        self._Configs.set('gpg', 'keyid', keyid)
        secret_file = "%s/usr/etc/gpg/%s.pass" % (self._Atoms.get('yombo.path'), keyid)
        yield save_file(secret_file, passphrase)
        self.__mypassphrase = passphrase

        gpg_keys = yield self.gpg.list_keys(keyid)
        keys = self._format_list_keys(gpg_keys)

        print("keys: %s" % type(keys))
        print("newkey1: %s" % newkey)
        print("newkey2: %s" % str(newkey))
        print("keys: %s" % keys)

        data = keys[str(newkey)]
        data['publickey'] = asciiArmoredPublicKey
        data['notes'] = 'Key generated during wizard setup.'
        data['have_private'] = 1
        yield self.sync_keyring_to_db()

        self._generating_key = False

        self._Configs.set('gpg', 'keyid', keyid)
        if self._generating_key_deferred is not None and self._generating_key_deferred.called is False:
            self._generating_key_deferred.callback(1)

        return {'keyid': keyid, 'keypublicascii': asciiArmoredPublicKey}

    def _gen_key(self, input_data):
        logger.warn("Generating new system GPG key. This can take a little while on slower systems.")
        newkey = self.gpg.gen_key(input_data)
        logger.info("Done generating key.")
        return newkey

    def get_key(self, keyid=None):
        if keyid is None:
            keyid = self.mykeyid()
        key = None
        if keyid in self.__gpg_keys:
            key = self.__gpg_keys[keyid].copy()
        # else:
        #     for key_id, data in self.__gpg_keys.items():
        #         if data['']

        if key is None:
            return

        if 'privatekey' in key:
            del key['privatekey']
        if 'passphrase' in key:
            del key['passphrase']
        return key


    # def get_key(self, keyid):
    #     asciiArmoredPublicKey = self.gpg.export_keys(keyid)
    #     return asciiArmoredPublicKey

    def display_encrypted(self, in_text):
        """
        Makes an input field friend version of an input. If encrypted, returns
        "-----ENCRYPTED DATA-----", otherwise returns the text unchanged.

        :param in_text:
        :return:
        """
        if in_text.startswith('-----BEGIN PGP MESSAGE-----'):
            return "-----ENCRYPTED DATA-----"
        else:
            return in_text

    ###########################################
    ###  Encrypt / Decrypt / Sign / Verify  ###
    ###########################################
    @inlineCallbacks
    def encrypt(self, in_text, destination=None, ):
        """
        Encrypt text and output as ascii armor text.

        :param in_text: Plain text to encrypt.
        :type in_text: string
        :param destination: Key fingerprint of the destination.
        :type destination: string
        :return: Ascii armored text.
        :rtype: string
        :raises: YomboException - If encryption failed.
        """
        if in_text.startswith('-----BEGIN PGP MESSAGE-----'):
            returnValue(in_text)

        if destination is None:
            destination = self.mykeyid()

        try:
            # output = self.gpg.encrypt(in_text, destination, sign=self.mykeyid())
            output = yield threads.deferToThread(self._gpg_encrypt, in_text, destination)
            # output = self.gpg.encrypt(in_text, destination)
            if output.status != "encryption ok":
                raise YomboWarning("Unable to encrypt string. Error 1.")
            returnValue(output.data)
        except Exception as e:
            raise YomboWarning("Unable to encrypt string. Error 2.: %s" % e)

    def _gpg_encrypt(self, data, destination):
        return self.gpg.encrypt(data, destination)

    @inlineCallbacks
    def decrypt(self, in_text):
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
            returnValue(verify)
        elif in_text.startswith('-----BEGIN PGP MESSAGE-----'):
            try:
                output = yield threads.deferToThread(self._gpg_decrypt, in_text)
                returnValue(output.data)
            except Exception as e:
                raise YomboWarning("Unable to decrypt string. Reason: {e}", e)
        returnValue(in_text)

    def _gpg_decrypt(self, data):
        return self.gpg.decrypt(data, passphrase=self.__mypassphrase)

    def sign(self, in_text, asciiarmor=True):
        """
        Signs in_text and returns the signature.
        """
        #cache the gpg/pgp key locally.
        if type(in_text) is str or type(in_text) is str:
            try:
                signed = self.gpg.sign(in_text, keyid=self.mykeyid(), clearsign=asciiarmor)
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
    # Ask yombo service for keyID of gateway
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
            return results
        except:
            return results

############ OLD Stuff
    #
    # def getKey(self, keyHash):
    #     d = self.dbpool.select('gpg_keys', ['id', 'keyid', 'keyhash', 'public_key', 'root_key_id', 'root_signed_time', 'expire_time', 'revoked'] , "WHERE keyhash=%s", keyHash)
    #     def dbResults(data):
    #       for key in data:
    #         if key['revoked']:
    #           break
    #         self.gpgRoot = key
    #         self.importKey(key, 6)
    #     d.addCallback(dbResults)
    #
    # def findKey(self, search):
    #     d = self.dbpool.select('gpg_keys', ['id', 'keyid', 'keyhash', 'public_key', 'revoked'] , "WHERE keyhash=%s or keyid=", keyHash)
    #     def dbResults(data):
    #       for key in data:
    #         if key['revoked']:
    #           break
    #         self.gpgRoot = key
    #         self.importKey(key, 6)
    #     d.addCallback(dbResults)

### Stuff from helps. For reference
# def pgpEncrypt(inText, destination):
#     """
#     Encrypt text and output as ascii armor text.
#
#     :param inText: Plain text to encrypt.
#     :type inText: string
#     :param destination: Key fingerprint of the destination.
#     :type destination: string
#     :return: Ascii armored text.
#     :rtype: string
#     :raises: Exception - If encryption failed.
#     """
#     if type(inText) is unicode and inText.startswith('-----BEGIN PGP MESSAGE-----'):
#         if not hasattr(pgpEncrypt, 'gpgkeyid'):
#             pgpEncrypt.gpgkeyid = self._Configs.get('core', 'gpgkeyid')
#             pgpEncrypt.gpg = gnupg.GPG()
#
#         try:
#             output = pgpEncrypt.gpg.encrypt(inText, destination, sign=pgpEncrypt.gpgkeyid )
#             if output.status != "encryption ok":
#                 raise Exception("Unable to encrypt string.")
#             return output.data
#         except:
#             raise Exception("Unable to encrypt string.")
#     return inText
#
# def pgpDecrypt(inText):
#     """
#     Decrypt a PGP / GPG ascii armor text.  If passed in string/text is not detected as encrypted,
#     will simply return the input.
#
#     #TODO: parse STDERR to make sure the key id is ours. Validates trust.
#
#     :param inText: Ascii armored encoded text.
#     :type inText: string
#     :return: Decoded string.
#     :rtype: string
#     :raises: Exception - If decoding failed.
#     """
#
#     if type(inText) is unicode and inText.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
#         return pgpVerify(inText)
#     elif type(inText) is unicode and inText.startswith('-----BEGIN PGP MESSAGE-----'):
#         if not hasattr(pgpDecrypt, 'gpgkeyid'):
#             pgpDecrypt.gpgkeyid = self._Configs.get('core', 'gpgkeyid')
#             pgpDecrypt.gpg = gnupg.GPG()
#         try:
#             out = pgpDecrypt.gpg.decrypt(inText)
#             return out.data
#         except:
#             raise Exception("Unable to decrypt string.")
#
#     return inText
#
#
# def pgpSign(inText, asciiarmor=True):
#     """
#     Signs inText and returns the signature.
#     """
#     #cache the gpg/pgp key locally.
#     if type(inText) is unicode or type(inText) is str:
#         if not hasattr(pgpSign, 'gpg'):
#             pgpSign.gpg = gnupg.GPG()
#
#         if not hasattr(pgpSign, 'gpgkeyid'):
#             pgpSign.gpgkeyid = self._Configs.get('core', 'gpgkeyid')
#             pgpSign.gpg = gnupg.GPG()
#
#         try:
#             signed = pgpSign.gpg.sign(inText, keyid=pgpSign.gpgkeyid, clearsign=asciiarmor)
#             return signed.data
#         except:
#             raise Exception("Error with GPG system. Unable to sign your message. 101b")
#     return False
#
# def pgpVerify(inText):
#     """
#     Verifys a signature. Returns the data if valid, otherwise False.
#     """
#     if type(inText) is unicode or type(inText) is str:
#         if not hasattr(pgpVerify, 'gpg'):
#             pgpVerify.gpg = gnupg.GPG()
#
#         try:
#             verified = pgpVerify.gpg.verify(inText)
#             if verified.status == "signature valid":
#                 if verified.stderr.find('TRUST_ULTIMATE') > 0:
#                     pass
#                 elif verified.stderr.find('TRUST_FULLY') > 0:
#                     pass
#                 else:
#                     raise Exception("Encryption not from trusted source!")
#                 out = pgpVerify.gpg.decrypt(inText)
#                 return out.data
#             else:
#                 return False
#         except:
#             raise Exception("Error with GPG system. Unable to verify signed text. 101a")
#     return False
#
# def pgpValidateDest(destination):
#     """
#     Validate that we have a key for the given destination.  If not, try to
#     fetch the given key and it to the key ring. Then revalidate.
#
#     .. todo::
#
#        This function is mostly a place holder. Function doesn't work or return anything useful.
#
#     :param destination: The destination key to check for.
#     :type destination: string
#     :return: True if destination is valid, otherwise false.
#     :rtype: bool
#     """
# # Pseudocode
# #
# # Determine if gateway
# # Ask yombo service for keyID of gateway
# #   Can just ask keys.yombo.net for it since gateway
# #   may have multiple keys - which one to use?
# # Wait for yombo service to give us the key id
# # Ask gnupg to fetch the key
# # Retyrn true if good.
#     pass
#
# def pgpDownloadRoot():
#     """
#     Fetch the latest Yombo root PGP/GPG keyID. Then download it from
#     keys.yombo.net. After, mark the key as fully trusted.
#     """
#     from twisted.web.client import getPage
#
#     environment = self._Configs.get("server", 'environment', "production")
#     uri = ''
#     if self._Configs.get("server", 'gpgidtxt', "") != "":
#         uri = "https://%s/" % self._Configs.get("server", 'gpgidtxt')
#     else:
#         if(environment == "production"):
#             uri = "https://yombo.net/gpgid.txt"
#         elif (environment == "staging"):
#             uri = "https://wwwstg.yombo.net/gpgid.txt"
#         elif (environment == "development"):
#             uri = "https://wwwdev.yombo.net/gpgid.txt"
#         else:
#             uri = "https://yombo.net/gpgid.txt"
#
#     uri = "https://yombo.net/gpgid.txt"
#     deferred = getPage(uri)
#     deferred.addCallback(pgpCheckRoot)
#
# def pgpCheckRoot(result):
#     """
#     A callback for :py:meth:`pgpDownloadRoot`. Now that we have Yombo Root
#     keyid, lets first check to see if we have already downloaded it this
#     session.  If we have, pass. Otherwise, download it and the "fully"
#     trust the cert.
#
#     :param result: Result of pgpDownloadRoot is the keyID.
#     :type result: string
#     """
#     if not hasattr(pgpCheckRoot, 'gpg'):
#         pgpCheckRoot.gpg = gnupg.GPG()
#         pgpCheckRoot.previousID = ""
#
#     rootID = result.strip()
#
#     if rootID == pgpCheckRoot.previousID:
#       return
#     else:
#        pgpCheckRoot.previousID = rootID
#
#     keys = pgpCheckRoot.gpg.list_keys()
#
#     haveRootKey = False
#
#     for key in keys:
#       if key['uids'][0][0:12] == "Yombo (Root)":
#         if key['keyid'] != rootID:
#           pgpCheckRoot.previousID = key['keyid']
#         else:
#           logger.debug("key ({key}) trust:: {ownertrust}", key=key['keyid'], ownertrust=key['ownertrust'])
#           haveRootKey = True
#           if key['ownertrust'] == 'u':
#             pass
#           elif key['ownertrust'] == 'f':
#             pass
#           else:
#             pgpTrustKey(key['fingerprint'])
#         break
#
#     if haveRootKey == False:
#         importResult = pgpCheckRoot.gpg.recv_keys("keys.yombo.net", rootID)
#         logger.debug("Yombo Root key import result: {importResults}", importResult=importResult)
#         pgpTrustKey(key['fingerprint'])
#     logger.debug("Yombo Root key: {haveRootKey}", haveRootKey=haveRootKey)
#
# def pgpCheckKeyTrust(fingerprint):
#     """
#     Returns the trust level of a given fingerprint.
#
#     :param fingerprint: Fingerprint of keyID to check.
#     :type fingerprint: string
#     :return: Level of trust.
#     :rtype: string
#
#     .. todo::
#
#        NOT DONE!!!  Does not work!!!
#     """
#     if not hasattr(pgpCheckKeyTrust, 'gpg'):
#         pgpCheckKeyTrust.gpg = gnupg.GPG()
#
#     keys = pgpCheckKeyTrust.gpg.list_keys()
#
#     logger.info("my keys: {keys}", keys=keys)
# #    return
# #    for key in keys:
# #      if key['uids'][0][0:12] == "Yombo (Root)":
# #        if key['keyid'] != rootID:
# #          pgpCheckKeyTrust.previousID = key['keyid']
# #        else:
# #          logger.info("4444")
# #          logger.info("Root key %s", key['keyid'])
# #          haveRootKey = True
# #          if key['trust'] == 'u':
# #            trustRootKey = True
# #          else:
# #            pgpTrustKey(key['fingerprint'])
# #        break
#
#
# def pgpFetchKey(searchKey):
#     if not hasattr(pgpFetchKey, 'gpg'):
#         pgpFetchKey.gpg = gnupg.GPG()
#
#     importResult = pgpFetchKey.gpg.recv_keys("keys.yombo.net", searchKey)
#     logger.debug("GPG Import result for {searchKey}: {importResult}", searchKey=searchKey, importResult=importResult)
#
# def pgpTrustKey(fingerprint, trustLevel = 5):
#     """
#     Sets the trust of a key.
#     #TODO: This function is blocking! Adjust to non-blocking. See below.
#     """
#     p = Popen(["gpg --import-ownertrust"], shell=True, stdin=PIPE, stdout=PIPE, close_fds=True)
#     (child_stdout, child_stdin) = (p.stdout, p.stdin)
#     child_stdin.write("%s:%d:\n" % (fingerprint, trustLevel))
#     child_stdin.close()
#
#     result = child_stdout.read()
#     logger.info("GPG Trust change: {result}", result=result)

