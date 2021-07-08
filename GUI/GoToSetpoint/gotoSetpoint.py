import sys
from PyQt5 import QtWidgets, uic
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import numpy as np
from nSOTScannerFormat import readNum, formatNum, printErrorInfo

path = sys.path[0] + r"\GoToSetpoint"
GoToSetpointUI, QtBaseClass = uic.loadUiType(path + r"\gotoSetpoint.ui")

#Window for going to a particular nSOT bias or magnetic field
class Window(QtWidgets.QMainWindow, GoToSetpointUI):
    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)

        self.setupUi(self)
        self.window = parent
        self.reactor = reactor

        self.moveDefault()

        self.cxn = False
        self.dac = False
        self.blink_server = False

        #Dictionaries of the setpoint settings with some default values
        self.settingsDict = {
                'bias current':     0.0,
                'bias setpoint':    0.0,
                'bias steps':       500,
                'bias delay':       0.001,
                'gate current':     0.0,
                'gate setpoint':    0.0,
                'gate steps':       500,
                'gate delay':       0.001,
        }

        self.lineEdit_biasSetpoint.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_biasSetpoint, 'bias setpoint', [-10.0, 10.0]))
        self.lineEdit_biasSteps.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_biasSteps, 'bias steps'))
        self.lineEdit_biasDelay.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_biasDelay, 'bias delay'))

        self.lineEdit_gateSetpoint.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_biasSetpoint, 'gate setpoint', [-10.0, 10.0]))
        self.lineEdit_gateSteps.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_biasSteps, 'gate steps'))
        self.lineEdit_gateDelay.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_biasDelay, 'gate delay'))

        self.zeroBiasBtn.clicked.connect(lambda: self.zeroBiasFunc())
        self.gotoBiasBtn.clicked.connect(lambda: self.gotoBiasFunc())

        self.zeroGateBtn.clicked.connect(lambda: self.zeroGateFunc())
        self.gotoGateBtn.clicked.connect(lambda: self.gotoGateFunc())

        self.blinkBtn.clicked.connect(lambda: self.blink())
        self.push_FdbkOn.clicked.connect(lambda: self.setFeedback(True))
        self.push_FdbkOff.clicked.connect(lambda: self.setFeedback(False))

        self.push_readGate.clicked.connect(lambda: self.readGate())
        self.push_readBias.clicked.connect(lambda: self.readBias())

        self.lockInterface()

    @inlineCallbacks
    def connectLabRAD(self, equip):
        try:
            self.cxn = equip.cxn

            '''
            Create another connection to labrad in order to have a set of servers opened up in a context
            specific to this module. This allows multiple datavault connections to be editted at the same
            time, or communication with multiple DACs / other devices
            '''

            from labrad.wrappers import connectAsync
            self.cxn_nsot = yield connectAsync(host = '127.0.0.1', password = 'pass')

            if 'nSOT DAC' in equip.servers:
                svr, ln, device_info, cnt, config = equip.servers['nSOT DAC']
                #Connected to the appropriate DACADC
                self.dac = yield self.cxn_nsot.dac_adc
                yield self.dac.select_device(device_info)

                self.biasChan = config['nSOT Bias'] - 1
                self.biasRefChan = config['Bias Reference'] - 1
                self.gateChan = config['nSOT Gate'] - 1
                self.gateRefChan = config['Gate Reference'] - 1
                self.feedbackChan = config['DC Readout'] - 1
            else:
                print("'nSOT DAC' not found, LabRAD connection of goToSetpoint Failed.")
                return

            if "Blink Device" in equip.servers:
                svr, labrad_name, device_info, cnt, config = equip.servers["Blink Device"]

                #Create a connection to the proper device for blinking
                if labrad_name.startswith('ad5764_dcbox'):
                    self.blink_server = yield self.cxn_scan.ad5764_dcbox
                    yield self.blink_server.select_device(device_info)
                    print('DC BOX Blink Device')
                elif labrad_name.startswith('DA'):
                    self.blink_server = yield self.cxn_scan.dac_adc
                    yield self.blink_server.select_device(device_info)
                    print('DAC ADC Blink Device')

                self.blinkChan = config['blink channel']
            else:
                print("'Blink Device' not found, LabRAD connection of goToSetpoint Failed.")
                return

            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")

            yield self.readInitVals()

            self.unlockInterface()
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            printErrorInfo()

    def disconnectLabRAD(self):
        self.lockInterface()

    @inlineCallbacks
    def readInitVals(self):
        try:
            yield self.readBias()
            yield self.readGate()
            yield self.readFeedback()
        except:
            printErrorInfo()

    def feedbackButtonColors(self, on):
        if on:
            style = '''QPushButton:pressed#push_FdbkOn{
                        color: rgb(0,170,0);
                        background-color:rgb(168,168,168);
                        border: 1px solid rgb(0,170,0);
                        border-radius: 5px
                        }

                        QPushButton#push_FdbkOn{
                        color: rgb(0,170,0);
                        background-color:rgb(0,0,0);
                        border: 2px solid  rgb(0,170,0);
                        border-radius: 5px
                        }
                        '''
            self.push_FdbkOn.setStyleSheet(style)

            style = '''QPushButton:pressed#push_FdbkOff{
                        color: rgb(95,107,166);
                        background-color:rgb(168,168,168);
                        border: 1px solid rgb(95,107,166);
                        border-radius: 5px
                        }

                        QPushButton#push_FdbkOff{
                        color: rgb(95,107,166);
                        background-color:rgb(0,0,0);
                        border: 2px solid  rgb(95,107,166);
                        border-radius: 5px
                        }
                        '''
            self.push_FdbkOff.setStyleSheet(style)
        else:
            style = '''QPushButton:pressed#push_FdbkOn{
                        color: rgb(95,107,166);
                        background-color:rgb(168,168,168);
                        border: 1px solid rgb(95,107,166);
                        border-radius: 5px
                        }

                        QPushButton#push_FdbkOn{
                        color: rgb(95,107,166);
                        background-color:rgb(0,0,0);
                        border: 2px solid  rgb(95,107,166);
                        border-radius: 5px
                        }
                        '''
            self.push_FdbkOn.setStyleSheet(style)

            style = '''QPushButton:pressed#push_FdbkOff{
                        color: rgb(161,0,0);
                        background-color:rgb(168,168,168);
                        border: 1px solid rgb(161,0,0);
                        border-radius: 5px
                        }

                        QPushButton#push_FdbkOff{
                        color: rgb(161,0,0);
                        background-color:rgb(0,0,0);
                        border: 2px solid  rgb(161,0,0);
                        border-radius: 5px
                        }
                        '''
            self.push_FdbkOff.setStyleSheet(style)

    @inlineCallbacks
    def setFeedback(self, on):
        if on:
            yield self.blink_server.set_voltage(self.blinkChan, 0)
        else:
            yield self.blink_server.set_voltage(self.blinkChan, 5)
        self.feedbackButtonColors(on)

    def updateSweepParameter(self, lineEdit, key, range = None):
        val = readNum(str(lineEdit.text())) #Read the text from the provided lineEdit
        if isinstance(val,float): #If it's a proper number, update the sweep Parameter dictionary
            if range == None:
                self.settingsDict[key] = val
            elif val >= range[0] and val <= range[1]: #Check that the number is within the proper range
                self.settingsDict[key] = val
        #Set the linedit to the formatted value. If it was input incorrectly, this resets the lineEdit to the previous value
        lineEdit.setText(formatNum(self.settingsDict[key], 6))

    @inlineCallbacks
    def zeroBiasFunc(self):
        try:
            curr_bias = self.settingsDict['bias current']
            steps = int(np.absolute(curr_bias) * 1000 + 5)
            delay = 2000

            yield self.dac.buffer_ramp([self.biasChan], [self.biasChan], [curr_bias], [0.0], steps, delay)
            self.settingsDict['bias current'] = 0.0
            new_bias = yield self.dac.read_voltage(self.biasRefChan)
            self.currBiasLbl.setText('Current Bias: ' + str(new_bias) + 'V')
        except:
            printErrorInfo()

    @inlineCallbacks
    def gotoBiasFunc(self):
        new_bias = self.settingsDict['bias setpoint']
        curr_bias = self.settingsDict['bias current']
        steps = int(self.settingsDict['bias steps'])
        delay = int(1e6*self.settingsDict['bias delay'])

        yield self.dac.buffer_ramp([self.biasChan], [self.biasChan], [curr_bias], [new_bias], steps, delay)
        self.settingsDict['bias current'] = new_bias
        self.currBiasLbl.setText('Current Bias: '+ str(new_bias) + 'V')
        self.currBiasLbl.setStyleSheet("QLabel#currBiasLbl{color: rgb(168,168,168); font:bold 10pt;}")

    @inlineCallbacks
    def zeroGateFunc(self):
        curr_gate = self.settingsDict['gate current']
        steps = int(np.absolute(curr_gate) * 1000 + 5)
        delay = 2000

        yield self.dac.buffer_ramp([self.gateChan], [self.gateChan], [curr_gate], [0], steps, delay)
        self.settingsDict['gate curent'] = 0.0
        new_gate = yield self.dac.read_voltage(self.gateRefChan)
        self.currGateLbl.setText('Current Gate: ' + str(new_gate) + 'V')

    @inlineCallbacks
    def gotoGateFunc(self):
        new_gate = self.settingsDict['gate setpoint']
        curr_gate = self.settingsDict['gate current']
        steps = int(self.settingsDict['gate steps'])
        delay = int(1e6*self.settingsDict['gate delay'])

        yield self.dac.buffer_ramp([self.gateChan], [self.gateChan], [curr_gate], [new_gate], steps, delay)
        self.settingsDict['gate current'] = new_gate
        self.currGateLbl.setText('Current Gate: '+ str(new_gate) + 'V')
        self.currGateLbl.setStyleSheet("QLabel#currGateLbl{color: rgb(168,168,168); font:bold 10pt;}")

    @inlineCallbacks
    def blink(self):
        yield self.blink_server.set_voltage(self.blinkChan, 5)
        self.feedbackButtonColors(False)
        yield self.sleep(0.25)
        yield self.blink_server.set_voltage(self.blinkChan, 0)
        self.feedbackButtonColors(True)

