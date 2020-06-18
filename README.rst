======================
Yombo Gateway Overview
======================

The `Yombo Gateway Framework <https://yombo.net/>`_ is used for home and
business automation. This framework provides a base foundation that can be
easily extended with modules (plugins) to provide advanced functionality.
Support for automation protocols occurs through the use of modules; such
as X10, Z-Wave, Insteon, Zigbee, etc.

This framework can also act a bridge between vendor protocols. For example,
an X10 controller can be used to control Z-Wave products.

`Modules <https://yg2.in/about_modules>`_ can:

* Extend the features of the framework through the use of
  `hooks <https://yg2.in/hooks>`_.
* Provide additional API features to other modules.
* Provide advanced automation rules and tasks.

=============
Documentation
=============

For new users, check out the `quick start guide <https://yg2.in/start>`_.

Otherwise, see the `full documentation <https://yg2.in/docs>`_.

To created intermediate to advanced automation rules or to extend the
capabilites of the gateway, consider
`developing a module <https://yg2.in/dev>`_.

============
Python 3.7.x
============

Yombo Gateway only works on python 3.7.x and above due to features being used. If
you are not using the `quick start <https://yg2.in/start>`
guide to get started, you can just install python 3.7.x using the
pyenv_setup.sh script file:

1) Go to the yombo gateway directory (where this README file is located)
2) bash scripts/pyenv_setup.sh

On a Raspberry Pi 3, this will take quite a while. On a Raspberry Pi 1/2/Zero, it's
best to enjoy some lunch or dinner at your favorite place.

==================
Developing Modules
==================

Full documentation for developing modules can be found at:
`developing modules <https://yg2.in/dev>`_.

Module quick start guide: `Building your first module <https://yg2.in/dev1>`_

===============================
Getting Help / Other Resources
===============================

* `Issue (tickets) <https://yg2.in/issues>`_
* `Feature requests & road maps <https://yg2.in/projects>`_

==================
Database support
==================

Yombo gateway is primarily developed using SQLite, however, the base structure
to add additional database backends is available.

To use mysql or mariadb, you must install the 'libmysqlclient-dev' package:

sudo apt install libmysqlclient-dev

If you are using pyenv (most automated installs do); change to the Yombo
gateway install directory, then:

pip3 install mysqlclient

Otherwise:

sudo pip3 install mysqlclient

==============
Privacy Policy
==============

The full privacy policy is located here:
https://yombo.net/policies/privacy_policy

In short: It's your data. We don't sell it or give it away, unless required
to do so by court order.

=========================
Yombo Gateway License
=========================

By accessing or using any Yombo code, you are agreeing to the licensing
terms as listed in the LICENSE file. If you do not agree to these terms,
do not access or use this software.

The Yombo Gateway source and/or binaries is governed by the Yombo
Reciprocal Public License Version 1.6. A copy is included in the LICENSE file
distributed with this software.
