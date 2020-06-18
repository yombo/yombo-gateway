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

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/gpg/gpgkey.html>`_
"""
# Import python libraries
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.log import get_logger
from yombo.core.schemas import GPGKeySchema

logger = get_logger("library.gpg")

TRUST_UNDEFINED = 0
TRUST_NEVER = 1
TRUST_MARGINAL = 2
TRUST_FULLY = 3
TRUST_ULTIMATE = 4

TRUST_LEVELS = {
    "TRUST_UNDEFINED": TRUST_UNDEFINED,
    "TRUST_NEVER": TRUST_NEVER,
    "TRUST_MARGINAL": TRUST_MARGINAL,
    "TRUST_FULLY": TRUST_FULLY,
    "TRUST_ULTIMATE": TRUST_ULTIMATE,
}


class GPGKey(Entity):
    """
    A command is represented by this class is returned to callers of the
    :py:meth:`get() <Commands.get>` or :py:meth:`__getitem__() <Commands.__getitem__>` functions.
    """
    _Entity_type: ClassVar[str] = "GPGKey"
    _Entity_label_attribute: ClassVar[str] = "machine_label"

    def __init__(self, parent, incoming):
        """
        Load the key's passphrase.
        :return:
        """
        super().__init__(parent)
        incoming = dict(GPGKeySchema().load(incoming))
        self.trust: str = incoming["trust"]
        self.length: int = incoming["length"]
        self.algo: int = incoming["algo"]
        self.keyid: str = incoming["keyid"]
        self.date: int = incoming["date"]
        self.expires: int = incoming["expires"]
        self.ownertrust: str = incoming["ownertrust"]
        self.uids: list = incoming["uids"]
        self.sigs: list = incoming["sigs"]
        self.subkeys: list = incoming["subkeys"]
        self.fingerprint: str = incoming["fingerprint"]
        self.has_private: bool = incoming["has_private"]
        self.publickey: str = incoming["publickey"]
        self.passphrase: str = incoming["passphrase"]
        self.uid_endpoint_id: str = incoming["uid_endpoint_id"]
        self.uid_endpoint_type: str = incoming["uid_endpoint_type"]
