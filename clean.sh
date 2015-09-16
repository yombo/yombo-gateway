#!/bin/sh
# Used by developers to quickly clean up the folder structure.

find . -type f -name "*.pyc" -exec rm -f {} \;
find . -type f -name "*.c" -exec rm -f {} \;
