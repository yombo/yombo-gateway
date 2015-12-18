.. index:: install_raspberrypi

.. _Install_Raspberry_PI:

==============================
Raspberry PI - From bare metal
==============================

This guide will walk you through bare metal Raspberry PI/PI2 to a running Yombo Gateway.
However, please note that on the original R-PI, it will take a minute or so for the Cython
modules to full compile the first time the gateway software runs.

Installing Debian - Jessie
--------------------------

The following outlines the steps required to get up and running with Debian Jessie.
You can download the image from here (latest version found as of Nov 9, 2015):

Download the "Raspbian Jessie" image from here: `<https://www.raspberrypi.org/downloads/raspbian/>`_

You will need to follow the steps and directions found here for writing the image:
`<https://www.raspberrypi.org/documentation/installation/installing-images/README.md>`_

Once the image has been written to the SD coard, plug it into the RPi and get
everything else connected.  Power it on.

After a few moments, you will be presented with a setup screen. Review this link for details:
`<https://www.raspberrypi.org/phpBB3/viewtopic.php?t=9206&p=107298>`_

Setup a new user
----------------

It is suggested to re-size the install partition to use the entire SD card.  Reboot.

Optional - Changing the username from "pi" is one the best ways to increase security
and also more convenient for you as well.  However, you cannot simply change the username.
You must add a new user, test it, and then delete the previous user.  First, add a user:

.. code-block:: bash

  sudo adduser _username_

Username is the new username that you wish to create.  You will be prompted twice for
the password.  Everything else, is optional:

.. code-block:: bash

  $ sudo adduser joe
  Adding user `joe' ...
  Adding new group `joe' (1003) ...
  Adding new user `joe' (1002) with group `joe' ...
  Creating home directory `/home/joe' ...
  Copying files from `/etc/skel' ...
  Enter new UNIX password:
  Retype new UNIX password:
  passwd: password updated successfully
  Changing the user information for joe
  Enter the new value, or press ENTER for the default
          Full Name []:
          Room Number []:
          Work Phone []:
          Home Phone []:
          Other []:
  Is the information correct? [Y/n]

To give this user root access, you need to add this user to the list of people that can do sudo:

.. code-block:: bash

  sudo visudo

At the bottom, copy the line "pi ALL=(ALL) NOPASSWD: ALL" and add a new one under it,
changing pi to your username.  It should look something like this:

.. code-block:: guess

  #includedir /etc/sudoers.d
  pi ALL=(ALL) NOPASSWD: ALL
  joe ALL=(ALL) NOPASSWD: ALL

Lets test it.  Open a new ssh session to the raspberry pi.  Try to login with the new
user and try a root command.  Such as "sudo visudo" and see if you can open the file.
Now that works, you can then safely remove the user pi. (Yes, we know that you skip
the 'sudo visudo' since you won't be able to do this without sudo.  This step was put
there incase you wanted to validate the access, but keep the username pi.)

Now, delete the pi user:

.. code-block:: bash

  $ sudo deluser -remove-home pi
  Looking for files to backup/remove ...
  Removing files ...
  Removing user `pi' ...
  Warning: group `pi' has no more members.
  Done.

USB Permissions
---------------

Debian marks all ttyUSB* ports as root:dialout. You need to add your new user
to the dialout group to access any USB <-> serial devices:

.. code-block:: bash

  $ sudo usermod -a -G dialout joe

Update Raspberry Firmware and OS
--------------------------------

Lets make sure everything is updated and running the current versions.  This will
take a while. If/when prompted to select a version of a configuration file, select
the default of N.

.. code-block:: bash

  cd
  sudo apt-get update
  sudo apt-get upgrade
  sudo apt-get install git rpi-update -y
  sudo rpi-update
  sudo reboot

Install Yombo-Gateway
=====================

The remaining steps are the same as for any other debian release.

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
