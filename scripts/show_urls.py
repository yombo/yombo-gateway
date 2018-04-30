#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.append("../")

print(constants.VERSION)

import configparser

try:
    config_parser = configparser.ConfigParser()
    config_parser.read('../yombo.ini')

    for section in config_parser.sections():
        if section not in self.configs:
            continue
        for option in config_parser.options(section):
            if option not in self.configs[section]:
                continue
            values = msgpack.loads(b64decode(config_parser.get(section, option)))
            self.configs[section][option] = dict_merge(self.configs[section][option], values)
except IOError as e:
    logger.warn("CAUGHT IOError!!!!!!!!!!!!!!!!!!  In reading meta: {error}", error=e)
except configparser.NoSectionError:
    logger.warn("CAUGHT ConfigParser.NoSectionError!!!!  IN saving. ")

