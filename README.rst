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

https://yombo.net/docs/gateway/html/current/index.html

===========
Quick Start
===========

1. Create an account at `Yombo account <https://yombo.net>`_ .
2. Create a gateway at `app.yombo.net <https://app.yombo.net`_.
3A. If you haven't downloaded the gateway software: See
   https://yombo.net/docs/gateway/html/current/chapters/install-gateway.html
3B. If you have the gateway software installed, see the ``install`` folder.
   Look for a file matching your operating system. Run the "-setup" version.
   For example: "debian-setup.sh".
4. Configure the gateway: ./config.py
5. You can run the Gateway from the local directory (thumb drive, etc)
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

https://yombo.net/policies/licensing/yombo-private-license
