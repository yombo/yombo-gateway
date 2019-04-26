#!/usr/bin/env python

"""
This file extracts a lokalise download file and places them in the correct directory.

To use:
1. Download the file from: https://lokalise.co/public/974982865b3422bf9a2177.49453396/
   - Click on download
   - Select all languages
   - Format: .json
   - File Structure: All Keys
   - Empty Translations: Don't export
   - Plural Format: Symfony
   - Placeholder format: ICU
   - Indentation: 2 spaces
2. Save the file to this folder as: Yombo_Frontend-locale.zip
3. Run this script: ./lang.py
4. Have some ice cream.
"""

import os
import shutil
import zipfile

# Unzip the file to 'locale' subfolder.
with zipfile.ZipFile("Yombo_Frontend-locale.zip", "r") as zip_ref:
    zip_ref.extractall(".")

# Create a list of files to process
files = os.listdir("./locale/")

for file in files:  # Process each file.
  parts = file.split(".")
  if parts[1] == "json":  # Open a file, append 'export' to it, and then spit it back out.
    in_file = f"./locale/{parts[0]}.json"
    print(f"Processing: {in_file: <22} ->    ../lang/{parts[0]}.js")
    open(f"../lang/{parts[0]}.js", "w").write("export default " + open(in_file, "r").read())

shutil.copyfile("./locale/en.json", "../lang/en.json")
