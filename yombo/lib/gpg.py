# cython: embedsignature=True
"""
Various pycrypto tools, if available, to create strong random strings.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""

# Import python libraries
import gnupg
import os
from subprocess import Popen, PIPE

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
#from yombo.core.message import Message

from yombo.core.log import get_logger
logger = get_logger('library.gpg')

class GPG(YomboLibrary):
    """
    Manage all GPG functions.
    """
    def _init_(self, loader):
        """
        Get the GnuPG subsystem up and loaded.
        """
        self.initDefer = Deferred()
        self.mykeyid = self._Configs.get('gpg', 'gpgkeyid')
        self.gpg = gnupg.GPG(homedir="usr/etc/gpg")
        logger.debug("syncing gpg keys into db")
        self.sync_keyring_to_db()
        self._done_init()
        return self.initDefer

#    @inlineCallbacks
    def _load_(self):
        """
        Get the root cert from database and make sure it's in our public keyring.
        """
        self._AMQPLibrary = self._Libraries['AMQPYombo']

        pass

    def _start_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        self.remote_get_root_key()
        pass

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        pass

    def _unload_(self):
        """
        Do nothing
        """
        pass

    def _done_init(self):
        self.initDefer.callback(10)

    def message(self, msg):
        """
        Defined to only catch messages sent to pgp on accident!

        :param message: A yombo message.
        :type message: :ref:`message`
        """
        pass

    ##########################
    #### Key management  #####
    ##########################
    @inlineCallbacks
    def sync_keyring_to_db(self):
        """
        Adds any keys found in the GPG keyring
        :return:
        """
        self.local_db = self._Libraries['localdb']
        db_keys = yield self.local_db.get_gpg_key()
        gpg_keys = yield self.gpg.list_keys()
        gpg_keys = self._format_list_keys(gpg_keys)
        logger.debug("db_keys: {db_keys}", db_keys=db_keys)
        logger.debug("gpg_keys: {gpg_keys}", gpg_keys=gpg_keys)
        for fingerprint, data in gpg_keys.iteritems():
            if fingerprint not in db_keys:
                if int(gpg_keys[fingerprint]['length']) < 2048:
                    logger.error("Not adding key ({length}) due to length being less then 2048. Key is unusable", length=gpg_keys[fingerprint]['length'])
                else:
                    logger.info("Adding key to keyring: {key}", key=data)
                    yield self.local_db.insert_gpg_key(data)

    def remote_get_server_key(self, key_hash):
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        msg = {'key_type': 'server', 'id': key_hash}
        self._AMQPLibrary.send_amqp_message(**self._generate_request_message('gpg_get_key', msg, self.amqp_response_get_key))
        self.import_to_keyring

    def remote_get_root_key(self):
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        msg = {'key_type': 'root'}
        self._AMQPLibrary.send_amqp_message(**self._generate_request_message('gpg_get_key', msg, self.amqp_response_get_key))

    def _generate_request_message(self, request_type, request_content, callback):
        request = {
            "exchange_name": "ysrv.e.gw_config",
            "source"       : "yombo.gateway.lib.gpg",
            "destination"  : "yombo.server.configs",
            "callback" : callback,
            "body": {
              "data_type": "object",
              "request"  : request_content,
            },
            "request_type": request_type,
        }
        return self._AMQPLibrary.generate_request_message(**request)

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
        Imports a new key. First, it checks if we already have the key imports, if so, we set the trust level.

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
        for record in keys:
            uid = record['uids'][0]
            key_comment = uid[uid.find("(")+1:uid.find(")")]
            key = {
                'endpoint': key_comment,
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
            variables[record['fingerprint']] = key
        return variables
#[{'dummy': u'', 'keyid': u'CDAADDFAA405F78F', 'expires': u'1495090800', 'sigs': {u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>': []}, 'subkeys': [], 'length': u'4096',
#  'ownertrust': u'u', 'algo': u'1', 'fingerprint': u'F7ADD4CD09A0DC9CC5F63B5ACDAADDFAA405F78F', 'date': u'1463636545', 'trust': u'u', 'type': u'pub',
#  'uids': [u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>']},




    ###########################################
    ###  Encrypt / Decrypt / Sign / Verify  ###
    ###########################################
    def encrypt_asymmetric(self, in_text, destination):
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
        if type(in_text) is unicode and in_text.startswith('-----BEGIN PGP MESSAGE-----'):
            try:
                output = self.gpg.encrypt(in_text, destination, sign=self.mykeyid)
                if output.status != "encryption ok":
                    raise YomboWarning("Unable to encrypt string.")
                return output.data
            except:
                raise YomboWarning("Unable to encrypt string.")
        return in_text

    def decrypt_asymmetric(self, in_text):
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
        if type(in_text) is unicode and in_text.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
            return self.verify_asymmetric(in_text)
        elif type(in_text) is unicode and in_text.startswith('-----BEGIN PGP MESSAGE-----'):
            try:
                out = self.gpg.decrypt(in_text)
                return out.data
            except:
                raise YomboWarning("Unable to decrypt string.")
        return in_text

    def sign_asymmetric(self, in_text, asciiarmor=True):
        """
        Signs in_text and returns the signature.
        """
        #cache the gpg/pgp key locally.
        if type(in_text) is unicode or type(in_text) is str:
            try:
                signed = self.gpg.sign(in_text, keyid=self.mykeyid, clearsign=asciiarmor)
                return signed.data
            except:
                raise YomboWarning("Error with GPG system. Unable to sign your message. 101b")
        return False

    def verify_asymmetric(self, in_text):
        """
        Verifys a signature. Returns the data if valid, otherwise False.
        """
        if type(in_text) is unicode and in_text.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
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
            except:
                raise YomboWarning("Error with GPG system. Unable to verify signed text. 101a")
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





############ OLD Stuff

    def getKey(self, keyHash):
        d = self.dbpool.select('gpg_keys', ['id', 'keyid', 'keyhash', 'public_key', 'root_key_id', 'root_signed_time', 'expire_time', 'revoked'] , "WHERE keyhash=%s", keyHash)
        def dbResults(data):
          for key in data:
            if key['revoked']:
              break
            self.gpgRoot = key
            self.importKey(key, 6)
        d.addCallback(dbResults)

    def findKey(self, search):
        d = self.dbpool.select('gpg_keys', ['id', 'keyid', 'keyhash', 'public_key', 'revoked'] , "WHERE keyhash=%s or keyid=", keyHash)
        def dbResults(data):
          for key in data:
            if key['revoked']:
              break
            self.gpgRoot = key
            self.importKey(key, 6)
        d.addCallback(dbResults)

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

