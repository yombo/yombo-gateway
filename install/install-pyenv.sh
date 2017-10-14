#!/usr/bin/env bash
if [ "$(id -u)" -e 0 ]; then
    echo "This must NOT be run with sudo, instead run as the user running the Yombo Gateway"
    echo "softgware. For security, it is recommended to run this software as a dedicated user."
    echo "Create a new account 'yombo' and run this command: 'sudo bash ./setup-debian.sh'"
    echo ""
    echo "> sudo bash ./setup-debian.sh"
    echo ""
    exit
fi

echo "This will download and install pyenv as well as python 3.6.2."
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

curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

pyenv install 3.6.2
cd /opt/yombo-gateway
pyenv local 3.6.2

pip3 isntall --upgrade -r requirements.txt
