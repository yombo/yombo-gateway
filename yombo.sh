#!/bin/bash
# Simple wrapper to call the yombo gateway framework. Called either directly
# by the user or by the init script.  The defaults will work most the
# time.
#
# The actual call is wrapped in a while loop and checks the exit status code.
# This is because the gateway may restart itself on a config reload or software
# update.

#reset vars
YOMBO_LOGFILE="/var/log/yombo/yombo.log"
#YOMBO_LOGFILE="yombo.log"
#YOMBO_PIDFILE="/var/run/yombo/gateway.pid"
YOMBO_PIDFILE="yombogateway.pid"
YOMBO_TACFILE="yombo.tac"
YOMBO_LOGENABLE="0"
YOMBO_DAEMON="0"

#Check if pyenv is being used and isn't loaded...
if [ -f ".python-version" ] ; then
  if ! [ -x "$(command -v pyenv)" ]; then
    echo "Yombo.sh setting up pyenv"
    export PATH="~/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
  fi
fi

usage()
{
cat << EOF
usage: $0 options

This script starts the Yombo Gateway service.

OPTIONS:
   -u        Show URLs to access Yombo Gateway.
   -d        Run in daemon (service) mode. Called by init script.
   -h        Show this message
   -l file   Change log file location
   -p file   Change pid file location
   -t file   Change tac file location (rarely used)
   -P        Enable profiling to profile.out
   -v        Version information

EOF
}

YOMBO_OPTS="twistd --pidfile=$YOMBO_PIDFILE"
SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
# Process args
while getopts ":muvdhl:LPp:t:" opt; do
  case $opt in
    m)
      # Show yombo motd
      $SCRIPTPATH/scripts/show_motd
      exit 1
      ;;
    u)
      # Show yombo urls
      $SCRIPTPATH/scripts/show_urls
      exit 1
      ;;
    v)
      # Show version of yombo.
      $SCRIPTPATH/scripts/show_version
      exit 1
      ;;
    d)
      # Run as daemon (used by init script)
      YOMBO_DAEMON=1
      ;;
    h)
      # Show help
      usage
      exit 1
      ;;
    l)
      # Change log file location
      YOMBO_LOGFILE=$OPTARG
      ;;
    t)
      # Change TAC file location
      YOMBO_TACFILE=$OPTARG
      ;;
    P)
      # Enable profiling
      echo "enabling profiler"
      YOMBO_OPTS="$YOMBO_OPTS --savestats --profiler cprofile -n --profile prof.stats"
      ;;
    p)
      # Change pid file location
      YOMBO_PIDFILE=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "For help: $0 -h" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

#Check if PID is running, if it is, then exit gracefully.
if [ -e $YOMBO_PIDFILE ]; then
  mypid=`cat $YOMBO_PIDFILE`
  if kill -0 &>1 > /dev/null $mypid; then
    echo "Yombo Gateway already running with pid: $mypid"
    exit 1
  fi
fi

if [ $YOMBO_DAEMON -eq "0" ]; then
   YOMBO_OPTS="$YOMBO_OPTS -n"
else
   YOMBO_OPTS="$YOMBO_OPTS --logfile=$YOMBO_LOGFILE"
fi

export SSL_CERT_FILE="$(python -m certifi)"
YOMBO_OPTS="$YOMBO_OPTS -y $YOMBO_TACFILE"

while :
do
  if [ $YOMBO_DAEMON -eq "1" ]; then
     $YOMBO_OPTS &
  else
     $YOMBO_OPTS
  fi
  OUT=$?
  if [ $OUT -le "126" ]; then
    # Gateway died for some reason or was told to quit, so, lets exit!
    exit $OUT
  fi
done
