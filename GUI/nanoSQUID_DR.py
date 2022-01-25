'''
A module defining the DR system specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner import nanoSQUIDSystem
from Equipment import CoreEquipment

class nanoSQUID_DR(nanoSQUIDSystem):
    system_name = 'DR'
    def configureEquipment(self):
        super().configureEquipment()

        '''
        Testing configuration
        '''
        conf = {'pll input':1, 'pll output':1, 'pid z out':1, 'z monitor':1, 'sum board toggle':1}
        self.equip.add_server("HF2LI Lockin", "hf2li_server", controller=CoreEquipment.HF2LI_Controller, config=conf)

        self.equip.add_server("ANC350", "anc350_server", controller=CoreEquipment.ANC350_Controller)

        conf = {'DC Readout':3, 'nSOT Bias':4, 'Noise Readout':2, 'nSOT Gate':1, 'Gate Reference':1, 'Bias Reference':4}
        self.equip.add_server("nSOT DAC", "dac_adc", "DA10_16_08 (COM4)", config=conf)

        conf = {'x out':2, 'y out':3, 'z out':1}
        self.equip.add_server("Scan DAC", "dac_adc", "DA10_16_08 (COM4)", config=conf)

        self.equip.add_server("Sample DAC", "dac_adc", "DA10_16_08 (COM4)")

        conf = {'blink channel':0}
        self.equip.add_server("Blink Device", "dac_adc", "DA10_16_08 (COM4)", config=conf)


#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    try:
        window = nanoSQUID_DR(reactor, computer='kraken', folderName='NanoSQUID DR')
        window.show()
    except:
        from traceback import format_exc
        print("-------------------")
        print("Main loop crashed")
        print(format_exc())
        print("-------------------")
    reactor.runReturn()
    sys.exit(app.exec_())
