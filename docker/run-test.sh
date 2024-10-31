#!/bin/bash

# Go into the project's source dir
cd /src

# Wait till our nexus server is up and running
# before attempting any tests
pdm run python ./docker/wait-for-nexus.py

# Then run the nox test scripts
nox --reuse-existing-virtualenvs $@

