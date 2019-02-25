import sys
from PyQt4 import QtGui, QtCore, uic
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

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()
        
        self.push_Settings.clicked.connect(self.updateSettings)
        self.push_heater.clicked.connect(self.toggleHeater)

        self.lineEdit_setpoint.editingFinished.connect(self.setSetpoint)
        
        self.time_offset = 0
        self.timeData = np.array([])
        self.magTempData = np.array([])
        self.sampleTempData = np.array([])
        
        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize all the labrad connections as False
        self.cxn = False
        self.ls = False
        
        #Keep track of if the first monitoring datapoint has been taken yet, to set the relative time
        self.first_data_point = True
        
        self.measurementSettings = {
                'mag Input'        : 'B',
                'sample Input'     : 'D5', 
                'p'                : 50.0,
                'i'                : 50.0,
                'd'                : 1.0,       #
                'setpoint'         : 4.0,       #Setpoint in Kelvin
                'heater range'     : 3,         #Range for the heater
                'heater output'    : 1, 
                'plot record'      : 1,         #plot length shown in hours
                'sample delay'     : 1,         #Delay between temperature samples
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
            print inst, sys.exc_traceback.tb_lineno
            
            
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
        self.magTempPlot.setLabel('left', 'Temperature', units = 'V')
        self.magTempPlot.setLabel('bottom', 'Time', units = 'h')
        self.magTempPlot.showAxis('right', show = True)
        self.magTempPlot.showAxis('top', show = True)
        self.magTempPlot.setTitle('Magnet Temperature vs. Time')
        
        self.sampleTempFrame.close()
        self.sampleTempPlot = pg.PlotWidget(parent = self)
        self.sampleTempPlot.setLabel('left', 'Temperature', units = 'V')
        self.sampleTempPlot.setLabel('bottom', 'Time', units = 'h')
        self.sampleTempPlot.showAxis('right', show = True)
        self.sampleTempPlot.showAxis('top', show = True)
        self.sampleTempPlot.setTitle('Sample Temperature vs. Time')
        
        self.horizontalLayout_2.addWidget(self.magTempPlot)
        self.horizontalLayout_2.addWidget(self.sampleTempPlot)
        
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
            self.measurementSettings['setpoint'] = setpoint
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno

    @inlineCallbacks
    def updateSettings(self, c = None):
        try:
            MeasSet = MeasurementSettings(self.reactor, self.measurementSettings, parent = self)
            if MeasSet.exec_():
                self.measurementSettings = MeasSet.getValues()
                print self.measurementSettings
                
                #Set pid settings
                yield self.ls.pid_set(self.measurementSettings['heater output'],self.measurementSettings['p'],self.measurementSettings['p'],self.measurementSettings['d'])
                #set the new pid settings and heater range and stuff 
                yield self.ls.range_set(self.measurementSettings['heater output'], self.measurementSettings['heater range'])
                
                #In case record time has changed, update plots to reflect that
                self.updatePlots()
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
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
                t = time.clock() - self.time_offset
                #Convert time to hours
                t = t / 3600
                
                self.magTempData = np.append(self.magTempData, float(magTemp))
                self.sampleTempData = np.append(self.sampleTempData, float(sampleTemp))
                self.timeData = np.append(self.timeData, float(t))
                
                self.lcdNumber_magTemp.display(float(magTemp))
                self.lcdNumber_sampleTemp.display(float(sampleTemp))
                
                self.updatePlots()
                
                yield self.sleep(self.measurementSettings['sample delay'])
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
    def updatePlots(self):
        try:
            length = len(self.timeData)
            if length > 1:
                if (self.timeData[length-1] - self.timeData[0]) <= self.measurementSettings['plot record']:
                    self.magTempPlot.clear()
                    self.magTempPlot.plot(self.timeData, self.magTempData)
                    self.sampleTempPlot.clear()
                    self.sampleTempPlot.plot(self.timeData, self.sampleTempData)
                else:
                    a = np.argmin(np.abs(self.timeData - (self.timeData[length-1] - self.measurementSettings['plot record'])))
                    self.magTempPlot.clear()
                    self.magTempPlot.plot(self.timeData[a:], self.magTempData[a:])
                    self.sampleTempPlot.clear()
                    self.sampleTempPlot.plot(self.timeData[a:], self.sampleTempData[a:])
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
    @inlineCallbacks
    def toggleHeater(self, c = None):
        if str(self.push_heater.text()) == 'Heater Off':
            yield self.ls.range_set(self.measurementSettings['heater output'], self.measurementSettings['heater range'])
            yield self.sleep(0.25)
            range = yield self.ls.range_read(self.measurementSettings['heater output'])
            if range != 0:
                self.push_heater.setText('Heater On')
        else:
            yield self.ls.range_set(self.measurementSettings['heater output'], 0)
            self.push_heater.setText('Heater Off')
            
    @inlineCallbacks
    def setSetpoint(self, c = None):
        val = readNum(str(self.lineEdit_setpoint.text()), self, False)
        if isinstance(val,float):
            self.measurementSettings['setpoint'] = val
            yield self.ls.setpoint(self.measurementSettings['heater output'], self.measurementSettings['setpoint'])
        self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['setpoint']))
        
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
    """ The following section has generally useful functions."""
           
    def lockInterface(self):
        self.push_Settings.setEnabled(False)
        self.push_heater.setEnabled(False)
        
        self.lineEdit_setpoint.setEnabled(False)
        
    def unlockInterface(self):
        self.push_Settings.setEnabled(True)
        self.push_heater.setEnabled(True)
        
        self.lineEdit_setpoint.setEnabled(True)
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        

class MeasurementSettings(QtGui.QDialog, Ui_MeasurementSettings):
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
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
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