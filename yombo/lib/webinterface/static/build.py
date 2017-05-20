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
    print("Saving to %s..." % output)
    with open(output, 'w') as outfile:
        for fname in inputs:
            print("...%s" % fname)
            with open(fname) as infile:
                outfile.write(infile.read())
    print("")


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
        'source/jquery/jquery-2.2.4.min.js',
        'source/sb-admin/js/js.cookie.min.js',
        'source/bootstrap/dist/js/bootstrap.min.js',
        'source/metisMenu/metisMenu.min.js',
    ]
    CAT_SCRIPTS_OUT = 'dist/js/jquery-cookie-bootstrap-metismenu.min.js'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        'source/bootstrap/dist/css/bootstrap.min.css',
        'source/metisMenu/metisMenu.min.css',
    ]
    CAT_SCRIPTS_OUT = 'dist/css/bootsrap-metisMenu.min.css'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        'source/sb-admin/js/sb-admin-2.min.js',
        'source/sb-admin/js/yombo.js',
    ]
    CAT_SCRIPTS_OUT = 'dist/js/sb-admin2.min.js'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        'source/sb-admin/css/sb-admin-2.css',
        'source/sb-admin/css/yombo.css',
        'source/font-awesome/css/font-awesome.min.css',
        ]
    CAT_SCRIPTS_OUT = 'dist/css/admin2-font_awesome.min.css'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        'source/datatables-plugins/integration/bootstrap/3/dataTables.bootstrap.css',
        'source/datatables-responsive/css/responsive.dataTables.min.css',
        ]
    CAT_SCRIPTS_OUT = 'dist/css/datatables.min.css'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        'source/datatables/js/jquery.dataTables.min.js',
        'source/datatables-plugins/integration/bootstrap/3/dataTables.bootstrap.min.js',
        'source/datatables-responsive/js/dataTables.responsive.min.js',
        ]
    CAT_SCRIPTS_OUT = 'dist/js/datatables.min.js'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        'source/chartist/chartist.min.js',
        ]
    CAT_SCRIPTS_OUT = 'dist/js/chartist.min.js'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    CAT_SCRIPTS = [
        'source/chartist/chartist.min.css',
        ]
    CAT_SCRIPTS_OUT = 'dist/css/chartist.min.css'
    do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

    # Just copy files
    copytree('source/font-awesome/fonts/', 'dist/fonts/')
    copytree('source/bootstrap/dist/fonts/', 'dist/fonts/')


if __name__ == '__main__':
    main()
