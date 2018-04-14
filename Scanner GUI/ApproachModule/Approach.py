import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import time
from collections import deque

path = sys.path[0] + r"\ApproachModule"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\Approach-v2.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_generalApproachSettings, QtBaseClass = uic.loadUiType(path + r"\generalApproachSettings.ui")
Ui_MeasurementSettings, QtBaseClass = uic.loadUiType(path + r"\MeasurementSettings.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    newPLLData = QtCore.pyqtSignal(float, float)
    newFdbkDCData = QtCore.pyqtSignal(float)
    newFdbkACData = QtCore.pyqtSignal(float)
    updateFeedbackStatus = QtCore.pyqtSignal(bool)
    updateConstantHeightStatus = QtCore.pyqtSignal(bool)

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.feedback = False
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()        

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Connect measurement buttons
        self.push_StartControllers.clicked.connect(self.toggleControllers)
        
        #Connect advanced setting pop up menues
        self.push_MeasurementSettings.clicked.connect(self.showMeasurementSettings)
        self.push_GenSettings.clicked.connect(self.showGenSettings)
        #Connect incrementing buttons
        self.push_addFreq.clicked.connect(self.incrementFreqThresh)
        self.push_subFreq.clicked.connect(self.decrementFreqThresh)
        self.push_addFeedback.clicked.connect(self.incrementFeedbackThresh)
        self.push_subFeedback.clicked.connect(self.decrementFeedbackThresh)

        self.lineEdit_freqSet.editingFinished.connect(self.setFreqThresh)

        self.lineEdit_P.editingFinished.connect(self.set_p)
        self.lineEdit_I.editingFinished.connect(self.set_i)
        self.lineEdit_D.editingFinished.connect(self.set_d)
        
        self.lineEdit_PID_Const_Height.editingFinished.connect(self.set_pid_const_height)
        self.lineEdit_PID_Step_Size.editingFinished.connect(self.set_pid_step_size)
        self.lineEdit_PID_Step_Speed.editingFinished.connect(self.set_pid_step_speed)
        
        self.lineEdit_Step_Const_Height.editingFinished.connect(self.set_step_const_height)
        self.lineEdit_Step_Step_Size.editingFinished.connect(self.set_step_step_size)
        self.lineEdit_Step_Step_Speed.editingFinished.connect(self.set_step_step_speed)

        #self.push_PIDApproach.clicked.connect(self.startPIDApproachSequence)
        self.push_Abort.clicked.connect(self.abortApproachSequence)
        
        self.push_ApproachForFeedback.clicked.connect(self.startFeedbackApproachSequence)
        self.push_PIDApproachForConstant.clicked.connect(self.startPIDConstantHeightApproachSequence)
        
        self.push_StepApproachForConstant.clicked.connect(self.startStepConstantHeightApproachSequence)

        self.push_Home.clicked.connect(self.returnToHomePosition)
        self.push_Withdraw.clicked.connect(self.withdrawSpecifiedDistance)
        self.lineEdit_Withdraw.editingFinished.connect(self.setWithdrawDistance)

        self.radioButton_plus.toggled.connect(self.setFreqThreshholdSign)

        self.push_Fake.clicked.connect(self.sendFakeSignals)
        #Initialize all the labrad connections as not connected
        self.cxn = False
        self.cpsc = False
        self.dac = False
        self.hf = False
        self.dcbox = False

        self.measuring = False
        self.approaching = False
        
        #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in
        self.PID_Index = 1

        self.Atto_Z_Voltage = 0.0 #Voltage being sent to Z of attocubes. Eventually should synchronize with the 
                                  #Scan module Atto Z voltage
        self.Temperature = 293 #in kelvin

        self.withdrawDistance = 2e-6
        self.constantHeight = 100e-9

        self.JPE_Steps = []

        self.deltaf_track_length = 100
        self.deltafData = deque([0]*self.deltaf_track_length)
                
        '''
        Below is the initialization of all the default measurement settings. Eventually organize into a dictionary
        '''
        self.PLL_Locked = 0 #PLL starts not locked

        self.measurementSettings = {
                'meas_pll'            : False,
                'meas_fdbk_dc'        : False,
                'meas_fdbk_ac'        : False,
                'pll_targetBW'        : 25,       #target bandwidth for pid advisor
                'pll_advisemode'      : 2,         #advisor mode. 0 is just proportional term, 1 just integral, 2 is prop + int, and 3 is full PID
                'pll_input'           : 1,         #hf2li input that has the signal for the pll
                'pll_centerfreq'      : None,      #center frequency of the pll loop
                'pll_phase_setpoint'  : None,      #phase setpoint of pll pid loop
                'pll_range'           : 20,        #range around center frequency that the pll is allowed to go
                'pll_harmonic'        : 1,         #harmonic of the input to the pll
                'pll_tc'              : 553.82e-6, #pll time constant
                'pll_filterBW'        : 125.0,     #pll filter bandwidth 
                'pll_filterorder'     : 4,         #pll filter order (how many filters are cascaded)
                'pll_p'               : 0.349361,     #pll pid proportional term
                'pll_i'               : 0.164253,     #pll pid integral term 
                'pll_d'               : 0,         #pll pid derivative term
                'pll_simBW'           : 28.69,         #current pid term simulated bandwidth 
                'pll_pm'              : 73.97,         #pll pid simulated phase margin (relevant to the stability of loop)   
                'pll_rate'            : 1.842e+6,  #Sampling rate of the PLL. Cannot be changed, despite it being spit out by the pid advisor. Just... is what it is. 
                'pll_output'          : 1,         #hf2li output to be used to completel PLL loop. 
                'pll_output_amp'      : 0.01,      #output amplitude   
                'fdbk_dc_input'       : 4,         # 1 indexed input of DAC ADC (5 and 6 correspond to Aux 1 and 2 from Zurich
                'fdbk_dc_setpoint'    : 0,         # DC setpoint from which to determine the change in feebdack output
                'fdbk_ac_input'       : 6,         # 1 indexed input of DAC ADC (5 and 6 correspond to Aux 1 and 2 from Zurich
                'fdbk_ac_setpoint'    : 0,         # AC setpoint from which to determine the change in feebdack output
                'z_mon_input'         : 1,         # Either 1 (aux in 1) or 2 (aux in 2) on the Zurich
                }

        '''
        Below is the initialization of all the default general approach settingss
        '''
        
        self.generalSettings = {
                'step_z_output'              : 1,     #output that goes to Z of attocubes from DAC ADC (1 indexed)
                'pid_z_output'               : 1,     #aux output that goes to Z of attocubes from HF2LI (1 indexed)
                'sumboard_toggle'            : 1,     #Output from the DC Box that toggles the summing amplifier (1 indexed)
                'jpe_tip_height'             : 24e-3, #Tip height from sample stage in meters. 
                'jpe_module_address'         : 1,     #Pretty sure this is always 1 unless we add more modules to the JPE controller
                'jpe_steps'                  : 500,   #Number of step forward in z direction taken by JPEs after attocube fully extend and retract
                'jpe_size'                   : 100,   #relative step size of jpe steps
                'jpe_freq'                   : 250,   #Frequency of steps on JPE approach
                'jpe_temperature'            : 293,   #Temperature setting of the JPEs
                'step_retract_speed'         : 1e-5, #speed in m/s when retracting
                'step_retract_time'          : 2.4,    #time required in seconds for full atto retraction
                'pid_retract_speed'          : 1e-5, #speed in m/s when retracting
                'pid_retract_time'           : 2.4,    #time required in seconds for full atto retraction
                'total_retract_dist'         : 24e-6, #distance retracted in meters by the attocube (eventually should update with temperature)
        }
                
        '''
        Below is the initialization of all the default PID Approach Settings
        '''
        self.PIDApproachSettings = {
                'p'                    : 0,     #Proportional term of approach PID 
                'i'                    : 1,     #Integral term of approach PID 
                'd'                    : 0,     #Derivative term of approach PID 
                'step_size'            : 10e-9, #Step size for feedback approach in meters
                'step_speed'           : 10e-9, #Step speed for feedback approach in m/s
                'height'               : 100e-9,#Height for constant height scanning
        }
        
        '''
        Below is the initialization of all the default Stepwise Approach Settings
        '''
        self.StepApproachSettings = {
                'step_size'            : 10e-9, #Step size for feedback approach in meters
                'step_speed'           : 10e-9, #Step speed for feedback approach in m/s
                'height'               : 100e-9,#Height for constant height scanning
        }
        
        #TODO represent PID parameters in terms of m/s per Hz instead of Volts / s per Hz

        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p'])) 
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i'])) 
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d'])) 
        self.lineEdit_PID_Step_Size.setText(formatNum(self.PIDApproachSettings['step_size'])) 
        self.lineEdit_PID_Step_Speed.setText(formatNum(self.PIDApproachSettings['step_speed'])) 
        self.lineEdit_PID_Const_Height.setText(formatNum(self.PIDApproachSettings['height']))

        self.lineEdit_Step_Step_Size.setText(formatNum(self.StepApproachSettings['step_size'])) 
        self.lineEdit_Step_Step_Speed.setText(formatNum(self.StepApproachSettings['step_speed'])) 
        self.lineEdit_Step_Const_Height.setText(formatNum(self.StepApproachSettings['height']))        

        '''
        Below is the initialization of all the thresholds for surface detection
        '''
        #Initialize values
        self.freqThreshold = 0.4
        self.setFreqThresh()
        
        self.feedbackThresh = 0.1
        self.setFeedbackThresh()
        
        self.feedbackACThresh = 0.1
        self.setFeedbackACThresh()

        self.lockInterface()

    def moveDefault(self):    
        self.move(10,170)

    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.hf = dict['hf2li']
            self.dac = dict['dac_adc']
            self.cpsc = dict['cpsc']
            self.dcbox = dict['dc_box']
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  
        if not self.cxn: 
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.hf:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.cpsc:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.dac:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.dcbox:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
            self.unlockInterface()
            self.lockFreq()
            self.lockFdbkDC()
            self.lockFdbkAC()
            self.zeroHF2LI_Aux_Out()
            self.initializePID()
            self.monitorZ = True
            self.monitorZVoltage()

    @inlineCallbacks
    def zeroHF2LI_Aux_Out(self, c= None):
        try:
            #Check to see if any PIDs are on. If they are, turn them off. Them being on prevents proper zeroing. 
            pid_on = yield self.hf.get_pid_on(1)
            if pid_on:
                yield self.hf.set_pid_on(1, False)
            pid_on = yield self.hf.get_pid_on(2)
            if pid_on:
                yield self.hf.set_pid_on(2, False)
            pid_on = yield self.hf.get_pid_on(3)
            if pid_on:
                yield self.hf.set_pid_on(3, False)
            pid_on = yield self.hf.get_pid_on(4)
            if pid_on:
                yield self.hf.set_pid_on(4, False)

            #Set outputs to manual control (note, if PID is on it overpowers manual control)
            yield self.hf.set_aux_output_signal(1, -1)
            yield self.hf.set_aux_output_signal(2, -1)
            yield self.hf.set_aux_output_signal(3, -1)
            yield self.hf.set_aux_output_signal(4, -1)

            #Set offsets to 0
            yield self.hf.set_aux_output_offset(1,0)
            yield self.hf.set_aux_output_offset(2,0)
            yield self.hf.set_aux_output_offset(3,0)
            yield self.hf.set_aux_output_offset(4,0)

        except Exception as inst:
            print inst

    def disconnectLabRAD(self):
        if self.hf is not False:
            #Makes sure that stops sending signals to monitor Z voltage
            self.monitorZ = False
            #Turn off the PLL 
            self.hf.set_pll_off(self.measurementSettings['pll_output'])
        self.cxn = False
        self.cpsc = False
        self.dac = False
        self.dcbox = False
        self.hf = False
        self.lockInterface()
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")

            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
    def showAdvancedFdbkApproach(self):      
        advApp = advancedFdbkApproachSettings(self.reactor, self.feedbackApproachSettings, self)
        if advApp.exec_():
            self.feedbackApproachSettings = advApp.getValues()

    def showAdvancedPIDApproach(self):
        advFeed = advancedPIDApproachSettings(self.reactor, self.PIDApproachSettings, self)
        if advFeed.exec_():
            self.PIDApproachSettings = advFeed.getValues()
            self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p'])) 
            self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i'])) 
            self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d'])) 
            self.setPIDParameters()
            
    def showMeasurementSettings(self):
        MeasSet = MeasurementSettings(self.reactor, self.measurementSettings, parent = self, server = self.hf)
        if MeasSet.exec_():
            self.measurementSettings = MeasSet.getValues()
            
            if self.measurementSettings['meas_pll']:
                self.unlockFreq()
            else:
                self.lockFreq()
                
            if self.measurementSettings['meas_fdbk_dc']:
                self.unlockFdbkDC()
            else:
                self.lockFdbkDC()
                
            if self.measurementSettings['meas_fdbk_ac']:
                self.unlockFdbkAC()
            else:
                self.lockFdbkAC()
            #TODO disable not selected measurements
        
    def showGenSettings(self):
        GenSet = generalApproachSettings(self.reactor, self.generalSettings, parent = self)
        if GenSet.exec_():
            self.generalSettings = GenSet.getValues()
        
    def setupAdditionalUi(self):
        self.freqSlider.close()
        self.freqSlider = MySlider(parent = self.centralwidget)
        self.freqSlider.setGeometry(120,100,260,70)
        self.freqSlider.setMinimum(0)
        self.freqSlider.setMaximum(1000000)
        self.freqSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.freqSlider.setTickPos([0.008, 0.01, 0.02, 0.04,0.06, 0.08, 0.1,0.2,0.4,0.6, 0.8,1, 2, 4, 6, 8, 10, 20])
        self.freqSlider.setNumPos([0.01, 0.1,1,10])
        self.freqSlider.lower()
        
        self.freqSlider.logValueChanged.connect(self.updateFreqThresh)
        
        self.feedbackSlider.close()
        self.feedbackSlider = MySlider(parent = self.centralwidget)
        self.feedbackSlider.setGeometry(120,175,260,70)
        self.feedbackSlider.setMinimum(0)
        self.feedbackSlider.setMaximum(1000000)
        self.feedbackSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.feedbackSlider.setTickPos([0.008, 0.01, 0.02, 0.04,0.06, 0.08, 0.1,0.2,0.4,0.6, 0.8,1, 2, 4, 6, 8, 10, 20])
        self.feedbackSlider.setNumPos([0.01, 0.1,1,10])
        self.feedbackSlider.lower()
        
        self.feedbackSlider.logValueChanged.connect(self.updateFeedbackThresh)
        
        self.feedbackACSlider.close()
        self.feedbackACSlider = MySlider(parent = self.centralwidget)
        self.feedbackACSlider.setGeometry(120,250,260,70)
        self.feedbackACSlider.setMinimum(0)
        self.feedbackACSlider.setMaximum(1000000)
        self.feedbackACSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.feedbackACSlider.setTickPos([0.008, 0.01, 0.02, 0.04,0.06, 0.08, 0.1,0.2,0.4,0.6, 0.8,1, 2, 4, 6, 8, 10, 20])
        self.feedbackACSlider.setNumPos([0.01, 0.1,1,10])
        self.feedbackACSlider.lower()
        
        self.feedbackACSlider.logValueChanged.connect(self.updateFeedbackACThresh)

    def set_p(self):
        val = readNum(str(self.lineEdit_P.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['p'] = val
            self.setPIDParameters()
        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))
        
    def set_i(self):
        #note that i can never be set to 0, otherwise the hidden integrator value jumps back to 0
        #which can lead to dangerous voltage spikes to the attocube. 
        val = readNum(str(self.lineEdit_I.text()))
        if isinstance(val,float):
            if np.abs(val)> 1e-30:
                self.PIDApproachSettings['i'] = val
                print 'Setting PID parameters'
                self.setPIDParameters()
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))
        
    def set_d(self):
        val = readNum(str(self.lineEdit_D.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['d'] = val
            self.setPIDParameters()
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))
        
    def set_pid_const_height(self):
        val = readNum(str(self.lineEdit_PID_Const_Height.text()))
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > self.generalSettings['total_retract_dist']:
                val = self.generalSettings['total_retract_dist']
            self.PIDApproachSettings['height'] = val
        self.lineEdit_PID_Const_Height.setText(formatNum(self.PIDApproachSettings['height']))
        
    def set_pid_step_size(self):
        val = readNum(str(self.lineEdit_PID_Step_Size.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['step_size'] = val
        self.lineEdit_PID_Step_Size.setText(formatNum(self.PIDApproachSettings['step_size']))
        
    def set_pid_step_speed(self):
        val = readNum(str(self.lineEdit_PID_Step_Speed.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['step_speed'] = val
        self.lineEdit_PID_Step_Speed.setText(formatNum(self.PIDApproachSettings['step_speed']))
        
    def set_step_const_height(self):
        val = readNum(str(self.lineEdit_Step_Const_Height.text()))
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > self.generalSettings['total_retract_dist']:
                val = self.generalSettings['total_retract_dist']
            self.StepApproachSettings['height'] = val
        self.lineEdit_Step_Const_Height.setText(formatNum(self.StepApproachSettings['height']))
        
    def set_step_step_size(self):
        val = readNum(str(self.lineEdit_Step_Step_Size.text()))
        if isinstance(val,float):
            self.StepApproachSettings['step_size'] = val
        self.lineEdit_Step_Step_Size.setText(formatNum(self.StepApproachSettings['step_size']))
        
    def set_step_step_speed(self):
        val = readNum(str(self.lineEdit_Step_Step_Speed.text()))
        if isinstance(val,float):
            self.StepApproachSettings['step_speed'] = val
        self.lineEdit_Step_Step_Speed.setText(formatNum(self.StepApproachSettings['step_speed']))
        
    def set_voltage_calibration(self, calibration):
        self.x_volts_to_meters = float(calibration[1])
        self.y_volts_to_meters = float(calibration[2])
        self.z_volts_to_meters = float(calibration[3])
        self.x_meters_max = float(calibration[4])
        self.y_meters_max = float(calibration[5])
        self.z_meters_max = float(calibration[6])
        self.x_volts_max = float(calibration[7])
        self.y_volts_max = float(calibration[8])
        self.z_volts_max = float(calibration[9])
        
        self.generalSettings['total_retract_dist'] = self.z_meters_max
        
        self.generalSettings['pid_retract_time'] = self.z_meters_max / self.generalSettings['pid_retract_speed']
        self.generalSettings['step_retract_time'] = self.z_meters_max / self.generalSettings['step_retract_speed']

        print 'Approach Window Voltage Calibration Set'

    def sendFakeSignals(self):
        self.updateConstantHeightStatus.emit(True)
        self.updateFeedbackStatus.emit(True)
        print 'Fake signals sent'

#--------------------------------------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to updating thresholds."""
    
    def updateFreqThresh(self, value = 0):
        try:
            self.freqThreshold = value
            self.lineEdit_freqSet.setText(formatNum(self.freqThreshold))
            self.freqSlider.setPosition(self.freqThreshold)
            self.setFreqThreshholdSign()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def setFreqThreshholdSign(self, c = None):
        if self.measurementSettings['pll_centerfreq'] is not None:
            if self.radioButton_plus.isChecked():
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] + self.freqThreshold)
            else:
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] - self.freqThreshold)

    def setFreqThresh(self):
        new_freqThresh = str(self.lineEdit_freqSet.text())
        val = readNum(new_freqThresh)
        if isinstance(val,float):
            if val < 0.008:
                val = 0.008
            elif val > 20:
                val = 20
            self.updateFreqThresh(value = val)
        else:
            self.lineEdit_freqSet.setText(formatNum(self.freqThreshold))
            
    def incrementFreqThresh(self):
        val = self.freqThreshold * 1.01
        if val < 0.008:
            val = 0.008
        elif val > 20:
            val = 20
        self.updateFreqThresh(value = val)
        
    def decrementFreqThresh(self):
        val = self.freqThreshold * 0.99
        if val < 0.008:
            val = 0.008
        elif val > 20:
            val = 20
        self.updateFreqThresh(value = val)
        
    def updateFeedbackThresh(self, value = 0):
        try:
            self.feedbackThreshold = value
            self.lineEdit_feedbackSet.setText(formatNum(self.feedbackThreshold))
            self.feedbackSlider.setPosition(self.feedbackThreshold)
        except Exception as inst:
            print inst
            
    def setFeedbackThresh(self):
        new_feedbackThresh = str(self.lineEdit_feedbackSet.text())
        val = readNum(new_feedbackThresh)
        if isinstance(val,float):
            if val < 0.008:
                val = 0.008
            elif val > 20:
                val = 20
            self.updateFeedbackThresh(value = val)
        else:
            self.lineEdit_feedbackSet.setText(formatNum(self.feedbackThreshold))
            
    def incrementFeedbackThresh(self):
        val = self.feedbackThreshold * 1.01
        if val < 0.008:
            val = 0.008
        elif val > 20:
            val = 20
        self.updateFeedbackThresh(value = val)
        
    def decrementFeedbackThresh(self):
        val = self.feedbackThreshold * 0.99
        if val < 0.008:
            val = 0.008
        elif val > 20:
            val = 20
        self.updateFeedbackThresh(value = val)
        
    def updateFeedbackACThresh(self, value = 0):
        try:
            self.feedbackACThreshold = value
            self.lineEdit_feedbackACSet.setText(formatNum(self.feedbackACThreshold))
            self.feedbackACSlider.setPosition(self.feedbackACThreshold)
        except Exception as inst:
            print inst
            
    def setFeedbackACThresh(self):
        new_feedbackACThresh = str(self.lineEdit_feedbackACSet.text())
        val = readNum(new_feedbackACThresh)
        if isinstance(val,float):
            if val < 0.008:
                val = 0.008
            elif val > 20:
                val = 20
            self.updateFeedbackACThresh(value = val)
        else:
            self.lineEdit_feedbackACSet.setText(formatNum(self.feedbackACThreshold))
            
    def incrementFeedbackACThresh(self):
        val = self.feedbackACThreshold * 1.01
        if val < 0.008:
            val = 0.008
        elif val > 20:
            val = 20
        self.updateFeedbackACThresh(value = val)
        
    def decrementFeedbackACThresh(self):
        val = self.feedbackACThreshold * 0.99
        if val < 0.008:
            val = 0.008
        elif val > 20:
            val = 20
        self.updateFeedbackACThresh(value = val)
