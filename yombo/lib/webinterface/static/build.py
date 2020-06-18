#!/usr/bin/env python

# The dist folder is built when the gateway runs. This file is here for development purposes.

##################
#
# Any changes to this file needs to be duplicated in the webinterface library _build_dist() function.
#
##################

# Builds the 'dist' directory from the 'build' directory. Easy way to update the source css/js files and update
# the webinterface JS and CSS files.

from os import path, listdir, mkdir
import shutil

if not path.exists('dist/'):
    mkdir('dist')
if not path.exists('dist/css'):
    mkdir('dist/css')
if not path.exists('dist/js'):
    mkdir('dist/js')


def do_cat(inputs, output):
    with open(output, 'w') as outfile:
        for fname in inputs:
            with open(fname) as infile:
                outfile.write(infile.read())


def copytree(src, dst, symlinks=False, ignore=None):
    if path.isdir(src):
        if not path.exists(dst):
            mkdir(dst)
    for item in listdir(src):
        s = path.join(src, item)
        d = path.join(dst, item)
        if path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def main():
    CAT_SCRIPTS = [
        "source/bootstrap4/css/bootstrap.min.css",
        "source/bootstrap-select/css/bootstrap-select.min.css",
        "source/bootstrap4-toggle/bootstrap4-toggle.min.css",
        "source/yombo/yombo.css",
        "source/yombo/mappicker.css",
    ]
    CAT_SCRIPTS_OUT = "css/basic_app.min.css"
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        "source/yombo/mappicker.js",
    ]
    CAT_SCRIPTS_OUT = "js/mappicker.js"
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        "source/jquery/jquery.validate.min.js",
    ]
    CAT_SCRIPTS_OUT = "js/jquery.validate.min.js"
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        "source/jquery/jquery-3.3.1.min.js",
        "source/jquery/jquery.validate.min.js",
        "source/js-cookie/js.cookie.min.js",
        "source/bootstrap4/js/bootstrap.bundle.min.js",
        "source/bootstrap-select/js/bootstrap-select.min.js",
        "source/yombo/jquery.are-you-sure.js",
        "source/bootstrap4-toggle/bootstrap4-toggle.min.js",
        "source/yombo/yombo.js",
    ]
    CAT_SCRIPTS_OUT = "js/basic_app.js"
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

if __name__ == '__main__':
    main()
