import time
import base64

from pytz import timezone
import pytz.reference

from izaber.wamp.zerp.controller import ZERP

from izaber import config, app_config
from izaber.startup import request_initialize, initializer
from izaber.wamp import wamp

from .models.zerp import TypedZERP

__version__ = '2.7.20200424'

CONFIG_BASE = """
default:
    wamp:
        zerp:
            database: 'databasename'
"""

zerp: TypedZERP = ZERP()

@initializer('wamp_zerp')
def load_config(**kwargs):
    request_initialize('wamp',**kwargs)
    config.config_amend_(CONFIG_BASE)
    zerp.configure(wamp,config.wamp.zerp.database)


