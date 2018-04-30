#!/usr/bin/env bash
@Echo off
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

cd /home/$USER/.pyenv && git pull && cd -
cd /opt/yombo-gateway
pyenv install 3.6.5
pyenv local --unset
pyenv local 3.6.5
pip3 list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U
pip3 install -r requirements.txt
