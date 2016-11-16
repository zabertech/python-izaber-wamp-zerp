from pytz import timezone
import pytz.reference

from izaber import config, app_config
from izaber.startup import request_initialize, initializer
from izaber.wamp import wamp

__version__ = '2.01'

CONFIG_BASE = """
default:
    wamp:
        zerp:
            database: 'databasename'
"""

METHOD_SHORTHANDS = {
    'schema':           'object.execute.fields_get',
    'exec_workflow':    'object.exec_workflow',
    'wizard_create':    'wizard.create',
    'report':           'report.report',
    'report_get':       'report.report_get',
    'reports_fetch':    'report.report_get',
    'search':           'object.execute.search',
    'search_fetch':     'object.execute.zerp_search_read',
    'search_fetch_one': 'object.execute.zerp_search_read_one',
    'fetch':            'object.execute.read',
    'fetch_one':        'object.execute.read',
    'write':            'object.execute.write',
    'create':           'object.execute.create',
    'unlink':           'object.execute.unlink',
}


class ZERPModel(object):
    def __init__(self,zerp,model,schema):
        self.zerp_ = zerp
        self.model_ = model
        self.schema_ = schema

    def __getattr__(self,k):
        if k in METHOD_SHORTHANDS:
            return lambda *a,**kw: self.zerp_.call(
                u':'.join([self.model_,METHOD_SHORTHANDS[k]]),
                *a, **kw
            )


        else:
            return lambda *a,**kw: self.zerp_.call(
                u':'.join([self.model_,'object.execute.'+k]),
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
        return self.call(model+':object.execute.fields_get')

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


