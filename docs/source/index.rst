.. Documentation master file, created on Tue Jul 10 13:38:03 2012.

Yombo Gateway Documentation
===========================
Welcome to the open source Yombo Gateway documentation.

TL;DR Quick Start Guide
=======================
Get your gateway up and running in no time.  Just three steps:

1. Install python and others: (:doc:`Debian/Mint/Ubuntu <prepare-operating-system/debian>` or :doc:`Raspberry PI/PI2 <prepare-operating-system/raspberry-pi>`)
2. :doc:`Download the gateway <install/install-gateway-basic>`
3. :doc:`Configure and run your gateway <chapters/configuring-the-gateway>`

Other Resouces
==============
* `Yombo.net <http://yombo.net/>`_ - Main website for Yombo
* `Projects.Yombo.net <http://projects.yombo.net/>`_ - Forums, submit tickets,
  feature requests, wiki.
* `bitbucket.org/yombo/ <https://bitbucket.org/yombo/>`_ - Where all the Yombo open source
  code lives.

Table of Contents
=================

.. toctree::
   :maxdepth: 2
   :numbered:
   :includehidden:

   chapters/prepare-operating-system.rst
   chapters/install-gateway.rst
   chapters/configuring-the-gateway.rst
   chapters/updating.rst
   chapters/yombo-framework.rst
   chapters/developing-yombo-modules.rst

Last updated: |today|

Contributing to Documentation
=============================

Yombo uses self documenting code. This document is generated directly from the
source code itself, as well as a few index files (such as this page).

Making changes is easy: simply find the section of the code and update the
code comment. This website is periodically updated from the source code.

If you wish to make changes to the index pages, the source code to that is
located in : docs/source/

Index and search
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

License Information
===================

:Homepage: http://yombo.net/
:Copyright: 2013-2015 Yombo
:License: For the open source license, see the LICENSE file or http://yombo.net/policies/licensing
