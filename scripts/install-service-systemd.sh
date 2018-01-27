#!/bin/bash
echo ""
if [ $UID != 0 ]; then
    echo "This must be run with sudo from the current user that will be using the gateway.
    echo
    echo "For example if user 'mitch' is installing the gateway, run this command logged
    echo "in as mitch: sudo install-debian-service.sh"
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

echo "Copying init script to /etc/systemd/system"
cp yombo-systemd /etc/systemd/system/yombo.service
sudo chmod 755 /etc/systemd/system/yombo.service

systemctl enable yombo

echo "Yombo installed. To start: `service yombo start`"
echo "To run without daemon, execute: './yombo.sh'"
