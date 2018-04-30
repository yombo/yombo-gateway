#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from os.path import dirname, abspath
yombo_path = dirname(dirname(abspath(__file__)))
print(yombo_path)
sys.path.append("%s/" % yombo_path)
import yombo.constants as constants
print(constants.VERSION)
