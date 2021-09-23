'''
A module defining the mobile racks dipper/vector magnet specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner import nanoSQUIDSystem


class nanoSQUID_mobile(nanoSQUIDSystem):
    system_name = 'mobile'
#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    try:
        window = nanoSQUID_mobile(reactor, folderName='NanoSQUID Mobile')
        window.show()
    except:
        from traceback import format_exc
        print("-------------------")
        print("Main loop crashed")
        print(format_exc())
        print("-------------------")
    reactor.runReturn()
    sys.exit(app.exec_())
