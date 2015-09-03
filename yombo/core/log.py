#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""
Handles logging functions. These functions are in dire need of attention:

.. todo::

   Revamp this to be able to control specific logs. Should be able to set
   the logging level of individual modules, all modules, specific libraries,
   all libraries, core code.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2015 by Yombo.
:license: LICENSE for details.
"""
#TODO: Migrate to new twisted 15.x logging system.
# Import python libraries
import logging
import ConfigParser

from twisted.internet import fdesc

loggers = {}    
configCache = {}
logLevels = {'GARBAGE':1,
             'TRACE':5,
             'DEBUG':10,
             'INFO':20,
             'WARNING':30,
             'ERROR':40,
             'CRITICAL':50}

def getLogger(logname='yombolog'):
    """
    Returns a logger object that allows logging of error messages.

    **Usage**:

    .. code-block:: python

       from yombo.care.log import getLogger

       logger = getLogger("module.ModuleName")
       logger.debug("Some status line, debug level items.")
       logger.info("ModuleName has finished starting is ready.")
       logger.warning("A warning!!")
       logger.error("Something really bad happened! I should quit.")
       
    :param logname: Name of the module or library.
    :type logname: string
    :return: logger object
    """
    global loggers
    global logLevels
    wasempty = None

#    logname = 'twisted'
    if len(loggers) == 0:
        wasempty = True
#        print "$$$$$$$$$$$$$$$$$$$ No logs!!"
        logging.TRACE = 5
        logging.GARBAGE = 1
        logging.addLevelName(logging.TRACE, 'TRACE')

        global configCache
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

    if logname in loggers:
#        print "$$$$$$$$$$$$$$$$$$$ Returing log: %s" % logname
        return loggers[logname]
    else:
#        print "$$$$$$$$$$$$$$$$$$$ NEW log: %s" % logname
        if logname in configCache:
            loglevel = configCache[logname]
        else:
            loglevel = 'TRACE'
        logger = logging.getLogger(logname)
        setattr(logger, 'trace', lambda *args: logger.log(5, *args))
        tempLevel = logLevels.get(logname, 20)
        logger.setLevel(tempLevel) # get log level, default is INFO

#        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(message)s")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s-%(name)s - %(filename)s:%(lineno)s - %(message)s")

#        fh = logging.RotatingFileHandler('usr/log/log.txt', maxBytes=10000000, backupCount=5)
#        fh = logging.FileHandler('usr/log/log.txt')
#        fdesc.setNonBlocking(fh.stream)
#        fh.setLevel(tempLevel)
#        fh.setFormatter(formatter)
#        logger.addHandler(fh)

#        db = SQLiteHandler('usr/sql/log.sqlite3')
#        db.setLevel(tempLevel)
#        db.setFormatter(formatter)
#        logger.addHandler(db)

        ch = logging.StreamHandler()
#        fdesc.setNonBlocking(ch.stream)
        ch.setLevel(tempLevel)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        loggers[logname] = logger

#    if wasempty == True:
#        print "$$$$$$$$$$$$$$$$$$$ was empty!"
#        from twisted.python import log
#        observer = log.PythonLoggingObserver("yombolog")
#        observer.start()

    return loggers[logname]

def resetLogLevels():
    """
    Used to reset the logs to their proper levels after
    configurations are downloaded. Also called when
    recieved a config update.
    """
    from yombo.core.helpers import getConfigValue
    global loggers
    global logLevels

    for key, aLog in loggers:
        newLevel = getConfigValue('logging', key, 10)
        aLog.setLevel(newlevel)

import sqlite3

class SQLiteHandler(logging.Handler): # Inherit from logging.Handler
    def __init__(self, filename):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Our custom argument
        self.db = sqlite3.connect(filename) # might need to use self.filename
        self.db.execute("""CREATE TABLE IF NOT EXISTS logs(
            created text,
            filename text,
            funcname text,
            levelname text,
            lineno text,
            module text,
            message text )""")
        self.db.commit()

    def emit(self, record):
        self.db.execute('INSERT INTO logs(created, filename, funcname, levelname, lineno, module, message) VALUES(?,?,?,?,?,?,?)',
            (record.created, record.filename, record.funcName, record.levelname, record.lineno, record.module, record.message))
        self.db.commit()

