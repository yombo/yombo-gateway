#!/usr/bin/env python3
"""Home Assistant setup script."""
from setuptools import setup, find_packages

import yombo.constants as yombo_const

PROJECT_NAME = 'Yombo'
PROJECT_PACKAGE_NAME = 'yombo'
PROJECT_LICENSE = 'Yombo Reciprocal Public License 1.6'
PROJECT_AUTHOR = 'The Yombo Authors'
PROJECT_COPYRIGHT = ' 2012-2018, {}'.format(PROJECT_AUTHOR)
PROJECT_URL = 'https://yombo.net/'
PROJECT_EMAIL = 'hello@yombo.net'
PROJECT_DESCRIPTION = ('Web based open-source home automation platform '
                       'using Python 3.')
PROJECT_LONG_DESCRIPTION = ('Yombo is an open-source home automation '
                            'platform running on Python 3 with an easy to use '
                            'web interfaces for setup and configuration. Track '
                            'and control various components within minutes.')
PROJECT_CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Home Automation'
]

PROJECT_GITHUB_USERNAME = 'yombo'
PROJECT_GITHUB_REPOSITORY = 'yombo-gateway'

PYPI_URL = 'https://pypi.python.org/pypi/{}'.format(PROJECT_PACKAGE_NAME)
GITHUB_PATH = '{}/{}'.format(
    PROJECT_GITHUB_USERNAME, PROJECT_GITHUB_REPOSITORY)
GITHUB_URL = 'https://github.com/{}'.format(GITHUB_PATH)

DOWNLOAD_URL = '{}/archive/{}.zip'.format(GITHUB_URL, yombo_const.__version__)

PACKAGES = find_packages(exclude=['tests', 'tests.*'])

REQUIRES = [
    'argon2_cffi>=18.1.0',
    'asyncio==3.4.*',
    'certifi',
    'cython',
    'decorator',
    'dnspython',
    'docutils',
    'ephem',
    'gnupg',
    'hashids',
    'hjson',
    'jinja2',
    'klein',
    'logger',
    'markdown',
    'msgpack-python',
    'netaddr',
    'netifaces',
    'numpy',
    'parsedatetime',
    'passlib',
    'pika',
    'pydispatcher',
    'pyephem',
    'pyopenssl',
    'pyserial==3.2.0',
    'python_dateutil',
    'python-gnupg',
    'pytz',
    'service_identity',
    'six',
    'treq',
    'Twisted==18.4.*',
    'unidecode',
    'uvloop',
    'voluptuous',
    'wheel',
]

MIN_PY_VERSION = '.'.join(map(str, yombo_const.REQUIRED_PYTHON_VER))

setup(
    name=PROJECT_PACKAGE_NAME,
    version=yombo_const.__version__,
    license=PROJECT_LICENSE,
    url=PROJECT_URL,
    download_url=DOWNLOAD_URL,
    author=PROJECT_AUTHOR,
    author_email=PROJECT_EMAIL,
    description=PROJECT_DESCRIPTION,
    packages=PACKAGES,
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=REQUIRES,
    python_requires='>={}'.format(MIN_PY_VERSION),
#    test_suite='tests',
    keywords=['home', 'automation'],
    entry_points={
        'console_scripts': [
            'ybo = yombo.__main__:main'
        ]
    },
    classifiers=PROJECT_CLASSIFIERS,
)
