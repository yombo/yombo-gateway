#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
.. module:: yombo.core
   :synopsis: Core resources of the Yombo gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: 2012-2015 by Yombo
:license: LICENSE for details.
"""


def getComponent(name):
    """
    Return loaded component
    """
    from yombo.lib.loader import getLoader
    return getLoader().getLoadedComponent(name)
