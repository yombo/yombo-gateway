=====================
What is Yombo Gateway
=====================

The Yombo Gateway is an open-source framework to provide automation of various
devices (X10, Z-Wave, Insteon, etc) from any manufacturer.  Yombo provides a
way out of vendor lock-in by allowing cross-vendor and cross-protocol bridging.

=============
Documentation
=============

Installation instructions, getting started and in-depth API documentation can
be found here:

http://www.yombo.net/docs/gateway/current/

===========
Quick Start
===========

1. You must have a `Yombo account <http://www.yombo.net>`_ .
2. Prepare your OS. Need to install python and various python modules.
   See http://www.yombo.net/docs/gateway/current/chapters/prepare-operating-system.html
3. See the ``install`` folder. Look for a file matching your operating with "OSVERSION-setup.ext".
   For exmaple, Debian users can use ``debian-setup.sh`` to setup their system.
3. Configure the gateway: ./config.py
4. You can run the Gateway from the local directory (thumb drive, etc)
   or install and have it start at bootup. The install folder contains
   OS-install-service script to setup the Gateway software and requests the
   system start it up bootup. Run with: `sudo ./OSVERSION-install-service.sh`

===============================
Getting Help / Other Resources
===============================

For issue (tickets), feature requests, forums,  and wiki articles, visit
`Yombo Gateway Projects <https://projects.yombo.net/projects/gateway>`_ page.

=========================
Yombo Gateway License 
=========================

By accessing or using any Yombo code, you are agreeing to the licensing terms as
listed in the LICENSE file. If you do not agree to these terms, do not
access or use this softare.

The Yombo Gateway source and/or binaries is governed by the Yombo Reciprocal
Public License Version 1.6. A copy is included in the LICENSE file distributed
with this software.

If you do not wish to release your source code of the software you build using Yombo
Gateway as the base, you may use Yombo Gateway source and/or binaries under the Yombo
Gateway Private License as described here:

http://www.yombo.net/policies/licensing/yombo-private-license
