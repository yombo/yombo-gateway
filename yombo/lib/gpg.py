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
from yombo.core.helpers import getConfigValue, getComponent
from yombo.core.library import YomboLibrary
from yombo.core.message import Message

from yombo.core.log import getLogger
logger = getLogger('library.gpg')

class GPG(YomboLibrary):
    """
    Manage all GPG functions.
    """
    def _init_(self, loader):
        """
        Get the GnuPG subsystem up and loaded.
        """
        self.initDefer = Deferred()
        self.mykeyid = getConfigValue('gpg', 'gpgkeyid')
        self.gpg = gnupg.GPG(homedir="usr/etc/gpg")
        logger.debug("syncing gpg keys into db")
        self.sync_keyring_to_db()
        return self.initDefer

#    @inlineCallbacks
    def _load_(self):
        """
        Get the root cert from database and make sure it's in our public keyring.
        """

        pass

    def _start_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
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
#        print db_keys
#        print gpg_keys
        for gwuuid, data in gpg_keys.iteritems():
            if gwuuid not in db_keys:
                for gwkey in gpg_keys[gwuuid]['keys']:
                    if int(gpg_keys[gwuuid]['keys'][gwkey]['length']) < 2048:
                        logger.error("Not adding key ({length}) due to length being less then 2048. Key is unusable", length=gpg_keys[gwuuid]['keys'][gwkey]['length'])
                    else:
                        logger.info("Adding key to keyring: {key}", key=gpg_keys[gwuuid]['keys'][gwkey])
                        yield self.local_db.insert_gpg_key(gpg_keys[gwuuid]['keys'][gwkey])
        self.initDefer.callback(10)

    def remote_get_key(self, key_hash):
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        msg = {'keytype': 'server', 'id': key_hash}
        self.AMQPYombo.send_amqp_message(**self._generate_request_message('GPGGetKey', msg, self.amqp_response_get_key))

    def remote_get_root_key(self, key_hash):
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        msg = {'keytype': 'root'}
        self.AMQPYombo.send_amqp_message(**self._generate_request_message('GPGGetKey', msg, self.amqp_response_get_key))


    def amqp_response_get_key(self, deliver, properties, message):
        """
        Receives keys as a response from remote_get_key

        :param deliver:
        :param properties:
        :param message:
        :return:
        """
        logger.warn("deliver: {deliver}, properties: {properties}, message: {message}", deliver=deliver, properties=properties, message=message)

    @inlineCallbacks
    def import_to_keyring(self, new_key, trust_level=3):
        """
        Imports a new key. First, it checks if we already have the key imports, if so, we set the trust level.

        If the key isn't in the keyring, it'll add it and set the trust.
        """
        existing_keys = yield self.gpg.list_keys()
        key_has_been_found = False
        for have_key in existing_keys:
          if have_key['keyid'] == new_key['keyid']:
#              logger.debug("key (%d) trust:: %s", trustLevel, key['ownertrust'])
              key_has_been_found = True
              if trust_level == 2 and have_key['ownertrust'] != 'q':
                self.pgpTrustKey(new_key['keyhash'], trust_level)
              elif trust_level == 3 and have_key['ownertrust'] != 'n':
                self.pgpTrustKey(new_key['keyhash'], trust_level)
              elif trust_level == 4 and have_key['ownertrust'] != 'm':
                self.pgpTrustKey(new_key['keyhash'], trust_level)
              elif trust_level == 5 and have_key['ownertrust'] != 'f':
                self.pgpTrustKey(new_key['keyhash'], trust_level)
              elif trust_level == 6 and have_key['ownertrust'] != 'u':
                self.pgpTrustKey(new_key['keyhash'], trust_level)
              break

        if key_has_been_found == False:  # If not found, lets add the key to gpg keyring
            importResult = yield self._add_to_keyring(new_key['public_key'])
            if importResult['status'] != "Failed":
              self.set_trust_level(new_key['keyhash'], trust_level)
              haveKey = True

    @inlineCallbacks
    def set_trust_level(self, fingerprint, trust_level = 5):
        """
        Sets the trust of a key.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        p = yield Popen(["gpg --import-ownertrust --homedir usr/etc/"], shell=True, stdin=PIPE, stdout=PIPE, close_fds=True)
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
    def _generate_request_message(self, request_type, requestContent, callback):
        request = {
            "exchange_name"  : "ysrv.e.gw_config",
            "source"        : "yombo.gateway.lib.gpg",
            "destination"   : "yombo.server.configs",
            "callback" : callback,
            "body"          : {
              "DataType"        : "Object",
              "Request"         : requestContent,
            },
            "request_type"   : request_type,
        }
        return self.AMQPYombo.generate_request_message(**request)

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
            comment_parts = key_comment.split("_")
            if key_comment not in variables:
                variables[key_comment] = {
                    'endpoint_type': comment_parts[0],
                    'endpoint_id': comment_parts[1],
                    'keys': {},
                }
            key = {
                'endpoint_type': comment_parts[0],
                'endpoint_id': comment_parts[1],
                'key_id': record['keyid'],
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
            variables[key_comment]['keys'][record['fingerprint']] = key
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

