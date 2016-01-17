======================
Yombo Gateway Overview
======================

The Yombo Gateway Framework provides a base foundation that allows users to
quickly and easily automate various devices (Z-Wave, X10, Insteon, etc).
This framework can also act a bridge between vendor protocols. For example,
an X10 controler can be mapped to control Z-Wave or Insteon products.

The gateway can also be easily extended using modules. The modules can:
* Extend the features of the framework throug the use of hooks.
* Provide additional API features to other modules.
* Provide advanced automation rules and tasks.

=============
Documentation
=============

For new users, check out the quick start guide at https://yombo.net

For those wishing to dive deeper into the code, the API, or those
wishing to develop modules, vist the documentation generated from
the source here: https://docs.yombo.net/

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

For the full license agreement, view the LICENSE file.

LICENSED SOFTWARE IS PROVIDED UNDER THIS LICENSE ON AN "AS IS" BASIS, WITHOUT
WARRANTY OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING, WITHOUT LIMITATION,
WARRANTIES THAT THE LICENSED SOFTWARE IS FREE OF DEFECTS, MERCHANTABLE, FIT
FOR A PARTICULAR PURPOSE OR NON-INFRINGING. FURTHER THERE IS NO WARRANTY MADE
AND ALL IMPLIED WARRANTIES ARE DISCLAIMED THAT THE LICENSED SOFTWARE MEETS OR
COMPLIES WITH ANY DESCRIPTION OF PERFORMANCE OR OPERATION, SAID COMPATIBILITY
AND SUITABILITY BEING YOUR RESPONSIBILITY. LICENSOR DISCLAIMS ANY WARRANTY,
IMPLIED OR EXPRESSED, THAT ANY CONTRIBUTOR'S EXTENSIONS MEET ANY STANDARD OF
COMPATIBILITY OR DESCRIPTION OF PERFORMANCE. THE ENTIRE RISK AS TO THE QUALITY
AND PERFORMANCE OF THE LICENSED SOFTWARE IS WITH YOU. SHOULD LICENSED SOFTWARE
PROVE DEFECTIVE IN ANY RESPECT, YOU (AND NOT THE LICENSOR OR ANY OTHER
CONTRIBUTOR) ASSUME THE COST OF ANY NECESSARY SERVICING, REPAIR OR CORRECTION.
UNDER THE TERMS OF THIS LICENSOR WILL NOT SUPPORT THIS SOFTWARE AND IS UNDER NO
OBLIGATION TO ISSUE UPDATES TO THIS SOFTWARE. LICENSOR HAS NO KNOWLEDGE OF
ERRANT CODE OR VIRUS IN THIS SOFTWARE, BUT DOES NOT WARRANT THAT THE SOFTWARE
IS FREE FROM SUCH ERRORS OR VIRUSES. THIS DISCLAIMER OF WARRANTY CONSTITUTES AN
ESSENTIAL PART OF THIS LICENSE. NO USE OF LICENSED SOFTWARE IS AUTHORIZED
HEREUNDER EXCEPT UNDER THIS DISCLAIMER.

UNDER NO CIRCUMSTANCES AND UNDER NO LEGAL THEORY, WHETHER TORT (INCLUDING
NEGLIGENCE), CONTRACT, OR OTHERWISE, SHALL THE LICENSOR, ANY CONTRIBUTOR, OR
ANY DISTRIBUTOR OF LICENSED SOFTWARE, OR ANY SUPPLIER OF ANY OF SUCH PARTIES,
BE LIABLE TO ANY PERSON FOR ANY INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES OF ANY CHARACTER INCLUDING, WITHOUT LIMITATION, DAMAGES FOR LOSS OF
GOODWILL, WORK STOPPAGE, COMPUTER FAILURE OR MALFUNCTION, OR ANY AND ALL OTHER
COMMERCIAL DAMAGES OR LOSSES, EVEN IF SUCH PARTY SHALL HAVE BEEN INFORMED OF
THE POSSIBILITY OF SUCH DAMAGES. THIS LIMITATION OF LIABILITY SHALL NOT APPLY
TO LIABILITY FOR DEATH OR PERSONAL INJURY RESULTING FROM SUCH PARTY'S
NEGLIGENCE TO THE EXTENT APPLICABLE LAW PROHIBITS SUCH LIMITATION. SOME
JURISDICTIONS DO NOT ALLOW THE EXCLUSION OR LIMITATION OF INCIDENTAL OR
CONSEQUENTIAL DAMAGES, SO THIS EXCLUSION AND LIMITATION MAY NOT APPLY TO YOU.

THE LICENSED SOFTWARE IS NOT FAULT-TOLERANT AND IS NOT DESIGNED, MANUFACTURED,
OR INTENDED FOR USE OR DISTRIBUTION AS ON-LINE CONTROL EQUIPMENT IN HAZARDOUS
ENVIRONMENTS REQUIRING FAIL-SAFE PERFORMANCE, SUCH AS IN THE OPERATION OF
NUCLEAR FACILITIES, AIRCRAFT NAVIGATION OR COMMUNICATIONS SYSTEMS, AIR TRAFFIC
CONTROL, DIRECT LIFE SUPPORT MACHINES, OR WEAPONS SYSTEMS, IN WHICH THE
FAILURE OF THE LICENSED SOFTWARE COULD LEAD DIRECTLY TO DEATH, PERSONAL
INJURY, OR SEVERE PHYSICAL OR ENVIRONMENTAL DAMAGE ("HIGH RISK ACTIVITIES").
LICENSOR AND CONTRIBUTORS SPECIFICALLY DISCLAIM ANY EXPRESS OR IMPLIED
WARRANTY OF FITNESS FOR HIGH RISK ACTIVITIES.
