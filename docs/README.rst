====================
Yombo Documentation
====================

This directory generates the content found at https://yombo.net/docs/gateway/html/current/index.html
and is generated from the comments within the source code.

This documentation is aimed at developers for code reference and lookup, it's
not intended for end user. End user documentation is found at:
https://yombo.net/docs

More development documentation can be found at: https://yg2.in/dev

Building the docs
=================

The documentation is build using sphinx. To get started, open a command prompt
and change to this directory (the docs subdirectory) and install the requirements:

From the root yombo-gateway directory:
pip3 install -r requirements.txt
pip3 install -r requirements-doc.txt

After installation, to build the documentation:

make html

The docuementation will be created in the build/html subdirectory of the docs directory.
