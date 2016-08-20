###################
Gateway Framework
###################

The Yombo Gateway is a framework that allows users to quickly development
modules to implement automation of various devices around the home, office,
and anything in between.

Navigating the framework
************************

The gateway framework is split into a few directories:

 * core - The most basic of functions to get stuff done.
 * lib - Libraries that run at startup and get the system going. Module
   developers will mostly care about the :doc:`devices <../lib/devices>`, and
   :doc:`commands <../lib/commands>` (in that order). The other libraries are responsible for
   starting/stopping the service.
 * modules - Where auto-downloaded or manually installed modules go.
 * usr - User data. Log files, database, cache, etc.
 * utils - Various utilities for getting things done.
 * ext - 3rd party extensions.

.. _core:

Core
****

Core modules are the base Yombo Gateway API functions. They provide the base
features to be used by libraries and modules.

.. toctree::
   :maxdepth: 1

   ../core/exceptions.rst
   ../core/gwservice.rst
   ../core/library.rst
   ../core/log.rst
   ../core/module.rst

.. _lib:

Lib
***

Libraries build on the core modules and functions and provide essential
gateway services.

.. toctree::
   :maxdepth: 1

   ../lib/amqp.rst
   ../lib/amqpyombo.rst
   ../lib/atoms.rst
   ../lib/automation.rst
   ../lib/automationhelpers.rst
   ../lib/commands.rst
   ../lib/configuration.rst
   ../lib/configurationupdate.rst
   ../lib/crontab.rst
   ../lib/devices.rst
   ../lib/downloadmodules.rst
   ../lib/devicetypes.rst
   ../lib/gpg.rst
   ../lib/loader.rst
   ../lib/localdb.rst
   ../lib/modules.rst
   ../lib/mqtt.rst
   ../lib/sqldict
   ../lib/startup.rst
   ../lib/states.rst
   ../lib/statistics.rst
   ../lib/times.rst
   ../lib/yomboapi.rst
   ../lib/voicecmds.rst
   ../lib/webinterface.rst

.. _util:

Utils
*****

Various utilities to help the Yombo Gateway get things done.

.. toctree::
   :maxdepth: 1

   ../utils/utils.rst
   ../utils/decorators.rst
   ../utils/filereader
   ../utils/fuzzysearch
   ../utils/lookupdict
   ../utils/maxdict

.. _ext:

Ext
***

This directory contains external modules that ship with Yombo to support
the framework features. They are governed under their respective
licenses. See the COPYING file included with this distribution for more
information.

.. toctree::
   :maxdepth: 1

   ../ext/expiringdict.rst
   ../ext/hjson.rst
   ../ext/six.rst
   ../ext/twistar.rst
