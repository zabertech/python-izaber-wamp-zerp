from pytz import timezone
import pytz.reference

from izaber import config, app_config
from izaber.startup import request_initialize, initializer
from izaber.wamp import wamp

__version__ = '2.00'

CONFIG_BASE = """
default:
    wamp:
        zerp:
            database: 'databasename'
"""

class ZERPModel(object):
    def __init__(self,zerp,model,schema):
        self.zerp_ = zerp
        self.model_ = model
        self.schema_ = schema

    def __getattr__(self,k):
        return lambda *a,**kw: self.zerp_.call(
            u':'.join([self.model_,'object.execute',k]),
            *a, **kw
        )

class ZERP(object):
    def __init__(self,*args,**kwargs):
        self.configure(*args,**kwargs)
        self.schema_cache = {}

    def configure(self,
                    wamp=None,
                    database=None):
        if not wamp is None:
            self.wamp = wamp
        if not database is None:
            self.database = unicode(database)

    def schema(self,model):
        if model in self.schema_cache:
            return self.schema_cache[model]
        schema = self.call(
                    u':'.join([model,'model','schema'])
                  )
        self.schema_cache[model] = schema

        return schema

    def get_model(self,model):
        return ZERPModel(self,model,self.schema(model))

    # Alias
    get = get_model

    def call(self,uri,*args,**kwargs):
        uri = u':'.join(['zerp',self.database,uri])
        return self.wamp.call(uri,*args,**kwargs)

zerp = ZERP()

@initializer('wamp_zerp')
def load_config(**kwargs):
    request_initialize('wamp',**kwargs)
    config.config_amend_(CONFIG_BASE)
    zerp.configure(wamp,config.wamp.zerp.database)


