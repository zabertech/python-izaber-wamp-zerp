#!/usr/bin/python

from setuptools import setup

setup(name='izaber_wamp_zerp',
      version='1.00',
      description='Base load point for iZaber WAMP ZERP code',
      url='',
      author='Aki Mimoto',
      author_email='aki+izaber@zaber.com',
      license='MIT',
      packages=['izaber_wamp_zerp'],
      scripts=[],
      install_requires=[
          'izaber_wamp',
          'autobahn_sync',
          'service_identity',
      ],
      zip_safe=False)

