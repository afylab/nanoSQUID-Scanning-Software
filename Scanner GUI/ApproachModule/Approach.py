'''
General Notes:

Everywhere with something I realized I wanted done, I wrote a comment starting with
TODO. Search for those for things to do :)

TODO test how the DAC responds to having a voltage prompted while it's ramping or buffer ramping

'''

import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import numpy as np
import time
from collections import deque

path = sys.path[0] + r"\ApproachModule"
ApproachUI, QtBaseClass = uic.loadUiType(path + r"\Approach.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_generalApproachSettings, QtBaseClass = uic.loadUiType(path + r"\generalApproachSettings.ui")
Ui_MeasurementSettings, QtBaseClass = uic.loadUiType(path + r"\MeasurementSettings.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, ApproachUI):
    newPLLData = QtCore.pyqtSignal(float, float)
    newAux2Data = QtCore.pyqtSignal(float)
    newFdbkDCData = QtCore.pyqtSignal(float)
    newFdbkACData = QtCore.pyqtSignal(float)
    newZData = QtCore.pyqtSignal(float)
    updateFeedbackStatus = QtCore.pyqtSignal(bool)
    updateConstantHeightStatus = QtCore.pyqtSignal(bool)
    updateApproachStatus = QtCore.pyqtSignal(bool)

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
        
        self.push_setZExtension.clicked.connect(self.setZExtension)

        self.lineEdit_freqSet.editingFinished.connect(self.setFreqThresh)

        self.lineEdit_P.editingFinished.connect(self.set_p)
        self.lineEdit_I.editingFinished.connect(self.set_i)
        self.lineEdit_D.editingFinished.connect(self.set_d)
        
        self.lineEdit_PID_Const_Height.editingFinished.connect(self.set_pid_const_height)
        self.lineEdit_PID_Step_Size.editingFinished.connect(self.set_pid_step_size)
        self.lineEdit_PID_Step_Speed.editingFinished.connect(self.set_pid_step_speed)
        
        self.lineEdit_Man_Z_Extension.editingFinished.connect(self.set_man_z_extension)

        self.push_Abort.clicked.connect(lambda: self.abortApproachSequence())
        
        self.push_ApproachForFeedback.clicked.connect(self.startFeedbackApproachSequence)
        self.push_PIDApproachForConstant.clicked.connect(self.startPIDConstantHeightApproachSequence)

        self.push_Withdraw.clicked.connect(lambda: self.withdraw(self.withdrawDistance))
        self.lineEdit_Withdraw.editingFinished.connect(self.setWithdrawDistance)

        self.radioButton_plus.toggled.connect(self.setFreqThreshholdSign)

        self.comboBox_ZMultiplier.currentIndexChanged.connect(self.setZMultiplier)
        
        self.checkBox_autoThreshold.stateChanged.connect(self.setAutoThreshold)
        
        self.push_setPLLThresh.clicked.connect(self.setPLLThreshold)
        
        self.push_frustrateFeedback.clicked.connect(self.setFrustratedFeedback)
        
        #Initialize all the labrad connections as not connected
        self.cxn = False
        self.anc = False
        self.dac = False
        self.hf = False
        self.dcbox = False

        self.measuring = False
        self.approaching = False
        self.constantHeight = False
        self.voltageMultiplied = False #Variable to keep track of sum box status ie if the voltage from the Zurich being multiplied down
        self.voltageMultiplier = 0.1   #This is the multiplier value for scanning in feedback
        self.CPStepping = False
        self.DACRamping = False
        self.withdrawing = False 
        self.autoThresholding = False
        self.coarsePositioner = False
        
        #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in
        self.PID_Index = 1

        self.Atto_Z_Voltage = 0.0 #Voltage being sent to Z of attocubes. Not synchronized with the Scan module Atto Z voltage
        self.Temperature = 293    #in kelvin

        #intial withdraw distance
        self.withdrawDistance = 2e-6

        #Height at which the previous approach made contact
        self.contactHeight = 0
        
        #Keep track of motion from the attocube positioners. 
        #Exists for historical reasons, probably best to just use the attocube coarse position module
        self.coarsePositionerExtension = 0

        self.deltaf_track_length = 100
        self.deltafData = deque([-200]*self.deltaf_track_length)
        
        self.z_track_length = 20
        self.zData = deque([-50e-9]*self.deltaf_track_length)
        self.zTime = np.linspace(self.z_track_length, 1, self.z_track_length)
        
        '''
        Below is the initialization of all the default measurement settings. Eventually organize into a dictionary
        '''
        
        self.PLL_Locked = 0 #PLL starts not locked

        self.measurementSettings = {
                'meas_pll'            : False,
                'meas_fdbk_dc'        : False,
                'meas_fdbk_ac'        : False,
                'pll_targetBW'        : 100,       #target bandwidth for pid advisor
                'pll_advisemode'      : 2,         #advisor mode. 0 is just proportional term, 1 just integral, 2 is prop + int, and 3 is full PID
                'pll_input'           : 1,         #hf2li input that has the signal for the pll
                'pll_centerfreq'      : None,      #center frequency of the pll loop
                'pll_phase_setpoint'  : None,      #phase setpoint of pll pid loop
                'pll_range'           : 20,        #range around center frequency that the pll is allowed to go
                'pll_harmonic'        : 1,         #harmonic of the input to the pll
                'pll_tc'              : 138.46e-6, #pll time constant
                'pll_filterBW'        : 500.0,     #pll filter bandwidth 
                'pll_filterorder'     : 4,         #pll filter order (how many filters are cascaded)
                'pll_p'               : 1.399,     #pll pid proportional term
                'pll_i'               : 2.932,     #pll pid integral term 
                'pll_d'               : 0,         #pll pid derivative term
                'pll_simBW'           : 115.36,    #current pid term simulated bandwidth 
                'pll_pm'              : 73.83,     #pll pid simulated phase margin (relevant to the stability of loop)   
                'pll_rate'            : 1.842e+6,  #Sampling rate of the PLL. Cannot be changed, despite it being spit out by the pid advisor. Just... is what it is. 
                'pll_output'          : 1,         #hf2li output to be used to completel PLL loop. 
                'pll_output_amp'      : 0.001,      #output amplitude   
                }
        
        '''
        Below is the initialization of all the default general approach settingss
        '''
        self.generalSettings = {
                'step_z_output'              : 1,     #output that goes to Z of attocubes from DAC ADC (1 indexed)
                'pid_z_output'               : 1,     #aux output that goes to Z of attocubes from HF2LI (1 indexed)
                'sumboard_toggle'            : 1,     #Output from the DC Box that toggles the summing amplifier (1 indexed)
                'blink_output'               : 2,     #1 indexed output from the DC box that goes to blinking
                'z_mon_input'                : 1,     # Either 1 (aux in 1) or 2 (aux in 2) on the Zurich
                'step_retract_speed'         : 1e-5,  #speed in m/s when retracting
                'step_retract_time'          : 2.4,   #time required in seconds for full atto retraction
                'pid_retract_speed'          : 1e-5,  #speed in m/s when retracting
                'pid_retract_time'           : 2.4,   #time required in seconds for full atto retraction
                'total_retract_dist'         : 24e-6, #total z distance retracted in meters by the attocube (eventually should update with temperature)
                'auto_retract_dist'          : 2e-6,  #distance retracted in meters when a surface event is triggered in constant height mode  
                'auto_retract_points'          : 3,   #points above frequency threshold before auto retraction is trigged
                'atto_distance'              : 6e-6,
                'atto_delay'                 : 0.1,
        }
        
        '''
        Below is the initialization of all the default PID Approach Settings
        '''
        self.PIDApproachSettings = {
                'p'                    : 0,     #Proportional term of approach PID 
                'i'                    : 1e-7,  #Integral term of approach PID 
                'd'                    : 0,     #Derivative term of approach PID 
                'step_size'            : 10e-9, #Step size for feedback approach in meters
                'step_speed'           : 10e-9, #Step speed for feedback approach in m/s
                'height'               : 5e-6,#Height for constant height scanning
                'man z extension'            : 0, #Step size for manual approach in meters
        }

        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))
        self.lineEdit_PID_Step_Size.setText(formatNum(self.PIDApproachSettings['step_size']))
        self.lineEdit_PID_Step_Speed.setText(formatNum(self.PIDApproachSettings['step_speed']))
        self.lineEdit_PID_Const_Height.setText(formatNum(self.PIDApproachSettings['height']))

        self.lineEdit_Man_Z_Extension.setText(formatNum(self.PIDApproachSettings['man z extension']))

        '''
        Below is the initialization of all the thresholds for surface detection
        '''
        #Initialize values based off of the numbers put in the lineEdit in the ui file
        self.setFreqThresh()

        #self.lockInterface()

    def moveDefault(self):
        self.move(10,170)
        
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.anc = dict['servers']['local']['anc350']

            if dict['devices']['system']['coarse positioner'] == 'Attocube ANC350':
                print 'Using ANC350 for Coarse Position Control'
                
            self.coarsePositioner = dict['devices']['system']['coarse positioner']
                
            #Create another connection for the connection to data vault to prevent 
            #problems of multiple windows trying to write the data vault at the same
            #time
            from labrad.wrappers import connectAsync
            self.cxn_app = yield connectAsync(host = '127.0.0.1', password = 'pass')
            
            self.hf = yield self.cxn_app.hf2li_server
            self.hf.select_device(dict['devices']['approach and TF']['hf2li'])

            self.dac = yield self.cxn_app.dac_adc
            self.dac.select_device(dict['devices']['scan']['dac_adc'])
                
            self.dcbox = yield self.cxn_app.ad5764_dcbox
            self.dcbox.select_device(dict['devices']['approach and TF']['dc_box'])
            
            if dict['devices']['system']['blink device'].startswith('ad5764_dcbox'):
                self.blink_server = yield self.cxn_app.ad5764_dcbox
                self.blink_server.select_device(dict['devices']['system']['blink device'])
            elif dict['devices']['system']['blink device'].startswith('DA'):
                self.blink_server = yield self.cxn_app.dac_adc
                self.blink_server.select_device(dict['devices']['system']['blink device'])
                
            self.generalSettings['step_z_output'] = dict['channels']['scan']['z out']
            self.generalSettings['pid_z_output'] = dict['channels']['approach and TF']['pid z out']
            self.generalSettings['sumboard_toggle'] = dict['channels']['approach and TF']['sum board toggle']
            self.generalSettings['blink_output'] = dict['channels']['approach and TF']['blink channel']
            self.generalSettings['z_mon_input'] = dict['channels']['approach and TF']['z monitor']
                
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            
            self.unlockInterface()
            self.lockFreq()
            self.lockFdbkDC()
            self.lockFdbkAC()
            
            #self.zeroHF2LI_Aux_Out()
            #self.initializePID()
            yield self.loadCurrentState()
            self.monitorZ = True
            self.monitorZVoltage()
        except Exception as inst:
            print inst
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  
    
    @inlineCallbacks
    def loadCurrentState(self):
        #load pid values
        P = yield self.hf.get_pid_p(self.PID_Index)
        I = yield self.hf.get_pid_i(self.PID_Index)
        D = yield self.hf.get_pid_d(self.PID_Index)
        
        #If PID parameters are the Zurich default (ie, the Zurich lock in was power cycled)
        #set to our default values
        #Otherwise use the loaded values
        if P == 1.0 and I == 10.0:
            yield self.setPIDParameters()
        else:
            self.PIDApproachSettings['p'] = P/self.z_volts_to_meters
            self.PIDApproachSettings['i'] = I/self.z_volts_to_meters
            self.PIDApproachSettings['d'] = D/self.z_volts_to_meters
            self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))
            self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))
            self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))
        
        pll_on_1 = yield self.hf.get_pll_on(1)
        pll_on_2 = yield self.hf.get_pll_on(2)
        if pll_on_1 or pll_on_2:
            self.measurementSettings['meas_pll'] = True
            
            if pll_on_1:
                self.measurementSettings['pll_output'] = 1
            else:
                self.measurementSettings['pll_output'] = 2
                
            freq = yield self.hf.get_pll_freqcenter(self.measurementSettings['pll_output'])
            phase = yield self.hf.get_pll_setpoint(self.measurementSettings['pll_output'])
            amp_range = yield self.hf.get_output_range(self.measurementSettings['pll_output'])
            amp_frac = yield self.hf.get_output_amplitude(self.measurementSettings['pll_output'])
            freq_range = yield self.hf.get_pll_freqrange(self.measurementSettings['pll_output'])
            
            print 'Amp range:', amp_range
            print 'Amp frac:', amp_frac
            
            self.measurementSettings['pll_centerfreq'] = freq
            self.measurementSettings['pll_phase_setpoint'] = phase
            self.measurementSettings['pll_output_amp'] = amp_range*amp_frac
            self.measurementSettings['pll_range'] = freq_range
            
            pll_p = yield self.hf.get_pll_p(self.measurementSettings['pll_output'])
            pll_i = yield self.hf.get_pll_i(self.measurementSettings['pll_output'])
            pll_d = yield self.hf.get_pll_d(self.measurementSettings['pll_output'])
            
            self.measurementSettings['pll_p'] = pll_p
            self.measurementSettings['pll_i'] = pll_i
            self.measurementSettings['pll_d'] = pll_d
            
            pll_input = yield self.hf.get_pll_input(self.measurementSettings['pll_output'])
            pll_harmonic = yield self.hf.get_pll_harmonic(self.measurementSettings['pll_output'])
            
            self.measurementSettings['pll_input'] = int(pll_input)
            self.measurementSettings['pll_harmonic'] = int(pll_harmonic)
            
            pll_tc = yield self.hf.get_pll_tc(self.measurementSettings['pll_output'])
            pll_filterorder = yield self.hf.get_pll_filterorder(self.measurementSettings['pll_output'])
            pll_filterBW = calculate_FilterBW(pll_filterorder, pll_tc)
            
            self.measurementSettings['pll_tc'] = pll_tc
            self.measurementSettings['pll_filterorder'] = pll_filterorder
            self.measurementSettings['pll_filterBW'] = pll_filterBW
            
            #Unlock everything in proper places
            self.unlockFreq()
            
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
            self.startFrequencyMonitoring()
            
        pid_on = yield self.hf.get_pid_on(self.PID_Index)
        if pid_on:
            setpoint = yield self.hf.get_pid_setpoint(self.PID_Index)
            
            delta_f = setpoint - self.measurementSettings['pll_centerfreq']
            
            if delta_f >0:
                self.radioButton_plus.setChecked(True)
            else:
                self.radioButton_plus.setChecked(False)
            
            self.updateFreqThresh(abs(delta_f))

            self.updateConstantHeightStatus.emit(True)
            self.constantHeight = True
            self.label_pidApproachStatus.setText('Constant Height')
            
            #Set constant height mode
            #Get and set freq setpoint / threshold in GUI properly
            
        self.Atto_Z_Voltage = yield self.dac.read_dac_voltage(self.generalSettings['step_z_output'] - 1)
    
    @inlineCallbacks
    def initializePID(self):
        '''
        This function ensures the integrator value of the PID is set such that the starting output voltage is 0 volts. 
        By default, when the range is from 0 to 3 V, the starting output voltage is 1.5V; this fixes that problem. 
        Also sets the output range from 0 to z_volts_max, which is the temperature dependent voltage range.
        
        09/02/2019 I cannot reproduce the starting output voltage being the center. It appears now that the voltage
        stays the same if possible when changing the PID center and range. I don't know how this would have been addressed
        given that no firmware update has been pushed. Anyways, this function is now no longer being called. 
        '''
        try:
            #Make sure the PID is off
            pid_on = yield self.hf.get_pid_on(self.PID_Index)
            if pid_on:
                yield self.hf.set_pid_on(self.PID_Index, False)

            #Set the output range to be what it needs to be
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
            #none of this output any voltage. 

            #turn the multiplier back to 1 for future use. 
            yield self.hf.set_aux_output_monitorscale(self.generalSettings['pid_z_output'], 1)
            #set output back to manual control 
            yield self.hf.set_aux_output_signal(self.generalSettings['pid_z_output'], -1)
        except Exception as inst:
            print inst

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
            #self.hf.set_pll_off(self.measurementSettings['pll_output'])
        self.cxn = False
        self.dac = False
        self.dcbox = False
        self.hf = False
        self.coarsePositioner = False
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
        self.freqSlider.setTickPos([0.008, 0.01, 0.02, 0.04,0.06, 0.08, 0.1,0.2,0.4,0.6, 0.8,1, 2, 4, 6, 8, 10, 20, 40, 60, 80, 100, 200])
        self.freqSlider.setNumPos([0.01, 0.1,1,10, 100])
        self.freqSlider.lower()
        
        self.freqSlider.logValueChanged.connect(self.updateFreqThresh)
        

    def set_p(self):
        val = readNum(str(self.lineEdit_P.text()), self)
        if isinstance(val,float):
            self.PIDApproachSettings['p'] = val
            self.setPIDParameters()
        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))
        
    def set_i(self):
        #note that i can never be set to 0, otherwise the hidden integrator value jumps back to 0
        #which can lead to dangerous voltage spikes to the attocube. 
        val = readNum(str(self.lineEdit_I.text()), self)
        if isinstance(val,float):
            if np.abs(val)> 1e-30:
                self.PIDApproachSettings['i'] = val
                self.setPIDParameters()
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))
        
    def set_d(self):
        val = readNum(str(self.lineEdit_D.text()), self)
        if isinstance(val,float):
            self.PIDApproachSettings['d'] = val
            self.setPIDParameters()
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))
        
    def set_pid_const_height(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_PID_Const_Height.text()), self)
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > self.generalSettings['total_retract_dist']:
                val = self.generalSettings['total_retract_dist']
            self.PIDApproachSettings['height'] = val
        self.lineEdit_PID_Const_Height.setText(formatNum(self.PIDApproachSettings['height']))
        
    def set_pid_step_size(self):
        val = readNum(str(self.lineEdit_PID_Step_Size.text()), self)
        if isinstance(val,float):
            self.PIDApproachSettings['step_size'] = val
        self.lineEdit_PID_Step_Size.setText(formatNum(self.PIDApproachSettings['step_size']))
        
    def set_pid_step_speed(self):
        val = readNum(str(self.lineEdit_PID_Step_Speed.text()), self)
        if isinstance(val,float):
            self.PIDApproachSettings['step_speed'] = val
        self.lineEdit_PID_Step_Speed.setText(formatNum(self.PIDApproachSettings['step_speed']))
        
    def set_man_z_extension(self):
        val = readNum(str(self.lineEdit_Man_Z_Extension.text()), self)
        if isinstance(val,float):
            self.PIDApproachSettings['man z extension'] = val
        self.lineEdit_Man_Z_Extension.setText(formatNum(self.PIDApproachSettings['man z extension'],5))
        
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
        
        if not not self.hf:
            self.setPIDParameters()
        
        print 'Approach Window Voltage Calibration Set'

