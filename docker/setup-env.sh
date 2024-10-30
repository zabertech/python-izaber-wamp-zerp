#!/bin/bash

ROOT_PATH=$(dirname $(readlink -f $0))

# This will ensure that poetry will execute
export PATH="/home/zaber/.local/bin:$PATH"
cd /src

curl -sSL https://pdm-project.org/install-pdm.py | python3 -

pdm install -d

