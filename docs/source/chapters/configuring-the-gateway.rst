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

yombo.ini
=========

.. warning::

  If you want to delete all the settings, deleting the yombo.ini alone will
  not do this. Run the ``./config`` tool to complete this action.

.. rst-class:: floater

.. warning::

  If you update the yombo.ini file while the **gateway is running**, any changes
  will be lost.

The yombo.ini file contains various configuration data to run the gateway. For
details about it's contents see the Yombo Wiki for
`yombo.ini <https://projects.yombo.net/projects/gateway/wiki/Yomboini>`_

Only the basic configurations are stored in the yombo.ini file, the remaining
configurations are stored in a local database file managed by the gateway.


Changing Settings
-----------------

The gateway was designed to be easily updated using various tools, including
the mobile app or through the Yombo API. It's recommended to use thse tools
instead of directly modifying the yombo.ini file.

Running the gateway
===================

The gateway can be started by executing the ``./yombo.sh`` or ``yombod.bat`` file.

On startup the gateway will:

* Read to the yombo.ini file
* Connect to Yombo Servers for any configuration updates
* Download any required modules
* Begin processing autoamtion tasks

Advanced configurations
=======================================

.. rst-class:: floater

.. note::

  Using the features listed below should only be used if  you are developing
  a module.

Creating Local Modules
----------------------

This file allows the loading and running of locally installed modules and bypasses
the Yombo infrastructure. This allows the gateway to run modules inside of the
Yombo Gateway framework without registering the module.

Use of this should be reserved for custom logic modules, or for developing a module
for publishing/posting later. See `Building your first module <https://projects.yombo.net/projects/modules/wiki/Building_your_first_module>`_.

The ``localmodules.ini`` is placed at gateway root directory.

For each module to load, edit the ``localmodules.ini`` file and create a new section.
Within the section, the label is the class name of of the modules, which is
typically the module name with mixed case.  Also, there is a "type"
field, which is one of:

* logic - Used to denote it's some sort of automation logic control.
* More to be defined later.

Anything other than "label" and "type" are considered module variables and will
be accessable by the standard module methods. See :ref:`YomboModule` for details.

Example section:

.. code-block:: guess

   [LogReader]
   label=LogReader
   type=logic
   logfile="logreader.log"

