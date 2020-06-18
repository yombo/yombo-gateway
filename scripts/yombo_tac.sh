#!/usr/bin/env bash
#
# This script shouldn't be called directly. This is called by 'ybo daemon'
#
# a basic wrapper around the yombo.tac (yombo service).

if [[ "$EUID" -eq 0 ]]; then
  echo ""
  echo "This must NOT be run as root, instead run as the user running the Yombo Gateway"
  echo ""
  echo "This script shouldn't be run directly."
  echo ""
  exit
fi

read -t .1 ECHOTAC
ARGUMENTS="$@"

SCRIPTPATH="$(dirname "$(readlink -f "$0")")"
rc=$?
if [[ $rc != 0 ]]; then
 SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
fi
WORK_DIR="$HOME/.yombo"
LOGCFGFILE=$WORK_DIR/log/config.log
LOGFILE=$WORK_DIR/log/service.log

cd $SCRIPTPATH/..
#export SSL_CERT_FILE="$(python -m certifi)"

#Check if pyenv is being used and isn't loaded...
if [ -f ".python-version" ] ; then
  if ! [ -x "$(command -v pyenv)" ]; then
    echo "Yombo.sh setting up pyenv"
    export PATH="~/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
  fi
fi

YOMBO_SERVICE="echo \"$ECHOTAC\" | twistd $ARGUMENTS"
while :
do
  echo "Starting yombo svc..."
  eval $YOMBO_SERVICE
  OUT=$?
  echo "Gateway ended: $OUT"
  if [ $OUT != "4" ]; then   # 4 is the exit code to signify a restart
    exit $OUT  # Gateway died for some reason or was told to quit, so, lets exit!
  fi
done
