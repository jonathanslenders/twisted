import os
import sys
import struct
import socket

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from twisted.internet import reactor
from twisted.internet import defer
from twisted.spread import pb
from twisted.python import log
from twisted.cred import credentials
from twisted.internet import protocol
from twisted.internet import unix
from twisted.application import internet

sys.path.append("../../pahan/sendmsg")
from sendmsg import recvmsg

class Client(unix.Client):
    def doRead(self):
        if not self.connected:
            return
        try:
            msg, flags, ancillary = recvmsg(self.fileno())
        except:
            log.msg('recvmsg():')
            log.err()
        else:
            buf = ancillary[0][2]
            fds = []
            while buf:
                fd, buf = buf[:4], buf[4:]
                fds.append(struct.unpack("i", fd)[0])
            try:
                self.protocol.fileDescriptorsReceived(fds)
            except:
                log.msg('protocol.fileDescriptorsReceived')
                log.err()
        return unix.Client.doRead(self)

class Connector(unix.Connector):
    def _makeTransport(self):
        return Client(self.address, self, self.reactor)

class UNIXClient(internet._AbstractClient):
    def _getConnection(self):
        from twisted.internet import reactor
        return reactor.connectWith(Connector, *self.args, **self.kwargs)

class _FileDescriptorUnpickler:
    def __init__(self, fdmap):
        self.fdmap = fdmap
        self.fdmemo = {}

    def persistent_load(self, id):
        if id == 'reactor':
            from twisted.internet import reactor
            return reactor
        id, rest = id.split(":", 1)
        id = int(id)
        if id in self.fdmemo:
            return self.fdmemo[id]
        rest = rest.split(":")
        type = rest.pop(0)
        method = getattr(self, "type_" + type)
        result = self.fdmemo[id] = method(id, *rest)
        return result

    def type_file(self, id, mode):
        return os.fdopen(self.fdmap[id], mode)

    def type_socket(self, id):
        return socket.fromfd(self.fdmap[id])

def FileDescriptorUnpickler(s, fdmap):
    ph = _FileDescriptorUnpickler(fdmap)
    p = pickle.Unpickler(s)
    p.persistent_load = ph.persistent_load
    return p

class FileDescriptorReceivingProtocol(protocol.Protocol):
    """
    Must be used with L{Port} as the transport.
    """
    
    def __init__(self, id, d):
        self.id = id
        self.d = d

    def connectionMade(self):
        self.transport.write("%s\r\n" % (self.id,))

    def dataReceived(self, data):
        print 'Got some random data', repr(data)

    def fileDescriptorsReceived(self, fds):
        self.d.callback(fds)
        self.transport.loseConnection()

class FileDescriptorRequestFactory(protocol.ClientFactory):
    protocol = FileDescriptorReceivingProtocol

    def __init__(self, id, d):
        self.id = id
        self.gotFDs = d

    def buildProtocol(self, addr):
        p = self.protocol(self.id, self.gotFDs)
        return p

class UserStateReceiver(pb.Referenceable):
    def stateReceived(self, state):
        print state

    def unproxyFileDescriptors(self, fds, state):
        s = StringIO.StringIO(state)
        p = FileDescriptorUnpickler(s, fds)
        self.stateReceived(p.load())
        return True

    def remote_takeResponsibility(self, id, state, path):
        d = defer.Deferred()
        f = FileDescriptorRequestFactory(id, d)
        client = UNIXClient(path, f, 60).startService()
        d.addCallback(self.unproxyFileDescriptors, state)
        return d

def main():
    log.startLogging(sys.stdout)
    f = pb.PBClientFactory()
    reactor.connectTCP("localhost", 10301, f)
    f.login(credentials.UsernamePassword("username", "password"), UserStateReceiver())
    reactor.run()

if __name__ == '__main__':
    main()
