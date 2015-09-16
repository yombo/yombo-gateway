.. index:: install_gateway_zip

.. _install_gateway_zip:

==========================================
Install using ZIP file
==========================================

If you have not already, you need to
:doc:`prepare your operating system <../chapters/prepare-operating-system>` first.

.. warning::

  Only download zip files as a last resort. Yombo Gateway is under constant development,
  which includes bug fixes and new features. Using ZIP files makes upgrading difficult
  and time consuming. Although this method is quick, the :doc:`basic GIT method is just as
  quick <install-gateway-git>` and allows for easily upgrading your gateway.

Download zip file
=================

Decide where you want to install the gateway. Our example uses "/opt",
which is a typical location for linux. Windows users can use use something
like "c:\myprograms".  After a location has been determined, open a shell
or command prompt to that location.

At this time, we currently recommend the development branch. Things are being added quickly to this branch and
slowly merged into mainline (or master).

* Master (more stable) - `zip <https://bitbucket.org/yombo/yombo-gateway/get/master.zip>`_ , `gz <https://bitbucket.org/yombo/yombo-gateway/get/master.tar.gz>`_ , `bz2 <https://bitbucket.org/yombo/yombo-gateway/get/master.tar.bz2>`_

* Develop (more active, mostly stable) - `zip <https://bitbucket.org/yombo/yombo-gateway/get/develop.zip>`_ , `gz <https://bitbucket.org/yombo/yombo-gateway/get/develop.tar.gz>`_ , `bz2 <https://bitbucket.org/yombo/yombo-gateway/get/develop.tar.bz2>`_

**The following code may have to be modified depending on install location!**

.. code-block:: bash

  # Install the code somewhere, typically in /opt or a subdirectory of your home dir.
  cd /opt

  # Cloning is git's way of saying download.
  unzip master.zip
  mv master yombo-gateway

  # Linux users should change the owner of the directory
  sudo chown -R username:username yombo-gateway

Next Steps
----------

The gateway has been installed, Continue to
:doc:`Configuration <../chapters/configuring-the-gateway>`.
