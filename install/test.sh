#!/bin/bash
# Name: /tmp/demo.bash : 
# Purpose: Tell in what directory $0 is stored in
# Warning: Not tested for portability 
# ------------------------------------------------
 
## who am i? ##
_script="$(readlink -f ${BASH_SOURCE[0]})"
 
## Delete last component from $_script ##
_base="$(dirname $_script)"
 
## Okay, print it ##
echo "Script name : $_script"
echo "Current working dir : $PWD"
echo "Script location path (dir) : $_base"
