#!/bin/bash
echo ""
if [ $UID != 0 ]; then
    echo "This must be run with sudo from the current user that will be using the gateway."
    echo ""
    echo "For example is user 'mitch' is installing the gateway, run this command logged"
    echo "in as mitch: sudo setup-debian.sh"
echo ""
    exit
fi

echo "This will install the required componets to run the Yombo Gateway."
echo
echo "This will take a while due to compiling needed requirements."
echo -n "Continue? [Y/n] ?"
read a
if [ "x$a" == "xn" ] || [ "x$a" == "xN" ]; then
    exit
fi

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

apt-get install python python-twisted python-twisted-words python-twisted-web python-twisted-mail gnupg2 python-pip rng-tools python-dev python-wokkel python-dev build-essential git -y
pip install python-gnupg pyephem cython pika
