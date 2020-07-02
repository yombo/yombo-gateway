# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `GPG @ Library Documentation <https://yombo.net/docs/libraries/encryption>`_

This library handles encrypting and decrypting content. For public key encryption, see the
:ref:`GPG <gpg>` library. This library allows data at rest to be encrypted, which
means any passwords or sensitive data will be encrypted before it is saved to disk. This library doesn't
attempt to manage data in memory or saved in a swap file.

.. note::

  The secret key is stored within the working directory where configuration files are stored. Care should
  be taken to keep this directory secure and access restricted. Yombo gateway attempts to do this by changing
  access permissions to only allow the user running this gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/encryption.html>`_
"""
# Import python libraries
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad as aespad, unpad as aesunpad
from Crypto import Random
import hashlib
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
# from yombo.mixins.library_search_mixin import LibrarySearchMixin
# from yombo.mixins.parent_storage_accessors_mixin import ParentStorageAccessorsMixin
# from yombo.mixins.child_storage_accessors_mixin import ChildStorageAccessorsMixin
from yombo.utils import random_string, bytes_to_unicode, unicode_to_bytes

logger = get_logger("library.encryption")


class Encryption(YomboLibrary):
    """
    Manage all encryption functions.
    """
    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Get the encryption system up - load the or create a default master key.
        """
        aes_key_path = f"{self._working_dir}/etc/gpg/aes.key"
        try:
            self.__aes_key = yield self._Files.read(aes_key_path, convert_to_unicode=False)
        except FileNotFoundError:
            self.__aes_key = random_string(length=512)
            yield self._Files.save(aes_key_path, self.__aes_key)
        self.__aes_key = self.__aes_key

    @staticmethod
    def _aes_expand_key(passphrase, cipher):
        """
        Internal function to standardize the key size. Uses sha256 to generate a hash from the key, and then trims
        as needed.

        :param passphrase: passphrase to use.
        :param cipher: 16, 24, 32
        :return:
        """
        cipher = int(cipher[3:])
        passphrase = hashlib.sha256(unicode_to_bytes(passphrase)).digest()
        if cipher == 128:
            passphrase = passphrase[:16]
        elif cipher == 192:
            passphrase = passphrase[:24]
        # Remaining is 256, or 32 bytes.
        return passphrase

    @staticmethod
    def validate_cipher(cipher: str) -> str:
        """
        Validates a given cipher is valid. Returns a valid cipher or raises YomboWarning.

        :param cipher:
        :return:
        """
        if cipher is None:
            cipher = "aes256"
        cipher = cipher.lower()
        if cipher not in ("aes128", "aes192", "aes256"):
            raise YomboWarning(f"Invalid encrypt cipher: {cipher}")
        return cipher

    def encrypt(self, data, passphrase: Optional[str] = None, cipher: Optional[str] = None):
        """
        Encrypt something, default is aes256.

        If data needs to be pickled and/or encoded (such as base64/base85) use self._Tools.data_pickle().

        Example: encrypted = self._Encryption.encrypt("secret data", cipher="aes256")

        Ciphers available:
        aes128
        aes192
        aes256

        Last notes: Encrypted data is generally not compressible. If the data should be compressed, do so before
        sending the data here.

        :param data: Any type of data can be encrypted. Text, binary.
        :param passphrase: A passphrase to use. If missing, uses system passphrase.
        :param cipher: Which cipher to use, default aes128.
        :return: String containing the encrypted content.
        """
        if data is None:
            return None
        cipher = self.validate_cipher(cipher)

        if passphrase is None:
            passphrase = self.__aes_key
        if cipher.startswith("aes"):
            results = self.encrypt_aes(data, passphrase, cipher)
        return results

    @classmethod
    def encrypt_aes(cls, data, passphrase, cipher):
        """
        Encrypt data with passphrase. Currently, only supporting aes 156.
        """
        passphrase = cls._aes_expand_key(passphrase, cipher)
        iv = Random.new().read(AES.block_size)
        aescipher = AES.new(passphrase, AES.MODE_CBC, iv)  # Create a AES cipher object with the key using the mode CBC
        raw = unicode_to_bytes(data)
        ciphered_data = aescipher.encrypt(aespad(raw, AES.block_size))
        return aescipher.iv + ciphered_data

    def decrypt(self, data, passphrase: Optional[str] = None, cipher: Optional[str] = None):
        """
        Decrypt something, defaults aes256.

        Example: data = self._Encryption.decrypt("x831jsd91je", cipher="aes256")

        Ciphers available:
        aes128
        aes192
        aes256

        :param data: Any type of data can be encrypted. Text, binary.
        :param passphrase: A passphrase to use. If missing, uses system passphrase.
        :param cipher: Which cipher to use, such as: aes128, aes192, aes256.
        :return: String containing the encrypted content.
        """
        if data is None:
            return None
        data = unicode_to_bytes(data)

        cipher = self.validate_cipher(cipher)

        if passphrase is None:
            passphrase = self.__aes_key

        if cipher.startswith("aes"):
            results = self.decrypt_aes(data, passphrase, cipher)

        return results

    @classmethod
    def decrypt_aes(cls, ciphered_data: str, passphrase: str, cipher: str):
        """
        Decrypt data. Typically should only be called by decrypt() method.

        :param ciphered_data: Encrypted data string.
        :param passphrase: A passphrase to use. If missing, uses system passphrase.
        :param cipher: Which cipher to use, such as: aes128, aes192, aes256.
        :return:
        """
        passphrase = cls._aes_expand_key(passphrase, cipher)

        ciphered_data = ciphered_data
        aesoriginal_data = AES.new(passphrase, AES.MODE_CBC, iv=ciphered_data[:16])  # Setup cipher
        original_data = aesunpad(aesoriginal_data.decrypt(ciphered_data), AES.block_size)
        try:
            return original_data[16:].decode("utf-8")
        except:
            return original_data[16:]
