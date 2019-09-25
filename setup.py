#!/usr/bin/python

from setuptools import setup

setup(
    name='izaber_wamp_zerp',
    version='2.5.20190925',
    description='Base load point for iZaber WAMP ZERP code',
    url = 'https://github.com/zabertech/python-izaber-wamp-zerp',
    download_url = 'https://github.com/zabertech/python-izaber-wamp-zerp/archive/2.4.tar.gz',
    author='Aki Mimoto',
    author_email='aki+izaber@zaber.com',
    license='MIT',
    packages=['izaber_wamp_zerp'],
    scripts=[],
    entry_points={
        'console_scripts': [
            'wampcli = izaber_wamp_zerp.wampcli:run_main'
        ],
    },
    install_requires=[
        'pytz',
        'izaber_wamp',
        'docopt',
        'swampyer>=1.20190905',
    ],
    dependency_links=[
    ],
    zip_safe=False
)