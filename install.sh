#!/bin/bash
echo
echo
if [ $UID != 0 ]; then
    echo "This must be run with sudo or as root."
    exit
fi

# Set a default home
YOMBOHOME="/home/yombo"
USER = whoami

if [ "x$1" == "x" ]; then
    echo "This will install Yombo Gateway as the current user. If you want this to"
    echo "run as a separate user, first create the new user and run this script as"
    echo "that user."
    echo
    echo "Installing for user: $SUDO_USER"
    echo
    echo "This script will install the start/stop daemon using the current path."
    echo
fi

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

echo "Copying init script to /etc/init.d/yombo"
cp misc/yombo-init /etc/init.d/yombo
SEDCOMMAND="sed -i s#SERVICE_DIR=SOURCE__DIRECTORY#SERVICE_DIR=$(pwd)# /etc/init.d/yombo"
$SEDCOMMAND
SEDCOMMAND="sed -i s#USER=SOURCE__USER#USER=$SUDO_USER# /etc/init.d/yombo"
$SEDCOMMAND

echo "Making scripts excutable..."
chmod +x /etc/init.d/yombo

echo "Setting Yombo to start from run level 3"
ln -s ../init.d/yombo /etc/rc3.d/S99yombo

echo "Yombo installed.  To start service daemon, execute '/etc/init.d/yombo start'"
echo "To run not in daemon, execut: './yombo.sh'"
