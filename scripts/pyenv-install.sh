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

LOGFILE=/home/$SUDO_USER/yombo_setup.log
function logsetup {
    exec > >(tee -a $LOGFILE)
    exec 2>&1
}

function log {
    echo "[$(date --rfc-3339=seconds)]: $*"
}
logsetup

CFLAGS='-O2'

log Installing pyenv
curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
#echo 'pyenv virtualenvwrapper' >> ~/.bashrc

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

log Installing python 3.6.4
cd ..

pyenv install 3.6.4
pyenv local 3.6.4
pip3 install -r requirements.txt