#--------------------------------------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to updating thresholds."""
    
    @inlineCallbacks
    def updateFreqThresh(self, value = 0):
        try:
            self.freqThreshold = value
            self.lineEdit_freqSet.setText(formatNum(self.freqThreshold))
            self.freqSlider.setPosition(self.freqThreshold)
            yield self.setFreqThreshholdSign()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def setFreqThreshholdSign(self):
        if self.measurementSettings['pll_centerfreq'] is not None and not self.withdrawing:
            if self.radioButton_plus.isChecked():
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] + self.freqThreshold)
            else:
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] - self.freqThreshold)
    
    @inlineCallbacks
    def setFreqThresh(self):
        new_freqThresh = str(self.lineEdit_freqSet.text())
        val = readNum(new_freqThresh, self, False)
        if isinstance(val,float):
            if val < 0.008:
                val = 0.008
            elif val > 200:
                val = 200
            yield self.updateFreqThresh(value = val)
        else:
            self.lineEdit_freqSet.setText(formatNum(self.freqThreshold))
            
    @inlineCallbacks
    def incrementFreqThresh(self):
        if self.radioButton_plus.isChecked():
            val = self.freqThreshold * 1.01
        else:
            val = self.freqThreshold * 0.99
        
        if val < 0.008:
            val = 0.008
        elif val > 200:
            val = 200
        yield self.updateFreqThresh(value = val)
        
    @inlineCallbacks
    def decrementFreqThresh(self):
        if self.radioButton_plus.isChecked():
            val = self.freqThreshold * 0.99
        else:
            val = self.freqThreshold * 1.01
            
        if val < 0.008:
            val = 0.008
        elif val > 200:
            val = 200
            
        yield self.updateFreqThresh(value = val)

