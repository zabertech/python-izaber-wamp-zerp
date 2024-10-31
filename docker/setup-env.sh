#!/bin/bash

# This will ensure that poetry will execute
export PATH="/home/zaber/.local/bin:$PATH"
cd /src

# We need to have a izaber.yaml so we'll put it into ~/izaber.yaml
ln -s /volumes/izaber.yaml /home/zaber/izaber.yaml

echo "Installing PDM"

curl -sSL https://pdm-project.org/install-pdm.py | python3 -

echo "installing development script code"

pdm install -d

