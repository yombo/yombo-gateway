#!/usr/bin/env python3
"""
Tests various encryption speeds.
"""

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto import Random

import hashlib
import sys
import os
import shutil
from time import time

sys.path.append(os.getcwd() + '/../../..')

import yombo.ext.gnupg as gnupg

if not os.path.exists("encrypt_gpg_temp"):
    os.makedirs("encrypt_gpg_temp")
gpg_module = gnupg.GPG(gnupghome=f"./encrypt_gpg_temp")

input_data = gpg_module.gen_key_input(
    name_email="test@example.com",
    name_real="Testing",
    name_comment="Created by https://Yombo.net/tinker",
    key_type="RSA",
    key_length=4096,
    expire_date="10y",
    preferences="SHA512 SHA384 SHA256 SHA224 AES256 AES192 AES CAST5 ZLIB BZIP2 ZIP Uncompressed",
    passphrase="I think I will buy the red car, or I will lease the blue one.",
    )


def encrypt(input):
    return gpg_module.encrypt(input, "test@example.com")


def decrypt(in_text):
    """
    Decrypt a PGP / GPG ascii armor text.
    """
    return gpg_module.decrypt(in_text, passphrase="I think I will buy the red car, or I will lease the blue one.")


def encrypt_aes(key, raw, size=128):
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
    # hash the password to ensure length, then trim for smaller aes sizes.
    if size not in (128, 192, 256):
        raise Exception("encrypt_aes size must be one of: 128, 192, or 256")

    key = hashlib.sha256(key.encode("utf-8")).digest()
    if size == 128:
        key = key[:16]
    elif size == 192:
        key = key[:24]
    iv = Random.new().read(AES.block_size);
    cipher = AES.new(key, AES.MODE_CBC, iv)  # Create a AES cipher object with the key using the mode CBC
    ciphered_data = cipher.encrypt(pad(raw, AES.block_size))
    return cipher.iv + ciphered_data


def decrypt_aes(key, ciphered_data, size=128):
    key = hashlib.sha256(key.encode("utf-8")).digest()
    if size == 128:
        key = key[:16]
    elif size == 192:
        key = key[:24]
    cipher = AES.new(key, AES.MODE_CBC, iv=ciphered_data[:16])  # Setup cipher
    original_data = unpad(cipher.decrypt(ciphered_data), AES.block_size)
    return original_data[16:]

source_data = b"Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore " \
              b"et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut " \
              b"aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse " \
              b"cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in " \
              b"culpa qui officia deserunt mollit anim id est laborum."
password = "thisismypassword!"

rounds = 2000

print("Testing AES speed...")
print(f"Testing with: {rounds} iterations.  Times are in seconds.")

start = time()
for i in range(0, rounds):
    results = encrypt_aes(password, source_data, 128)
end = time()
# print(base64.b16encode(results))
print(f"aes-128 ENcryption time: {round(end-start, 5)}, length = {len(results)}.")

start = time()
for i in range(0, rounds):
    output = decrypt_aes(password, results, 128)
end = time()
print(f"aes-128 DEcryption time: {round(end-start, 5)}. Decrypted text is same as input: {source_data == output}")

start = time()
for i in range(0, rounds):
    results = encrypt_aes(password, source_data, 192)
end = time()
print(f"aes-192 ENcryption time: {round(end-start, 5)}, length = {len(results)}.")

start = time()
for i in range(0, rounds):
    output = decrypt_aes(password, results, 192)
end = time()
print(f"aes-192 DEcryption time: {round(end-start, 5)}. Decrypted text is same as input: {source_data == output}")

start = time()
for i in range(0, rounds):
    results = encrypt_aes(password, source_data, 256)
end = time()
print(f"aes-256 ENcryption time: {round(end-start, 5)}, length = {len(results)}")

start = time()
for i in range(0, rounds):
    output = decrypt_aes(password, results, 256)
end = time()
print(f"aes-256 DEcryption time: {round(end-start, 5)}. Decrypted text is same as input: {source_data == output}")


print("\nGenerating GPG key...")
print("GPG timing is interpolated with lower sample numbers due to increased decryption time. ")
newkey = gpg_module.gen_key(input_data)
print("\nTesting GPG speed...\n")
start = time()
for i in range(0, round(rounds/100)):
    results = encrypt(source_data)
end = time()
print(f"GPG encryption time: {(round(end-start, 5))*100}. Length: {len(results.data)}")

start = time()
for i in range(0, round(rounds/100)):
    output = decrypt(results.data)
end = time()
print(f"GPG decryption time: {(round(end-start, 5))*100}. Match: {source_data == output.data}")

shutil.rmtree('./encrypt_gpg_temp')
try:
    os.remove("./pubring.kbx~")
except:
    pass