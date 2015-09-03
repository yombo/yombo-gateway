.. index:: install_debian

.. _Install_Debian:

=================================================
Installing on Debian (Mint, Ubuntu, Xubuntu, etc)
=================================================

Installing the Yombo Gateway is straight forward on debian systems. This
includes Ubuntu, Xubuntu, and Mint. The following script can copied and used.

.. warning::

  If using **Ubuntu 12.04/Mint 13 or older**, you will need to edit this script
  uncomment the two commented commands. This installs an updated version of
  twisted.

Steps
-----

The following two steps will prepare your debian system.  Start in the directory
where the Yombo Gateway was downloaded and extracted.



.. code-block:: bash

  # If using **Ubuntu 12.04/Mint 13 or older** uncomment the following two
  # commands. This points to and installs an updated version of twisted. 
  #sudo add-apt-repository ppa:twisted-dev/ppa
  #sudo apt-get update

  # Install most of the needed items.
  sudo apt-get install python python-twisted python-twisted-words python-twisted-web python-twisted-mail gnupg2 python-pip rng-tools python-dev python-wokkel python-dev build-essential git

  # gnupg is used for signing and encryption. pyephem is used for sunset/sunrise times.
  sudo pip install python-gnupg pyephem cython

Next steps
========== 

The python environment is now ready to run the gateway software. Proceed to
:doc:`installing the gateway <../chapters/install-gateway>`.

