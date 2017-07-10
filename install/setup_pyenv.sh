#!/usr/bin/env bash

sudo apt-get update
sudo apt-get install --force-yes -y make libudev-dev g++ libyaml-dev
sudo apt-get install python python-pip python-setuptools python-dev gnupg2 rng-tools build-essential git libncurses5 libncurses5-dev libncursesw5 \
libncursesw5-dev xz-utils libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev curl wget llvm tk-dev -y

export PATH="/home/$USER/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
env | grep PATH

CFLAGS='-O2'

curl -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash

echo "export PATH=\"/home/$USER/.pyenv/bin:\$PATH\"" >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

pyenv install 3.6.1

pyenv local 3.6.1
pip install -r requirements.txt

