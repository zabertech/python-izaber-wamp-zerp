from izaber.compat import *

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
    'read':             'object.execute.read',
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

    def reports_fetch(self, ids, context=None ):
        """ Request a report be generated then fetch it!
            The return value should be the decoded data file
        """
        if context is None: context = {}

        generated_report_id = self.report(ids,context)

        # The report must be created.
        # Make sure we can generate the report
        reports = []
        for i in range(50):
            time.sleep(0.1)

            report = self.zerp_.report_get(generated_report_id)

            if report['state']:
                # Normalize the result (take the result string out of
                # base64 encoding)
                report['result'] = base64.decodestring(report['result'])

                # Add it to the list of reports found.
                reports.append(report)
                break

        # Couldn't get it!
        else:
            raise Exception("Couldn't get report!")

        return reports

    def report_fetch_one(self, report_id, context=None ):
        reports = self.reports_fetch([report_id],context)
        return reports[0]


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

    def report_get(self,report_id):
        return self.call('report.report_get',report_id)
