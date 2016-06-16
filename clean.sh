#!/bin/sh
# Used to quickly clean up all compiled versions of the source code.
# Normally only used for testing and development.

find . -type f -name "*.pyc" -exec rm -f {} \;
find . -type f -name "*.c" -exec rm -f {} \;
