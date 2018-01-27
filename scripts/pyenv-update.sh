#!/usr/bin/env bash
if [ "$(id -u)" -eq 0 ]; then
    echo ""
    echo "Besure your debian system is up to date: with apt-get update && apt-get upgrade first."
    echo ""
    echo "This must NOT be run as root, instead run as the user running the Yombo Gateway"
    echo "software. Then:"
    echo ""
    echo "> bash ./pyenv-udpate.sh"
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

#export PATH="/home/$USER/.pyenv/bin:$PATH"
#eval "$(pyenv init -)"
#eval "$(pyenv virtualenv-init -)"
#env | grep PATH

CFLAGS='-O2'

cd /home/$USER/.pyenv && git pull && cd -

cd ..
pyenv install 3.6.4
pyenv local 3.6.4
pip3 list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U
pip3 install -r requirements.txt

