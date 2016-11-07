# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""
Handles logging functions.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
import ConfigParser
from zope.interface import provider
import io

# Import twisted libraries
from twisted.logger import FileLogObserver, FilteringLogObserver, globalLogPublisher, InvalidLogLevelError, \
    Logger, LogLevel, LogLevelFilterPredicate, ILogObserver, formatEvent, formatTime, jsonFileLogObserver

loggers = {}
configCache = {}
logFirstRun = True

logLevels = (
    "debug",
    "info",
    "warn",
    "error",
)

bcolor = {'debug':'\033[94m',
        'info':'\033[92m',
        'warn':'\033[93m',
        'error':'\033[91m',
        'default':'\033[33m',
        }

@provider(ILogObserver)
def simpleObserver(event):
#    event['log_system'] = "asdf"
    print event
    print(formatEvent(event))

logFormat = lambda event: u"{0} [{1}]: {2}".format(formatTime(event["log_time"]), event["log_level"].name.upper(),
                                                   formatEvent(event))

@provider(ILogObserver)
def consoleLogObserver(event):
    print u"[{0}{1}\033[39m-{2}]: {3}".format(bcolor[event["log_level"].name.lower()], event["log_level"].name.upper(), event["log_namespace"], formatEvent(event))


def get_logger(logname='yombolog', **kwargs):
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

    # A simple cache or existing loggers...
    if logname in loggers:
        return loggers[logname]

    global configCache

    loglevel = None
    source = kwargs.get('source', logname)
    json = kwargs.get('source', False)

    # Determine the logging level
    if len(loggers) == 0:
        config_parser = ConfigParser.SafeConfigParser()
        try:
            fp = open('yombo.ini')
            config_parser.readfp(fp)
            ini = config_parser
            for option in ini.options('logging'):
                value =  ini.get('logging', option)
                configCache[option] = value
            fp.close()
        except IOError:
            pass
        except ConfigParser.NoSectionError:
            pass

    logFilter = LogLevelFilterPredicate()
    try:
        if logname in configCache:
          iniLogLevel = configCache[logname].lower()
          logFilter.setLogLevelForNamespace(logname, LogLevel.levelWithName(iniLogLevel))
#        else:
#          iniLogLevel = 'info'
#          iniLogLevel = False
#        print "iniLogLevel: %s, logname: %s" % (iniLogLevel, logname)
        invalidLogLevel = False
    except InvalidLogLevelError:
        logFilter.setLogLevelForNamespace(logname, LogLevel.info)
        invalidLogLevel = True

    # Yell at the user if they specified an invalid log level
    if invalidLogLevel:
        loggers[logname].warn("yombo.ini file contained invalid log level {invalidLevel}, level has been set to INFO instead.",
                           invalidLevel=configCache[logname].lower())

    # Set up logging
    consoleFilterObserver = FilteringLogObserver(consoleLogObserver, (logFilter,))

    logger = Logger(namespace=logname, source=source, observer=consoleFilterObserver)

    global logFirstRun
    if logFirstRun is True:
      logFirstRun = False
      # This doesn't appear to be working yet...
#      globalLogPublisher.addObserver(jsonFileLogObserver(io.open("yombo.log.json", "a")))

    loggers[logname] = logger
    
    return loggers[logname]

def reset_log_levels():
    """
    Used to reset the logs to their proper levels after
    configurations are downloaded. Also called when
    recieved a config update.
    """
    #TODO: Test this!
    from yombo.core.helpers import getConfigValue
    global loggers
    global logLevels

    for key, aLog in loggers:
        newLevel = getConfigValue('logging', key, 10)
        aLog.setLevel(newlevel)


