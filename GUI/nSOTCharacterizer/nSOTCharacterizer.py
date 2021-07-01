import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import numpy as np
import pyqtgraph as pg
import time
import math
from nSOTScannerFormat import readNum, formatNum, printErrorInfo, saveDataToSessionFolder

path = sys.path[0] + r"\nSOTCharacterizer"
characterGUI = path + r"\character_GUI.ui"
dialogBox = path + r"\sweepCheck.ui"
prelimSweep = path + r"\preliminarySweep.ui"
toeReminder = path + r"\toeReminder.ui"
serlist = path + r"\requiredServers.ui"

Ui_MainWindow, QtBaseClass = uic.loadUiType(characterGUI)
Ui_DialogBox, QtBaseClass = uic.loadUiType(dialogBox)
Ui_prelimSweep, QtBaseClass = uic.loadUiType(prelimSweep)
Ui_toeReminder, QtBaseClass = uic.loadUiType(toeReminder)
Ui_ServerList, QtBaseClass = uic.loadUiType(serlist)

#Main characterization window with plots, sweep paramteres, etc.
class Window(QtWidgets.QMainWindow, Ui_MainWindow):
    newToeField = QtCore.pyqtSignal(float, float, float)

    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)
        #QtWidgets.QDialog.__init__(self)
        self.parent = parent
        self.reactor = reactor

        #Initialize GUI element
        self.setupUi(self)
        self.setupAdditionalUi()

        #By default empty the magnet power supply comboBox
        self.comboBox_magnetPower.clear()

        #Dictionaries of the wiring and instrument settings with some default values
        self.settingsDict = {
                'blink':                2, #1 index DAC or DC box channel
                'nsot bias output':     1, #1 index bias output on the DAC ADC
                'toellner volts':       4, #1 indexed output on the DAC ADC to control Toellner power supply voltage
                'toellner current':     3, #1 indexed output on the DAC ADC to control Toellner power supply current
                'nsot bias input':      4, #1 indexed input on the DAC ADC to read the nsot bias voltage
                'feedback DC input':    3, #1 indexed input on the DAC ADC to read the DC feedback signal
                'noise input':          2, #1 indexed input on the DAC ADC to read the noise
                'Magnet device':        'Toellner 8851', #Device used to control the magnetic field
        }

        #Dictionary of parameters defining the nSOT sweep
        self.sweepParamDict = { 'B_min' : 0,
                                'B_max' : 0.1,
                                'B_pnts' : 101,
                                'B_step' : 0.1/100,
                                'B_rate' : 1,
                                'V_min' : 0,
                                'V_max' : 1,
                                'V_pnts' : 501,
                                'V_step' : 1/500,
                                'delay' : 0.001,
                                'sweep mode' : 0,
                                'blink mode' : 0,
                                'sweep time' : '1 hours 0 minutes'}

        #Initialize plots
        self.plt_pos = [0, 0] #Position of the bottom left corner of the plot
        self.plt_scale = [0.1 / 101, 1 / 501] #Scale factor for the size of each pixel

        #Initialize empty arrays for the data for plotting
        self.curTraceData = np.zeros([101,501])
        self.noiseTraceData =np.zeros([101,501])
        self.curRetraceData = np.zeros([101,501])
        self.noiseRetraceData = np.zeros([101,501])

        self.updatePlots()

        #Starts a sweep
        self.push_startSweep.clicked.connect(lambda: self.startSweep())

        #Flag used to initiate an abort function in the middle of a sweep
        self.abortFlag = False
        self.push_abortSweep.clicked.connect(self.abortSweep)

        #Opens the preliminary sweep window
        self.push_prelim.clicked.connect(self.runPrelimSweep)

        #Toggles between number of steps and Tesla/Volts per step in the sweep parameter display in the main window
        self.push_fieldStepsInc.clicked.connect(self.toggleFieldSteps)
        self.fieldSIStat = 'num pnts'
        self.push_biasStepsInc.clicked.connect(self.toggleBiasSteps)
        self.biasSIStat = 'num pnts'

        #Adds/removes the ability to take line cuts in the displayed data
        self.liveTracePlotStatus = False #By default, do not automatically update the trace linecuts
        self.liveRetracePlotStatus = False #By default, do not automatically update the retrace linecuts
        self.push_liveTracePlot.clicked.connect(self.toggleTraceLineCut)
        self.push_liveRetracePlot.clicked.connect(self.toggleRetraceLineCut)

        #Shows/hides the color scales on the trace/retrace plots
        self.push_showTraceGrad.hide()
        self.push_hideTraceGrad.raise_()
        self.push_hideTraceGrad.clicked.connect(self.hideTraceHistogram)
        self.push_showTraceGrad.clicked.connect(self.showTraceHistogram)
        self.push_showRetraceGrad.hide()
        self.push_hideRetraceGrad.raise_()
        self.push_hideRetraceGrad.clicked.connect(self.hideRetraceHistogram)
        self.push_showRetraceGrad.clicked.connect(self.showRetraceHistogram)

        #Updates the position of the vertical/horizontal line cuts when the value in the corresponding line-edit in changed
        self.vCutTracePos.editingFinished.connect(self.changeVLine)
        self.hCutTracePos.editingFinished.connect(self.changeHLine)
        self.vCutRetracePos.editingFinished.connect(self.changeVLine)
        self.hCutRetracePos.editingFinished.connect(self.changeHLine)

        #Updates the estimate of the SQUID diameter when the measurement lines are moved
        self.MeasureLine1.sigPositionChangeFinished.connect(self.UpdateFieldPeriod)
        self.MeasureLine2.sigPositionChangeFinished.connect(self.UpdateFieldPeriod)
        self.pushButton_Show.clicked.connect(self.ToggleMeasurementLine)
        self.Flag_MeasurementLineShowing = True

        #Toggles between showing 1D plots along vertical/horizontal lines
        self.comboBox_traceLinecut.currentIndexChanged.connect(self.toggle_bottomTracePlot)
        self.comboBox_retraceLinecut.currentIndexChanged.connect(self.toggle_bottomRetracePlot)

        #Updates the bias and blink modes
        self.comboBox_biasSweepMode.currentIndexChanged.connect(self.updateBiasSweepMode)
        self.comboBox_blinkMode.currentIndexChanged.connect(self.updateBlinkMode)

        #Checks that the min/max field/bias values are in a sensible range and in the correct format
        self.lineEdit_fieldMax.editingFinished.connect(self.updateFieldMax)
        self.lineEdit_fieldMin.editingFinished.connect(self.updateFieldMin)
        self.lineEdit_fieldPoints.editingFinished.connect(self.updateFieldPoints)
        self.lineEdit_fieldSpeed.editingFinished.connect(self.updateFieldSpeed)

        self.lineEdit_biasMax.editingFinished.connect(self.updateBiasMax)
        self.lineEdit_biasMin.editingFinished.connect(self.updateBiasMin)
        self.lineEdit_biasPoints.editingFinished.connect(self.updateBiasPoints)
        self.lineEdit_biasDelay.editingFinished.connect(self.updateBiasDelay)

        #Toggles between plotting the Feedback voltage and Noise signal in either the trace or retrace plots
        self.tab_trace.currentChanged.connect(self.toggleTracePlots)
        self.tab_retrace.currentChanged.connect(self.toggleRetracePlots)

        self.push_Servers.clicked.connect(self.showServersList)

        #Initialize the servers to False
        self.gen_dv = False
        self.dv = False
        self.dac = False
        self.dac_toe = False
        self.ips = False
        self.blink_server = False

        #By default lock the interface
        self.lockInterface()

    def setupAdditionalUi(self):
        #Set up the plot for the DC output trace data
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

        #Set up interactive verical and horizontal lines for the trace DC output plot linecuts
        self.vTraceLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hTraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vTraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hTraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        self.view0.addItem(self.vTraceLine, ignoreBounds = True)
        self.view0.addItem(self.hTraceLine, ignoreBounds =True)

        #Add interactive vertical lines to be aligned with features of the
        #SQUID interference pattern to estimate the SQUID diameter
        self.MeasureLine1 = pg.InfiniteLine(pos = 0.1, angle = 90, movable = True, pen = 'b', hoverPen = (50, 50, 200))
        self.MeasureLine2 = pg.InfiniteLine(pos = 0.2, angle = 90, movable = True, pen = 'b', hoverPen = (50, 50, 200))
        self.view0.addItem(self.MeasureLine1, ignoreBounds = True)
        self.view0.addItem(self.MeasureLine2, ignoreBounds = True)

        #Set up the plot for the noise of the trace data
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

        #Set up interactive verical and horizontal lines for the trace noise plot linecuts
        self.vTraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hTraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vTraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hTraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        self.view1.addItem(self.vTraceNoiseLine, ignoreBounds = True)
        self.view1.addItem(self.hTraceNoiseLine, ignoreBounds =True)

        #Set up the plot for the DC output retrace data
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

        #Set up interactive verical and horizontal lines for the retrace DC output plot linecuts
        self.vRetraceLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hRetraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vRetraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hRetraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        self.view2.addItem(self.vRetraceLine, ignoreBounds = True)
        self.view2.addItem(self.hRetraceLine, ignoreBounds =True)

        #Set up the plot for the noise of the retrace data
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

        #Set up interactive verical and horizontal lines for the retrace noise plot linecuts
        self.vRetraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hRetraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        self.view3.addItem(self.vRetraceNoiseLine, ignoreBounds = True)
        self.view3.addItem(self.hRetraceNoiseLine, ignoreBounds = True)

        #Initialize all the plots for the linecuts
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

    def moveDefault(self):
        self.move(550,10)

    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            #Keep a copy of the dataVault server initialized by the LabRADConnect module
            #to synchronize data save folders
            self.gen_dv = dict['servers']['local']['dv']

            '''
            Create another connection to labrad in order to have a set of servers opened up in a context
            specific to this module. This allows multiple datavault connections to be editted at the same
            time, or communication with multiple DACs / other devices
            '''
            from labrad.wrappers import connectAsync
            cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield cxn.data_vault
            #Set the directory of the local datavault connection to be the same as the one
            #selected in the LabRAD Connect module
            curr_folder = yield self.gen_dv.cd()
            yield self.dv.cd(curr_folder)

            #Connected to the appropriate DACADC
            self.dac = yield cxn.dac_adc
            yield self.dac.select_device(dict['devices']['nsot']['dac_adc'])

            #Select the appropriate magnet power supply
            if dict['devices']['system']['magnet supply'] == 'Toellner Power Supply':
                self.dac_toe = dict['servers']['local']['dac_adc']
                self.settingsDict['Magnet device'] = 'Toellner 8851'
                self.settingsDict['toellner volts'] = dict['channels']['system']['toellner dac voltage']
                self.settingsDict['toellner current'] = dict['channels']['system']['toellner dac current']
                self.comboBox_magnetPower.addItem('Toellner 8851')
            elif dict['devices']['system']['magnet supply'] == 'IPS 120 Power Supply':
                self.ips = dict['servers']['remote']['ips120']
                self.settingsDict['Magnet device'] = 'IPS 120-10'
                self.comboBox_magnetPower.addItem('IPS 120-10')
            else:
                raise Exception #Raise error if no magnet power supply is connected

            #select the appropriate blink device
            if dict['devices']['system']['blink device'].startswith('ad5764_dcbox'):
                self.blink_server = yield cxn.ad5764_dcbox
                yield self.blink_server.select_device(dict['devices']['system']['blink device'])
                print('DC BOX Blink Device')
            elif dict['devices']['system']['blink device'].startswith('DA'):
                self.blink_server = yield cxn.dac_adc
                yield self.blink_server.select_device(dict['devices']['system']['blink device'])
                print('DAC ADC Blink Device')
            else:
                raise Exception #Raise error if no blink device is selected

            #Set all the channels as specified by the DeviceSelect module
            self.blinkDevice = dict['devices']['system']['blink device']
            self.settingsDict['blink'] = dict['channels']['system']['blink channel']
            self.settingsDict['nsot bias output'] = dict['channels']['nsot']['nSOT Bias']
            self.settingsDict['nsot bias input'] = dict['channels']['nsot']['Bias Reference']
            self.settingsDict['feedback DC input'] = dict['channels']['nsot']['DC Readout']
            self.settingsDict['noise input'] = dict['channels']['nsot']['Noise Readout']

            #Set the server pushbutton to green to show servers were connected
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")

            #Unlock the interface
            self.unlockInterface()
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")

    def disconnectLabRAD(self):
        try:
            self.comboBox_magnetPower.removeItem(0)
        except:
            pass
        self.gen_dv = False
        self.dv = False
        self.dac = False
        self.dac_toe = False
        self.ips = False
        self.blink_server = False
        self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to updating parameters from
         line edits. The first is thoroughly commented as an example, but since the
         structure of these functions are all very similar they aren't all commented
         with the same thoroughness."""

    def updateFieldMin(self, val = None):
        #If no value is specified get the value from the lineEdit
        if val is None:
            val = readNum(str(self.lineEdit_fieldMin.text()))
        #If the val retrieved from the lineedit is a float
        if isinstance(val,float):
            #Update the parameters dictionary with the new value
            self.sweepParamDict['B_min'] = self.checkFieldRange(val)
        #Set the text in the lineEdit to the value in the dictionary. If an
        #improperly formatted number was read that didn't result in the
        #dictionary being updated, this will set the text to the previous
        #number.
        self.lineEdit_fieldMin.setText(formatNum(self.sweepParamDict['B_min']))

    def updateFieldMax(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_fieldMax.text()))
        if isinstance(val,float):
            self.sweepParamDict['B_max'] = self.checkFieldRange(val)
        self.lineEdit_fieldMax.setText(formatNum(self.sweepParamDict['B_max']))

    def checkFieldRange(self, val):
        #Keeps the field value within 1.25T for the dipper magnet
        if self.settingsDict['Magnet device'] == 'Toellner 8851':
            if val < -1.25:
                val = -1.25
            elif val > 1.25:
                val = 1.25
        #Keeps the field value within 5T for the 1K system magnet
        elif self.settingsDict['Magnet device'] == 'IPS 120-10':
            if val < -5:
                val = -5
            elif val > 5:
                val = 5
        return val

    def updateFieldSpeed(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_fieldSpeed.text()))
        if isinstance(val,float):
            self.sweepParamDict['B_rate'] = val
        self.lineEdit_fieldSpeed.setText(formatNum(self.sweepParamDict['B_rate']))

    def updateFieldPoints(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_fieldPoints.text()))
        if isinstance(val,float) and val > 2:
            #Updates both the number of field points and the field step size.
            #If the GUI is toggled such that it enters the step size instead of
            #the number of points (which happens when fieldSIStat is not 'num pnts')
            #Then the value is taken to be the step size instad of the number of
            #points
            if self.fieldSIStat == 'num pnts':
                self.sweepParamDict['B_pnts'] = int(val)
                self.sweepParamDict['B_step'] = (self.sweepParamDict['B_max']-self.sweepParamDict['B_min'])/(val-1)
            else:
                self.sweepParamDict['B_pnts'] = round(1+(self.sweepParamDict['B_max']-self.sweepParamDict['B_min'])/val)
                self.sweepParamDict['B_step'] = (self.sweepParamDict['B_max']-self.sweepParamDict['B_min'])/(self.sweepParamDict['B_pnts']-1)

        if self.fieldSIStat == 'num pnts':
            self.lineEdit_fieldPoints.setText(formatNum(self.sweepParamDict['B_pnts']))
        else:
            self.lineEdit_fieldPoints.setText(formatNum(self.sweepParamDict['B_step']))

    def updateBiasMin(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_biasMin.text()))
        if isinstance(val,float):
            self.sweepParamDict['V_min'] = self.checkBiasRange(val)
            self.checkSweepVoltageParameters()
        self.lineEdit_biasMin.setText(formatNum(self.sweepParamDict['V_min']))

    def updateBiasMax(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_biasMax.text()))
        if isinstance(val,float):
            self.sweepParamDict['V_max'] = self.checkBiasRange(val)
            self.checkSweepVoltageParameters()
        self.lineEdit_biasMax.setText(formatNum(self.sweepParamDict['V_max']))

    def checkBiasRange(self, val):
        #Keeps the voltage value within 10V
        if val < -10:
            val = -10
        elif val > 10:
            val = 10
        return val

    def checkSweepVoltageParameters(self):
        #Makes sure the min and max voltages are compatible with the selected
        #sweep mode. If the mode is 0 (min to max), then any voltage work.
        #if sweep mode is 1 (zero to min/max), then the minimum voltage needs
        #to be negative and the maximum positive.
        if self.sweepParamDict['sweep mode'] == 1:
            v_min = self.sweepParamDict['V_min']
            v_max = self.sweepParamDict['V_max']
            if v_min < 0 and v_max > 0:
                pass
            else:
                vDefault = max(abs(float(v_min)), abs(float(v_max)))
                v_max = vDefault
                v_min = -vDefault
            self.sweepParamDict['V_max'] = v_max
            self.sweepParamDict['V_min'] = v_min

    def updateBiasPoints(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_biasPoints.text()))
        if isinstance(val,float) and val > 2:
            #Updates both the number of bias points and the bias step size.
            #If the GUI is toggled such that it enters the step size instead of
            #the number of points (which happens when biasSIStat is not 'num pnts')
            #Then the value is taken to be the step size instad of the number of
            #points
            if self.biasSIStat == 'num pnts':
                self.sweepParamDict['V_pnts'] = int(val)
                self.sweepParamDict['V_step'] = (self.sweepParamDict['V_max']-self.sweepParamDict['V_min'])/(val-1)
            else:
                self.sweepParamDict['V_pnts'] = round(1+(self.sweepParamDict['V_max']-self.sweepParamDict['V_min'])/val)
                self.sweepParamDict['V_step'] =  (self.sweepParamDict['V_max']-self.sweepParamDict['V_min'])/(self.sweepParamDict['V_pnts']-1)

        if self.biasSIStat == 'num pnts':
            self.lineEdit_biasPoints.setText(formatNum(self.sweepParamDict['V_pnts']))
        else:
            self.lineEdit_biasPoints.setText(formatNum(self.sweepParamDict['V_step']))

    def updateBiasDelay(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_biasDelay.text()))
        if isinstance(val,float) and val > 0:
            self.sweepParamDict['delay'] = val
        self.lineEdit_biasDelay.setText(formatNum(self.sweepParamDict['delay']))

    def toggleFieldSteps(self):
        #Toggles between number of steps and Tesla/step in the sweep parameter line edits
        if self.fieldSIStat == 'num pnts':
            self.FieldInc.setText("Tesla per Step")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
            self.lineEdit_fieldPoints.setText(formatNum(self.sweepParamDict['B_step']))
            self.fieldSIStat = 'field step'
        else:
            self.FieldInc.setText("Number of Steps")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
            self.lineEdit_fieldPoints.setText(formatNum(self.sweepParamDict['B_pnts']))
            self.fieldSIStat = 'num pnts'

    def toggleBiasSteps(self):
        #Toggles between number of steps and Volts/step in the sweep parameter line edits
        if self.biasSIStat == 'num pnts':
            self.BiasInc.setText("Volts per Step")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
            self.lineEdit_biasPoints.setText(formatNum(self.sweepParamDict['V_step']))
            self.biasSIStat = 'bias step'
        else:
            self.BiasInc.setText("Number of Steps")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
            self.lineEdit_biasPoints.setText(formatNum(self.sweepParamDict['V_pnts']))
            self.biasSIStat = 'num pnts'

    def updateBiasSweepMode(self):
        self.sweepParamDict['sweep mode'] = self.comboBox_biasSweepMode.currentIndex()
        self.checkSweepVoltageParameters()
        self.lineEdit_biasMin.setText(formatNum(self.sweepParamDict['V_min']))
        self.lineEdit_biasMax.setText(formatNum(self.sweepParamDict['V_max']))

    def updateBlinkMode(self):
        self.sweepParamDict['blink mode'] = self.comboBox_blinkMode.currentIndex()

    def updateSweepTime(self):
        #Define local variables just to make equation not ridiculously long
        bpoints = self.sweepParamDict['B_pnts']
        bspeed = self.sweepParamDict['B_rate']
        bmin = self.sweepParamDict['B_min']
        bmax = self.sweepParamDict['B_max']
        vpoints = self.sweepParamDict['V_pnts']
        delay = self.sweepParamDict['delay']

        #Estimate time of sweep in minutes

        #Fudge factor included by the original writer who didn't comment their code.
        #Presumably a blanket 5 seconds added per voltage sweep for latency slow
        tLatent = 5
        #Time contributions from
        #1. Sweeping field from zero to start field, then end field to zero
        #2. Time from sweeping the field between bmin and bmax.
        #3. Time from doing the voltage sweeps
        T = (np.absolute(bmin) + np.absolute(bmax)) / (bspeed) + (np.absolute(bmax - bmin) / (bspeed)) + (bpoints/60) * ((vpoints - 1) * (delay) + float(tLatent))
        #Multiply by 2 to include trace and retrace time
        T = 2*T
        #Get number of hours and minutes
        hours = int(T / 60)
        minutes = int(T)%60
        TotalTime = str(hours) + ' hours ' + str(minutes) + ' minutes'

        self.sweepParamDict['sweep time'] = TotalTime

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to SQUID diameter analysis"""

    def UpdateFieldPeriod(self):
        #Get the position of the analysis markers in tesla
        pos1 = self.MeasureLine1.value()
        pos2 = self.MeasureLine2.value()
        #The period is the difference between the two
        period = abs(pos1 - pos2)
        #Set the text of the lineEdIt to be the field in mT
        self.lineEdit_FieldPeriod.setText(str(round(period * 1000, 1)))
        fluxquanta = 2.0678338 / (10.0 ** 15)
        area = fluxquanta / period
        diameter = 2 * math.sqrt(area / math.pi)
        #Set the text of the lineEDit to be the diameter in nm
        self.lineEdit_Diameter.setText(str(round(diameter * 10.0 ** 9, 1)))

    def ToggleMeasurementLine(self):
        #Toggle adding / removing the measurement lines for analysis
        if self.Flag_MeasurementLineShowing:
            self.view0.removeItem(self.MeasureLine1)
            self.view0.removeItem(self.MeasureLine2)
        else:
            self.view0.addItem(self.MeasureLine1)
            self.view0.addItem(self.MeasureLine2)
        self.Flag_MeasurementLineShowing = not self.Flag_MeasurementLineShowing

