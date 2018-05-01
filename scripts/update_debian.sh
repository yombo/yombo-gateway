#!/usr/bin/env bash
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must run with sudo to gain root access. This is needed to install"
    echo "the latest updates."
    echo ""
    echo "mycomputer> sudo ./update_debian.sh"
    echo ""
    exit
fi

echo "This script will update the pyenv to the latest compatible Python version as well as"
echo "any dependencies."
echo ""
echo "This will take a while due to compiling the needed requirements."
while true; do
    read -p "Do you wish to update these programs? (y/n)" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

apt-get update
apt-get upgrade -y
apt-get install git wget -y

sudo pip3 install --upgrade pip

cd /usr/local/src/yombo/libwebsockets
git remote update
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")
BASE=$(git merge-base @ "$UPSTREAM")

if [ $LOCAL = $REMOTE ]; then
    LIBWEBSOCKETSUPDATED=no
    echo "libwebsockets is current, skipping"
elif [ $LOCAL = $BASE ]; then
    LIBWEBSOCKETSUPDATED=yes
    git pull
    cd build
    make clean
    cmake ..
    sudo make install
    sudo ldconfig
fi

cd /usr/local/src/yombo
git clone https://github.com/eclipse/mosquitto.git
cd mosquitto
make binary WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/
sudo make install WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/

cd /usr/local/src/yombo/mosquitto
git remote update
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")
BASE=$(git merge-base @ "$UPSTREAM")

if [ $LOCAL = $REMOTE ] and [$LIBWEBSOCKETSUPDATED == "no"]; then
    echo "libwebsockets is current, skipping"
else [ $LOCAL = $BASE ]; then
    git pull
    make clean
    make binary WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/
    sudo make install WITH_WEBSOCKETS=yes WITH_DOCS=no CFLAGS=-I/usr/local/include/
fi

sudo runuser -l $SSH_USER -c "bash /opt/yombo-gateway/scripts/update_debian_user.sh"
