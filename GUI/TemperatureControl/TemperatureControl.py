import sys
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QRect
from PyQt5.QtCore import Qt
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import time
import pyqtgraph as pg
import copy
import numpy as np
from datetime import datetime
from nSOTScannerFormat import readNum, formatNum, printErrorInfo

path = sys.path[0] + r"\TemperatureControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\TempControl_v2.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_MeasurementSettings, QtBaseClass = uic.loadUiType(path + r"\MeasurementSettings.ui")
Ui_ThermoWidget, QtBaseClass = uic.loadUiType(path + r"\temp-widget.ui")
Ui_LoopWidget, QtBaseClass = uic.loadUiType(path + r"\loop_widget.ui")

class ThermometerWidget(QtWidgets.QWidget, Ui_ThermoWidget):
    def __init__(self, reactor, reference, parent=None):
        super(ThermometerWidget, self).__init__(parent)
        self.setupUi(self)
        self.reference = reference
        self.reactor = reactor
        
class LoopWidget(QtWidgets.QWidget, Ui_LoopWidget):
    def __init__(self, reactor, index, parent=None):
        super(LoopWidget, self).__init__(parent)
        self.setupUi(self)
        self.index = index # Either loop 1 or loop 2
        self.label_title.setText("Loop " + str(index))
        self.reactor = reactor
        self.ls = False
        self.loopSettings = {
            'p'                : 50.0,
            'i'                : 50.0,
            'd'                : 1.0,       #
            'setpoint'         : 4.0,       #Setpoint in Kelvin for closed loop (PID) operation
            'out percent'      : 0,         #Pencentage output for open loop / manual mode
            'feedback thermometer' : 1,     #Which thermometer should be used for closed loop heating
            'heater range'     : 1,         #Range for the heater
            'heater mode'      : 0,         #0 is closed loop, ie using PID. 1 is open loop, using manual setting mode.
        }
        
        # self.push_Settings.clicked.connect(lambda: self.updateSettings())
        self.push_heater.clicked.connect(lambda: self.toggleHeater())
        self.lineEdit_setpoint.editingFinished.connect(self.setSetpoint)
        
        self.lineEdit_P.editingFinished.connect(self.updatePID)
        self.lineEdit_I.editingFinished.connect(self.updatePID)
        self.lineEdit_D.editingFinished.connect(self.updatePID)
        
        self.range_combo.currentTextChanged.connect(self.setRange)
        self.thermo_comboBox.currentTextChanged.connect(self.setFeedbackThermometer)
        self.comboBox_heaterMode.currentTextChanged.connect(self.setHeaterMode)
    
    @inlineCallbacks
    def connectLabRAD(self, ls):
        self.ls = ls
        yield self.readCurrentSettings()
    
    def disconnectLabRAD(self):
        self.ls = False
    
    def setThermometers(self, thermometerDict):
        self.thermometers = thermometerDict
        for k in self.thermometers.keys():
            self.thermo_comboBox.addItem(k)
    
    @inlineCallbacks
    def readCurrentSettings(self): 
        try:
            range = yield self.ls.range_read(self.index)
            if range !=0:
                self.loopSettings['heater range'] = range
                self.push_heater.setText('Heater Off')
                self.status_label.setText('Active')
                self.status_label.setStyleSheet("#status_label{color: rgb(13, 192, 13);}")
                self.thermo_comboBox.setEnabled(False)
                self.comboBox_heaterMode.setEnabled(False)

            pid = yield self.ls.pid_read(self.index)
            pid = pid.split(',')
            setpoint = yield self.ls.setpoint_read(self.index)

            self.lineEdit_setpoint.setText(formatNum(float(setpoint)))
            self.loopSettings['p'] = float(pid[0])
            self.lineEdit_P.setText(formatNum(self.loopSettings['p']))
            self.loopSettings['i'] = float(pid[1])
            self.lineEdit_I.setText(formatNum(self.loopSettings['i']))
            self.loopSettings['d'] = float(pid[2])
            self.lineEdit_D.setText(formatNum(self.loopSettings['d']))
            self.loopSettings['setpoint'] = float(setpoint)
            self.lineEdit_setpoint.setText(formatNum(self.loopSettings['setpoint']))
            
            outmode = yield self.ls.out_mode_read(self.index)
            outmode = outmode.split(',')
            if outmode[0] == '3':
                self.loopSettings['heater mode'] = 1
                index = self.comboBox_heaterMode.findText("Open Loop (Manual)", Qt.MatchFixedString)
                if index >= 0:
                     self.comboBox_heaterMode.setCurrentIndex(index)
            if outmode[1] == '1':
                thermo = "A"
            elif outmode[1] == '2':
                thermo = "B"
            elif outmode[1] == '3':
                thermo = "C"
            elif outmode[1] == '4':
                thermo = "D"
            elif outmode[1] == '5':
                thermo = "D2"
            elif outmode[1] == '6':
                thermo = "D3"
            elif outmode[1] == '7':
                thermo = "D4"
            elif outmode[1] == '8':
                thermo = "D5"
            else:
                print("Warning Invalid Thermometer from Lakeshore", outmode)
                thermo = "WTF"
            for k,v in self.thermometers.items():
                if v == thermo:
                    index = self.thermo_comboBox.findText(k, Qt.MatchFixedString)
                    if index >= 0:
                         self.thermo_comboBox.setCurrentIndex(index)
        except:
            printErrorInfo()

    @inlineCallbacks
    def setRange(self, value):
        if value == "Low":
            self.loopSettings['heater range'] = 1
        elif value == "Medium":
            self.loopSettings['heater range'] = 2
        elif value == "High":
            self.loopSettings['heater range'] = 3
        else:
            print("setRange Invalid entry")
            return
        
        if self.status_label.text() == "Active":
            yield self.ls.range_set(self.index, self.loopSettings['heater range'])
            yield self.sleep(0.5) # There's a short delay when setting the heater
    
    @inlineCallbacks
    def setHeaterMode(self, value):
        outmode = yield self.ls.out_mode_read(self.index)
        outmode = outmode.split(',')
        if value == "Open Loop (Manual)":
            self.loopSettings['heater mode'] = 1
            yield self.ls.out_mode_set(self.index, 3, int(outmode[1]), 0)
            self.label_setpoint.setText("Output (%):")
            self.lineEdit_setpoint.setText(formatNum(self.loopSettings['out percent']))
        else:
            self.loopSettings['heater mode'] = 0
            yield self.ls.out_mode_set(self.index, 1, int(outmode[1]), 0)
            self.label_setpoint.setText("Setpoint (K):")
            self.lineEdit_setpoint.setText(formatNum(self.loopSettings['setpoint']))
            yield self.ls.write('MOUT%i,%f'%(self.index,0.0))
    
    @inlineCallbacks
    def setFeedbackThermometer(self, value):
        if self.ls == False:
            return
        if value in self.thermometers:
            thermometer = self.thermometers[value]
            if thermometer == "A":
                thermo = 1
            elif thermometer == "B":
                thermo = 2
            elif thermometer == "C":
                thermo = 3
            elif thermometer == "D":
                thermo = 4
            elif thermometer == "D2":
                thermo = 5
            elif thermometer == "D3":
                thermo = 6
            elif thermometer == "D4":
                thermo = 7
            elif thermometer == "D5":
                thermo = 8
            else:
                print("Error Invalid Thermometer Selected for Feedback")
                return
            if self.loopSettings['heater mode'] == 0:
                yield self.ls.out_mode_set(self.index, 1, thermo, 0)
            elif self.loopSettings['heater mode'] == 1:
                yield self.ls.out_mode_set(self.index, 3, thermo, 0)
        else:
            print("setFeedbackThermometer Invalid entry")
    
    @inlineCallbacks
    def updatePID(self):
        P = readNum(str(self.lineEdit_P.text()))
        if isinstance(P,float):
            self.loopSettings['p'] = P
        self.lineEdit_P.setText(formatNum(self.loopSettings['p']))
        I = readNum(str(self.lineEdit_I.text()))
        if isinstance(I,float):
            self.loopSettings['i'] = I
        self.lineEdit_I.setText(formatNum(self.loopSettings['i']))
        D = readNum(str(self.lineEdit_D.text()))
        if isinstance(D,float):
            self.loopSettings['d'] = D
        self.lineEdit_D.setText(formatNum(self.loopSettings['d']))
        
        yield self.ls.pid_set(self.index,self.loopSettings['p'],self.loopSettings['i'],self.loopSettings['d'])
    
    @inlineCallbacks
    def toggleHeater(self):
        if str(self.push_heater.text()) == 'Heater On':
            yield self.heaterOn()
        else:
            yield self.heaterOff()
    
    @inlineCallbacks
    def heaterOn(self):
        #If closed loop operation, turn off the manual heater contribution
        if self.loopSettings['heater mode'] == 0:
            yield self.ls.write('MOUT%i,%f'%(self.index,0.0))
        elif self.loopSettings['heater mode'] == 1:
            yield self.ls.write('MOUT%i,%f'%(self.index,self.loopSettings['out percent']))
        yield self.sleep(1) # There's a short delay when setting the heater
        
        yield self.ls.range_set(self.index, self.loopSettings['heater range'])
        yield self.sleep(1) # There's a short delay when setting the heater

        self.push_heater.setText('Heater Off')
        self.status_label.setText('Active')
        self.status_label.setStyleSheet("#status_label{color: rgb(13, 192, 13);}")
        self.thermo_comboBox.setEnabled(False)
        self.comboBox_heaterMode.setEnabled(False)
    
    @inlineCallbacks
    def heaterOff(self):
        if self.loopSettings['heater mode'] == 1:
            yield self.ls.write('MOUT%i,%f'%(self.index,0.0))
            yield self.sleep(1) # There's a short delay when setting the heater
        yield self.ls.range_set(self.index, 0)
        yield self.sleep(1) # There's a short delay when setting the heater
        
        self.push_heater.setText('Heater On')
        self.status_label.setText('Off')
        self.status_label.setStyleSheet("#status_label{color: rgb(144, 140, 9);}")
        self.thermo_comboBox.setEnabled(True)
        self.comboBox_heaterMode.setEnabled(True)

    @inlineCallbacks
    def setSetpoint(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_setpoint.text()))
        if isinstance(val,float):
            if self.loopSettings['heater mode'] == 0:
                self.loopSettings['setpoint'] = val
                yield self.ls.setpoint(self.index, self.loopSettings['setpoint'])
            elif self.loopSettings['heater mode'] == 1:
                self.loopSettings['out percent'] = val
                yield self.ls.write('MOUT%i,%f'%(self.index,self.loopSettings['out percent']))
        if self.loopSettings['heater mode'] == 0:
            self.lineEdit_setpoint.setText(formatNum(self.loopSettings['setpoint']))
        elif self.loopSettings['heater mode'] == 1:
            self.lineEdit_setpoint.setText(formatNum(self.loopSettings['out percent']))
    
    def lockInterface(self):
        self.push_heater.setEnabled(False)
        self.lineEdit_setpoint.setEnabled(False)

    def unlockInterface(self):
        self.push_heater.setEnabled(True)
        self.lineEdit_setpoint.setEnabled(True)

    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous
    # delay that allows other labrad / pyqt methods to run
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class Window(QtWidgets.QMainWindow, ScanControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()

        self.lineEdit_time.editingFinished.connect(self.updateTime)
        self.lineEdit_delay.editingFinished.connect(self.updateDelay)

        self.time_offset = 0
        self.timeData = np.array([])

        #Connect show servers list pop up
        self.push_all_off.clicked.connect(self.allOff)
        self.push_Servers.clicked.connect(self.showServersList)

        #Initialize all the labrad connections as False
        self.cxn = False
        self.ls = False

        #Keep track of if the first monitoring datapoint has been taken yet, to set the relative time
        self.first_data_point = True

        self.measurementSettings = {
            'plot record'      : 1,         #plot length shown in hours
            'sample delay'     : 1,         #Delay between temperature samples, seconds
        }
        self.lineEdit_time.setText(formatNum(self.measurementSettings['plot record']))
        self.lineEdit_delay.setText(formatNum(self.measurementSettings['sample delay']))

        self.lockInterface()

    def moveDefault(self):
        self.move(550,10)

    @inlineCallbacks
    def connectLabRAD(self, equip):
        try:
            # The Lakeshore 350 and 336 are functionally equivalent for our purposes
            if "LS 350" in equip.servers:
                svr, ln, device_info, cnt, config = equip.servers['LS 350']
            elif "LS 336" in equip.servers:
                svr, ln, device_info, cnt, config = equip.servers['LS 336']
            else:
                print("Lakeshore not found, no LabRAD connections made.")
                return
            
            self.ls = svr
            self.dv = yield equip.get_datavault()
            self.time_offset = equip.sync_time # Sync the temperature time to other loops

            for widget in self.loopWidgets:
                widget.connectLabRAD(svr)

            if not self.ls:
                self.push_Servers.setStyleSheet("#push_Servers{" +
                "background: rgb(161, 0, 0);border-radius: 4px;border: 0px;}")
            else:
                self.push_Servers.setStyleSheet("#push_Servers{" +
                    "background: rgb(0, 170, 0);border-radius: 4px;border: 0px;}")
                self.unlockInterface()
                yield self.startTempMonitoring()
        except:
            from traceback import print_exc
            print_exc()
            #printErrorInfo()

    def disconnectLabRAD(self):
        self.monitoring = False
        self.cxn = False
        self.ls = False
        for widget in self.loopWidgets:
            widget.disconnectLabRAD()
        self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;border: 0px;}")

    def setupAdditionalUi(self):
        self.loopWidgets = []
        self.loopWidgets.append(LoopWidget(self.reactor, 1, self.loop_1_frame))
        self.loopWidgets.append(LoopWidget(self.reactor, 2, self.loop_2_frame))
        
        # Here for easy access in scripting module
        self.loop1 = self.loopWidgets[0]
        self.loop2 = self.loopWidgets[1]

    def setupTemperatureUi(self, equip):
        #Set up UI that isn't easily done from Qt Designer
        #self.push_Settings.hide() # Legacy configuration manaag
        if "LS 350" in equip.servers:
            svr, ln, device_info, cnt, config = equip.servers['LS 350']
        elif "LS 336" in equip.servers:
            svr, ln, device_info, cnt, config = equip.servers['LS 336']
        else:
            print("Lakeshore not found, TemperatureControl GUI not configured.")
            return
        
        n = 0
        ix = 0
        self.TempWidgets = []
        self.TempPlots = []
        self.input_data_labels = []
        self.inputSettings = []
        self.sampleData = []
        thermometerDict = {}
        for ix in range(5):
            lbl = "Input " + str(ix+1)
            if lbl in config:
                n += 1
                self.inputSettings.append(config[lbl])
                label = config[lbl + ' Label']
                self.input_data_labels.append(label)
                thermometerDict[label] = config[lbl]
                self.sampleData.append(np.array([]))
                
                self.TempWidgets.append(ThermometerWidget(self.reactor, lbl, self.temperature_frame))
                self.TempWidgets[ix].move((n-1)*350,0)
                self.TempWidgets[ix].title_label.setText(label)
            
                self.TempPlots.append(pg.PlotWidget(parent=self.TempWidgets[ix].display_frame))
                self.TempPlots[ix].setLabel('left', 'Temperature', units = 'K')
                self.TempPlots[ix].setLabel('bottom', 'Time', units = 'h')
                self.TempPlots[ix].showAxis('right', show = True)
                self.TempPlots[ix].showAxis('top', show = True)
                self.TempPlots[ix].setTitle(str(label)+' vs. Time')
                self.TempPlots[ix].setGeometry(QRect(5, 0, 340, 340))
                ix += 1
        self.temperature_frame.setGeometry(QRect(260, 0, n*350+10, 500))
        self.setGeometry(QRect(0, 0, n*350+270, 515))
        
        for widget in self.loopWidgets:
            widget.setThermometers(thermometerDict)

    def updateTime(self):
        val = readNum(str(self.lineEdit_time.text()))
        if isinstance(val,float):
            self.measurementSettings['plot record'] = val
        self.lineEdit_time.setText(formatNum(self.measurementSettings['plot record']))

    def updateDelay(self):
        val = readNum(str(self.lineEdit_delay.text()))
        if isinstance(val,float):
            self.measurementSettings['sample delay'] = val
        self.lineEdit_delay.setText(formatNum(self.measurementSettings['sample delay']))

    @inlineCallbacks
    def startTempMonitoring(self):
        try:
            errcount = 0
            self.monitoring = True
            if self.first_data_point:
                self.first_data_point = False
                date = datetime.now()
                self.datestamp = date.strftime("%Y-%m-%d %H:%M:%S")
            
            
            file_info = yield self.dv.new("Temperature Log", ['time (hours)'], self.input_data_labels)
            self.dvFileName = file_info[1]
            self.lineEdit_ImageNum.setText(file_info[1].split(" - ")[1]) # second string is unique identifier
            yield self.dv.add_parameter('Start date and time', self.datestamp)

            while self.monitoring:
                t = time.time() - self.time_offset
                t = t / 3600 #Convert time to hours
                self.timeData = np.append(self.timeData, float(t))
                dat = np.zeros(len(self.TempWidgets)+1)
                dat[0] = float(t)

                for ix in range(len(self.inputSettings)):
                    try:
                        if self.ls == False:
                            break
                        Temp = yield self.ls.read_temp(self.inputSettings[ix])
                        
                        # Sometimes after setting commands there is an odd semicolon is returned
                        # Handle that case and other strings being returned.
                        if Temp == ';' or Temp == '': # If it's just a semicolon or empty, try again
                            Temp = yield self.ls.read_temp(self.inputSettings[ix])
                        if ';' in Temp: # If it contains a semicolon, replace it
                            Temp = Temp.replace(';','')
                        try:
                            float(Temp)
                        except:
                            print("Reading", self.input_data_labels[ix], "Failed with:", Temp)
                            Temp = self.sampleData[ix][-1]
                        
                        self.sampleData[ix] = np.append(self.sampleData[ix], float(Temp))
                        self.TempWidgets[ix].lcdNumber_Temp.display(float(Temp))
                        dat[ix+1] = float(Temp)
                    except:
                        if len(self.sampleData[ix]) < len(self.timeData): # Prevent inconsistent length error
                            self.sampleData[ix] = np.append(self.sampleData[ix], 0)
                        printErrorInfo()
                        errcount += 1
                self.dv.add(dat)
                if errcount > 25:
                    print("=========================")
                    print("startTempMonitoring in Temperature Control: More than 25 errors, stopping polling")
                    print("=========================")
                    break
                self.updatePlots()

                yield self.sleep(self.measurementSettings['sample delay'])
        except:
            printErrorInfo()
            pass

    def updatePlots(self):
        try:
            length = len(self.timeData)
            if length > 1:
                if (self.timeData[length-1] - self.timeData[0]) <= self.measurementSettings['plot record']:
                    for ix in range(len(self.inputSettings)):
                        self.TempPlots[ix].clear()
                        self.TempPlots[ix].plot(self.timeData, self.sampleData[ix])
                else:
                    a = np.argmin(np.abs(self.timeData - (self.timeData[length-1] - self.measurementSettings['plot record'])))
                    for ix in range(len(self.inputSettings)):
                        self.TempPlots[ix].clear()
                        self.TempPlots[ix].plot(self.timeData[a:], self.sampleData[ix][a:])
        except:
            printErrorInfo()

    @inlineCallbacks
    def allOff(self, e):
        for widget in self.loopWidgets:
            yield widget.heaterOff()

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
        self.push_all_off.setEnabled(False)
        for widget in self.loopWidgets:
            widget.lockInterface()

    def unlockInterface(self):
        self.push_all_off.setEnabled(True)
        for widget in self.loopWidgets:
            widget.unlockInterface()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""
    @inlineCallbacks
    def readTherm(self, label):
        '''
        Label is name of the thermometer on the front panel and in datavault
        '''
        for i in range(len(self.input_data_labels)):
            if self.input_data_labels[i] == label:
                returnValue(self.sampleData[i][-1])
        print("Error readTherm: could not find " + str(label))
        returnValue(None)
    '''
    Legacy Scripting Module functions when this implemented only one loop. 
    If needed they can be reimplemented. But most functionlity
    could be replicated by calling functions on the loop widgets. For example to turn on loop 1 with
    a given setpoint in the scripting module:
    
    yield TempControl.loop1.setSetpoint(self, 1.5)
    yield TempControl.loop1.setRange("Low")
    yield TempControl.loop1.heaterOn()
    # Do experiment
    yield TempControl.loop1.heaterOff()
    '''
    # @inlineCallbacks
    # def setFeedbackThermometer(self, ind):
    #     self.measurementSettings['feedback thermometer'] = ind
    #     yield self.setOutputSettings()
    # 
    # @inlineCallbacks
    # def setHeaterMode(self, mode):
    #     self.measurementSettings['heater mode'] = mode
    # 
    #     if self.measurementSettings['heater mode'] == 0:
    #         self.label_setpoint.setText('Setpoint (K):')
    #         self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['setpoint']))
    #     elif self.measurementSettings['heater mode'] == 1:
    #         self.label_setpoint.setText('Output (%):')
    #         self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['out percent']))
    #     else:
    #         self.label_setpoint.setText('WTF?!?!')
    # 
    #     yield self.setOutputSettings()
    # 
    # @inlineCallbacks
    # def setHeaterPID(self, loop, p, i , d):
    #     self.measurementSettings['p'] = p
    #     self.measurementSettings['i'] = i
    #     self.measurementSettings['d'] = d
    #     yield self.ls.pid_set(self.index,self.measurementSettings['p'],self.measurementSettings['i'],self.measurementSettings['d'])
    # 
    # @inlineCallbacks
    # def setHeaterRange(self, rang):
    #     self.measurementSettings['heater range'] = rang
    #     if str(self.push_heater.text()) == 'Heater On':
    #         yield self.ls.range_set(self.index, self.measurementSettings['heater range'])
    # 
    # @inlineCallbacks
    # def setHeaterSetpoint(self, setpoint):
    #     self.measurementSettings['setpoint'] = setpoint
    #     if self.measurementSettings['heater mode'] == 0:
    #         self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['setpoint']))
    #     yield self.ls.setpoint(self.index, self.measurementSettings['setpoint'])
    # 
    # @inlineCallbacks
    # def setHeaterPercentage(self, percent):
    #     self.measurementSettings['out percent'] = percent
    #     if self.measurementSettings['heater mode'] == 1:
    #         self.lineEdit_setpoint.setText(formatNum(self.measurementSettings['out percent']))
    #     yield self.ls.write('MOUT%i,%f'%(self.index,self.measurementSettings['out percent']))
    # 
    # @inlineCallbacks
    # def setHeaterOn(self):
    #     if str(self.push_heater.text()) == 'Heater Off':
    #         yield self.toggleHeater()
    # 
    # @inlineCallbacks
    # def setHeaterOff(self):
    #     if str(self.push_heater.text()) == 'Heater On':
    #         yield self.toggleHeater()

class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
