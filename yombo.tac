#import pyximport; pyximport.install()
# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
import sys
import os

stdoutbefore = getattr(sys.stdout, "encoding", None)
stderrbefore = getattr(sys.stderr, "encoding", None)

import asyncio
import uvloop
from asyncio.tasks import ensure_future
from twisted.internet import asyncioreactor

loop = uvloop.new_event_loop()
asyncio.set_event_loop(loop)
asyncioreactor.install(eventloop=loop)

from twisted.internet import reactor
from twisted.application import service

#ensure that usr data directory exists
if not os.path.exists('usr'):
    os.makedirs('usr')
if not os.path.exists('usr'):
    os.makedirs('usr/gpg')
if not os.path.exists('usr/bak'):
    os.makedirs('usr/bak')
if not os.path.exists('usr/bak/yombo_ini'):
    os.makedirs('usr/bak/yombo_ini')
if not os.path.exists('usr/etc'):
    os.makedirs('usr/etc')
if not os.path.exists('usr/etc/gpg'):
    os.makedirs('usr/etc/gpg')
if not os.path.exists('usr/etc/certs'):
    os.makedirs('usr/etc/certs')
if not os.path.exists('usr/locale'):
    os.makedirs('usr/locale')
#logging directory
if not os.path.exists('usr/log'):
    os.makedirs('usr/log')
if not os.path.exists('usr/opt'):
    os.makedirs('usr/opt')

# ensure only our user can read these directories. Allows a
# backup group to be assigned for backup purposes.
os.chmod('usr/etc', 0o700)
os.chmod('usr/etc/gpg', 0o700)
os.chmod('usr/etc/certs', 0o700)
os.chmod('usr/bak', 0o760)

try:
    from yombo.core.gwservice import GWService
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), ""))
    from yombo.core.gwservice import GWService

application = service.Application('yombo')

service = GWService()
service.setServiceParent(application)
service.start()
reactor.run()