#--------------------------------------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to toggling measurements."""
    @inlineCallbacks
    def toggleControllers(self):
        try:
            if not self.approaching:
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
                            
                    #Turn PID off
                    yield self.hf.set_pid_on(self.PID_Index, False)
            else:
                msgBox = QtGui.QMessageBox(self)
                msgBox.setIcon(QtGui.QMessageBox.Information)
                msgBox.setWindowTitle('Measurements Necessary')
                msgBox.setText("\r\n You cannot stop measuring mid-approach. Safely abort the approach before stopping the measurements.")
                msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()
        except Exception as inst:
            print inst
            
    def setWorkingPoint(self, freq, phase, out, amp):
        self.measurementSettings['pll_centerfreq'] = freq
        self.measurementSettings['pll_phase_setpoint'] = phase
        self.measurementSettings['pll_output'] = out
        self.measurementSettings['pll_output_amp'] = amp
        
        self.measurementSettings['meas_pll'] = True
        self.unlockFreq()
        
    @inlineCallbacks
    def setHF2LI_PLL_Settings(self, c = None):
        try:
            #first disable autoSettings
            yield self.hf.set_pll_autocenter(self.measurementSettings['pll_output'],False)
            yield self.hf.set_pll_autotc(self.measurementSettings['pll_output'],False)
            yield self.hf.set_pll_autopid(self.measurementSettings['pll_output'],False)

            #All settings are set for PLL 1 -- this looks not true anymore. Check if modifying
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

            yield self.hf.set_output_range(self.measurementSettings['pll_output'],self.measurementSettings['pll_output_amp'])
            range = yield self.hf.get_output_range(self.measurementSettings['pll_output'])
            yield self.hf.set_output_amplitude(self.measurementSettings['pll_output'],self.measurementSettings['pll_output_amp']/range)
        except Exception as inst:
            print inst
        
    @inlineCallbacks
    def startFrequencyMonitoring(self):
        try:
            #Turn on out and start PLL
            yield self.hf.set_output(self.measurementSettings['pll_output'], True)
            yield self.hf.set_pll_on(self.measurementSettings['pll_output'])
            
            self.deltafData = deque([-200]*self.deltaf_track_length)
            
            while self.measuring:
                deltaf = yield self.hf.get_pll_freqdelta(self.measurementSettings['pll_output'])
                phaseError = yield self.hf.get_pll_error(self.measurementSettings['pll_output'])
                locked = yield self.hf.get_pll_lock(self.measurementSettings['pll_output'])
                self.lineEdit_freqCurr.setText(formatNum(deltaf))
                self.lineEdit_phaseError.setText(formatNum(phaseError))
                
                #Add frequency data to list
                if not self.CPStepping:
                    self.deltafData.appendleft(deltaf)
                    self.deltafData.pop()
                
                points_above_freq_thresh = 0
                
                for f in self.deltafData:
                    if self.radioButton_plus.isChecked():
                        points_above_freq_thresh = points_above_freq_thresh + (f > self.freqThreshold)
                    else:
                        points_above_freq_thresh = points_above_freq_thresh + (f > (-1.0*self.freqThreshold))
                        
                if self.constantHeight and points_above_freq_thresh >= self.generalSettings['auto_retract_points']:
                    print 'auto withdrew'
                    self.withdraw(self.generalSettings['auto_retract_dist'])
                
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
    def abortApproachSequence(self):
        self.approaching = False
        self.updateApproachStatus.emit(False)
        #Turn off PID (just does nothing if it's already off)
        yield self.hf.set_pid_on(self.PID_Index, False)
        
        self.label_pidApproachStatus.setText('Idle')
        self.label_stepApproachStatus.setText('Idle')
    
    @inlineCallbacks
    def disableSetThreshold(self, time):
        self.push_setPLLThresh.setEnabled(False)
        yield self.sleep(time)
        self.push_setPLLThresh.setEnabled(True)
    
