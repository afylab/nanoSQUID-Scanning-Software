'''
A module defining the 1.5K system specifically
'''
import sys
from PyQt5 import QtGui, QtWidgets
from nSOTScanner import nanoSQUIDSystem


class nanoSQUID1p5K(nanoSQUIDSystem):
    pass
#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    window = nanoSQUID1p5K(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
