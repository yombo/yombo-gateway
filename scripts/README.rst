=====================
Scripts Directory
=====================

The installation scripts have been moved to a separate repository. To
install Yombo gateway, visit the `quick start guide <https://yg2.in/start>`_.

update_debian.sh
----------------------

Used on x86 (32/64 bit) based Debian systems (Ubuntu, Mint, Debian, etc).

Updates all the software related to Yombo gateway. This script updates the Debian system,
the Yombo gateway software, and any required dependencies.

This script must be run under sudo:
sudo ./update-debian.sh

update_debian_user.sh
----------------------

Called by the update_debian.sh script to update user level component. This shouldn't
be called directly.


update_raspberrypi.sh
--------------------------

Used on arm based Debian systems (Raspbian, Stretch, etc).

Updates all the software related to Yombo gateway. This script updates the Debian system,
the Yombo gateway software, and any required dependencies.

This script must be run under sudo:
sudo ./update-raspberrypi.sh

update_raspberrypi.sh
----------------------

Called by the update_raspberrypi.sh script to update user level component. This shouldn't
be called directly.
