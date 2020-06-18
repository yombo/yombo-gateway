#!/usr/bin/env python3

# This python script is for Yombo.Net locale file merging. This merges multiple JSON files into a single file.

from collections.abc import Mapping
import json
import os
import sys

if len(sys.argv) > 1:
    working_dir = sys.argv[1]
else:
    working_dir = f"{os.path.expanduser('~')}/.yombo"

app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))

frontend_utils_dir = os.path.dirname(os.path.realpath(__file__))
source_frontend_dir = os.path.dirname(frontend_utils_dir)

source_locale_dir = f"{os.path.dirname(source_frontend_dir)}/locale/frontend"
dest_frontend_dir = f"{working_dir}/var/frontend"
dest_lang_dir = f"{dest_frontend_dir}/lang"

# print(working_dir)
# print(app_dir)
# print(frontend_utils_dir)
# print(source_frontend_dir)
# print(source_locale_dir)
# print(dest_frontend_dir)
# print(dest_lang_dir)


def recursive_dict_merge(original, changes):
    """
    Recursively merges a dictionary with any changes. Sub-dictionaries won't be overwritten - just updated.
    """
    for key, value in changes.items():
        if (key in original and isinstance(original[key], dict)
                and isinstance(changes[key], Mapping)):
            recursive_dict_merge(original[key], changes[key])
        else:
            original[key] = changes[key]
    return original


def read_json_file(file):
    suffix = file.split(".")[-1]
    if suffix != "json":
        raise FileNotFoundError("Invalid json file extension.")
    with open(file) as json_file:
        return json.load(json_file)


locales = {}  # Store all the language translations.. YAY memory
primary_locale = os.listdir(source_locale_dir)
for file in primary_locale:
    try:
        locales[file] = read_json_file(f"{source_locale_dir}/{file}")
    except json.JSONDecodeError as e:
        print(f"System frontend local file has invalid format (bad JSON): {source_locale_dir}/{file}:")
        print(e)
        continue
    except FileNotFoundError as e:
        print(f"Error reading module local file: {e}")
        continue

modules_dir = os.listdir(f"{app_dir}/yombo/modules")
for module in modules_dir:
    full_path = f"{app_dir}/yombo/modules/{module}"
    if os.path.isdir(full_path):
        if os.path.isdir(f"{full_path}/frontend_locale"):
            module_locals = os.listdir(f"{full_path}/frontend_locale")
            for file in module_locals:
                try:
                    recursive_dict_merge(locales[file], read_json_file(f"{full_path}/frontend_locale/{file}"))
                except json.JSONDecodeError as e:
                    print(f"Module file has invalid format for local file (bad JSON): {full_path}/frontend_locale/{file}:")
                    print(e)
                    continue
                except FileNotFoundError as e:
                    print(f"Error reading module local file: {e}")
                    continue

for file, data in locales.items():
    filename = file.split(".")[0]
    if filename == "en":
        with open(f"{dest_lang_dir}/{filename}.json", "w") as outfile:
            json.dump(data, outfile)
    else:
        with open(f"{dest_lang_dir}/{filename}.js", "w") as outfile:
            outfile.write(f"export default {json.dumps(data)}")
