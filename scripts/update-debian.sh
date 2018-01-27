#!/usr/bin/env bash
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must run with sudo to gain root access."
    echo "If you created a dedicate account for this software, first log into that account."
    echo "Then run this script as:"
    echo ""
    echo "mycomputer> sudo bash ./update-debian.sh"
    echo ""
    exit
fi

LOGFILE=/home/$SUDO_USER/yombo_setup.log
function logsetup {
    exec > >(tee -a $LOGFILE)
    exec 2>&1
}

function log {
    echo "[$(date --rfc-3339=seconds)]: $*"
}
logsetup

echo "The log file for these changes will be available at: $LOGFILE";
echo ""
echo "This script will update pyenv and use the latest python compatible with Yombo gateway."
echo ""
echo "This script will also update the system software with 'apt-get upgrade -y'"
echo ""
while true; do
    read -p "Do you wish to install these programs? (y/n)" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

apt-get update
apt-get upgrade -y

log Installing homebridge incase it's going to be used later.

sudo npm install -g --unsafe-perm mdns
sudo npm install -g --unsafe-perm homebridge

log Upgrading pip3
sudo pip3 install --upgrade pip

sudo runuser -l $SUDO_USER -c "git pull"

cd /usr/local/src/yombo/libwebsockets
git pull
cd build
cmake ..
make clean
make
sudo make install
sudo ldconfig

cd /usr/local/src/yombo/mosquitto
git pull
make clean
make binary WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/
sudo make install WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/

log Calling the user portion installation script: pyenv-update.sh
sudo runuser -l $SUDO_USER -c "bash pyenv-update.sh"
