'''
A module defining the 3He system specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner import nanoSQUIDSystem


class nanoSQUID_3He(nanoSQUIDSystem):
    system_name = '3He'
#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    window = nanoSQUID_3He(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
