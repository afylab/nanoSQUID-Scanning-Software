'''
A module defining the 1.5K system specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner import nanoSQUIDSystem
from Equipment import MagnetControllers


class nanoSQUID_1p5K(nanoSQUIDSystem):
    system_name = '1p5K'
    def configureEquipment(self):
        super().configureEquipment()

        dict = {'max_field':5}
        self.equip.add_server("Magnet", "ips120_power_supply", "IPS 120", controller=MagnetControllers.IPS120_MagnetController, config=dict)

#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    window = nanoSQUID_1p5K(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
