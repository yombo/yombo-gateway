# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Tools @ Library Documentation <https://yombo.net/docs/libraries/tools>`_

Misc tools.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2018-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/tools.html>`_
"""
# Import python libraries
import base64
from copy import deepcopy
import lz4.frame
import simplejson as json
import msgpack
from typing import Any, ClassVar, Dict, List, Optional, Type, Union
import zlib

from twisted.names import client

# Import 3rd-party libs
import yombo.ext.base62 as base62

# Import Yombo libraries
from yombo.constants.encryption import AVAILABLE_CIPHERS
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.core.exceptions import YomboWarning
from yombo.utils import unicode_to_bytes, bytes_to_unicode

logger = get_logger("library.tools")


class Tools(YomboLibrary):
    """
    Misc tools/helpers.
    """
    def _init_(self, **kwargs):
        """ Setups DNS resolver. """
        # https://twistedmatrix.com/documents/current/api/twisted.names.client.html#createResolver
        self.dns = client.createResolver()

    @classmethod
    def pickle_records(cls, records: Union[list, dict], pickled_columns: Union[dict, list]) -> Union[list, dict]:
        """
        Pickles record items according to pickled_columns.

        :param records: A list of dictionaries or a single dictionary to unpickle.
        :param pickled_columns: List of dictionary of columns that are pickled.
        """
        if records is None:
            raise YomboWarning("Unable to pickle records, records is None")
        if pickled_columns is None:
            raise YomboWarning("Unable to pickle records, pickled_columns is None")

        if len(pickled_columns) == 0 or len(records) == 0:
            return records

        if isinstance(pickled_columns, list):
            temp_pickle = {}
            for key in pickled_columns:
                temp_pickle[key] = "msgpack_base85"
            pickled_columns = temp_pickle

        def do_pickle(columns):
            local_results = deepcopy(columns)
            for column, encoding in pickled_columns.items():
                if column in columns and columns[column] is not None:
                    local_results[column] = cls.data_pickle(columns[column], encoding)
            return local_results

        if isinstance(records, dict):
            return do_pickle(records)
        else:
            results = []
            for record in records:
                results.append(do_pickle(record))
            return results

    @classmethod
    def unpickle_records(cls, records: Union[list, dict], pickled_columns: Union[dict, list]) -> None:
        """
        Un-pickles record items according to pickled_columns.

        :param records: A list of dictionaries or a single dictionary to unpickle.
        :param pickled_columns: List of dictionary of columns that are pickled.
        :return:
        """
        if records is None:
            raise YomboWarning("Unable to unpickle records, input is None")
        if pickled_columns is None:
            raise YomboWarning("Unable to unpickle records, pickled_columns is None")

        if len(pickled_columns) == 0 or len(records) == 0:
            return records

        if isinstance(pickled_columns, list):
            temp_pickle = {}
            for key in pickled_columns:
                temp_pickle[key] = "msgpack_base85"
            pickled_columns = temp_pickle

        # print(f"tools: unpickle_records 5: pickled_columns - {pickled_columns}")

        def do_unpickle(columns):
            local_results = deepcopy(columns)
            for column, encoding in pickled_columns.items():
                if column in columns and columns[column] is not None:
                    local_results[column] = cls._Tools.data_unpickle(columns[column], encoding)
            return local_results

        if isinstance(records, dict):
            return do_unpickle(records)
        else:
            results = []
            for record in records:
                results.append(do_unpickle(record))
            return results

    @classmethod
    def data_pickle(cls, data: Any, content_type: Optional[str] = None, compression_level: Optional[int] = None,
                    local: Optional[bool]=None, passphrase: Optional[str] = None,
                    use_decimal: Optional[bool] = None) -> Union[str, bytes]:
        """
        Encodes data based on value of the content_type type. The default is "msgpack_base85". This easily allows data
        to be sent externally or even the database. The ordering of the content_type does not matter.

        Format of the content_type:
        {pickle-method}_{compress method}_{encode-method}.

        Pickle methods:
        * msgpack - Use msgpack to pickle the data. More space efficient than json.
        * json - Use JSON to pickle the data.

        Compression can also be applied, simply append:
        * lz4 - Use the lz4 compression
        * zip - Use the gzip compression

        Encryption is also supported:
        * aes256, aes192, aes128

        Encode methods:
        * base32 - Encode with base32 - Biggest size.
        * base62 - Encode with base62 - Like base64, but URL safe.
        * base64 - Encode with base64
        * base85 - Encode with base85

        Examples:
        * msgpack_zip - Pickle with msgpack, then compress with gzip.
        * zip_msgpack - Same as above, just different order.
        * msgpack_base85_zip - Pickle with msgpack, then compress with gzip, then encode with base85
        * msgpack_zip_aes256_base85 - Pickle with msgpack, compress with gzip, encrypt with aes, then encode with base85
        * json_lz4 - Pickle with json, then compress with z-standard.

        Non-encoded results typically return bytes, while encoded results return strings.

        :param data: String, list, or dictionary to be encoded.
        :param content_type: Optional encode method.
        :param compression_level: Sets a compression level - default depends on compressor.
        :param passphrase: Passphrase will be sent to the encryption function.

        :return: bytes of the encoded data that can be used with data_unpickle.
        """
        if data is None:
            return None

        if content_type is None:
            content_type = "msgpack_base85"
        elif content_type == "string":
            return str(data)
        elif content_type == "bool":
            return bool(data)
        content_type = content_type.lower()

        if "json" in content_type and "msgack" in content_type:
            raise YomboWarning("Pickle data can only have json or msgpack, not both.")

        encoder_count = 0
        for encoder_check in ("base32", "base62", "base64", "base85"):
            if encoder_check in content_type:
                encoder_count +=1
        if encoder_count > 1:
            raise YomboWarning("Pickle data can only one of: base32, base62, base64 or base85, not multiple.")

        if "json" in content_type:
            try:
                data = json.dumps(data, separators=(",", ":"), use_decimal=use_decimal)
            except Exception as e:
                raise YomboWarning(f"Error encoding json: {e}")
        elif "msgpack" in content_type:
            try:
                data = msgpack.packb(data)
            except Exception as e:
                raise YomboWarning(f"Error encoding msgpack: {e}")

        if "lz4" in content_type:
            if compression_level is None:
                compression_level = 2
            elif compression_level > 1 or compression_level < 9:
                compression_level = 2
            try:
                data = lz4.frame.compress(unicode_to_bytes(data), compression_level)
            except Exception as e:
                raise YomboWarning(f"Error encoding {content_type}: {e}")
        elif "gzip" in content_type or "zip" in content_type:
            if compression_level is None:
                compression_level = 5
            elif compression_level > 1 or compression_level < 9:
                compression_level = 5
            try:
                data = zlib.compress(unicode_to_bytes(data), compression_level)
            except Exception as e:
                raise YomboWarning(f"Error encoding {content_type}: {e}")

        for cipher in AVAILABLE_CIPHERS:
            if cipher in content_type:
                try:
                    data = cls._Encryption.encrypt_aes(data, passphrase=passphrase, cipher=cipher)
                except Exception:
                    break

        if "base32" in content_type:
            data = bytes_to_unicode(base64.b32encode(data))
            if local is True:
                data = data.rstrip("=")
        elif "base62" in content_type:
            data = bytes_to_unicode(base62.encodebytes(data))
            if local is True:
                data = data.rstrip("=")
        elif "base64" in content_type:
            data = bytes_to_unicode(base64.b64encode(data))
            if local is True:
                data = data.rstrip("=")
        elif "base85" in content_type:
            data = bytes_to_unicode(base64.b85encode(data))
        return data

    @classmethod
    def data_unpickle(cls, data: Any, content_type: Optional[str] = None, passphrase: Optional[str] = None,
                      use_decimal: Optional[bool] = None):
        """
        Unpack data packed with data_pickle. See data_pickle() for content_type options.

        :param data:
        :param content_type:
        :param passphrase: Passphrase will be sent to the encryption function.

        :return:
        """
        if data is None:
            return None
        data = bytes_to_unicode(data)

        if content_type is None:
            content_type = "msgpack_base85"
        elif content_type == "string":
            return str(data)
        elif content_type == "bool":
            return bool(data)
        content_type = content_type.lower()

        # Sometimes empty dictionaries are encoded...  This is a simple shortcut.
        if content_type == "msgpack_base85_zip" and data == "cwTD&004mifd":
            return {}
        elif content_type == "msgpack_base85" and data == "fB":
            return {}

        if "json" in content_type and "msgack" in content_type:
            raise YomboWarning("Unpickle data can only have json or msgpack, not both.")

        encoder_count = 0
        for encoder_check in ("base32", "base62", "base64", "base85"):
            if encoder_check in content_type:
                encoder_count +=1
        if encoder_count > 1:
            raise YomboWarning("Pickle data can only one of: base32, base62, base64 or base85, not multiple.")

        if "base32" in content_type:
            data = base64.b32decode(data)
        if "base62" in content_type:
            data = base62.decodebytes(data)
        if "base64" in content_type:
            data = data + "=" * (-len(data) % 4)
            data = base64.b64decode(data)
        elif "base85" in content_type:
            data = base64.b85decode(data)

        for cipher in AVAILABLE_CIPHERS:
            if cipher in content_type:
                try:
                    print(f"tools.unpickle, about to decrypt: {data}")
                    data = cls._Encryption.decrypt_aes(data, passphrase=passphrase, cipher=cipher)
                    print(f"tools.unpickle, about to decrypt, done: {data}")
                except Exception:
                    break

        if "lz4" in content_type:
            try:
                data = lz4.frame.decompress(data, passphrase=passphrase)
            except Exception as e:
                raise YomboWarning(f"Error lz4 decompress {content_type}: {e}")
        elif "gzip" in content_type or "zip" in content_type:
            try:
                data = zlib.decompress(data)
            except Exception as e:
                raise YomboWarning(f"Error zlib decompress {content_type}: {e}")

        try:
            data = zlib.decompress(data)
        except Exception as e:
            pass

        if isinstance(data, str) or isinstance(data, bytes):
            if "json" in content_type:
                data = unicode_to_bytes(data)
                try:
                    data = bytes_to_unicode(json.loads(data, use_decimal=use_decimal))
                except Exception as e:
                    raise YomboWarning(f"data_unpickle received non-json content: {data}")
            elif "msgpack" in content_type:
                data = unicode_to_bytes(data)
                try:
                    data = bytes_to_unicode(msgpack.unpackb(data))
                except Exception as e:
                    raise YomboWarning(f"data_unpickle received non-msgpack content: {data}")
        return data
