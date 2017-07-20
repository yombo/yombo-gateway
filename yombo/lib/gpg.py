# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This library handles encrypting and decrypting content. This library allows data at rest to be encrypted, which
means any passwords or sensitive data will be encrypted before it is saved to disk. This library doesn't
attempt to manage data in memory or saved in a swap file.

The gateway starts up, any variables that are encryptes (such as passwords), we passed to this library for
decryption. A decrypted version of the data is stored in memory. This allows modules to access the data as needed.

It's important to note that any module within the Yombo system will have access to this data, unencumbered.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""

# Import python libraries
import yombo.ext.gnupg as gnupg
# import os
from subprocess import Popen, PIPE
import base64
from Crypto import Random
from Crypto.Cipher import AES
import hashlib

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from twisted.internet import reactor, threads

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboCritical
from yombo.core.library import YomboLibrary
from yombo.utils import random_string

from yombo.core.log import get_logger
logger = get_logger('library.gpg')

class GPG(YomboLibrary):
    """
    Manage all GPG functions.
    """
    def _init_(self, **kwargs):
        """
        Get the GnuPG subsystem up and loaded.
        """
        self.aes_blocksize = 32
        self._key_generation_status = {}

        self.gpg = gnupg.GPG(gnupghome="usr/etc/gpg")
        self.sync_keyring_to_db()

        self.gwid = self._Configs.get2("core", "gwid", None, False)
        self.gwuuid = self._Configs.get2("core", "gwuuid", None, False)
        self.mykeyid = self._Configs.get2('gpg', 'keyid', None, False)
        self.mykeyascii = self._Configs.get2('gpg', 'keyascii', None, False)

        # self.initDefer = Deferred()
        # self._done_init()
        # return self.initDefer

#    @inlineCallbacks
    def _load_(self, **kwargs):
        """
        Get the root cert from database and make sure it's in our public keyring.
        """
        self._AMQPLibrary = self._Libraries['AMQPYombo']

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
        pass

    def _unload_(self, **kwargs):
        """
        Do nothing
        """
        pass

    def _done_init(self):
        self.initDefer.callback(10)
    #
    # def _configuration_set_(self, **kwargs):
    #     """
    #     Receive configuruation updates and adjust as needed.
    #
    #     :param kwargs: section, option(key), value
    #     :return:
    #     """
    #     section = kwargs['section']
    #     option = kwargs['option']
    #     value = kwargs['value']
    #
    #     if section == 'core':
    #         if option == 'gwid':
    #             self.gwid = value
    #         if option == 'gwuuid':
    #             self.gwuuid = value

    ##########################
    #### Key management  #####
    ##########################
    @inlineCallbacks
    def sync_keyring_to_db(self):
        """
        Adds any keys found in the GPG keyring to the Yombo Database

        :return:
        """
        logger.debug("syncing gpg keys into db")
        self.local_db = self._Libraries['localdb']

        db_keys = yield self.local_db.get_gpg_key()
        gpg_public_keys = yield self.gpg.list_keys()
        gpg_private_keys = yield self.gpg.list_keys(True)

        gpg_public_keys = self._format_list_keys(gpg_public_keys)
        gpg_private_keys = self._format_list_keys(gpg_private_keys)

        logger.debug("db_keys: {db_keys}", db_keys=db_keys)
        logger.debug("gpg_public_keys: {gpg_keys}", gpg_keys=gpg_public_keys)
        logger.debug("gpg_private_keys: {gpg_keys}", gpg_keys=gpg_private_keys)

        for fingerprint, data in gpg_public_keys.items():
            if fingerprint not in db_keys:
                if int(gpg_public_keys[fingerprint]['length']) < 2048:
                    logger.error("Not adding key ({length}) due to length being less then 2048. Key is unusable", length=gpg_public_keys[fingerprint]['length'])
                else:
                    data['publickey'] = self.gpg.export_keys(data['fingerprint'])
                    data['notes'] = _('GPG key loaded from keyring')
                    if data['fingerprint'] in gpg_private_keys:
                        data['have_private'] = 1
                    else:
                        data['have_private'] = 0
                    logger.debug("Adding key to keyring: {key}", key=data)
                    yield self.local_db.insert_gpg_key(data)

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
                'expires' : record['expires'],
                'sigs' : record['sigs'],
                'subkeys' : record['subkeys'],
                'length' : record['length'],
                'ownertrust' : record['ownertrust'],
                'algo' : record['algo'],
                'created' : record['date'],
                'trust' : record['trust'],
                'type' : record['type'],
                'uids' : record['uids'],
            }
            variables[record['fingerprint'].encode('utf-8')] = key
        return variables
#[{'dummy': u'', 'keyid': u'CDAADDFAA405F78F', 'expires': u'1495090800', 'sigs': {u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>': []}, 'subkeys': [], 'length': u'4096',
#  'ownertrust': u'u', 'algo': u'1', 'fingerprint': u'F7ADD4CD09A0DC9CC5F63B5ACDAADDFAA405F78F', 'date': u'1463636545', 'trust': u'u', 'type': u'pub',
#  'uids': [u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>']},

    def generate_key_status(self, request_id):
        return self._key_generation_status[request_id]

    @inlineCallbacks
    def generate_key(self, request_id = None):
        """
        Generates a new GPG key pair. Updates yombo.ini and marks it to be sent when gateway conencts to server
        again.
        """
        if self.gwid is None or self.gwuuid is None:
            self._key_generation_status[request_id] = 'failed-gateway not setup'
            return
        input_data = self.gpg.gen_key_input(
            name_email=self.gwuuid() + "@yombo.net",
            name_real="Yombo Gateway",
            name_comment="gw_" + self.gwuuid(),
            key_type='RSA',
            key_length=2048,
            expire_date='5y')

        if request_id is None:
            request_id = random_string(length=16)
        self._key_generation_status[request_id] = 'working'
        newkey = yield self.gpg.gen_key(input_data)
        self._key_generation_status[request_id] = 'done'

        print("newkey!!!!!! ====")
        print(format(newkey))
        print("request id =")
        print(request_id)
        if newkey == '':
            print("\n\rERROR: Unable to generate GPG keys.... Is GPG installed and configured? Is it in your path?\n\r")
            raise YomboCritical("Error with python GPG interface.  Is it installed?")

        private_keys = self.gpg.list_keys(True)
        keyid = ''

        for key in private_keys:
            if str(key['fingerprint']) == str(newkey):
                keyid=key['keyid']
        asciiArmoredPublicKey = self.gpg.export_keys(keyid)

        gpg_keys = yield self.gpg.list_keys(keyid)
        keys = self._format_list_keys(gpg_keys)

        print("keys: %s" % type(keys))
        print("keys: %s" % keys)

        data = keys[format(newkey)]
        data['publickey'] = asciiArmoredPublicKey
        data['notes'] = 'Key generated during wizard setup.'
        data['have_private'] = 1
        yield self.local_db.insert_gpg_key(data)

        # print "new generated key: %s" % data
        #
        # print "New keys (public and private) have been saved to key ring."
        returnValue({'keyid': keyid, 'keypublicascii': asciiArmoredPublicKey})

    def get_key(self, keyid):
        asciiArmoredPublicKey = self.gpg.export_keys(keyid)
        return asciiArmoredPublicKey

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
        return self.gpg.decrypt(data)

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

