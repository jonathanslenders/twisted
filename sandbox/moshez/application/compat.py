# Twisted, the Framework of Your Internet
# Copyright (C) 2001-2003 Matthew W. Lefkowitz
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
from twisted.python import components, log
from twisted.application import servers, clients, persist, service

class IOldApplication(components.Interface):

    def listenWith(self, portType, *args, **kw):
        pass

    def unlistenWith(self, portType, *args, **kw):
        pass

    def listenTCP(self, port, factory, backlog=5, interface=''):
        pass

    def unlistenTCP(self, port, interface=''):
        pass

    def listenUNIX(self, filename, factory, backlog=5, mode=0666):
        pass

    def unlistenUNIX(self, filename):
        pass

    def listenUDP(self, port, proto, interface='', maxPacketSize=8192):
        pass

    def unlistenUDP(self, port, interface=''):
        pass

    def listenSSL(self, port, factory, ctxFactory, backlog=5, interface=''):
        pass

    def unlistenSSL(self, port, interface=''):
        pass

    def connectWith(self, connectorType, *args, **kw):
        pass

    def connectUDP(self, remotehost, remoteport, protocol, localport=0,
                  interface='', maxPacketSize=8192):
        pass

    def connectTCP(self, host, port, factory, timeout=30, bindAddress=None):
        pass

    def connectUNIX(self, address, factory, timeout=30):
        pass

    def bindPorts(self):
        pass

    def save(self, tag=None, filename=None, passphrase=None):
        pass

    def logPrefix(self):
        pass

    def run(self, save=1, installSignalHandlers=1):
        pass

class ServiceNetwork:

    __implements__ = IOldApplication,

    def __init__(self, app):
        self.app = app

    def listenWith(self, portType, *args, **kw):
        servers.GenericServer(portType, *args, **kw).setServiceParent(self.app)

    def unlistenWith(self, portType, *args, **kw):
        raise NotImplementedError()

    def listenTCP(self, port, factory, backlog=5, interface=''):
        s = servers.TCPServer(port, factory, backlog, interface)
        s.setServiceParent(self.app)

    def unlistenTCP(self, port, interface=''):
        raise NotImplementedError()

    def listenUNIX(self, filename, factory, backlog=5, mode=0666):
        s = servers.UNIXServer(filename, factory, backlog, mode)
        s.setServiceParent(self.app)

    def unlistenUNIX(self, filename):
        raise NotImplementedError()

    def listenUDP(self, port, proto, interface='', maxPacketSize=8192):
        s = servers.UDPServer(port, proto, interface, maxPacketSize)
        s.setServiceParent(self.app)

    def unlistenUDP(self, port, interface=''):
        raise NotImplementedError()

    def listenSSL(self, port, factory, ctxFactory, backlog=5, interface=''):
        s = servers.SSLServer(port, factory, ctxFactory, backlog, interface)
        s.setServiceParent(self.app)

    def unlistenSSL(self, port, interface=''):
        raise NotImplementedError()

    def connectWith(self, connectorType, *args, **kw):
        s = clients.GenericClient(connectorType,  *args, **kw)
        s.setServiceParent(self.app)

    def unlistenSSL(self, port, interface=''):
        raise NotImplementedError()

    def connectUDP(self, remotehost, remoteport, protocol, localport=0,
                  interface='', maxPacketSize=8192):
        s = clients.GenericClient(connectorType,  *args, **kw)
        s.setServiceParent(self.app)

    def connectTCP(self, host, port, factory, timeout=30, bindAddress=None):
        s = clients.TCPClient(host, port, factory, timeout, bindAddress)
        s.setServiceParent(self.app)

    def connectUNIX(self, address, factory, timeout=30):
        s = clients.UNIXClient(address, factory, timeout)
        s.setServiceParent(self.app)

    def bindPorts(self):
        self.app.privilegedStartService()

    def save(self, tag=None, filename=None, passphrase=None):
        persist.IPersistable(self.app).save(tag, filename, passphrase)

    def logPrefix(self):
        return '*%s*' % self.app.name

    def run(self, save=1, installSignalHandlers=1):
        self.app.startService()
        from twisted.internet import reactor
        reactor.addSystemEventTrigger('before', 'shutdown',
                                      self.app.stopService)
        if save:
            self.app.scheduleSave()
        log.callWithLogger(self, reactor.run,
                           installSignalHandlers=installSignalHandlers)

    def setEUID(self):
        try:
            os.setegid(self.app.gid)
            os.seteuid(self.app.uid)
        except (AttributeError, OSError):
            pass
        else:
            log.msg('set euid/egid %s/%s' % (self.app.uid, self.app.gid))

    def setUID(self):
        try:
            os.setgid(self.app.gid)
            os.setuid(self.app.uid)
        except (AttributeError, OSError):
            pass
        else:
            log.msg('set uid/gid %s/%s' % (self.app.uid, self.app.gid))

    def __getattr__(self, name):
        return getattr(self.app, name)


components.registerAdapter(ServiceNetwork,
                           service.IServiceCollection, IOldApplication)
