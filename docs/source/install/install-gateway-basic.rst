.. index:: install_gateway_basic

.. _install_gateway_basic:

=======================================
Basic install of Yombo Gateway software
=======================================

If you have not already, you need to install
:doc:`python and git <../chapters/prepare-operating-system>` first.

The software can be downloaded by two methods:

1. Download with git - Prefered, uses git to clone (copy) the open source software for you.
2. Download a snapshot - Only used if git is not available on the computer.

However, if this tool is not available or can't be installed, a snapshot can
be downloaded.

Download with git
=================

Decide where you want to install the gateway. Our example uses "/opt",
which is a typical location for linux. Windows users can use use something
like "c:\myprograms".  After a location has been determined, open a shell
or command prompt to that location.

**The following code may have to be modified depending on install location!**

.. code-block:: bash

  # Install the code somewhere, typically in /opt or a subdirectory of your home dir.
  cd /opt

  # Cloning is git's way of saying download.
  sudo git clone https://bitbucket.org/yombo/yombo-gateway.git

  # Linux users should change the owner of the directory
  sudo chown -R username:username yombo-gateway

Next Steps
----------

The gateway has been installed, Continue to
:doc:`Configuration and Running <../chapters/running-the-gateway>`.

Download a snapshot
===================

Only download zip files as a last resort. It's recommended to use git so
the software can be kept up to date. Yombo Gateway is under constant
development. This includes new features and bug fixes.

At this time, we currently recommend the development branch. Things are
being added quickly to this branch and slowly merged into mainline (or master).

* Master - `zip <https://bitbucket.org/yombo/yombo-gateway/get/master.zip>`_ , `gz <https://bitbucket.org/yombo/yombo-gateway/get/master.tar.gz>`_ , `bz2 <https://bitbucket.org/yombo/yombo-gateway/get/master.tar.bz2>`_

  * Stable releases

* Develop - `zip <https://bitbucket.org/yombo/yombo-gateway/get/develop.zip>`_ , `gz <https://bitbucket.org/yombo/yombo-gateway/get/develop.tar.gz>`_ , `bz2 <https://bitbucket.org/yombo/yombo-gateway/get/develop.tar.bz2>`_

  * Active, mostly stable.

Next Steps
----------

The gateway has been installed, Continue to
:doc:`Configuration and Running <../chapters/running-the-gateway>`.
