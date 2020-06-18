# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Log Core @ Module Development <https://yombo.net/docs/core/log>`_


Handles logging functions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/log.html>`_
"""
# Import python libraries
from copy import copy
import gzip
import io
import os
from zope.interface import provider

# Import twisted libraries
from twisted.logger import (globalLogPublisher, FilteringLogObserver, InvalidLogLevelError, Logger, LogLevel,
                            LogLevelFilterPredicate, ILogObserver, formatEvent,
                            textFileLogObserver, jsonFileLogObserver)
from twisted.internet import reactor

def static_var(varname, value):
    """
    Sets a static variable within a function. This is an easy way to set a default.

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import static_var

        @static_var("my_variable", 0)
        def some_function(x):
            some_function.my_variable += 1
            print(f"I've been called {some_function.my_variable}s times.")

    :param varname: variable name to create
    :param value: initial value to set.
    :return:
    """
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate


loggers = {}
open_files = {}
observers = {}
log_levels = {}
logFirstRun = True

logLevels = (
    "debug",
    "info",
    "warn",
    "error",
)

bcolor = {"debug": "\033[94m",
          "info": "\033[92m",
          "warn": "\033[93m",
          "error": "\033[91m",
          "default": "\033[33m",
         }



@provider(ILogObserver)
def simpleObserver(event):
    print(event)
    print((formatEvent(event)))


# log_format = lambda event: f"{formatTime(event['log_time'])} [{event['log_level'].name.upper()}]: {formatEvent(event)}"


@provider(ILogObserver)
def consoleLogObserver(event):
    print("[{0}{1}\033[39m-{2}]: {3}".format(bcolor[event["log_level"].name.lower()], event["log_level"].name.upper(), event["log_namespace"], formatEvent(event)))


@static_var("rotate_loop", None)
def get_logger(logname="yombolog", **kwargs):
    """
    Returns a logger object that allows logging of error messages.

    **Usage**:

    .. code-block:: python

       from yombo.core.log import get_logger

       logger = get_logger("module.ModuleName")
       logger.debug("Some status line, debug level items.")
       logger.info("ModuleName has finished starting is ready.")
       logger.warn("A warning!!")
       logger.error("Something really bad happened! I should quit.")

    :param logname: Name of the module or library.
    :type logname: string
    :return: logger object
    """
    global loggers
    global observers
    global log_levels
    global open_files

    # A simple cache or existing loggers...
    if logname in loggers:
        return loggers[logname]

    source = kwargs.get("source", logname)

    # Determine the logging level
    if len(loggers) == 0:
        try:
            from yombo.core.settings import logger_settings
            log_levels = logger_settings
        except ImportError:
            log_levels = []

    ini_log_level = "info"
    log_filter = LogLevelFilterPredicate()
    logname_search = copy(logname).lower()

    try:
        while len(logname_search) > 0 and len(log_levels):
            try:
                ini_log_level = log_levels[logname_search]
                break
            except KeyError:
                pass
            # This crazy line removes the last element in the string.
            logname_search = ".".join(logname_search.rsplit(".")[:-1])
    except InvalidLogLevelError:
        # Yell at the user if they specified an invalid log level
        loggers[logname].warn("yombo.toml file contained invalid log level {invalidLevel}, "
                              "level has been set to INFO instead.",
                              invalidLevel=log_levels[logname].lower())

    if isinstance(ini_log_level, str) is False:
        ini_log_level = "info"

    log_filter.setLogLevelForNamespace(logname, LogLevel.levelWithName(ini_log_level))

    # Set up logging
    consoleFilterObserver = FilteringLogObserver(consoleLogObserver, (log_filter,))

    logger = Logger(namespace=logname, source=source, observer=consoleFilterObserver)
    loggers[logname] = logger
    return loggers[logname]


def rotate_logs():
    reactor.callInThread(do_rotate_logs, "usr/log/yombo.json", "json")
    reactor.callInThread(do_rotate_logs, "usr/log/yombo.text", "text")


def do_rotate_logs(basefile, type):
    global observers

    if os.path.exists(basefile):
        if os.path.getsize(basefile) > 1000:
            for c in range(19, 0, -1):
                filename_cur = f"{basefile}.1"
                if c == 1 and os.path.exists(filename_cur):
                    with open(filename_cur) as src, gzip.open(f"{filename_cur}.gz", "wb") as dst:
                        dst.writelines(src)
                    os.remove(filename_cur)

                filename_cur = f"{basefile}.{c}.gz"
                filename_next = f"{basefile}.{c+1}.gz"
                if os.path.exists(filename_cur):
                    os.rename(filename_cur, filename_next)
            os.rename(basefile, f"{basefile}.1")


        if type == "json":
            globalLogPublisher.removeObserver(observers["json"])
            observers["json"] = jsonFileLogObserver(io.open("usr/log/yombo.json", "a"))
            globalLogPublisher.addObserver(observers["json"])


            globalLogPublisher.addObserver(jsonFileLogObserver(io.open(basefile, "a")))
        elif type == "text":
            observers["text"] = textFileLogObserver(io.open("usr/log/yombo.text", "a"))
            globalLogPublisher.addObserver(observers["text"])


            globalLogPublisher.removeObserver(textFileLogObserver())
            globalLogPublisher.addObserver(textFileLogObserver(io.open(basefile, "a")))
