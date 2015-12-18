.. index:: install_debian

.. _Install_Debian:

=================================================
Installing on Debian (Mint, Ubuntu, Xubuntu, etc)
=================================================

This simple install script will install any prerequisites and then download
the Yombo Gateway software into a new subdirectory.

It's best to run this from either "/opt/" or "/usr/local/bin/" directory as
the user you wish to run the software as.

This example downloads and installs as user "yombo" into "/opt/yombo-gateway":

.. code-block:: bash

  cd /opt
  su yobmo
  curl -sS https://get.yombo.net/debian | sudo bash

.. rubric:: Next steps

Your system is ready to be configured.
Next: :doc:`Configuration <../chapters/configuring-the-gateway>`.