#--------------------------------------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to toggling measurements."""
    @inlineCallbacks
    def toggleControllers(self, c = None):
        try:
            if not self.measuring:
                self.push_StartControllers.setText("Stop Meas.")  
                style = """ QPushButton#push_StartControllers{
                        color: rgb(50,168,50);
                        background-color:rgb(0,0,0);
                        border: 1px solid rgb(50,168,50);
                        border-radius: 5px
                        }  
                        QPushButton:pressed#push_StartControllers{
                        color: rgb(168,168,168);
                        background-color:rgb(95,107,166);
                        border: 1px solid rgb(168,168,168);
                        border-radius: 5px
                        }
                        """
                self.push_StartControllers.setStyleSheet(style)
                self.measuring = True
                self.push_MeasurementSettings.setEnabled(False)
                if self.measurementSettings['meas_pll']:
                    yield self.setHF2LI_PLL_Settings()
                    self.startFrequencyMonitoring()
                if self.measurementSettings['meas_fdbk_dc']:
                    self.startFdbkDCMonitoring()
                if self.measurementSettings['meas_fdbk_ac']:
                    self.startFdbkACMonitoring()
            else: 
                self.push_StartControllers.setText("Start Meas.")
                style = """ QPushButton#push_StartControllers{
                        color: rgb(168,168,168);
                        background-color:rgb(0,0,0);
                        border: 1px solid rgb(168,168,168);
                        border-radius: 5px
                        }  
                        QPushButton:pressed#push_StartControllers{
                        color: rgb(168,168,168);
                        background-color:rgb(95,107,166);
                        border: 1px solid rgb(168,168,168);
                        border-radius: 5px
                        }
                        """
                self.push_StartControllers.setStyleSheet(style)
                self.measuring = False
                self.push_MeasurementSettings.setEnabled(True)
                yield self.sleep(0.1)
                self.PLL_Locked = 0
                self.push_Locked.setStyleSheet("""#push_Locked{
                        background: rgb(161, 0, 0);
                        border-radius: 5px;
                        }""")
        except Exception as inst:
            print inst
            
    def setWorkingPoint(self, freq, phase, out, amp):
        #self.checkBox_Freq.setCheckable(True)
        #self.push_CenterSet.setStyleSheet("""#push_CenterSet{
        #                                    background: rgb(0, 170, 0);
        #                                    border-radius: 5px;
        #                                    }""")
        self.measurementSettings['pll_centerfreq'] = freq
        self.measurementSettings['pll_phase_setpoint'] = phase
        self.measurementSettings['pll_output'] = out
        self.measurementSettings['pll_output_amp'] = amp

        
    @inlineCallbacks
    def setHF2LI_PLL_Settings(self, c = None):
        try:
            #first disable autoSettings
            yield self.hf.set_pll_autocenter(self.measurementSettings['pll_output'],False)
            yield self.hf.set_pll_autotc(self.measurementSettings['pll_output'],False)
            yield self.hf.set_pll_autopid(self.measurementSettings['pll_output'],False)

            #All settings are set for PLL 1
            yield self.hf.set_pll_input(self.measurementSettings['pll_output'],self.measurementSettings['pll_input'])
            yield self.hf.set_pll_freqcenter(self.measurementSettings['pll_output'], self.measurementSettings['pll_centerfreq'])
            yield self.hf.set_pll_setpoint(self.measurementSettings['pll_output'],self.measurementSettings['pll_phase_setpoint'])
            yield self.hf.set_pll_freqrange(self.measurementSettings['pll_output'],self.measurementSettings['pll_range'])
            
            yield self.hf.set_pll_harmonic(self.measurementSettings['pll_output'],self.measurementSettings['pll_harmonic'])
            yield self.hf.set_pll_tc(self.measurementSettings['pll_output'],self.measurementSettings['pll_tc'])
            self.PLL_TC = yield self.hf.get_pll_tc(self.measurementSettings['pll_output'])
            self.PLL_FilterBW = calculate_FilterBW(self.measurementSettings['pll_filterorder'], self.measurementSettings['pll_tc'])
            
            yield self.hf.set_pll_filterorder(self.measurementSettings['pll_output'],self.measurementSettings['pll_filterorder'])
            
            yield self.hf.set_pll_p(self.measurementSettings['pll_output'],self.measurementSettings['pll_p'])
            yield self.hf.set_pll_i(self.measurementSettings['pll_output'],self.measurementSettings['pll_i'])
            yield self.hf.set_pll_d(self.measurementSettings['pll_output'],self.measurementSettings['pll_d'])

        except Exception as inst:
            print inst
        
    @inlineCallbacks
    def startFrequencyMonitoring(self, c=None):
        try:
            #Turn on out and start PLL
            yield self.hf.set_output(self.measurementSettings['pll_output'], True)
            yield self.hf.set_pll_on(self.measurementSettings['pll_output'])
            
            self.deltafData = deque([0]*self.deltaf_track_length)
            
            while self.measuring:
                deltaf = yield self.hf.get_pll_freqdelta(self.measurementSettings['pll_output'])
                phaseError = yield self.hf.get_pll_error(self.measurementSettings['pll_output'])
                locked = yield self.hf.get_pll_lock(self.measurementSettings['pll_output'])
                self.lineEdit_freqCurr.setText(formatNum(deltaf))
                self.lineEdit_phaseError.setText(formatNum(phaseError))
                
                #TODO: prevent adding data points if JPEs are stepping
                #Add frequency data to list
                self.deltafData.appendleft(deltaf)
                self.deltafData.pop()

                self.newPLLData.emit(deltaf, phaseError)

                if self.PLL_Locked != locked:
                    if locked == 0:
                        self.push_Locked.setStyleSheet("""#push_Locked{
                                        background: rgb(161, 0, 0);
                                        border-radius: 5px;
                                        }""")
                    else: 
                        self.push_Locked.setStyleSheet("""#push_Locked{
                                        background: rgb(0, 170, 0);
                                        border-radius: 5px;
                                        }""")

                    self.PLL_Locked = locked

            yield self.hf.set_pll_off(self.measurementSettings['pll_output'])
            yield self.hf.set_output(self.measurementSettings['pll_output'], False)
        except Exception as inst:
            print inst
            
    @inlineCallbacks
    def startFdbkDCMonitoring(self, c = None):
        try:
            measChnl = self.measurementSettings['fdbk_dc_input']
            setpoint = self.measurementSettings['fdbk_dc_setpoint']
            while self.measuring:
                if measChnl <= 4:
                    data = yield self.dac.read_voltage(measChnl-1)
                else:
                    data = yield self.hf.get_aux_input_value(measChnl - 4)
                    
                data = data - setpoint
                self.lineEdit_fdbkDC.setText(formatNum(data))
                self.newFdbkDCData.emit(data)
        except Exception as inst:
            print inst
    
    @inlineCallbacks
    def startFdbkACMonitoring(self, c = None):
        try:
            measChnl = self.measurementSettings['fdbk_ac_input']
            setpoint = self.measurementSettings['fdbk_ac_setpoint']
            while self.measuring:
                if measChnl <= 4:
                    data = yield self.dac.read_voltage(measChnl-1)
                else:
                    data = yield self.hf.get_aux_input_value(measChnl-4)
                
                data = data - setpoint
                self.lineEdit_fdbkAC.setText(formatNum(data))
                self.newFdbkACData.emit(data)
        except Exception as inst:
            print inst
            
            
