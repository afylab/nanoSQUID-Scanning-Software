from __future__ import division
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading
import math
import copy

path = sys.path[0] + r"\nSOTCharacterizer"
characterGUI = path + r"\character_GUI.ui"
dialogBox = path + r"\sweepCheck.ui"
dacSet = path + "\dacChannels.ui"
acSet = path + r"\acSetting.ui"
prelimSweep = path + r"\preliminarySweep.ui"
toeReminder = path + r"\toeReminder.ui"
gotoSetPoint = path + r"\gotoSetpoint.ui"
serlist = path + r"\requiredServers.ui"

Ui_MainWindow, QtBaseClass = uic.loadUiType(characterGUI)
Ui_DialogBox, QtBaseClass = uic.loadUiType(dialogBox)
Ui_dacSet, QtBaseClass = uic.loadUiType(dacSet)
Ui_acSet, QtBaseClass = uic.loadUiType(acSet)
Ui_prelimSweep, QtBaseClass = uic.loadUiType(prelimSweep)
Ui_toeReminder, QtBaseClass = uic.loadUiType(toeReminder)
Ui_ServerList, QtBaseClass = uic.loadUiType(serlist)

#Main characterization window with plots, sweep paramteres, etc.
class Window(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)
        #QtGui.QDialog.__init__(self)
        self.parent = parent
        
        self.reactor = reactor
        self.setupUi(self)
        self.setUpPlots()
        self.magnetPower.clear()
    
        #Dictionaries of the wiring and instrument settings
        self.settingsDict = {
                'blink':                2, #1 index DAC or DC box channel
                'nsot bias output':     1, #1 index bias output on the DAC ADC
                'toellner volts':       4, #1 indexed output on the DAC ADC to control Toellner power supply voltage
                'toellner current':     3, #1 indexed output on the DAC ADC to control Toellner power supply current
                'nsot bias input':      4, #1 indexed input on the DAC ADC to read the nsot bias voltage
                'feedback DC input':    3, #1 indexed input on the DAC ADC to read the DC feedback signal
                'noise input':          2, #1 indexed input on the DAC ADC to read the noise
                'feedback AC input':    1, #1 indexed input on the DAC ADC to read the AC signal (should be coming from a lockin)
                'Magnet device':        'Toellner 8851', #Device used to control the magnetic field 
        }
        
        # AC voltage characteristics, though this functionality is no longer fully set up with the Zurich lockin
        # If this is ever used again, it should be combined with the previous dictionary
        self.acSettingsDict = {'freq' : 4.0, 'amp' : 2.0}
        
        #Dictionary of parameters defining the nSOT sweep
        self.sweepParamDict = {'B_min' : 0, 'B_max' : 0.1, 'B_pnts' : 100, 'B_rate' : 1, 'V_min' : 0, 'V_max' : 1, 'V_pnts' : 500, 'delay' : 1,'volt mode' : 'min/max', 'Magnet device' : 'Toellner 8851', 'blink mode' : 'on'}
        #Dictionary the keeps track of the setpoints in magnetic field and bias voltage that are set by the 'Go To Setpoint' window
        self.setpntDict = {'field' : 0, 'bias' : 0}
        #Flag that tells the main window whether the nSOT is at a field or bias setpoint
        self.atSetpoint = False
        self.fieldPos = 0
        self.plotNoPlot = 0
        
        #Open the window reminding the user to turn on the Toellner output, or goes straight to the window used to confirm the sweep parameters if using the IPS
        self.startSweep.clicked.connect(self.toeCheck)
        #Flag used to initiate an abort function in the middle of a sweep
        self.abortFlag = False
        self.abortSweep.setEnabled(False)
        self.abortSweep.clicked.connect(self.initAbort)
        #Opens the preliminary sweep window
        self.prelim.clicked.connect(self.runPrelimSweep)
        
        #Toggles between number of steps and Tesla/Volts per step in the sweep parameter display in the main window
        self.fieldStepsInc.clicked.connect(self.toggleFieldSteps)
        self.fieldSIStat = 'num pnts'
        self.biasStepsInc.clicked.connect(self.toggleBiasSteps)
        self.biasSIStat = 'num pnts'
        
        #Adds/removes the ability to take line cuts in the displayed data
        self.liveTracePlot.clicked.connect(self.toggleTraceLineCut)
        self.liveTracePlotStatus = False
        self.liveRetracePlot.clicked.connect(self.toggleRetraceLineCut)
        self.liveRetracePlotStatus = False
        
        #Opens the AC settings windows
        self.acSetOpen.clicked.connect(self.acSet)

        #Shows/hides the color scales on the trace/retrace plots
        self.showTraceGrad.hide()
        self.hideTraceGrad.raise_()
        self.hideTraceGrad.clicked.connect(self.shrinkTracePlot)
        self.showTraceGrad.clicked.connect(self.enlargeTracePlot)
        self.showRetraceGrad.hide()
        self.hideRetraceGrad.raise_()
        self.hideRetraceGrad.clicked.connect(self.shrinkRetracePlot)
        self.showRetraceGrad.clicked.connect(self.enlargeRetracePlot)

        #Updates the position of the vertical/horizontal line cuts when the value in the corresponding line-edit in changed
        self.vCutTracePos.editingFinished.connect(self.changeVLine)
        self.hCutTracePos.editingFinished.connect(self.changeHLine)
        self.vCutRetracePos.editingFinished.connect(self.changeVLine)
        self.hCutRetracePos.editingFinished.connect(self.changeHLine)

        #Toggles between showing 1D plots along vertical/horizontal lines
        self.currentBiasTraceSelect.currentIndexChanged.connect(self.toggle_bottomTracePlot)
        self.currentBiasRetraceSelect.currentIndexChanged.connect(self.toggle_bottomRetracePlot)

        #Checks that the min/max field/bias values are in a sensible range and in the correct format
        self.fieldMaxSetValue.editingFinished.connect(lambda: self.UpdateBVals(self.fieldMaxSetValue))
        self.fieldMinSetValue.editingFinished.connect(lambda: self.UpdateBVals(self.fieldMinSetValue))
        self.fieldPointsSetValue.editingFinished.connect(lambda: self.pntsFormat(self.fieldPointsSetValue, 'field'))
        self.fieldSpeedSetValue.editingFinished.connect(lambda: self.UpdateBVals(self.fieldSpeedSetValue, 'speed'))

        self.biasMaxSetValue.editingFinished.connect(lambda: self.UpdateVVals(self.biasMaxSetValue))
        self.biasMinSetValue.editingFinished.connect(lambda: self.UpdateVVals(self.biasMinSetValue))
        self.biasPointsSetValue.editingFinished.connect(lambda: self.pntsFormat(self.biasPointsSetValue, 'bias'))
        self.biasSpeedSetValue.editingFinished.connect(lambda: self.pntsFormat(self.biasSpeedSetValue, 'delay'))
        
        #Toggles between plotting the Feedback voltage and Noise signal in either the trace or retrace plots
        self.tabsTrace.currentChanged.connect(self.toggleTracePlots)
        self.tabsRetrace.currentChanged.connect(self.toggleRetracePlots)
        
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize to no data to avoid line cut error
        self.isData = False
        
        #Initialize the servers to False
        self.cxn = False
        self.gen_dv = False
        self.cxn_nsot = False
        self.dv = False
        self.dac = False
        self.dac_toe = False
        self.ips = False
        self.blink_server = False
        
        self.lockInterface()

    def UpdateFieldPeriod(self):
        pos1 = self.MeasureLine1.value()
        pos2 = self.MeasureLine2.value()
        period = abs(pos1 - pos2)
        self.lineEdit_FieldPeriod.setText(str(round(period * 1000, 1)))
        fluxquanta = 2.0678338 / (10.0 ** 15)
        area = fluxquanta / period
        diameter = 2 * math.sqrt(area / math.pi)
        self.lineEdit_Diameter.setText(str(round(diameter * 10.0 ** 9, 1)))

    def ToggleMeasurementLine(self):
        if self.Flag_MeasurementLineShowing:
            self.view0.removeItem(self.MeasureLine1)
            self.view0.removeItem(self.MeasureLine2)
        else:
            self.view0.addItem(self.MeasureLine1)
            self.view0.addItem(self.MeasureLine2)
        self.Flag_MeasurementLineShowing = not self.Flag_MeasurementLineShowing

    def moveDefault(self):
        self.move(550,10)
        
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.gen_dv = dict['servers']['local']['dv']

            if dict['devices']['system']['magnet supply'] == 'Toellner Power Supply':
                self.dac_toe = dict['servers']['local']['dac_adc']
                self.magnetPower.addItem('Toellner 8851')
                self.settingsDict['Magnet device'] = 'Toellner 8851'
            elif dict['devices']['system']['magnet supply'] == 'IPS 120 Power Supply':
                self.ips = dict['servers']['remote']['ips120']
                self.magnetPower.addItem('IPS 120-10')
                self.settingsDict['Magnet device'] = 'IPS 120-10'
            
            '''
            Create another connection to labrad in order to have a set of servers opened up in a context
            specific to this module. This allows multiple datavault connections to be editted at the same
            time, or communication with multiple DACs / other devices 
            '''
            
            from labrad.wrappers import connectAsync
            self.cxn_nsot = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn_nsot.data_vault
            curr_folder = yield self.gen_dv.cd()
            yield self.dv.cd(curr_folder)
            
            self.dac = yield self.cxn_nsot.dac_adc
            self.dac.select_device(dict['devices']['nsot']['dac_adc'])
            
            print dict['devices']['system']['blink device']
            if dict['devices']['system']['blink device'].startswith('ad5764_dcbox'):
                self.blink_server = yield self.cxn_nsot.ad5764_dcbox
                self.blink_server.select_device(dict['devices']['system']['blink device'])
                print 'DC BOX Blink Device'
            elif dict['devices']['system']['blink device'].startswith('DA'):
                self.blink_server = yield self.cxn_nsot.dac_adc
                self.blink_server.select_device(dict['devices']['system']['blink device'])
                print 'DAC ADC Blink Device'
            
            self.blinkDevice = dict['devices']['system']['blink device']
            self.settingsDict['blink'] = dict['channels']['system']['blink channel']
            
            self.settingsDict['nsot bias output'] = dict['channels']['nsot']['nSOT Bias']
            self.settingsDict['nsot bias input'] = dict['channels']['nsot']['Bias Reference']
            self.settingsDict['feedback DC input'] = dict['channels']['nsot']['DC Readout']
            self.settingsDict['feedback AC input'] = dict['channels']['nsot']['AC Readout']
            self.settingsDict['noise input'] = dict['channels']['nsot']['Noise Readout']
            
            self.settingsDict['toellner volts'] = dict['channels']['system']['toellner dac voltage']
            self.settingsDict['toellner current'] = dict['channels']['system']['toellner dac current']
            
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            
            self.unlockInterface()
        except Exception as inst:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            print 'nsot labrad connect', inst
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print 'line num ', exc_tb.tb_lineno
            
    def disconnectLabRAD(self):
        self.magnetPower.removeItem(0)
        self.cxn = False
        self.gen_dv = False
        self.cxn_nsot = False
        self.dv = False
        self.dac = False
        self.dac_toe = False
        self.ips = False
        self.blink_server = False
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            
    def updateDataVaultDirectory(self):
        curr_folder = yield self.gen_dv.cd()
        yield self.dv.cd(curr_folder)
            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
    
    #Opens the preliminary sweep window
    def runPrelimSweep(self):
        self.prelim.setEnabled(False)
        self.prelimSweep = preliminarySweep(self.reactor, self.dv, self.dac, self.settingsDict, self)
        self.prelimSweep.show()
           
    #Opens window to adjust the AC response settings
    def acSet(self):
        self.acSetOpen.setEnabled(False)
        self.acSettings = acSettings(self.acSettingsDict, self)
        if self.acSettings.exec_():
            print 'AC Settings: ', self.acSettingsDict

    #Initializes an abort of a sweep by changing the self.abortFlag to True
    def initAbort(self):
        self.abortFlag = True

    #Checks the format of number of steps in magnetic field or bias voltage 
    def pntsFormat(self, lineEdit, type):
        ans = self.siFormat(lineEdit.text())

        if lineEdit == 'REFORMAT':
            pass
        elif ans == 'Invalid format':
            lineEdit.setText('REFORMAT')
        else:
            if type == 'field':
                if self.fieldSIStat == 'num pnts':
                    lineEdit.setText(str(int(ans)))
                    
            elif type == 'bias':
                if self.biasSIStat == 'num pnts':
                    lineEdit.setText(str(int(ans)))        
                    
            elif type == 'delay':
                pass
    
    #Toggles between number of steps and Tesla/step in the sweep parameter line edits
    def toggleFieldSteps(self):
        if self.fieldSIStat == 'num pnts':
            self.FieldInc.setText("Millitesla per Step")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
            steps = float(self.fieldPointsSetValue.text())
            bMax = self.siFormat(self.fieldMaxSetValue.text(), 3)
            bMin = self.siFormat(self.fieldMinSetValue.text(), 3)
            if steps != 1 and steps != 0:
                inc = np.round((1000 * (bMax - bMin) / (steps - 1)), decimals = 3)
                self.fieldPointsSetValue.setText(str(inc))
                self.fieldSIStat = 'field step'
            else:
                self.FieldInc.setText("Millitesla per Step")
                self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
                self.fieldSIStat = 'field step'
        else:
            self.FieldInc.setText("Number of Steps")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
            inc = float(self.fieldPointsSetValue.text())
            bMax = self.siFormat(self.fieldMaxSetValue.text(), 3)
            bMin = self.siFormat(self.fieldMinSetValue.text(), 3)
            if inc != 0:
                steps = int(1000 * (bMax - bMin) / (inc)) +1 
                self.fieldPointsSetValue.setText(str(steps))
                self.fieldSIStat = 'num pnts'
            else:
                self.FieldInc.setText("Number of Steps")
                self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
                self.fieldSIStat = 'num pnts'              

    #Toggles between number of steps and Volts/step in the sweep parameter line edits
    def toggleBiasSteps(self):
        if self.biasSIStat == 'num pnts':
            self.BiasInc.setText("Millivolts per Step")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
            steps = float(self.biasPointsSetValue.text())
            vMax = self.siFormat(self.biasMaxSetValue.text(), 3)
            vMin = self.siFormat(self.biasMinSetValue.text(), 3)
            if steps != 1:
                inc = np.round((1000 * (vMax - vMin) / (steps - 1)), decimals = 3)
                self.biasPointsSetValue.setText(str(inc))
                self.biasSIStat = 'bias step'
            else:
                self.BiasInc.setText("Millivolts per Step")
                self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
                self.biasSIStat = 'bias step'
        else:
            self.BiasInc.setText("Number of Steps")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
            inc = float(self.biasPointsSetValue.text())
            vMax = self.siFormat(self.biasMaxSetValue.text(), 3)
            vMin = self.siFormat(self.biasMinSetValue.text(), 3)
            if inc != 0:
                steps = int(1000 * (vMax - vMin) / (inc)) + 1
                self.biasPointsSetValue.setText(str(steps))
                self.biasSIStat = 'num pnts'
            else:
                self.BiasInc.setText("Number of Steps")
                self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
                self.biasSIStat = 'num pnts'            

    #Hides/shows the color scales on the Trace and Retrace plots
    def shrinkTracePlot(self):
        self.tracePlot.ui.histogram.hide()
        self.noiseTracePlot.ui.histogram.hide()
        self.hideTraceGrad.hide()
        self.showTraceGrad.show()
        self.showTraceGrad.raise_()

    def enlargeTracePlot(self):
        self.tracePlot.ui.histogram.show()
        self.noiseTracePlot.ui.histogram.show()
        self.hideTraceGrad.show()
        self.showTraceGrad.hide()      
        self.showTraceGrad.raise_()          

    def shrinkRetracePlot(self):
        self.retracePlot.ui.histogram.hide()
        self.noiseRetracePlot.ui.histogram.hide()
        self.hideRetraceGrad.hide()
        self.showRetraceGrad.show()
        self.showRetraceGrad.raise_()

    def enlargeRetracePlot(self):
        self.retracePlot.ui.histogram.show()
        self.noiseRetracePlot.ui.histogram.show()
        self.hideRetraceGrad.show()
        self.showRetraceGrad.hide()          
        self.showRetraceGrad.raise_()

    #Formats line edits with SI suffixes and/or scientific notation
    #Why the fuck Avi... I told you this existed already. 
    #TODO implement the version of this that already exists and is used everywhere else in
    #the code
    def siFormat(self, string, digits = None):
        siDict = {'T': 12, 'G' : 9, 'M' : 6, 'k' : 3, 'c': -2, 'm' : -3, 'u' : -6, 'n' : -9, 'p' : -12}
        string = str(string)
        if digits == None:
            digits = len(string)
        if not string[-1].isdigit():
            try:
                
                suff = siDict[string[-1]]
                if 'e' in string[0:-1]:
                    mant, exp = string[0:-1].split('e')[0], string[0:-1].split('e')[1]
                    
                elif 'E' in string[0:-1]:
                    mant, exp = string[0:-1].split('E')[0], string[0:-1].split('E')[1]
                else:
                    mant, exp = string[0:-1], 0
                num = np.round(np.float(mant), decimals = digits)*10**(suff + np.float(exp))
                
                return num
            except:
                return 'Invalid format'
        else:
            try:
                
                if 'e' in string:
                    mant, exp = string.split('e')[0], string.split('e')[1]
                    
                elif 'E' in string:
                    mant, exp = string.split('E')[0], string.split('E')[1]
                else:
                    mant, exp = string, 0
                num = np.round(np.float(mant), decimals = digits)*10**(np.float(exp))
                return num 
            except:
                return 'Invalid format'
                
    #Check the format of the magnetic field Min/Max values and ensures that the are in an appropriate range
    def UpdateBVals(self, lineEdit, speed = None):
        ans = self.siFormat(lineEdit.text(), 3)
        if lineEdit == 'REFORMAT':
            pass
        elif ans == 'Invalid format':
            lineEdit.setText('REFORMAT')
        
        elif speed == 'speed':
            pass
        #Keeps the field value within 1.25T for the dipper magnet    
        elif self.settingsDict['Magnet device'] == 'Toellner 8851':
            if float(ans) < 0:
                lineEdit.setText('0')

            
            elif -1.25 <= float(ans) <= 1.25:
                pass
            elif float(ans) >= 1.25:
                lineEdit.setText('1.25')


            elif float(ans) <= -1.25:
                lineEdit.setText('-1.25')
                        
        #Keeps the field value within 5T for the cryostat magnet
        elif self.settingsDict['Magnet device'] == 'IPS 120-10':
            if -5 <= float(ans) <= 5:
                pass
            elif float(ans) >= 5:
                lineEdit.setText('5')


            elif float(ans) <= -5:
                lineEdit.setText('-5')    

    #Check the format of the bias voltage Min/Max values and ensures that the are in an appropriate range
    def UpdateVVals(self, lineEdit):
        ans = self.siFormat(lineEdit.text(), 3)
        if lineEdit == 'REFORMAT':
            pass
        elif ans == 'Invalid format':
            lineEdit.setText('REFORMAT')
        #Makes sure the voltage is between -10V and +10V to accomodate the DAC
        elif -10 <= float(ans) <= 10:
            pass
        elif float(ans) >= 10:
            lineEdit.setText('10.00')
        elif float(ans) <= -10:
            lineEdit.setText('-10.00')

    def setUpPlots(self):
        self.vTraceLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hTraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vTraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hTraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        
        self.vTraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hTraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vTraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hTraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.vRetraceLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hRetraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vRetraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hRetraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        
        self.vRetraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hRetraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.view0 = pg.PlotItem(name = "Field-Bias-DC Volts")
        self.view0.setLabel('left', text='Bias Voltage', units = 'V')
        self.view0.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view0.showAxis('top', show = True)
        self.view0.showAxis('right', show = True)
        self.view0.setAspectLocked(lock = False, ratio = 1)
        self.tracePlot = pg.ImageView(parent = self.currentTracePlot, view = self.view0)
        self.tracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.tracePlot.ui.menuBtn.hide()
        self.tracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.tracePlot.ui.roiBtn.hide()
        self.tracePlot.ui.menuBtn.hide()
        self.view0.setAspectLocked(False)
        self.view0.invertY(False)
        self.view0.setXRange(-1.25,1.25,0)
        self.view0.setYRange(-10,10, 0)

        self.view0.addItem(self.vTraceLine, ignoreBounds = True)
        self.view0.addItem(self.hTraceLine, ignoreBounds =True)

        #Raymond's addition
        self.MeasureLine1 = pg.InfiniteLine(pos = 0.1, angle = 90, movable = True, pen = 'b', hoverPen = (50, 50, 200))
        self.MeasureLine2 = pg.InfiniteLine(pos = 0.2, angle = 90, movable = True, pen = 'b', hoverPen = (50, 50, 200))
        self.MeasureLine1.sigPositionChangeFinished.connect(self.UpdateFieldPeriod)
        self.MeasureLine2.sigPositionChangeFinished.connect(self.UpdateFieldPeriod)
        self.pushButton_Show.clicked.connect(self.ToggleMeasurementLine)
        self.Flag_MeasurementLineShowing = True
        self.view0.addItem(self.MeasureLine1, ignoreBounds = True)
        self.view0.addItem(self.MeasureLine2, ignoreBounds = True)

        self.view1 = pg.PlotItem(name = "Field-Bias-Noise")
        self.view1.setLabel('left', text='Bias Voltage', units = 'V')
        self.view1.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view1.showAxis('top', show = True)
        self.view1.showAxis('right', show = True)
        self.view1.setAspectLocked(lock = False, ratio = 1)
        self.noiseTracePlot = pg.ImageView(parent = self.noiseTracePlot, view = self.view1)
        self.noiseTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.noiseTracePlot.ui.menuBtn.hide()
        self.noiseTracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.noiseTracePlot.ui.roiBtn.hide()
        self.noiseTracePlot.ui.menuBtn.hide()
        self.view1.setAspectLocked(False)
        self.view1.invertY(False)
        self.view1.setXRange(-1.25,1.25,0)
        self.view1.setYRange(-10,10, 0)
        
        self.view1.addItem(self.vTraceNoiseLine, ignoreBounds = True)
        self.view1.addItem(self.hTraceNoiseLine, ignoreBounds =True)

        self.view2 = pg.PlotItem(name = "Field-Bias-DC Volts")
        self.view2.setLabel('left', text='Bias Voltage', units = 'V')
        self.view2.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view2.showAxis('top', show = True)
        self.view2.showAxis('right', show = True)
        self.view2.setAspectLocked(lock = False, ratio = 1)
        self.retracePlot = pg.ImageView(parent = self.currentRetracePlot, view = self.view2)
        self.retracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.retracePlot.ui.menuBtn.hide()
        self.retracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.retracePlot.ui.roiBtn.hide()
        self.retracePlot.ui.menuBtn.hide()
        self.view2.setAspectLocked(False)
        self.view2.invertY(False)
        self.view2.setXRange(-1.25,1.25,0)
        self.view2.setYRange(-10,10, 0)

        self.view2.addItem(self.vRetraceLine, ignoreBounds = True)
        self.view2.addItem(self.hRetraceLine, ignoreBounds =True)

        self.view3 = pg.PlotItem(name = "Field-Bias-Noise")
        self.view3.setLabel('left', text='Bias Voltage', units = 'V')
        self.view3.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view3.showAxis('top', show = True)
        self.view3.showAxis('right', show = True)
        self.view3.setAspectLocked(lock = False, ratio = 1)
        self.noiseRetracePlot = pg.ImageView(parent = self.noiseRetracePlot, view = self.view3)
        self.noiseRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.noiseRetracePlot.ui.menuBtn.hide()
        self.noiseRetracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.noiseRetracePlot.ui.roiBtn.hide()
        self.noiseRetracePlot.ui.menuBtn.hide()
        self.view3.setAspectLocked(False)
        self.view3.invertY(False)
        self.view3.setXRange(-1.25,1.25,0)
        self.view3.setYRange(-10,10, 0)
        
        self.view3.addItem(self.vRetraceNoiseLine, ignoreBounds = True)
        self.view3.addItem(self.hRetraceNoiseLine, ignoreBounds =True)

        self.IVTracePlot = pg.PlotWidget(parent = self.curbiasTracePlot)
        self.IVTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IVTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.IVTracePlot.showAxis('right', show = True)
        self.IVTracePlot.showAxis('top', show = True)

        self.IBTracePlot = pg.PlotWidget(parent = self.curfieldTracePlot)
        self.IBTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IBTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.IBTracePlot.showAxis('right', show = True)
        self.IBTracePlot.showAxis('top', show = True)

        self.IVRetracePlot = pg.PlotWidget(parent = self.curbiasRetracePlot)
        self.IVRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IVRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.IVRetracePlot.showAxis('right', show = True)
        self.IVRetracePlot.showAxis('top', show = True)

        self.IBRetracePlot = pg.PlotWidget(parent = self.curfieldRetracePlot)
        self.IBRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IBRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.IBRetracePlot.showAxis('right', show = True)
        self.IBRetracePlot.showAxis('top', show = True)

        self.tracePlotNow = "bias"
        self.retracePlotNow = "bias"
        self.traceNoiseNow = "bias"
        self.retraceNoiseNow = "bias"
    
    def toeCheck(self):
        self.checkToe = toellnerReminder()
        self.startSweep.setEnabled(False)
        if self.settingsDict['Magnet device'] != 'Toellner 8851':
            self.checkSweep()
        else:
            self.checkToe.show()
            self.checkToe.accepted.connect(self.checkSweep)
            self.checkToe.rejected.connect(self.decline)

    def checkSweep(self):
        sweepMod = self.biasSweepMode.currentIndex()
        blinkMod = self.blink.currentIndex()

        b_min = self.siFormat(self.fieldMinSetValue.text(), 3)
        b_max = self.siFormat(self.fieldMaxSetValue.text(), 3)
        if self.fieldSIStat == 'num pnts':
            b_pnts = int(self.fieldPointsSetValue.text())
        elif self.fieldSIStat == 'field step':
            b_pnts = int(1000 * np.absolute(b_max - b_min) / (float(self.fieldPointsSetValue.text())))
        b_speed = self.siFormat(self.fieldSpeedSetValue.text(), 3)
        v_min = self.siFormat(self.biasMinSetValue.text(), 3)
        v_max = self.siFormat(self.biasMaxSetValue.text(), 3)
        if self.biasSIStat == 'bias steps':
            v_pnts = int(1000 * np.absolute(v_max - v_min) / (float(self.biasPointsSetValue.text())))
        elif self.biasSIStat == 'num pnts':
            v_pnts = int(self.biasPointsSetValue.text())
        v_speed = self.siFormat(self.biasSpeedSetValue.text())
        if b_min > b_max:
            b_max_str, b_min_str = self.fieldMaxSetValue.text(), self.fieldMinSetValue.text()
            self.fieldMinSetValue.setText(b_max_str)
            self.fieldMaxSetValue.setText(b_min_str)
            b_min = self.siFormat(self.fieldMinSetValue.text(), 3)
            b_max = self.siFormat(self.fieldMaxSetValue.text(), 3)
        if v_min > v_max:
            v_max_str, v_min_str = self.biasMaxSetValue.text(), self.biasMinSetValue.text()
            self.biasMinSetValue.setText(v_max_str)
            self.biasMaxSetValue.setText(v_min_str)
            v_min = self.siFormat(self.biasMinSetValue.text(), 3)
            v_max = self.siFormat(self.biasMaxSetValue.text(), 3)
        if sweepMod == 1:
            if v_min < 0 and v_max > 0:
                pass
            else:
                vDefault = max(abs(float(v_min)), abs(float(v_max)))
                v_max = vDefault
                v_min = -vDefault

        if v_speed <0.001:
            vSpeed = '1'
        else:
            pass
    
        self.bMin = float(b_min)
        self.bMax = float(b_max)
        self.bPoints = int(b_pnts)
        self.bSpeed = float(b_speed)
        self.vMin = float(v_min)
        self.vMax = float(v_max)
        self.vPoints = int(v_pnts)
        self.vSpeed = float(v_speed)
        self.sweepMod = int(sweepMod)
        self.blinkMod = int(blinkMod)
        
        if b_pnts != 0:
            tLatent = 5
            T = (np.absolute(self.bMin) + np.absolute(self.bMax)) / (self.bSpeed) + (self.bPoints/self.bSpeed)* (np.absolute(self.bMax - self.bMin) / (self.bPoints)) + (self.bPoints/60) * ( (self.vPoints - 1) * (self.vSpeed/1000000) + float(tLatent))
            T = 2*T
            hours = int(T / 60) 
            minutes = int(T)%60
            TotalTime = str(hours) + ' hours ' + str(minutes) + ' minutes' 
        else:
            TotalTime = "infinite"
        
        self.sweepParamDict = {'B_min' : b_min, 'B_max' : b_max, 'B_pnts' : b_pnts, 'B_rate' : b_speed, 'V_min' : v_min, 'V_max' : v_max, 'V_pnts' : v_pnts, 'delay' : v_speed, 'sweep mode' : sweepMod, 'blink mode' : blinkMod, 'Magnet device' : self.settingsDict['Magnet device'], 'sweep time' : TotalTime} 
        
        print '------------------------------------------------------------------------------------'
        print 'Sweep Parameters'
        print self.sweepParamDict
        print 'General Input Settings'
        print self.settingsDict
        print '-------------------------------------------------------------------------------------'
        self.dialog = DialogBox(self.sweepParamDict, self)
        self.dialog.show()    
        self.dialog.accepted.connect(self.initSweep)
        self.dialog.rejected.connect(self.decline)        

    def decline(self):
        self.startSweep.setEnabled(True)
        self.abortSweep.setEnabled(False)

    def toggleTraceLineCut(self):
        if self.liveTracePlotStatus is True:
            self.view0.addItem(self.vTraceLine, ignoreBounds = True)
            self.view0.addItem(self.hTraceLine, ignoreBounds =True)
            self.view1.addItem(self.vTraceNoiseLine, ignoreBounds = True)
            self.view1.addItem(self.hTraceNoiseLine, ignoreBounds = True)
            self.vTraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hTraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.vTraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hTraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.liveTracePlotStatus = False
        elif self.liveTracePlotStatus is False:
            self.view0.removeItem(self.vTraceLine)
            self.view0.removeItem(self.hTraceLine)
            self.view1.removeItem(self.vTraceNoiseLine)
            self.view1.removeItem(self.hTraceNoiseLine)
            self.liveTracePlotStatus = True
            
    def toggleRetraceLineCut(self):
        if self.liveRetracePlotStatus is True:
            self.view2.addItem(self.vRetraceLine, ignoreBounds = True)
            self.view2.addItem(self.hRetraceLine, ignoreBounds =True)
            self.view3.addItem(self.vRetraceNoiseLine, ignoreBounds = True)
            self.view3.addItem(self.hRetraceNoiseLine, ignoreBounds = True)
            self.vRetraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hRetraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.vRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.liveRetracePlotStatus = False
        elif self.liveRetracePlotStatus is False:
            self.view2.removeItem(self.vRetraceLine)
            self.view2.removeItem(self.hRetraceLine)
            self.view3.removeItem(self.vRetraceNoiseLine)
            self.view3.removeItem(self.hRetraceNoiseLine)
            self.liveRetracePlotStatus = True

    def updateVLineBox(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.vTraceLine.value()
                self.vCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.vTraceNoiseLine.value()
                self.vCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass            
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.vRetraceLine.value()
                print posRetrace
                self.vCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.vRetraceNoiseLine.value()
                print posRetrace
                self.vCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
                    
    def updateHLineBox(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.hTraceLine.value()
                self.hCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.hTraceNoiseLine.value()
                self.hCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.hRetraceLine.value()
                print posRetrace
                self.hCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.hRetraceNoiseLine.value()
                print posRetrace
                self.hCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            
    def changeVLine(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.vCutTracePos.value()
                self.vTraceLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.vCutTracePos.value()
                self.vTraceNoiseLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.vCutRetracePos.value()
                self.vRetraceLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.vCutRetracePos.value()
                self.vRetraceNoiseLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
                    
    def changeHLine(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.hCutTracePos.value()
                self.hTraceLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.hCutTracePos.value()
                self.hTraceNoiseLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:     
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.hCutRetracePos.value()
                self.hRetraceLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.hCutRetracePos.value()
                self.hRetraceNoiseLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
                    
    def toggleTracePlots(self):
        self.currentBiasTraceSelect.currentIndexChanged.disconnect(self.toggle_bottomTracePlot)
        self.updateHLineBox()
        self.updateVLineBox()
        self.currentBiasTraceSelect.removeItem(0)
        self.currentBiasTraceSelect.removeItem(0)
        if self.tabsTrace.currentIndex() == 1:
            self.currentBiasTraceSelect.addItem("RMS Noise vs Bias")
            self.currentBiasTraceSelect.addItem("RMS Noise vs Field")
            if self.traceNoiseNow == "bias":
                self.currentBiasTraceSelect.setCurrentIndex(0)
                self.curfieldTracePlot.lower()
                self.curbiasTracePlot.raise_()
                self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.traceNoiseNow == "field":
                self.currentBiasTraceSelect.setCurrentIndex(1)
                self.curbiasTracePlot.lower()
                self.curfieldTracePlot.raise_()
                self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVTracePlot.setLabel('left', 'RMS Noise', units = 'V')
            self.IBTracePlot.setLabel('left', 'RMS Noise', units = 'V')

        elif self.tabsTrace.currentIndex() == 0:
            self.currentBiasTraceSelect.addItem("DC Output vs Bias")
            self.currentBiasTraceSelect.addItem("DC Output vs Field")
            if self.tracePlotNow == "bias":
                self.currentBiasTraceSelect.setCurrentIndex(0)
                self.curfieldTracePlot.lower()
                self.curbiasTracePlot.raise_()
                self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.tracePlotNow == "field":
                self.currentBiasTraceSelect.setCurrentIndex(1)
                self.curbiasTracePlot.lower()
                self.curfieldTracePlot.raise_()
                self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
            self.IBTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.currentBiasTraceSelect.currentIndexChanged.connect(self.toggle_bottomTracePlot)
    
    def toggleRetracePlots(self):
        self.currentBiasRetraceSelect.currentIndexChanged.disconnect(self.toggle_bottomRetracePlot)
        self.updateHLineBox()
        self.updateVLineBox()
        self.currentBiasRetraceSelect.removeItem(0)
        self.currentBiasRetraceSelect.removeItem(0)
        if self.tabsRetrace.currentIndex() == 1:
            self.currentBiasRetraceSelect.addItem("RMS Noise vs Bias")
            self.currentBiasRetraceSelect.addItem("RMS Noise vs Field")
            if self.retraceNoiseNow == "bias":
                self.currentBiasRetraceSelect.setCurrentIndex(0)
                self.curfieldRetracePlot.lower()
                self.curbiasRetracePlot.raise_()
                self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.retraceNoiseNow == "field":
                self.currentBiasRetraceSelect.setCurrentIndex(1)
                self.curbiasRetracePlot.lower()
                self.curfieldRetracePlot.raise_()
                self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVRetracePlot.setLabel('left', 'RMS Noise', units = 'V')
            self.IBRetracePlot.setLabel('left', 'RMS Noise', units = 'V')
        elif self.tabsRetrace.currentIndex() == 0:
            self.currentBiasRetraceSelect.addItem("DC Output vs Bias")
            self.currentBiasRetraceSelect.addItem("DC Output vs Field")
            if self.retracePlotNow == "bias":
                self.currentBiasRetraceSelect.setCurrentIndex(0)
                self.curfieldRetracePlot.lower()
                self.curbiasRetracePlot.raise_()
                self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.retracePlotNow == "field":
                self.currentBiasRetraceSelect.setCurrentIndex(1)
                self.curbiasRetracePlot.lower()
                self.curfieldRetracePlot.raise_()
                self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
            self.IBRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')              
        self.currentBiasRetraceSelect.currentIndexChanged.connect(self.toggle_bottomRetracePlot)
        
    def toggle_bottomTracePlot(self):
        if self.tabsTrace.currentIndex() == 0 and self.tracePlotNow == "field":
            self.tracePlotNow = "bias"
            self.curfieldTracePlot.lower()
            self.curbiasTracePlot.raise_()
            self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
        elif self.tabsTrace.currentIndex() == 0 and self.tracePlotNow == "bias":
            self.tracePlotNow = "field"
            self.curbiasTracePlot.lower()
            self.curfieldTracePlot.raise_()
            self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
        elif self.tabsTrace.currentIndex() == 1 and self.traceNoiseNow == "field":
            self.traceNoiseNow = "bias"
            self.curfieldTracePlot.lower()
            self.curbiasTracePlot.raise_()
            self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
        elif self.tabsTrace.currentIndex() == 1 and self.traceNoiseNow == "bias":
            self.traceNoiseNow = "field"
            self.curbiasTracePlot.lower()
            self.curfieldTracePlot.raise_()
            self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
                
    def toggle_bottomRetracePlot(self):
        if self.tabsRetrace.currentIndex() == 0 and self.retracePlotNow == "field":
            self.retracePlotNow = "bias"
            self.curfieldRetracePlot.lower()
            self.curbiasRetracePlot.raise_()
            self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass
        elif self.tabsRetrace.currentIndex() == 0 and self.retracePlotNow == "bias":
            self.retracePlotNow = "field"
            self.curbiasRetracePlot.lower()
            self.curfieldRetracePlot.raise_()
            self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass
        elif self.tabsRetrace.currentIndex() == 1 and self.retraceNoiseNow == "field":
            self.retraceNoiseNow = "bias"
            self.curfieldRetracePlot.lower()
            self.curbiasRetracePlot.raise_()
            self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass
        elif self.tabsRetrace.currentIndex() == 1 and self.retraceNoiseNow == "bias":
            self.retraceNoiseNow = "field"
            self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.curbiasRetracePlot.lower()
            self.curfieldRetracePlot.raise_()
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass


    def updateBottomTracePlot(self):
        index = self.currentBiasTraceSelect.currentIndex()
        x0, x1 = (self.x0, self.x1)
        y0, y1 = (self.y0, self.y1)
        xscale, yscale = (x1-x0) / (self.curTraceData.shape[0] - 1), (y1-y0) / (self.curTraceData.shape[1] - 1)
        if index == 1:
            pos = self.hCutTracePos.value()
            self.IBTracePlot.clear()
            if pos > self.sweepParamDict['V_max'] or pos < self.sweepParamDict['V_min']:
                pass
            else:
                p = int(abs(pos - self.sweepParamDict['V_min']) / yscale)
                xVals = np.linspace(self.sweepParamDict['B_min'], self.sweepParamDict['B_max'], num = self.sweepParamDict['B_pnts'])
                if self.tabsTrace.currentIndex() == 0:
                    yVals = self.curTraceData[:,p]
                elif self.tabsTrace.currentIndex() == 1:
                    yVals = self.noiseTraceData[:,p]
                self.IBTracePlot.plot(x = xVals, y = yVals, pen = 0.5)
        elif index == 0:
            pos = self.vCutTracePos.value()
            self.IVTracePlot.clear()
            if pos > self.sweepParamDict['B_max'] or pos < self.sweepParamDict['B_min']:
                pass
            else:
                p = int(abs(pos - self.sweepParamDict['B_min']) / xscale)
                xVals = np.linspace(self.sweepParamDict['V_min'], self.sweepParamDict['V_max'], num = self.sweepParamDict['V_pnts'])
                if self.tabsTrace.currentIndex() == 0:
                    yVals = self.curTraceData[p]
                elif self.tabsTrace.currentIndex() == 1:
                    yVals = self.noiseTraceData[p]
                self.IVTracePlot.plot(x = xVals, y = yVals, pen = 0.5)
                
    def updateBottomRetracePlot(self):
        index = self.currentBiasRetraceSelect.currentIndex()
        x0, x1 = (self.x0, self.x1)
        y0, y1 = (self.y0, self.y1)
        xscale, yscale = (x1-x0) / (self.curRetraceData.shape[0] - 1), (y1-y0) / (self.curTraceData.shape[1] - 1)
        if index == 1:
            pos = self.hCutRetracePos.value()
            self.IBRetracePlot.clear()
            if pos > self.sweepParamDict['V_max'] or pos < self.sweepParamDict['V_min']:
                pass
            else:
                p = int(abs(pos - self.sweepParamDict['V_min']) / yscale)
                xVals = np.linspace(self.sweepParamDict['B_min'], self.sweepParamDict['B_max'], num = self.sweepParamDict['B_pnts'])
                if self.tabsRetrace.currentIndex() == 0:
                    yVals = self.curRetraceData[:,p]
                elif self.tabsRetrace.currentIndex() == 1:
                    yVals = self.noiseRetraceData[:,p]
                self.IBRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)
        elif index == 0:
            pos = self.vCutRetracePos.value()
            self.IVRetracePlot.clear()
            if pos >= self.sweepParamDict['B_max'] or pos <=  self.sweepParamDict['B_min']:
                pass
            else:
                p = int(abs(pos - self.sweepParamDict['B_min']) / xscale)
                xVals = np.linspace(self.sweepParamDict['V_min'], self.sweepParamDict['V_max'], num = self.sweepParamDict['V_pnts'])
                if self.tabsRetrace.currentIndex() == 0:
                    yVals = self.curRetraceData[p]
                elif self.tabsRetrace.currentIndex() == 1:
                    yVals = self.noiseRetraceData[p]
                self.IVRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)

    def update_bottomTracePlot(self, i):
        if self.liveTracePlotStatus is False:
            pass
        elif self.liveTracePlotStatus is True:
            index = self.currentBiasTraceSelect.currentIndex()
            if index == 0:
                
                self.IVTracePlot.clear()
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.curTraceData[i]
                self.IVTracePlot.plot(x = xVals, y = yVals, pen = 0.5)
            else:
                pass

    def update_bottomRetracePlot(self, i):
        if self.liveRetracePlotStatus is False:
            pass
        elif self.liveRetracePlotStatus is True:
            index = self.currentBiasRetraceSelect.currentIndex()
            if index == 0:
                self.IVRetracePlot.clear()
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.curRetraceData[i]
                self.IVRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)
            else:
                pass

    def updatePlots(self, new_line):
        if new_line[0][0] == 1:
            i = new_line[0][1]
            new_curData = [x[5] for x in new_line]
            new_noiseData = [x[6] for x in new_line]
            self.curRetraceData[i] = new_curData
            self.noiseRetraceData[i] = new_noiseData
            self.retracePlot.setImage(self.curRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.update_bottomRetracePlot(i)
            self.plotNoPlot += 1

        elif new_line[0][0] == 0:
            i = new_line[0][1]
            new_curData = [x[5] for x in new_line]
            new_noiseData = [x[6] for x in new_line]
            self.curTraceData[i] = new_curData
            self.noiseTraceData[i] = new_noiseData
            self.tracePlot.setImage(self.curTraceData, autoRange = False, autoLevels = True, pos=[self.x0,self.y0],scale=[self.xscale, self.yscale])
            self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.update_bottomTracePlot(i)
            self.plotNoPlot += 1
                
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def initSweep(self):
        b_min, b_max = self.sweepParamDict['B_min'], self.sweepParamDict['B_max']
        v_min, v_max = self.sweepParamDict['V_min'], self.sweepParamDict['V_max']
        b_pnts, v_pnts = self.sweepParamDict['B_pnts'], self.sweepParamDict['V_pnts']
        b_range, v_range = np.absolute(b_max - b_min), np.absolute(v_max - v_min)
        if self.sweepParamDict['sweep mode'] == 1:
            self.positive_points = int((v_pnts * v_max)/v_range) + 1 #int((self.vPoints * self.vMax) / abs(self.vMax - self.vMin)) + 1
            self.negative_points = v_pnts - self.positive_points #self.vPoints - self.positive_points
        else:
            pass

        self.extent = [b_min, b_max, v_min, v_max]    #[self.bMin,self.bMax,self.vMin,self.vMax]
        self.curTraceData = np.zeros([b_pnts, v_pnts]) #np.zeros([self.bPoints,self.vPoints])
        self.noiseTraceData =np.zeros([b_pnts, v_pnts])     #np.zeros([self.bPoints,self.vPoints])
        self.curRetraceData = np.zeros([b_pnts, v_pnts]) #np.zeros([self.bPoints,self.vPoints])
        self.noiseRetraceData = np.zeros([b_pnts, v_pnts]) #np.zeros([self.bPoints,self.vPoints])
        self.biasVals = np.linspace(float(v_min),float(v_max), num = int(v_pnts))
        self.fieldVals = np.linspace(float(b_min),float(b_max), num = int(b_pnts))
        self.x0, self.x1 = (self.extent[0], self.extent[1])
        self.y0, self.y1 = (self.extent[2], self.extent[3])
        self.xscale, self.yscale = (self.x1-self.x0) / self.curTraceData.shape[0], (self.y1-self.y0) / self.curTraceData.shape[1]
        self.startSweep.setEnabled(False)
        self.abortSweep.setEnabled(True)
        self.magnetPower.setEnabled(False)
        self.blink.setEnabled(False)
        self.biasSweepMode.setEnabled(False)
        self.prelim.setEnabled(False)
        self.fieldMinSetValue.setReadOnly(True)
        self.fieldMaxSetValue.setReadOnly(True)
        self.fieldPointsSetValue.setReadOnly(True)
        self.fieldSpeedSetValue.setReadOnly(True)
        self.biasMinSetValue.setReadOnly(True)
        self.biasMaxSetValue.setReadOnly(True)
        self.biasPointsSetValue.setReadOnly(True)
        self.biasSpeedSetValue.setReadOnly(True)
        self.tracePlot.setImage(self.curTraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.retracePlot.setImage(self.curRetraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.liveTracePlotStatus = False
        self.liveRetracePlotStatus = False
        self.toggleRetraceLineCut()
        self.toggleTraceLineCut()
        #self.plotNoPlot = 0
        self.abortFlag = False
        if self.sweepParamDict['sweep mode'] == 0:
            self.isData = True
            self.sweepMinMax(self.settingsDict['Magnet device'])
            
        elif  self.sweepParamDict['sweep mode'] == 1:
            self.isData = True
            self.sweepFromZero(self.settingsDict['Magnet device'])


    @inlineCallbacks
    def abortSweepFunc(self, magpower, bVal, vVal, c = None):
        print 'aborting sweep'
        #DAC OUTPUTS
        
        #DAC out channel that outputs DC bias (1 through 4)
        DAC_out = self.settingsDict['nsot bias output'] - 1
        #DAC out channel that switches between 0 and 5 volts to toggle feedback off then on (aka blink)
        DAC_blink = self.settingsDict['blink'] - 1
        #DAC channel that sets the voltage setpoint for the Toellner power supply
        DAC_set_volt = self.settingsDict['toellner volts'] - 1
        #DAC channel that sets the current setpoint for the Toellner power supply
        DAC_set_current = self.settingsDict['toellner current'] - 1
        
        #DAC INPUTS
        
        #DAC in channel that reads DC bias (1 through 4)
        DAC_in_ref = self.settingsDict['nsot bias input'] - 1

        print 'Aborting sweep from applied field of ', bVal,'T and nSOT bias of ', vVal, 'V' 
        print 'Ramping nSOT bias to zero'
        if vVal != 0:
            yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref], [vVal], [0], abs(int(vVal * 1000)), 10000)
        else:
            pass
        yield self.sleep(1)
        print 'Sweeping magnetic field back to zero'
        if magpower == 'IPS 120-10':
            if bVal != 0:
                yield self.ips.set_control(3)
                #Go to 0 field
                yield self.ips.set_targetfield(0)
                yield self.ips.set_activity(2)
                #Set control method back to local control 
                yield self.ips.set_control(2)
            else:
                pass
        
        elif magpower == 'Toellner 8851':
            if bVal != 0:
                yield self.toeSweepField(bVal, 0, 0.1)
                yield self.dac.set_voltage(DAC_set_volt, 0)
                yield self.dac.set_voltage(DAC_set_current, 0)
            else:
                pass
                
        self.refreshInterface()
            
    def refreshInterface(self):
        self.startSweep.setEnabled(True)
        self.abortSweep.setEnabled(False)
        self.magnetPower.setEnabled(True)
        self.blink.setEnabled(True)
        self.biasSweepMode.setEnabled(True)

        self.prelim.setEnabled(True)

        self.fieldMinSetValue.setReadOnly(False)
        self.fieldMaxSetValue.setReadOnly(False)

        self.fieldPointsSetValue.setReadOnly(False)
        self.fieldSpeedSetValue.setReadOnly(False)
        self.biasMinSetValue.setReadOnly(False)
        self.biasMaxSetValue.setReadOnly(False)
        self.biasPointsSetValue.setReadOnly(False)
        self.biasSpeedSetValue.setReadOnly(False)
            
    @inlineCallbacks
    def sweepMinMax(self, magpower, c = None):
        B_min, B_max = self.sweepParamDict['B_min'], self.sweepParamDict['B_max']
        V_min, V_max = self.sweepParamDict['V_min'], self.sweepParamDict['V_max']
        B_pnts, V_pnts = int(self.sweepParamDict['B_pnts']), int(self.sweepParamDict['V_pnts'])
        V_range = np.absolute(V_max - V_min)
        B_rate = self.sweepParamDict['B_rate']
        delay = int(1000 * self.sweepParamDict['delay'])
        
        B_space = np.linspace(B_min, B_max, B_pnts)
        
        #DAC OUTPUTS
        
        #DAC out channel that outputs DC bias (1 through 4)
        DAC_out = self.settingsDict['nsot bias output'] - 1
        #DAC out channel that switches between 0 and 5 volts to toggle feedback off then on (aka blink)
        DAC_blink = self.settingsDict['blink'] - 1
        #DAC channel that sets the voltage setpoint for the Toellner power supply
        DAC_set_volt = self.settingsDict['toellner volts'] - 1
        #DAC channel that sets the current setpoint for the Toellner power supply
        DAC_set_current = self.settingsDict['toellner current'] - 1
        
        
        #DAC INPUTS
        
        #DAC in channel that reads DC bias (1 through 4)
        DAC_in_ref = self.settingsDict['nsot bias input'] - 1
        #DAC in channel that read DC signal (1 through 4)
        V_out = self.settingsDict['feedback DC input'] - 1
        #DAC in channel that read DC signal proportional to AC signal (1 through 4)
        dIdV_out = self.settingsDict['feedback AC input'] - 1
        #DAC in channel to read noise measurement
        noise = self.settingsDict['noise input'] - 1


        #AC excitation information for quasi dI/dV measurement. Frequency should be larger than 
        # ~2 kHz to avoid being filtered out by the lock in AC coupling high pass filter.  
        #THIS FUNCTIONALITY IS DISABLED AND MUST BE SET MANUALLY ON THE SR830
        #AC Oscillation amplitude
        vac_amp = self.acSettingsDict['amp']
        #Frequency in kilohertz
        frequency = self.acSettingsDict['freq']
        
        file_info = yield self.dv.new("nSOT vs. Bias Voltage and Field", ['Trace Index', 'B Field Index','Bias Voltage Index','B Field','Bias Voltage'],['DC SSAA Output','Noise', 'dI/dV'])
        self.dvFileName = file_info[1]
        self.lineEdit_ImageNum.setText(file_info[1][0:5])
        session     = ''
        for folder in file_info[0][1:]:
            session = session + '\\' + folder
        self.lineEdit_ImageDir.setText(r'\.datavault' + session)
        print 'DataVault setup complete'

        if magpower == 'Toellner 8851':
            yield self.dac.set_voltage(DAC_out, 0)
            #If minimum bias voltage is not zero, sweep bias to minimum value, 1mV per step with a reasonably short delay
            if V_min != 0:
                tmp = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [V_min], int(V_min * 1000), 1000)
            else:
                pass
        
            for i in range(0, B_pnts):
                
                if i == 0:

                    if self.abortFlag == False:
                        pass
                    else:
                        yield self.abortSweepFunc(magpower, 0, V_min)
                        break
                    
                    if B_space[0] != 0:
                        print 'Ramping field to ' + str(B_space[0])+'.'
                        yield self.toeSweepField(0, B_space[0], B_rate)
                    else:
                        pass
                else:
                    if self.abortFlag == False:
                        pass
                    else:
                        yield self.abortSweepFunc(magpower, B_space[i-1], V_min)
                        break
                    yield self.toeSweepField(B_space[i-1], B_space[i], B_rate)
                    
                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])
                
                print 'Blinking prior to sweep'
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_min)
                    break
                        
                #Sweep from minimum to maximum bias voltage
                print 'Ramping up nSOT bias voltage from ' + str(V_min) + ' to ' + str(V_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_min], [V_max], V_pnts, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, V_pnts):
                    formated_data.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data)

                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_max)
                    break
                
                #Sweep from maximum to minimum bias voltage
                print 'Ramping nSOT bias voltage back down from ' + str(V_max) + ' to ' + str(V_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_max], [V_min], V_pnts, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, V_pnts):
                    formated_data.append((1, i, V_pnts - 1 - j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data[::-1])
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_min)
                    break
                
            #If minimum bias voltage is not zero, sweep bias back to zero, 1mV per step with a reasonably short delay
            if V_min != 0:
                tmp = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_min], [0], int(V_min * 1000), 1000)
            else:
                pass
    
            yield self.dac.set_voltage(DAC_out, 0)
            
            #Go to zero field and set power supply voltage setpoint to zero.
            self.toeSweepField(B_space[-1], 0, B_rate)
            yield self.dac.set_voltage(DAC_set_volt, 0)
            yield self.dac.set_voltage(DAC_set_current, 0)
        
        elif magpower == 'IPS 120-10':
            yield self.ips.set_control(3)
            yield self.ips.set_comm_protocol(6)
            yield self.ips.set_control(2)
            
            yield self.sleep(0.25)
            
            yield self.ips.set_control(3)
            yield self.ips.set_fieldsweep_rate(B_rate)
            yield self.ips.set_control(2)
            
            #ramp voltage to zero if still at setpoint
            if np.absolute(self.setpntDict['bias']) > 0.01:
                step = int(np.absolute(self.setpntDict['bias'])) * 1000
                tmp = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref], [self.setpntDict['bias']], [0], step, 2000)
                
            yield self.dac.set_voltage(DAC_out, 0)
        
            #If minimum bias voltage is not zero, sweep bias to minimum value, 1mV per step with a reasonably short delay
            if V_min != 0:
                tmp = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [V_min], int(V_min * 1000), 1000)
            else:
                pass
        
            for i in range(0, B_pnts):
                t0 = time.time()
                yield self.ips.set_control(3)
                yield self.ips.set_targetfield(B_space[i])
                yield self.ips.set_control(2)
                
                yield self.ips.set_control(3)
                yield self.ips.set_activity(1)
                yield self.ips.set_control(2)

                print 'Setting field to ' + str(B_space[i])
                #wait for field to be reached
                while True:
                    yield self.ips.set_control(3)
                    curr_field = yield self.ips.read_parameter(7)
                    yield self.ips.set_control(2)
                    if float(curr_field[1:]) <= B_space[i]+0.00001 and float(curr_field[1:]) >= B_space[i]-0.00001:
                        break
                    if time.time() - t0 > 1:
                        yield self.ips.set_control(3)
                        yield self.ips.set_targetfield(B_space[i])
                        yield self.ips.set_control(2)
                        
                        yield self.ips.set_control(3)
                        yield self.ips.set_activity(1)
                        yield self.ips.set_control(2)
                        t0 = time.time()
                        print 'restarting loop'
                    yield self.sleep(0.25)
                    
                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])
                
                print 'Blinking prior to sweep'
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_min)
                    break

                #Sweep from minimum to maximum bias voltage
                print 'Ramping up nSOT bias voltage from ' + str(V_min) + ' to ' + str(V_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_min], [V_max], V_pnts, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, V_pnts):
                    formated_data.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_max)
                    break

                #Sweep from maximum to minimum bias voltage
                print 'Ramping nSOT bias voltage back down from ' + str(V_max) + ' to ' + str(V_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_max], [V_min], V_pnts, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, V_pnts):
                    formated_data.append((1, i, V_pnts - 1 - j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data[::-1])
                
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i],V_min)
                    break
            
            #If minimum bias voltage is not zero, sweep bias back to zero, 1mV per step with a reasonably short delay
            if V_min != 0:
                tmp = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_min], [0], int(V_min * 1000), 1000)
            else:
                pass

            yield self.dac.set_voltage(DAC_out, 0)
            yield self.sleep(0.25)
            print 'Set nSOT bias to zero, sweeping field to 0T.'
            
            #Go to 0 field
            yield self.ips.set_control(3)
            yield self.ips.set_targetfield(0)
            yield self.ips.set_control(2)
            
                
            yield self.ips.set_control(3)
            yield self.ips.set_activity(1)
            yield self.ips.set_control(2)
            #wait for field to be reached
            t0 = time.time()
            while True:
                yield self.ips.set_control(3)
                curr_field = yield self.ips.read_parameter(7)
                yield self.ips.set_control(2)
                if float(curr_field[1:]) <= 0.00001 and float(curr_field[1:]) >= -0.00001:
                    break
                if time.time() - t0 > 1:
                    yield self.ips.set_control(3)
                    yield self.ips.set_targetfield(0)
                    yield self.ips.set_control(2)
                    
                    yield self.ips.set_control(3)
                    yield self.ips.set_activity(1)
                    yield self.ips.set_control(2)
                    t0 = time.time()
                    print 'restarting loop'
                    if self.abortFlag == True:
                        break
                yield self.sleep(0.25)

            #Set control method back to local control 
            yield self.ips.set_control(2)
        print 'Sweep complete'
        self.refreshInterface()
        #Wait until all plots are appropriately updated before saving screenshot
        yield self.sleep(0.25)
        self.saveDataToSessionFolder()
        
    @inlineCallbacks
    def sweepFromZero(self, magpower, c = None):
        B_min, B_max = self.sweepParamDict['B_min'], self.sweepParamDict['B_max']
        V_min, V_max = self.sweepParamDict['V_min'], self.sweepParamDict['V_max']
        B_pnts, V_pnts = int(self.sweepParamDict['B_pnts']), int(self.sweepParamDict['V_pnts'])
        V_range = np.absolute(V_max - V_min)
        positive_points = int(np.absolute(V_pnts * V_max) / V_range)
        negative_points = V_pnts - positive_points

        B_rate = self.sweepParamDict['B_rate']
        delay = 1000 * self.sweepParamDict['delay']
        B_space = np.linspace(B_min, B_max, B_pnts)
        
        #DAC OUTPUTS
        
        #DAC out channel that outputs DC bias (1 through 4)
        DAC_out = self.settingsDict['nsot bias output'] - 1
        #DAC out channel that switches between 0 and 5 volts to toggle feedback off then on (aka blink)
        DAC_blink = self.settingsDict['blink'] - 1
        #DAC channel that sets the voltage setpoint for the Toellner power supply
        DAC_set_volt = self.settingsDict['toellner volts'] - 1
        #DAC channel that sets the current setpoint for the Toellner power supply
        DAC_set_current = self.settingsDict['toellner current'] - 1
        
        
        #DAC INPUTS
        
        #DAC in channel that reads DC bias (1 through 4)
        DAC_in_ref = self.settingsDict['nsot bias input'] - 1
        #DAC in channel that read DC signal (1 through 4)
        V_out = self.settingsDict['feedback DC input'] - 1
        #DAC in channel that read DC signal proportional to AC signal (1 through 4)
        dIdV_out = self.settingsDict['feedback AC input'] - 1
        #DAC in channel to read noise measurement
        noise = self.settingsDict['noise input'] - 1
        
        #ramp voltage to zero if still at setpoint
        if np.absolute(self.setpntDict['bias']) > 0.01:
            step = int(np.absolute(self.setpntDict['bias'])) * 1000
            tmp = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref], [self.setpntDict['bias']], [0], step, 2000)
            


        #AC excitation information for quasi dI/dV measurement. Frequency should be larger than 
        # ~2 kHz to avoid being filtered out by the lock in AC coupling high pass filter.  
        #THIS FUNCTIONALITY IS DISABLED AND MUST BE SET MANUALLY ON THE SR830
        #AC Oscillation amplitude
        vac_amp = self.acSettingsDict['amp']
        #Frequency in kilohertz
        frequency = self.acSettingsDict['freq']
        file_info = yield self.dv.new("nSOT vs. Bias Voltage and Field", ['Trace Index', 'B Field Index','Bias Voltage Index','B Field','Bias Voltage'],['DC SSAA Output','Noise', 'dI/dV'])
        self.dvFileName = file_info[1]
        self.lineEdit_ImageNum.setText(file_info[1][0:5])
        session     = ''
        for folder in file_info[0][1:]:
            session = session + '\\' + folder
        self.lineEdit_ImageDir.setText(r'\.datavault' + session)
        print 'DataVault setup complete'
        
        if magpower == 'Toellner 8851':
            for i in range (0, B_pnts):
            
                if i == 0:
                    if B_space[0] != 0:
                        print 'Ramping field to ' + str(B_space[0])+'.'
                        yield self.toeSweepField(0, B_space[0], B_rate)
                    else:
                        pass
                else:
                    yield self.toeSweepField(B_space[i-1], B_space[i], B_rate)

                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])

                #Set bias voltage to zero and blink
                yield self.dac.set_voltage(DAC_out,0)
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], 0)
                    break
                
                #Sweep from zero volts to maximum bias voltage
                print 'Ramping up nSOT bias voltage from zero to ' + str(V_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [V_max], positive_points, delay)
    
                #Reform data and add to data vault
                #formated_data = []
                data_uptrace = []
                for j in range(0, positive_points):
                    data_uptrace.append((0, i, negative_points + j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_max)
                    break

                
                #Sweep from maximum bias voltage to zero volts and blink
                print 'Ramping nSOT bias voltage back down from ' + str(V_max) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_max], [0], positive_points, delay)

                #formated_data = []
                data_upretrace = []
                for j in range(0, positive_points):
                    data_upretrace.append((1, i, V_pnts - j - 1, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], 0)
                    break
                
                #Sweep from zero volts to minimum bias voltage
                print 'Ramping down nSOT bias voltage from zero to ' + str(V_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [V_min], negative_points, delay)
    
                #Reform data and add to data vault
                #formated_data = []
                data_downtrace = []
                for j in range(0, negative_points):
                    data_downtrace.append((0, i, negative_points  - 1 - j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                
                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_min)
                    break
                
                #Sweep from minimum bias voltage to zero volts
                print 'Ramping nSOT bias voltage up down from ' + str(V_min) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_min], [0], negative_points, delay)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], 0)
                    break

                #Reform data and add to data vault
                #formated_data = []
                data_downretrace = []
                for j in range(0, negative_points):
                    data_downretrace.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                trace_data = []
                retrace_data = []
                trace_data = data_downtrace[::-1] + data_uptrace
                retrace_data = data_downretrace + data_upretrace[::-1]
                
                yield self.dv.add(trace_data)
                yield self.updatePlots(trace_data)
                yield self.dv.add(retrace_data)
                yield self.updatePlots(retrace_data)

            yield self.dac.set_voltage(DAC_out, 0)
            
            #Go to zero field and set power supply voltage setpoint to zero.
            yield self.toeSweepField(B_space[-1], 0, B_rate)
            yield self.dac.set_voltage(DAC_set_volt, 0)
        
        elif magpower == 'IPS 120-10': 
            yield self.ips.set_control(3)
            yield self.ips.set_comm_protocol(6)
            yield self.ips.set_control(2)
            yield self.sleep(0.25)
            
            yield self.ips.set_control(3)
            yield self.ips.set_fieldsweep_rate(B_rate)
            yield self.ips.set_control(2)
            
            for i in range (0, B_pnts):
                t0 = time.time()
                yield self.ips.set_control(3)
                yield self.ips.set_targetfield(B_space[i])
                yield self.ips.set_control(2)
                
                yield self.ips.set_control(3)
                yield self.ips.set_activity(1)
                yield self.ips.set_control(2)
                #wait for field to be reached
                while True:
                    yield self.ips.set_control(3)
                    curr_field = yield self.ips.read_parameter(7)
                    yield self.ips.set_control(2)
                    if float(curr_field[1:]) <= B_space[i]+0.00001 and float(curr_field[1:]) >= B_space[i]-0.00001:
                        break
                    if time.time() - t0 > 1:
                        yield self.ips.set_control(3)
                        yield self.ips.set_targetfield(B_space[i])
                        yield self.ips.set_control(2)
                        
                        yield self.ips.set_control(3)
                        yield self.ips.set_activity(1)
                        yield self.ips.set_control(2)
                        yield self.sleep(0.5)
                        t0 = time.time()
                    yield self.sleep(0.25)
                    
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], 0)
                    break


                #Set bias voltage to zero and blink
                yield self.dac.set_voltage(DAC_out,0)
                yield self.blinkFunc()
                
                #Sweep from zero volts to maximum bias voltage
                print 'Ramping up nSOT bias voltage from zero to ' + str(V_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [V_max], positive_points, delay)
    
                #Reform data and add to data vault
                data_uptrace = []
                for j in range(0, positive_points):
                    data_uptrace.append((0, i, negative_points + j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
              
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], V_max)
                    break
       
                #Sweep from maximum bias voltage to zero volts and blink
                print 'Ramping nSOT bias voltage back down from ' + str(V_max) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_max], [0], positive_points, delay)

                #formated_data = []
                data_upretrace = []
                for j in range(0, positive_points):
                    data_upretrace.append((1, i, V_pnts - j - 1, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], 0)
                    break

                yield self.blinkFunc()

                
                #Sweep from zero volts to minimum bias voltage
                print 'Ramping down nSOT bias voltage from zero to ' + str(V_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [V_min], negative_points, delay)
    
                #Reform data and add to data vault

                data_downtrace = []
                for j in range(0, negative_points):
                    data_downtrace.append((0, i,negative_points     - 1 - j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i],V_min)
                    break
                
                #Sweep from minimum bias voltage to zero volts
                print 'Ramping nSOT bias voltage up from ' + str(V_min) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [V_min], [0], negative_points, delay)

                #Reform data and add to data vault

                data_downretrace = []
                for j in range(0, negative_points):
                    data_downretrace.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                trace_data = []
                retrace_data = []
                trace_data = data_downtrace[::-1] + data_uptrace
                retrace_data = data_downretrace + data_upretrace[::-1]
                yield self.dv.add(trace_data)
                yield self.updatePlots(trace_data)
                yield self.dv.add(retrace_data)
                yield self.updatePlots(retrace_data)                
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield self.abortSweepFunc(magpower, B_space[i], 0)
                    break

            yield self.dac.set_voltage(DAC_out, 0)
            
            #Go to 0 field
            yield self.ips.set_control(3)
            yield self.ips.set_targetfield(0)
            yield self.ips.set_activity(2)
            
            yield self.ips.set_control(3)
            yield self.ips.set_activity(1)
            yield self.ips.set_control(2)
            
            while True:
                yield self.ips.set_control(3)
                curr_field = yield self.ips.read_parameter(7)
                yield self.ips.set_control(2)
                if float(curr_field[1:]) <= 0.00001 and float(curr_field[1:]) >= -0.00001:
                    break
                if time.time() - t0 > 1:
                    yield self.ips.set_control(3)
                    yield self.ips.set_targetfield(0)
                    yield self.ips.set_control(2)
                    
                    yield self.ips.set_control(3)
                    yield self.ips.set_activity(1)
                    yield self.ips.set_control(2)
                    t0 = time.time()
                    print 'restarting loop'
                    if self.abortFlag == True:
                        break
                yield self.sleep(0.25)

            #Set control method back to local control 
            yield self.ips.set_control(2)    
        print 'Sweep Complete'
        self.refreshInterface()
        #Wait until all plots are appropriately updated before saving screenshot
        yield self.sleep(0.25)
        self.saveDataToSessionFolder()
    
    @inlineCallbacks
    def blinkFunc(self, c = None):
        yield self.blink_server.set_voltage(self.settingsDict['blink']-1, 5)
        yield self.sleep(0.25)
        yield self.blink_server.set_voltage(self.settingsDict['blink']-1, 0)
        yield self.sleep(0.25)
    
    @inlineCallbacks
    def toeSweepField(B_i, B_f, B_speed, c = None):
        DAC_set_volt, DAC_set_current = self.settingsDict['toellner volts'] - 1, self.settingsDict['toellner current'] - 1
        DAC_in_ref = self.settingsDict['nsot bias input']
        #Toellner voltage set point / DAC voltage out conversion [V_Toellner / V_DAC]
        VV_conv = 3.20
        #Toellner current set point / DAC voltage out conversion [I_Toellner / V_DAC]
        IV_conv = 1.0 

        #Field / Current ratio on the dipper magnet (0.132 [Tesla / Amp])
        IB_conv = 0.132

        #Starting and ending field values in Tesla, use positive field values for now
        B_range = np.absolute(B_f - B_i)

        #Delay between DAC steps in microseconds
        magnet_delay = 5000
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
        ramp_steps = int(np.absolute(V_setpoint - V_initial) * 1000)
        ramp_delay = 1000
        yield self.dac_toe.buffer_ramp([DAC_set_volt], [DAC_in_ref], [V_initial], [V_setpoint], ramp_steps, ramp_delay)
        
        #Sweeps field from B_i to B_f
        print 'Sweeping field from ' + str(B_i) + ' to ' + str(B_f)+'.'
        yield self.dac_toe.buffer_ramp([DAC_set_current],[DAC_in_ref],[v_start],[v_end], sweep_steps, magnet_delay)

        
    def setSessionFolder(self, folder):
        self.sessionFolder = folder
            
    def saveDataToSessionFolder(self):
        try:
            p = QtGui.QPixmap.grabWindow(self.winId())
            a = p.save(self.sessionFolder + '\\' + self.dvFileName + '.jpg','jpg')
            if not a:
                print "Error saving nSOT data picture"
        except Exception as inst:
            print 'nSOTChar error: ', inst
            print 'on line: ', sys.exc_traceback.tb_lineno
            
    def lockInterface(self):
        self.biasSweepMode.setEnabled(False)
        self.blink.setEnabled(False)
        self.magnetPower.setEnabled(False)
        self.fieldMinSetValue.setEnabled(False)
        self.fieldMaxSetValue.setEnabled(False)
        self.fieldPointsSetValue.setEnabled(False)
        self.fieldStepsInc.setEnabled(False)
        self.fieldSpeedSetValue.setEnabled(False)
        self.biasMinSetValue.setEnabled(False)
        self.biasMaxSetValue.setEnabled(False)
        self.biasPointsSetValue.setEnabled(False)
        self.biasStepsInc.setEnabled(False)
        self.biasSpeedSetValue.setEnabled(False)
        self.startSweep.setEnabled(False)
        self.prelim.setEnabled(False)
        self.abortSweep.setEnabled(False)
        self.acSetOpen.setEnabled(False)
        
    def unlockInterface(self):
        self.biasSweepMode.setEnabled(True)
        self.blink.setEnabled(True)
        self.magnetPower.setEnabled(True)
        self.fieldMinSetValue.setEnabled(True)
        self.fieldMaxSetValue.setEnabled(True)
        self.fieldPointsSetValue.setEnabled(True)
        self.fieldStepsInc.setEnabled(True)
        self.fieldSpeedSetValue.setEnabled(True)
        self.biasMinSetValue.setEnabled(True)
        self.biasMaxSetValue.setEnabled(True)
        self.biasPointsSetValue.setEnabled(True)
        self.biasStepsInc.setEnabled(True)
        self.biasSpeedSetValue.setEnabled(True)
        self.startSweep.setEnabled(True)
        self.prelim.setEnabled(True)
        self.abortSweep.setEnabled(True)
        self.acSetOpen.setEnabled(True)
            
    def closeEvent(self, e):
        pass

