#!/bin/bash
set -e

readonly SETUP_DONE='/yombo-gateway/virtualization/vagrant/setup_done'
readonly RESTART='/yombo-gateway/virtualization/vagrant/restart'

readonly SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
readonly PARENTPATH="$(dirname "$SCRIPTPATH")"
readonly YOMBOPATH="$(dirname "$PARENTPATH")"

usage() {
    echo '
############################################################
Use `./provision.sh` to manage the virtualization.

usage: ./provision.sh [command]
example: ./providion setup

COMMANDS:
  status    Get the status of the machine
  setup     Create the virtual machine
  start     Start the virtual machine
  stop      Stop the virtual machine
  restart      Stop the virtual machine
  recreate  Destroy the machine, if any, and create anew

Note: You can open the VirtualBox console after provisioning
is complete the adjust the system resources.
############################################################'
}

guest_status() {
    echo "Getting IP addresses, please wait..."
    new_nat_ip=$(vagrant ssh -c "ip address show eth0 | grep 'inet ' | sed -e 's/^.*inet //' -e 's/\/.*$//'" 2> /dev/null)
    echo "
############################################################
#          Yombo Gateway provision status                  #
############################################################
Username: vagrant
Password: vagrant
"
    new_eth_ip=$(vagrant ssh -c "ip address show eth1 | grep 'inet ' | sed -e 's/^.*inet //' -e 's/\/.*$//'" 2> /dev/null)
echo "Private IP Address: $new_nat_ip
Network IP Address: $new_eth_ip

Fetching Yombo MOTD...
"
vagrant ssh -c 'bash -i -c "ybo motd"'
}

show_status() {
if [ -f "$SCRIPTPATH/setup_done" ]; then
  guest_status
else
  echo
  echo "Vagrant is not setup. Run: ./provision.sh setup"
fi
}

setup_error() {
    echo '############################################################
Error with setup, perhaps setup did not complete?
Please run setup again and ensure it ran correctly at least once.

Try again with: `./provision.sh setup`

See https://yombo.net/docs/gateway/vagrant for more details.

############################################################'
    exit 1
}

restart() {
    echo "Restarting Yombo Gateway."
    if ! systemctl restart yombo-gateway; then
        setup_error
    else
        echo "done"
    fi
    rm $RESTART
}

setup_start() {
    rm -f $SETUP_DONE
    echo
    echo -e "\e[1mAbout to setup a Vagrant Yombo Gateway installation.\e[0m"
    echo
    echo
    echo
    echo -e "\e[1m#################################################################"
    echo -e "\e[1m#                          IMPORTANT                            #"
    echo -e "\e[1m#################################################################"
    echo -e "\e[1m# If you are prompted for a default bridge, select your primary #"
    echo -e "\e[1m# network interface. Usually eno1 or eth0.                      #"
    echo -e "\e[1m#################################################################"
    echo
    echo
    echo
}

setup() {
    echo "Starting Yombo Setup...."
    local ygw_path='/yombo-gateway/ybo'
    local systemd_bin_path='/usr/local/bin/ybo'

    touch /home/vagrant/.yombo
    chown vagrant:vagrant /home/vagrant/.yombo

    if ! [ -f "$SCRIPTPATH/setup_done" ]; then
        sudo apt-get update
        echo "==> apt-get - Upgrading OS (apt-get upgrade) - starting downloads"
        sudo apt-mark hold keyboard-configuration
        sudo apt-mark hold grub-pc

        apt-get upgrade --download-only -y

        echo "==> apt-get - Upgrading OS (apt-get upgrade) - Upgrading OS, this will take a few minutes"
        apt-get upgrade -y
        sudo apt-mark unhold keyboard-configuration
        sudo apt-mark unhold grub-pc

        sudo apt upgrade
        /yombo-gateway/scripts/yombo_install vagrant
        touch $SETUP_DONE
    fi
    if ! [ -f $systemd_bin_path ]; then
        ln -s $ygw_path $systemd_bin_path
    fi

    usage
}

check_setup() {
    if ! [ -f "$SCRIPTPATH/setup_done" ]; then
      echo
      echo -e "\e[1mVagrant not setup!\e[0m"
      echo
      echo -e "\e[1m#################################################################"
      echo -e "\e[1m#                          IMPORTANT                            #"
      echo -e "\e[1m#################################################################"
      echo -e "\e[1m# Run './provision setup'   first.                              #"
      echo -e "\e[1m#################################################################"
      exit
    fi
}

main() {
    # If a parameter is provided, it's probably the user in interactive mode
    # with the provider script...
    case $1 in
        "setup") rm -f setup_done; vagrant box update; setup_start; vagrant up --provision; guest_status; exit ;;
        "restart") vagrant halt ; sleep 1; vagrant up --provision ; exit ;;
        "start") check_setup; vagrant up --provision; guest_status; exit ;;
        "stop") vagrant halt ; exit ;;
        "destroy") vagrant destroy -f ; rm -f setup_done; rm -rf ./working_dir/* ; \
                   touch ./working_dir/.placeholder ; exit ;;
        "recreate") setup_start; rm -f setup_done restart; vagrant destroy -f; \
                    rm -rf ./working_dir/* ; touch ./working_dir/.placeholder ; vagrant box update; \
                    vagrant up --provision; guest_status; exit ;;
        "status") show_status; exit ;;
    esac
    # ...otherwise we assume it's the Vagrant provisioner
    if [ $(hostname) != "ubuntu2004.localdomain" ]; then usage; exit; fi
    if ! [ -f $SETUP_DONE ]; then setup; fi
    if [ -f $RESTART ]; then restart; fi
    if ! systemctl start yombo.service; then
        setup_error
    fi
}

main $*
