#!/usr/bin/env bash
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must run with sudo to gain root access. This is needed to install"
    echo "the required software as well as adjust some system settings to enable"
    echo "USB/Serial port access."
    echo "If you created a dedicate account for this software, first log into that account."
    echo "Then run this script as:"
    echo ""
    echo "mycomputer> sudo bash ./install-debian.sh"
    echo ""
    exit
fi

LOGFILE=/home/$SUDO_USER/yombo_setup.log
function logsetup {
#    TMP=$(tail -n $RETAIN_NUM_LINES $LOGFILE 2>/dev/null) && echo "${TMP}" > $LOGFILE
    exec > >(tee -a $LOGFILE)
    exec 2>&1
}

function log {
    echo "[$(date --rfc-3339=seconds)]: $*"
}
logsetup

echo "The log file for these changes will be available at: $LOGFILE";
echo ""
echo "This script will use pyenv so that the latest compatible python version will be used"
echo "the Yombo Gateway. This allows python version isolation from the system installed"
echo "python version."
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

echo ""
echo "If you forked your own copy of the Yombo Gateway repository, enter it below. Otherwise,"
echo "the default Yombo Gateway git repository will be installed."
echo ""
read -e -p "Git Repo: " -i "https://github.com/yombo/yombo-gateway.git" repolocation

echo ""
log Using git repo location: $repolocation

log Adding mostquitto (MQTT broker) to local repos
apt-add-repository ppa:mosquitto-dev/mosquitto-ppa
apt-get update
apt-get upgrade -y

log Installing required dependencies.

apt-get install make libudev-dev g++ libssl-dev zlib1g-dev libbz2-dev libreadline6-dev \
libreadline6-dev libreadline-dev libsqlite3-dev libexpat1-dev liblzma-dev \
python python-dev python3-dev gnupg2 rng-tools build-essential cmake git \
python3-setuptools python3-pip python-pip libyaml-dev libncurses5 \
libncurses5-dev libncursesw5 libncursesw5-dev xz-utils curl wget llvm tk-dev libbluetooth-dev \
mosquitto libmosquitto-dev libcurl4-openssl-dev libc-ares-dev uuid-dev daemon quilt dirmngr \
libavahi-compat-libdnssd-dev nodejs libbluetooth3 libboost-thread-dev libglib2.0 -y

log Installing homebridge incase it's going to be used later.

sudo npm install -g --unsafe-perm mdns
sudo npm install -g --unsafe-perm homebridge

log Upgrading pip3
sudo pip3 install --upgrade pip
log Adding correct user to dialout group to gain access to serial/USB ports.
sudo usermod -a -G dialout $SUDO_USER

# we install mosquitto to get the services installed and configs installed.
# but later we will manually install a version for updated features and
# to use an updated libwebsockets
log Installing and upgrading mosquitto, updating it's configuration.
sudo apt-mark hold mosquitto

cd /etc/mosquitto
sudo mkdir yombo
sudo chown pi yombo
echo "include_dir /etc/mosquitto/yombo" >> /etc/mosquitto/mosquitto.conf
log Updating mosquitto to use newer libwebsockets

cd /usr/local/src
sudo mkdir yombo
sudo chown $SUDO_USER yombo
cd yombo
git clone https://github.com/warmcat/libwebsockets.git
cd libwebsockets
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig

cd /usr/local/src/yombo
git clone https://github.com/eclipse/mosquitto.git
cd mosquitto
make binary WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/
sudo make install WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/

cwd=$(pwd)

log Downloading Yombo Gateway
cd /opt
sudo git clone $repolocation
sudo chown -R pi:pi /opt/yombo-gateway
sudo chown -R pi:pi /opt/yombo-gateway/.[^.]*
sudo chown -R pi:pi /opt/yombo-gateway/..?*

log Setting up systemctl service
cd /etc/systemd/system/
sudo wget -O yombo.service https://get.yombo.net/debian_files/yombo.service-debian
sudo chmod 755 yombo.service

log Setting up additional sudoers configs
cd /etc/sudoers.d
sudo wget -O mosquitto https://get.yombo.net/yombian_files/sudoers-mosquitto
sudo wget -O yombo https://get.yombo.net/yombian_files/sudoers-yombo
sudo chmod 644 mosquitto
sudo chmod 644 yombo

log Setting up various runtime directories for Yombo Gateway
if [ ! -d /var/run/yombo ]; then
  mkdir /var/run/yombo
fi
chmod 775 /var/run/yombo
chown $SUDO_USER:$SUDO_USER /var/run/yombo

if [ ! -d /var/log/yombo ]; then
  mkdir /var/log/yombo
fi
chmod 775 /var/log/yombo
chown $SUDO_USER:$SUDO_USER /var/log/yombo

log Calling the user portion installation script: pyenv-install.sh

sudo runuser -l $SUDO_USER -c "bash pyenv-install.sh"
