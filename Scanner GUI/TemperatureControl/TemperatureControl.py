import sys
from PyQt5 import QtGui, QtWidgets, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import time
import pyqtgraph as pg
import numpy as np

path = sys.path[0] + r"\TemperatureControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\TemperatureControl.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_MeasurementSettings, QtBaseClass = uic.loadUiType(path + r"\MeasurementSettings.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way. 
sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtWidgets.QMainWindow, ScanControlWindowUI):
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()
        
        self.push_Settings.clicked.connect(self.updateSettings)
        self.push_heater.clicked.connect(self.toggleHeater)

        self.lineEdit_setpoint.editingFinished.connect(self.setSetpoint)
        
        self.lineEdit_therm1.editingFinished.connect(self.setTherm1PlotTitle)
        self.lineEdit_therm2.editingFinished.connect(self.setTherm2PlotTitle)
        self.lineEdit_therm3.editingFinished.connect(self.setTherm3PlotTitle)
        
        self.time_offset = 0
        self.timeData = np.array([])
        self.magTempData = np.array([])
        self.sampleTempData = np.array([])
        self.potTempData = np.array([])
        
        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize all the labrad connections as False
        self.cxn = False
        self.ls = False
        
        #Keep track of if the first monitoring datapoint has been taken yet, to set the relative time
        self.first_data_point = True
        
        #For historical reasons, thermometer 1 is called "mag thermometer", thermometer 2 is "sample thermometer" and thermometer 3 is "pot thermometer"
        self.measurementSettings = {
                'mag Input'        : 'D5',
                'sample Input'     : 'D4', 
                'pot Input'        : 'B', 
                'p'                : 50.0,
                'i'                : 50.0,
                'd'                : 1.0,       #
                'setpoint'         : 4.0,       #Setpoint in Kelvin for closed loop (PID) operation
                'out percent'      : 0,         #Pencentage output for open loop / manual mode
                'feedback thermometer' : 2,     #Which thermometer should be used for closed loop heating
                'heater range'     : 5,         #Range for the heater
                'heater output'    : 2,         #Either output 1 or 2
                'heater mode'      : 0,         #0 is closed loop, ie using PID. 1 is open loop, using manual setting mode. 
                'plot record'      : 1,         #plot length shown in hours
                'sample delay'     : 1,         #Delay between temperature samples
        }
        
        self.ls350inputs = {
        'A' : 1,
        'B' : 2, 
        'C' : 3, 
        'D1': 4, 
        'D2': 5, 
        'D3': 6, 
        'D4': 7, 
        'D5': 8,
        }
        
        self.lockInterface()
        
    def moveDefault(self):    
        self.move(550,10)
        self.resize(800,500)
        
    def connectLabRAD(self, dict):
        #This module doesn't use any local labrad connections
        pass
            
    @inlineCallbacks
    def connectLabRAD(self,dict):
        try:
            self.ls = dict['servers']['remote']['ls350']
            if not self.ls:
                self.push_Servers.setStyleSheet("#push_Servers{" + 
                "background: rgb(161, 0, 0);border-radius: 4px;border: 0px;}")
            else:
                self.push_Servers.setStyleSheet("#push_Servers{" + 
                    "background: rgb(0, 170, 0);border-radius: 4px;border: 0px;}")
                self.unlockInterface()
                yield self.readCurrentSettings()
                yield self.startTempMonitoring()
        except Exception as inst:
            print(inst, sys.exc_traceback.tb_lineno)
            
            
    def disconnectLabRAD(self):
        self.cxn = False
        self.ls = False
        self.monitoring = False
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;border: 0px;}")
        
    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        self.magTempFrame.close()
        self.magTempPlot = pg.PlotWidget(parent = self)
        self.magTempPlot.setLabel('left', 'Temperature', units = 'K')
        self.magTempPlot.setLabel('bottom', 'Time', units = 'h')
        self.magTempPlot.showAxis('right', show = True)
        self.magTempPlot.showAxis('top', show = True)
        self.magTempPlot.setTitle('Thermometer 1 vs. Time')
        
        self.sampleTempFrame.close()
        self.sampleTempPlot = pg.PlotWidget(parent = self)
        self.sampleTempPlot.setLabel('left', 'Temperature', units = 'K')
        self.sampleTempPlot.setLabel('bottom', 'Time', units = 'h')
        self.sampleTempPlot.showAxis('right', show = True)
        self.sampleTempPlot.showAxis('top', show = True)
        self.sampleTempPlot.setTitle('Thermometer 2 vs. Time')
        
        self.potTempFrame.close()
        self.potTempPlot = pg.PlotWidget(parent = self)
        self.potTempPlot.setLabel('left', 'Temperature', units = 'K')
        self.potTempPlot.setLabel('bottom', 'Time', units = 'h')
        self.potTempPlot.showAxis('right', show = True)
        self.potTempPlot.showAxis('top', show = True)
        self.potTempPlot.setTitle('Thermometer 3 vs. Time')
        
        self.horizontalLayout_2.addWidget(self.magTempPlot)
        self.horizontalLayout_2.addWidget(self.sampleTempPlot)
        self.horizontalLayout_2.addWidget(self.potTempPlot)
        
    @inlineCallbacks
    def readCurrentSettings(self, c = None):
        try:
            range = yield self.ls.range_read(self.measurementSettings['heater output'])
            
            pid = yield self.ls.pid_read(self.measurementSettings['heater output'])
            pid = pid.split(',')
            
            setpoint = yield self.ls.setpoint_read(self.measurementSettings['heater output'])

            self.lineEdit_setpoint.setText(formatNum(float(setpoint)))
            if range !=0:
                self.measurementSettings['heater range'] = range
            self.measurementSettings['p'] = float(pid[0])
            self.measurementSettings['i'] = float(pid[1])
            self.measurementSettings['d'] = float(pid[2])
            self.measurementSettings['setpoint'] = float(setpoint)
        except Exception as inst:
            print(inst, sys.exc_traceback.tb_lineno)

    @inlineCallbacks
    def updateSettings(self, c = None):
        try:
            MeasSet = MeasurementSettings(self.reactor, self.measurementSettings, parent = self)
            if MeasSet.exec_():
                self.measurementSettings = MeasSet.getValues()
                print(self.measurementSettings)
                
                #Set pid settings
                yield self.ls.pid_set(self.measurementSettings['heater output'],self.measurementSettings['p'],self.measurementSettings['i'],self.measurementSettings['d'])
                
                #Set output settings
                yield self.setOutputSettings()
                
                #In case record time has changed, update plots to reflect that
                self.updatePlots()
                
                if self.measurementSettings['heater mode'] == 0:
                    self.label_setpoint.setText('Setpoint (K):')
                    self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['setpoint']))
                elif self.measurementSettings['heater mode'] == 1:
                    self.label_setpoint.setText('Output (%):')
                    self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['out percent']))
                else:
                    self.label_setpoint.setText('WTF?!?!')
                    
        except Exception as inst:
            print(inst, sys.exc_traceback.tb_lineno)
            
    @inlineCallbacks
    def setOutputSettings(self):
        if self.measurementSettings['feedback thermometer'] == 1:
            feedback_thermometer = self.ls350inputs[self.measurementSettings['mag Input']]
        elif self.measurementSettings['feedback thermometer'] == 2:
            feedback_thermometer = self.ls350inputs[self.measurementSettings['sample Input']]
        elif self.measurementSettings['feedback thermometer'] == 3:
            feedback_thermometer = self.ls350inputs[self.measurementSettings['pot Input']]
        
        if self.measurementSettings['heater mode'] == 0:
            yield self.ls.out_mode_set(self.measurementSettings['heater output'], 1, feedback_thermometer, 0)
        elif self.measurementSettings['heater mode'] == 1:
            yield self.ls.out_mode_set(self.measurementSettings['heater output'], 3, feedback_thermometer, 0)
            
        if str(self.push_heater.text()) == 'Heater On':
            yield self.ls.range_set(self.measurementSettings['heater output'], self.measurementSettings['heater range'])
            
    @inlineCallbacks
    def startTempMonitoring(self, c = None):
        try:
            self.monitoring = True
            if self.first_data_point:
                self.time_offset = time.clock()
                self.first_data_point = False

            while self.monitoring:
                magTemp = yield self.ls.read_temp(self.measurementSettings['mag Input'])
                sampleTemp = yield self.ls.read_temp(self.measurementSettings['sample Input'])
                #potTemp =  yield self.ls.read_temp(self.measurementSettings['pot Input'])
                t = time.clock() - self.time_offset
                #Convert time to hours
                t = t / 3600
                
                self.magTempData = np.append(self.magTempData, float(magTemp))
                self.sampleTempData = np.append(self.sampleTempData, float(sampleTemp))
                #self.potTempData = np.append(self.potTempData, float(potTemp))
                self.timeData = np.append(self.timeData, float(t))
                
                self.lcdNumber_magTemp.display(float(magTemp))
                self.lcdNumber_sampleTemp.display(float(sampleTemp))
                #self.lcdNumber_potTemp.display(float(potTemp))
                
                self.updatePlots()
                
                yield self.sleep(self.measurementSettings['sample delay'])
        except Exception as inst:
            print(inst, sys.exc_traceback.tb_lineno)
            
    def updatePlots(self):
        try:
            length = len(self.timeData)
            if length > 1:
                if (self.timeData[length-1] - self.timeData[0]) <= self.measurementSettings['plot record']:
                    self.magTempPlot.clear()
                    self.magTempPlot.plot(self.timeData, self.magTempData)
                    self.sampleTempPlot.clear()
                    self.sampleTempPlot.plot(self.timeData, self.sampleTempData)
                    #self.potTempPlot.clear()
                    #self.potTempPlot.plot(self.timeData, self.potTempData)
                else:
                    a = np.argmin(np.abs(self.timeData - (self.timeData[length-1] - self.measurementSettings['plot record'])))
                    self.magTempPlot.clear()
                    self.magTempPlot.plot(self.timeData[a:], self.magTempData[a:])
                    self.sampleTempPlot.clear()
                    self.sampleTempPlot.plot(self.timeData[a:], self.sampleTempData[a:])
                    #self.potTempPlot.clear()
                    #self.potTempPlot.plot(self.timeData[a:], self.potTempData[a:])
        except Exception as inst:
            print(inst, sys.exc_traceback.tb_lineno)
            
    @inlineCallbacks
    def toggleHeater(self):
        if str(self.push_heater.text()) == 'Heater Off':
            yield self.ls.range_set(self.measurementSettings['heater output'], self.measurementSettings['heater range'])
            yield self.sleep(0.25)
            range = yield self.ls.range_read(self.measurementSettings['heater output'])
            
            #If closed loop operation, turn off the manual heater contribution
            if self.measurementSettings['heater mode'] == 0:
                yield self.ls.gpib_write('MOUT%i,%f'%(self.measurementSettings['heater output'],0.0))
            elif self.measurementSettings['heater mode'] == 1:
                yield self.ls.gpib_write('MOUT%i,%f'%(self.measurementSettings['heater output'],self.measurementSettings['out percent']))
            
            if range != 0:
                self.push_heater.setText('Heater On')
        else:
            yield self.ls.range_set(self.measurementSettings['heater output'], 0)
            self.push_heater.setText('Heater Off')
            
    @inlineCallbacks
    def setSetpoint(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_setpoint.text()), self, False)
        if isinstance(val,float):
            if self.measurementSettings['heater mode'] == 0:
                self.measurementSettings['setpoint'] = val
                yield self.ls.setpoint(self.measurementSettings['heater output'], self.measurementSettings['setpoint'])
            elif self.measurementSettings['heater mode'] == 1:
                self.measurementSettings['out percent'] = val
                yield self.ls.gpib_write('MOUT%i,%f'%(self.measurementSettings['heater output'],self.measurementSettings['out percent']))
        if self.measurementSettings['heater mode'] == 0:
            self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['setpoint']))
        elif self.measurementSettings['heater mode'] == 1:
            self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['out percent']))
            
    def setTherm1PlotTitle(self):
        text = str(self.lineEdit_therm1.text())
        self.magTempPlot.setTitle(text + ' vs. Time')
        
    def setTherm2PlotTitle(self):
        text = str(self.lineEdit_therm2.text())
        self.sampleTempPlot.setTitle(text + ' vs. Time')
        
    def setTherm3PlotTitle(self):
        text = str(self.lineEdit_therm3.text())
        self.potTempPlot.setTitle(text + ' vs. Time')
        
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()

    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous 
    # delay that allows other labrad / pyqt methods to run   
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""
    
    @inlineCallbacks
    def readTherm1(self):
        magTemp = yield self.ls.read_temp(self.measurementSettings['mag Input'])
        returnValue(magTemp)
        
    @inlineCallbacks
    def readTherm2(self):
        sampleTemp = yield self.ls.read_temp(self.measurementSettings['sample Input'])
        returnValue(sampleTemp)
        
    @inlineCallbacks
    def readTherm3(self):
        potTemp = yield self.ls.read_temp(self.measurementSettings['pot Input'])
        returnValue(potTemp)
        
    @inlineCallbacks
    def setFeedbackThermometer(self, ind):
        self.measurementSettings['feedback thermometer'] = ind
        yield self.setOutputSettings()
                
    @inlineCallbacks
    def setHeaterMode(self, mode):
        self.measurementSettings['heater mode'] = mode
        
        if self.measurementSettings['heater mode'] == 0:
            self.label_setpoint.setText('Setpoint (K):')
            self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['setpoint']))
        elif self.measurementSettings['heater mode'] == 1:
            self.label_setpoint.setText('Output (%):')
            self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['out percent']))
        else:
            self.label_setpoint.setText('WTF?!?!')
            
        yield self.setOutputSettings()
        
    @inlineCallbacks
    def setHeaterOutput(self, output):
        self.measurementSettings['heater output'] = output
        yield self.ls.pid_set(self.measurementSettings['heater output'],self.measurementSettings['p'],self.measurementSettings['i'],self.measurementSettings['d'])
        yield self.setOutputSettings()
        
    @inlineCallbacks
    def setHeaterPID(self, p, i , d):
        self.measurementSettings['p'] = p
        self.measurementSettings['i'] = i
        self.measurementSettings['d'] = d
        yield self.ls.pid_set(self.measurementSettings['heater output'],self.measurementSettings['p'],self.measurementSettings['i'],self.measurementSettings['d'])
        
    @inlineCallbacks
    def setHeaterRange(self, rang):
        self.measurementSettings['heater range'] = rang
        if str(self.push_heater.text()) == 'Heater On':
                    yield self.ls.range_set(self.measurementSettings['heater output'], self.measurementSettings['heater range'])
    
    @inlineCallbacks
    def setHeaterSetpoint(self, setpoint):
        self.measurementSettings['setpoint'] = setpoint
        if self.measurementSettings['heater mode'] == 0:
            self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['setpoint']))
        yield self.ls.setpoint(self.measurementSettings['heater output'], self.measurementSettings['setpoint'])
        
    @inlineCallbacks
    def setHeaterPercentage(self, percent):
        self.measurementSettings['out percent'] = percent
        if self.measurementSettings['heater mode'] == 1:
            self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['out percent']))
        yield self.ls.gpib_write('MOUT%i,%f'%(self.measurementSettings['heater output'],self.measurementSettings['out percent']))
        
    @inlineCallbacks
    def setHeaterOn(self):
        if str(self.push_heater.text()) == 'Heater Off':
            yield self.toggleHeater()
    
    @inlineCallbacks
    def setHeaterOff(self):
        if str(self.push_heater.text()) == 'Heater On':
            yield self.toggleHeater()
    
