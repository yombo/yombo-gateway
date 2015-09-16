.. index:: install_gateway_git

.. _install_gateway_git:

====================================
Install using GIT
====================================

Besure you have :doc:`prepared your operating sytem <../chapters/prepare-operating-system>`
first.

GIT should already be installed if you followed the above link to prepare
your operating system.

Configure GIT
=============

Tell GIT who you are you.

.. code-block:: bash

  $ git config --global user.name "John Doe"
  $ git config --global user.email johndoe@example.com

Download The Gateway
====================

.. code-block:: bash

  $ git clone https://bitbucket.org/yombo/yombo-gateway.git
  #
  # OR
  #
  # SSH if you have submitted your SSH key (preferred)
  $ git clone git@bitbucket.org/yombo/yombo-gateway.git

Next Steps
----------

Continue to
:doc:`Configuration <../chapters/running-the-gateway>`.
