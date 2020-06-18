# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
The TAC file is the twisted matrix entry point to start Yombo Gateway. This sets up some basic items
and then calls yombo.core.gwservice to actually start the gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
"""
import asyncio
import builtins
import os
import pathlib
import select
import shlex
import sys
from typing import Dict, Type, Union

from twisted.internet import asyncioreactor

# Adds the yombo directory to the python path.
sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), "")[:-1])

import yombo.core.settings as settings

try:
    # Try to use a faster looper.
    import uvloop
    loop = uvloop.new_event_loop()
    # Interact with asyncio for await/async.
    asyncio.set_event_loop(loop)
    asyncioreactor.install(eventloop=loop)
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass


def show_help() -> None:
    """Display the help menu when calling the tac file directly (a no-no)."""
    print("This file shouldn't be called directly by users. Please use:")
    print("'ybo' - If installed by Yombo install scripts")
    print("\n")


def get_arguments() -> Dict[str, Union[str, int, float]]:
    """
    Twisted tac files cannot accept options. So, they are read in via the
    stdin....annoying and ugly.

    :return:
    """
    defaults = {
        "app_dir": os.path.dirname(os.path.abspath(__file__)),
        "debug": False,
        "debug_items": [],
        "restoretoml": True,
        "working_dir": f"{os.path.expanduser('~')}/.yombo",
    }

    # Reads arguments from stdin.
    if select.select([sys.stdin, ], [], [], 0.05)[0]:
        args = shlex.split(sys.stdin.readline())
        arguments = {k: True if v.startswith("-") else v
                     for k, v in zip(args, args[1:] + ["--"]) if k.startswith("-")}
    else:
        arguments = {}

    if any(key in arguments for key in ["-?", "-h", "-help", "--help", "--?"]):
        show_help()
        exit()
    if "-w" in arguments:
        defaults["working_dir"] = arguments["-w"]
    if not os.path.exists(str(os.path.dirname(defaults["working_dir"]))):
        raise Exception(f"Invalid working directory 'defaults['working_dir']', "
                        f"the parent '{os.path.dirname(defaults['working_dir'])}' must exist.")

    if "-a" in arguments:
        defaults["app_dir"] = arguments["-a"]
    elif "--app_dir" in arguments:
        defaults["app_dir"] = arguments["--app_dir"]
    if not os.path.exists(defaults["app_dir"]):
        raise Exception(f"Invalid app directory '{defaults['app_dir']}', it doesn't exist.")

    if "-d" in arguments:
        defaults["debug"] = True
    elif "--debug" in arguments:
        defaults["debug"] = True
    if defaults["debug"] is True:
        if "--debug-items" in arguments:
            defaults["debug_items"] = arguments["--debug-items"].split(",")
        else:
            defaults["debug_items"] = ["*"]

    if "--norestoretoml" in arguments:
        defaults["restoretoml"] = False

    if "--restoretoml" in arguments:
        defaults["restoretoml"] = True

    return defaults


def temp_translator(msgid, *args, **kwargs):
    """
    A temporary translator placeholder used during bootup.

    :param msgid:
    :param args:
    :param kwargs:
    :return:
    """
    return msgid


def start() -> Type["twisted.application.service.Application"]:
    """ Start Yombo. """
    try:
        arguments = get_arguments()
    except Exception as e:
        print(f"Error starting Yombo: {e}")
        exit()

    working_dir = arguments["working_dir"]  # Typically the user"s directory: ~/.yombo
    settings.init(arguments)

    # ensure that usr data directory exists with proper security settings.
    if not os.path.exists(f"{working_dir}/gpg"):
        os.makedirs(f"{working_dir}/gpg")
    if not os.path.exists(f"{working_dir}/bak"):
        os.makedirs(f"{working_dir}/bak")
    if not os.path.exists(f"{working_dir}/bak/yombo_toml"):
        os.makedirs(f"{working_dir}/bak/yombo_toml")
    if not os.path.exists(f"{working_dir}/bak/db"):
        os.makedirs(f"{working_dir}/bak/db")
    if not os.path.exists(f"{working_dir}/etc"):
        os.makedirs(f"{working_dir}/etc")
    if not os.path.exists(f"{working_dir}/etc/gpg"):
        os.makedirs(f"{working_dir}/etc/gpg")
    if not os.path.exists(f"{working_dir}/etc/certs"):
        os.makedirs(f"{working_dir}/etc/certs")
    if not os.path.exists(f"{working_dir}/locale"):
        os.makedirs(f"{working_dir}/locale")
    if not os.path.exists(f"{working_dir}/frontend"):
        os.makedirs(f"{working_dir}/frontend")
    if not os.path.exists(f"{working_dir}/log"):
        os.makedirs(f"{working_dir}/log")
    if not os.path.exists(f"{working_dir}/opt"):
        os.makedirs(f"{working_dir}/opt")
    if not os.path.exists(f"{working_dir}/var"):
        os.makedirs(f"{working_dir}/var")

    # ensure only our user can read these directories.
    os.chmod(f"{working_dir}/etc", 0o700)
    os.chmod(f"{working_dir}/etc/gpg", 0o700)
    os.chmod(f"{working_dir}/etc/certs", 0o700)
    os.chmod(f"{working_dir}/bak", 0o700)

    os.system(f"gpg-agent --homedir {working_dir}/etc/gpg/ --daemon > {working_dir}/log/gpg-agent 2>&1")

    builtins.__dict__["_"] = temp_translator

    from twisted.application import service as twisted_service
    twisted_application = twisted_service.Application("yombo")

    # Gateway service is responsible for actually running everything.
    from yombo.core.gwservice import GWService
    gateway_service = GWService()
    gateway_service.setServiceParent(twisted_application)
    gateway_service.start()
    return twisted_application

if __name__ == "builtins":
    application = start()
