from __future__ import division
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import time

path = sys.path[0] + r"\GoToSetpoint"
GoToSetpointUI, QtBaseClass = uic.loadUiType(path + r"\gotoSetpoint.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

#Window for going to a particular nSOT bias or magnetic field 
class Window(QtGui.QMainWindow, GoToSetpointUI):
    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)
        
        self.setupUi(self)
        self.window = parent
        self.reactor = reactor

        self.moveDefault()
        
        self.cxn = False
        self.dac = False
        self.ips = False
        self.blink_server = False
        
        self.zeroFieldBtn.clicked.connect(self.zeroFieldFunc)
        self.zeroBiasBtn.clicked.connect(self.zeroBiasFunc)
        self.gotoFieldBtn.clicked.connect(self.gotoFieldFunc)
        self.gotoBiasBtn.clicked.connect(self.gotoBiasFunc)
        
        self.blinkBtn.clicked.connect(self.blinkOutFunc)
        self.push_readSetpoint.clicked.connect(self.readSetpoint)
        self.push_zeroFeedback.clicked.connect(self.zeroFeedback)

        self.lockInterface()
        
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']

            #Eventually make this module compatible with Toellner, for now it is not
            if dict['devices']['system']['magnet supply'] == 'Toellner Power Supply':
                self.dac_toe = dict['servers']['local']['dac_adc']
                self.magDevice = 'Toellner 8851'
            elif dict['devices']['system']['magnet supply'] == 'IPS 120 Power Supply':
                self.ips = dict['servers']['remote']['ips120']
                self.magDevice = 'IPS 120-10'
                
            self.toeCurChan = dict['channels']['system']['toellner dac current'] - 1
            self.toeVoltsChan = dict['channels']['system']['toellner dac voltage'] - 1
            
            '''
            Create another connection to labrad in order to have a set of servers opened up in a context
            specific to this module. This allows multiple datavault connections to be editted at the same
            time, or communication with multiple DACs / other devices 
            '''
            
            from labrad.wrappers import connectAsync
            self.cxn_nsot = yield connectAsync(host = '127.0.0.1', password = 'pass')
            
            self.dac = yield self.cxn_nsot.dac_adc
            self.dac.select_device(dict['devices']['nsot']['dac_adc'])
                
            if dict['devices']['system']['blink device'].startswith('ad5764_dcbox'):
                self.blink_server = yield self.cxn_nsot.ad5764_dcbox
                self.blink_server.select_device(dict['devices']['system']['blink device'])
            elif dict['devices']['system']['blink device'].startswith('DA'):
                self.blink_server = yield self.cxn_nsot.dac_adc
                self.blink_server.select_device(dict['devices']['system']['blink device'])

            self.blinkChan = dict['channels']['system']['blink channel'] - 1
                
            self.biasChan = dict['channels']['nsot']['nSOT Bias'] - 1
            self.biasRefChan = dict['channels']['nsot']['Bias Reference'] - 1
            self.feedbackChan = dict['channels']['nsot']['DC Readout'] - 1
            
            self.setpointDict = {'field' : 0, 'bias' : 0}

            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            
            self.unlockInterface()
            
        except Exception as inst:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            #print 'nsot labrad connect', inst
            #exc_type, exc_obj, exc_tb = sys.exc_info()
            #print 'line num ', exc_tb.tb_lineno

    @inlineCallbacks
    def readInitVals(self, c = None):
        try:
            if self.magDevice == 'IPS 120-10':
                yield self.ips.set_control(3)
                curr_field = yield self.ips.read_parameter(7)
                yield self.ips.set_control(2)
                curr_field =float(curr_field[1:])

                self.setpointDict['field'] = curr_field
                self.currFieldLbl.setText('Current Field: ' + str(curr_field) + 'T')
                
            else:
                self.currFieldLbl.setText('Current Field: 0T')
            
            curr_bias = yield self.dac.read_voltage(self.biasRefChan)
            self.setpointDict['bias'] = float(curr_bias)
            
            self.currBiasLbl.setText('Current Bias: '+ str(curr_bias) + 'V')
            self.currStatusLbl.setText('Status: Idle')
        except Exception as inst:
            print "readInitVals Error: ", inst

    def readSetpoint(self):
        self.readInitVals()
            
    @inlineCallbacks
    def ipsGoToFieldFunc(self, field, rate, c = None):
        try:
            yield self.ips.set_control(3)
            yield self.ips.set_comm_protocol(6)
            yield self.ips.set_control(2)
            yield self.sleep(0.1)

            yield self.ips.set_control(3)
            yield self.ips.set_targetfield(field)
            yield self.ips.set_control(2)
            yield self.sleep(0.1)

            yield self.ips.set_control(3)
            yield self.ips.set_fieldsweep_rate(rate)
            yield self.ips.set_control(2)
            yield self.sleep(0.1)
            
            yield self.ips.set_control(3)
            yield self.ips.set_activity(1)
            yield self.ips.set_control(2)
            yield self.sleep(0.1)
            
            t0 = time.time()
            self.currStatusLbl.setText('Status: Ramping Field')
            while True:
                yield self.ips.set_control(3)
                curr_field = yield self.ips.read_parameter(7)
                yield self.ips.set_control(2)
                if float(curr_field[1:]) <= field + 0.00001 and float(curr_field[1:]) >= field -0.00001:
                    break
                if time.time() - t0 > 1:
                    yield self.ips.set_control(3)
                    yield self.ips.set_targetfield(float(field))
                    yield self.ips.set_control(2)
                    t0 = time.time()
                yield self.sleep(0.25)
            
            self.setpointDict['field'] = field
            self.currFieldLbl.setText('Current Field: '+ str(field) + 'T')
            self.currStatusLbl.setText('Status: Idle')
        except Exception as inst:
            print 'nsot labrad connect', inst
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print 'line num ', exc_tb.tb_lineno
        
            
    @inlineCallbacks
    def zeroFieldFunc(self, c = None):
        if self.magDevice == 'IPS 120-10':
            try:
                rate = float(self.fieldRampRateLine.text())
                yield self.ipsGoToFieldFunc(0, rate, self.reactor)
            except:
                yield self.ipsGoToFieldFunc(0, 0.1, self.reactor)

    @inlineCallbacks
    def zeroBiasFunc(self, c = None):
        curr_bias = float(self.setpointDict['bias'])
        steps = int(np.absolute(curr_bias) * 1000)
        delay = 2000
        tmp = yield self.dac.buffer_ramp([self.biasChan], [self.biasChan], [curr_bias], [0], steps, delay)
        self.setpointDict['bias'] = 0
        new_bias = yield self.dac.read_voltage(self.biasRefChan)
        self.currBiasLbl.setText('Current Bias: ' + str(new_bias) + 'V')

    @inlineCallbacks
    def gotoFieldFunc(self, c = None):
        flag = False
        if self.magDevice == 'IPS 120-10':
            field = readNum(self.fieldSetpntLine.text(), self, False)
            
            if not isinstance(field, float):
                self.fieldSetpntLine.setText('FORMAT')
                flag = True

            rate = np.absolute(readNum(self.fieldRampRateLine.text(), self, False))
            if not isinstance(rate, float):
                self.fieldRampRateLine.setText('FORMAT')
                flag = True
                
            if np.absolute(field) > 5:
                field  = 5 * (field / np.absolute(field))
                
            if flag == False:
                yield self.ipsGoToFieldFunc(field, rate)
        
    @inlineCallbacks
    def gotoBiasFunc(self, c = None):
        flag = False
        
        new_bias = readNum(self.biasSetpntLine.text(), self, False)
        if not isinstance(new_bias, float):
            flag = True
            self.biasSetpntLine.setText('FORMAT ERROR')
            
        steps = np.absolute(int(readNum(self.biasPntsLine.text(), self, False)))
        if not isinstance(steps, int):
            flag = True
            self.biasSetpntLine.setText('FORMAT ERROR')
            
        delay = np.absolute(int(readNum(self.biasDelayLine.text(), self, False))) * 1000
        if not isinstance(delay, int):
            flag = True
            self.biasSetpntLine.setText('FORMAT ERROR')
            
        print self.setpointDict
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
    def blinkOutFunc(self, c = None):
        yield self.blink_server.set_voltage(self.blinkChan, 5)
        yield self.sleep(0.25)
        yield self.blink_server.set_voltage(self.blinkChan, 0)
        yield self.sleep(0.25)
        
    @inlineCallbacks
    def zeroFeedback(self, c = None):
        try:
            val = yield self.dac.read_voltage(self.feedbackChan)
            yield self.dac.set_voltage(0,val)
            print 'Channel 1 Output on the nSOT DAC ADC has been set to ' + str(val) + ' volts to offset the lock points voltage and allow maximal gain on the SR560.'
        except Exception as inst:
            print inst
            
            
    def lockInterface(self):
        self.fieldSetpntLine.setEnabled(False)
        self.fieldRampRateLine.setEnabled(False)
        self.biasSetpntLine.setEnabled(False)
        self.biasPntsLine.setEnabled(False)
        self.biasDelayLine.setEnabled(False)
        
        self.gotoFieldBtn.setEnabled(False)
        self.zeroFieldBtn.setEnabled(False)
        
        self.gotoBiasBtn.setEnabled(False)
        self.zeroBiasBtn.setEnabled(False)
        
        self.push_readSetpoint.setEnabled(False)
        self.push_zeroFeedback.setEnabled(False)
        self.blinkBtn.setEnabled(False)
        
    def unlockInterface(self):
        self.fieldSetpntLine.setEnabled(True)
        self.fieldRampRateLine.setEnabled(True)
        self.biasSetpntLine.setEnabled(True)
        self.biasPntsLine.setEnabled(True)
        self.biasDelayLine.setEnabled(True)
        
        self.gotoFieldBtn.setEnabled(True)
        self.zeroFieldBtn.setEnabled(True)
        
        self.gotoBiasBtn.setEnabled(True)
        self.zeroBiasBtn.setEnabled(True)
        
        self.push_readSetpoint.setEnabled(True)
        self.push_zeroFeedback.setEnabled(True)
        self.blinkBtn.setEnabled(True)
        
    def moveDefault(self):
        self.move(550,10)
        
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d