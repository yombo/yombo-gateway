.. index:: install_raspberrypi

.. _Install_Raspberry_PI:

==============================
Raspberry PI - From bare metal
==============================

This guide will walk you through bare metal Raspberry PI to a running Yombo Gateway. However,
please note that on the original R-PI, it will take a minute or so for the Cython modules
to full compile the first time the gateway software runs.

Debian - Wheezy
---------------

The following outlines the steps required to get up and running with Debian Wheezy.
You can download the image from here (latest version found as of 2015-05-05):

You will need to follow the steps and directions found here for writing
the image: `<http://www.raspberrypi.org/downloads>`_

Download the ``Raspbian "wheezy"`` image from" http://www.raspberrypi.org/downloads

Write the image to your SD card.  Once that is done, plug it into the RPi and get
everything else connected.  Power it on.

After a few moments, you will be presented with a setup screen. Review this link for details:
`<http://www.raspberrypi.org/phpBB3/viewtopic.php?t=9206&p=107298>`_

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

  $ sudo usermod -a -G dialout user

Lets make sure everything is updated and running the current versions.  This will
take a while. If/when prompted to select a version of a configuration file, select
the default of N.  You might want to save this snippet as a script and running
regularly, such as every other sunday morning at 2am.

.. code-block:: bash

  cd
  sudo apt-get update
  sudo apt-get upgrade
  sudo apt-get install python python-pip python-setuptools python-dev gnupg2 rng-tools build-essential git -y
  sudo pip install Twisted msgpack-python python-gnupg pyephem cython gnupg service_identity
  # git clone git://github.com/Hexxeh/rpi-update.git
  # sudo rpi-update/rpi-update
  sudo reboot

Next steps
==========

Your system is ready, continue to: :doc:`installing the gateway <../chapters/install-gateway>`.
