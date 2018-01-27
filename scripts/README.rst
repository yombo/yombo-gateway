=====================
Scripts Directory
=====================

Various files to get Yombo Gateway installed on various platforms. To get started
and information on installation, visit: https://yombo.net/docs/gateway/quick_start


Debian
======

For installing on Debian based systems, including Mint and Ubuntu.


install-debian.sh
----------------------

Installs the required software before Yombo Gateway can run.

update-debian.sh
----------------------

Updates all the software related to Yombo gateway.

install-service-systemd.sh
--------------------------

Setup Yombo Gateway to run as a service on using systemd (used on newer Debian based systems).
After installation, you can use the service command to manage the Gateway.

install-service-initd.sh
--------------------------

Setup Yombo Gateway to run as a service on using initd (used on older Debian based systems).
After installation, you can use the service command to manage the Gateway.


Misc
====

Misc files in this directory.

yombo-init
----------

initd script to be installed on linux distributions. Used by the install-service-initd script.

yombo-systemd
-------------

systemd script to be installed on linux distributions. Used by the install-service-systemd script.
