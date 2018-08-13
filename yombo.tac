# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
"""
import asyncio
import os
import select
import shlex
import sys
from twisted.internet import asyncioreactor

""" Try to use a faster looper."""
try:
    import uvloop
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncioreactor.install(eventloop=loop)
except ImportError:
    pass

try:
    import yombo.core.settings as settings
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), ""))
    import yombo.core.settings as settings

stdoutbefore = getattr(sys.stdout, "encoding", None)
stderrbefore = getattr(sys.stderr, "encoding", None)


def show_help():
    """Display the help menu when calling the tac file directly (a no-no)."""
    print("This file shouldn't be called directly by users. Please use either:")
    print("1) ybo - If installed by Yombo install scripts")
    print("2) %s/yombo.sh" % os.path.dirname(os.path.abspath(__file__)))
    print("\n")


def get_arguments():
    """
    Twisted tac files cannot accept options. So, they are read in via the
    stdin....annoying and ugly.

    :return:
    """
    defaults = {
        'app_dir': os.path.dirname(os.path.abspath(__file__)),
        'debug': False,
        'debug_items': [],
        'norestoreini': False,
        'restoreini': False,
        'working_dir': "%s/.yombo" % os.path.expanduser("~"),
    }

    # Reads arguments from stdin.
    if select.select([sys.stdin, ], [], [], 0.05)[0]:
        args = shlex.split(sys.stdin.readline())
        arguments = {k: True if v.startswith('-') else v
                     for k, v in zip(args, args[1:] + ["--"]) if k.startswith('-')}
    else:
        arguments = {}

    if any(key in arguments for key in ['-?', '-h', '-help', '--help', '--?']):
        show_help()
        exit()
    if '-w' in arguments:
        defaults['working_dir'] = arguments['-w']
    if not os.path.exists('%s' % os.path.dirname(defaults['working_dir'])):
        raise Exception("Invalid working directory '%s', the parent '%s' must exist." %
                        (defaults['working_dir'], os.path.dirname(defaults['working_dir'])))

    if '-a' in arguments:
        defaults['app_dir'] = arguments['-a']
    elif '--app_dir' in arguments:
        defaults['app_dir'] = arguments['--app_dir']
    if not os.path.exists('%s' % defaults['app_dir']):
        raise Exception("Invalid app directory '%s', it doesn't exist." % defaults['app_dir'])

    if '-d' in arguments:
        defaults['debug'] = True
    elif '--debug' in arguments:
        defaults['debug'] = True
    if defaults['debug'] is True:
        if '--debug-items' in arguments:
            defaults['debug_items'] = arguments['--debug-items'].split(',')
        else:
            defaults['debug_items'] = ['*']

    if '--norestoreini' in arguments:
        defaults['norestoreini'] = True

    if '--restoreini' in arguments:
        defaults['restoreini'] = True

    return defaults


def start():
    """ Start Yombo. """
    try:
        arguments = get_arguments()
    except Exception as e:
        print("Error starting Yombo: %s" % e)
        exit()

    working_dir = arguments['working_dir']  # Typically the user's directory: ~/.yombo
    #ensure that usr data directory exists
    if not os.path.exists('%s/gpg' % working_dir):
        os.makedirs('%s/gpg' % working_dir)
    if not os.path.exists('%s/bak' % working_dir):
        os.makedirs('%s/bak' % working_dir)
    if not os.path.exists('%s/bak/yombo_ini' % working_dir):
        os.makedirs('%s/bak/yombo_ini' % working_dir)
    if not os.path.exists('%s/etc' % working_dir):
        os.makedirs('%s/etc' % working_dir)
    if not os.path.exists('%s/etc/gpg' % working_dir):
        os.makedirs('%s/etc/gpg' % working_dir)
    if not os.path.exists('%s/etc/certs' % working_dir):
        os.makedirs('%s/etc/certs' % working_dir)
    if not os.path.exists('%s/locale' % working_dir):
        os.makedirs('%s/locale' % working_dir)
    if not os.path.exists('%s/log' % working_dir):
        os.makedirs('%s/log' % working_dir)
    if not os.path.exists('%s/opt' % working_dir):
        os.makedirs('%s/opt' % working_dir)

    # ensure only our user can read these directories. Allows a
    # backup group to be assigned for backup purposes.
    os.chmod('%s/etc' % working_dir, 0o700)
    os.chmod('%s/etc/gpg' % working_dir, 0o700)
    os.chmod('%s/etc/certs' % working_dir, 0o700)
    os.chmod('%s/bak' % working_dir, 0o760)

    os.system('gpg-agent --homedir %s/etc/gpg/ --daemon > file 2>&1' % working_dir)

    results = settings.init(arguments)
    if results is False:
        print("Error with loading yombo.ini. Quiting.")
        exit(200)
    from twisted.application import service as twisted_service
    application = twisted_service.Application('yombo')

    # Gateway service is responsible for actually running everything.
    from yombo.core.gwservice import GWService
    gwservice = GWService()
    gwservice.setServiceParent(application)
    gwservice.start()
    return application

if __name__ == "builtins":
    application = start()