#--------------------------------------------------------------------------------------------------------------------------#
    """ The following section contains the stepwise approach sequence."""
    """
    @inlineCallbacks
    def startApproachSequence(self, c = None):
        '''
        Function needs to be updated with new HF2LI Server subcribe / poll syntax.
        
        General procedure: 
            1. Measure deltaf, get average value. 
            2. Compare to threshhold. If below, procedure to step 3. Otherwise, you're done!
            3. Attempt to step the z voltage by the specified step size. 
               If this is possible (ie. z + z_step < z_max), return to step 1. 
               If not, proceed to step 4. 
            4. Set z voltage back to 0. 
            5. Step JPEs forward. Then return to step 1. 
        '''
        
        self.approaching = True
        
        #yield self.cpsc.set_height(self.JPE_Tip_Height*1000 + 33.9)
        
        while self.approaching:
            yield self.sleep(0.25)
            #data = yield self.hf.poll_pll(1, self.Approach_MeasTime, 500)
            #df_avg = np.avg(data[0])
            #if dv_avg > self.freqThreshold:
            #    self.approaching = False
            #    break

            #Here need to compute conversion rate between voltage and step size
            start_voltage = self.Atto_Z_Voltage
            end_voltage = self.Atto_Z_Voltage + self.stepwiseApproachSettings['atto_z_step_size'] * self.z_volts_to_meters

            if end_voltage < 10 and self.approaching:
                #yield self.dac.buffer_ramp([self.Atto_Z_DAC_Out],[],[start_voltage],[end_voltage], self.stepwiseApproachSettings['atto_z_points'], self.stepwiseApproachSettings['atto_z_points_delay'] * 1e6)
                self.lineEdit_FineZ.setText(formatNum(end_voltage / self.z_volts_to_meters, 3))
                self.Atto_Z_Voltage = end_voltage
                self.progressBar.setValue(int(100*self.Atto_Z_Voltage))
            elif self.approaching:
                end_voltage = 0
                self.Atto_Z_Voltage = end_voltage
                self.progressBar.setValue(int(100*self.Atto_Z_Voltage))
                #retract atto
                #yield self.dac.buffer_ramp([self.Atto_Z_DAC_Out],[],[start_voltage],[end_voltage], self.stepwiseApproachSettings['atto_retract_points'], self.stepwiseApproachSettings['atto_retract_points_delay'] * 1e6)
                self.lineEdit_FineZ.setText(formatNum(end_voltage / self.z_volts_to_meters))
                #Do a coarse step forward
                #yield self.cpsc.move_z(self.JPE_Module_Address, self.Temperature, , self.JPE_Approach_Freq, self.JPE_Approach_Size, self.JPE_Approach_Steps)
            print 'Starting at voltage: ' + str(start_voltage) + '. Finishing at voltage: ' + str(end_voltage)
    """

    def updateCoarseSteps(self):
        try:
            steps = 0
            for a in self.JPE_Steps:
                steps = steps + a[4]
            self.lineEdit_CoarseZ.setText(formatNum(np.abs(steps), 0))
        except Exception as inst:
            print inst

    def abortApproachSequence(self):
        self.approaching = False

