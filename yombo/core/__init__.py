#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
.. module:: yombo.core
   :synopsis: Core resources of the Yombo gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: 2012-2015 by Yombo
:license: LICENSE for details.
"""
from yombo.core.log import get_logger

logger = get_logger('core')


def getComponent(name):
    """
    Return loaded component
    """
    from yombo.lib.loader import get_loader
    return get_loader().get_loaded_component(name)