#----------------------------------------------------------------------------------------------#
    """ The following functions hide or show the histogram on the colorplots"""

    def hideTraceHistogram(self):
        #Hide the histogram for the trace image view
        self.tracePlot.ui.histogram.hide()
        self.noiseTracePlot.ui.histogram.hide()
        self.push_hideTraceGrad.hide()
        self.push_showTraceGrad.show()
        self.push_showTraceGrad.raise_()

    def showTraceHistogram(self):
        #Show the histogram for the trace image view
        self.tracePlot.ui.histogram.show()
        self.noiseTracePlot.ui.histogram.show()
        self.push_hideTraceGrad.show()
        self.push_showTraceGrad.hide()
        self.push_showTraceGrad.raise_()

    def hideRetraceHistogram(self):
        #Hide the histogram for the retrace image view
        self.retracePlot.ui.histogram.hide()
        self.noiseRetracePlot.ui.histogram.hide()
        self.push_hideRetraceGrad.hide()
        self.push_showRetraceGrad.show()
        self.push_showRetraceGrad.raise_()

    def showRetraceHistogram(self):
        #Show the histogram for the retrace image view
        self.retracePlot.ui.histogram.show()
        self.noiseRetracePlot.ui.histogram.show()
        self.push_hideRetraceGrad.show()
        self.push_showRetraceGrad.hide()
        self.push_showRetraceGrad.raise_()

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to sweeping buttons"""

    def runPrelimSweep(self):
        #Opens the preliminary sweep window
        self.push_prelim.setEnabled(False)
        self.prelimSweep = preliminarySweep(self.reactor, self.dv, self.dac, self.settingsDict, self)
        self.prelimSweep.show()

    def abortSweep(self):
        #Aborts sweep by changing the self.abortFlag to True
        self.abortFlag = True

    @inlineCallbacks
    def startSweep(self):
        #Prevent user from starting multiple sweeps at the same time by disabling the button while sweeping
        self.push_startSweep.setEnabled(False)
        #By default, do not abort the sweep.
        self.abortFlag = False

        #Update the estimated sweep time
        yield self.updateSweepTime()

        #Throw a reminder to check that the output of the Toellner is on if it's being used
        if self.settingsDict['Magnet device'] == 'Toellner 8851':
            checkToe = toellnerReminder()
            if not checkToe.exec_():
                #If not, abort the sweep
                self.abortFlag = True

        #Have user review the sweep parameters before starting
        if not self.abortFlag:
            checkSweepParams = DialogBox(self.settingsDict['Magnet device'], self.sweepParamDict, self)
            #If the user does not like the sweep parameters, abort the sweep
            if not checkSweepParams.exec_():
                self.abortFlag = True

        if not self.abortFlag:
            #Have the sweep happen in a separate function so that when scripting
            #the GUI checks are not run
            yield self.initSweep()

        #once the sweep is done, re-enable the startSweep button
        self.push_startSweep.setEnabled(True)

    def lockSweepParameters(self):
        self.push_startSweep.setEnabled(False)
        self.comboBox_magnetPower.setEnabled(False)
        self.comboBox_blinkMode.setEnabled(False)
        self.comboBox_biasSweepMode.setEnabled(False)
        self.push_prelim.setEnabled(False)
        self.lineEdit_fieldMin.setReadOnly(True)
        self.lineEdit_fieldMax.setReadOnly(True)
        self.lineEdit_fieldPoints.setReadOnly(True)
        self.lineEdit_fieldSpeed.setReadOnly(True)
        self.lineEdit_biasMin.setReadOnly(True)
        self.lineEdit_biasMax.setReadOnly(True)
        self.lineEdit_biasPoints.setReadOnly(True)
        self.lineEdit_biasDelay.setReadOnly(True)

    def unlockSweepParameters(self):
        self.push_startSweep.setEnabled(True)
        self.comboBox_magnetPower.setEnabled(True)
        self.comboBox_blinkMode.setEnabled(True)
        self.comboBox_biasSweepMode.setEnabled(True)
        self.push_prelim.setEnabled(True)
        self.lineEdit_fieldMin.setReadOnly(False)
        self.lineEdit_fieldMax.setReadOnly(False)
        self.lineEdit_fieldPoints.setReadOnly(False)
        self.lineEdit_fieldSpeed.setReadOnly(False)
        self.lineEdit_biasMin.setReadOnly(False)
        self.lineEdit_biasMax.setReadOnly(False)
        self.lineEdit_biasPoints.setReadOnly(False)
        self.lineEdit_biasDelay.setReadOnly(False)

    @inlineCallbacks
    def initSweep(self):
        try:
            #Lock GUI elements that should not be changed mid scan
            self.lockSweepParameters()

            #First create shorter local variables of all the important sweep parameters
            b_min, b_max, b_rate = self.sweepParamDict['B_min'], self.sweepParamDict['B_max'], self.sweepParamDict['B_rate']
            v_min, v_max = self.sweepParamDict['V_min'], self.sweepParamDict['V_max']
            b_pnts, v_pnts = self.sweepParamDict['B_pnts'], self.sweepParamDict['V_pnts']
            delay = int(1e6 * self.sweepParamDict['delay']) #Get the delay in units of microseconds

            #Create a data vault file for this sweep
            file_info = yield self.dv.new("nSOT vs. Bias Voltage and Field", ['Trace Index', 'B Field Index','Bias Voltage Index','B Field','Bias Voltage'],['DC SSAA Output','Noise'])
            self.dvFileName = file_info[1] #Get the name of the file
            self.lineEdit_ImageNum.setText(file_info[1][0:5]) #Update the GUI element showing the dataset number
            session = ''
            for folder in file_info[0][1:]:
                session = session + '\\' + folder
            self.lineEdit_ImageDir.setText(r'\.datavault' + session) #Update the GUI element showing the dataset directory
            print('DataVault setup complete')

            print(self.sweepParamDict)

            #For the data of the speed, determine the position of the plot and the scale factors
            self.plt_pos = [b_min, v_min] #Position of the bottom left corner of the plot
            self.plt_scale = [(b_max-b_min) / b_pnts, (v_max-v_min) / v_pnts] #Scale factor for the size of each pixel

            #Initialize empty arrays for the data for plotting
            self.curTraceData = np.zeros([b_pnts, v_pnts])
            self.noiseTraceData = np.zeros([b_pnts, v_pnts])
            self.curRetraceData = np.zeros([b_pnts, v_pnts])
            self.noiseRetraceData = np.zeros([b_pnts, v_pnts])

            #Update the plots with the empty datasets
            self.updatePlots()

            #Generate arrays with values of magnetic fields that need to be sampled
            b_vals = np.linspace(float(b_min),float(b_max), num = int(b_pnts))

            #Start by making sure the voltage output on the nSOT is zero.
            #This should be improved at some point to coordinate with the setpoint
            #module to not jump the bias voltage on the SQUID.
            #That being said, it isn't a problem that damages SQUIDs usually
            yield self.dac.set_voltage(self.settingsDict['nsot bias output'] - 1, 0)

            #If starting (minimum) bias voltage is not zero, sweep bias to minimum value, 1mV per step with a 1ms delay
            if v_min != 0:
                a = yield self.dac.buffer_ramp([self.settingsDict['nsot bias output'] - 1], [0], [0], [v_min], np.absolute(int(v_min * 1000)), 1000)

            #Loop through the magnetic field points
            for i in range(0, b_pnts):
                #Check if user selected to abort the sweep
                if self.abortFlag:
                    yield self.abortSweepFunc(0, v_min)
                    break

                #Ramp the magnetic field from the current field to
                print('Ramping field to ' + str(b_vals[i])+'.')
                if i == 0:
                    #For the first field point, assume we were at zero field to begin with
                    yield self.setMagneticField(0, b_vals[0], b_rate)
                else:
                    yield self.setMagneticField(b_vals[i-1], b_vals[i], b_rate)

                #Check if user selected to abort the sweep while the field was changing
                if self.abortFlag:
                    yield self.abortSweepFunc(b_vals[i], v_min)
                    break

                print('Starting sweep with magnetic field set to: ' + str(b_vals[i]))

                #Do the voltage sweep. The function takes into account the sweep mode
                trace, retrace = yield self.rampVoltage(v_min, v_max, v_pnts, delay, self.sweepParamDict['sweep mode'])

                #Reform data and add to data vault
                formated_trace = []
                for j in range(0, v_pnts):
                    formated_trace.append((0, i, j, b_vals[i], trace[0][j], trace[1][j], trace[2][j]))

                formated_retrace = []
                for j in range(0, v_pnts):
                    formated_retrace.append((1, i, v_pnts - 1 - j, b_vals[i], retrace[0][j], retrace[1][j], retrace[2][j]))

                yield self.dv.add(formated_trace)
                yield self.dv.add(formated_retrace)

                #update the plots
                yield self.updatePlots(formated_trace)
                yield self.updatePlots(formated_retrace)

                #Check if user selected to abort the sweep while voltages were sweeping
                if self.abortFlag:
                    yield self.abortSweepFunc(b_vals[i], v_min)
                    break

            #If minimum bias voltage is not zero, sweep bias back to zero, 1mV per step with a reasonably short delay
            if v_min != 0 and not self.abortFlag:
                yield self.dac.buffer_ramp([self.settingsDict['nsot bias output'] - 1], [0], [v_min], [0], np.absolute(int(v_min * 1000)), 1000)

            #Zero the magnetic field if the checkBox is checked
            if self.checkBox_ZeroField.isChecked() and not self.abortFlag:
                #Go to zero field and set power supply voltage setpoint to zero.
                yield self.setMagneticField(b_vals[-1], 0, b_rate)

            print('Sweep complete')
            #unlock the GUI elements now that the sweep is complete
            self.unlockSweepParameters()
            #Wait until all plots are appropriately updated before saving screenshot
            yield self.sleep(0.25)
            saveDataToSessionFolder(self, self.sessionFolder, self.dvFileName)
        except:
            printErrorInfo()

    @inlineCallbacks
    def setMagneticField(self, B_i, B_f, B_rate):
        #Set the magnetic field with either the Toellner or the IPS
        if self.settingsDict['Magnet device'] == 'Toellner 8851':
            yield self.toeSetField(B_i, B_f, B_rate)
        elif self.settingsDict['Magnet device'] == 'IPS 120-10':
            yield self.ipsSetField(B_f, B_rate)

    @inlineCallbacks
    def toeSetField(self, B_i, B_f, B_rate):
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
            sweep_steps = int((t_conv * B_range) / (B_rate * magnet_delay))  + 1
            v_start = B_i / (IB_conv * IV_conv)
            v_end = B_f / (IB_conv * IV_conv)

            #Sets an appropraite voltage set point to ensure that the Toellner power supply stays in constant current mode
            # assuming a parasitic resistance of R_p between the power supply and magnet
            R_p = 1
            V_setpoint =  (R_p * B_f) / (VV_conv * IB_conv)
            V_initial = (R_p * B_i) / (VV_conv * IB_conv)
            if V_setpoint*VV_conv > 5.0:
                V_setpoint = 5.0/VV_conv
            else:
                pass
            if V_initial*VV_conv > 5.0:
                V_initial = 5.0/VV_conv
            else:
                pass

            #Sweeps field from B_i to B_f
            print('Sweeping field from ' + str(B_i) + ' to ' + str(B_f)+'.')
            yield self.dac_toe.buffer_ramp([self.settingsDict['toellner current']-1, self.settingsDict['toellner current']-1],[0],[v_start, V_initial],[v_end, V_setpoint], sweep_steps, magnet_delay)

            self.newToeField.emit(B_f, B_f/IB_conv, V_setpoint)
        except:
            printErrorInfo()

    @inlineCallbacks
    def ipsSetField(self, B_f, B_rate):
        yield self.ips.set_control(3) #Set the IPS120 to remote communication
        yield self.ips.set_comm_protocol(6) #Set the IPS120 to the proper communication protocol
        yield self.ips.set_fieldsweep_rate(B_rate) #Set the sweep rate
        yield self.ips.set_targetfield(B_f) #Set the target field
        yield self.ips.set_activity(1) #Set the IPS to sweep field if it is not yet at the target field
        yield self.ips.set_control(2) #Set the IPS120 to local communication so that it can be used IRL

        print('Setting field to ' + str(B_f))

        #Keep track of time since the field started changing
        t0 = time.time()

        #wait for field to be reached
        while True:
            #Read the current field
            yield self.ips.set_control(3)
            curr_field = yield self.ips.read_parameter(7)
            yield self.ips.set_control(2)

            #Break out of loop if the field is at the desired field
            if float(curr_field[1:]) <= B_f+0.00001 and float(curr_field[1:]) >= B_f-0.00001:
                break

            #Break out of loop if the user aborts the sweep
            if self.abortFlag == True:
                break

            #If it's taking a long time to get to the next point, sometimes reseting them
            #setpoint and activity helps
            if time.time() - t0 > 1:
                yield self.ips.set_control(3)
                yield self.ips.set_targetfield(B_f)
                yield self.ips.set_activity(1)
                yield self.ips.set_control(2)
                t0 = time.time()
                print('restarting loop')

            yield self.sleep(0.25)

        #Once the field is reached, set the IPS to no longer change field
        yield self.ips.set_control(3)
        yield self.ips.set_activity(0)
        yield self.ips.set_control(2)

    @inlineCallbacks
    def rampVoltage(self, v_min, v_max, pnts, delay, mode):
        #DAC OUTPUTS
        DAC_out = self.settingsDict['nsot bias output'] - 1 #DAC out channel that outputs DC bias (1 through 4)

        #DAC INPUTS
        DAC_in_ref = self.settingsDict['nsot bias input'] - 1 #DAC in channel that reads DC bias (1 through 4)
        V_out = self.settingsDict['feedback DC input'] - 1 #DAC in channel that read DC signal (1 through 4)
        noise = self.settingsDict['noise input'] - 1 #DAC in channel to read noise measurement

        #Here differentiate between sweep modes
        if mode == 0: #This corresponds to min to max sweeps
            #If blink mode is enabled, blink before the voltage sweep step
            if self.sweepParamDict['blink mode'] == 0:
                print('Blinking prior to sweep')
                yield self.blink()

            #Sweep from minimum to maximum bias voltage
            print('Ramping up nSOT bias voltage from ' + str(v_min) + ' to ' + str(v_max) + '.')
            trace = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise], [v_min], [v_max], pnts, delay)

            #Sweep from maximum to minimum bias voltage
            print('Ramping nSOT bias voltage back down from ' + str(v_max) + ' to ' + str(v_min) + '.')
            retrace = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise], [v_max], [v_min], pnts, delay)

            #Flip the retrace data so that the ith point corresponds to the same voltage as the ith point of the trace data
            retrace = [data[::-1] for data in retrace]

        elif mode == 1: #This corresponds to zero to mix max
            #If sweeping from zero to min/max, find the appropriate number of points
            #for positive and negative voltages
            v_range = v_max - v_min
            positive_points = int((pnts * v_max)/v_range) #Think about the +1 in rest of script
            negative_points = pnts - positive_points

            #If blink mode is enabled, blink before the voltage sweep step
            if self.sweepParamDict['blink mode'] == 0:
                print('Blinking prior to sweep')
                yield self.blink()

            #Sweep from zero volts to maximum bias voltage
            print('Ramping up nSOT bias voltage from zero to ' + str(v_max) + '.')
            up_trace = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise], [0], [v_max], positive_points, delay)

            #Sweep from maximum bias voltage to zero volts and blink
            print('Ramping nSOT bias voltage back down from ' + str(v_max) + ' to zero.')
            up_retrace = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise], [v_max], [0], positive_points, delay)

            #If blink mode is enabled, blink before the voltage sweep step
            if self.sweepParamDict['blink mode'] == 0:
                print('Blinking prior to sweep')
                yield self.blink()

            #Sweep from zero volts to minimum bias voltage
            print('Ramping down nSOT bias voltage from zero to ' + str(v_min) + '.')
            down_trace = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise], [0], [v_min], negative_points, delay)

            #Sweep from minimum bias voltage to zero volts
            print('Ramping nSOT bias voltage up down from ' + str(v_min) + ' to zero.')
            down_retrace = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise], [v_min], [0], negative_points, delay)

            trace = down_trace[::-1] + up_trace
            retrace = down_retrace + up_retrace[::-1]

        returnValue([trace, retrace])

    @inlineCallbacks
    def abortSweepFunc(self, bVal, vVal):
        print('Aborting sweep from applied field of ', bVal,'T and nSOT bias of ', vVal, 'V')
        print('Ramping nSOT bias to zero')
        #If minimum bias voltage is not zero, sweep bias back to zero, 1mV per step with a reasonably short delay
        if vVal != 0:
            yield self.dac.buffer_ramp([self.settingsDict['nsot bias output'] - 1], [0], [vVal], [0], np.absolute(int(vVal * 1000)), 1000)

        #if the zero field checkbox is checked zero the field
        if self.checkBox_ZeroField.isChecked():
            print('Sweeping magnetic field back to zero')
            yield self.setMagneticField(bVal, 0, self.sweepParamDict['B_rate'])

        self.unlockSweepParameters()

    @inlineCallbacks
    def blink(self):
        #Blink, resetting the analog feedback control loop for the nSOT
        yield self.blink_server.set_voltage(self.settingsDict['blink']-1, 5)
        yield self.sleep(0.25)
        yield self.blink_server.set_voltage(self.settingsDict['blink']-1, 0)
        yield self.sleep(0.25)

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to plotting"""

    def updatePlots(self, new_line = None):
        if new_line is None: #If no line is provided, just update all the image views with the current data
            self.tracePlot.setImage(self.curTraceData, autoRange = True , autoLevels = True, pos = self.plt_pos, scale = self.plt_scale)
            self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = True , autoLevels = True, pos = self.plt_pos, scale = self.plt_scale)
            self.retracePlot.setImage(self.curRetraceData, autoRange = True , autoLevels = True, pos = self.plt_pos, scale = self.plt_scale)
            self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = True , autoLevels = True, pos = self.plt_pos, scale = self.plt_scale)
        elif new_line[0][0] == 1: #If first index of the new line is retrace, update retrace plots
            i = new_line[0][1]
            new_curData = [x[5] for x in new_line]
            new_noiseData = [x[6] for x in new_line]
            self.curRetraceData[i] = new_curData
            self.noiseRetraceData[i] = new_noiseData
            self.retracePlot.setImage(self.curRetraceData, autoRange = False, autoLevels = True, pos = self.plt_pos,scale = self.plt_scale)
            self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = False, autoLevels = True, pos = self.plt_pos, scale = self.plt_scale)
            if self.liveTracePlotStatus is True:
                self.plotRetraceLinecut(i)
        elif new_line[0][0] == 0: #If first index of the new line is trace, update trace plots
            i = new_line[0][1]
            new_curData = [x[5] for x in new_line]
            new_noiseData = [x[6] for x in new_line]
            self.curTraceData[i] = new_curData
            self.noiseTraceData[i] = new_noiseData
            self.tracePlot.setImage(self.curTraceData, autoRange = False, autoLevels = True, pos = self.plt_pos, scale = self.plt_scale)
            self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = False, autoLevels = True, pos = self.plt_pos, scale = self.plt_scale)
            if self.liveRetracePlotStatus is True:
                self.plotTraceLinecut(i)

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
        if self.liveTracePlotStatus is False:
            if self.tab_trace.currentIndex() == 0:
                posTrace = self.vTraceLine.value()
                self.vCutTracePos.setValue(posTrace)
                self.updateBottomTracePlot()
            elif self.tab_trace.currentIndex() == 1:
                posTrace = self.vTraceNoiseLine.value()
                self.vCutTracePos.setValue(posTrace)
                self.updateBottomTracePlot()

        if self.liveRetracePlotStatus is False:
            if self.tab_retrace.currentIndex() == 0:
                posRetrace = self.vRetraceLine.value()
                self.vCutRetracePos.setValue(posRetrace)
                self.updateBottomRetracePlot()
            elif self.tab_retrace.currentIndex() == 1:
                posRetrace = self.vRetraceNoiseLine.value()
                self.vCutRetracePos.setValue(posRetrace)
                self.updateBottomRetracePlot()

    def updateHLineBox(self):
        if self.liveTracePlotStatus is False:
            if self.tab_trace.currentIndex() == 0:
                posTrace = self.hTraceLine.value()
                self.hCutTracePos.setValue(posTrace)
                self.updateBottomTracePlot()

            elif self.tab_trace.currentIndex() == 1:
                posTrace = self.hTraceNoiseLine.value()
                self.hCutTracePos.setValue(posTrace)
                self.updateBottomTracePlot()

        if self.liveRetracePlotStatus is False:
            if self.tab_retrace.currentIndex() == 0:
                posRetrace = self.hRetraceLine.value()
                self.hCutRetracePos.setValue(posRetrace)
                self.updateBottomRetracePlot()
            elif self.tab_retrace.currentIndex() == 1:
                posRetrace = self.hRetraceNoiseLine.value()
                self.hCutRetracePos.setValue(posRetrace)
                self.updateBottomRetracePlot()

    def changeVLine(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tab_trace.currentIndex() == 0:
                posTrace = self.vCutTracePos.value()
                self.vTraceLine.setValue(posTrace)
                self.updateBottomTracePlot()

            elif self.tab_trace.currentIndex() == 1:
                posTrace = self.vCutTracePos.value()
                self.vTraceNoiseLine.setValue(posTrace)
                self.updateBottomTracePlot()
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            if self.tab_retrace.currentIndex() == 0:
                posRetrace = self.vCutRetracePos.value()
                self.vRetraceLine.setValue(posRetrace)
                self.updateBottomRetracePlot()
            elif self.tab_retrace.currentIndex() == 1:
                posRetrace = self.vCutRetracePos.value()
                self.vRetraceNoiseLine.setValue(posRetrace)
                self.updateBottomRetracePlot()

    def changeHLine(self):
        if self.liveTracePlotStatus is False:
            if self.tab_trace.currentIndex() == 0:
                posTrace = self.hCutTracePos.value()
                self.hTraceLine.setValue(posTrace)
                self.updateBottomTracePlot()
            elif self.tab_trace.currentIndex() == 1:
                posTrace = self.hCutTracePos.value()
                self.hTraceNoiseLine.setValue(posTrace)
                self.updateBottomTracePlot()

        if self.liveRetracePlotStatus is False:
            if self.tab_retrace.currentIndex() == 0:
                posRetrace = self.hCutRetracePos.value()
                self.hRetraceLine.setValue(posRetrace)
                self.updateBottomRetracePlot()
            elif self.tab_retrace.currentIndex() == 1:
                posRetrace = self.hCutRetracePos.value()
                self.hRetraceNoiseLine.setValue(posRetrace)
                self.updateBottomRetracePlot()

    def toggleTracePlots(self):
        self.comboBox_traceLinecut.currentIndexChanged.disconnect(self.toggle_bottomTracePlot)
        self.updateHLineBox()
        self.updateVLineBox()
        self.comboBox_traceLinecut.removeItem(0)
        self.comboBox_traceLinecut.removeItem(0)
        if self.tab_trace.currentIndex() == 1:
            self.comboBox_traceLinecut.addItem("RMS Noise vs Bias")
            self.comboBox_traceLinecut.addItem("RMS Noise vs Field")
            if self.traceNoiseNow == "bias":
                self.comboBox_traceLinecut.setCurrentIndex(0)
                self.curfieldTracePlot.lower()
                self.curbiasTracePlot.raise_()
                self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.traceNoiseNow == "field":
                self.comboBox_traceLinecut.setCurrentIndex(1)
                self.curbiasTracePlot.lower()
                self.curfieldTracePlot.raise_()
                self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVTracePlot.setLabel('left', 'RMS Noise', units = 'V')
            self.IBTracePlot.setLabel('left', 'RMS Noise', units = 'V')

        elif self.tab_trace.currentIndex() == 0:
            self.comboBox_traceLinecut.addItem("DC Output vs Bias")
            self.comboBox_traceLinecut.addItem("DC Output vs Field")
            if self.tracePlotNow == "bias":
                self.comboBox_traceLinecut.setCurrentIndex(0)
                self.curfieldTracePlot.lower()
                self.curbiasTracePlot.raise_()
                self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.tracePlotNow == "field":
                self.comboBox_traceLinecut.setCurrentIndex(1)
                self.curbiasTracePlot.lower()
                self.curfieldTracePlot.raise_()
                self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
            self.IBTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.comboBox_traceLinecut.currentIndexChanged.connect(self.toggle_bottomTracePlot)

    def toggleRetracePlots(self):
        self.comboBox_retraceLinecut.currentIndexChanged.disconnect(self.toggle_bottomRetracePlot)
        self.updateHLineBox()
        self.updateVLineBox()
        self.comboBox_retraceLinecut.removeItem(0)
        self.comboBox_retraceLinecut.removeItem(0)
        if self.tab_retrace.currentIndex() == 1:
            self.comboBox_retraceLinecut.addItem("RMS Noise vs Bias")
            self.comboBox_retraceLinecut.addItem("RMS Noise vs Field")
            if self.retraceNoiseNow == "bias":
                self.comboBox_retraceLinecut.setCurrentIndex(0)
                self.curfieldRetracePlot.lower()
                self.curbiasRetracePlot.raise_()
                self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.retraceNoiseNow == "field":
                self.comboBox_retraceLinecut.setCurrentIndex(1)
                self.curbiasRetracePlot.lower()
                self.curfieldRetracePlot.raise_()
                self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVRetracePlot.setLabel('left', 'RMS Noise', units = 'V')
            self.IBRetracePlot.setLabel('left', 'RMS Noise', units = 'V')
        elif self.tab_retrace.currentIndex() == 0:
            self.comboBox_retraceLinecut.addItem("DC Output vs Bias")
            self.comboBox_retraceLinecut.addItem("DC Output vs Field")
            if self.retracePlotNow == "bias":
                self.comboBox_retraceLinecut.setCurrentIndex(0)
                self.curfieldRetracePlot.lower()
                self.curbiasRetracePlot.raise_()
                self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.retracePlotNow == "field":
                self.comboBox_retraceLinecut.setCurrentIndex(1)
                self.curbiasRetracePlot.lower()
                self.curfieldRetracePlot.raise_()
                self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
            self.IBRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.comboBox_retraceLinecut.currentIndexChanged.connect(self.toggle_bottomRetracePlot)

    def toggle_bottomTracePlot(self):
        if self.tab_trace.currentIndex() == 0 and self.tracePlotNow == "field":
            self.tracePlotNow = "bias"
            self.curfieldTracePlot.lower()
            self.curbiasTracePlot.raise_()
            self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            self.updateBottomTracePlot()
        elif self.tab_trace.currentIndex() == 0 and self.tracePlotNow == "bias":
            self.tracePlotNow = "field"
            self.curbiasTracePlot.lower()
            self.curfieldTracePlot.raise_()
            self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.updateBottomTracePlot()
        elif self.tab_trace.currentIndex() == 1 and self.traceNoiseNow == "field":
            self.traceNoiseNow = "bias"
            self.curfieldTracePlot.lower()
            self.curbiasTracePlot.raise_()
            self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            self.updateBottomTracePlot()
        elif self.tab_trace.currentIndex() == 1 and self.traceNoiseNow == "bias":
            self.traceNoiseNow = "field"
            self.curbiasTracePlot.lower()
            self.curfieldTracePlot.raise_()
            self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.updateBottomTracePlot()

    def toggle_bottomRetracePlot(self):
        if self.tab_retrace.currentIndex() == 0 and self.retracePlotNow == "field":
            self.retracePlotNow = "bias"
            self.curfieldRetracePlot.lower()
            self.curbiasRetracePlot.raise_()
            self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            self.updateBottomRetracePlot()
        elif self.tab_retrace.currentIndex() == 0 and self.retracePlotNow == "bias":
            self.retracePlotNow = "field"
            self.curbiasRetracePlot.lower()
            self.curfieldRetracePlot.raise_()
            self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.updateBottomRetracePlot()
        elif self.tab_retrace.currentIndex() == 1 and self.retraceNoiseNow == "field":
            self.retraceNoiseNow = "bias"
            self.curfieldRetracePlot.lower()
            self.curbiasRetracePlot.raise_()
            self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            self.updateBottomRetracePlot()
        elif self.tab_retrace.currentIndex() == 1 and self.retraceNoiseNow == "bias":
            self.retraceNoiseNow = "field"
            self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.curbiasRetracePlot.lower()
            self.curfieldRetracePlot.raise_()
            self.updateBottomRetracePlot()

    def updateBottomTracePlot(self):
        index = self.comboBox_traceLinecut.currentIndex()
        x0, y0 = self.plt_pos
        xscale, yscale =  self.plt_scale
        if index == 1:
            pos = self.hCutTracePos.value()
            self.IBTracePlot.clear()
            if pos > self.sweepParamDict['V_max'] or pos < self.sweepParamDict['V_min']:
                pass
            else:
                p = int(abs(pos - self.sweepParamDict['V_min']) / yscale)
                xVals = np.linspace(self.sweepParamDict['B_min'], self.sweepParamDict['B_max'], num = self.sweepParamDict['B_pnts'])
                if self.tab_trace.currentIndex() == 0:
                    yVals = self.curTraceData[:,p]
                elif self.tab_trace.currentIndex() == 1:
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
                if self.tab_trace.currentIndex() == 0:
                    yVals = self.curTraceData[p]
                elif self.tab_trace.currentIndex() == 1:
                    yVals = self.noiseTraceData[p]
                self.IVTracePlot.plot(x = xVals, y = yVals, pen = 0.5)

    def updateBottomRetracePlot(self):
        index = self.comboBox_retraceLinecut.currentIndex()
        x0, y0 = self.plt_pos
        xscale, yscale =  self.plt_scale
        if index == 1:
            pos = self.hCutRetracePos.value()
            self.IBRetracePlot.clear()
            if pos > self.sweepParamDict['V_max'] or pos < self.sweepParamDict['V_min']:
                pass
            else:
                p = int(abs(pos - self.sweepParamDict['V_min']) / yscale)
                xVals = np.linspace(self.sweepParamDict['B_min'], self.sweepParamDict['B_max'], num = self.sweepParamDict['B_pnts'])
                if self.tab_retrace.currentIndex() == 0:
                    yVals = self.curRetraceData[:,p]
                elif self.tab_retrace.currentIndex() == 1:
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
                if self.tab_retrace.currentIndex() == 0:
                    yVals = self.curRetraceData[p]
                elif self.tab_retrace.currentIndex() == 1:
                    yVals = self.noiseRetraceData[p]
                self.IVRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)

    def plotTraceLinecut(self, i):
        index = self.comboBox_traceLinecut.currentIndex()
        if index == 0:
            self.IVTracePlot.clear()
            xVals = np.linspace(self.sweepParamDict['V_min'], self.sweepParamDict['V_max'], num = self.sweepParamDict['V_pnts'])
            yVals = self.curTraceData[i]
            self.IVTracePlot.plot(x = xVals, y = yVals, pen = 0.5)

    def plotRetraceLinecut(self, i):
        index = self.comboBox_retraceLinecut.currentIndex()
        if index == 0:
            self.IVRetracePlot.clear()
            xVals = np.linspace(self.sweepParamDict['V_min'], self.sweepParamDict['V_max'], num = self.sweepParamDict['V_pnts'])
            yVals = self.curRetraceData[i]
            self.IVRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)

