#!/usr/bin/env bash
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
export SSL_CERT_FILE="$(python -m certifi)"
#YOMBO_SERVICE="$YOMBO_SERVICE -y $TACFILE"

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
echo "About to call this command: $YOMBO_SERVICE"
while :
do
  echo "Starting yombo svc..."
  eval $YOMBO_SERVICE
  OUT=$?
  echo "Last output: $OUT"
  if [ $OUT -ge "126" ]; then
    # Gateway died for some reason or was told to quit, so, lets exit!
    exit $OUT
  fi
done
