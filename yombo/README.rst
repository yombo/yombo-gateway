=====================
Yombo Directory
=====================

Contains the core functions, libraries to run the gateway
and a place to put modules.  See online documentation for
more details.
https://yg2.in/dev

classes
---------
Various helper classes.

constants
---------
Constants help maintain consistency across the Yombo Gateway framework.

core
------
Contains base functions and various Yombo Gateway APIs. Most libraries and
modules are built. `Core reference <https://yg2.in/dev_core>`_

ext
---------
External resources used by Yombo. See the
`COPYING <https://github.com/yombo/yombo-gateway/blob/master/COPYING>`_ file
for more details.

frontend
----------
Frontend web application written in javascript using the Vue & Nuxt framework.

lib
----------
The primary framework of the Yombo Gateway is in the libraries.
`Library reference <https://yg2.in/dev_lib>`_

locale
----------
Translation files for the backend and front are stored here.

mixins
----------
Common methods that extends various libraries.

modules
----------
The gateway ships with a few core modules, however, when a user requests
modules to be installed, they are placed here.

See more:

* `Available modules <https://yg2.in/mod>`_
* `Developing modules <https://yg2.in/dev>`_

utils
----------
Misc utility functions to help Yombo Gateway get things done. See:
`Development utilities <https://yg2.in/dev_util>`_
