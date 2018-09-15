# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Responsible for collecting arguments called to Yombo Gateway and gettings settings from
yombo.ini and it's matching meta data.

.. module:: yombo.core.settings
   :synopsis: Arguments and configurations.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: 2018 by Yombo
:license: LICENSE for details.
"""
import configparser
import os
from shutil import copy2 as copyfile
from time import localtime, strftime

# Import Yombo libraries
from yombo.utils import is_string_bool

yombo_ini = {}
arguments = {}

def init(incoming_arguments):
    """
    Called by yombo.tac to handle command line arguments (as stdin, not actual
    command line arguments). This also reads the yombo.ini file which act act
    a bootstrap configs library until the real configs library is started.

    The configs library will call read_yombo_ini() to read the actual contents.

    :param incoming_arguments:
    :return:
    """
    global arguments
    arguments = incoming_arguments
    # Now we load the basic yombo.ini file. This is here so we don't have to load and
    # process this multiple times before the actual configuration library is loaded.

    working_dir = arguments['working_dir']
    ini_norestore = arguments['norestoreini']
    yombo_ini_path = "%s/yombo.ini" % working_dir
    if os.path.exists(yombo_ini_path):
        if os.path.isfile(yombo_ini_path) is False:
            try:
                os.remove(yombo_ini_path)
            except Exception as e:
                print("'yombo.ini' file exists, but it's not a file and cannot be deleted!")
                return False
            if ini_norestore:
                restore_backup_yombi_ini()
        else:
            if os.path.getsize(yombo_ini_path) < 2:
                print('yombo.ini appears corrupt, attempting to restore from backup.')
                if ini_norestore:
                    restore_backup_yombi_ini()
            elif arguments['restoreini'] is True:
                restore_backup_yombi_ini()
    else:
        if ini_norestore:
            restore_backup_yombi_ini()

    last_yombo_ini_read = read_yombo_ini()
    if last_yombo_ini_read is False:
        yombo_ini = False


def read_yombo_ini():
    """
    Called to actually read the yombo.ini file. Makes a backup copy before it's read.

    :return:
    """
    global yombo_ini
    global arguments
    working_dir = arguments['working_dir']
    yombo_ini_path = "%s/yombo.ini" % working_dir

    yombo_ini = {}
    try:
        timeString = strftime("%Y-%m-%d_%H:%M:%S", localtime())
        copyfile(yombo_ini_path, "%s/bak/yombo_ini/%s_yombo.ini" % (working_dir, timeString))

        config_parser = configparser.ConfigParser()
        config_parser.optionxform = str
        config_parser.read(yombo_ini_path)
        for section in config_parser.sections():
            yombo_ini[section] = {}
            for option in config_parser.options(section):
                value = config_parser.get(section, option)
                if value == "None":
                    value = None
                else:
                    try:
                        value = is_string_bool(value)
                    except:
                        try:
                            value = int(value)
                        except:
                            try:
                                value = float(value)
                            except:
                                value = str(value)
                yombo_ini[section][option] = value
    except IOError:
        print("yombo.ini doesn't exist and didn't (or wasn't allowed to) find a backup copy.")
        return False
    except configparser.NoSectionError as e:
        print("CAUGHT ConfigParser.NoSectionError!!!!  In Loading. %s" % str(e))
        return False
    else:
        # self._Atoms.set('configuration.yombo_ini.found', True)
        # print("yombo.ini: %s" % yombo_ini)
        return True


def restore_backup_yombi_ini(arguments):
    """
    Restores the last backup if needed/requested.

    :param arguments:
    :return:
    """
    working_dir = arguments['working_dir']
    yombo_ini_path = "%s/yombo.ini" % working_dir
    backup_yombo_ini_path = "%s/bak/yombo_ini/" % working_dir

    dated_files = [(os.path.getmtime("%s/%s" % (backup_yombo_ini_path, fn)), os.path.basename(fn))
                   for fn in os.listdir(backup_yombo_ini_path)]
    dated_files.sort()
    dated_files.reverse()
    print("# Attempting to restore yombo.ini file from backup.")
    if len(dated_files) > 0:
        for i in range(0, len(dated_files)):
            the_restore_file = "%s/%s" % (backup_yombo_ini_path, dated_files[i][1])
            if os.path.getsize(the_restore_file) > 100:
                copyfile(the_restore_file, yombo_ini_path)
                print("# - yombo.ini file restored from previous backup: %s" % the_restore_file)
                return True
    return False
