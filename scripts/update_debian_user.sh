#!/usr/bin/env bash
if [ "$(id -u)" -e 0 ]; then
    echo ""
    echo "This must NOT be run as root, instead run as the user running the Yombo Gateway"
    echo ""
    echo "If you created a dedicate account for this software, first log into that account."
    echo "Then run this script as:"
    echo ""
    echo "mycomputer> bash ./pyenv-install.sh"
    echo ""
    exit
fi

# This can't be used on raspberry pi
CFLAGS='-O2'

cd /home/$USER/.pyenv && git pull && cd -
cd /opt/yombo-gateway
pyenv install 3.6.5
pyenv local --unset
pyenv local 3.6.5
pip3 list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U
pip3 install -r requirements.txt
