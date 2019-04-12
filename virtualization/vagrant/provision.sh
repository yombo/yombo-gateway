#!/bin/bash
set -e

readonly SETUP_DONE='/yombo-gateway/virtualization/vagrant/setup_done'
readonly RESTART='/yombo-gateway/virtualization/vagrant/restart'

usage() {
    echo '############################################################

Use `./provision.sh` to interact with Yombo. E.g:

- start the virtualization: `./provision.sh start`
- stop the virtualization: `./provision.sh stop`
- destroy the host and start anew: `./provision.sh recreate`

############################################################'
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

user_setup() {
rm -f setup_done
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

vagrant up --provision
touch setup_done
}

setup_done() {
    new_nat_ip=$(vagrant ssh -c "ip address show eth0 | grep 'inet ' | sed -e 's/^.*inet //' -e 's/\/.*$//'")
    new_eth_ip=$(vagrant ssh -c "ip address show eth1 | grep 'inet ' | sed -e 's/^.*inet //' -e 's/\/.*$//'")
    echo "############################################################
#          Yombo Gateway provision completed               #
############################################################
Username: vagrant
Password: vagrant

Private IP Address: new_nat_ip
Network IP Address: new_eth_ip

You can access the box using either:
ssh $new_nat_ip 2222
ssh $new_eth_ip

More information at https://yombo.net/docs/gateway/vagrant

"
}
main() {
    # If a parameter is provided, it's probably the user in interactive mode
    # with the provider script...
    case $1 in
        "setup") user_setup; exit ;;
        "restart") touch restart; vagrant provision ; exit ;;
        "start") vagrant up --provision ; exit ;;
        "stop") vagrant halt ; exit ;;
        "destroy") vagrant destroy -f ; exit ;;
        "recreate") rm -f setup_done restart; vagrant destroy -f; \
                    vagrant up --provision; exit ;;
    esac
    # ...otherwise we assume it's the Vagrant provisioner
    if [ $(hostname) != "contrib-ubuntu1804" ]; then usage && setup_done; exit; fi
    if ! [ -f $SETUP_DONE ]; then setup; fi
    if [ -f $RESTART ]; then restart; fi
    if [ -f $RUN_TESTS ]; then run_tests; fi
    if ! systemctl start yombo-gateway; then
        setup_error
    fi
}

main $*