#--------------------------------------------------------------------------------------------------------------------------#
    """ The following section contains the PID approach sequence and all related functions."""
        
    @inlineCallbacks
    def startPIDApproachSequence(self, c = None):
        '''
        General procedure: 
            1. Describe this at some point
        '''
    
        #Add checks that controllers are running and working properly
        self.approaching = True
        self.label_approachStatus.setText('Approaching with Zurich')
        #Initializes all the PID settings
        yield self.setHF2LI_PID_Settings()
        
        #Set the output range to be 0 to the max z voltage, which is specified by the temperture of operation. 
        yield self.setPIDOutputRange(self.z_volts_max)

        #Toggle the sum board to be 1 to 1 
        yield self.dcbox.set_voltage(self.PIDApproachSettings['sumboard_toggle']-1, 0)
        
        yield self.hf.set_pid_on(self.PID_Index, True)
        i = 0
        while self.approaching:
            '''
            #Eventually figure out how to do this properly so it doesn't trigger during JPE steps. 
            points_above_freq_thresh = 0
            for deltaf in self.deltafData:
                points_above_freq_thresh = points_above_freq_thresh + (deltaf > self.freqThreshold)
                
            if points_above_freq_thresh > 10:
                self.label_approachStatus.setText('Surface contacted')
                #Maybe eventually add auto retract function
            '''
            z_voltage = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])

            if z_voltage >= (self.z_volts_max - 0.001) and self.approaching:
                yield self.hf.set_pid_on(self.PID_Index, False)
                self.label_approachStatus.setText('Retracting Attocubes')
                #Find desired retract speed in volts per second
                retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
                yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)
                
                if self.approaching:
                    self.label_approachStatus.setText('Stepping with JPEs')
                    #Step JPE by specified amount in z direction
                    yield self.cpsc.move_z(int(self.PIDApproachSettings['jpe_module_address']), int(self.PIDApproachSettings['jpe_temperature']), int(self.PIDApproachSettings['jpe_approach_freq']), int(self.PIDApproachSettings['jpe_approach_size']), -1.0*self.PIDApproachSettings['jpe_approach_steps'],30)
                    self.JPE_Steps.append([int(self.PIDApproachSettings['jpe_module_address']), int(self.PIDApproachSettings['jpe_temperature']), int(self.PIDApproachSettings['jpe_approach_freq']), int(self.PIDApproachSettings['jpe_approach_size']), -1.0*self.PIDApproachSettings['jpe_approach_steps']])
                    try:
                        self.updateCoarseSteps()
                    except Exception as inst:
                        print inst
                    
                if self.approaching:
                    #Turn back on
                    yield self.hf.set_pid_on(self.PID_Index, True)
                    self.label_approachStatus.setText('Approaching with Zurich')
                
        yield self.hf.set_pid_on(self.PID_Index, False)
        self.label_approachStatus.setText('Idle')
        
    @inlineCallbacks
    def initializePID(self, c = None):
        '''
        This function ensures the integrator value of the PID is set such that the starting output voltage is 0 volts. 
        By default, when the range is from 0 to 3 V, the starting output voltage is 1.5V; this fixes that problem. 
        Also sets the output range from 0 to z_volts_max, which is the temperature dependent voltage range.
        '''
        try:
            #Make sure the PID is off
            pid_on = yield self.hf.get_pid_on(self.PID_Index)
            if pid_on:
                yield self.hf.set_pid_on(self.PID_Index, False)

            #Set the output range to be 0 to 3 V, which is the required range for room temperature. 
            yield self.setPIDOutputRange(self.z_volts_max)

            #Set integral term to 1, and 0 to the rest
            yield self.hf.set_pid_p(self.PID_Index, 0)
            yield self.hf.set_pid_d(self.PID_Index, 0)
            yield self.hf.set_pid_i(self.PID_Index, 1)

            #Sets the PID input signal to be the auxiliary output 
            yield self.hf.set_pid_input_signal(self.PID_Index, 5)
            #Sets channel to be aux output 4, which should never be in use elsewhere (as warned on the GUI)
            yield self.hf.set_pid_input_channel(self.PID_Index, 4)

            #The following two settings get reset elsewhere in the code before running anything important. 
            #They're useful for understanding the units if the set integrator term (and making sure that
            # 1 is sufficient.)

            #Sets the output signal type to be an auxiliary output offset
            yield self.hf.set_pid_output_signal(self.PID_Index, 3)
            #Sets the correct channel of the aux output
            yield self.hf.set_pid_output_channel(self.PID_Index, self.generalSettings['pid_z_output'])
            
            yield self.hf.set_pid_setpoint(self.PID_Index, -10)
            #Sets the setpoint to be -10V. The input signal (aux output 4), is always left as 0 Volt output. 
            #This means that the rate at which the voltage changes is this setpoint (-10V) times the integrator
            # value (1 /s). So, this changes the voltage at a rate of 10V/s. 
            
            #Once monitored, can turn the multiplier to 0 so that the output is always 0 volts. 
            yield self.hf.set_aux_output_monitorscale(self.generalSettings['pid_z_output'],0)
            #Set the aux output corresponding the to output going to the attocubes to be monitored. 
            yield self.hf.set_aux_output_signal(self.generalSettings['pid_z_output'], -2)

            #At this point, turn on the PID. 
            yield self.hf.set_pid_on(self.PID_Index, True)
            #Wait for the voltage to go from 5V to 0V (should take 0.5 second). However, there's a weird bug that
            #if the monitor scale is set to 0, the integrator when the pid is turned on instantly goes to 0. 
            #Just toggling is sufficient. 
            yield self.sleep(0.25)
            #Turn off PID
            yield self.hf.set_pid_on(self.PID_Index, False)
            #none of this output any voltage. This is good in case instructions were ignored and the attocubes were left plugged in. 

            #turn the multiplier back to 1 for future use. 
            yield self.hf.set_aux_output_monitorscale(self.generalSettings['pid_z_output'], 1)
            #set output back to manual control 
            yield self.hf.set_aux_output_signal(self.generalSettings['pid_z_output'], -1)
        except Exception as inst:
            print inst
        
        
    @inlineCallbacks
    def setHF2LI_PID_Settings(self, c = None):
        try:
            #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in (initialized at start)

            #Set PID parameters
            yield self.setPIDParameters()
            #Sets the output signal type to be an auxiliary output offset
            yield self.hf.set_pid_output_signal(self.PID_Index, 3)
            #Sets the correct channel of the aux output
            yield self.hf.set_pid_output_channel(self.PID_Index, self.PIDApproachSettings['atto_z_output'])

            #Sets the PID input signal to be the oscillator frequency
            yield self.hf.set_pid_input_signal(self.PID_Index, 10)
            #Sets the oscillator frequency to be the same as the one for which the PLL is running
            yield self.hf.set_pid_input_channel(self.PID_Index, self.measurementSettings['pll_output'])

            #Set the setpoint, noting whether it should be plus or minus as specified in the GUI
            if self.radioButton_plus.isChecked():
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] + self.freqThreshold)
            else:
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] - self.freqThreshold)

        except Exception as inst:
            print "Set PID settings error" + str(inst)
            
    @inlineCallbacks
    def setPIDOutputRange(self, max):
        #Set the output range to be 0 to max V.
        yield self.hf.set_pid_output_center(self.PID_Index, float(max)/2)
        yield self.hf.set_pid_output_range(self.PID_Index, float(max)/2)
        
    @inlineCallbacks
    def setPIDParameters(self):
        print 'Yupperino'
        #Sets PID parameters, noting that i cannot ever be 0, because otherwise this will lead to 
        #voltage jumps as it resets the integrator value. 
        yield self.hf.set_pid_p(self.PID_Index, self.PIDApproachSettings['p'])
        yield self.hf.set_pid_i(self.PID_Index, self.PIDApproachSettings['i'])
        yield self.hf.set_pid_d(self.PID_Index, self.PIDApproachSettings['d'])
            
    @inlineCallbacks
    def setHF2LI_PID_Integrator(self, val = 0, speed = 1):
        '''
        Function takes the provided speed (in V/s) to set the integrator value from its current value to the desired value. 
        note: this method can only reduce the voltage. This is done to avoid approaching the sample with PID off. Whenever
        getting closer, the PID should always be active. 
        '''
        #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in (initialized at start)
        try:
            curr_val = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])

            if 0 <= val and val <= curr_val:
                #Make sure the pid is off when setting up the integrator changing
                pid_on = yield self.hf.get_pid_on(self.PID_Index)
                if pid_on:
                    yield self.hf.set_pid_on(self.PID_Index, False)

                #First turn off proportional and derivative terms, and intergral term to 1 to simplify calculation
                yield self.hf.set_pid_p(self.PID_Index, 0)
                yield self.hf.set_pid_i(self.PID_Index, 1)
                yield self.hf.set_pid_d(self.PID_Index, 0)

                #Sets the PID input signal to be the auxliary output 
                yield self.hf.set_pid_input_signal(self.PID_Index, 5)
                #Sets channel to be aux output 4, which should never be in use elsewhere (as warned on the GUI)
                yield self.hf.set_pid_input_channel(self.PID_Index, 4)

                #the following two should already be appropriately set, but can't hurt to set them to the proper values again. 
                #Sets the output signal type to be an auxiliary output offset
                yield self.hf.set_pid_output_signal(self.PID_Index, 3)
                #Sets the correct channel of the aux output
                yield self.hf.set_pid_output_channel(self.PID_Index, self.PIDApproachSettings['atto_z_output'])

                yield self.hf.set_pid_setpoint(self.PID_Index, -speed)
                #Sets the setpoint to be -10V. The input signal (aux output 4), is always left as 0 Volt output. 
                #This means that the rate at which the voltage changes is this setpoint (-'speed') times the integrator
                # value (1 /s). So, this changes the voltage at a rate of 'speed' V/s.

                expected_time = (curr_val - val)/speed

                #Turn on PID
                yield self.hf.set_pid_on(self.PID_Index, True)
                if expected_time - 0.05 > 0:
                    yield self.sleep(expected_time - 0.05)
                else:
                    yield self.sleep(expected_time)
                yield self.hf.set_pid_on(self.PID_Index, False)

                #Set the appropriate PID settings again
                yield self.setHF2LI_PID_Settings()

        except Exception as inst:
            print "Set integrator error" + str(inst)

    @inlineCallbacks
    def withdrawSpecifiedDistance(self, c = None):
        try:          
            #Eventually add a way to make sure that the DAC / JPEs are no longer moving anything before sending the retract command
            self.approaching = False
            self.updateConstantHeightStatus.emit(False)
            self.updateFeedbackStatus.emit(False)
            
            self.push_Withdraw.setEnabled(False)
            self.push_PIDApproach.setEnabled(False)
            self.push_ApproachForFeedback.setEnabled(False)
            self.push_ApproachForConstant.setEnabled(False)
            
            #Turn PID off
            yield self.hf.set_pid_on(self.PID_Index, False)
            z_voltage = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])
            
            self.label_approachStatus.setText('Withdrawing')
            self.label_feedbackStatus.setText('Withdrawing')
            self.label_constHeightStatus.setText('Withdrawing')
            
            #eventually replace with a proper condition identifying that the DAC ADC is connected instead of connected 
            #via aux out of the hf2li pid. Also, know when 10 divider is being used so appropriate multiplier is set. 
            
            if z_voltage >= 0.001: 
                #Find desired end voltage
                end_voltage = z_voltage - self.withdrawDistance * self.z_volts_to_meters

                if end_voltage < 0:
                    end_voltage = 0

                #Find desired retract speed in volts per second
                retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
                yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)
            
            elif self.Atto_Z_Voltage > 0:
                start_voltage = self.Atto_Z_Voltage
                end_voltage = self.Atto_Z_Voltage - self.withdrawDistance * self.z_volts_to_meters
                
                #eventually send message saying can't withdraw distance without coarse movement
                if end_voltage < 0:
                    end_voltage = 0
                #hard coded to be the first output, output 0. Generalize later
                print self.feedbackApproachSettings['atto_retract_points']
                print self.feedbackApproachSettings['atto_retract_points_delay']
                yield self.dac.ramp1(0, float(start_voltage), float(end_voltage), int(self.feedbackApproachSettings['atto_retract_points']), int(1e6*self.feedbackApproachSettings['atto_retract_points_delay']))
                self.Atto_Z_Voltage = end_voltage
                
            self.push_Withdraw.setEnabled(True)
            self.push_PIDApproach.setEnabled(True)
            self.push_ApproachForFeedback.setEnabled(True)
            self.push_ApproachForConstant.setEnabled(True)
            
            self.label_approachStatus.setText('Idle')
            self.label_feedbackStatus.setText('Idle')
            self.label_constHeightStatus.setText('Idle')
            
        except Exception as inst:
            print inst
        
    @inlineCallbacks
    def returnToHomePosition(self, c = None):
        try:
            #Stop you from being able to reapproach while the 
            #PID is taking you home
            pidapproach_enabled = False
            if self.push_PIDApproach.isEnabled():
                pidapproach_enabled = True
                self.push_PIDApproach.setEnabled(False)
            '''
            stepapproach_enabled = False
            if self.push_Approach.isEnabled():
                stepapproach_enabled = True
                self.push_Approach.setEnabled(False)
            '''
            #note retract speed is divided by 10 when in the divide by 10 mode
            #This retracts the attocubes voltage contribution from the HF2LI
            retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
            yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)
            
            length = len(self.JPE_Steps)
            for i in range (0,length):
                JPE_Step_Info = self.JPE_Steps[length -1 -i]
                #Go through the steps in reverse direction
                yield self.cpsc.move_z(JPE_Step_Info[0], JPE_Step_Info[1], JPE_Step_Info[2], JPE_Step_Info[3], -1.0*JPE_Step_Info[4],30)
                del self.JPE_Steps[length -1 -i]
                self.updateCoarseSteps()
            self.JPE_Steps = []

            if pidapproach_enabled:
                self.push_PIDApproach.setEnabled(True)
            '''
            if stepapproach_enabled:
                self.push_Approach.setEnabled(True)
            '''
        except Exception as inst:
            print "Return home error" + str(inst)

    @inlineCallbacks
    def startFeedbackApproachSequence(self, c = None):
        msgBox = QtGui.QMessageBox(self)
        msgBox.setIcon(QtGui.QMessageBox.Information)
        msgBox.setWindowTitle('MAKE SURE IN DIVIDE BY 10 MODE')
        msgBox.setText("\r\n MAKE SURE HF2LI OUTPUT IS BEING DIVIDED BY 10, OTHERWISE CATASTROPHE.")
        msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
        msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
        if msgBox.exec_():
            #Make sure the PID is off
            pid_on = yield self.hf.get_pid_on(self.PID_Index)
            if pid_on:
                yield self.hf.set_pid_on(self.PID_Index, False)
                
            #Set range from 0 to 10 V. This voltage should be divided by 10, at room temperature
            #This corresponds to ~8 microns
            yield self.setPIDOutputRange(10)
            
            #Initializes all the PID settings. Note: for now this uses the same settings as
            #The PID approach
            yield self.setHF2LI_PID_Settings()
            
            #Toggle the sum board to be 10 to 1 
            yield self.dcbox.set_voltage(self.PIDApproachSettings['sumboard_toggle']-1, 2.5)
            
            #start PID approach sequence
            self.approaching = True
            yield self.hf.set_pid_on(self.PID_Index, True)
            self.label_feedbackStatus.setText('Approaching with Zurich')

            #Lets add conditions to know when we're done approaching with the PID
            while self.approaching:
                z_voltage = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])
                #if we've maxed out the PID voltage, we're done approaching with the PID
                if z_voltage >= 10:
                    break
                
                #Find the number of data points that are above the threshhold
                points_above_freq_thresh = 0
                for deltaf in self.deltafData:
                    points_above_freq_thresh = points_above_freq_thresh + (deltaf > self.freqThreshold)
                #If more than 10 of the recent points are above the frequency threshhold, then probably
                #in contact and can break from approaching with the PID
                if points_above_freq_thresh > 10:
                    break
                    
            #Once PID maxes out, or we're in contact with the surface, step forward with the DAC adc
            #until we're in the middle of the Zurich output range, so that we can maintain feedback 
            #over a range of z voltages
            self.label_feedbackStatus.setText('Approaching with DAC')
            try:
                while self.approaching:
                    PID_output = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])
                    #If we're midrange of the Zurich PID output, then we're in contact with good range
                    #8 could be changed to 5 to really be in the middle eventually
                    if PID_output < 8:
                        print 'In feedback biotch'
                        self.label_feedbackStatus.setText('In Feedback')
                        self.updateFeedbackStatus.emit(True)
                        break
                        
                    #Atto_Z_Voltage corresponds to the DAC ADC output voltage. HF2LI PID voltage is 
                    #always added in on top of this voltage. 
                    start_voltage = self.Atto_Z_Voltage
                    end_voltage = self.Atto_Z_Voltage + self.feedbackApproachSettings['atto_z_step_size'] * self.z_volts_to_meters
                    
                    #Check to see if we've reached the maximum z voltage. If so, break loop. 
                    if (end_voltage + 1) > self.z_volts_max:
                        #Withdraw sequence
                        self.approaching = False
                        msgBox = QtGui.QMessageBox(self)
                        msgBox.setIcon(QtGui.QMessageBox.Information)
                        msgBox.setWindowTitle('Feedback Approach Failure')
                        msgBox.setText("\r\n Failed to reach the surface without coarse stepping. Make sure that you're already close to the surface" + 
                                       " before attempting to engage in feedback scanning mode.")
                        msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
                        msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                        
                        break
                    #Take a step forward as specified by the stepwise approach advanced settings
                    #yield self.dac.ramp1(self.feedbackApproachSettings['atto_z_output'],start_voltage,end_voltage,self.feedbackApproachSettings['atto_z_points'], self.feedbackApproachSettings['atto_z_points_delay'] * 1e6)
                    #For now hard coded to be output 0
                    yield self.dac.ramp1(self.feedbackApproachSettings['atto_z_output']-1,float(start_voltage),float(end_voltage),int(self.feedbackApproachSettings['atto_z_step_points']), int(self.feedbackApproachSettings['atto_z_step_points_delay'] * 1e6))
                    #check to see if output voltage of the PID has dropped to below 8V 

                    self.Atto_Z_Voltage = end_voltage
                        
                self.approaching = False
            except Exception as inst:
                print inst
            
            #Add checks that controllers are running and working properly
            
    @inlineCallbacks
    def startPIDConstantHeightApproachSequence(self, c = None):
        #If the DAC voltage is not 0, don't approach with constant height
        #Probably no longer necessary (well, only necessary if we have non-zero voltage
        #and are toggled to the +10V thing
        if self.Atto_Z_Voltage != 0:
            msgBox = QtGui.QMessageBox(self)
            msgBox.setIcon(QtGui.QMessageBox.Information)
            msgBox.setWindowTitle('Make sure fully retracted')
            msgBox.setText("\r\n Make sure DAC ADC is outputting 0 volts (equivalently, start fully retracted)")
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
            msgBox.exec_()
        else: 
            msgBox = QtGui.QMessageBox(self)
            msgBox.setIcon(QtGui.QMessageBox.Information)
            msgBox.setWindowTitle('Make sure fully retracted')
            msgBox.setText("\r\n Make sure switch is set to be 1 to 1 voltage.")
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
            if msgBox.exec_():
                self.approaching = True
                self.label_constHeightStatus.setText('Approaching with Zurich')
                #Initializes all the PID settings
                yield self.setHF2LI_PID_Settings()
                
                #Set the output range to be 0 to the maximum voltage. This is 3V at room temp.
                yield self.setPIDOutputRange(self.z_volts_max)
                
                #Toggle the sum board to be 1 to 1 
                yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 0)
                
                #Turn on PID to start approaching
                yield self.hf.set_pid_on(self.PID_Index, True)

                while self.approaching:
                    #Read the voltage being output by the PID
                    z_voltage = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])
                    
                    #Find the number of data points that are above the threshhold
                    #TODO: figure out how to do this properly so it doesn't trigger during JPE steps. 
                    points_above_freq_thresh = 0
                    for deltaf in self.deltafData:
                        points_above_freq_thresh = points_above_freq_thresh + (deltaf > self.freqThreshold)

                    #If the voltage being output is equal to (or somehow larger than) the maximum voltage,
                    #we have reached the end of the range
                    if z_voltage >= (self.z_volts_max - 0.001) and self.approaching:
                        #Turn off the PID
                        yield self.hf.set_pid_on(self.PID_Index, False)
                        
                        #Withdraw attocubes completely 
                        self.label_constHeightStatus.setText('Withdrawing')
                        retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
                        yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)
                        
                        if self.approaching:
                            self.label_constHeightStatus.setText('Stepping with JPEs')
                            #Step JPE by specified amount in z direction
                            yield self.cpsc.move_z(int(self.generalSettings['jpe_module_address']), int(self.generalSettings['jpe_temperature']), int(self.generalSettings['jpe_freq']), int(self.generalSettings['jpe_approach_size']), -1.0*self.generalSettings['jpe_steps'],30)
                            self.JPE_Steps.append([int(self.generalSettings['jpe_module_address']), int(self.generalSettings['jpe_temperature']), int(self.generalSettings['jpe_freq']), int(self.generalSettings['jpe_approach_size']), -1.0*self.generalSettings['jpe_steps']])
                            try:
                                self.updateCoarseSteps()
                            except Exception as inst:
                                print inst
                            
                        if self.approaching:
                            #Turn back on
                            yield self.hf.set_pid_on(self.PID_Index, True)
                            self.label_constHeightStatus.setText('Approaching with Zurich')

                    #If we see that more than 10 points were above the frequency threshhold, then we probably
                    #have found the surface
                    elif points_above_freq_thresh > 10 and self.approaching:
                        self.label_constHeightStatus.setText('Surface Detected')
                        #Turn off the PID and back off by appropriate amount
                        yield self.hf.set_pid_on(self.PID_Index, False)
                        end_voltage = z_voltage - self.constantHeight * self.z_volts_to_meters
                        #Find desired retract speed in volts per second
                        retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
                        yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)
                        
                        #Set range such that maximally extended is at the proper distance from the surface. 
                        yield self.setPIDOutputRange(end_voltage)

                        #Turn PID back on so that if there's drift or the sample is taller than expected, 
                        #the PID will retract the tip
                        yield self.hf.set_pid_on(self.PID_Index, True)

                        #Emit that we can now scan in constant height mode
                        self.updateConstantHeightStatus.emit(True)
                        self.label_constHeightStatus.setText('Constant Height')
                        self.approaching = False
                        
                        #TODO:
                        #Start a monitor of whether or not still in constant height (ie, if no longer at 
                        #max voltage output, then probably not at constant height). Maybe give error when
                        #Hit surface
            
                yield self.hf.set_pid_on(self.PID_Index, False)
                self.label_approachStatus.setText('Idle')
                        
                        
    @inlineCallbacks
    def startStepConstantHeightApproachSequence(self, c = None):
        pass
    
    
    def setWithdrawDistance(self):
        val = readNum(str(self.lineEdit_Withdraw.text()))
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > self.generalSettings['total_retract_dist']:
                val = self.generalSettings['total_retract_dist']
            self.withdrawDistance = val
        self.lineEdit_Withdraw.setText(formatNum(self.withdrawDistance))

    @inlineCallbacks
    def monitorZVoltage(self):
        while self.monitorZ:
            try:
                z_voltage = yield self.hf.get_aux_input_value(1)
                self.progressBar.setValue(int(1000*(z_voltage/self.z_volts_max)))
                self.lineEdit_FineZ.setText(formatNum(z_voltage / self.z_volts_to_meters, 3))
                yield self.sleep(0.1)
            except Exception as inst:
                print 'monitor error: ' + str(inst)
                yield self.sleep(0.1)


