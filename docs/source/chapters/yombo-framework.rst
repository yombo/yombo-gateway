###################
Gateway Framework
###################

The Yombo Gateway is a framework that allows users to quickly development
modules to implement automation of various devices around the home, office,
and anything in between.

Navigating the framework
************************

The gateway framework is split into a few directories:

 * core - The most basic of functions to get stuff done. Module developers
   will mostly care about the helpers file.
 * lib - Libraries that run at startup and get the system going. Module
   developers will mostly care about the :doc:`messages <../core/message>`, :doc:`devices <../lib/devices>`, and
   :doc:`commands <../lib/commands>` (in that order). The other libraries are responsible for
   starting/stopping the service.
 * modules - Where downloaded or manually installed modules go.
 * usr - User data. Log files, database, cache, etc.
 * utils - Various utilities for getting things done.
 * ext - 3rd party extensions

.. _core:

Core
****

Core modules are the base Yombo Gateway API functions. They provide the base
features to be used by libraries and modules.

.. toctree::
   :maxdepth: 1

   ../core/auth.rst
   ../core/exceptions
   ../core/gwservice
   ../core/helpers
   ../core/library
   ../core/log
   ../core/message
   ../core/module

.. _lib:

Lib
***

Libraries build on the core modules and functions and provide essential
gateway services. There should be no need to access libraries directly,
instead, use a function from the :doc:`devices <../core/helpers>` module
as part of the core. An *exception* to this would be the CronTab and
Times libararies.

.. toctree::
   :maxdepth: 1

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
   ../lib/loader.rst
   ../lib/messages.rst
   ../lib/modules.rst
   ../lib/startup.rst
   ../lib/states.rst
   ../lib/statistics.rst
   ../lib/times.rst
   ../lib/voicecmds.rst

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
   ../utilssqldict

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
