import time
import base64

from pytz import timezone
import pytz.reference

from controller import ZERP

from izaber import config, app_config
from izaber.startup import request_initialize, initializer
from izaber.wamp import wamp

__version__ = '2.02'

CONFIG_BASE = """
default:
    wamp:
        zerp:
            database: 'databasename'
"""

zerp = ZERP()

@initializer('wamp_zerp')
def load_config(**kwargs):
    request_initialize('wamp',**kwargs)
    config.config_amend_(CONFIG_BASE)
    zerp.configure(wamp,config.wamp.zerp.database)


