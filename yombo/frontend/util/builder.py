#!/usr/bin/env python3

# This file is responsible for building both production and development frontend builds.
# This will collect the primary source from the Yombo directory as well as all the
# module directories. Once combined, it will start to build for either prod or dev.
#
# The working dir for this: $working_dir'/var/frontend Eg: /home/user/.yombo/var/frontend
#
#
# To run the build process, goto the frontend directory within the gateway repo, then:
# yarn run dev
#     or
# yarn run build

import os
import subprocess
import sys

if len(sys.argv) > 1:
    working_dir = sys.argv[1]
else:
    working_dir = "~/.yombo"

app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

frontend_utils_dir = os.path.dirname(os.path.realpath(__file__))
source_frontend_dir = os.path.dirname(frontend_utils_dir)

source_locale_dir = f"{os.path.dirname(source_frontend_dir)}/locale/frontend"
dest_frontend_dir = f"{working_dir}/var/frontend"
dest_lang_dir = f"{dest_frontend_dir}/lang"


print(working_dir)
print(app_dir)
print(frontend_utils_dir)
print(source_frontend_dir)
print(source_locale_dir)
print(dest_frontend_dir)
print(dest_lang_dir)



# The start of migration from sh script to python3. :-)

# def copy_source_files():
#     """ Copies the frontend directory to a build location."""
#     print("Copying frontend core directory.")
#     subprocess.run(["mkdir", "-p", dest_frontend_dir])
#     subprocess.run(["rsync", "-a", f"{source_frontend_dir}/", "--exclude", "/.nuxt/", "--exclude", "/dist",
#                     dest_frontend_dir])
#
#
# def copy_to_destination():
#     """ For production builds, copies the dist files to the final resting place when done. """
#     print("Copying final destination.")
#     subprocess.run(["mkdir", "-p", f"{working_dir}/frontend/"])
#     subprocess.run(["rsync", "-a", f"{dest_frontend_dir}/dist/", f"{working_dir}/frontend/"])


