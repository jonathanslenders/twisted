#!/usr/bin/python2
# Twisted, the Framework of Your Internet
# Copyright (C) 2001 Matthew W. Lefkowitz
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
from twisted.protocols.ldap import ldapclient
from twisted.protocols import pureber


CONNECTIONS=5
SEARCHES=10

class LDAPSearchAndPrint(ldapclient.LDAPSearch):
    def __init__(self, client, prefix):
        ldapclient.LDAPSearch.__init__(self, client,
                                       baseObject='dc=example, dc=com')
        self.prefix=prefix

    def handle_success(self):
        self.client.search_done(self.prefix)

    def handle_entry(self, objectName, attributes):
        print "%s: %s %s"%(self.prefix, objectName,
                           repr(map(lambda (a,l):
                                    (str(a),
                                     map(lambda i: str(i), l)),
                                    attributes)))

    def handle_fail(self, resultCode, errorMessage):
        print "%s: fail: %d: %s"%(self.prefix, resultCode, errorMessage or "Unknown error")
        self.client.search_done(self.prefix)

class SearchALot(ldapclient.LDAPClient):
    def __init__(self, callback, prefix):
        self.clients = map(lambda x, prefix=prefix: prefix+x, map(str, xrange(0,SEARCHES)))
        self.callback = callback
        self.prefix = prefix
    
    def connectionMade(self):
        self.bind()

    def handle_bind_success(self, matchedDN, serverSaslCreds):
        for k in self.clients:
            LDAPSearchAndPrint(self, k)

    def search_done(self, prefix):
        self.clients.remove(prefix)
        if self.clients==[]:
            self.callback(self)



conns = []

def callback(searchalot):
    conns.remove(searchalot)
    if not conns:
        from twisted.install import reactor
        reactor.stop()

def main():
    from twisted.internet import default
    default.install()
    from twisted.install import reactor
    for x in xrange(0,CONNECTIONS):
        s=SearchALot(callback, str(x)+'.')
        conns.append(s)
        reactor.clientTCP("localhost", 389, s)
    reactor.run()

if __name__ == "__main__":
    main()
