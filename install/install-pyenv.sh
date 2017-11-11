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

echo "This will download and install pyenv as well as python 3.6.3."
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

sudo apt-get update
sudo apt-get install --force-yes -y make libudev-dev g++ libyaml-dev
sudo apt-get install python3-pip python3-setuptools python3-dev gnupg2 rng-tools build-essential git libncurses5 libncurses5-dev libncursesw5 \
libncursesw5-dev xz-utils libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl wget llvm tk-dev -y

export PATH="/home/$USER/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
env | grep PATH

CFLAGS='-O2'

curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

pyenv install 3.6.3
pyenv local 3.6.3
mv .python-version ../
pip install -r ../requirements.txt
