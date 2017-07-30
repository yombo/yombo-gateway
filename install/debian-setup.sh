#!/usr/bin/env bash
if [ "$(id -u)" -ne 0 ]; then
    echo "This must be run with sudo from the current user that will be running the gateway."
    echo ""
    echo "For security, it is recommended to run this software as a dedicated user."
    echo "Create a new account 'yombo' and run this command: 'sudo bash ./setup-debian.sh'"
    echo ""
    echo "yombo@mycomputer> sudo bash ./setup-debian.sh"
    echo ""
    exit
fi

echo "This will download any required components as well as download the Yombo Gateway"
echo "using git."
echo ""
echo "This will take a while due to compiling the needed requirements."
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
echo "the default Yombo Gateway git respository will be installed."
echo ""
read -e -p "Git Repo: " -i "https://bitbucket.org/yombo/yombo-gateway.git" repolocation

echo ""
echo "Using git repo location: $repolocation";

sudo apt-get update
sudo apt-get upgrade -y

sudo apt-get install make libudev-dev g++ libssl-dev zlib1g-dev libbz2-dev libreadline6-dev \
libreadline6-dev libreadline-dev libsqlite3-dev libexpat1-dev liblzma-dev \
python python-dev python3-dev gnupg2 rng-tools build-essential git \
python3-setuptools python3-pip python-pip libyaml-dev libncurses5 \
libncurses5-dev libncursesw5 libncursesw5-dev xz-utils curl wget llvm tk-dev libbluetooth-dev -y

sudo pip3 install --upgrade pip
sudo usermod -a -G dialout $SUDO_USER

cwd=$(pwd)

cd /opt
sudo git clone https://bitbucket.org/yombo/yombo-gateway.git
sudo chown -R $SUDO_USER:$SUDO_USER /opt/yombo-gateway
sudo chown -R $SUDO_USER:$SUDO_USER /opt/yombo-gateway/.[^.]*

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

echo ""
echo "System files installed and setup. Now is time to install the user portion."
echo ""
echo "Execute 'install-pyenv'? This will install pyenv and Python 3.6.2 inside that."
echo ""
echo "This will take a while due to compiling the needed requirements."
while true; do
    read -p "Do you wish to install these programs? (y/n)" yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

cd $cwd
sudo runuser -l pi -c "bash install-pyenv.sh"