#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""  
    
    def lockInterface(self):
        self.push_Home.setEnabled(False)
        self.push_Withdraw.setEnabled(False)
        self.push_GenSettings.setEnabled(False)
        
        self.push_StartControllers.setEnabled(False)
        self.push_MeasurementSettings.setEnabled(False)
        
        self.push_Abort.setEnabled(False)
        self.push_ApproachForFeedback.setEnabled(False)
        self.push_PIDApproachForConstant.setEnabled(False)
        
        self.push_StepApproachForConstant.setEnabled(False)
        
        self.push_addFreq.setEnabled(False)
        self.push_subFreq.setEnabled(False)
        self.push_addFeedback.setEnabled(False)
        self.push_subFeedback.setEnabled(False)
        self.push_addFeedbackAC.setEnabled(False)
        self.push_subFeedbackAC.setEnabled(False)
        
        self.lineEdit_Withdraw.setDisabled(True)

        self.lineEdit_FineZ.setDisabled(True)
        self.lineEdit_CoarseZ.setDisabled(True)
        self.lineEdit_PID_Const_Height.setDisabled(True)
        self.lineEdit_PID_Step_Size.setDisabled(True)
        self.lineEdit_PID_Step_Speed.setDisabled(True)
        self.lineEdit_Step_Const_Height.setDisabled(True)
        self.lineEdit_Step_Step_Size.setDisabled(True)
        self.lineEdit_Step_Step_Speed.setDisabled(True)
        self.lineEdit_P.setDisabled(True)
        self.lineEdit_I.setDisabled(True)
        self.lineEdit_D.setDisabled(True)

        self.lockFreq()
        self.lockFdbkDC()
        self.lockFdbkAC()

    def lockFreq(self):
        self.lineEdit_freqSet.setDisabled(True)
        self.freqSlider.setEnabled(False)
        self.radioButton_plus.setEnabled(False)
        self.radioButton_minus.setEnabled(False)
        
    def lockFdbkDC(self):
        self.feedbackSlider.setEnabled(False)
        self.lineEdit_feedbackSet.setDisabled(True)
        
    def lockFdbkAC(self):
        self.feedbackACSlider.setEnabled(False)
        self.lineEdit_feedbackACSet.setDisabled(True)
        
    def unlockInterface(self):
        self.push_Home.setEnabled(True)
        self.push_Withdraw.setEnabled(True)
        self.push_GenSettings.setEnabled(True)
        
        self.push_StartControllers.setEnabled(True)
        self.push_MeasurementSettings.setEnabled(True)
        
        self.push_Abort.setEnabled(True)
        self.push_ApproachForFeedback.setEnabled(True)
        self.push_PIDApproachForConstant.setEnabled(True)
        
        self.push_StepApproachForConstant.setEnabled(True)
        
        self.push_addFreq.setEnabled(True)
        self.push_subFreq.setEnabled(True)
        self.push_addFeedback.setEnabled(True)
        self.push_subFeedback.setEnabled(True)
        self.push_addFeedbackAC.setEnabled(True)
        self.push_subFeedbackAC.setEnabled(True)
        
        self.lineEdit_Withdraw.setDisabled(False)

        self.lineEdit_FineZ.setDisabled(False)
        self.lineEdit_CoarseZ.setDisabled(False)
        self.lineEdit_PID_Const_Height.setDisabled(False)
        self.lineEdit_PID_Step_Size.setDisabled(False)
        self.lineEdit_PID_Step_Speed.setDisabled(False)
        self.lineEdit_Step_Const_Height.setDisabled(False)
        self.lineEdit_Step_Step_Size.setDisabled(False)
        self.lineEdit_Step_Step_Speed.setDisabled(False)
        self.lineEdit_P.setDisabled(False)
        self.lineEdit_I.setDisabled(False)
        self.lineEdit_D.setDisabled(False)
        
        self.unlockFdbkAC()
        self.unlockFdbkDC()
        self.unlockFreq()
        
    def unlockFreq(self):
        self.lineEdit_freqSet.setDisabled(False)
        self.freqSlider.setEnabled(True)
        self.radioButton_plus.setEnabled(True)
        self.radioButton_minus.setEnabled(True)
        
    def unlockFdbkDC(self):
        self.feedbackSlider.setEnabled(True)
        self.lineEdit_feedbackSet.setDisabled(False)
        
    def unlockFdbkAC(self):
        self.feedbackACSlider.setEnabled(True)
        self.lineEdit_feedbackACSet.setDisabled(False)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        
