import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np

path = sys.path[0] + r"\Field Control"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\FieldControl.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way. 
sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()        

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        self.push_viewField.clicked.connect(self.viewField)
        self.push_viewCurr.clicked.connect(self.viewCurr)
        self.push_viewVolts.clicked.connect(self.viewVolts)
        self.push_GotoSet.clicked.connect(self.gotoSet)
        self.push_GotoZero.clicked.connect(self.gotoZero)
        self.push_hold.clicked.connect(self.hold)
        self.push_clamp.clicked.connect(self.clamp)
        self.push_toggleView.clicked.connect(self.toggleView)
        self.push_persistSwitch.clicked.connect(self.togglePersist)
        
        self.lineEdit_setpoint.editingFinished.connect(self.setSetpoint)
        self.lineEdit_ramprate.editingFinished.connect(self.setRamprate)
        
        self.ips = False
        self.dac_toe = False
        
        self.currField = 0
        self.currCurrent = 0 
        self.currVoltage = 0
        
        self.monitor_param = 'Field'
        self.setting_value = False
        self.viewChargingInfo = True
        #By default, the switch is off, which corresponds to being in persist mode
        self.persist = True
        self.lockInterface()
        
    def moveDefault(self):
        self.move(550,10)
        
    def connectLabRAD(self, dict):
        #This module does not require any local labrad connections
        pass
            
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            if dict['devices']['system']['magnet supply'] == 'Toellner Power Supply':
                self.dac_toe = dict['servers']['local']['dac_adc']
                self.magDevice = 'Toellner 8851'
                self.setToellnerButtonConfig()
                self.toeCurChan = dict['channels']['system']['toellner dac current'] - 1
                self.toeVoltsChan = dict['channels']['system']['toellner dac voltage'] - 1
            elif dict['devices']['system']['magnet supply'] == 'IPS 120 Power Supply':
                self.ips = dict['servers']['remote']['ips120']
                self.magDevice = 'IPS 120-10'
                self.setDefaultButtonConfig()
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  
        if not self.ips and not self.dac_toe:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:   
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            yield self.loadInitialValues()
            self.unlockInterface()
            self.monitor = True #modified temporarily
            yield self.monitorField()
            
    def disconnectLabRAD(self):
        self.monitor = False
        self.ips120 = False
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.lockInterface()
        
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        pass
        
    @inlineCallbacks
    def monitorField(self):
        try:
            while self.monitor:
                if self.magDevice == 'IPS 120-10':
                    if not self.setting_value:
                        if self.monitor_param == 'Field':
                            if self.viewChargingInfo:
                                val = yield self.ips.read_parameter(7)
                                self.currField = float(val[1:])
                            else:
                                val = yield self.ips.read_parameter(18)
                                self.currField = float(val[1:])
                        elif self.monitor_param == 'Curr':
                            if self.viewChargingInfo:
                                val = yield self.ips.read_parameter(0)
                                self.currCurrent = float(val[1:])
                            else:
                                val = yield self.ips.read_parameter(16)
                                self.currCurrent = float(val[1:])
                        elif self.monitor_param == 'Volts':
                            if self.viewChargingInfo:
                                val = yield self.ips.read_parameter(1)
                                self.currVoltage = float(val[1:])
                            else:
                                val = '  '
                try:
                    if self.monitor_param == 'Field':
                        self.label_fieldval.setText(formatNum(self.currField,3))
                    elif self.monitor_param == 'Curr':
                        self.label_fieldval.setText(formatNum(self.currCurrent,3))
                    elif self.monitor_param == 'Volts':
                        self.label_fieldval.setText(formatNum(self.currVoltage,3))
                except Exception as inst:
                    print inst
                yield self.sleep(0.5)
        except Exception as inst:
            print inst
            
    @inlineCallbacks
    def loadInitialValues(self):
        try:
            #Load parameters
            if self.magDevice == 'IPS 120-10':
                setpoint = yield self.ips.read_parameter(8)
                ramprate = yield self.ips.read_parameter(9)
                self.setpoint = float(setpoint[1:])
                self.ramprate = float(ramprate[1:])

                yield self.updateSwitchStatus()
            else:
                self.setpoint = 0.0
                self.ramprate = 1.0
                yield self.sleep(0.1)
                
            self.lineEdit_setpoint.setText(formatNum(self.setpoint))
            self.lineEdit_ramprate.setText(formatNum(self.ramprate))
        except Exception as inst:
            print inst
    
    @inlineCallbacks
    def updateSwitchStatus(self):
        status = yield self.ips.examine()
        #The 9th (index 8) character of the status string encodes whether or not
        #the persistent switch is currently on
        if int(status[8]) == 0 or int(status[8]) == 2:
            style = '''#push_persistSwitch{
                        background: rgb(161, 0, 0);
                        border-radius: 10px;
                        }'''
            self.push_persistSwitch.setStyleSheet(style)
            self.label_switchStatus.setText('Persist')
            self.persist = True
        elif int(status[8]) == 1:
            style = '''#push_persistSwitch{
                        background: rgb(0, 170, 0);
                        border-radius: 10px;
                        }'''
            self.push_persistSwitch.setStyleSheet(style)
            self.label_switchStatus.setText('Charging')
            self.persist = False
        else:
            style = '''#push_persistSwitch{
                        background: rgb(0, 0, 152);
                        border-radius: 10px;
                        }'''
            self.push_persistSwitch.setStyleSheet(style)
            self.label_switchStatus.setText('Error')
            self.persist = False
            
    def setSetpoint(self, c = None):
        val = readNum(str(self.lineEdit_setpoint.text()), self, False)
        if isinstance(val,float):
            self.setpoint = val
        self.lineEdit_setpoint.setText(formatNum(self.setpoint, 4))
        
    @inlineCallbacks
    def setRamprate(self, c = None):
        val = readNum(str(self.lineEdit_ramprate.text()), self, False)
        if isinstance(val,float):
            self.ramprate = val
            if self.magDevice == 'IPS 120-10':
                self.setting_value = True
                yield self.ips.set_control(3)
                yield self.ips.set_fieldsweep_rate(val)
                yield self.ips.set_control(2)
                self.setting_value = False
            else:
                yield self.sleep(0.1)
        self.lineEdit_ramprate.setText(formatNum(self.ramprate))
        
    def viewField(self):
        self.monitor_param = 'Field'
        self.label_display.setText('Field (T):')
    
    def viewCurr(self):
        self.monitor_param = 'Curr'
        self.label_display.setText('Current (A):')
    
    def viewVolts(self):
        self.monitor_param = 'Volts'
        self.label_display.setText('Volts (V):')
        
    @inlineCallbacks
    def gotoSet(self, c = None):
        try:
            if self.magDevice == 'IPS 120-10':
                yield self.gotoSetIPS()
            else:
                yield self.toeSweepField(self.currField, self.setpoint, self.ramprate)
        except Exception as inst:
            print 'GTS, ', str(inst)
            
    @inlineCallbacks
    def gotoSetIPS(self, c = None):
        self.setting_value = True
        yield self.ips.set_control(3)
        yield self.ips.set_targetfield(self.setpoint)
        yield self.ips.set_activity(1)
        yield self.ips.set_control(2)
        self.setting_value = False
        
    @inlineCallbacks
    def gotoZero(self, c = None):
        try:
            if self.magDevice == 'IPS 120-10':
                yield self.gotoZeroIPS()
            else:
                yield self.toeSweepField(self.currField, 0, self.ramprate)
        except Exception as inst:
            print 'GTZ, ', str(inst)
            
    @inlineCallbacks
    def gotoZeroIPS(self, c = None):
        self.setting_value = True
        yield self.ips.set_control(3)
        yield self.ips.set_activity(2)
        yield self.ips.set_control(2)
        self.setting_value = False
        
    #Only can be called when in the IPS configuration
    @inlineCallbacks
    def hold(self, c = None):
        self.setting_value = True
        yield self.ips.set_control(3)
        yield self.ips.set_activity(0)
        yield self.ips.set_control(2)
        self.setting_value = False
        
    @inlineCallbacks
    def clamp(self, c= None):
        self.setting_value = True
        yield self.ips.set_control(3)
        yield self.ips.set_activity(4)
        yield self.ips.set_control(2)
        self.setting_value = False
        
    def toggleView(self):
        if self.viewChargingInfo:
            self.viewChargingInfo = False
            self.push_toggleView.setText('Monitoring Persist')
        else:
            self.viewChargingInfo = True
            self.push_toggleView.setText('Monitoring Charging')
            
    @inlineCallbacks
    def togglePersist(self, c = None):
        try:
            self.setting_value = True
            if self.persist:
                yield self.ips.set_control(3)
                yield self.ips.set_switchheater(1)
                yield self.sleep(0.25)
                yield self.updateSwitchStatus()
                yield self.ips.set_control(2)
            else:
                yield self.ips.set_control(3)
                yield self.ips.set_switchheater(0)
                yield self.sleep(0.25)
                yield self.updateSwitchStatus()
                yield self.ips.set_control(2)
            self.setting_value = False
        except Exception as inst:
            print inst
            
    @inlineCallbacks
    def toeSweepField(self, B_i, B_f, B_speed, c = None):
        try:
            #Toellner voltage set point / DAC voltage out conversion [V_Toellner / V_DAC]
            VV_conv = 3.20
            #Toellner current set point / DAC voltage out conversion [I_Toellner / V_DAC]
            IV_conv = 1.0 

            #Field / Current ratio on the dipper magnet (0.132 [Tesla / Amp])
            IB_conv = 0.132

            #Starting and ending field values in Tesla, use positive field values for now
            B_range = np.absolute(B_f - B_i)

            #Delay between DAC steps in microseconds
            magnet_delay = 1000
            #Converts between microseconds and minutes [us / minute]
            t_conv = 6e07

            #Sets the appropriate DAC buffer ramp parameters
            sweep_steps = int((t_conv * B_range) / (B_speed * magnet_delay))  + 1
            v_start = B_i / (IB_conv * IV_conv)
            v_end = B_f / (IB_conv * IV_conv)

            #Sets an appropraite voltage set point to ensure that the Toellner power supply stays in constant current mode
            # assuming a parasitic resistance of R_p between the power supply and magnet
            overshoot = 5
            R_p = 2
            V_setpoint =  (overshoot * R_p * np.amax([B_i, B_f])) / (VV_conv * IB_conv)
            V_initial = (overshoot * R_p * np.amin([B_i, B_f])) / (VV_conv * IB_conv)
            if V_setpoint > 10.0:
                V_setpoint = 10.0
            else:
                pass
            if V_initial > 10.0:
                V_initial = 10.0
            else:
                pass

            #Ramps the DAC such that the Toellner voltage setpoint stays in constant current mode
            #ramp_steps = int(np.absolute(V_setpoint - V_initial) * 1000)+1
            #ramp_delay = 1000
            #yield self.dac_toe.buffer_ramp([self.toeVoltsChan], [0], [V_initial], [V_setpoint], ramp_steps, ramp_delay)
            
            #Sweeps field from B_i to B_f
            print 'Sweeping field from ' + str(B_i) + ' to ' + str(B_f)+'.'
            yield self.dac_toe.buffer_ramp([self.toeCurChan, self.toeVoltsChan],[0],[v_start, V_initial],[v_end, V_setpoint], sweep_steps, magnet_delay)

            self.currVoltage = V_setpoint
            self.currCurrent = B_f/IB_conv
            self.currField = B_f
        except Exception as inst:
            print 'SF, ', str(inst )
    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous 
    # delay that allows other labrad / pyqt methods to run
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""
           
    def lockInterface(self):
        self.push_viewField.setEnabled(False)
        self.push_viewCurr.setEnabled(False)
        self.push_viewVolts.setEnabled(False)
        self.push_GotoZero.setEnabled(False)
        self.push_GotoSet.setEnabled(False)
        self.push_hold.setEnabled(False)
        self.push_clamp.setEnabled(False)
        self.push_toggleView.setEnabled(False)
        self.push_persistSwitch.setEnabled(False)
        self.lineEdit_setpoint.setEnabled(False)
        self.lineEdit_ramprate.setEnabled(False)
        
    def unlockInterface(self):
        self.push_viewField.setEnabled(True)
        self.push_viewCurr.setEnabled(True)
        self.push_viewVolts.setEnabled(True)
        self.push_GotoZero.setEnabled(True)
        self.push_GotoSet.setEnabled(True)
        self.push_hold.setEnabled(True)
        self.push_clamp.setEnabled(True)
        self.push_toggleView.setEnabled(True)
        self.push_persistSwitch.setEnabled(True)
        self.lineEdit_setpoint.setEnabled(True)
        self.lineEdit_ramprate.setEnabled(True)
        
    def setToellnerButtonConfig(self):
        self.push_toggleView.hide()
        self.push_hold.hide()
        self.push_clamp.hide()
        self.push_persistSwitch.hide()
        self.label_switchStatus.hide()
        
    def setDefaultButtonConfig(self):
        self.push_toggleView.show()
        self.push_hold.show()
        self.push_clamp.show()
        self.push_persistSwitch.show()
        self.label_switchStatus.show()
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        
        