#--------------------------------------------------------------------------------------------------------------------------#
    """ The following section contains the PID approach sequence and all related functions."""
    
    @inlineCallbacks
    def startPIDApproachSequence(self):
        try:
            #TODO Add checks that controllers are running and working properly
            self.approaching = True
            self.updateApproachStatus.emit(True)
            
            #Set PID off for initialization
            yield self.hf.set_pid_on(self.PID_Index, False)
            
            #Makes sure we're not in a divded voltage mode, or have DAC Z voltage contributions
            yield self.prepareForPIDApproach()
            
            self.label_pidApproachStatus.setText('Approaching with Zurich')
            #Initializes all the PID settings
            yield self.setHF2LI_PID_Settings()
            
            #Set the output range to be 0 to the max z voltage, which is specified by the temperture of operation. 
            yield self.setPIDOutputRange(self.z_volts_max)
            
            #Turn on PID to start the approach
            yield self.hf.set_pid_on(self.PID_Index, True)
            
            #Empty the deltafData array. This prevents the software from thinking it hit the surface because of 
            #another approach
            self.deltafData = deque([-200]*self.deltaf_track_length)
            
            #Disable to setPLL threshold button until the queue of deltafdata has been replenished. Otherwise, spamming the set threshhold
            #button after starting an approach will be spurradic results
            self.disableSetThreshold(30)
            
            #Empty the zData array. This prevents the software from thinking it hit the surface because of
            #another approach
            self.zData = deque([-50e-9]*self.z_track_length)
            
            while self.approaching:
            
                if self.madeSurfaceContact():
                    self.label_pidApproachStatus.setText('Surface contacted')
                    #PID approach is finished as the surface has been found. 
                    break

                z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

                if z_voltage >= (self.z_volts_max - 0.001) and self.approaching:
                    yield self.hf.set_pid_on(self.PID_Index, False)
                    
                    self.label_pidApproachStatus.setText('Retracting Attocubes')
                    #Find desired retract speed in volts per second
                    retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                    yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)
                    
                    if self.approaching:
                        yield self.stepCoarsePositioners()

                    if self.approaching and self.autoThresholding:
                        self.label_pidApproachStatus.setText('Collecting data for threshold.')
                        #Wait for 30 seconds 
                        yield self.sleep(30)
                        
                        yield self.setPLLThreshold()
                        
                    if self.approaching:
                        #Empty the zData array. This prevents the software from thinking it hit the surface because of
                        #the approach prior to the coarse positioners setpping
                        self.zData = deque([-50e-9]*self.z_track_length)
                        #Turn back on
                        yield self.hf.set_pid_on(self.PID_Index, True)
                        self.label_pidApproachStatus.setText('Approaching with Zurich')
        except Exception as inst:
            print "Gen PID Approach Error:"
            print inst
            
            
    def madeSurfaceContact(self):
        #Two different surface detection algorithms are run. the first just monitors the frequency 
        #of the PLL. If enough points are above the frequency threshold, then assume we're in contact.
        #this number has been aribtrarily set to 5. 10 seemed a little slow.  
        points_above_freq_thresh = 0
        for f in self.deltafData:
            if self.radioButton_plus.isChecked():
                points_above_freq_thresh = points_above_freq_thresh + (f > self.freqThreshold)
            else:
                points_above_freq_thresh = points_above_freq_thresh + (f > (-1.0*self.freqThreshold))
    
        if points_above_freq_thresh > 5:
            print 'Surface contact made with points above frequency threshhold algorithm.'
            return True
            
        #The second algorith fits a line to the past 20 z positions. If the slope of the line is less than 0
        #then presume we made contact. 
        slope, offset = np.polyfit(self.zTime, self.zData, 1)
        if slope < -1e-10:
            print 'Surface contact made with negative z slope algorithm with slope: ', slope
            return True
            
        return False
    
    '''
    Function makes sure that, for the constant height PID approach, we do not have a Z voltage contributed by 
    '''
    @inlineCallbacks
    def prepareForPIDApproach(self):
        #Toggle the sum board to be 1 to 1 
        if self.voltageMultiplied == True:
            #Withdraw completely before switching to 1 to 1
            yield self.withdraw(self.z_meters_max)
            yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 0)
            self.voltageMultiplied = False
            #TODO check that voltage is actually 1 to 1 if recently switched
            
    @inlineCallbacks
    def setZExtension(self):
        #Turn off PID for initialization
        yield self.hf.set_pid_on(self.PID_Index, False)
        #Make sure voltage isn't multiplied or offset by the DAC
        yield self.prepareForPIDApproach()
        
        #Gets the current z extension
        z_voltage = yield self.hf.get_aux_input_value(self.generalSettings['z_mon_input'])
        z_meters = z_voltage / self.z_volts_to_meters
        
        #If current z extension is greater than the desired extension, withdraw
        if z_meters > self.PIDApproachSettings['man z extension']:
            #Eventually have it withdraw the proper amount
            pass
        else:
            #Initializes all the PID settings
            yield self.setHF2LI_PID_Settings()
            
            #Set the output range to be 0 to the max z voltage, which is specified by the temperture of operation. 
            yield self.setPIDOutputRange(self.PIDApproachSettings['man z extension']*self.z_volts_to_meters)
            
            #Turn on PID to start the approach
            yield self.hf.set_pid_on(self.PID_Index, True)
            
            #Emit signal allowing for constant height scanning
            self.updateConstantHeightStatus.emit(True)
            self.constantHeight = True
            self.label_pidApproachStatus.setText('Constant Height')
        
    @inlineCallbacks
    def setPLLThreshold(self):
        #Find the mean and standard deviation of the data that exists 
        #This should just be the mean and std of the past 100 data points taken
        mean = np.mean(self.deltafData)
        std = np.std(self.deltafData)
        
        print "Mean and standard deviation of past 100 points: ", mean, std
        
        new_thresh = mean + 4*std 
        
        if 0.008 < new_thresh < 200:
            self.radioButton_plus.setChecked(True)
            self.radioButton_minus.setChecked(False)
        elif 0 < new_thresh < 0.008:
            self.radioButton_plus.setChecked(True)
            self.radioButton_minus.setChecked(False)
            new_thresh = 0.008
        elif new_thresh > 200:
            self.radioButton_plus.setChecked(True)
            self.radioButton_minus.setChecked(False)
            new_thresh = 200
        elif -0.008 < new_thresh < 0:
            self.radioButton_plus.setChecked(False)
            self.radioButton_minus.setChecked(True)
            new_thresh = 0.008
        elif -200 < new_thresh < -0.008:
            self.radioButton_plus.setChecked(False)
            self.radioButton_minus.setChecked(True)
            new_thresh = np.abs(new_thresh)
        elif new_thresh < -200:
            self.radioButton_plus.setChecked(False)
            self.radioButton_minus.setChecked(True)
            new_thresh = 200
            
        print "New threshold determined by 4 std above the mean: ", new_thresh
        
        yield self.updateFreqThresh(value = new_thresh)
            
    @inlineCallbacks
    def startFeedbackApproachSequence(self):
        try:
            #This function assumes that we are already within the DAC extension range of the surface. 
        
            #TODO make automated check to make sure that sum box is changing voltage
            #mode appropriately. Probably toggle voltage, then go up to 1V output?
            
            #TODO: take note of current surface position to make next step more efficient?
            #Could use self.contactHeight
            
            #First lock in the choice of feedback voltage multiplier 
            self.comboBox_ZMultiplier.setEnabled(False)
            
            #First emit signal saying we are no longer in contact with the surface, either at constant height
            #for feedback
            self.updateConstantHeightStatus.emit(False)
            self.constantHeight = False
            self.updateFeedbackStatus.emit(False)
    
            #start PID approach sequence
            self.approaching = True
            self.updateApproachStatus.emit(True)
            
            
            self.Atto_Z_Voltage = yield self.dac.read_dac_voltage(self.generalSettings['step_z_output'] - 1)
            
            #If the voltage is not yet in the multiplied mode and it needs to be,
            #then we need to withdraw fully to do so safely
            if not self.voltageMultiplied and self.voltageMultiplier < 1:
                #Withdraw fully. This zeros both the Zurich and DAC voltage. 
                yield self. withdraw(self.z_meters_max)
            
            #If the voltage is multiplied, but needs to not be, then we also 
            #need to withdraw
            if self.voltageMultiplied and self.voltageMultiplier == 1:
                #Withdraw fully. This zeros both the Zurich and DAC voltage. 
                yield self. withdraw(self.z_meters_max)
                
            if self.approaching:
                #Make sure the PID is off
                pid_on = yield self.hf.get_pid_on(self.PID_Index)
                if pid_on:
                    yield self.hf.set_pid_on(self.PID_Index, False)
                    
                #If the multiplier is less than one, toggle the sum board
                if self.voltageMultiplier < 1 and not self.voltageMultiplied:
                    #The choice between 0.4 and 0.1 is done through selecting a different sum box. Make sure 
                    #the selected option matches the hardware
                    yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 2.5)
                    self.voltageMultiplied = True
                elif self.voltageMultiplier == 1 and self.voltageMultiplied:
                    yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 0)
                    self.voltageMultiplied = False
                    
                #Scale up the output voltage range. This voltage should be multiplied by 0.4 or 0.1.
                #makes sure that it doesn't accidentally overshoot the voltage
                if self.voltageMultiplied:
                    if self.voltageMultiplier*10 < self.z_volts_max:
                        yield self.setPIDOutputRange(10)
                        max_zurich_voltage = 10
                    else:
                        yield self.setPIDOutputRange(self.z_volts_max/self.voltageMultiplier)
                        max_zurich_voltage = self.z_volts_max/self.voltageMultiplier
                else:
                    yield self.setPIDOutputRange(self.z_volts_max)
                    max_zurich_voltage = self.z_volts_max
                    
                #Initializes all the PID settings. This is mostly to update the PID parameters
                # self.setPIDParameters() might be sufficent instead of all PID settings
                yield self.setHF2LI_PID_Settings()
                
                #start PID approach sequence
                yield self.hf.set_pid_on(self.PID_Index, True)
                self.label_pidApproachStatus.setText('Approaching with Zurich')
                
                #Empty the deltafData array. This prevents the software from thinking it hit the surface because of 
                #another approach
                self.deltafData = deque([-200]*self.deltaf_track_length)
                
                #Empty the zData array. This prevents the software from thinking it hit the surface because of
                #another approach
                self.zData = deque([-50e-9]*self.z_track_length)
                
                #Set conditions to know when we're done approaching with the PID
                while self.approaching:
                    z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
                    #if we've maxed out the PID voltage, we're done approaching with the PID (100 uV offset to deal with minor fringe errors)
                    if z_voltage >= max_zurich_voltage-0.0001:
                        break

                    if self.madeSurfaceContact():
                        break
                        
                #Once PID maxes out, or we're in contact with the surface, step forward with the DAC adc
                #until we're in the middle of the Zurich output range, so that we can maintain feedback 
                #over a range of z voltages
                #TODO: make this better by retracting all the way, taking the appropriate step in with the DAC
                #then approaching again. Also use this to center the voltage better than at 8V
                self.label_pidApproachStatus.setText('Approaching with DAC')
                try:
                    while self.approaching:
                        #check to see if output voltage of the PID has dropped to below 8V 
                        PID_output = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
                        #If we're midrange of the Zurich PID output, then we're in contact with good range
                        if PID_output < max_zurich_voltage/2:
                            print 'In feedback biotch'
                            self.label_pidApproachStatus.setText('In Feedback')
                            self.updateFeedbackStatus.emit(True)
                            break
                            
                        #Atto_Z_Voltage corresponds to the DAC ADC output voltage. HF2LI PID voltage is 
                        #always added in on top of this voltage. 
                        start_voltage = self.Atto_Z_Voltage
                        end_voltage = self.Atto_Z_Voltage + self.PIDApproachSettings['step_size'] * self.z_volts_to_meters
                        
                        #Check to see if we've reached the maximum z voltage. 
                        #If so, stop the approach 
                        if (end_voltage + PID_output*self.voltageMultiplier) > self.z_volts_max:
                            self.label_pidApproachStatus.setText('Feedback Approach Failed')
                            
                            #Fully withdraw DAC and Zurich
                            speed = self.generalSettings['pid_retract_speed']*self.z_volts_to_meters/self.voltageMultiplier
                            yield self.setHF2LI_PID_Integrator(0, speed)
                            
                            speed = self.generalSettings['step_retract_speed']*self.z_volts_to_meters
                            yield self.setDAC_Voltage(self.Atto_Z_Voltage, 0, speed)
                            
                            #Set mode to 1 to 1 again, so that if Approach for Feedback is reinitiated, it does a 
                            #surface approach first -- This might be outdated. Check at some point
                            yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 0)
                            self.voltageMultiplied = False
                            
                            self.approaching = False
                            self.updateApproachStatus.emit(False)
                            break
                            
                        #Take a step forward as specified by the stepwise approach advanced settings
                        speed = self.PIDApproachSettings['step_speed']*self.z_volts_to_meters
                        yield self.setDAC_Voltage(start_voltage, end_voltage, speed)
                            
                    self.approaching = False
                    self.updateApproachStatus.emit(False)
                    self.comboBox_ZMultiplier.setEnabled(True)
                except Exception as inst:
                    print "Feedback Sequence 2 error:"
                    print inst
        except Exception as inst:
            print "Feedback Sequence error:"
            print inst
   
    @inlineCallbacks
    def startPIDConstantHeightApproachSequence(self):
        try:
            #First emit signal saying we are no longer in contact with the surface, either at constant height
            #for feedback
            self.updateConstantHeightStatus.emit(False)
            self.constantHeight = False
            self.updateFeedbackStatus.emit(False)
            
            #Bring us to the surface
            yield self.startPIDApproachSequence()
            
            if self.approaching:
                #Read the voltage being output by the PID
                z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
                
                self.contactHeight = z_voltage / self.z_volts_to_meters
                
                #Determine voltage to which we want to retract to be at the provided constant height
                end_voltage = z_voltage - self.PIDApproachSettings['height'] * self.z_volts_to_meters
                #Find desired retract speed in volts per second
                retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                #Go to the position. The PID will be turned off by calling the set integrator command
                yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)
                    
                #Set range such that maximally extended is at the proper distance from the surface. 
                result = yield self.setPIDOutputRange(end_voltage)
                
                #result is true if we successfully set the range. If we didn't, it means we made contact with the sample closer than we expected
                if result:
                    #Turn PID back on so that if there's drift or the sample is taller than expected, 
                    #the PID will retract the tip
                    yield self.hf.set_pid_on(self.PID_Index, True)
                    
                    #Wait 60 seconds to clear the buffer of frequencies so that we don't autowithdraw from having hit the surface
                    #This can probably be done in a more intelligent way in the future to save a minute
                    yield self.sleep(60)
                    
                    #Emit that we can now scan in constant height mode
                    self.updateConstantHeightStatus.emit(True)
                    self.constantHeight = True
                    self.label_pidApproachStatus.setText('Constant Height')
                    self.approaching = False
                    self.updateApproachStatus.emit(False)
                else:
                    self.label_pidApproachStatus.setText('Could not extend to desired height')
                    self.approaching = False
                    self.updateApproachStatus.emit(False)
                    
        except Exception as inst:
            print inst
            print sys.exc_traceback.tb_lineno
        
        
    @inlineCallbacks
    def setHF2LI_PID_Settings(self, c = None):
        try:
            #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's
            #hard coded in (initialized at start)

            #Set PID parameters
            yield self.setPIDParameters()
            #Sets the output signal type to be an auxiliary output offset
            yield self.hf.set_pid_output_signal(self.PID_Index, 3)
            #Sets the correct channel of the aux output
            yield self.hf.set_pid_output_channel(self.PID_Index, self.generalSettings['pid_z_output'])

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
        if max > 0:
            #Set the output range to be 0 to 'max' V.
            yield self.hf.set_pid_output_center(self.PID_Index, float(max)/2)
            yield self.hf.set_pid_output_range(self.PID_Index, float(max)/2)
            returnValue(True)
        else:
            #If for some reason trying to go into the negative voltages, at least withdraw as far as possible with the Zurich
            print 'Settings output range to be negative!'
            retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters / self.voltageMultiplier
            yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)
            returnValue(False)
            
    @inlineCallbacks
    def setPIDParameters(self):
        print 'PID Parameters Set'
        #Sets PID parameters, noting that i cannot ever be 0, because otherwise this will lead to 
        #voltage jumps as it resets the integrator value. 
        
        #This also converts from m -> V, because the PID works off of volts, yet the input parameters
        #are in meters. Also takes into account whether or not the system is currently in the voltage
        #divided mode
        try:
            if not self.voltageMultiplied:
                yield self.hf.set_pid_p(self.PID_Index, self.z_volts_to_meters*self.PIDApproachSettings['p'])
                yield self.hf.set_pid_i(self.PID_Index, self.z_volts_to_meters*self.PIDApproachSettings['i'])
                yield self.hf.set_pid_d(self.PID_Index, self.z_volts_to_meters*self.PIDApproachSettings['d'])
            else:
                yield self.hf.set_pid_p(self.PID_Index, self.z_volts_to_meters*self.PIDApproachSettings['p']/self.voltageMultiplier)
                yield self.hf.set_pid_i(self.PID_Index, self.z_volts_to_meters*self.PIDApproachSettings['i']/self.voltageMultiplier)
                yield self.hf.set_pid_d(self.PID_Index, self.z_volts_to_meters*self.PIDApproachSettings['d']/self.voltageMultiplier)
        except Exception as inst:
            print "PID errror:"
            print inst
            
    @inlineCallbacks
    def setHF2LI_PID_Integrator(self, val = 0, speed = 1, curr_val = None):
        '''
        Function takes the provided speed (in V/s) to set the integrator value from its current value to the desired value. 
        note: this method can only reduce the voltage. This is done to avoid approaching the sample with PID off. Whenever
        getting closer, the PID should always be active. 
        '''
        #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in (initialized at start)
                
        #Everything below is written as a workaround because there is no way to "Ramp" a voltage with the
        #PID on the Zurich. Therefore, the software uses internal parameters on the Zurich to set up a fake
        #signal, to ramp the PID
        
        #Some settings are changed in bulk with the set_settings function from the HF2LI server instead of the individual functions written in the server
        #to reduce latency and minimize the time spent in limbo before withdrawing 
        tzero = time.clock()
        
        try:
            self.lockWithdrawSensitiveInputs()
            if curr_val is None:
                curr_val = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

            #Only allow withdrawing, ie, lowering the voltage 
            if 0 <= val and val <= curr_val:
                #Get the HF2LI device ID in order to be able to do latency minimizing commands
                dev_ID = yield self.hf.list_devices()
                dev_ID = dev_ID[0][1]
                
                t1 = time.clock()
                
                print 'T1: ', t1 - tzero
                #Calculate center and range to withdraw exactly desired amount
                center = (curr_val - val)/2 + val
                range = (curr_val - val)/2
               
                #Keep track of what aux out 4 was before this algorithm. Removed to make withdrawing faster
                #aux_out_sig = yield self.hf.get_aux_output_signal(4)
                #aux_out_off = yield self.hf.get_aux_output_offset(4)
                
                t2 = time.clock()
                
                print 'T2: ', t2 - tzero
                
                #Make sure the pid is off when setting up the integrator changing
                yield self.hf.set_pid_on(self.PID_Index, False)

                t3 = time.clock()
                
                print 'T3: ', t3 - tzero
                
                #First three inputs turn off proportional and derivative terms, and intergral term to 1 to simplify calculation
                #Next two inputs set the PID input to be aux output 4
                #Next input sets the PID setpoint to be -speed volts. The input signal (aux output 4), is always left as 0 Volt output. 
                #This means that the rate at which the voltage changes is this setpoint (-'speed') times the integrator
                # value (1 /s). So, this changes the voltage at a rate of 'speed' V/s.
                #Next two inputs set Center and range is determined such that at most we withdraw to the desired point. 
                #Final input sets aux out 4 to manual mode, 
                settings = [['/%s/pids/%d/center' % (dev_ID, self.PID_Index-1), str(center)],
                            ['/%s/pids/%d/range' % (dev_ID, self.PID_Index-1), str(range)],
                            ['/%s/pids/%d/input' % (dev_ID, self.PID_Index-1), '5'],
                            ['/%s/pids/%d/inputchannel' % (dev_ID, self.PID_Index-1), '3'],
                            ['/%s/pids/%d/p' % (dev_ID, self.PID_Index-1), '0'],
                            ['/%s/pids/%d/i' % (dev_ID, self.PID_Index-1), '1'],
                            ['/%s/pids/%d/d' % (dev_ID, self.PID_Index-1), '0'],
                            ['/%s/auxouts/%d/outputselect' % (dev_ID, 4-1), '-1'],
                            ['/%s/pids/%d/setpoint' % (dev_ID, self.PID_Index-1),str(-speed)]]
                
                #Next two inputs set the PID output to be the aux output with the right channel. Probably not necessary
                #Following can be added back in if necessary
                # ['/%s/pids/%d/output' % (dev_ID, self.PID_Index-1), '3'],
                # ['/%s/pids/%d/outputchannel' % (dev_ID, self.PID_Index-1), str(self.generalSettings['pid_z_output']-1)]
                
                yield self.hf.set_settings(settings)
                
                t4 = time.clock()
                
                print 'T4: ', t4 - tzero
                # yield self.hf.set_pid_p(self.PID_Index, 0)
                # yield self.hf.set_pid_i(self.PID_Index, 1)
                # yield self.hf.set_pid_d(self.PID_Index, 0)

                # #Sets the PID input signal type to be an auxliary output 
                # yield self.hf.set_pid_input_signal(self.PID_Index, 5)
                # #Sets channel to be aux output 4, which should never be in use elsewhere (as warned on the GUI)
                # yield self.hf.set_pid_input_channel(self.PID_Index, 4)

                # #the following two should already be appropriately set, but can't hurt to set them to the proper values again. 
                # #Sets the output signal type to be an auxiliary output offset
                # yield self.hf.set_pid_output_signal(self.PID_Index, 3)
                # #Sets the correct channel of the aux output
                # yield self.hf.set_pid_output_channel(self.PID_Index, self.generalSettings['pid_z_output'])
                
                # yield self.hf.set_pid_setpoint(self.PID_Index, -speed)
                # #Sets the setpoint to be -speed volts. The input signal (aux output 4), is always left as 0 Volt output. 
                # #This means that the rate at which the voltage changes is this setpoint (-'speed') times the integrator
                # # value (1 /s). So, this changes the voltage at a rate of 'speed' V/s.
                
                #Turn on PID
                yield self.hf.set_pid_on(self.PID_Index, True)
                
                tafter = time.clock()
                
                print 'Total time: ', tafter - tzero
                #Wait the appropriate amount of time
                expected_time = (curr_val - val)/speed
                yield self.sleep(expected_time)
                
                #Turn the PID off
                yield self.hf.set_pid_on(self.PID_Index, False)

                #Set the appropriate PID settings for the PLL, instead of the nonsense set here
                yield self.setHF2LI_PID_Settings()
                
                #Reset the range to the appropriate range
                if self.voltageMultiplied:
                    if self.voltageMultiplier*10 <= self.z_volts_max:
                        yield self.setPIDOutputRange(10)
                    else:
                        yield self.setPIDOutputRange(self.z_volts_max/self.voltageMultiplier)
                else:
                    yield self.setPIDOutputRange(self.z_volts_max)
                    
                #Return aux output 4 to what it was before. Commented out to make process faster
                #yield self.hf.set_aux_output_signal(4, aux_out_sig)
                #yield self.hf.set_aux_output_offset(4, aux_out_off)

            self.unlockWithdrawSensitiveInputs()
        except Exception as inst:
            print "Set integrator error: " + str(inst)
            print 'Error occured on line: ', sys.exc_traceback.tb_lineno
    
    '''
    Function to smoothly ramp between two voltage points are the desired speed provided in volts/s
    '''
    @inlineCallbacks
    def setDAC_Voltage(self, start, end, speed):
        if float(start) != float(end) and end >=0:
            #points required to make smooth ramp of 300 microvolt steps (the limit of 16 bit dac)
            points = np.abs(int((start-end) / (300e-6)))
            #delay in microseconds between each point to get the right speed
            delay = int(300 / speed)

            self.DACRamping = True
            yield self.dac.ramp1(self.generalSettings['step_z_output'] - 1, float(start), float(end), points, delay)
            yield self.sleep(points * delay / 1e6)
            self.DACRamping = False
            self.Atto_Z_Voltage = float(end)
            
            if points * delay / 1e6 > 0.9: 
                a = yield self.dac.read()
                while a != '':
                    print a
                    a = yield self.dac.read()
        
    @inlineCallbacks
    def stepCoarsePositioners(self):
        if self.coarsePositioner == 'Attocube ANC350':
            yield self.stepANC350()
                    
    @inlineCallbacks
    def stepANC350(self, c= None):
        #Set module to coarse positioners are stepping
        self.CPStepping = True
        
        #Assume axis 3 is the z axis. Set the output to be on, and to turn off automatically when end of travel is reached
        yield self.anc.set_axis_output(2, True, True)

        '''
        The following code is for closed loop operation. However, the encoders do not seem reliable 
        enough to make this a good solution, so instead we are using open loop operation
        
        #Set target position for axis 3 to be 6 microns
        yield self.anc.set_target_position(2, 6e-6)
        #Axis 2, True (start automatic motion), True (relative to current position)
        yield self.anc.start_auto_move(2, True, True)
        
        target_reached = False
        while target_reached:
            #Get status information of the axis
            connected, enabled, moving, target, eotFwd, eotBwd, error = yield self.anc.get_axis_status(2)
            #If the target has been reached, then this should all be done
            target_reached = bool(target)
            yield self.sleep(0.25)
        '''
        
        self.label_pidApproachStatus.setText('Stepping with ANC350')
        
        #Get the starting position in z before stepping 
        pos_start = yield self.anc.get_position(2)
        num_steps = 0
        delta = 0
        while delta < self.generalSettings['atto_distance'] and self.approaching:
            #Give axis number and direction (False forward, True is backwards)
            yield self.anc.start_single_step(2, False)
            yield self.sleep(self.generalSettings['atto_delay'])
            pos_curr = yield self.anc.get_position(2)
            if pos_curr < 50e-6:
                yield self.abortApproachSequence()
                break
            delta = pos_curr - pos_start
            num_steps += 1
        print "Moving a distance of " + str(delta) + " took " + str(num_steps) + " steps."
    
        self.coarsePositionerExtension += delta
        self.updateCoarseSteps()
        
        #Once done, set coarse positioners stepping to be false
        self.CPStepping = False
        
    def updateCoarseSteps(self):
        if self.coarsePositioner == 'Attocube ANC350':
            self.lineEdit_CoarseZ.setText(formatNum(self.coarsePositionerExtension, 4))
            
    @inlineCallbacks
    def withdraw(self, dist):
        try:
            #Signal that we are no longer approaching
            self.approaching = False
            self.updateApproachStatus.emit(False)
            
            #Signal that no longer in constant height or in feedback
            self.updateConstantHeightStatus.emit(False)
            self.constantHeight = False
            self.updateFeedbackStatus.emit(False)
        
            #Disable buttons for insane button clickers like Charles Tschirhart <3
            self.push_Withdraw.setEnabled(False)
            self.push_ApproachForFeedback.setEnabled(False)
            self.push_PIDApproachForConstant.setEnabled(False)
            
            #Get Zurich voltage output
            z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
            #Get the Z voltage on the attocubes
            self.Atto_Z_Voltage = yield self.dac.read_dac_voltage(self.generalSettings['step_z_output'] - 1)
            
            self.label_stepApproachStatus.setText('Withdrawing')
            self.label_pidApproachStatus.setText('Withdrawing')
            
            #Keep track of how much distance still needs to be withdrawn after each step
            withdrawDistance = dist
            
            if z_voltage >= 0.001: 
                #Find desired end voltage
                end_voltage = z_voltage - withdrawDistance * self.z_volts_to_meters
                if self.voltageMultiplied:
                    end_voltage = z_voltage - withdrawDistance * self.z_volts_to_meters/self.voltageMultiplier
                    
                print 'Zurich start voltage: '
                print z_voltage
                print 'Zurich end voltage: '
                print end_voltage
                
                if end_voltage < 0:
                    end_voltage = 0
                    #Remaining withdraw distance
                    if self.voltageMultiplied:
                        withdrawDistance = withdrawDistance - z_voltage / (self.z_volts_to_meters/self.voltageMultiplier)
                    else:
                        withdrawDistance = withdrawDistance - z_voltage / self.z_volts_to_meters
                else:
                    #Remaining withdraw distance
                    withdrawDistance = 0
                    
                print 'Zurich distance remaning: '
                print withdrawDistance
                    
                #Find desired retract speed in volts per second
                retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                
                #If output voltage is being divided by 10, multiply by 10 to compensate
                if self.voltageMultiplied:
                    retract_speed = retract_speed/self.voltageMultiplier
                    
                yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed, curr_val = z_voltage)
            
            if self.Atto_Z_Voltage > 0 and withdrawDistance > 0:
                start_voltage = self.Atto_Z_Voltage
                end_voltage = self.Atto_Z_Voltage - withdrawDistance * self.z_volts_to_meters
                
                print 'DACADC start voltage: '
                print start_voltage
                print 'DACADC end voltage: '
                print end_voltage
                
                if end_voltage < 0:
                    end_voltage = 0
                    #distance being withdrawn by DAC
                    withdrawDistance = start_voltage / self.z_volts_to_meters
                
                print 'DACADC withdraw distance: '
                print withdrawDistance
                
                #speed in volts / second
                speed = self.generalSettings['step_retract_speed']*self.z_volts_to_meters
                yield self.setDAC_Voltage(start_voltage, end_voltage, speed)
            
            #Take care of the scenario where the tilt has a negative voltage applied. If this leads to an 
            #overall negative voltage bias on the piezos, zero it. 
            z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
            if z_voltage + self.Atto_Z_Voltage < 0:
                #speed in volts / second
                speed = self.generalSettings['step_retract_speed']*self.z_volts_to_meters
                yield self.setDAC_Voltage(self.Atto_Z_Voltage, -z_voltage, speed)
                
            self.push_Withdraw.setEnabled(True)
            self.push_ApproachForFeedback.setEnabled(True)
            self.push_PIDApproachForConstant.setEnabled(True)
            
            self.label_stepApproachStatus.setText('Idle')
            self.label_pidApproachStatus.setText('Idle')
        except Exception as inst:
            print inst
    
    def setWithdrawDistance(self):
        val = readNum(str(self.lineEdit_Withdraw.text()), self)
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > self.generalSettings['total_retract_dist']:
                val = self.generalSettings['total_retract_dist']
            self.withdrawDistance = val
        self.lineEdit_Withdraw.setText(formatNum(self.withdrawDistance))

    def setZMultiplier(self):
        if self.comboBox_ZMultiplier.currentIndex() == 0:
            self.voltageMultiplier = 1
        elif self.comboBox_ZMultiplier.currentIndex() == 1:
            self.voltageMultiplier = 0.4
        elif self.comboBox_ZMultiplier.currentIndex() == 2:
            self.voltageMultiplier = 0.1
        
    def setAutoThreshold(self):
        self.autoThresholding = self.checkBox_autoThreshold.isChecked()
        
    @inlineCallbacks
    def monitorZVoltage(self):
        #Sleep 2 seconds before starting monitoring to allow everything else to start up properly
        yield self.sleep(2)
        while self.monitorZ:
            try:
                z_voltage = yield self.hf.get_aux_input_value(self.generalSettings['z_mon_input'])
                if z_voltage >= 0:
                    self.progressBar.setValue(int(1000*(z_voltage/self.z_volts_max)))
                else:
                    self.progressBar.setValue(0)
                z_meters = z_voltage / self.z_volts_to_meters
                self.lineEdit_FineZ.setText(formatNum(z_meters, 3))
                self.newZData.emit(z_meters)
                
                self.zData.appendleft(z_meters)
                self.zData.pop()
                
                #Also monitor the other aux input
                aux2_voltage = yield self.hf.get_aux_input_value(self.generalSettings['z_mon_input']%2+1)
                self.newAux2Data.emit(aux2_voltage)
                
                yield self.sleep(0.1)
            except Exception as inst:
                print 'monitor error: ' + str(inst)
                yield self.sleep(0.1)

    @inlineCallbacks
    def blink(self, c = None):
        yield self.blink_server.set_voltage(self.generalSettings['blink_output']-1, 5)
        yield self.sleep(0.25)
        yield self.blink_server.set_voltage(self.generalSettings['blink_output']-1, 0)
        yield self.sleep(0.25)
        
