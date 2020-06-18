# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Responsible for collecting command line arguments and reading the yombo.toml/etc/yombo_meta.toml files. The

arguments called to Yombo Gateway and get settings from
yombo.toml and it's matching meta data.

Handles command line arguments and basic settings.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2018-2020 by Yombo
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/settings.html>`_
"""
from typing import ClassVar
import tomlkit as tk

from yombo.classes.dotdict import DotDict

arguments: dict = {"app_dir": None,  # Defaults to pass tests
                   "working_dir": None,
                   }
logger_settings: ClassVar[DotDict] = DotDict()


def init(incoming_arguments):
    """
    Called by yombo.tac to handle command line arguments (as stdin, not actual
    command line arguments).

    This also reads the yombo.toml file which is used for the logger to get it's configs.
    It shouldn't be used for anything else.

    :param incoming_arguments:
    :return:
    """
    global arguments
    global logger_settings
    arguments = incoming_arguments

    try:
        yombo_toml_path = f'{arguments["working_dir"]}/yombo.toml'
        toml_file_pointer = open(yombo_toml_path, 'r')
        yombo_toml = tk.parse(toml_file_pointer.read())
        if "logging" in yombo_toml:
            logger_settings.update(yombo_toml["logging"])
            logger_settings = DotDict({k.replace("_", "."): v for k, v in yombo_toml["logging"].items()})
        else:
            logger_settings = DotDict()
    except:
        pass
