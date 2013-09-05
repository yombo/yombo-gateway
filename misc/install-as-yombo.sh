#!/bin/bash
echo
echo
if [ $UID != 0 ]; then
    echo "This must be run with sudo or as root."
    exit
fi

# Set a default home
YOMBOHOME="/home/yombo"

if [ "x$1" == "x" ]; then
    echo "You are using the default install location."
    echo "You can change this by running install.sh with a path."
    echo "Example:  install.sh /usr/local/lib/yombo"
    echo
    echo "Default: /home/yombo"
    echo
fi

echo -n "Install set to: $YOMBOHOME [Y/n] ?"
read a
if [ "x$a" == "xn" ] || [ "x$a" == "xN" ]; then
    exit
fi

echo "Creating user 'yombo'."
useradd -m -d $YOMBOHOME yombo
if [ ! -d $YOMBOHOME ]; then
    mkdir $YOMBOHOME
fi

echo "Creating PID file location."
if [ ! -d /var/run/yombo ]; then
  mkdir /var/run/yombo
  chown yombo:yombo /var/run/yombo
  chmod 775 /var/run/yombo
fi

echo "Copying files to $YOMBOHOME..."
cp -a * $YOMBOHOME
chown -R yombo:yombo $YOMBOHOME

echo "Copying init script to /etc/init.d/yombo"
cp misc/yombo-init /etc/init.d/yombo

echo "Making scripts excutable..."
chmod +x /etc/init.d/yombo

echo "Setting Yombo to start from run level 3"
ln -s ../init.d/yombo /etc/rc3.d/S99yombo

echo "Yombo installed.  To start service daemon, execute '/etc/init.d/yombo start'"
echo "To run not in daemon, login as yombo with 'sudo su yombo' and then ./yombo.sh'"
