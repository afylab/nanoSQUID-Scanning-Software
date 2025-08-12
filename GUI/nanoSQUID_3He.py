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
    default_script_dir = "C:\\Users\\Leviathan\\Software\\Scanning Scripts"

    def configureEquipment(self):
        super().configureEquipment()
        
        self.Approach.approach_type = "Advance"
        # self.ApproachMonitor.save_logs = True # Save the full output of Approach monitor for debugging
        self.GoToSetpoint.autoBlinkOnZero = True

        conf = {'pll input':1, 'pll output':1, 'pid z out':1, 'z monitor':1, 'sum board toggle':1}
        self.equip.add_server("HF2LI Lockin", "hf2li_server", controller=CoreEquipment.HF2LI_Controller, config=conf)

        self.equip.add_server("ANC350", "anc350_server", controller=CoreEquipment.ANC350_Controller)

        conf = {'DC Readout':7,#3,
            'nSOT Bias':4, 
            'Noise Readout':2, 
            'nSOT Gate':1, 
            'Gate Reference':1, 
            'Bias Reference':4,
            'Bias Res':15.5, # Bias resistance, in units of kOhms. Includes series resistance of filters 2x 5.1 kOhms
            'Feedback Res':1.11, # Feedback resistance, in units of kOhms
            'Shunt Res':2.9, # Shunt resistance, in units of Ohms
            'Winding Ratio':14 # Turns ratio fo the array, for amplification.
            }
        self.equip.add_server("nSOT DAC", "dac_adc", "DA20_16_05 (COM3)", config=conf)

        conf = {'x out':2, 'y out':3, 'z out':1}
        # self.equip.add_server("Scan DAC", "dac_adc", "DA20_16_06 (COM6)", config=conf)
        self.equip.add_server("Scan DAC", "dac_adc_scan", "DA20_16_06 (COM6)", config=conf)

        self.equip.add_server("Sample DAC", "dac_adc", "DA20_16_04 (COM7)")
        #self.equip.add_server("Sample DAC", "dac_adc", "DA20_16_06 (COM6)") # Swapped with scan

        conf = {'blink channel':3}
        self.equip.add_server("Blink Device", "dac_adc", "DA20_16_05 (COM3)", config=conf)

        conf = {
            'Input 1':'A', 'Input 1 Label':'Charcoal',
            'Input 2':'B', 'Input 2 Label':'1K POT',
            'Input 3':'C', 'Input 3 Label':'He3 POT',
            'Input 4':'D', 'Input 4 Label':'Sample',
            }
        self.equip.add_server("LS 336", "lakeshore_336", config=conf)

        # conf = {'max_field':6, 'gauss_to_amps':870.827, "max_ramp":0.5, "channel":1}
        # self.equip.add_server("Magnet Z", "cryo_4g_power_supply", "desktop-abpkrkg GPIB Bus - GPIB0::21::INSTR", controller=MagnetControllers.Cryomag4G_Power_Supply, config=conf)
        conf = {'max_field':6, 'gauss_to_amps':870.827, "max_ramp":0.5} # MAX OF 5T for 1 T/min ramp rate, from 5-6T need 0.5 T/min
        self.equip.add_server("Magnet Z", "ips120_power_supply", "phys-leviathan GPIB Bus - GPIB0::25::INSTR", controller=MagnetControllers.IPS120_MagnetController_ALT, config=conf)

        conf = {'max_field':1, 'gauss_to_amps':160.539, "max_ramp":0.15, "channel":1}
        self.equip.add_server("Magnet X", "cryo_4g_power_supply", "phys-leviathan GPIB Bus - GPIB0::22::INSTR", controller=MagnetControllers.Cryomag4G_Power_Supply, config=conf)
        
        conf = {'max_field':1, 'gauss_to_amps':159.591, "max_ramp":0.15, "channel":2}
        self.equip.add_server("Magnet Y", "cryo_4g_power_supply", "phys-leviathan GPIB Bus - GPIB0::22::INSTR", controller=MagnetControllers.Cryomag4G_Power_Supply, config=conf)
        
        # Other Servers
        self.equip.add_server("SR 830", "sr830", "phys-leviathan GPIB Bus - GPIB0::15::INSTR")
        self.equip.add_server("SR 860", "sr860", "phys-leviathan GPIB Bus - GPIB0::4::INSTR")
        self.equip.add_server("AC Box", "ad5764_acbox")
        self.equip.add_server("GND Switchbox", "ground_switch_actuator")
        self.equip.add_server("Sorb Valve", "he_valve")
        #self.equip.add_server("LM 510", "lm_510")
#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    try:
        window = nanoSQUID_3He(reactor, computer='phys_leviathan', folderName='NanoSQUID 300 mK')
        window.show()
    except:
        from traceback import format_exc
        print("-------------------")
        print("Main loop crashed")
        print(format_exc())
        print("-------------------")
    reactor.runReturn()
    sys.exit(app.exec_())
