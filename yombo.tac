import pyximport; pyximport.install()
#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://www.yombo.net
"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2013 by Yombo.
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
#sql data directory
if not os.path.exists('usr/sql'):
    os.makedirs('usr/sql')
#downloaded modules directory
if not os.path.exists('usr/opt'):
    os.makedirs('usr/opt')
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
#from twisted.python import log
#observer = log.PythonLoggingObserver(loggerName='twistedlogger')
#observer.start()

#sys.stdout = stdoutbefore
#sys.stderr = stderrbefore

application = service.Application('yombo')

service = GWService()
service.setServiceParent(application)
service.start()
#logging.basicConfig(level=logging.DEBUG)