#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""

    def setMinVoltage(self, vmin):
        self.updateBiasMin(vmin)

    def setMaxVoltage(self, vmax):
        self.updateBiasMax(vmax)

    def setVoltagePoints(self, pnts):
        if not self.biasSIStat == 'num pnts':
            self.toggleBiasSteps()
        self.updateBiasPoints(pnts)

    def setBiasDelay(self, delay):
        self.updateBiasDelay(delay)

    def setMinField(self, bmin):
        self.updateFieldMin(bmin)

    def setMaxField(self, bmax):
        self.updateFieldMax(bmax)

    def setFieldPoints(self, pnts):
        if not self.fieldSIStat == 'num pnts':
            self.toggleFieldSteps()
        self.updateFieldPoints(pnts)

    def setSweepMode(self, mode):
        self.comboBox_biasSweepMode.setCurrentIndex(mode)

    @inlineCallbacks
    def readFeedbackVoltage(self):
        fdbk_input = self.settingsDict['feedback DC input'] - 1
        val = yield self.dac.read_voltage(fdbk_input)
        returnValue(val)

    @inlineCallbacks
    def runSweep(self):
        yield self.initSweep() #Starts the sweep.

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def setSessionFolder(self, folder):
        self.sessionFolder = folder

    def updateDataVaultDirectory(self):
        curr_folder = yield self.gen_dv.cd()
        yield self.dv.cd(curr_folder)

    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()

    def lockInterface(self):
        self.comboBox_biasSweepMode.setEnabled(False)
        self.comboBox_blinkMode.setEnabled(False)
        self.comboBox_magnetPower.setEnabled(False)
        self.lineEdit_fieldMin.setEnabled(False)
        self.lineEdit_fieldMax.setEnabled(False)
        self.lineEdit_fieldPoints.setEnabled(False)
        self.push_fieldStepsInc.setEnabled(False)
        self.lineEdit_fieldSpeed.setEnabled(False)
        self.lineEdit_biasMin.setEnabled(False)
        self.lineEdit_biasMax.setEnabled(False)
        self.lineEdit_biasPoints.setEnabled(False)
        self.push_biasStepsInc.setEnabled(False)
        self.lineEdit_biasDelay.setEnabled(False)
        self.push_startSweep.setEnabled(False)
        self.push_prelim.setEnabled(False)
        self.push_abortSweep.setEnabled(False)

    def unlockInterface(self):
        self.comboBox_biasSweepMode.setEnabled(True)
        self.comboBox_blinkMode.setEnabled(True)
        self.comboBox_magnetPower.setEnabled(True)
        self.lineEdit_fieldMin.setEnabled(True)
        self.lineEdit_fieldMax.setEnabled(True)
        self.lineEdit_fieldPoints.setEnabled(True)
        self.push_fieldStepsInc.setEnabled(True)
        self.lineEdit_fieldSpeed.setEnabled(True)
        self.lineEdit_biasMin.setEnabled(True)
        self.lineEdit_biasMax.setEnabled(True)
        self.lineEdit_biasPoints.setEnabled(True)
        self.push_biasStepsInc.setEnabled(True)
        self.lineEdit_biasDelay.setEnabled(True)
        self.push_startSweep.setEnabled(True)
        self.push_prelim.setEnabled(True)
        self.push_abortSweep.setEnabled(True)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def closeEvent(self, e):
        pass

