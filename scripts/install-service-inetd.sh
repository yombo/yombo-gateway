#!/bin/bash
echo ""
if [ $UID != 0 ]; then
    echo "This must be run with sudo from the current user that will be using the gateway.
    echo
    echo "For example if user 'mitch' is installing the gateway, run this command logged
    echo "in as mitch: sudo install-service-initd.sh"
    exit
fi

echo "This will install Yombo Gateway as the current user. If you want this to"
echo "run as a separate user, first create the new user and run this script as"
echo "that user."
echo
echo "Installing for user: $SUDO_USER"
echo

echo -n "Continue? [Y/n] ?"

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

echo "Yombo installed. To start: `service yombo start`"
echo "To run without daemon, execute: './yombo.sh'"