class generalApproachSettings(QtGui.QDialog, Ui_generalApproachSettings):
    def __init__(self,reactor, settings, parent = None):
        super(generalApproachSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.pushButton.clicked.connect(self.acceptNewValues)

        self.generalApproachSettings = settings

        self.comboBox_PID_Out.currentIndexChanged.connect(self.setPID_Out)
        self.comboBox_Step_Out.currentIndexChanged.connect(self.setStep_Out)
        self.comboBox_Sumboard_Toggle.currentIndexChanged.connect(self.setSumboard_toggle)
        
        self.lineEdit_Step_Retract_Speed.editingFinished.connect(self.setStep_Retract_Speed)
        self.lineEdit_Step_Retract_Time.editingFinished.connect(self.setStep_Retract_Time)
        
        self.lineEdit_PID_Retract_Speed.editingFinished.connect(self.setPID_Retract_Speed)
        self.lineEdit_PID_Retract_Time.editingFinished.connect(self.setPID_Retract_Time)

        self.lineEdit_JPE_Temp.editingFinished.connect(self.setTemperature)
        self.lineEdit_JPE_Height.editingFinished.connect(self.setJPE_Tip_Height)
        self.comboBox_JPE_Address.currentIndexChanged.connect(self.setJPE_Address)
        
        self.lineEdit_JPE_Steps.editingFinished.connect(self.setJPE_Steps)
        self.lineEdit_JPE_Size.editingFinished.connect(self.setJPE_Size)
        self.lineEdit_JPE_Freq.editingFinished.connect(self.setJPE_Freq)
        
        self.loadValues()
      
    def loadValues(self):
    
        self.comboBox_PID_Out.setCurrentIndex(self.generalApproachSettings['pid_z_output'] - 1)
        self.comboBox_Step_Out.setCurrentIndex(self.generalApproachSettings['step_z_output'] - 1)
        self.comboBox_Sumboard_Toggle.setCurrentIndex(self.generalApproachSettings['sumboard_toggle']-1)
        
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        
        self.lineEdit_JPE_Temp.setText(formatNum(self.generalApproachSettings['jpe_temperature']))
        self.lineEdit_JPE_Height.setText(formatNum(self.generalApproachSettings['jpe_tip_height']))
        self.comboBox_JPE_Address.setCurrentIndex(self.generalApproachSettings['jpe_module_address'] - 1)
        
        self.lineEdit_JPE_Steps.setText(formatNum(self.generalApproachSettings['jpe_steps']))
        self.lineEdit_JPE_Size.setText(formatNum(self.generalApproachSettings['jpe_size']))
        self.lineEdit_JPE_Freq.setText(formatNum(self.generalApproachSettings['jpe_freq']))

    def setPID_Out(self):
        self.generalApproachSettings['pid_z_output'] = self.comboBox_PID_Out.currentIndex() + 1
        
    def setStep_Out(self):
        self.generalApproachSettings['step_z_output'] = self.comboBox_Step_Out.currentIndex() + 1
        
    def setSumboard_toggle(self):
        self.generalApproachSettings['sumboard_toggle'] = self.comboBox_Sumboard_Toggle.currentIndex() + 1
        
    def setStep_Retract_Speed(self):
        val = readNum(str(self.lineEdit_Step_Retract_Speed.text()))
        if isinstance(val,float):
            self.generalApproachSettings['step_retract_speed'] = val
            self.generalApproachSettings['step_retract_time'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['step_retract_speed']
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))
        
    def setStep_Retract_Time(self):
        val = readNum(str(self.lineEdit_Step_Retract_Time.text()))
        if isinstance(val,float):
            self.generalApproachSettings['step_retract_time'] = val
            self.generalApproachSettings['step_retract_speed'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['step_retract_time']
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))

    def setPID_Retract_Speed(self):
        val = readNum(str(self.lineEdit_PID_Retract_Speed.text()))
        if isinstance(val,float):
            self.generalApproachSettings['pid_retract_speed'] = val
            self.generalApproachSettings['pid_retract_time'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['pid_retract_speed']
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))
        
    def setPID_Retract_Time(self):
        val = readNum(str(self.lineEdit_PID_Retract_Time.text()))
        if isinstance(val,float):
            self.generalApproachSettings['pid_retract_time'] = val
            self.generalApproachSettings['pid_retract_speed'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['pid_retract_time']
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))
        
    def setTemperature(self):
        val = readNum(str(self.lineEdit_JPE_Temp.text()))
        if isinstance(val,float):
            self.generalApproachSettings['jpe_temperature'] = val
        self.lineEdit_JPE_Temp.setText(formatNum(self.generalApproachSettings['jpe_temperature']))
    
    def setJPE_Tip_Height(self):
        val = readNum(str(self.lineEdit_JPE_Height.text()))
        if isinstance(val,float):
            self.generalApproachSettings['jpe_tip_height'] = val
        self.lineEdit_JPE_Height.setText(formatNum(self.generalApproachSettings['jpe_tip_height']))
        
    def setJPE_Address(self):
        self.generalApproachSettings['jpe_module_address'] = self.comboBox_JPE_Address.currentIndex() + 1
    
    def setJPE_Steps(self):
        val = readNum(str(self.lineEdit_JPE_Steps.text()))
        if isinstance(val,float):
            self.generalApproachSettings['jpe_steps'] = val
        self.lineEdit_JPE_Steps.setText(formatNum(self.generalApproachSettings['jpe_steps']))
        
    def setJPE_Size(self):
        val = readNum(str(self.lineEdit_JPE_Size.text()))
        if isinstance(val,float):
            self.generalApproachSettings['jpe_size'] = val
        self.lineEdit_JPE_Size.setText(formatNum(self.generalApproachSettings['jpe_size']))
        
    def setJPE_Freq(self):
        val = readNum(str(self.lineEdit_JPE_Freq.text()))
        if isinstance(val,float):
            self.generalApproachSettings['jpe_freq'] = val
        self.lineEdit_JPE_Freq.setText(formatNum(self.generalApproachSettings['jpe_freq'] ))
        
    def acceptNewValues(self):
        self.accept()
        
    def getValues(self):
        return self.generalApproachSettings
        

