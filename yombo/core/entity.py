#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Entity Core @ Module Development <https://yombo.net/docs/core/entity>`_


Used by all classes to show various information about any Yombo related class.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/entity.html>`_
"""
class Entity(object):
    """
    Define a basic class that setup basic library class variables.
    """

    def __init__(self):
        self._Entity_type = None
        super().__init__()
