'''
A module defining the 3He system specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner import nanoSQUIDSystem
from Equipment import CoreEquipment

class nanoSQUID_3He(nanoSQUIDSystem):
    system_name = '3He'

    def configureEquipment(self):
        super().configureEquipment()

        dict = {'pll input':1, 'pll output':1, 'pid z out':1, 'z monitor':1, 'sum board toggle':1}
        self.equip.add_server("HF2LI Lockin", "hf2li_server", controller=CoreEquipment.HF2LI_Controller, config=dict)

        # self.equip.add_server("ANC350", "anc350_server", controller=CoreEquipment.ANC350_Controller)

        dict = {'DC Readout':3, 'nSOT Bias':4, 'Noise Readout':2, 'nSOT Gate':1, 'Gate Reference':1, 'Bias Reference':4}
        self.equip.add_server("nSOT DAC", "dac_adc", "DA20_16_04 (COM6)", config=dict)

        dict = {'x out':2, 'y out':3, 'z out':1}
        self.equip.add_server("Scan DAC", "dac_adc", "DA20_16_05 (COM3)", config=dict)

        self.equip.add_server("Sample DAC", "dac_adc", "DA20_16_06 (COM7)")

        dict = {'blink channel':0}
        self.equip.add_server("Blink Device", "dac_adc", "DA20_16_05 (COM3)", config=dict)

#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    window = nanoSQUID_3He(reactor, computer='desktop_abpkrkg')
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
