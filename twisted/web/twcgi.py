"""I hold resource classes and helper classes that deal with CGI scripts.
"""

# System Imports
import string
import os
import sys

# Twisted Imports
from twisted.protocols import http
from twisted.internet import process
from twisted.spread import pb

# Sibling Imports
import server
import error
import html
import resource
from server import NOT_DONE_YET

class CGIDirectory(resource.Resource):
    def __init__(self, pathname):
        resource.Resource.__init__(self)
        self.path = pathname

    def getChild(self, path, request):
        fn = os.path.join(self.path, path)

        if os.path.isdir(fn):
            return CGIDirectory(fn)
        if os.path.exists(fn):
            return CGIScript(fn)
        return error.NoResource()

    def render(self):
        return error.NoResource.render()

class CGIScript(resource.Resource):
    """I represent a CGI script.

    My implementation is complex due to the fact that it requires asynchronous
    IPC with an external process with an unpleasant protocol.
    """
    isLeaf = 1
    def __init__(self, filename):
        """Initialize, with the name of a CGI script file.
        """
        self.filename = filename

    def render(self, request):
        """Do various things to conform to the CGI specification.

        I will set up the usual slew of environment variables, then spin off a
        process.
        """
        script_name = "/"+string.join(request.prepath, '/')
        python_path = string.join(sys.path, os.pathsep)
        serverName = string.split(request.getHeader('host') or
                                  request.getHost(), ':')[0]
        env = {"SERVER_SOFTWARE":   server.version,
               "SERVER_NAME":       serverName,
               "GATEWAY_INTERFACE": "CGI/1.1",
               "SERVER_PROTOCOL":   request.clientproto,
               "SERVER_PORT":       str(request.server_port),
               "REQUEST_METHOD":    request.method,
               "SCRIPT_NAME":       script_name, # XXX
               "SCRIPT_FILENAME":   self.filename,
               "REQUEST_URI":       request.uri,
               "PYTHONPATH" :       python_path
               }

        client = request.getClient()
        if client is not None:
            env['REMOTE_HOST'] = client
        ip = request.getClientIP()
        if ip is not None:
            env['REMOTE_ADDR'] = ip
        pp = request.postpath
        if pp:
            env["PATH_INFO"] = "/"+string.join(pp, '/')

        qindex = string.find(request.uri, '?')
        if qindex != -1:
            env['QUERY_STRING'] = request.uri[qindex+1:]
        else:
            env['QUERY_STRING'] = ''

        for title, header in request.received.items():
            envname = string.upper(string.replace(title, '-', '_'))
            if title not in ('content-type', 'content-length'):
                envname = "HTTP_" + envname
            env[envname] = header
        # And they're off!
        self.runProcess(env, request)
        return NOT_DONE_YET

    def runProcess(self, env, request):
        """Callback that actually creates a process.
        """
        CGIProcess(self.filename, [self.filename], env, request)

class FilteredScript(CGIScript):
    """I am a special version of a CGI script, that uses a specific executable.

    This is useful for interfacing with other scripting languages that adhere
    to the CGI standard (cf. PHPScript).  My 'filter' attribute specifies what
    executable to run, and my 'filename' init parameter describes which script
    to pass to the first argument of that script.
    """
    filter = '/usr/bin/cat'
    def runProcess(self, env, request):
        CGIProcess(self.filter, [self.filename], env, request)

class PHPScript(FilteredScript):
    """I am a FilteredScript that uses the default PHP3 command on most systems.
    """
    filter = '/usr/bin/php3'

class CGIProcess(process.Process, pb.Proxied):
    handling_headers = 1
    headers_written = 0
    headertext = ''
    errortext = ''

    # Remotely relay producer interface.

    def proxy_resumeProducing(self, issuer):
        self.resumeProducing()

    def proxy_pauseProducing(self, issuer):
        self.pauseProducing()

    def proxy_stopProducing(self, issuer):
        self.stopProducing()
    
    def __init__(self, script, args, env, request):
        self.request = request
        process.Process.__init__(self, script, args, env)

    def startProcess(self, script, args, env):
        self.request.registerProducer(self, 1)
        process.Process.startProcess(self, script, args, env)
        if self.request.content:
            self.write(self.request.content)
        self.closeStdin()

    def handleError(self, error):
        self.errortext = self.errortext + error

    def handleChunk(self, output):
        """
        Handle a chunk of input
        """
        # First, make sure that the headers from the script are sorted
        # out (we'll want to do some parsing on these later.)
        if self.handling_headers:
            text = self.headertext + output
            headerEnds = []
            for delimiter in '\n\n','\r\n\r\n','\r\r':
                headerend = string.find(text,delimiter)
                if headerend != -1:
                    headerEnds.append((headerend, delimiter))
            if headerEnds:
                headerEnds.sort()
                headerend, delimiter = headerEnds[0]
                self.headertext = text[:headerend]
                # This is a final version of the header text.
                linebreak = delimiter[:len(delimiter)/2]
                headers = string.split(self.headertext, linebreak)
                for header in headers:
                    br = string.find(header,': ')
                    if br == -1:
                        print 'ignoring malformed CGI header: %s' % header
                    else:
                        headerName = string.lower(header[:br])
                        headerText = header[br+2:]
                        if headerName == 'location':
                            self.request.setResponseCode(http.FOUND)
                        if headerName == 'status':
                            try:
                                statusNum = int(headerText)
                            except:
                                print "malformed status header"
                            else:
                                self.request.setResponseCode(statusNum)
                        else:
                            self.request.setHeader(headerName,headerText)
                output = text[headerend+len(delimiter):]
                self.handling_headers = 0
            if self.handling_headers:
                self.headertext = text
        if not self.handling_headers:
            self.request.write(output)

    def connectionLost(self):
        process.Process.connectionLost(self)
        if self.handling_headers:
            self.request.write(
                error.ErrorPage(http.INTERNAL_SERVER_ERROR,
                          "CGI Script Error",
                          "Premature end of script headers; errors follow:<hr>" +
                          html.PRE(self.errortext) + "<hr>").render(self.request))
        self.request.finish()
