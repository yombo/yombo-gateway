import pyximport; pyximport.install()
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at https://yombo.net
"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""

import sys
import os

stdoutbefore = getattr(sys.stdout, "encoding", None)
stderrbefore = getattr(sys.stderr, "encoding", None)


from twisted.application import internet, service, strports

#ensure that usr data directory exists
if not os.path.exists('usr'):
    os.makedirs('usr')
if not os.path.exists('usr'):
    os.makedirs('usr/gpg')
#sql data directory
if not os.path.exists('usr/sql'):
    os.makedirs('usr/sql')
#Misc items are stored here.
if not os.path.exists('usr/etc'):
    os.makedirs('usr/etct')
#logging directory
if not os.path.exists('usr/log'):
    os.makedirs('usr/log')

try:
    from yombo.core.gwservice import GWService
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), ""))
    from yombo.core.gwservice import GWService

from yombo.core.log import getLogger

logger = getLogger('twistedlogger')

application = service.Application('yombo')

service = GWService()
service.setServiceParent(application)
service.start()
#logger.basicConfig(level=logging.DEBUG)
