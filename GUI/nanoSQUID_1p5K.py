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
    default_script_dir = "C:\\Users\\Lagrange\\Software\\Scanning Scripts"
    def configureEquipment(self):
        # super().configureEquipment() # Not using superclass configuration because 1.5K
        # system has GPIB equipment on remote server
        self.equip.add_server("LabRAD", None, display_frame=self.genericFrame)
        self.equip.add_server("Data Vault", "data_vault", display_frame=self.genericFrame)
        self.equip.add_server("Serial Server", 'serial_server', display_frame=self.genericFrame)

        self.Approach.approach_type = "Steps" #Step the coarse positioners the old way
        self.GoToSetpoint.autoBlinkOnZero = False # Do not automatically Blink when zeroing

        # Local Servers
        conf = {'pll input':1, 'pll output':1, 'pid z out':1, 'z monitor':1, 'sum board toggle':1}
        self.equip.add_server("HF2LI Lockin", "hf2li_server", controller=CoreEquipment.HF2LI_Controller, config=conf)

        self.equip.add_server("ANC350", "anc350_server", controller=CoreEquipment.ANC350_Controller)

        conf = {'DC Readout':3,
            'nSOT Bias':4,
            'Noise Readout':2,
            'nSOT Gate':1,
            'Gate Reference':1,
            'Bias Reference':4,
            'Bias Res':13.47, # Bias resistance, in units of kOhms
            'Feedback Res':1.003, # Feedback resistance, in units of kOhms
            'Shunt Res':7.8, # Shunt resistance, in units of Ohms
            'Winding Ratio':13.78 # Turns ratio fo the array, for amplification.
            }
        self.equip.add_server("nSOT DAC", "dac_adc", "DA16_16_03 (COM9)", config=conf)

        conf = {'x out':2, 'y out':3, 'z out':1, 'read x':8, 'read y':7 }
        self.equip.add_server("Scan DAC", "dac_adc", "DA20_16_03 (COM6)", config=conf)

        self.equip.add_server("Sample DAC", "dac_adc", "DA20_16_05 (COM14)")

        self.equip.add_server("DC Box", "ad5764_dcbox", "ad5764_dcbox (COM10)")
        
        self.equip.add_server("AC Box", "ad5764_acbox", "ad5764_acbox (COM7)")

        conf = {'blink channel':3} #Output of DC box that corresponds on the frontpanel to Blink
        self.equip.add_server("Blink Device", "ad5764_dcbox", "ad5764_dcbox (COM10)", config=conf)

        # conf = {'max_field':5, "max_ramp":1}
        # self.equip.add_server("Magnet Supply", "ips120_power_supply", "IPS 120", controller=MagnetControllers.IPS120_MagnetController, config=conf)
        conf = {'max_field':5, "max_ramp":1}
        self.equip.add_server("Magnet Z", "ips120_power_supply", 'lagrange GPIB Bus - GPIB0::23::INSTR', controller=MagnetControllers.IPS120_MagnetController, config=conf)
        # conf = {'max_field':6, 'gauss_to_amps':870.827, "max_ramp":0.5, "channel":1}
        # self.equip.add_server("Magnet Z", "cryo_4g_power_supply", "desktop-abpkrkg GPIB Bus - GPIB0::21::INSTR", controller=MagnetControllers.Cryomag4G_Power_Supply, config=conf)

        conf = {
        'Input 1':'D5', 'Input 1 Label':'Sample',
        'Input 2':'D4', 'Input 2 Label':'1.5K Pot',
        'Input 3':'B', 'Input 3 Label':'Magnet'
        }
        self.equip.add_server("LS 350", "lakeshore_350", config=conf)
        
        self.equip.add_server("GND Switchbox", "ground_switch_actuator", 'lagrange_serial_server - COM13')
        self.equip.add_server("SR860", "sr860", 'lagrange GPIB Bus - GPIB0::4::INSTR')
        # # Remote Servers
        # self.equip.configure_remote_host('4KMonitor', 'minint_o9n40pb')
        #
        # conf = {'max_field':5}
        # self.equip.add_remote_server("Magnet Supply", "ips120_power_supply", "IPS 120", controller=MagnetControllers.IPS120_MagnetController, config=conf)
        #
        # self.equip.add_remote_server("LS 350", "lakeshore_350")
        #
        # # self.equip.add_remote_server("LM 510", "lm_510")


#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    try:
        window = nanoSQUID_1p5K(reactor, computer='lagrange', folderName='NanoSQUID 1p5K')
        window.show()
    except:
        from traceback import format_exc
        print("-------------------")
        print("Main loop crashed")
        print(format_exc())
        print("-------------------")
    reactor.runReturn()
    sys.exit(app.exec_())