#Window for reminding user to turn Toellner output on
class toellnerReminder(QtWidgets.QDialog, Ui_toeReminder):
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
class DialogBox(QtWidgets.QDialog, Ui_DialogBox):
    def __init__(self, magnet, sweepParams, parent = None):
        super(DialogBox, self).__init__(parent)

        self.sweepParamDict = sweepParams
        self.magnetDevice = magnet

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

        if self.magnetDevice == 'IPS 120-10':
            self.magnetPowerSupply.setText('Oxford IPS 120-10 Magnet Power Supply')
            self.magnetPowerSupply.setStyleSheet("QLabel#magnetPowerSupply {color: rgb(168,168,168); font-size: 10pt}")
        elif self.magnetDevice == 'Toellner 8851':
            self.magnetPowerSupply.setText('Toellner 8851 Power Supply')
            self.magnetPowerSupply.setStyleSheet("QLabel#magnetPowerSupply {color: rgb(168,168,168); font-size: 10pt}")

        if self.sweepParamDict['sweep mode'] == 0:
            self.sweepModeSetting.setText('Min to Max')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(168,168,168); font-size: 10pt}")
        elif self.sweepParamDict['sweep mode'] ==1:
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
        self.reject()

#Window for doing preliminary sweeps of the nSOT
class preliminarySweep(QtWidgets.QDialog, Ui_prelimSweep):
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

        self.push_startSweep.clicked.connect(lambda: self.sweep())
        self.push_showFitBtn.clicked.connect(self.showFitFunc)
        self.btnAction = 'sweep'

        self.flag_IcLineShowing = False
        self.pushButton_Show.clicked.connect(self.toggleIcMeasurementLine)

        self.push_closeWin.clicked.connect(self.close)

    def toggleIcMeasurementLine(self):
        if self.flag_IcLineShowing:
            self.sweepPlot.removeItem(self.IcLine)
        else:
            self.sweepPlot.addItem(self.IcLine)
        self.flag_IcLineShowing = not self.flag_IcLineShowing

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
        self.IcLine = pg.InfiniteLine(pos = 0.0 , angle = 90, movable = True, pen = 'b', hoverPen = (50, 50, 200))
        self.IcLine.sigPositionChangeFinished.connect(self.updateIC)

    def updateIC(self, e):
        if not self.data is None:
            xVals = [x[1] for x in self.data]
            yVals = [x[2] for x in self.data]
            absxVals = list(map(abs, xVals))
            xzeroindex = absxVals.index(np.amin(absxVals))
            xscale = float((np.amax(xVals)) - float(np.amin(xVals))) / float((len(xVals) - 1))
            index = int(round(self.IcLine.value() / xscale))
            ssaaRes = float(self.ssaaRes.value())*1000
            winding = float(self.ssaaWinding.value())
            yValue = yVals[index] - yVals[xzeroindex]
            I_c =  np.round(np.absolute((yValue) / (ssaaRes * winding)) * 1e6, decimals = 4)
            self.lineEdit_critCurrLine.setText(str(I_c))

    @inlineCallbacks
    def plotSweepData(self, data):
        self.data = data

        xVals = [x[1] for x in self.data]
        yVals = [x[2] for x in self.data]
        yield self.sleep(0.1)

        self.sweepPlot.plot(x = xVals, y = yVals, pen = 0.5)

        absX = np.absolute(xVals)
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
            self.lineEdit_parRes.setText('Nan')
        else:
            ratio = np.absolute(deltaV_DAC / deltaV_F)
            r = np.round(alpha * (winding * ssaaRes * ratio - biasRes), decimals = 1)
            self.lineEdit_parRes.setText(str(r))

    def toggleStartBtn(self, state):
        reg = "QPushButton#" + 'push_startSweep'
        press = "QPushButton:pressed#" + 'push_startSweep'
        if state == 'sweep':
            regStr = reg + "{color: rgb(0,250,0);background-color:rgb(0,0,0);border: 2px solid rgb(0,250,0);border-radius: 5px}"
            pressStr = press + "{color: rgb(0,0,0); background-color:rgb(0,250,0);border: 2px solid rgb(0,250,0);border-radius: 5px}"
            style = regStr + " " + pressStr
            self.push_startSweep.setText('Start Sweep')
            self.push_startSweep.setStyleSheet(style)
            self.btnAction = 'sweep'
        elif state == 'reset':
            regStr = reg + "{color: rgb(95,107,166);background-color:rgb(0,0,0);border: 2px solid rgb(95,107,166);border-radius: 5px}"
            pressStr = press + "{color: rgb(0,0,0); background-color:rgb(95,107,166);border: 2px solid rgb(95,107,166);border-radius: 5px}"
            style = regStr + " " + pressStr
            self.push_startSweep.setText('Reset')
            self.push_startSweep.setStyleSheet(style)
            self.btnAction = 'reset'

    @inlineCallbacks
    def sweep(self):
        yield self.sleep(0.1)
        if self.btnAction == 'sweep':
            try:
                self.toggleStartBtn('reset')
                self.push_startSweep.setEnabled(False)

                self.sweepPlot.clear()
                #Sets sweep parameters
                biasMin = float(self.biasStart.value())
                biasMax = float(self.biasEnd.value())

                biasPoints = int(self.sweepPoints.value())
                delay = int(self.delay.value() * 1000)

                #Sets DAC Channels
                DAC_out = self.settingsDict['nsot bias output'] - 1

                DAC_in_ref = self.settingsDict['nsot bias input'] - 1
                DAC_in_sig = self.settingsDict['feedback DC input'] - 1
                DAC_in_noise = self.settingsDict['noise input'] - 1

                file_info = yield self.dv.new("nSOT Preliminary Sweep", ['Bias Voltage Index','Bias Voltage'],['DC SSAA Output','Noise'])
                self.dvFileName = file_info[1]
                self.lineEdit_ImageNum.setText(file_info[1][0:5])
                session     = ''
                for folder in file_info[0][1:]:
                    session = session + '\\' + folder
                self.lineEdit_ImageDir.setText(r'\.datavault' + session)

                print('DataVault setup complete')

                yield self.dac.set_voltage(DAC_out, 0)
                try:
                    yield self.window.blink()
                except:
                    printErrorInfo()

                if biasMin != 0:
                    yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [0], [biasMin], abs(int(biasMin * 1000)), 1000)
                    yield self.sleep(1)

                #Do sweep
                print('Ramping up nSOT bias voltage from ' + str(biasMin) + ' to ' + str(biasMax) + '.')
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_sig, DAC_in_noise], [biasMin], [biasMax], biasPoints, delay)

                biasvoltage = np.linspace(biasMin, biasMax, biasPoints)
                formatted_data = []
                for j in range(0, biasPoints):
                        formatted_data.append((j, biasvoltage[j], dac_read[0][j], dac_read[1][j]))
                yield self.dv.add(formatted_data)

                yield self.plotSweepData(formatted_data)

                yield self.sleep(0.25)
                saveDataToSessionFolder(self, self.window.sessionFolder, self.dvFileName)

                #Return to zero voltage gently
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [biasMax], [0], abs(int(biasMax * 1000)), 1000)
                yield self.sleep(0.25)
                yield self.dac.set_voltage(DAC_out, 0)
                self.push_startSweep.setEnabled(True)

            except:
                printErrorInfo()
        elif self.btnAction == 'reset':
            self.toggleStartBtn('sweep')

    def sleep(self, secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def closeEvent(self, e):
        self.window.push_prelim.setEnabled(True)
        self.close()

class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
