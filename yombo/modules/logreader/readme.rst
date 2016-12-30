Usage
=====

This module extends the capabilities of the `Yombo Gateway <https://yombo.net/>`_
by adding the ability to monitor a text file for device commands.

Logreader
=========

With this module, you can simple echo in a command to be peformed:

echo "bathroom light on" >> monitored_file.txt

This is useful if you want basic scripts or other utilities to control automation
devices.

.. warning::

   Be sure to grant write access only to users and applications that should
   be able to send commands.

The actual commands are processed by the YomboBot module and is required.

Installation
============

Simply mark this module as being used by the gateway, and the gateway will
download and install this module automatically.

Requirements
============

YomboBot module is required for parsing the commands.

License
=======

The `Yombo <https://yombo.net/>`_ team and other contributors
hopes that it will be useful, but WITHOUT ANY WARRANTY; without even the
implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See LICENSE file for full details.
