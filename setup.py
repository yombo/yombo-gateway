import codecs
import os

from setuptools import setup, find_packages

# from distutils.core import setup
# from distutils.extension import Extension

HERE = os.path.abspath(os.path.dirname(__file__))

def read(*parts):
    """
    Build an absolute path from *parts* and and return the contents of the
    resulting file.  Assume UTF-8 encoding.
    """
    with codecs.open(os.path.join(HERE, *parts), "rb", "utf-8") as f:
        return f.read()

def list_files(path):
    files = (file for file in os.listdir(os.path.join(HERE, path))
             if os.path.isfile(os.path.join('yombo/lib', file)))

    good_files = []
    for file in files: # You could shorten this to one line, but it runs on a bit.
        if file.endswith('.py'):
            new_file = path + '/' +file
            new_file.replace('/', '.')
            good_files.append(path + '/' +file)

    return good_files

NAME = "yombo"
VERSION = "0.12.0.alpha"
DESCRIPTION = "Yombo automation software for home and business.",
URL='https://yombo.net/'
AUTHOR='Mitch Schwenk',
AUTHOR_EMAIL='mitch-gwy@yombo.net',
MAINTAINER='Yombo',
MAINTAINER_EMAIL='support-pypi@yombo.net',
LICENSE='YRPL',
PACKAGES=['yombo'],
KEYWORDS = ["automation"]
CLASSIFIERS=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Natural Language :: English',
        'Operating System :: OS Independent',

        # Indicate who your project is intended for
        'Intended Audience :: Users',
        'Topic :: Home Automation :: Business Automation',

        # Pick your license as you wish (should match "license" above)
         'License :: YRPL',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

REQUIRES=[
        'hbmqtt',
        'Twisted',
        'python-gnupg',
        'pyephem',
        'gnupg',
        'service_identity',
        'parsedatetime'
        ],

Y_CORE = list_files("yombo/core")
Y_LIB = list_files("yombo/lib")
PY_MODULES = Y_CORE + Y_LIB


#     ext_modules =  [
#                     Extension("yombo.core.fuzzysearch", ["yombo/core/fuzzysearch.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.core.message", ["yombo/core/message.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.core.sqldict", ["yombo/core/sqldict.pyx"], extra_link_args=['-s']),
# #                    Extension("yombo.core.voicecmd", ["yombo/core/voicecmd.pyx"], extra_link_args=['-s']),
#
#                     Extension("yombo.lib.configuration", ["yombo/lib/configuration.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.lib.configurationupdate", ["yombo/lib/configurationupdate.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.lib.commands", ["yombo/lib/commands.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.lib.devices", ["yombo/lib/devices.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.lib.downloadmodules", ["yombo/lib/downloadmodules.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.lib.gatewaycontrol", ["yombo/lib/gatewaycontrol.pyx"], extra_link_args=['-s']),
# #                    Extension("yombo.lib.gatewaydata", ["yombo/lib/gatewaydata.pyx"], extra_link_args=['-s']),
#                     Extension("yombo.lib.times", ["yombo/lib/times.pyx"], extra_link_args=['-s']),
#                    ],
#     data_files = [
#                   ('yombo', ['yombod', 'yombo.tac', 'LICENSE', 'README']),
#                   ('/etc', ['yombo.ini']),
#                  ],
# )

if __name__ == "__main__":
    print Y_LIB

    setup(
        name=NAME,
        description=DESCRIPTION,
        license=LICENSE,
        url=URL,
        version=VERSION,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        keywords=KEYWORDS,
        long_description=read("README.rst"),
        # packages=PACKAGES,
        # py_modules=PY_MODULES,
        zip_safe=False,
        classifiers=CLASSIFIERS,
        install_requires=REQUIRES,
    )
