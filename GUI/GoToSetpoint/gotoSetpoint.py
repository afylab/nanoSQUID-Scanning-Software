
import sys
import twisted
from PyQt5 import QtCore, QtGui, QtWidgets, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import time
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
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']

            '''
            Create another connection to labrad in order to have a set of servers opened up in a context
            specific to this module. This allows multiple datavault connections to be editted at the same
            time, or communication with multiple DACs / other devices
            '''

            from labrad.wrappers import connectAsync
            self.cxn_nsot = yield connectAsync(host = '127.0.0.1', password = 'pass')

            self.dac = yield self.cxn_nsot.dac_adc
            yield self.dac.select_device(dict['devices']['nsot']['dac_adc'])

            if dict['devices']['system']['blink device'].startswith('ad5764_dcbox'):
                self.blink_server = yield self.cxn_nsot.ad5764_dcbox
                self.blink_server.select_device(dict['devices']['system']['blink device'])
            elif dict['devices']['system']['blink device'].startswith('DA'):
                self.blink_server = yield self.cxn_nsot.dac_adc
                self.blink_server.select_device(dict['devices']['system']['blink device'])

            self.blinkChan = dict['channels']['system']['blink channel'] - 1

            self.biasChan = dict['channels']['nsot']['nSOT Bias'] - 1
            self.biasRefChan = dict['channels']['nsot']['Bias Reference'] - 1
            self.gateChan = dict['channels']['nsot']['nSOT Gate'] - 1
            self.gateRefChan = dict['channels']['nsot']['Gate Reference'] - 1
            self.feedbackChan = dict['channels']['nsot']['DC Readout'] - 1

            self.setpointDict = {'bias' : 0,
                                 'gate' : 0}

            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")

            yield self.readInitVals()

            self.unlockInterface()

        except Exception as inst:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")

    @inlineCallbacks
    def readInitVals(self):
        try:
            yield self.readBias()
            yield self.readGate()
            yield self.readFeedback()
        except Exception as inst:
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

    @inlineCallbacks
    def zeroBiasFunc(self):
        try:
            curr_bias = float(self.setpointDict['bias'])
            steps = int(np.absolute(curr_bias) * 1000 + 5)
            delay = 2000
            tmp = yield self.dac.buffer_ramp([self.biasChan], [self.biasChan], [curr_bias], [0], steps, delay)
            self.setpointDict['bias'] = 0
            new_bias = yield self.dac.read_voltage(self.biasRefChan)
            self.currBiasLbl.setText('Current Bias: ' + str(new_bias) + 'V')
        except Exception as inst:
            printErrorInfo()

    @inlineCallbacks
    def gotoBiasFunc(self):
        flag = False

        new_bias = readNum(self.biasSetpntLine.text())
        if not isinstance(new_bias, float):
            flag = True
            self.biasSetpntLine.setText('FORMAT ERROR')

        steps = np.absolute(int(readNum(self.biasPntsLine.text())))
        if not isinstance(steps, int):
            flag = True
            self.biasPntsLine.setText('FORMAT ERROR')

        delay = np.absolute(int(readNum(self.biasDelayLine.text()))) * 1000
        if not isinstance(delay, int):
            flag = True
            self.biasDelayLine.setText('FORMAT ERROR')

        if np.absolute(new_bias) > 10:
            new_bias = 10 * (new_bias / np.absolute(new_bias))
            self.biasSetpntLine.setText(str(new_bias))

        if flag == False:
            tmp = yield self.dac.buffer_ramp([self.biasChan], [self.biasChan], [self.setpointDict['bias']], [new_bias], steps, delay)
            self.setpointDict['bias'] = new_bias
            self.currBiasLbl.setText('Current Bias: '+ str(new_bias) + 'V')
            self.currBiasLbl.setStyleSheet("QLabel#currBiasLbl{color: rgb(168,168,168); font:bold 10pt;}")
        else:
            yield self.sleep(0.5)

    @inlineCallbacks
    def zeroGateFunc(self):
        curr_gate = float(self.setpointDict['gate'])
        steps = int(np.absolute(curr_gate) * 1000 + 5)
        delay = 2000
        tmp = yield self.dac.buffer_ramp([self.gateChan], [self.gateChan], [curr_gate], [0], steps, delay)
        self.setpointDict['gate'] = 0
        new_gate = yield self.dac.read_voltage(self.gateRefChan)
        self.currGateLbl.setText('Current Gate: ' + str(new_gate) + 'V')

    @inlineCallbacks
    def gotoGateFunc(self):
        flag = False

        new_gate = readNum(self.gateSetpntLine.text())
        if not isinstance(new_gate, float):
            flag = True
            self.gateSetpntLine.setText('FORMAT ERROR')

        steps = np.absolute(int(readNum(self.gatePntsLine.text())))
        if not isinstance(steps, int):
            flag = True
            self.gatePntsLine.setText('FORMAT ERROR')

        delay = np.absolute(int(readNum(self.gateDelayLine.text()))) * 1000
        if not isinstance(delay, int):
            flag = True
            self.gateDelayLine.setText('FORMAT ERROR')

        if np.absolute(new_gate) > 10:
            new_gate = 10 * (new_gate / np.absolute(new_gate))
            self.gateSetpntLine.setText(str(new_gate))

        if flag == False:
            tmp = yield self.dac.buffer_ramp([self.gateChan], [self.gateChan], [self.setpointDict['gate']], [new_gate], steps, delay)
            self.setpointDict['gate'] = new_gate
            self.currGateLbl.setText('Current Gate: '+ str(new_gate) + 'V')
            self.currGateLbl.setStyleSheet("QLabel#currGateLbl{color: rgb(168,168,168); font:bold 10pt;}")
        else:
            yield self.sleep(0.5)

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
        self.biasSetpntLine.setText(formatNum(bias))
        yield self.gotoBiasFunc()

    @inlineCallbacks
    def readBias(self):
        curr_bias = yield self.dac.read_voltage(self.biasRefChan)
        self.setpointDict['bias'] = float(curr_bias)

        self.currBiasLbl.setText('Current Bias: '+ str(curr_bias) + 'V')
        self.currBiasLbl.setStyleSheet("QLabel#currBiasLbl{color: rgb(168,168,168); font:bold 10pt;}")

        returnValue(float(curr_bias))

    @inlineCallbacks
    def setGate(self, gate):
        self.gateSetpntLine.setText(formatNum(gate))
        yield self.gotoGateFunc()

    @inlineCallbacks
    def readGate(self):
        curr_gate = yield self.dac.read_voltage(self.gateRefChan)
        self.setpointDict['gate'] = float(curr_gate)

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
            printErrorInfo()

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def lockInterface(self):
        self.biasSetpntLine.setEnabled(False)
        self.biasPntsLine.setEnabled(False)
        self.biasDelayLine.setEnabled(False)

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
        self.biasSetpntLine.setEnabled(True)
        self.biasPntsLine.setEnabled(True)
        self.biasDelayLine.setEnabled(True)

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
