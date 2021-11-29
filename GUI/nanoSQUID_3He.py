'''
A module defining the 3He system specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner import nanoSQUIDSystem
from Equipment import CoreEquipment
from Equipment import MagnetControllers

class nanoSQUID_3He(nanoSQUIDSystem):
    system_name = '3He'

    def configureEquipment(self):
        super().configureEquipment()

        conf = {'pll input':1, 'pll output':1, 'pid z out':1, 'z monitor':1, 'sum board toggle':1}
        self.equip.add_server("HF2LI Lockin", "hf2li_server", controller=CoreEquipment.HF2LI_Controller, config=conf)

        self.equip.add_server("ANC350", "anc350_server", controller=CoreEquipment.ANC350_Controller)

        conf = {'DC Readout':3, 'nSOT Bias':4, 'Noise Readout':8, 'nSOT Gate':1, 'Gate Reference':1, 'Bias Reference':4}
        self.equip.add_server("nSOT DAC", "dac_adc", "DA20_16_04 (COM6)", config=conf)

        conf = {'x out':2, 'y out':3, 'z out':1}
        self.equip.add_server("Scan DAC", "dac_adc", "DA20_16_05 (COM3)", config=conf)

        # TEMPORARILY REPLACING SAMPLE DAC AND SCAN DAC DUE TO CONNECITON ISSUE
        #self.equip.add_server("Sample DAC", "dac_adc", "DA20_16_06 (COM7)")
        self.equip.add_server("Sample DAC", "dac_adc", "DA20_16_05 (COM3)")

        conf = {'blink channel':0}
        self.equip.add_server("Blink Device", "dac_adc", "DA20_16_05 (COM3)", config=conf)

        conf = {'Input 1':'B', 'Input 1 Label':'1K POT',
            'Input 2':'D', 'Input 2 Label':'Sample',
            'Input 3':'C', 'Input 3 Label':'He3 POT'
            }
        self.equip.add_server("LS 336", "lakeshore_336", config=conf)

        conf = {'max_field':6, 'gauss_to_amps':870.827, "max_ramp":0.5, "channel":1}
        self.equip.add_server("Magnet Z", "cryo_4g_power_supply", "desktop-abpkrkg GPIB Bus - GPIB0::21::INSTR", controller=MagnetControllers.Cryomag4G_Power_Supply, config=conf)

        conf = {'max_field':1, 'gauss_to_amps':160.539, "max_ramp":0.15, "channel":1}
        self.equip.add_server("Magnet X", "cryo_4g_power_supply", "desktop-abpkrkg GPIB Bus - GPIB0::22::INSTR", controller=MagnetControllers.Cryomag4G_Power_Supply, config=conf)

        conf = {'max_field':1, 'gauss_to_amps':159.591, "max_ramp":0.15, "channel":2}
        self.equip.add_server("Magnet Y", "cryo_4g_power_supply", "desktop-abpkrkg GPIB Bus - GPIB0::22::INSTR", controller=MagnetControllers.Cryomag4G_Power_Supply, config=conf)

        self.equip.add_server("LM 510", "lm_510")
#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    try:
        window = nanoSQUID_3He(reactor, computer='desktop_abpkrkg', folderName='NanoSQUID 300 mK')
        window.show()
    except:
        from traceback import format_exc
        print("-------------------")
        print("Main loop crashed")
        print(format_exc())
        print("-------------------")
    reactor.runReturn()
    sys.exit(app.exec_())
