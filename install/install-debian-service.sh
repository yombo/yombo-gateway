#!/bin/bash
echo
echo
if [ $UID != 0 ]; then
    echo "This must be run with sudo."
    exit
fi

echo "This will install Yombo Gateway as the current user. If you want this to"
echo "run as a separate user, first create the new user and run this script as"
echo "that user."
echo
echo "Installing for user: $SUDO_USER"
echo
echo "This script will install the start/stop daemon using the current path."
echo

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
cp yombo-init /etc/init.d/yombo
DAEMON=SOURCE__DAEMON

_scriptLocation="$(readlink -f ${BASH_SOURCE[0]})"
 YOMBO_PARENTDIR="$(dirname $_scriptLocation)"

SEDCOMMAND="sed -i s#DAEMON=SOURCE__DAEMON#DAEMON=$YOMBO_PARENTDIR/yombo.sh# /etc/init.d/yombo"
$SEDCOMMAND
SEDCOMMAND="sed -i s#SERVICE_DIR=SOURCE__DIRECTORY#SERVICE_DIR=$YOMBO_PARENTDIR# /etc/init.d/yombo"
$SEDCOMMAND
SEDCOMMAND="sed -i s#USER=SOURCE__USER#USER=$SUDO_USER# /etc/init.d/yombo"
$SEDCOMMAND

echo "Making scripts excutable..."
chmod +x /etc/init.d/yombo

echo "Setting Yombo to start from run level 3"
ln -s ../init.d/yombo /etc/rc3.d/S99yombo

echo "Yombo installed.  To start service daemon, execute '/etc/init.d/yombo start'"
echo "To run not in daemon, execute: './yombo.sh'"
