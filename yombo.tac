import pyximport; pyximport.install()
# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
import sys
import os

import sys, gettext
kwargs = {}
if sys.version_info[0] > 3:
    # In Python 2, ensure that the _() that gets installed into built-ins
    # always returns unicodes.  This matches the default behavior under
    # Python 3, although that keyword argument is not present in the
    # Python 3 API.
    kwargs['unicode'] = True
gettext.install('yombo', 'locale', **kwargs)

#print _("hello")  # prints: hello2

stdoutbefore = getattr(sys.stdout, "encoding", None)
stderrbefore = getattr(sys.stderr, "encoding", None)

from twisted.application import internet, service, strports

#ensure that usr data directory exists
if not os.path.exists('usr'):
    os.makedirs('usr')
if not os.path.exists('usr'):
    os.makedirs('usr/gpg')
if not os.path.exists('usr/etc'):
    os.makedirs('usr/etc')
if not os.path.exists('usr/bak'):
    os.makedirs('usr/bak')
if not os.path.exists('usr/bak/yombo_ini'):
    os.makedirs('usr/bak/yombo_ini')
if not os.path.exists('usr/lang'):
    os.makedirs('usr/lang')
if not os.path.exists('usr/etc/gpg'):
    os.makedirs('usr/etc/gpg')
    os.chmod('usr/etc/gpg', 0700)
#logging directory
if not os.path.exists('usr/log'):
    os.makedirs('usr/log')

try:
    from yombo.core.gwservice import GWService
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), ""))
    from yombo.core.gwservice import GWService

from yombo.core.log import get_logger

logger = get_logger('root.twistd')

application = service.Application('yombo')

service = GWService()
service.setServiceParent(application)
service.start()
