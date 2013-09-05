#!/bin/bash
# Simple wrapper to call the twistd framework
twistd --pidfile=/var/run/yombo/yombo.pid -n -y yombo.tac

#Profiling options
##  twistd --profiler=cprofile -p profile.out --profiler "cprofile" -n -y yombo.tac
#  twistd --profiler=cprofile -p profile.out -n -y yombo.tac

