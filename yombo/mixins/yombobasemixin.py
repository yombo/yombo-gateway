# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
A simple parent class for children of various Yombo libriaries.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.22.0

Yombo base mixin. If submitted, sets the _Parent attribute. Future versions will provide more
capabilities.

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
"""
from time import time
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("library.users.yombobasemixin")


class YomboBaseMixin(object):

    def __init__(self, parent, *args, **kwargs):
        self._Parent = parent
        super().__init__()
