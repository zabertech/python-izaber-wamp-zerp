# izaber.wamp.zerp

Base module that brings together most of the requirements to allow ZERP WAMP connectivity within Zaber

## Installation

Install the module for your local version of python using the command below. If you have both python 2 and 3 installed then you might need to replace the `python` keyword with `python2`, `py -2`, `python3`, or `py -3` based on the python version you want to use the module for.

```
python -m pip install izaber-wamp-zerp
```

This installs the module that can be used in your custom ZERP based python scripts and also provides a command line tool called `wampcli` to make simple WAMP calls from the command line.

## Configuration

The module reads all of its settings from a globally defined configuration file located in the root directory of the user's computer. This configuration file is **required for proper operation** of the module.

- Create a file named `~/izaber.yaml` (i.e. in the home directory).
  - Linux: ``/home/yourusername/izaber.yaml``
  - MacOS: ``/Users/yourusername/izaber.yaml``
  - Windows: ``C:\Users\yourusername\izaber.yaml``

- Paste the following into the file to get started and connect to the `sandbox` database

  ```yaml
  default:
      wamp:
          connection:
              url: 'wss://nexus.izaber.com/ws'
              username: 'username'
              password: 'password_for_user'
              timeout: 10
          zerp:
              database: 'sandbox'
  ```
- Replace the username and password with your zerp user and a dashboard API key (or your ZERP password but that is not recommended).
- More detailed information about defining the configuration files can be found [here](https://github.com/zabertech/python-izaber/blob/master/docs/tutorial.rst)

## Usage

- [Using izaber-wamp-zerp in python scripts](docs/usage_in_scripts.md)
- [Running simple commands on the command line using WAMP CLI](docs/wampcli_usage.md)
- [Generating ZERP types locally on your system](docs/type_generation.md)