.. configuring-the-gateway:

####################################
Configuraing the Gateway
####################################

Before the gateway can do anything, it needs be configured.

=========================
Configuring the Gateway
=========================

Gateway setup and configuration takes place by using the ``./config`` command
in the root of the yombo-gateway directory.

========
Overview
========

The steps to configuring the gateway:

# Create new gateway using mobile app.
# Run ``./config`` file to complete setup.

./config
========

The ``./config`` file manages the gateway configuration. The user must
create the new gateway using the mobile app first. This tool wll perform
the following:

* Complete the setup of a new gateway.
* Change the configuration of a gateway. Note: Most configuration changes
  are handled through the mobile app.

yombo.ini
=========

The yombo.ini file contains various configuration data to run the gateway. For
details about it's contents see 
`yombo.ini <https://projects.yombo.net/projects/gateway/wiki/Yomboini>`_

Only the basic configurations are stored in the yombo.ini file, the remaining
configurations are stored in a local database file managed by the gateway.

.. warning::

  If you update the yombo.ini file while the **gateway is running**, any changes
  will be lost.

.. warning::

  If you want to delete all the settings, deleting the yombo.ini alone will
  not do this. Run the ``./config`` tool to complete this action for you.

Changing Settings
-----------------

The gateway was designed to be easily updated using various tools, including
the mobile app or through the Yombo API.

===================
Running the gateway
===================

The gateway can be started by executing the ``./yombo.sh`` or ``yombod.bat`` file.

On startup the gateway will:

# Read to the yombo.ini file
# Connect to Yombo Servers for any configuration updates
# Download remaining configurations for modules, devices, etc.

=======================================
Including modules with localmodules.ini
=======================================

.. note::

  Using the localmodules.ini is an advanced feature. This should only be used if
  you are developing a local module.

This file allows the loading and running of locally installed modules and bypasses
the Yombo infrastructure to run modules inside of the Yombo Gateway framework.

Use of this should be reserved for custom logic modules, or for developing a module
for publishing/posting later.  See ``Your First Module`` for directions on creating
the required files and where to place them.

The ``localmodules.ini`` is placed at gateway root directory.

Structure
=========

For each module to load, create a new section, this is typically the name of
the module.  Within the section, the label is the class name of of the modules,
which is typically the module name with mixed case.  Also, there is a "type"
field, which is one of:

* logic - Used to denote it's some sort of automation logic control.
* more to be documented later...

Anything other than "label" and "type" are considered module variables and will
be accessable by the standard module methods. See :ref:`YomboModule` for details.

Example section:

.. code-block:: guess

   [LogReader]
   lable=LogReader
   type=logic
   logfile="logreader.log"

