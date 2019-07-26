import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred

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
        
        self.cxn = False
        self.ips = False
        
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
            self.cxn = dict['servers']['remote']['cxn']
            self.ips = dict['servers']['remote']['ips120']
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  
        if not self.cxn: 
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.ips:
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
        self.cxn = False
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
        while self.monitor:
            if not self.setting_value:
                if self.monitor_param == 'Field':
                    if self.viewChargingInfo:
                        val = yield self.ips.read_parameter(7)
                    else:
                        val = yield self.ips.read_parameter(18)
                elif self.monitor_param == 'Curr':
                    if self.viewChargingInfo:
                        val = yield self.ips.read_parameter(0)
                    else:
                        val = yield self.ips.read_parameter(16)
                elif self.monitor_param == 'Volts':
                    if self.viewChargingInfo:
                        val = yield self.ips.read_parameter(1)
                    else:
                        val = '  '
                try:
                    self.label_fieldval.setText(formatNum(float(val[1:]),3))
                except Exception as inst:
                    print inst
            yield self.sleep(0.5)
            
    @inlineCallbacks
    def loadInitialValues(self):
        #Load parameters
        setpoint = yield self.ips.read_parameter(8)
        ramprate = yield self.ips.read_parameter(9)
        self.setpoint = setpoint
        self.ramprate = ramprate
        self.lineEdit_setpoint.setText(formatNum(float(setpoint[1:])))
        self.lineEdit_ramprate.setText(formatNum(float(ramprate[1:])))
        
        #self.ramprate = 1.0
        #self.lineEdit_ramprate.setText('1.0')
        #yield self.setRamprate()
        
        yield self.updateSwitchStatus()
        
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
            self.setting_value = True
            yield self.ips.set_control(3)
            yield self.ips.set_fieldsweep_rate(val)
            yield self.ips.set_control(2)
            self.setting_value = False
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
        yield self.ips.set_control(3)
        a = yield self.ips.set_targetfield(self.setpoint)
        print a
        yield self.ips.set_activity(1)
        yield self.ips.set_control(2)
        
    @inlineCallbacks
    def gotoZero(self, c = None):
        yield self.ips.set_control(3)
        yield self.ips.set_activity(2)
        yield self.ips.set_control(2)
        
    @inlineCallbacks
    def hold(self, c = None):
        yield self.ips.set_control(3)
        yield self.ips.set_activity(0)
        yield self.ips.set_control(2)
        
    @inlineCallbacks
    def clamp(self, c= None):
        yield self.ips.set_control(3)
        yield self.ips.set_activity(4)
        yield self.ips.set_control(2)
        
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
        except Exception as inst:
            print inst
            
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
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        
        