=====================
Install Directory
=====================

Various files to get Yombo Gateway installed

install-debian-requirements.sh
------------------------------

Installs the requirements needed for Yombo Gateway. It also configures the
the log file path and pid file path.

install-debian-service.sh
-------------------------

For Debian based systems (Debian, Ubuntu, Mint, etc), this will setup Yombo
Gateway to run at startup. After installation, you can use the service
command to manage the Gateway.

yombo-init
----------

Init script to be installed on linux distributions.  Used by the install.sh
installation script.
