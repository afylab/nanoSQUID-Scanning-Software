'''
A module defining the 1.5K system specifically
'''
import sys
from PyQt4 import QtGui
from nSOTScanner import nanoSQUIDSystem


class nanoSQUID1p5K(nanoSQUIDSystem):
    pass
#

""" The following runs the 1.5K GUI"""
if __name__=="__main__":
    import qt4reactor
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install()
    from twisted.internet import reactor
    window = nanoSQUIDSystem(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