#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""
        
    def setHeight(self, height):
        self.set_pid_const_height(height)
        
    @inlineCallbacks
    def approachConstHeight(self):
        yield self.startPIDConstantHeightApproachSequence()
    
    def getContactPosition(self):
        return self.contactHeight
        
    @inlineCallbacks
    def setFrustratedFeedback(self):
        '''
        Turns on the PLL and PID with frustrated feedback at the current z extension. 
        '''
        #Turn off PID for initialization
        yield self.hf.set_pid_on(self.PID_Index, False)
        
        #Gets the current z extension
        z_voltage = yield self.hf.get_aux_input_value(self.generalSettings['z_mon_input'])
        z_meters = z_voltage / self.z_volts_to_meters
        
        #Initializes all the PID settings
        yield self.setHF2LI_PID_Settings()
        
        #Set the output range to be 0 to the current z voltage
        yield self.setPIDOutputRange(z_voltage)
        
        #Turn on PID to start the approach
        yield self.hf.set_pid_on(self.PID_Index, True)
        
        #Emit signal allowing for constant height scanning
        self.constantHeight = True
        self.updateConstantHeightStatus.emit(True)
        self.label_pidApproachStatus.setText('Constant Height')
        
#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""  
    
    def lockInterface(self):
        self.push_Withdraw.setEnabled(False)
        self.push_GenSettings.setEnabled(False)
        
        self.push_StartControllers.setEnabled(False)
        self.push_MeasurementSettings.setEnabled(False)
        
        self.push_Abort.setEnabled(False)
        self.push_ApproachForFeedback.setEnabled(False)
        self.push_PIDApproachForConstant.setEnabled(False)
        
        self.push_addFreq.setEnabled(False)
        self.push_subFreq.setEnabled(False)
        
        self.push_setZExtension.setEnabled(False)
        
        self.push_setPLLThresh.setDisabled(True)
        
        self.lineEdit_Withdraw.setDisabled(True)

        self.lineEdit_FineZ.setDisabled(True)
        self.lineEdit_CoarseZ.setDisabled(True)
        self.lineEdit_PID_Const_Height.setDisabled(True)
        self.lineEdit_PID_Step_Size.setDisabled(True)
        self.lineEdit_PID_Step_Speed.setDisabled(True)
        self.lineEdit_P.setDisabled(True)
        self.lineEdit_I.setDisabled(True)
        self.lineEdit_D.setDisabled(True)

        self.comboBox_ZMultiplier.setEnabled(False)
        
        self.checkBox_autoThreshold.setEnabled(False)
        
        self.lockFreq()

    def lockFreq(self):
        self.lineEdit_freqSet.setDisabled(True)
        self.freqSlider.setEnabled(False)
        self.radioButton_plus.setEnabled(False)
        self.radioButton_minus.setEnabled(False)
        
    def lockWithdrawSensitiveInputs(self):
        self.lockFreq()
        self.lockFdbkDC()
        self.lockFdbkAC()
        self.lineEdit_P.setDisabled(True)
        self.lineEdit_I.setDisabled(True)
        self.lineEdit_D.setDisabled(True)
        self.push_setPLLThresh.setDisabled(True)
        self.push_addFreq.setDisabled(True)
        self.push_subFreq.setDisabled(True)
        
    def unlockInterface(self):
        self.push_Withdraw.setEnabled(True)
        self.push_GenSettings.setEnabled(True)
        
        self.push_StartControllers.setEnabled(True)
        self.push_MeasurementSettings.setEnabled(True)
        
        self.push_Abort.setEnabled(True)
        self.push_ApproachForFeedback.setEnabled(True)
        self.push_PIDApproachForConstant.setEnabled(True)
        
        self.push_addFreq.setEnabled(True)
        self.push_subFreq.setEnabled(True)
        
        self.push_setZExtension.setEnabled(True)
        
        self.push_setPLLThresh.setDisabled(False)
        
        self.lineEdit_Withdraw.setDisabled(False)

        self.lineEdit_FineZ.setDisabled(False)
        self.lineEdit_CoarseZ.setDisabled(False)
        self.lineEdit_PID_Const_Height.setDisabled(False)
        self.lineEdit_PID_Step_Size.setDisabled(False)
        self.lineEdit_PID_Step_Speed.setDisabled(False)
        self.lineEdit_P.setDisabled(False)
        self.lineEdit_I.setDisabled(False)
        self.lineEdit_D.setDisabled(False)
        
        self.comboBox_ZMultiplier.setEnabled(True)
        
        self.checkBox_autoThreshold.setEnabled(True)
        
        self.unlockFreq()
        
    def unlockFreq(self):
        self.lineEdit_freqSet.setDisabled(False)
        self.freqSlider.setEnabled(True)
        self.radioButton_plus.setEnabled(True)
        self.radioButton_minus.setEnabled(True)
        
    def unlockWithdrawSensitiveInputs(self):
        if self.measurementSettings['meas_pll']:
            self.unlockFreq()
        if self.measurementSettings['meas_fdbk_dc']:
            self.unlockFdbkDC()
        if self.measurementSettings['meas_fdbk_ac']:
            self.unlockFdbkAC()
        self.lineEdit_P.setDisabled(False)
        self.lineEdit_I.setDisabled(False)
        self.lineEdit_D.setDisabled(False)
        self.push_setPLLThresh.setDisabled(False)
        self.push_addFreq.setDisabled(False)
        self.push_subFreq.setDisabled(False)
        
    def updateScanningStatus(self, status):
        print "Scanning status in approach window updated to: "
        print status
        self.DACRamping = status
        
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
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        
class generalApproachSettings(QtGui.QDialog, Ui_generalApproachSettings):
    def __init__(self,reactor, settings, parent = None):
        super(generalApproachSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.pushButton.clicked.connect(self.acceptNewValues)

        self.generalApproachSettings = settings

        self.lineEdit_Step_Retract_Speed.editingFinished.connect(self.setStep_Retract_Speed)
        self.lineEdit_Step_Retract_Time.editingFinished.connect(self.setStep_Retract_Time)
        
        self.lineEdit_PID_Retract_Speed.editingFinished.connect(self.setPID_Retract_Speed)
        self.lineEdit_PID_Retract_Time.editingFinished.connect(self.setPID_Retract_Time)
        
        self.lineEdit_AutoRetractDist.editingFinished.connect(self.setAutoRetractDist)
        self.lineEdit_AutoRetractPoints.editingFinished.connect(self.setAutoRetractPoints)
        
        self.lineEdit_Atto_Distance.editingFinished.connect(self.setAttoDist)
        self.lineEdit_Atto_Delay.editingFinished.connect(self.setAttoDelay)
        
        self.loadValues()
      
    def loadValues(self):
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        
        self.lineEdit_AutoRetractDist.setText(formatNum(self.generalApproachSettings['auto_retract_dist']))
        self.lineEdit_AutoRetractPoints.setText(formatNum(self.generalApproachSettings['auto_retract_points']))
        
        self.lineEdit_Atto_Distance.setText(formatNum(self.generalApproachSettings['atto_distance']))
        self.lineEdit_Atto_Delay.setText(formatNum(self.generalApproachSettings['atto_delay']))
        
    def setSumboard_toggle(self):
        self.generalApproachSettings['sumboard_toggle'] = self.comboBox_Sumboard_Toggle.currentIndex() + 1
        
    def setBlink(self):
        self.generalApproachSettings['blink_output'] = self.comboBox_Blink.currentIndex() + 1
        
    def setStep_Retract_Speed(self):
        val = readNum(str(self.lineEdit_Step_Retract_Speed.text()), self)
        if isinstance(val,float):
            self.generalApproachSettings['step_retract_speed'] = val
            self.generalApproachSettings['step_retract_time'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['step_retract_speed']
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))
        
    def setStep_Retract_Time(self):
        val = readNum(str(self.lineEdit_Step_Retract_Time.text()), self, False)
        if isinstance(val,float):
            self.generalApproachSettings['step_retract_time'] = val
            self.generalApproachSettings['step_retract_speed'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['step_retract_time']
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))

    def setPID_Retract_Speed(self):
        val = readNum(str(self.lineEdit_PID_Retract_Speed.text()), self)
        if isinstance(val,float):
            self.generalApproachSettings['pid_retract_speed'] = val
            self.generalApproachSettings['pid_retract_time'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['pid_retract_speed']
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))
        
    def setPID_Retract_Time(self):
        val = readNum(str(self.lineEdit_PID_Retract_Time.text()), self, False)
        if isinstance(val,float):
            self.generalApproachSettings['pid_retract_time'] = val
            self.generalApproachSettings['pid_retract_speed'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['pid_retract_time']
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))
    
    def setAutoRetractDist(self):
        val = readNum(str(self.lineEdit_AutoRetractDist.text()), self)
        if isinstance(val,float):
            self.generalApproachSettings['auto_retract_dist'] = val
        self.lineEdit_AutoRetractDist.setText(formatNum(self.generalApproachSettings['auto_retract_dist']))
    
    def setAutoRetractPoints(self):
        val = readNum(str(self.lineEdit_AutoRetractPoints.text()), self, False)
        if isinstance(val,float):
            self.generalApproachSettings['auto_retract_points'] = int(val)
        self.lineEdit_AutoRetractPoints.setText(formatNum(self.generalApproachSettings['auto_retract_points']))
    
    def setAttoDist(self):
        val = readNum(str(self.lineEdit_Atto_Distance.text()), self, False)
        if isinstance(val,float):
            self.generalApproachSettings['atto_distance'] = val
        self.lineEdit_Atto_Distance.setText(formatNum(self.generalApproachSettings['atto_distance']))
    
    def setAttoDelay(self):
        val = readNum(str(self.lineEdit_Atto_Delay.text()), self, False)
        if isinstance(val,float):
            self.generalApproachSettings['atto_delay'] = val
        self.lineEdit_Atto_Delay.setText(formatNum(self.generalApproachSettings['atto_delay']))
    
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
        
        self.loadValues()
        self.createLoadingColors()

    def setupAdditionalUi(self):
        self.comboBox_PLL_Input.view().setMinimumWidth(100)
        
    def loadValues(self):
        self.checkBox_pll.setChecked(self.measSettings['meas_pll'])
    
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
        
    def setPLL_TargetBW(self):
        new_target = str(self.lineEdit_TargetBW.text())
        val = readNum(new_target, self, False)
        if isinstance(val,float):
            self.measSettings['pll_targetBW'] = val
        self.lineEdit_TargetBW.setText(formatNum(self.measSettings['pll_targetBW']))
      
    def setPLL_Range(self):
        new_range = str(self.lineEdit_PLL_Range.text())
        val = readNum(new_range, self, False)
        if isinstance(val,float):
            self.measSettings['pll_range'] = val
        self.lineEdit_PLL_Range.setText(formatNum(self.measSettings['pll_range']))

    @inlineCallbacks
    def setPLL_TC(self, c = None):
        new_TC = str(self.lineEdit_PLL_TC.text())
        val = readNum(new_TC, self)
        if isinstance(val,float):
            self.measSettings['pll_tc'] = val
            self.measSettings['pll_filterBW'] = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_tc'])
            yield self.hf.set_advisor_tc(self.measSettings['pll_tc'])
            yield self.updateSimulation()
        self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))

    @inlineCallbacks
    def setPLL_FilterBW(self, c = None):
        new_filterBW = str(self.lineEdit_PLL_FilterBW.text())
        val = readNum(new_filterBW, self, False)
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
        val = readNum(new_P, self, False)
        if isinstance(val,float):
            self.measSettings['pll_p'] = val
            yield self.hf.set_advisor_p(self.measSettings['pll_p'])
            yield self.updateSimulation()
        self.lineEdit_PLL_P.setText(formatNum(self.measSettings['pll_p'], 3))
        
    @inlineCallbacks
    def setPLL_I(self, c = None):
        new_I = str(self.lineEdit_PLL_I.text())
        val = readNum(new_I, self, False)
        if isinstance(val,float):
            self.measSettings['pll_i'] = val
            yield self.hf.set_advisor_i(self.measSettings['pll_i'])
            yield self.updateSimulation()
        self.lineEdit_PLL_I.setText(formatNum(self.measSettings['pll_i'], 3))
        
    @inlineCallbacks
    def setPLL_D(self, c = None):
        new_D = str(self.lineEdit_PLL_D.text())
        val = readNum(new_D, self, False)
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
        val = readNum(str(self.lineEdit_PLL_Amplitude.text()), self)
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