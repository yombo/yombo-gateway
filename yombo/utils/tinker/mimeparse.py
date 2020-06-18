#!/usr/bin/env python3
"""
Tests various encryption speeds.
"""
import sys
import os
from time import time

sys.path.append(os.getcwd() + '/../../..')

# Import 3rd-party libs
import yombo.ext.magic as magicfile
magicparse = magicfile.Magic(mime_encoding=True, mime=True)

rounds = 10

source_data = b"Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore " \
              b"et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut " \
              b"aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse " \
              b"cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in " \
              b"culpa qui officia deserunt mollit anim id est laborum."

print("Magic file detection speed...")
print(f"Testing with: {rounds} iterations.  Times are in seconds.")

data = source_data+source_data+source_data+source_data+source_data+source_data+source_data+source_data+source_data
data = data+data+data+data+data+data+data+data+data+data+data+data+data+data+data+data+data+data+data+data+data+data
start = time()
for i in range(0, rounds):
    results = magicparse.from_buffer(data)
end = time()
print(results)
print(f"MagicParse: {round(end-start, 5)}")
