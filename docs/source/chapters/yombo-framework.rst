###################
Gateway Framework
###################

The Yombo Gateway is a framework that allows users to quickly development
modules to implement automation of various devices around the home, office,
and anything in between.

Navigating the framework
************************

The gateway framework is split into four directories:

 * core - The most basic of functions to get stuff done. Module developers
   will mostly care about the helpers file.
 * lib - Libraries that run at startup and get the system going. Module
   developers will mostly care about the :doc:`messages <../core/message>`, :doc:`devices <../lib/devices>`, and
   :doc:`commands <../lib/commands>` (in that order). The other libraries are responsible for
   starting/stopping the service.
 * modules - Where downloaded or manually installed modules go.
 * usr - User data. Log files, database, cache, etc.

.. _core:

Core
****

Core modules are the base Yombo Gateway API functions. They provide the base
features to be used by libraries and modules.

.. toctree::
   :maxdepth: 1

   ../core/auth.rst
   ../core/db.rst
   ../core/exceptions
   ../core/filereader
   ../core/fuzzysearch
   ../core/helpers
   ../core/library
   ../core/log
   ../core/message
   ../core/module
   ../core/sqldict
   ../core/yombodict

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
   ../lib/commands.rst
   ../lib/configuration.rst
   ../lib/configurationupdate.rst
   ../lib/crontab.rst
   ../lib/devices.rst
   ../lib/downloadmodules.rst
   ../lib/loader.rst
   ../lib/startup.rst
   ../lib/times.rst
   ../lib/voicecmds.rst