#Window for setting the AC excitation for dI/dV sweeps, probably will never be used
class acSettings(QtGui.QDialog, Ui_acSet):
    def __init__(self, acDict, parent = None):
        super(acSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.acDict = acDict
        #self.acSettingsDict = {'freq' : 4.0, 'amp' : 2.0}
        self.window = parent

        self.acFreqValue.setValue(self.acDict['freq'])
        self.acAmpValue.setValue(self.acDict['amp'])

        self.cancelACSet.clicked.connect(self._close)
        self.okACSet.clicked.connect(self._ok)

    def closeEvent(self, e):
        self.window.acSetOpen.setEnabled(True)
        self.close()

    def _close(self):
        self.window.acSetOpen.setEnabled(True)
        self.close()
    def _ok(self):
        self.acDict = {'freq' : float(self.acFreqValue.value()), 'amp' : float(self.acAmpValue.value())}
        self.window.acSettingsDict = copy.copy(self.acDict)
        
        self.window.acSetOpen.setEnabled(True)
        self.close()

#Window for reminding user to turn Toellner output on
class toellnerReminder(QtGui.QDialog, Ui_toeReminder):
    def __init__(self, parent = None):
        super(toellnerReminder, self).__init__(parent)
        self.window = parent
        self.setupUi(self)
        
        self.yes.clicked.connect(self.continueSweep)
        self.no.clicked.connect(self.backUp)
        
    def continueSweep(self):
        self.accept()
        
    def backUp(self):
        self.reject()
        
    def closeEvent(self, e):
        self.reject()

#Window for finalizing sweep parameters, inherits the list of sweep parameters from the MainWindow checkSweep function
class DialogBox(QtGui.QDialog, Ui_DialogBox):
    def __init__(self, sweepParams, parent = None):
        super(DialogBox, self).__init__(parent)
        
        self.sweepParamDict = sweepParams
        
        self.window = parent
        self.setupUi(self)
        
        self.fieldMinValue.setText(str(self.sweepParamDict['B_min']))
        self.fieldMinValue.setStyleSheet("QLabel#fieldMinValue {color: rgb(168,168,168); font-size: 10pt}")
        self.fieldMaxValue.setText(str(self.sweepParamDict['B_max']))
        self.fieldMaxValue.setStyleSheet("QLabel#fieldMaxValue {color: rgb(168,168,168); font-size: 10pt}")
        self.fieldIncValue.setText(str(self.sweepParamDict['B_pnts']))
        self.fieldIncValue.setStyleSheet("QLabel#fieldIncValue {color: rgb(168,168,168); font-size: 10pt}")
        self.fieldSpeedValue.setText(str(self.sweepParamDict['B_rate']))
        self.fieldSpeedValue.setStyleSheet("QLabel#fieldSpeedValue {color: rgb(168,168,168); font-size: 10pt}")

        self.biasMinValue.setText(str(self.sweepParamDict['V_min']))
        self.biasMinValue.setStyleSheet("QLabel#biasMinValue {color: rgb(168,168,168); font-size: 10pt}")
        self.biasMaxValue.setText(str(self.sweepParamDict['V_max']))
        self.biasMaxValue.setStyleSheet("QLabel#biasMaxValue {color: rgb(168,168,168); font-size: 10pt}")
        self.biasIncValue.setText(str(self.sweepParamDict['V_pnts']))
        self.biasIncValue.setStyleSheet("QLabel#biasIncValue {color: rgb(168,168,168); font-size: 10pt}")
        self.biasSpeedValue.setText(str(self.sweepParamDict['delay']))
        self.biasSpeedValue.setStyleSheet("QLabel#biasSpeedValue {color: rgb(168,168,168); font-size: 10pt}")
        
        if self.sweepParamDict['Magnet device'] == 'IPS 120-10':
            self.magnetPowerSupply.setText('Oxford IPS 120-10 Magnet Power Supply')
            self.magnetPowerSupply.setStyleSheet("QLabel#magnetPowerSupply {color: rgb(168,168,168); font-size: 10pt}")
        elif self.sweepParamDict['Magnet device'] == 'Toellner 8851':
            self.magnetPowerSupply.setText('Toellner 8851 Power Supply')
            self.magnetPowerSupply.setStyleSheet("QLabel#magnetPowerSupply {color: rgb(168,168,168); font-size: 10pt}")
        if self.sweepParamDict['sweep mode'] == 0:
            self.sweepModeSetting.setText('Max to Min')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(168,168,168); font-size: 10pt}")
        elif self.sweepParamDict['sweep mode'] ==1:
            self.sweepModeSetting.setText('Min to Max')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(168,168,168); font-size: 10pt}")
        elif self.sweepParamDict['sweep mode'] ==2:
            self.sweepModeSetting.setText('Zero to Max/Min')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(168,168,168); font-size: 10pt}")

        if self.sweepParamDict['blink mode']== 0:
            self.blinkOrNot.setText('Enabled')
            self.blinkOrNot.setStyleSheet("QLabel#blinkOrNot {color: rgb(168,168,168); font-size: 10pt}")
        elif self.sweepParamDict['blink mode'] == 1:
            self.blinkOrNot.setText('Disabled')
            self.blinkOrNot.setStyleSheet("QLabel#blinkOrNot {color: rgb(168,168,168); font-size: 10pt}")
        if self.sweepParamDict['sweep time'] != "infinite":
            self.sweepTime.setText('Sweep Time Estimate: ' + self.sweepParamDict['sweep time'])
            self.sweepTime.setStyleSheet("QLabel#sweepTime {color: rgb(168,168,168); font-size: 10pt}")
        else:
            self.sweepTime.setTextFormat(1)
            self.sweepTime.setText('<html><head/><body><p><span style=" font-size:10pt; color:#ffffff;">Sweep will take &#8734; time</span></p></body></html>')

        self.startSweepReally.clicked.connect(self.testSweep)
        self.beIndecisive.clicked.connect(self.exitDialog)

    #If accepted, runs the sweep
    def testSweep(self):
        self.accept()
    def exitDialog(self):
        #self.window.startSweep.setEnabled(True)
        self.reject()
    def closeEvent(self, e):
        self.window.startSweep.setEnabled(True)
        self.window.abortSweep.setEnabled(False)

