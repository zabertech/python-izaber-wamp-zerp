#!/bin/bash

# Link our izaber.yaml file to ~/izaber.yaml for defaults
ln -s /volumes/izaber.yaml /home/zaber/izaber.yaml 

export PATH="/home/zaber/.local/bin:$PATH"

echo "Installing PDM"
curl -sSL https://pdm-project.org/install-pdm.py | python3 -

echo "installing development script code"
cd /src

pdm install -d

