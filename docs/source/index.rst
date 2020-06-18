.. title:: Yombo Python API Reference

=================================
Yombo Automation Python Reference
=================================

Release |release|
(`Release notes <https://yombo.net/release_notes/gateway/0.24.0>`_)

The Yombo Gateway is a framework that allows users to quickly develop
modules to implement automation of various devices around the home, office,
and anything in between.

Documentation Links
=======================
* **End user** - For users getting started, visit the
  `User Quick Start Guide <https://yombo.net/docs/gateway/quick_start>`_.
* **Developers** - For developing modules to add enhanced automation rules or
  to add support for additional automation protocols and devices, visit the
  `Yombo Development Documentation <https://yombo.net/docs/developing_modules>`_

Additional Links
========================
* `Yombo.net <https://yombo.net/>`_
* `End user documentation <https://yombo.net/docs>`_
* `Building your first module - a complete guide <https://yombo.net/docs/developing_modules/building_your_first_module>`_


Overview
========

**Yombo** automation allows simple DIY automation. Setup and configuration is completed using a browser
instead of getting lost in complicated text files.

The true power of the system comes from building simple modules that even non-programmers can write. These
are simple python files that nearly anyone can write.  This example turns on a porch light when it's dusk
and turns it off at 10:30pm:

.. code-block:: python

    #  A simple custom module that manages the porch light.
    def _time_event_(**kwargs):
        """
        Called when a time of day event occurs.
        """
        event = kwargs['value']  # Can be 'now_light', 'now_twilight', 'now_not_dawn', etc.
        if (event == 'now_dusk'):
           porch_light = self._Device['porch light']
           porch_light.command(command='on')  # turn on now

           off_time = self._Times.get_next('hour=22', 'minute'=30')  # get epoch for the next 10:30pm time.
           porch_light.command(command='off', not_before=off_time)  # turn of at 10:30pm

Navigating the framework
===========================

The gateway framework is split into a few directories:

 * :ref:`framework_ext` - 3rd party extensions.
 * :ref:`framework_constants` - Used to keep various attributes consistent across the Yombo Gateway framework.
 * :ref:`framework_core` - Basic functions used by various libraries.
 * :ref:`framework_lib` - Libraries provide all the services and tools to manage the system, including sending
   :doc:`commands <../lib/commands>` to :doc:`devices <../lib/devices/devices>`.
 * :ref:`framework_mixins` - Mixins add various features to a class.
 * :ref:`framework_modules` - Extend the features of the Yombo gateway.
 * :ref:`framework_utils` - Various utilities for getting things done.

.. _framework_frontend:

Frontend Application
==========================

The :ref:`frontend application <frontend_summary>` is a Vue + Nuxt web application used for interacting with the gateway.
This includes gateway configuration and device management. It also used as a control panel to
view and control devices. The application is only accessible once the user has authenticated
and logged in and will be displayed automatically after authentication.

.. _framework_core:

Core
=====

Core modules are the base Yombo Gateway API functions. They provide the base
features to be used by libraries and modules.

.. toctree::
   :maxdepth: 1

   ../core/entity.rst
   ../core/exceptions.rst
   ../core/gwservice.rst
   ../core/library.rst
   ../core/log.rst
   ../core/module.rst
   ../core/schemas.rst
   ../core/settings.rst

.. _framework_lib:

Libraries
=============

Libraries build on the core modules and functions and provide essential
gateway services, such as routing commands from devices, talking to other
IoT devices, etc.

.. toctree::
   :maxdepth: 1

   ../lib/amqp/_summary.rst
   ../lib/amqpyombo/_summary.rst
   ../lib/authkeys/_summary.rst
   ../lib/atoms.rst
   ../lib/automation.rst
   ../lib/cache.rst
   ../lib/calllater.rst
   ../lib/commands.rst
   ../lib/configs.rst
   ../lib/crontab.rst
   ../lib/devicecommands/_summary.rst
   ../lib/devices/_summary.rst
   ../lib/devicecommandinputs.rst
   ../lib/devicetypecommands.rst
   ../lib/devicestates/_summary.rst
   ../lib/devicetypes/_summary.rst
   ../lib/discovery.rst
   ../lib/downloadmodules.rst
   ../lib/encryption.rst
   ../lib/events.rst
   ../lib/files/_summary.rst
   ../lib/gateways/_summary.rst
   ../lib/gpg/_summary.rst
   ../lib/inputtypes/_summary.rst
   ../lib/hash.rst
   ../lib/hashids.rst
   ../lib/intents.rst
   ../lib/loader.rst
   ../lib/localdb/_summary.rst
   ../lib/localize.rst
   ../lib/locations.rst
   ../lib/moduledevicetypes.rst
   ../lib/modules.rst
   ../lib/modulesinstalled.rst
   ../lib/mosquitto.rst
   ../lib/mqtt/_summary.rst
   ../lib/mqttusers.rst
   ../lib/mqttyombo/_summary.rst
   ../lib/nodes/_summary.rst
   ../lib/notifications.rst
   ../lib/permissions.rst
   ../lib/queue.rst
   ../lib/requests.rst
   ../lib/roles/_summary.rst
   ../lib/scenes.rst
   ../lib/sqldicts.rst
   ../lib/sslcerts/_summary.rst
   ../lib/startup.rst
   ../lib/states.rst
   ../lib/statistics/_summary.rst
   ../lib/storage.rst
   ../lib/systemdatahandler.rst
   ../lib/tasks.rst
   ../lib/template.rst
   ../lib/times.rst
   ../lib/tools.rst
   ../lib/users/_summary.rst
   ../lib/validate.rst
   ../lib/variabledata.rst
   ../lib/variablefields.rst
   ../lib/variablegroups.rst
   ../lib/webinterface/_summary.rst
   ../lib/websessions/_summary.rst
   ../lib/yomboapi/_summary.rst

.. _framework_mixins:

Mixins
=========

Mixins add various features to a class. For example, add the authmixin to treat
the object as something can be used for authentication.

.. toctree::
   :maxdepth: 1

   ../mixins/amqp_mixin.rst
   ../mixins/auth_mixin.rst
   ../mixins/child_storage_accessors_mixin.rst
   ../mixins/library_db_child_attributes_mixin.rst
   ../mixins/library_db_child_mixin.rst
   ../mixins/library_search_mixin.rst
   ../mixins/parent_storage_accessors_mixin.rst
   ../mixins/permission_mixin.rst
   ../mixins/roles_mixin.rst
   ../mixins/systemdata_mixin.rst
   ../mixins/user_mixin.rst

.. _framework_constants:

Constants
=========

Constants help keep consistency across the framework. To view all the
contents, visit the
`Constants source @ GitHub <https://github.com/yombo/yombo-gateway/tree/master/yombo/constants>`_

.. toctree::
   :maxdepth: 1

   ../frontend/summary.rst

.. _framework_modules:

Modules
=======

System modules, user modules, and downloaded modules go into the modules folder. These
extend the capabilites of the gateway and provide the gateway the ability to
communicate with various devices over various protocols.

For a list of modules available to be installed by end users:
`Available Modules <https://yg2.in/f_gdoc_modules>`_

.. _framework_utils:

Classes
=========

Various helper classes that can make life easier.

.. toctree::
   :maxdepth: 1

   ../classes/caseinsensitivedict.rst
   ../classes/dictobject.rst
   ../classes/dotdict.rst
   ../classes/filecontainer.rst
   ../classes/fuzzysearch.rst
   ../classes/imagecontainer.rst
   ../classes/jsonapi.rst
   ../classes/lookupdict.rst
   ../classes/maxdict.rst
   ../classes/sliceableordereddict.rst
   ../classes/triggerdict.rst

Utilities
===========

Various utilities to help the Yombo Gateway get things done.

.. toctree::
   :maxdepth: 2

   ../utils/caller.rst
   ../utils/color.rst
   ../utils/converters.rst
   ../utils/datatypes.rst
   ../utils/datetime.rst
   ../utils/decorators/_summary.rst
   ../utils/dictionaries.rst
   ../utils/ffmpeg/_summary.rst
   ../utils/hookinvoke.rst
   ../utils/networking.rst
   ../utils/utils.rst

.. _framework_ext:

3rd party extensions
=====================

This directory contains external modules that ship with Yombo to support
the framework features. They are governed under their respective
licenses. See the COPYING file included with this distribution for more
information.

Note: Many of the extensions don't properly display here, visit
`Extensions source @ GitHub <https://github.com/yombo/yombo-gateway/tree/master/yombo/ext>`_

.. toctree::
   :maxdepth: 1

   ../ext/base62.rst
   ../ext/expiringdict.rst
   ../ext/gnupg.rst
   ../ext/ipy.rst
   ../ext/magic.rst
   ../ext/txrdq.rst
   ../ext/validators.rst

License
========================

Yombo license information.

.. toctree::
   :maxdepth: 1

   ../chapters/license.rst

Contributing to Developer Documentation
========================================

The Yombo Gateway uses self documenting code. All documentation found on this website is generated directly from
the `source code itself <https://github.com/yombo/yombo-gateway>`_.

Making changes is easy: simply find the section of the code and update the code comment. This website is periodically
updated from the source code.

Yombo PyDoc Links
-----------------

* :ref:`Full index <genindex>`
* :ref:`Search page <search>`

Last updated: |today|
