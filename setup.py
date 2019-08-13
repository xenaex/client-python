#!/usr/bin/env python
import codecs
import os
import re
from setuptools import setup


with codecs.open(
        os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            'xena',
            '__init__.py'
        ), 'r', 'latin1') as fp:
    try:
        version = re.findall(r"^__version__ = '([^']+)'$", fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')

setup(
    name='python-xena',
    version=version,
    packages=['xena'],
    description='XenaExchange API python implementation',
    license='MIT',
    author_email='',
    install_requires=[
        'requests', 'six', 'pyOpenSSL', 'service-identity', 'dateparser', 'urllib3', 'chardet', 'certifi',
        'cryptography', 'aiohttp', 'ecdsa', 'protobuf'
    ],
    keywords='xena exchange api bitcoin ethereum btc eth neo',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
