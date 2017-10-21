======================
Yombo Gateway Overview
======================

The `Yombo Gateway Framework <https://yombo.net/>`_ is used for home and business automation. This
framework provides a base foundation that can be easily extended with module
to provide advanced functionality. Support for automation protocols occurs
through the use of modules; such as X10, Z-Wave, Insteon, Zigbee, etc.

This framework can also act a bridge between vendor protocols. For example,
an X10 controler can be used to control Z-Wave products.

`Modules <https://docs.yombo.net/Modules>`_ can:

* Extend the features of the framework through the use of `hooks <https://docs.yombo.net/Hooks>`_.
* Provide additional API features to other modules.
* Provide advanced automation rules and tasks.

=============
Documentation
=============

For new users, check out the quick start guide at https://docs.yombo.net/Gateway/Quick_start

Otherwise, full documentation can be found at https://docs.yombo.net/

To created intermediate to advanced automation rules or to extend the
capabilites of the gateway, consider `developing a module <https://docs.yombo.net/Developing_modules>`_.

============
Python 3.6.x
============

It's HIGHLY recommended to use latest Python 3.6 version. A simple script is located in yombo/install,
to setup:
1) Go to the yombo gateway directory (where this README file is located)
2) install/setup_pyenv.sh

On a Raspberry Pi 3, this will take quite a while. On a Raspberry Pi Zero, it's best to enjoy some
lunch or dinner at your favorite place or simply use
`one of our images <https://docs.yombo.net/Gateway/Raspberry_Pi_from_bare_metal>`_.

==================
Developing Modules
==================

Documentation for developing modules can be found at: https://docs.yombo.net/Developing_modules

A quick start guide to developing modules can be found her:
https://docs.yombo.net/Developing_modules/Building_your_first_module

===============================
Getting Help / Other Resources
===============================

For issue (tickets), feature requests, and roadmaps, visit
`Yombo Projects <https://projects.yombo.net/>`_ page.

==============
Privacy Policy
==============

The full privacy policy is located here: https://yombo.net/policies/privacy

In short: It's your data. We don't sell it or give it away, unless required to
do so by court order.

=========================
Yombo Gateway License 
=========================

By accessing or using any Yombo code, you are agreeing to the licensing terms as
listed in the LICENSE file. If you do not agree to these terms, do not
access or use this softare.

The Yombo Gateway source and/or binaries is governed by the Yombo Reciprocal
Public License Version 1.6. A copy is included in the LICENSE file distributed
with this software.

If you do not wish to release your source code of the software you build using Yombo
Gateway as the base, you may use Yombo Gateway source and/or binaries under the Yombo
Gateway Private License as described here:

https://yombo.net/policies/private-license
