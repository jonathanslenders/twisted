
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

from wxPython.wx import *

from twisted.internet import main, wxinternet

class HelloWorld:

    def timeout(self):
        return 1.0
    
    def runUntilCurrent(self):
        print "hello, world"

main.addDelayed(HelloWorld())


ID_EXIT  = 101

class MyFrame(wxFrame):
    def __init__(self, parent, ID, title):
        wxFrame.__init__(self, parent, ID, title, wxDefaultPosition, wxSize(300, 200))
        menu = wxMenu()
        menu.Append(ID_EXIT, "E&xit", "Terminate the program")
        menuBar = wxMenuBar()
        menuBar.Append(menu, "&File");
        self.SetMenuBar(menuBar)
        EVT_MENU(self, ID_EXIT,  self.DoExit)

    def DoExit(self, event):
        self.Close(true)
        main.shutDown()


class MyApp(wxinternet.twixApp):

    def OnInit(self):
        frame = MyFrame(NULL, -1, "Hello, world")
        frame.Show(true)
        self.SetTopWindow(frame)
        return true


def demo():
    app = MyApp(0)
    wxinternet.install(app)
    main.run()


if __name__ == '__main__':
    demo()