class MeasurementSettings(QtGui.QDialog, Ui_MeasurementSettings):
    def __init__(self,reactor, measSettings, parent = None, server = None):
        super(MeasurementSettings, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        
        self.pushButton.clicked.connect(self.acceptNewValues)
        
        self.push_AdvisePID.clicked.connect(self.advisePID)
        
        self.measSettings = measSettings

        self.hf = server
        
        self.checkBox_pll.stateChanged.connect(self.setMeasPLL)
        self.checkBox_fdbkDC.stateChanged.connect(self.setMeasFdbkDC)
        self.checkBox_fdbkAC.stateChanged.connect(self.setMeasFdbkAC)
            
        self.lineEdit_TargetBW.editingFinished.connect(self.setPLL_TargetBW)
        self.lineEdit_PLL_Range.editingFinished.connect(self.setPLL_Range)
        self.lineEdit_PLL_TC.editingFinished.connect(self.setPLL_TC)
        self.lineEdit_PLL_FilterBW.editingFinished.connect(self.setPLL_FilterBW)
        self.lineEdit_PLL_P.editingFinished.connect(self.setPLL_P)
        self.lineEdit_PLL_I.editingFinished.connect(self.setPLL_I)
        self.lineEdit_PLL_D.editingFinished.connect(self.setPLL_D)
        
        self.comboBox_PLL_Advise.currentIndexChanged.connect(self.setPLL_AdviseMode)
        self.comboBox_PLL_FilterOrder.currentIndexChanged.connect(self.setPLL_FilterOrder)
        self.comboBox_PLL_Harmonic.currentIndexChanged.connect(self.setPLL_Harmonic)
        self.comboBox_PLL_Input.currentIndexChanged.connect(self.setPLL_Input)

        self.lineEdit_PLL_Amplitude.editingFinished.connect(self.setPLL_Output_Amplitude)
        self.comboBox_PLL_Output.currentIndexChanged.connect(self.setPLL_Output)

        self.comboBox_DC_Input.currentIndexChanged.connect(self.setFdbk_DC_Input)
        self.lineEdit_DC_Setpoint.editingFinished.connect(self.setFdbk_DC_Setpoint)
        self.comboBox_AC_Input.currentIndexChanged.connect(self.setFdbk_AC_Input)
        self.lineEdit_AC_Setpoint.editingFinished.connect(self.setFdbk_AC_Setpoint)
        
        self.loadValues()
        self.createLoadingColors()

    def setupAdditionalUi(self):
        self.comboBox_PLL_Input.view().setMinimumWidth(100)
        
    def loadValues(self):
        self.checkBox_pll.setChecked(self.measSettings['meas_pll'])
        self.checkBox_fdbkDC.setChecked(self.measSettings['meas_fdbk_dc'])
        self.checkBox_fdbkAC.setChecked(self.measSettings['meas_fdbk_ac'])
    
        self.lineEdit_TargetBW.setText(formatNum(self.measSettings['pll_targetBW']))
        self.comboBox_PLL_Advise.setCurrentIndex(self.measSettings['pll_advisemode'])
        self.comboBox_PLL_Input.setCurrentIndex(self.measSettings['pll_input'] - 1)
        
        if self.measSettings['pll_centerfreq'] is not None:
            self.lineEdit_PLL_CenterFreq.setText(formatNum(self.measSettings['pll_centerfreq']))
        else:
            self.lineEdit_PLL_CenterFreq.setText('None')
        if self.measSettings['pll_phase_setpoint'] is not None:
            self.lineEdit_PLL_phaseSetPoint.setText(formatNum(self.measSettings['pll_phase_setpoint']))
        else:
            self.lineEdit_PLL_phaseSetPoint.setText('None')
        self.lineEdit_PLL_Range.setText(formatNum(self.measSettings['pll_range']))
        
        self.comboBox_PLL_Harmonic.setCurrentIndex(self.measSettings['pll_harmonic'] -1)
        self.hf.set_advisor_harmonic(self.measSettings['pll_harmonic'])
        
        self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))
        self.hf.set_advisor_tc(self.measSettings['pll_tc'])
        
        self.comboBox_PLL_FilterOrder.setCurrentIndex(self.measSettings['pll_filterorder'] -1)
        self.hf.set_advisor_filterorder(self.measSettings['pll_filterorder'])
        
        self.lineEdit_PLL_P.setText(formatNum(self.measSettings['pll_p'], 3))
        self.hf.set_advisor_p(self.measSettings['pll_p'])
        self.lineEdit_PLL_I.setText(formatNum(self.measSettings['pll_i'], 3))
        self.hf.set_advisor_i(self.measSettings['pll_i'])
        self.lineEdit_PLL_D.setText(formatNum(self.measSettings['pll_d'], 3))
        self.hf.set_advisor_d(self.measSettings['pll_d'])
        self.lineEdit_PLL_SimBW.setText(formatNum(self.measSettings['pll_simBW']))
        self.lineEdit_PLL_PM.setText(formatNum(self.measSettings['pll_pm']))
        self.lineEdit_PLL_Rate.setText(formatNum(self.measSettings['pll_rate']))

        self.lineEdit_PLL_Amplitude.setText(formatNum(self.measSettings['pll_output_amp']))
        self.comboBox_PLL_Output.setCurrentIndex(self.measSettings['pll_output'] - 1)
        
        self.comboBox_DC_Input.setCurrentIndex(self.measSettings['fdbk_dc_input']-1)
        self.lineEdit_DC_Setpoint.setText(formatNum(self.measSettings['fdbk_dc_setpoint']))
        self.comboBox_AC_Input.setCurrentIndex(self.measSettings['fdbk_ac_input']-1)
        self.lineEdit_AC_Setpoint.setText(formatNum(self.measSettings['fdbk_ac_setpoint']))
        
    #Creates a list of stylesheets with a gradient of grey to black. This
    #will be used when the advisePID button is pressed to indicate that
    #it is processing. 
    def createLoadingColors(self):
        base_sheet = '''#push_AdvisePID{
                        background-color: rgb(230,230,230);
                        border: 2px solid rgb(210,210,210);
                        border-radius: 2px;
                        }'''
        self.sheets = []
        for i in range(0,40):
            new_border = 210 - i*5
            new_background = 230 - i*5
            new_sheet = base_sheet.replace('210',str(new_border))
            new_sheet = new_sheet.replace('230',str(new_background))
            self.sheets.append(new_sheet)
        for i in range(0,40):
            new_border = 20 + i*5
            new_background = 40 + i*5
            new_sheet = base_sheet.replace('210',str(new_border))
            new_sheet = new_sheet.replace('230',str(new_background))
            self.sheets.append(new_sheet)
        
    def setMeasPLL(self):
        if self.measSettings['pll_centerfreq'] is not None:
            self.measSettings['meas_pll'] = self.checkBox_pll.isChecked()
        else:
            self.checkBox_pll.setChecked(False)
            self.checkBox_pll.setCheckState(False)
        
    def setMeasFdbkDC(self):
        self.measSettings['meas_fdbk_dc'] = self.checkBox_fdbkDC.isChecked()
        
    def setMeasFdbkAC(self):
        self.measSettings['meas_fdbk_ac'] = self.checkBox_fdbkAC.isChecked()
        
    def setPLL_TargetBW(self):
        new_target = str(self.lineEdit_TargetBW.text())
        val = readNum(new_target)
        if isinstance(val,float):
            self.measSettings['pll_targetBW'] = val
        self.lineEdit_TargetBW.setText(formatNum(self.measSettings['pll_targetBW']))
      
    def setPLL_Range(self):
        new_range = str(self.lineEdit_PLL_Range.text())
        val = readNum(new_range)
        if isinstance(val,float):
            self.measSettings['pll_range'] = val
        self.lineEdit_PLL_Range.setText(formatNum(self.measSettings['pll_range']))

    @inlineCallbacks
    def setPLL_TC(self, c = None):
        new_TC = str(self.lineEdit_PLL_TC.text())
        val = readNum(new_TC)
        if isinstance(val,float):
            self.measSettings['pll_tc'] = val
            self.measSettings['pll_filterBW'] = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_tc'])
            yield self.hf.set_advisor_tc(self.PLL_TC)
            yield self.updateSimulation()
        self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))
    
    @inlineCallbacks
    def setPLL_FilterBW(self, c = None):
        new_filterBW = str(self.lineEdit_PLL_FilterBW.text())
        val = readNum(new_filterBW)
        if isinstance(val,float):
            self.measSettings['pll_filterBW']  = val
            self.measSettings['pll_tc']  = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_filterBW'])
            yield self.hf.set_advisor_tc(self.measSettings['pll_tc'])
            yield self.updateSimulation()
        self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))
    
    @inlineCallbacks
    def setPLL_P(self, c = None):
        new_P = str(self.lineEdit_PLL_P.text())
        val = readNum(new_P)
        if isinstance(val,float):
            self.measSettings['pll_p'] = val
            yield self.hf.set_advisor_p(self.measSettings['pll_p'])
            yield self.updateSimulation()
        self.lineEdit_PLL_P.setText(formatNum(self.measSettings['pll_p'], 3))
        
    @inlineCallbacks
    def setPLL_I(self, c = None):
        new_I = str(self.lineEdit_PLL_I.text())
        val = readNum(new_I)
        if isinstance(val,float):
            self.measSettings['pll_i'] = val
            yield self.hf.set_advisor_i(self.measSettings['pll_i'])
            yield self.updateSimulation()
        self.lineEdit_PLL_I.setText(formatNum(self.measSettings['pll_i'], 3))
        
    @inlineCallbacks
    def setPLL_D(self, c = None):
        new_D = str(self.lineEdit_PLL_D.text())
        val = readNum(new_D)
        if isinstance(val,float):
            self.measSettings['pll_d'] = val
            yield self.hf.set_advisor_d(self.measSettings['pll_d'])
            yield self.updateSimulation()
        self.lineEdit_PLL_D.setText(formatNum(self.measSettings['pll_d'], 3))
        
    def setPLL_Input(self):
        self.measSettings['pll_input'] = self.comboBox_PLL_Input.currentIndex() + 1

    def setPLL_Output(self):
        self.measSettings['pll_output'] = self.comboBox_PLL_Output.currentIndex() + 1
        
    def setPLL_Output_Amplitude(self):
        val = readNum(str(self.lineEdit_PLL_Amplitude.text()))
        if isinstance(val,float):
            self.measSettings['pll_output_amp'] = val
        self.lineEdit_PLL_Amplitude.setText(formatNum(self.measSettings['pll_output_amp']))

    @inlineCallbacks
    def setPLL_Harmonic(self, c = None):
        self.measSettings['pll_harmonic'] = self.comboBox_PLL_Harmonic.currentIndex() + 1
        yield self.hf.set_advisor_harmonic(self.measSettings['pll_harmonic'])
        yield self.updateSimulation()
        
    @inlineCallbacks
    def setPLL_FilterOrder(self, c = None):
        self.measSettings['pll_filterorder'] = self.comboBox_PLL_FilterOrder.currentIndex() + 1
        self.measSettings['pll_filterBW'] = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_tc'])
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))
        yield self.hf.set_advisor_filterorder(self.measSettings['pll_filterorder'])
        yield self.updateSimulation()
        
    def setPLL_AdviseMode(self):
        self.measSettings['pll_adivsemode'] = self.comboBox_PLL_Advise.currentIndex()

    @inlineCallbacks
    def updateSimulation(self):
        try:
            #Waiting for one second seems to work fine for auto calculation to be complete
            yield self.sleep(1)

            pm = yield self.hf.get_advisor_pm()
            bw = yield self.hf.get_advisor_simbw()
            self.measSettings['pll_pm'] = pm
            self.measSettings['pll_simBW'] = bw
            self.lineEdit_PLL_PM.setText(formatNum(pm))
            self.lineEdit_PLL_SimBW.setText(formatNum(bw))

            self.updateStability()
        except Exception as inst:
            print inst
         
    @inlineCallbacks
    def updateStability(self, c = None):
        stable = yield self.hf.get_advisor_stable()
        if stable:
            style = """ #push_stability{
                    background: rgb(0, 161, 0);
                    border-radius: 8px;
                    }
                    """
        else:
            style = """ #push_stability{
                    background: rgb(161, 0, 0);
                    border-radius: 8px;
                    }
                    """
        self.push_stability.setStyleSheet(style)

    def acceptNewValues(self):
        self.accept()
        
    def advisePID(self):
        try:
            self.PID_advice = False
            self.computePIDParameters()
            self.displayCalculatingGraphics()
        except Exception as inst:
            print inst
        
    @inlineCallbacks
    def computePIDParameters(self, c = None):
        try:
            self.PID_advice = yield self.hf.advise_pll_pid(self.measSettings['pll_output'], self.measSettings['pll_targetBW'],self.measSettings['pll_advisemode'])
            self.measSettings['pll_p'] = yield self.hf.get_advisor_p()
            self.measSettings['pll_i'] = yield self.hf.get_advisor_i()
            self.measSettings['pll_d'] = yield self.hf.get_advisor_d()
            self.measSettings['pll_simBW'] = yield self.hf.get_advisor_simbw()
            self.measSettings['pll_rate']  = yield self.hf.get_advisor_rate()
            self.measSettings['pll_pm'] = yield self.hf.get_advisor_pm()
            self.measSettings['pll_tc'] = yield self.hf.get_advisor_tc()
            self.measSettings['pll_filterBW'] = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_tc'])

            self.lineEdit_PLL_P.setText(formatNum(self.measSettings['pll_p'], 3))
            self.lineEdit_PLL_I.setText(formatNum(self.measSettings['pll_i'], 3))
            self.lineEdit_PLL_D.setText(formatNum(self.measSettings['pll_d'], 3))
            self.lineEdit_PLL_PM.setText(formatNum(self.measSettings['pll_pm']))
            self.lineEdit_PLL_SimBW.setText(formatNum(self.measSettings['pll_simBW']))
            self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))
            self.lineEdit_PLL_Rate.setText(formatNum(self.measSettings['pll_rate'], 3))
            self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))

            self.updateStability()
        except Exception as inst:
            print inst
        
    @inlineCallbacks
    def displayCalculatingGraphics(self, c = None):
        try:
            i = 0
            while not self.PID_advice:
                self.push_AdvisePID.setStyleSheet(self.sheets[i])
                yield self.sleep(0.025)
                i = (i+1)%80
            self.push_AdvisePID.setStyleSheet(self.sheets[0])
        except Exception as inst:
            print inst
            
    def setFdbk_DC_Input(self):
        self.measSettings['fdbk_dc_input'] = self.comboBox_DC_Input.currentIndex() + 1
    
    def setFdbk_DC_Setpoint(self):
        val = readNum(str(self.lineEdit_DC_Setpoint.text()))
        if isinstance(val,float):
            self.measSettings['fdbk_dc_setpoint'] = val
        self.lineEdit_DC_Setpoint.setText(formatNum(self.measSettings['fdbk_dc_setpoint']))

    def setFdbk_AC_Input(self):
        self.measSettings['fdbk_ac_input'] = self.comboBox_AC_Input.currentIndex() + 1
    
    def setFdbk_AC_Setpoint(self):
        val = readNum(str(self.lineEdit_AC_Setpoint.text()))
        if isinstance(val,float):
            self.measSettings['fdbk_ac_setpoint'] = val
        self.lineEdit_AC_Setpoint.setText(formatNum(self.measSettings['fdbk_ac_setpoint']))

    def getValues(self):
        return self.measSettings
        
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
class MySlider(QtGui.QSlider):
    logValueChanged = QtCore.pyqtSignal(float)
    #Shitty programming. Only looks good for horizontal sliders with length 400 and thickness 70. 
    def __init__(self, parent=None): 
        self.tickPos = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.numPos = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        super(MySlider, self).__init__(QtCore.Qt.Horizontal, parent)
 
        self.valueChanged.connect(self.emitLogValue)
        self.valueChangedManually = False
        
    def paintEvent(self, event):
        """Paint log scale ticks"""
        super(MySlider, self).paintEvent(event)
        qp = QtGui.QPainter(self)
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setColor(QtGui.QColor(168,168,168))
 
        qp.setPen(pen)
        font = QtGui.QFont('Times', 10)
        font_y_offset = font.pointSize()/2
        qp.setFont(font)
        size = self.size()
        contents = self.contentsRect()
        width = contents.width()
        height = contents.height()
        y = contents.y()
        max = np.log10(self.tickPos[-1])
        min = np.log10(self.tickPos[0])
        lower_padding = 8
        upper_padding = 16
        for val in self.tickPos:
            log_val = np.log10(val)
            x_val = round( (log_val-min)* (width-upper_padding) / (max-min)) + lower_padding
            if val in self.numPos:
                pen.setColor(QtGui.QColor(95,107,166))
                pen.setWidth(2)
                qp.setPen(pen)
                qp.drawLine(x_val , y + 45,  x_val, y+50)
                pen.setColor(QtGui.QColor(168,168,168))
                pen.setWidth(1)
                qp.setPen(pen)
                #text = '{0:2}'.format(val)
                text = formatNum(val)
                x_offset = float(len(text)*font.pointSize()/(3))
                qp.drawText(x_val - x_offset, y + 58 + font_y_offset,text)
            else:
                qp.drawLine(x_val , y + 45,  x_val, y+50)
    
    def setTickPos(self, ticks):
        self.tickPos = ticks
        
    def setNumPos(self, nums):
        self.numPos = nums
        
    def emitLogValue(self, val):
        if not self.valueChangedManually:
            min = float(self.minimum())
            max = float(self.maximum())
            val = self.tickPos[0]*10**(np.log10(self.tickPos[-1]/self.tickPos[0])*(val-min)/max)
            self.logValueChanged.emit(val)
        else:
            self.valueChangedManually = False
            
    def setPosition(self,val):
        min = float(self.minimum())
        max = float(self.maximum())
        val = min + np.log10(val/self.tickPos[0])*max/np.log10(self.tickPos[-1]/self.tickPos[0])
        self.valueChangedManually = True
        self.setSliderPosition(int(round(val)))

def calculate_FilterBW(PLL_FilterOrder, tc):
    #note, this works to calculate either the bandwidth or the time constant, since
    # BW = const / TC and TC = const / BW. 
    if PLL_FilterOrder == 1:
        BW = 0.1591549431 / tc
    elif PLL_FilterOrder == 2:
        BW = 0.1024312067 / tc
    elif PLL_FilterOrder == 3:
        BW = 0.0811410938 / tc
    elif PLL_FilterOrder == 4:
        BW = 0.0692291283 / tc
    elif PLL_FilterOrder == 5:
        BW = 0.0613724151 / tc
    elif PLL_FilterOrder == 6:
        BW = 0.0556956006 / tc
    elif PLL_FilterOrder == 7:
        BW = 0.0513480105 / tc
    elif PLL_FilterOrder == 8:
        BW = 0.0478809738 / tc
    return BW