#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""
           
    def lockInterface(self):
        self.push_Settings.setEnabled(False)
        self.push_heater.setEnabled(False)
        
        self.lineEdit_setpoint.setEnabled(False)
        
    def unlockInterface(self):
        self.push_Settings.setEnabled(True)
        self.push_heater.setEnabled(True)
        
        self.lineEdit_setpoint.setEnabled(True)
        
class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        

class MeasurementSettings(QtWidgets.QDialog, Ui_MeasurementSettings):
    def __init__(self,reactor, measSettings, parent = None):
        super(MeasurementSettings, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        
        self.measurementSettings = measSettings
        
        self.loadValues()
        
        self.pushButton.clicked.connect(self.accept)
        
        self.comboBox_MagInput.currentIndexChanged.connect(self.updateMagInput)
        self.comboBox_sampInput.currentIndexChanged.connect(self.updateSampleInput)
        self.comboBox_potInput.currentIndexChanged.connect(self.updatePotInput)
        self.comboBox_heaterMode.currentIndexChanged.connect(self.updateHeaterMode)
        
        self.lineEdit_D.editingFinished.connect(self.updateD)
        self.lineEdit_I.editingFinished.connect(self.updateI)
        self.lineEdit_P.editingFinished.connect(self.updateP)
        
        self.lineEdit_time.editingFinished.connect(self.updateTime)
        self.lineEdit_delay.editingFinished.connect(self.updateDelay)
        
        self.radioButton_heat1.toggled.connect(self.setHeater)
        self.radioButton_heat2.toggled.connect(self.setHeater)
        
        self.radioButton_1.toggled.connect(self.setHeaterRange)
        self.radioButton_2.toggled.connect(self.setHeaterRange)
        self.radioButton_3.toggled.connect(self.setHeaterRange)
        self.radioButton_4.toggled.connect(self.setHeaterRange)
        self.radioButton_5.toggled.connect(self.setHeaterRange)
        
        self.radioButton_fdbk1.toggled.connect(self.setFdbkThermometer)
        self.radioButton_fdbk2.toggled.connect(self.setFdbkThermometer)
        self.radioButton_fdbk3.toggled.connect(self.setFdbkThermometer)
        
    def setupAdditionalUi(self):
        pass
        
    def loadValues(self):
        try:
            self.lineEdit_P.setText(formatNum(self.measurementSettings['p']))
            self.lineEdit_I.setText(formatNum(self.measurementSettings['i']))
            self.lineEdit_D.setText(formatNum(self.measurementSettings['d']))
            
            self.lineEdit_time.setText(formatNum(self.measurementSettings['plot record']))
            self.lineEdit_delay.setText(formatNum(self.measurementSettings['sample delay']))
            
            if self.measurementSettings['mag Input'] == 'A':
                self.comboBox_MagInput.setCurrentIndex(0)
            elif self.measurementSettings['mag Input'] == 'B':
                self.comboBox_MagInput.setCurrentIndex(1)
            elif self.measurementSettings['mag Input'] == 'C':
                self.comboBox_MagInput.setCurrentIndex(2)
            elif self.measurementSettings['mag Input'] == 'D1':
                self.comboBox_MagInput.setCurrentIndex(3)
            elif self.measurementSettings['mag Input'] == 'D2':
                self.comboBox_MagInput.setCurrentIndex(4)
            elif self.measurementSettings['mag Input'] == 'D3':
                self.comboBox_MagInput.setCurrentIndex(5)
            elif self.measurementSettings['mag Input'] == 'D4':
                self.comboBox_MagInput.setCurrentIndex(6)
            elif self.measurementSettings['mag Input'] == 'D5':
                self.comboBox_MagInput.setCurrentIndex(7)
                
            if self.measurementSettings['sample Input'] == 'A':
                self.comboBox_sampInput.setCurrentIndex(0)
            elif self.measurementSettings['sample Input'] == 'B':
                self.comboBox_sampInput.setCurrentIndex(1)
            elif self.measurementSettings['sample Input'] == 'C':
                self.comboBox_sampInput.setCurrentIndex(2)
            elif self.measurementSettings['sample Input'] == 'D1':
                self.comboBox_sampInput.setCurrentIndex(3)
            elif self.measurementSettings['sample Input'] == 'D2':
                self.comboBox_sampInput.setCurrentIndex(4)
            elif self.measurementSettings['sample Input'] == 'D3':
                self.comboBox_sampInput.setCurrentIndex(5)
            elif self.measurementSettings['sample Input'] == 'D4':
                self.comboBox_sampInput.setCurrentIndex(6)
            elif self.measurementSettings['sample Input'] == 'D5':
                self.comboBox_sampInput.setCurrentIndex(7)
                
            if self.measurementSettings['pot Input'] == 'A':
                self.comboBox_potInput.setCurrentIndex(0)
            elif self.measurementSettings['pot Input'] == 'B':
                self.comboBox_potInput.setCurrentIndex(1)
            elif self.measurementSettings['pot Input'] == 'C':
                self.comboBox_potInput.setCurrentIndex(2)
            elif self.measurementSettings['pot Input'] == 'D1':
                self.comboBox_potInput.setCurrentIndex(3)
            elif self.measurementSettings['pot Input'] == 'D2':
                self.comboBox_potInput.setCurrentIndex(4)
            elif self.measurementSettings['pot Input'] == 'D3':
                self.comboBox_potInput.setCurrentIndex(5)
            elif self.measurementSettings['pot Input'] == 'D4':
                self.comboBox_potInput.setCurrentIndex(6)
            elif self.measurementSettings['pot Input'] == 'D5':
                self.comboBox_potInput.setCurrentIndex(7)
                
            if self.measurementSettings['heater range'] == 1:
                self.radioButton_1.setChecked(True)
            elif self.measurementSettings['heater range'] == 2:
                self.radioButton_2.setChecked(True)
            elif self.measurementSettings['heater range'] == 3:
                self.radioButton_3.setChecked(True)
            elif self.measurementSettings['heater range'] == 4:
                self.radioButton_4.setChecked(True)
            elif self.measurementSettings['heater range'] == 5:
                self.radioButton_5.setChecked(True)
                
            if self.measurementSettings['heater output'] == 1:
                self.radioButton_heat1.setChecked(True)
            else:
                self.radioButton_heat2.setChecked(True)
                
            if self.measurementSettings['feedback thermometer'] == 1:
                self.radioButton_fdbk1.setChecked(True)
            elif self.measurementSettings['feedback thermometer'] == 2:
                self.radioButton_fdbk2.setChecked(True)
            elif self.measurementSettings['feedback thermometer'] == 3:
                self.radioButton_fdbk3.setChecked(True)
                
            self.comboBox_heaterMode.setCurrentIndex(self.measurementSettings['heater mode'])
            
        except Exception as inst:
            print(inst, sys.exc_traceback.tb_lineno)
            
    def updateMagInput(self):
        if self.comboBox_MagInput.currentIndex() ==0:
            self.measurementSettings['mag Input'] = 'A'
        elif self.comboBox_MagInput.currentIndex() == 1:
            self.measurementSettings['mag Input'] = 'B'
        elif self.comboBox_MagInput.currentIndex() == 2:
            self.measurementSettings['mag Input'] = 'C'
        elif self.comboBox_MagInput.currentIndex() == 3:
            self.measurementSettings['mag Input'] = 'D1'
        elif self.comboBox_MagInput.currentIndex() == 4:
            self.measurementSettings['mag Input'] = 'D2'
        elif self.comboBox_MagInput.currentIndex() == 5:
            self.measurementSettings['mag Input'] = 'D3'
        elif self.comboBox_MagInput.currentIndex() == 6:
            self.measurementSettings['mag Input'] = 'D4'
        elif self.comboBox_MagInput.currentIndex() == 7:
            self.measurementSettings['mag Input'] = 'D5'

    def updateSampleInput(self):
        if self.comboBox_sampInput.currentIndex() ==0:
            self.measurementSettings['sample Input'] = 'A'
        elif self.comboBox_sampInput.currentIndex() == 1:
            self.measurementSettings['sample Input'] = 'B'
        elif self.comboBox_sampInput.currentIndex() == 2:
            self.measurementSettings['sample Input'] = 'C'
        elif self.comboBox_sampInput.currentIndex() == 3:
            self.measurementSettings['sample Input'] = 'D1'
        elif self.comboBox_sampInput.currentIndex() == 4:
            self.measurementSettings['sample Input'] = 'D2'
        elif self.comboBox_sampInput.currentIndex() == 5:
            self.measurementSettings['sample Input'] = 'D3'
        elif self.comboBox_sampInput.currentIndex() == 6:
            self.measurementSettings['sample Input'] = 'D4'
        elif self.comboBox_sampInput.currentIndex() == 7:
            self.measurementSettings['sample Input'] = 'D5'
            
    def updatePotInput(self):
        if self.comboBox_potInput.currentIndex() ==0:
            self.measurementSettings['pot Input'] = 'A'
        elif self.comboBox_potInput.currentIndex() == 1:
            self.measurementSettings['pot Input'] = 'B'
        elif self.comboBox_potInput.currentIndex() == 2:
            self.measurementSettings['pot Input'] = 'C'
        elif self.comboBox_potInput.currentIndex() == 3:
            self.measurementSettings['pot Input'] = 'D1'
        elif self.comboBox_potInput.currentIndex() == 4:
            self.measurementSettings['pot Input'] = 'D2'
        elif self.comboBox_potInput.currentIndex() == 5:
            self.measurementSettings['pot Input'] = 'D3'
        elif self.comboBox_potInput.currentIndex() == 6:
            self.measurementSettings['pot Input'] = 'D4'
        elif self.comboBox_potInput.currentIndex() == 7:
            self.measurementSettings['pot Input'] = 'D5'
            
    def updateHeaterMode(self):
        self.measurementSettings['heater mode'] = self.comboBox_heaterMode.currentIndex()
            
    def updateP(self):
        val = readNum(str(self.lineEdit_P.text()), self, False)
        if isinstance(val,float):
            self.measurementSettings['p'] = val
        self.lineEdit_P.setText(formatNum(self.measurementSettings['p']))
    
    def updateD(self):
        val = readNum(str(self.lineEdit_D.text()), self, False)
        if isinstance(val,float):
            self.measurementSettings['d'] = val
        self.lineEdit_D.setText(formatNum(self.measurementSettings['d']))
    
    def updateI(self):
        val = readNum(str(self.lineEdit_I.text()), self, False)
        if isinstance(val,float):
            self.measurementSettings['i'] = val
        self.lineEdit_I.setText(formatNum(self.measurementSettings['i']))
        
    def updateTime(self):
        val = readNum(str(self.lineEdit_time.text()), self, False)
        if isinstance(val,float):
            self.measurementSettings['plot record'] = val
        self.lineEdit_time.setText(formatNum(self.measurementSettings['plot record']))
        
    def updateDelay(self):
        val = readNum(str(self.lineEdit_delay.text()), self, False)
        if isinstance(val,float):
            self.measurementSettings['sample delay'] = val
        self.lineEdit_delay.setText(formatNum(self.measurementSettings['sample delay']))
        
    def setHeater(self):
        if self.radioButton_heat1.isChecked():
            self.measurementSettings['heater output'] = 1
        else:
            self.measurementSettings['heater output'] = 2
            
    def setHeaterRange(self):
        if self.radioButton_1.isChecked():
            self.measurementSettings['heater range'] = 1
        elif self.radioButton_2.isChecked():
            self.measurementSettings['heater range'] = 2
        elif self.radioButton_3.isChecked():
            self.measurementSettings['heater range'] = 3
        elif self.radioButton_4.isChecked():
            self.measurementSettings['heater range'] = 4
        elif self.radioButton_5.isChecked():
            self.measurementSettings['heater range'] = 5
            
    def setFdbkThermometer(self):
        if self.radioButton_fdbk1.isChecked():
            self.measurementSettings['feedback thermometer'] = 1
        elif self.radioButton_fdbk2.isChecked():
            self.measurementSettings['feedback thermometer'] = 2
        elif self.radioButton_fdbk3.isChecked():
            self.measurementSettings['feedback thermometer'] = 3
            
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
    def acceptNewValues(self):
        self.accept()
        
    def getValues(self):
        return self.measurementSettings