.. index:: install_windows

.. _Install_Windows:

=====================
Installing on Windows
=====================

Using Virtualbox
================

Installing the Yombo Gateway on a Windows machine is an involved process.
There are many many open source tools that Yombo glues together to make your
life easier. It manages and uses these various tools to create a complete
automation system.  For example, it uses GNUpg (GPG / PGP) to encrypt and
secure data sent between places. It also uses it to validate who sent the
data.  You'll need to install GNUph and the python gnupg package. The list
continues.

You are probably better off downloading
`virtualbox <https://www.virtualbox.org/wiki/Downloads>`_ and installing a
free Linux operating system. Virtualbox allows you to run nearly any
perating system as a virtual machine inside of Windows. This allows you to
install your favorite flavor of Linux. If you don't have a favorite flavor,
Yombo suggests using `Linux Mint <http://www.linuxmint.com/>`_ . Who doesn't
like mint?

Linux Mint is a repackaged Ubuntu distribution that has better eye candy and
many say a better and easier to use graphics interface. However, you are
welcome to use any Linux distribution you wish. Within Linux Mint, you have
many choices of desktop environments. If you don't have a preference, we
suggest using, Cinnamon...only because it's at the top of the page and
easiest to find. It'll work just fine and is easy to use.

Quick steps, this assumes you'll use 1gb of memeory for you're virtual machine.
Linux with Yombo will run just fine 1gb:

# Download and install `virtualbox <https://www.virtualbox.org/wiki/Downloads>`_
# Download either 32 Linux distribution you prefer.
# Within virtual box, create a new new virtual machine.
# Mount the ISO to the CD/DVD drive.
# Install you're OS.

Now that you have your virtual machine runnging and happy, visit the
:doc:`preparing operating system <../chapters/prepare-operating-system>` page
to get the new operating system ready for yombo.

Sticking to Windows
===================

Documentation is pending for getting it working on Windows.

Installing GIT
==============

The msysGit project is easy to install - just download the installer
and run it:

`<http://code.google.com/p/msysgit>`_

This installes command-line version, which includes an SSH client to
communicate with remote repositories, and the standard GUI.