#Window for doing preliminary sweeps of the nSOT
class preliminarySweep(QtGui.QDialog, Ui_prelimSweep):
    def __init__(self, reactor, dv, dac, settings, parent = None):
        super(preliminarySweep, self).__init__(parent)
        self.window = parent
        self.reactor = reactor
        self.setupUi(self)
        
        self.setupPlot()
        self.dv = dv
        self.dac = dac
        
        self.settingsDict = settings
        
        self.data = None
        self.fitPoints = 1
        self.fitPlotItem = pg.PlotCurveItem()
        self.dataPlotItem = pg.PlotCurveItem()
        self.critCurrLine.setReadOnly(True)
        self.parRes.setReadOnly(True)

        self.startSweep.clicked.connect(lambda: self.sweep(self.reactor))
        self.showFitBtn.clicked.connect(self.showFitFunc)
        self.btnAction = 'sweep'

        self.flag_IcLineShowing = False
        self.pushButton_Show.clicked.connect(self.toggleIcMeasurementLine)

        self.closeWin.clicked.connect(self._close)

    def toggleIcMeasurementLine(self):
        if self.flag_IcLineShowing:
            self.sweepPlot.removeItem(self.IcLine)
        else:
            self.sweepPlot.addItem(self.IcLine)
        self.flag_IcLineShowing = not self.flag_IcLineShowing

    def refreshSweep(self):
        self.startSweep.setEnabled(True)
        self.newSweep.setEnabled(False)
        
    def showFitFunc(self):
        if not self.fitPoints is None:
            if self.showFitBtn.text() == 'Show Fit':
                self.fitPlotItem.setData(x = self.fitPoints[0:2], y = self.fitPoints[2::], pen = pg.mkPen(color = (250, 0, 0)))
                self.sweepPlot.addItem(self.fitPlotItem)
                self.showFitBtn.setText('Hide Fit')
            elif self.showFitBtn.text() == 'Hide Fit':
                self.sweepPlot.removeItem(self.fitPlotItem)
                self.showFitBtn.setText('Show Fit')
                
    def setupPlot(self):
        self.win = pg.GraphicsWindow(parent = self.plotSweepFrame)
        self.sweepPlot = self.win.addPlot()
        self.win.setGeometry(QtCore.QRect(0, 0, 435, 290))
        self.sweepPlot.setLabel('left', 'DC Feedback Voltage', units = 'V')
        self.sweepPlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.sweepPlot.showAxis('right', show = True)
        self.sweepPlot.showAxis('top', show = True)
        self.sweepPlot.setXRange(0,1)
        self.sweepPlot.setYRange(0,2)
        self.sweepPlot.enableAutoRange(enable = True)
        proxy = pg.SignalProxy(self.sweepPlot.scene().sigMouseClicked ,slot=self.updateIC)
        # self.sweepPlot.scene().sigMouseClicked.connect(self.updateIC)
        self.IcLine = pg.InfiniteLine(pos = 0.0 , angle = 90, movable = True, pen = 'b', hoverPen = (50, 50, 200))
        self.IcLine.sigPositionChangeFinished.connect(self.updateIC)

    def updateIC(self, e):
        if not self.data is None:
            xVals = [x[1] for x in self.data]
            yVals = [x[2] for x in self.data]
            xscale = float((np.amax(xVals)) - float(np.amin(xVals))) / float((len(xVals) - 1))
            index = self.IcLine.value() / xscale
            ssaaRes = float(self.ssaaRes.value())*1000
            winding = float(self.ssaaWinding.value())
            yValue = yVals[index]
            I_c =  np.round(np.absolute((yValue) / (ssaaRes * winding)) * 1e6, decimals = 2)
            self.critCurrLine.setText(str(I_c))
                
    @inlineCallbacks
    def plotSweepData(self, data):
        self.data = data

        xVals = [x[1] for x in self.data]
        yVals = [x[2] for x in self.data]
        yield self.sleep(0.1)

        self.sweepPlot.plot(x = xVals, y = yVals, pen = 0.5)
        
        absX = np.absolute(xVals)
        zeroVolts = np.amin(absX)
        zeroIndex = np.argmin(absX)
        bigHalf = np.amax([len(xVals) - zeroIndex -1, zeroIndex])

        chi = 0
        if bigHalf>zeroIndex:
            j = zeroIndex + 5
            while chi / (len(xVals) - 2) < 1e-5 and j<len(xVals):
                p, chi, _, _, _ = np.polyfit(xVals[zeroIndex:j], yVals[zeroIndex:j], 1, full = True)
                j += 1
            j = int(0.9 * j)
            p, chi, _, _, _ = np.polyfit(xVals[zeroIndex:j], yVals[zeroIndex:j], 1, full = True)

        else:
            j = zeroIndex - 5
            while chi / (len(xVals) - 2) < 1e-5 and j >= 0:
                p, chi, _, _, _ = np.polyfit(xVals[j:zeroIndex], yVals[j:zeroIndex], 1, full = True)
                j -= 1
            j = int(0.9 * j)
            p, chi, _, _, _ = np.polyfit(xVals[j:zeroIndex], yVals[j:zeroIndex], 1, full = True)

        biasRes = float(self.biasRes.value())*1000
        shuntRes = float(self.shuntRes.value())
        ssaaRes = float(self.ssaaRes.value())*1000
        winding = float(self.ssaaWinding.value())

        alpha = shuntRes / (shuntRes + biasRes)

        deltaV_DAC = np.absolute(xVals[j] - xVals[zeroIndex])

        deltaV_F = np.absolute(yVals[j] - yVals[zeroIndex])
        
        self.fitPoints = [xVals[zeroIndex], xVals[j], yVals[zeroIndex], yVals[j]]

        if deltaV_F == 0:
            self.parRes.setText('Nan')
        else:
            ratio = np.absolute(deltaV_DAC / deltaV_F)
            r = np.round(alpha * (winding * ssaaRes * ratio - biasRes), decimals = 1)
            self.parRes.setText(str(r))
            
    def sleep(self, secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
    def _close(self):
        self.window.prelim.setEnabled(True)
        self.close()
        
    def closeEvent(self, e):
        self.window.prelim.setEnabled(True)
        self.close()
        
    def toggleStartBtn(self, state):
        reg = "QPushButton#" + 'startSweep'
        press = "QPushButton:pressed#" + 'startSweep'
        if state == 'sweep':
            regStr = reg + "{color: rgb(0,250,0);background-color:rgb(0,0,0);border: 2px solid rgb(0,250,0);border-radius: 5px}"
            pressStr = press + "{color: rgb(0,0,0); background-color:rgb(0,250,0);border: 2px solid rgb(0,250,0);border-radius: 5px}" 
            style = regStr + " " + pressStr
            self.startSweep.setText('Start Sweep')
            self.startSweep.setStyleSheet(style)
            self.btnAction = 'sweep'
        elif state == 'reset':
            regStr = reg + "{color: rgb(95,107,166);background-color:rgb(0,0,0);border: 2px solid rgb(95,107,166);border-radius: 5px}"
            pressStr = press + "{color: rgb(0,0,0); background-color:rgb(95,107,166);border: 2px solid rgb(95,107,166);border-radius: 5px}" 
            style = regStr + " " + pressStr
            self.startSweep.setText('Reset')
            self.startSweep.setStyleSheet(style)
            self.btnAction = 'reset'
            
    @inlineCallbacks
    def sweep(self, c):
        yield self.sleep(0.1)
        if self.btnAction == 'sweep':
            try:
                self.toggleStartBtn('reset')
                self.startSweep.setEnabled(False)
                
                self.sweepPlot.clear()
                #x = np.linspace(0,1, 100)+np.random.random()*10
                #y = np.linspace(2,3, 100)
                #self.plotSweepData(np.transpose([x,y]))
                
                #Sets sweep parameters
                biasMin = float(self.biasStart.value())
                biasMax = float(self.biasEnd.value())
                biasRange = abs(biasMax - biasMin)
                
                biasPoints = int(self.sweepPoints.value())
                delay = int(self.delay.value() * 1000)
                
                #Sets DAC Channels
                DAC_out = self.settingsDict['nsot bias output'] - 1
                DAC_blink = self.settingsDict['blink'] - 1
                
                DAC_in_ref = self.settingsDict['nsot bias input'] - 1
                DAC_in_sig = self.settingsDict['feedback DC input'] - 1
                DAC_in_noise = self.settingsDict['noise input'] - 1
                print DAC_in_sig, DAC_in_ref
                
                file_info = yield self.dv.new("nSOT Preliminary Sweep", ['Bias Voltage Index','Bias Voltage'],['DC SSAA Output','Noise'])
                self.dvFileName = file_info[1]
                self.lineEdit_ImageNum.setText(file_info[1][0:5])
                session     = ''
                for folder in file_info[0][1:]:
                    session = session + '\\' + folder
                self.lineEdit_ImageDir.setText(r'\.datavault' + session)
                        
                print 'DataVault setup complete'
                
                yield self.dac.set_voltage(DAC_out, 0)
                try:
                    yield self.window.blinkFunc()
                except Exception as inst:
                    print inst
                    print 'Blinks the problem yo'

                if biasMin != 0:
                    yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [0], [biasMin], abs(int(biasMin * 1000)), 1000)
                    yield self.sleep(1)

                #Do sweep
                print 'Ramping up nSOT bias voltage from ' + str(biasMin) + ' to ' + str(biasMax) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [biasMin], [biasMax], biasPoints, delay)

                formatted_data = []
                for j in range(0, biasPoints):
                        formatted_data.append((j, dac_read[0][j], dac_read[1][j], dac_read[2][j]))
                yield self.dv.add(formatted_data)

                yield self.plotSweepData(formatted_data)
                
                yield self.sleep(0.25)
                self.saveDataToSessionFolder()
                
                #Return to zero voltage gently
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [biasMax], [0], abs(int(biasMax * 1000)), 1000)
                yield self.sleep(0.25)
                yield self.dac.set_voltage(DAC_out, 0)
                self.startSweep.setEnabled(True)
                
            except Exception as inst:
                print inst
        elif self.btnAction == 'reset':
            self.toggleStartBtn('sweep')
            
    def saveDataToSessionFolder(self):
        try:
            p = QtGui.QPixmap.grabWindow(self.winId())
            #grab the sessionFolder name from the main window
            a = p.save(self.window.sessionFolder + '\\' + self.dvFileName + '.jpg','jpg')
            if not a:
                print "Error saving nSOT Prelim data picture"
        except Exception as inst:
            print 'nSOTChar Prelim error: ', inst
            print 'on line: ', sys.exc_traceback.tb_lineno
            
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
