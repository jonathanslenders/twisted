"""
A test harness for the twisted.web2 server.
"""

from zope.interface import implements
from twisted.web2 import http, http_headers, iweb, server, responsecode
from twisted.trial import unittest, util, assertions
from twisted.internet import defer

class TestChanRequest:
    implements(iweb.IChanRequest)

    def __init__(self, site, method, prepath, uri,
                 headers=None, version=(1,1)):
        self.site = site
        self.method = method
        self.prepath = prepath
        self.uri = uri
        if headers is None:
            headers = http_headers.Headers()
        self.headers = headers
        self.http_version = version
        # Anything below here we do not pass as arguments
        self.request = server.Request(self,
                                      self.method,
                                      self.uri,
                                      self.http_version,
                                      self.headers,
                                      site=self.site,
                                      prepathuri=self.prepath)
        self.code = None
        self.responseHeaders = None
        self.data = ''
        self.deferredFinish = defer.Deferred()

    def writeIntermediateResponse(code, headers=None):
        pass
    
    def writeHeaders(self, code, headers):
        self.responseHeaders = headers
        self.code = code
        
    def write(self, data):
        self.data += data

    def finish(self):
        result = self.code, self.responseHeaders, self.data
        self.finished = True
        self.deferredFinish.callback(result)

    def abortConnection(self):
        pass

    def registerProducer(self, producer, streaming):
        pass

    def unregisterProducer(self):
        pass

from twisted.web2 import resource
from twisted.web2 import stream
from twisted.web2 import http
from twisted.web2 import responsecode


class TestResource(resource.Resource):
    responseCode = 200
    responseText = 'This is a fake resource.'
    addSlash = True

    def render(self, ctx):
        return http.Response(self.responseCode, stream=self.responseStream())

    def responseStream(self):
        return stream.MemoryStream(self.responseText)

    def child_validChild(self, ctx):
        f = TestResource()
        f.responseCode = 200
        f.responseText = 'This is a valid child resource.'
        return f

    def child_missingChild(self, ctx):
        f = TestResource()
        f.responseCode = 404
        f.responseStream = lambda self: None
        return f



class BaseCase(unittest.TestCase):
    method = 'GET'
    version = (1, 1)
    
    def chanrequest(self, root, uri, headers, method, version, prepath):
        site = server.Site(root)
        return TestChanRequest(site, method, prepath, uri, headers, version)

    def getResponseFor(self, root, uri, headers={},
                       method=None, version=None, prepath=''):
        headers = http_headers.Headers(headers)
        if not headers.hasHeader('content-length'):
            headers.setHeader('content-length', 0)
        if method is None:
            method = self.method
        if version is None:
            version = self.version
        cr = self.chanrequest(root, uri, headers, method, version, prepath)
        cr.request.process()
        return cr.deferredFinish

    def assertResponse(self, request_data, expected_response):
        d = self.getResponseFor(*request_data)
        def _gotResponse((code, headers, data)):
            expected_code, expected_headers, expected_data = expected_response
            self.assertEquals(code, expected_code)
            if expected_data is not None:
                self.assertEquals(data, expected_data)
            for key, value in expected_headers.iteritems():
                self.assertEquals(headers.getHeader(key), value)
        d.addCallback(_gotResponse)
        util.wait(d)



class SampleWebTest(BaseCase):
    root = TestResource()

    def test_root(self):
        self.assertResponse(
            (self.root, 'http://host/'),
            (200, {}, 'This is a fake resource.'))

    def test_validChild(self):
        self.assertResponse(
            (self.root, 'http://host/validChild'),
            (200, {}, 'This is a valid child resource.'))

    def test_invalidChild(self):
        self.assertResponse(
            (self.root, 'http://host/invalidChild'),
            (404, {}, None))

