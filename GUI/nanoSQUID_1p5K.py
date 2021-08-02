'''
A module defining the 1.5K system specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner import nanoSQUIDSystem
from Equipment import CoreEquipment
from Equipment import MagnetControllers


class nanoSQUID_1p5K(nanoSQUIDSystem):
    system_name = '1p5K'
    def configureEquipment(self):
        # super().configureEquipment() # Not using superclass configuration because 1.5K
        # system has GPIB equipment on remote server
        self.equip.add_server("LabRAD", None, display_frame=self.genericFrame)
        self.equip.add_server("Data Vault", "data_vault", display_frame=self.genericFrame)
        self.equip.add_server("Serial Server", 'serial_server', display_frame=self.genericFrame)

        # Local Servers
        dict = {'pll input':1, 'pll output':1, 'pid z out':1, 'z monitor':1, 'sum board toggle':1}
        self.equip.add_server("HF2LI Lockin", "hf2li_server", controller=CoreEquipment.HF2LI_Controller, config=dict)

        self.equip.add_server("ANC350", "anc350_server", controller=CoreEquipment.ANC350_Controller)

        dict = {'DC Readout':3, 'nSOT Bias':4, 'Noise Readout':2, 'nSOT Gate':1, 'Gate Reference':1, 'Bias Reference':4}
        self.equip.add_server("nSOT DAC", "dac_adc", "DA16_16_03 (COM6)", config=dict)

        dict = {'x out':2, 'y out':3, 'z out':1}
        self.equip.add_server("Scan DAC", "dac_adc", "DA20_16_03 (COM11)", config=dict)

        self.equip.add_server("Sample DAC", "dac_adc", "DA16_16_06 (COM3)")

        self.equip.add_server("DC Box", "ad5764_dcbox", "ad5764_dcbox (COM5)")

        dict = {'blink channel':0}
        self.equip.add_server("Blink Device", "ad5764_dcbox", "ad5764_dcbox (COM5)", config=dict)

        # Remote Servers
        self.equip.configure_remote_host('4KMonitor', 'minint_o9n40pb')

        dict = {'max_field':5}
        self.equip.add_remote_server("Magnet Supply", "ips120_power_supply", "IPS 120", controller=MagnetControllers.IPS120_MagnetController, config=dict)

        self.equip.add_remote_server("LS 350", "lakeshore_350")

        # self.equip.add_remote_server("LM 510", "lm_510")
#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    window = nanoSQUID_1p5K(reactor, computer='cthulu', folderName='NanoSQUID 1p5K')
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