#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""

    @inlineCallbacks
    def setBias(self, bias):
        self.lineEdit_biasSetpoint.setText(formatNum(bias))
        yield self.gotoBiasFunc()

    @inlineCallbacks
    def readBias(self):
        curr_bias = yield self.dac.read_voltage(self.biasRefChan)
        self.settingsDict['bias current'] = float(curr_bias)

        self.currBiasLbl.setText('Current Bias: '+ str(curr_bias) + 'V')
        self.currBiasLbl.setStyleSheet("QLabel#currBiasLbl{color: rgb(168,168,168); font:bold 10pt;}")

        returnValue(float(curr_bias))

    @inlineCallbacks
    def setGate(self, gate):
        self.lineEdit_gateSetpoint.setText(formatNum(gate))
        yield self.gotoGateFunc()

    @inlineCallbacks
    def readGate(self):
        curr_gate = yield self.dac.read_voltage(self.gateRefChan)
        self.settingsDict['gate current'] = float(curr_gate)

        self.currGateLbl.setText('Current Gate: '+ str(curr_gate) + 'V')
        self.currGateLbl.setStyleSheet("QLabel#currGateLbl{color: rgb(168,168,168); font:bold 10pt;}")

        returnValue(float(curr_gate))

    @inlineCallbacks
    def readFeedback(self):
        feedback = False;
        try:
            curr_fdbk = yield self.blink_server.get_voltage(self.blinkChan)
            if curr_fdbk < 0.2:
                self.feedbackButtonColors(True)
                feedback = True
            else:
                self.feedbackButtonColors(False)
                feedback = False
            returnValue(feedback)
        except:
            print('Blink server does not have voltage reading capabilities.')

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def lockInterface(self):
        self.lineEdit_biasSetpoint.setEnabled(False)
        self.lineEdit_biasSteps.setEnabled(False)
        self.lineEdit_biasDelay.setEnabled(False)

        self.lineEdit_gateSetpoint.setEnabled(False)
        self.lineEdit_gateSteps.setEnabled(False)
        self.lineEdit_gateDelay.setEnabled(False)

        self.gotoBiasBtn.setEnabled(False)
        self.zeroBiasBtn.setEnabled(False)
        self.push_readBias.setEnabled(False)

        self.blinkBtn.setEnabled(False)

        self.push_FdbkOn.setEnabled(False)
        self.push_FdbkOff.setEnabled(False)

        self.gotoGateBtn.setEnabled(False)
        self.zeroGateBtn.setEnabled(False)
        self.push_readGate.setEnabled(False)

    def unlockInterface(self):
        self.lineEdit_biasSetpoint.setEnabled(True)
        self.lineEdit_biasSteps.setEnabled(True)
        self.lineEdit_biasDelay.setEnabled(True)

        self.lineEdit_gateSetpoint.setEnabled(True)
        self.lineEdit_gateSteps.setEnabled(True)
        self.lineEdit_gateDelay.setEnabled(True)

        self.gotoBiasBtn.setEnabled(True)
        self.zeroBiasBtn.setEnabled(True)
        self.push_readBias.setEnabled(True)

        self.blinkBtn.setEnabled(True)

        self.push_FdbkOn.setEnabled(True)
        self.push_FdbkOff.setEnabled(True)

        self.gotoGateBtn.setEnabled(True)
        self.zeroGateBtn.setEnabled(True)
        self.push_readGate.setEnabled(True)

    def moveDefault(self):
        self.move(550,10)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
