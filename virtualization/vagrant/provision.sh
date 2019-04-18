#!/bin/bash
set -e

readonly SETUP_DONE='/yombo-gateway/virtualization/vagrant/setup_done'
readonly RESTART='/yombo-gateway/virtualization/vagrant/restart'

readonly SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
readonly PARENTPATH="$(dirname "$SCRIPTPATH")"
readonly YOMBOPATH="$(dirname "$PARENTPATH")"

usesss() {
echo "asdfasdfasdf";
}

usage() {
    echo '
############################################################
Use `./provision.sh` to manage the virtualization.

- yombo status:                    `./provision.sh status`
- start the virtualization:        `./provision.sh start`
- stop the virtualization:         `./provision.sh stop`
- destroy the host and start anew: `./provision.sh recreate`

Note: You can open the VirtualBox console after provisioning
is complete the adjust the system resources.
############################################################'
}

guest_status() {
    echo "Getting IP addresses, please wait..."
    new_nat_ip=$(vagrant ssh -c "ip address show eth0 | grep 'inet ' | sed -e 's/^.*inet //' -e 's/\/.*$//'")
    new_eth_ip=$(vagrant ssh -c "ip address show eth1 | grep 'inet ' | sed -e 's/^.*inet //' -e 's/\/.*$//'")
    echo "
############################################################
#          Yombo Gateway provision status                  #
############################################################
Username: vagrant
Password: vagrant

Private IP Address: $new_nat_ip
Network IP Address: $new_eth_ip

Fetching Yombo MOTD...
"
vagrant ssh -c "ybo motd"
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
    echo
    echo "About to setup a Vagrant Yombo Gateway installation."
    echo
    echo "#################################################################"
    echo "#                          IMPORTANT                            #"
    echo "#################################################################"
    echo "# If you are prompted for a default bridge, select your primary #"
    echo "# network interface. Usually eth0 or eno1.                      #"
    echo "#################################################################"
    echo
    echo
}

setup() {
    echo "Starting Yombo Setup...."
    local ygw_path='/yombo-gateway/ybo'
    local systemd_bin_path='/usr/bin/ybo'

    touch /home/vagrant/.yombo
    chown vagrant:vagrant /home/vagrant/.yombo
#    touch /home/vagrant/yombo_setup.log
#    chown vagrant:vagrant /home/vagrant/yombo_setup.log
#    touch /home/vagrant/yombo_setup_detailed.log
#    chown vagrant:vagrant /home/vagrant/yombo_setup_detailed.log

    /yombo-gateway/scripts/helpers/ubuntu_setup vagrant
    runuser -l vagrant -c "bash -i /yombo-gateway/scripts/helpers/pyenv_setup"
    if ! [ -f $systemd_bin_path ]; then
        ln -s $ygw_path $systemd_bin_path
    fi

    # Setup systemd
    cp /yombo-gateway/virtualization/vagrant/yombo-gateway@.service \
        /etc/systemd/system/yombo-gateway.service
#    systemctl --system daemon-reload
#    systemctl enable yombo-gateway
#    systemctl stop yombo-gateway
    # Install packages
    touch $SETUP_DONE
    usage
    ybo motd
}

main() {
    # If a parameter is provided, it's probably the user in interactive mode
    # with the provider script...
    case $1 in
        "setup") rm -f setup_done; setup_start; vagrant up --provision; exit ;;
        "restart") vagrant halt ; vagrant resume ; exit ;;
        "start") vagrant resume ; guest_status ; exit ;;
        "stop") vagrant halt ; exit ;;
        "destroy") vagrant destroy -f ; exit ;;
        "recreate") setup_start; rm -f setup_done restart; vagrant destroy -f; \
                    vagrant up --provision; exit ;;
        "status") show_status; exit ;;
    esac
    # ...otherwise we assume it's the Vagrant provisioner
    echo "Hostname: $(hostname)"
    if [ $(hostname) != "ubuntu1804.localdomain" ]; then usesss; exit; fi
    if ! [ -f $SETUP_DONE ]; then setup; fi
    if [ -f $RESTART ]; then restart; fi
    if ! systemctl start yombo-gateway; then
        setup_error
    fi
}

main $*