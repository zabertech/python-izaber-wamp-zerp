import os
import pathlib
import subprocess
import socket
import time
import json
import sys
import logging
import re

# Setup for proper pathing for libs and data
LIB_PATH = pathlib.Path(__file__).resolve().parent
TEST_PATH = LIB_PATH.parent
SRC_PATH = TEST_PATH.parent
DATA_PATH = pathlib.Path('/data')
SNAPSHOT_FPATH = DATA_PATH / "snapshot.json"

NEXUS_URL = "ws://nexus:8282/ws"
NEXUS_REALM = "izaber"

IZABER_TEMPLATE = """
default:
  wamp:
    connection:
      url: 'ws://nexus:8282/ws'
      username: '{username}'
      password: '{password}'

"""

sys.path.insert(1, f"{SRC_PATH}/lib")

def load_nexus_db():
    """ The nexus test db should have a dump of all the roles
        users, and such at tests/data/snapshot.json
    """
    snapshot_fh = SNAPSHOT_FPATH.open('r')
    snapshot_data = json.load(snapshot_fh)
    return snapshot_data

