#!/bin/bash
######!/usr/bin/env bash
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

echo "This will download any required components as well as downloading the Yombo Gateway"
echo "using git."
echo ""
echo "This will take a while due to compiling needed requirements."
while true; do
    read -p "Do you wish to install this program? (y/n)" yn
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
exit

echo "Creating PID file location."
if [ ! -d /var/run/yombo ]; then
  mkdir /var/run/yombo
fi
chmod 775 /var/run/yombo
chown $SUDO_USER:$SUDO_USER /var/run/yombo

echo "Create log file location."
if [ ! -d /var/log/yombo ]; then
  mkdir /var/log/yombo
fi
chmod 775 /var/log/yombo
chown $SUDO_USER:$SUDO_USER /var/log/yombo

apt-get install python python-pip python-setuptools python-dev gnupg2 rng-tools build-essential git -y
pip install Twisted python-gnupg pyephem cython gnupg service_identity parsedatetime yaml
pip3 install hbmqtt

