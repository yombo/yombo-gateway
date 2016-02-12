.. configuring-the-gateway:

####################################
Configuring the Gateway
####################################

Gateway setup and configuration takes place by using the ``./config``
command in the root of the yombo-gateway directory.

Execute: ``./config`` 

This tool can perform the following functions:

* Complete the setup of a new gateway.
* Change the configuration of a gateway. Note: Most configuration changes
  are handled through the mobile or desktop applications.
* Reset the gateway back to it's default settings.

**If are you setting up a new gateway, you are done.** The remaining sections
explain making configuration changes that can normally be performed though the
mobile or desktop applications.

yombo.ini
=========

.. rst-class:: floater

.. warning::

  Deleting the yombo.ini alone will not delete all settings. Run the
  ``./config`` tool to complete this action.

.. rst-class:: floater

.. warning::

  If you update the yombo.ini file while the **gateway is running**, any changes
  will be **lost**.

The majority of the time, the default settings will work fine. However, the
gateway exposes many settings that allows various options to be tweaked. Some
caution is needed: *you can break things!*

The yombo.ini file contains various configuration settings. For details about
it's contents see the Yombo Wiki for
`yombo.ini <https://projects.yombo.net/projects/gateway/wiki/Yomboini>`_

Only the basic configurations are stored in the yombo.ini file, the remaining
configurations (devices, commands, etc) are stored in a local database file
managed by the gateway.

The gateway was designed to be easily updated using various tools, including
the mobile app or through the Yombo API. It's recommended to use those tools
instead of directly modifying the yombo.ini file.

Running the gateway
===================

The gateway can be started by executing the ``./yombo.sh`` or ``yombod.bat`` file.

On startup the gateway will:

* Read to the yombo.ini file
* Connect to Yombo Servers for any configuration updates
* Download any required modules
* Begin processing automation tasks

Advanced configurations
=======================================

.. rst-class:: floater

.. note::

  Using the features listed below should only be used if  you are developing
  a module.

Creating Local Modules
----------------------

For those wanting to create a local module and not make it publicly available,
you can instruct the gateway to load it by creating a ``localmodules.ini``
at gateway root directory. This allows the gateway to run modules inside of
the Yombo Gateway framework without registering the module.

To get started building your first module, see:
`Building your first module <https://projects.yombo.net/projects/modules/wiki/Building_your_first_module>`_.

For each module to load, edit the ``localmodules.ini`` file and create a new
section. Within the section. Here's an example:

.. code-block:: guess

   [LogReader]
   label=LogReader
   type=logic
   logfile="logreader.log"

The ``label`` is the class name of the module, which is typically the module
name, but with mixed case. Type is one of:

* logic - Used to denote it's some sort of automation logic control.
* command - A command processor - such as X10, insteon, Z Wave commands.
* interface - A module that bridges a command module to some interface - such
  as a USB port or network location.

Anything other than "label" and "type" are considered module variables and will
be accessable inside the module through: ``self._ModVariables['variable_name']``
See :ref:`YomboModule` for details.