.. configuring-the-gateway:

####################################
Configuring the Gateway
####################################

After downloading the gateway, simply executing the ``./yombo.sh`` or
``yombod.bat`` file. You will see something like this:

..

   2016-08-18T15:23:56 ###########################################################
   2016-08-18T15:23:56 #                                                         #
   2016-08-18T15:23:56 # The website can be accessed from the following urls:    #
   2016-08-18T15:23:56 #                                                         #
   2016-08-18T15:23:56 # On local machine:                                       #
   2016-08-18T15:23:56 #  http://localhost:8080                                  #
   2016-08-18T15:23:56 #                                                         #
   2016-08-18T15:23:56 # On local network:                                       #
   2016-08-18T15:23:56 #  http://10.10.1.50:8080                                 #
   2016-08-18T15:23:56 #                                                         #
   2016-08-18T15:23:56 # From external network (check port forwarding):          #
   2016-08-18T15:23:56 #  http://173.20.84.23:8080                               #
   2016-08-18T15:23:56 #                                                         #
   2016-08-18T15:23:56 #                                                         #
   2016-08-18T15:23:56 # Web Interface access pin code:                          #
   2016-08-18T15:23:56 #  RrS9kV                                                 #
   2016-08-18T15:23:56 #                                                         #
   2016-08-18T15:23:56 ###########################################################

Visit each link until you find one that works. From here, you will be able to configure
your server using the setup wizard.

Running the gateway
===================

Just execute the same command from above. On startup the gateway will:

* Read to the yombo.ini file
* Connect to Yombo Servers for any configuration updates
* Download any required modules
* Begin processing automation tasks

.. note::

  If are you setting up a new gateway, you are done.

.. warning::

  The information below if for advanced settings and can break things. It's recommended that
  you stop here. The remaining sections explain making configuration changes that can normally
  be performed though the configuration website or mobile apps.

yombo.ini
=========

The majority of the time, the default settings will work fine. However, the
gateway exposes many settings that allows various options to be tweaked. Some
caution is needed: *you can break things!*

.. rst-class:: floater

.. warning::

  Deleting the yombo.ini alone will not delete all settings. Be sure to delete the
  database file: yombo-gateawy/usr/etc/yombo.db


The yombo.ini file contains various configuration settings. For details about
it's contents see the Yombo Wiki for
`yombo.ini <https://projects.yombo.net/projects/gateway/wiki/Yomboini>`_

.. rst-class:: floater

.. warning::

  If you update the yombo.ini file while the **gateway is running**, any changes
  will be **lost**.


Only the basic configurations are stored in the yombo.ini file, the remaining
configurations (devices, commands, etc) are stored in a local database file
managed by the gateway.

The gateway was designed to be easily updated using various tools, including
the mobile app or through the Yombo API. It's recommended to use those tools
instead of directly modifying the yombo.ini file.


Advanced configurations
=======================================

.. rst-class:: floater

.. note::

  Using the features listed below should only be used if you are developing
  a new module that hasn't been published yet.

Creating Local Modules
----------------------

To get started building your first module, see:
`Building your first module <https://projects.yombo.net/projects/modules/wiki/Building_your_first_module>`_.

For those wanting to create a local module and not make it publicly available,
you can instruct the gateway to load it by creating a ``localmodules.ini``
at gateway root directory. This allows the gateway to run modules inside of
the Yombo Gateway framework without registering the module.

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