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

    @inlineCallbacks
    def sync_keyring_to_db(self):
        self.local_db = self._Libraries['localdb']
        db_keys = yield self.local_db.get_gpg_key()
        self.gpg = gnupg.GPG(homedir="usr/etc/gpg")
        gpg_keys = yield self.gpg.list_keys()
        gpg_keys = self.format_gen_keys(gpg_keys)
#        print db_keys
#        print gpg_keys
        for gwuuid, data in gpg_keys.iteritems():
            if gwuuid not in db_keys:
                for gwkey in gpg_keys[gwuuid]['keys']:
                    if int(gpg_keys[gwuuid]['keys'][gwkey]['length']) < 2048:
                        logger.error("Not adding key ({length}) due to length being less then 2048. Key is unusable", length=gpg_keys[gwuuid]['keys'][gwkey]['length'])
                    else:
                        yield self.local_db.insert_gpg_key(gpg_keys[gwuuid]['keys'][gwkey])
        self.initDefer.callback(10)



    def format_gen_keys(self, keys):
        variables = {}
        for record in keys:
            uid = record['uids'][0]
            gwuuid = uid[uid.find("(")+1:uid.find(")")]
            if gwuuid not in variables:
                variables[gwuuid] = {
                    'gwuuid': gwuuid,
                    'keys': {},
                }
            key = {
                'gwuuid': gwuuid,
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
            variables[gwuuid]['keys'][record['fingerprint']] = key
        return variables
#[{'dummy': u'', 'keyid': u'CDAADDFAA405F78F', 'expires': u'1495090800', 'sigs': {u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>': []}, 'subkeys': [], 'length': u'4096',
#  'ownertrust': u'u', 'algo': u'1', 'fingerprint': u'F7ADD4CD09A0DC9CC5F63B5ACDAADDFAA405F78F', 'date': u'1463636545', 'trust': u'u', 'type': u'pub',
#  'uids': [u'Yombo Gateway (L2rwJHeKuRSUQoxQFOQP7RnB) <L2rwJHeKuRSUQoxQFOQP7RnB@yombo.net>']},

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

    def remoteGetKey(self, keyHash):
        """
        Send a request to AMQP server to get a key. When something comes back, add it to the key store.

        :param keyHash:
        :return:
        """
        request = {
            "exchange_name"  : "ysrv.e.gw_config",
            "source"        : "yombo.gateway.lib.configurationupdate",
            "destination"   : "yombo.server.configs",
            "callback" : self.amqpDirectIncoming,
            "body"          : {
              "DataType"        : "Object",
              "Request"         : keyHash,
            },
            "request_type"   : "GPGGetKey",
        }
        self.AMQPYombo.sendDirectMessage(**self._generateRequest(item, "All"))

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

    @inlineCallbacks
    def importKey(self, installKey, trustLevel=3):
        """
        Does a quick check to make sure provided key is installed. If not, imports it, sets trust
        level.
        """
        keys = yield self.gpg.list_keys()
        haveKey = False
        for key in keys:
          if key['keyid'] == installKey['keyid']:
#              logger.debug("key (%d) trust:: %s", trustLevel, key['ownertrust'])
              haveKey = True
              if trustLevel == 2 and key['ownertrust'] != 'q':
                self.pgpTrustKey(installKey['keyhash'], trustLevel)
              elif trustLevel == 3 and key['ownertrust'] != 'n':
                self.pgpTrustKey(installKey['keyhash'], trustLevel)
              elif trustLevel == 4 and key['ownertrust'] != 'm':
                self.pgpTrustKey(installKey['keyhash'], trustLevel)
              elif trustLevel == 5 and key['ownertrust'] != 'f':
                self.pgpTrustKey(installKey['keyhash'], trustLevel)
              elif trustLevel == 6 and key['ownertrust'] != 'u':
                self.pgpTrustKey(installKey['keyhash'], trustLevel)
              break

        if haveKey == False:
            importResult = yield self.pgpImportKey(installKey['public_key'])
            if importResult['status'] != "Failed":
              self.pgpTrustKey(installKey['keyhash'], trustLevel)
              haveKey = True

    def pgpEncrypt(self, inText, destination):
        """
        Encrypt text and output as ascii armor text.

        :param inText: Plain text to encrypt.
        :type inText: string
        :param destination: Key fingerprint of the destination.
        :type destination: string
        :return: Ascii armored text.
        :rtype: string
        :raises: YomboException - If encryption failed.
        """
        if type(inText) is unicode and inText.startswith('-----BEGIN PGP MESSAGE-----'):
            try:
                output = self.gpg.encrypt(inText, destination, sign=self.mykeyid)
                if output.status != "encryption ok":
                    raise YomboException("Unable to encrypt string.")
                return output.data
            except:
                raise YomboException("Unable to encrypt string.")
        return inText

    def pgpDecrypt(self, inTemykeyidxt):
        """
        Decrypt a PGP / GPG ascii armor text.  If passed in string/text is not detected as encrypted,
        will simply return the input.

        #TODO: parse STDERR to make sure the key id is ours. Validates trust.

        :param inText: Ascii armored encoded text.
        :type inText: string
        :return: Decoded string.
        :rtype: string
        :raises: YomboException - If decoding failed.
        """
        if type(inText) is unicode and inText.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
            return pgpVerify(inText)
        elif type(inText) is unicode and inText.startswith('-----BEGIN PGP MESSAGE-----'):
            try:
                out = self.gpg.decrypt(inText)
                return out.data
            except:
                raise YomboException("Unable to decrypt string.")
        return inText


    def pgpSign(self, inText, asciiarmor=True):
        """
        Signs inText and returns the signature.
        """
        #cache the gpg/pgp key locally.
        if type(inText) is unicode or type(inText) is str:
            try:
                signed = self.gpg.sign(inText, keyid=self.mykeyid, clearsign=asciiarmor)
                return signed.data
            except:
                raise YomboException("Error with GPG system. Unable to sign your message. 101b")
        return False

    def pgpVerify(self, inText):
        """
        Verifys a signature. Returns the data if valid, otherwise False.
        """
        if type(inText) is unicode and inText.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
            try:
                verified = self.gpg.verify(inText)
                if verified.status == "signature valid":
                    if verified.stderr.find('TRUST_ULTIMATE') > 0:
                        pass
                    elif verified.stderr.find('TRUST_FULLY') > 0:
                        pass
                    else:
                        raise YomboException("Encryption not from trusted source!")
                    out = self.gpg.decrypt(inText)
                    return out.data
                else:
                    return False
            except:
                raise YomboException("Error with GPG system. Unable to verify signed text. 101a")
        return False

    def pgpValidateDest(self, destination):
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

    def pgpCheckKeyTrust(self, keyid):
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

    def pgpImportKey(self, keyText):
        importResults = self.gpg.import_keys(keyText)
        results = importResults.results
#        logger.debug("Result size: %s", len(results) )
        if (len(results) == 1):
            results = results[0]
            results['status'] = results['status'].replace("\n", "")
        else:
            results = {'status' : 'Failed'}
        return results

    @inlineCallbacks
    def pgpTrustKey(self, fingerprint, trustLevel = 5):
        """
        Sets the trust of a key.
        #TODO: This function is blocking! Adjust to non-blocking. See below.
        """
        p = yield Popen(["gpg --import-ownertrust --homedir usr/etc/"], shell=True, stdin=PIPE, stdout=PIPE, close_fds=True)
        (child_stdout, child_stdin) = (p.stdout, p.stdin)
#        logger.info("%s:%d:\n" % (fingerprint, trustLevel))
        child_stdin.write("%s:%d:\n" % (fingerprint, trustLevel))
        child_stdin.close()
        result = child_stdout.read()
        logger.info("GPG Trust change: {result}", result=result)
