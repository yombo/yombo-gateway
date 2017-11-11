#!/bin/sh
# Used by developers to quickly clean up the folder structure.
echo "This script simply cleans up cached compiled python code files."
find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
echo "[-] Local python cache files have been removed."
