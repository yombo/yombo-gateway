.. index:: install_debian

.. _Install_Debian:

=================================================
Installing on Debian (Mint, Ubuntu, Xubuntu, etc)
=================================================

Installing the Yombo Gateway is straight forward on debian systems. This
includes Ubuntu, Xubuntu, and Mint. The following script can copied and used.

.. warning::

  Review the script and adjust for your release. Some day, someone will get
  around to writing an install script!

.. code-block:: bash

  # If using **Ubuntu 12.04/Mint 13 or older** uncomment the following two
  # commands. This points to and installs an updated version of twisted. 
  #sudo add-apt-repository ppa:twisted-dev/ppa
  #sudo apt-get update

  # Install most of the needed items.
  sudo apt-get install python python-twisted python-twisted-words python-twisted-web python-twisted-mail gnupg2 python-pip rng-tools python-dev python-wokkel python-dev build-essential

  # gnupg is used for signing and encryption. pyephem is used for sunset/sunrise times.
  sudo pip install python-gnupg pyephem

  # We need the latest version of Cython, not always available on various
  # distributions. Find the latest link http://cython.org/#documentation
  # Compile from source:

  # Find a place to put it.
  cd /usr/local/src

  # Most distros lock this down. So, lets brute force it.
  sudo mkdir /usr/local/src/Cython-0.19.1

  # Get the source.
  sudo wget http://cython.org/release/Cython-0.19.1.tar.gz

  # Extract the source
  sudo tar zxf Cython-0.19.1.tar.gz

  # Build it and install it.
  cd Cython-0.17.4/
  sudo python setup.py install

  # Last but not least, install git to download repositories
  sudo apt-get install git

Next steps
========== 

The python environment is now ready to run the gateway software. Proceed to
:doc:`installing the gateway <../chapters/install-gateway>`.

