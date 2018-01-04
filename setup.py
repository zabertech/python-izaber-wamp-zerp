#!/usr/bin/python

from setuptools import setup

setup(name='izaber_wamp_zerp',
      version='2.04',
      description='Base load point for iZaber WAMP ZERP code',
      url='',
      author='Aki Mimoto',
      author_email='aki+izaber@zaber.com',
      license='MIT',
      packages=['izaber_wamp_zerp'],
      scripts=[],
      install_requires=[
          'pytz',
          'izaber_wamp',
      ],
      dependency_links=[
          'git+https://gitlab.izaber.com/systems/izaber-wamp.git#egg=izaber_wamp-1.11'
      ],
      zip_safe=False)

