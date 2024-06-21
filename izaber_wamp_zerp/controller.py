from izaber.log import log
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

    def hello(self, file_, **kwargs):
        """Introduce yourself to Zerp so a log entry can be made to aid
        in troubleshooting. Must be called after initialize.
        :param file_:
            The filename of this script. (__file__)
        :Keyword Arguments:
            All keyword arguments are recorded in the Zerp log entry as
            "*key*: *value*". I suggest supplying at least the following
            arguments.
            * *author* --
                The name of the author of this script.
            * *version* --
                The version number of this script.
            * *description* --
                A description of the purpose of this script.
        :example:

        >>> zerp.hello(__file__, author="My Name", version="1.0", description="Just an example")
        """
        from socket import gethostname
        from . import __version__
        try:
            hostname = gethostname()
        except Exception as err:
            hostname = None
            log.error("Unable to determine hostname {}".format(err))
        try:

            # This is a deprecated method of getting the connection IP from
            # the wamp connection. With version 2.x, as the internal structure
            # has moved from being websocket-only to an abstracted transport,
            # connecting directly to a websocket instance is no longer feasible.
            try:
                ipaddress = self.wamp.wamp.ws.sock.getsockname()[0]
            except AttributeError:
                # Pinched from:
                # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/28950776#28950776
                # FIXME: This will only support IPv4 addresses, at some point
                # we'd want to allow IPv6 or even other types of network/mesh
                # identities
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.connect(('10.255.255.255', 1))
                    ipaddress = sock.getsockname()[0]
                finally:
                    sock.close()
        except Exception as err:
            ipaddress = None
            log.error("Unable to determine ipaddress {}".format(err))
        try:
            authid = self.wamp.wamp.authid
        except Exception as err:
            authid = None
            log.error("Unable to determine authid {}".format(err))
        description = "\"izaber.wamp.zerp {version} ({authid}) {description}\"".format(
                version=__version__,
                authid=authid,
                description=kwargs.get("description", ""))
        kwargs.update({
            "hostname": hostname,
            "ipaddress": ipaddress,
            "description": description
        })
        return self.get("res.users").hello(file_, **kwargs)

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

