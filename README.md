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


## Development

For hacking on the code, this requires the following:

- `git`
- `>=python3.8`
- [pdm](https://pdm-project.org/en/latest/)

### Setup

```bash
git clone git@gitlab.izaber.com:systems/izaber-wamp-zerp.git
cd izaber-wamp-zerp
pdm install
```

And now it's possible to make changes to the code

### Tests via Docker

It's not always desireable to pollute the environment with multiple versions of python so using docker compose is the recommend method for testing.

1. Copy the `./volumes/izaber.yaml.tempate` and update with the appropriate permissions to access Nexus
2. Running the following command will run the tests against pypy3 and from cpython versions 3.8 through 3.13.
    ```bash
    docker compose up
    ```

If you would like to work within the container, have a look at the `docker-compose.yml` and update the `CMD` to `sleep infinity` and it will provide a shell environment (via something like `docker compose exec src bash`) for testing the code within a container.


### Tests via Docker via Dev-Env

It's not always desireable to pollute the environment with multiple versions of python so using the [dev-env](https://gitlab.izaber.com/devops/dev-env) is the recommended way of performing testing.

1. Clone the dev-env the way you normally would
2. Ensure that `python-izaber-wamp-zerp` is enabled in the configuration `izaber.yaml`
3. Running docker compose up should instantiate a container like `XXXX-python-izaber-wamp-zerp-1`

Using the new container will allow testing and verification that the various pythons will function when deployed.

### Packaging

- Ensure that the `pyproject.toml` has the newest version.
- Update the `VERSIONS.md` with the changes made into the library
- Then, assuming access to the pypi account.
    ```bash
    pdm build
    pdm publish
    ```


