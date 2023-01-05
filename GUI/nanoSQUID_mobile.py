'''
A module defining the mobile racks dipper/vector magnet specifically
'''
import sys
from PyQt5 import QtWidgets
from nSOTScanner_minimal import nanoSQUIDSystem
from Equipment import MagnetControllers

class nanoSQUID_mobile(nanoSQUIDSystem):
    system_name = 'mobile'
    
    def configureEquipment(self):
        super().configureEquipment()

        conf = {'DC Readout':3, 
            'nSOT Bias':4, 
            'Noise Readout':2, 
            'nSOT Gate':1, 
            'Gate Reference':1, 
            'Bias Reference':4,
            'Bias Res':10.5, # Bias resistance, in units of kOhms
            'Feedback Res':1.11, # Feedback resistance, in units of kOhms
            'Shunt Res':2.9, # Shunt resistance, in units of Ohms
            'Winding Ratio':14 # Turns ratio fo the array, for amplification.
            }
        self.equip.add_server("nSOT DAC", "dac_adc", "DA16_16_02 (COM4)", config=conf)

        conf = {'blink channel':3}
        self.equip.add_server("Blink Device", "dac_adc", "DA16_16_02 (COM4)", config=conf)

        # conf = {'Input 1':'B', 'Input 1 Label':'1K POT',
            # 'Input 2':'D', 'Input 2 Label':'Sample',
            # 'Input 3':'C', 'Input 3 Label':'He3 POT'
            # }
        # self.equip.add_server("LS 335", "lakeshore_335", config=conf)

        conf = {'max_field':12, "max_ramp":0.3}
        self.equip.add_server("Magnet Z", "mercury_ips_server", controller=MagnetControllers.IPSMagnetControl, config=conf)

#

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    try:
        window = nanoSQUID_mobile(reactor, computer='desktop_4cdp0cl', folderName='NanoSQUID Mobile')
        window.show()
    except:
        from traceback import format_exc
        print("-------------------")
        print("Main loop crashed")
        print(format_exc())
        print("-------------------")
    reactor.runReturn()
    sys.exit(app.exec_())
