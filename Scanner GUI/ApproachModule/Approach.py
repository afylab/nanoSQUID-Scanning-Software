import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import time

path = sys.path[0] + r"\ApproachModule"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\Approach.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_advancedStepApproachSettings, QtBaseClass = uic.loadUiType(path + r"\advancedStepApproachSettings.ui")
Ui_advancedPIDApproachSettings, QtBaseClass = uic.loadUiType(path + r"\advancedPIDApproachSettings.ui")
Ui_MeasurementSettings, QtBaseClass = uic.loadUiType(path + r"\MeasurementSettings.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    newPLLData = QtCore.pyqtSignal(float, float)

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
        self.push_AdvancedStepApproach.clicked.connect(self.showAdvancedStepApproach)
        self.push_AdvancedPIDApproach.clicked.connect(self.showAdvancedPIDApproach)
        self.push_MeasurementSettings.clicked.connect(self.showMeasurementSettings)
        
        #Connect incrementing buttons
        self.push_addFreq.clicked.connect(self.incrementFreqThresh)
        self.push_addField.clicked.connect(self.incrementFieldThresh)
        self.push_addTemp.clicked.connect(self.incrementTempThresh)
        self.push_subFreq.clicked.connect(self.decrementFreqThresh)
        self.push_subField.clicked.connect(self.decrementFieldThresh)
        self.push_subTemp.clicked.connect(self.decrementTempThresh)
        
        self.lineEdit_freqSet.editingFinished.connect(self.setFreqThresh)
        self.lineEdit_tempSet.editingFinished.connect(self.setTempThresh)
        self.lineEdit_fieldSet.editingFinished.connect(self.setFieldThresh)
        
        self.push_Approach.clicked.connect(self.startApproachSequence)
        self.push_Approach_Abort.clicked.connect(self.abortApproachSequence)

        self.push_PIDApproach.clicked.connect(self.startPIDApproachSequence)
        self.push_PIDApproach_Abort.clicked.connect(self.abortApproachSequence)
        
        self.push_Home.clicked.connect(self.returnToHomePosition)
        self.push_Withdraw.clicked.connect(self.withdrawSpecifiedDistance)
        self.lineEdit_Withdraw.editingFinished.connect(self.setWithdrawDistance)
        
        self.radioButton_plus.toggled.connect(self.setFreqThreshholdSign)

        #Initialize all the labrad connections as none
        self.cxn = None
        self.cpsc = None
        self.dac = None
        self.hf = None

        self.measuring = False
        self.approaching = False
        
        #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in
        self.PID_Index = 1

        self.Atto_Z_Voltage = 0 #Current voltage being sent to Z of attocubes. 
        self.Temperature = 293 #in kelvin
        self.z_volts_to_meters = 3/ 24e-6 #24 microns corresponds to 3 volts, units of volts per meter. Eventually value should depend on temperature
        
        self.withdrawDistance = 2e-6

        self.JPE_Steps = []
                
        '''
        Below is the initialization of all the default measurement settings. Eventually organize into a dictionary
        '''
        self.PLL_Locked = 0 #PLL starts not locked

        self.measurementSettings = {
                'pll_targetBW'        : 100,       #target bandwidth for pid advisor
                'pll_advisemode'      : 2,         #advisor mode. 0 is just proportional term, 1 just integral, 2 is prop + int, and 3 is full PID
                'pll_input'           : 1,         #hf2li input that has the signal for the pll
                'pll_centerfreq'      : None,      #center frequency of the pll loop
                'pll_phase_setpoint'  : None,      #phase setpoint of pll pid loop
                'pll_range'           : 20,        #range around center frequency that the pll is allowed to go
                'pll_harmonic'        : 1,         #harmonic of the input to the pll
                'pll_tc'              : 138.46e-6,  #pll time constant
                'pll_filterBW'        : 500.0,     #pll filter bandwidth 
                'pll_filterorder'     : 4,         #pll filter order (how many filters are cascaded)
                'pll_p'               : 1.397,     #pll pid proportional term
                'pll_i'               : 2.626,     #pll pid integral term 
                'pll_d'               : 0,         #pll pid derivative term
                'pll_simBW'           : 0,         #current pid term simulated bandwidth 
                'pll_pm'              : 0,         #pll pid simulated phase margin (relevant to the stability of loop)   
                'pll_rate'            : 1.842e+6,  #Sampling rate of the PLL. Cannot be changed, despite it being spit out by the pid advisor. Just... is what it is. 
                'pll_output'          : 1,         #hf2li output to be used to completel PLL loop. 
                'pll_output_amp'      : 0.01,      #output amplitude   
                'ft_input'            : 2,         #input of the field / temperature measurement (same input, but different harmonics)
                'ft_freq'             : 20000,     #frequency of the field / temperature measurement
                'ft_output'           : 3,         #output to sample / meander of the field / temperature measurement 
                'ft_amplitude'        : 0.1,       #amplitude of output  
                'field_demod'         : 1,         #demodulator used by the field measurement
                'field_harmonic'      : 1,         #harmonic used for the field measurement
                'field_tc'            : 0.001,     #time constant used for the field measurement   
                'temp_demod'          : 1,         #demodulator used for the temp measurement
                'temp_harmonic'       : 2,         #harmonic used for the temp measurement
                'temp_tc'             : 0.001,     #time constant used for the temp measurement
                }

        '''
        Below is the initialization of all the default Stepwise Approach Settings
        '''

        self.stepwiseApproachSettings = {
                'atto_z_output'              : 1,     #output that goes to Z of attocubes (either from DAC or HF2LI)
                'meastime'                   : 1,     #measurement time in seconds per data point
                'atto_z_step_size'           : 5e-9,  #z step size in meters between measurement points (and/or scanning in xy)
                'atto_z_step_points'         : 50,    #number of points to go through when ramping a single step 
                'atto_z_step_points_delay'   : 1e-3,  #delay in seconds between each point
                'atto_z_step_speed'          : 5e-9 / (50 * 1e-3), #speed in m/s of a step
                'atto_retract_points'        : 1000,  #number of points in ramp when retracting
                'atto_retract_points_delay'  : 5e-4,  #delay in seconds between each point when retracting
                'atto_retract_speed'         : 24e-6 / (1000 * 5e-4), #speed in m/s when retracting
                'jpe_tip_height'             : 24e-3, #Tip height from sample stage in meters. 
                'jpe_module_address'         : 1,     #Pretty sure this is always 1 unless we add more modules to the JPE controller
                'jpe_approach_steps'         : 1000,  #Number of step forward in z direction taken by JPEs after attocube fully extend and retract
                'jpe_approach_size'          : 100,   #relative step size of jpe steps
                'jpe_approach_freq'          : 600,   #Frequency of steps on JPE approach   
                'jpe_retract_steps'          : 1000,  #Number of step forward in z direction taken by JPEs after attocube fully extend and retract
                'jpe_retract_size'           : 100,   #relative step size of jpe steps
                'jpe_retract_freq'           : 600,   #Frequency of steps on JPE approach   
                'jpe_temperature'            : 293,   #Temperature setting of the JPEs
                }
        
        '''
        Below is the initialization of all the default PID Approach Settings
        '''

        self.PIDApproachSettings = {
                'p'                    : 0,     #Proportional term of approch PID 
                'i'                    : 1,     #Integral term of approch PID 
                'd'                    : 0,     #Derivative term of approch PID 
                'atto_z_output'        : 1,     #aux out channel index of output
                'atto_retract_time'    : 2 ,  #time required in seconds for full atto retraction
                'atto_retract_dist'    : 24e-6, #distance retracted in meters by the attocube (eventually should update with temperature)
                'atto_retract_speed'   : 12e-6, #retraction speed in m/s
                'jpe_tip_height'       : 24e-3, #Tip height from sample stage in meters. 
                'jpe_module_address'   : 1,     #Pretty sure this is always 1 unless we add more modules to the JPE controller
                'jpe_approach_steps'   : 1000,  #Number of step forward in z direction taken by JPEs after attocube fully extend and retract
                'jpe_approach_size'    : 100,   #relative step size of jpe steps
                'jpe_approach_freq'    : 600,   #Frequency of steps on JPE approach   
                'jpe_retract_steps'    : 1000,  #Number of step forward in z direction taken by JPEs after attocube fully extend and retract
                'jpe_retract_size'     : 100,   #relative step size of jpe steps
                'jpe_retract_freq'     : 600,   #Frequency of steps on JPE approach   
                'jpe_temperature'      : 293,   #Temperature setting of the JPEs
                }

        '''
        Below is the initialization of all the thresholds for surface detection
        '''

        #Initialize values
        self.freqThreshold = 1.00
        self.tempThreshold = 1e-4
        self.fieldThreshold = 1e-4
        
        self.setFreqThresh()
        self.setTempThresh()
        self.setFieldThresh()

        self.lockInterface()


    def moveDefault(self):    
        self.move(10,170)
        
    def connectLabRAD(self, dict):
        try:
            #self.unlockInterface()
            self.cxn = dict['cxn']
            self.hf = dict['hf2li']
            self.dac = dict['dac_adc']
            self.cpsc = dict['cpsc']
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
        #elif not self.dac:
        #    self.push_Servers.setStyleSheet("#push_Servers{" + 
        #    "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
            self.unlockInterface()
            self.unlockPIDApproach()
        if self.dac != False:
            self.unlockStepwiseApproach()

        self.zeroHF2LI_Aux_Out()
        self.initializePID()
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

    @inlineCallbacks
    def initializePID(self, c = None):
        '''
        This function sets the output range of the PID to be 0V to 10 V. It also
        makes sure the integrator value of the PID is set such that the starting output voltage is 0 volts. 
        By default, when the range is from 0 to 3 V, the starting output voltage is 1.5V; this fixes that
        problem. 
        '''
        try:
            #Make sure the PID is off
            pid_on = yield self.hf.get_pid_on(self.PID_Index)
            if pid_on:
                yield self.hf.set_pid_on(self.PID_Index, False)

            #Set the output range to be 0 to 3 V, which is the required range for room temperature. 
            yield self.hf.set_pid_output_center(self.PID_Index, 1.5)
            yield self.hf.set_pid_output_range(self.PID_Index, 1.5)

            #First turn off proportional and derivative terms
            yield self.hf.set_pid_p(self.PID_Index, 0)
            yield self.hf.set_pid_d(self.PID_Index, 0)
            #Set integrator term to 1
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
            yield self.hf.set_pid_output_channel(self.PID_Index, self.PIDApproachSettings['atto_z_output'])
            
            yield self.hf.set_pid_setpoint(self.PID_Index, -10)
            #Sets the setpoint to be -10V. The input signal (aux output 4), is always left as 0 Volt output. 
            #This means that the rate at which the voltage changes is this setpoint (-10V) times the integrator
            # value (10 /s). So, this changes the voltage at a rate of 10V/s. 
            
            #once monitored, can turn the multiplier to 0 so that the output is always 0 volts. 
            yield self.hf.set_aux_output_monitorscale(self.PIDApproachSettings['atto_z_output'],0)
            #Set the aux output corresponding the to output going to the attocubes to be monitored. 
            yield self.hf.set_aux_output_signal(self.PIDApproachSettings['atto_z_output'], -2)

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
            yield self.hf.set_aux_output_monitorscale(self.PIDApproachSettings['atto_z_output'], 1)
            #set output back to manual control 
            yield self.hf.set_aux_output_signal(self.PIDApproachSettings['atto_z_output'], -1)
        except Exception as inst:
            print inst

    def disconnectLabRAD(self):
        self.cxn = None
        self.cpsc = None
        self.dac = None
        self.hf = None
        self.lockInterface()
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
    def showAdvancedStepApproach(self):      
        advApp = advancedStepApproachSettings(self.reactor, self.stepwiseApproachSettings, self)
        if advApp.exec_():
            self.stepwiseApproachSettings = advApp.getValues()

    def showAdvancedPIDApproach(self):
        advFeed = advancedPIDApproachSettings(self.reactor, self.PIDApproachSettings, self)
        if advFeed.exec_():
            self.PIDApproachSettings = advFeed.getValues()
        
    def showMeasurementSettings(self):
        MeasSet = MeasurementSettings(self.reactor, self.measurementSettings, parent = self, server = self.hf)
        if MeasSet.exec_():
            self.measurementSettings = MeasSet.getValues()
        
    def setupAdditionalUi(self):
        self.fieldSlider.close()
        self.fieldSlider = MySlider(parent = self.centralwidget)
        self.fieldSlider.setGeometry(120,85,260,70)
        self.fieldSlider.setMinimum(0)
        self.fieldSlider.setMaximum(1000000)
        self.fieldSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.fieldSlider.setTickPos([8e-6, 1e-5, 2e-5, 4e-5, 6e-5, 8e-5, 1e-4, 2e-4, 4e-4, 6e-4, 8e-4,1e-3, 2e-3])
        self.fieldSlider.setNumPos([1e-5,1e-4,1e-3])
        self.fieldSlider.lower()
        
        self.tempSlider.close()
        self.tempSlider = MySlider(parent = self.centralwidget)
        self.tempSlider.setGeometry(120,175,260,70)
        self.tempSlider.setMinimum(0)
        self.tempSlider.setMaximum(1000000)
        self.tempSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.tempSlider.setTickPos([8e-6, 1e-5, 2e-5, 4e-5, 6e-5, 8e-5, 1e-4, 2e-4, 4e-4, 6e-4, 8e-4,1e-3, 2e-3])
        self.tempSlider.setNumPos([1e-5,1e-4,1e-3])
        self.tempSlider.lower()
        
        self.freqSlider.close()
        self.freqSlider = MySlider(parent = self.centralwidget)
        self.freqSlider.setGeometry(120,265,260,70)
        self.freqSlider.setMinimum(0)
        self.freqSlider.setMaximum(1000000)
        self.freqSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.freqSlider.setTickPos([0.08, 0.1,0.2,0.4,0.6, 0.8,1, 2, 4, 6, 8, 10, 20])
        self.freqSlider.setNumPos([0.1,1,10])
        self.freqSlider.lower()
        
        self.freqSlider.logValueChanged.connect(self.updateFreqThresh)
        self.fieldSlider.logValueChanged.connect(self.updateFieldThresh)
        self.tempSlider.logValueChanged.connect(self.updateTempThresh)
        
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
            if val < 0.08:
                val = 0.08
            elif val > 20:
                val = 20
            self.updateFreqThresh(value = val)
        
    def incrementFreqThresh(self):
        val = self.freqThreshold * 1.01
        if val < 0.08:
            val = 0.8
        elif val > 20:
            val = 20
        self.updateFreqThresh(value = val)

        
    def decrementFreqThresh(self):
        val = self.freqThreshold * 0.99
        if val < 0.08:
            val = 0.08
        elif val > 20:
            val = 20
        self.updateFreqThresh(value = val)
        
    @inlineCallbacks
    def updateFieldThresh(self, value = 0, update = False):
        self.fieldThreshold = value
        self.lineEdit_fieldSet.setText(formatNum(self.fieldThreshold))
        self.fieldSlider.setPosition(self.fieldThreshold)
        if update:
            #Eventually have this actually live update whatever value necessary
            yield self.sleep(0.1)

    def setFieldThresh(self):
        new_fieldThresh = str(self.lineEdit_fieldSet.text())
        val = readNum(new_fieldThresh)
        if isinstance(val,float):
            if val < 8e-6:
                val = 8e-6
            elif val > 2e-3:
                val = 2e-3
            self.updateFieldThresh(value = val)
        
    def incrementFieldThresh(self):
        val = self.fieldThreshold * 1.005
        if val < 8e-6:
            val = 8e-6
        elif val > 2e-3:
            val = 2e-3
        self.updateFieldThresh(value = val, update = True)
        
    def decrementFieldThresh(self):
        val = self.fieldThreshold * 0.995
        if val < 8e-6:
            val = 8e-6
        elif val > 2e-3:
            val = 2e-3
        self.updateFieldThresh(value = val, update = True)
        
    @inlineCallbacks
    def updateTempThresh(self, value = 0, update = False):
        self.tempThreshold = value
        self.lineEdit_tempSet.setText(formatNum(self.tempThreshold))
        self.tempSlider.setPosition(self.tempThreshold)
        if update:
            #Eventually have this actually live update whatever value necessary
            yield self.sleep(0.1)
        
    def setTempThresh(self):
        new_tempThresh = str(self.lineEdit_tempSet.text())
        val = readNum(new_tempThresh)
        if isinstance(val,float):
            if val < 8e-6:
                val = 8e-6
            elif val > 2e-3:
                val = 2e-3
            self.updateTempThresh(value = val)
            
    def incrementTempThresh(self):
        val = self.tempThreshold * 1.005
        if val < 8e-6:
            val = 8e-6
        elif val > 2e-3:
            val = 2e-3
        self.updateTempThresh(value = val, update = True)
        
    def decrementTempThresh(self):
        val = self.tempThreshold * 0.995
        if val < 8e-6:
            val = 8e-6
        elif val > 2e-3:
            val = 2e-3
        self.updateTempThresh(value = val, update = True)
        
#--------------------------------------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to toggling measurements."""
    @inlineCallbacks
    def toggleControllers(self, c = None):
        if not self.measuring:
            self.push_StartControllers.setText("Stop Controllers")  
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
            
            if self.checkBox_Field.isChecked():
                print 'Starting field measurement'
            if self.checkBox_Freq.isChecked():
                yield self.setHF2LI_PLL_Settings()
                yield self.startFrequencyMonitoring()
            if self.checkBox_Temp.isChecked():
                print 'Starting temp measurement'
        else: 
            self.push_StartControllers.setText("Start Controllers")
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
            
    def setWorkingPoint(self, freq, phase, out, amp):
        self.checkBox_Freq.setCheckable(True)
        self.push_CenterSet.setStyleSheet("""#push_CenterSet{
                                            background: rgb(0, 170, 0);
                                            border-radius: 5px;
                                            }""")
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

            while self.measuring:
                deltaf = yield self.hf.get_pll_freqdelta(self.measurementSettings['pll_output'])
                phaseError = yield self.hf.get_pll_error(self.measurementSettings['pll_output'])
                locked = yield self.hf.get_pll_lock(self.measurementSettings['pll_output'])
                self.lineEdit_freqCurr.setText(formatNum(deltaf))
                self.lineEdit_phaseError.setText(formatNum(phaseError))

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

#--------------------------------------------------------------------------------------------------------------------------#
    """ The following section contains the approach sequence."""
    
    @inlineCallbacks
    def startApproachSequence(self, c = None):
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
            
            #measure deltaf, get average value
            #if below threshold, step by specified step size
            #repeat until full z voltage
            #retract entire way 
            #step forward with JPEs
            #repeat atto cube process
    
    def abortApproachSequence(self):
        self.approaching = False

    @inlineCallbacks
    def startPIDApproachSequence(self, c = None):

        #Add checks that controllers are running and working properly
        self.approaching = True

        #Initializes all the PID settings
        yield self.setHF2LI_PID_Settings()

        yield self.hf.set_pid_on(self.PID_Index, True)

        while self.approaching:
            self.Atto_Z_Voltage = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])
            if self.Atto_Z_Voltage >= 3:
                yield self.hf.set_pid_on(self.PID_Index, False)

                #Find desired retract speed in volts per second
                retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
                yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)

                #Step JPE by specified amount in z direction
                yield self.cpsc.move_z(int(self.PIDApproachSettings['jpe_module_address']), int(self.PIDApproachSettings['jpe_temperature']), int(self.PIDApproachSettings['jpe_approach_freq']), int(self.PIDApproachSettings['jpe_approach_size']), -1.0*self.PIDApproachSettings['jpe_approach_steps'])
                self.JPE_Steps.append([int(self.PIDApproachSettings['jpe_module_address']), int(self.PIDApproachSettings['jpe_temperature']), int(self.PIDApproachSettings['jpe_approach_freq']), int(self.PIDApproachSettings['jpe_approach_size']), -1.0*self.PIDApproachSettings['jpe_approach_steps']])
                #Turn back on
                yield self.hf.set_pid_on(self.PID_Index, True)
        
        yield self.hf.set_pid_on(self.PID_Index, False)

    @inlineCallbacks
    def setHF2LI_PID_Settings(self, c = None):
        try:
            #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in (initialized at start)

            #first set PID parameters, noting that i cannot ever be 0, because otherwise this will lead to voltage jumps as it resets the integrator value. 
            yield self.hf.set_pid_p(self.PID_Index, self.PIDApproachSettings['p'])
            yield self.hf.set_pid_i(self.PID_Index, self.PIDApproachSettings['i'])
            yield self.hf.set_pid_d(self.PID_Index, self.PIDApproachSettings['d'])

            #Sets the output signal type to be an auxiliary output offset
            yield self.hf.set_pid_output_signal(self.PID_Index, 3)
            #Sets the correct channel of the aux output
            yield self.hf.set_pid_output_channel(self.PID_Index, self.PIDApproachSettings['atto_z_output'])

            #Sets the PID input signal to be the oscillator frequency
            yield self.hf.set_pid_input_signal(self.PID_Index, 10)
            #Sets the oscillator frequency to be the same as the one for which the PLL is running
            yield self.hf.set_pid_input_channel(self.PID_Index, self.measurementSettings['pll_output'])

            #Set setpoint
            if self.radioButton_plus.isChecked():
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] + self.freqThreshold)
            else:
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] - self.freqThreshold)

        except Exception as inst:
            print "Set PID settings error" + str(inst)

    @inlineCallbacks
    def setHF2LI_PID_Integrator(self, val = 0, speed = 1):
        #Function takes the provided speed (in V/s) to set the integrator value from its current value to the desired value. 
        #note: this method can only reduce the voltage. This is done to avoid approaching the sample with PID off. Whenever
        #getting closer, the PID should always be active. 
        try:
            #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's hard coded in (initialized at start)
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

            yield self.sleep(0.25)
            #eventually replace with a proper condition identifying that the DAC ADC is connected instead of connected via aux out of the hf2li pid.
            if False:
                start_voltage = self.Atto_Z_Voltage
                end_voltage = self.Atto_Z_Voltage - self.withdrawDistance * self.z_volts_to_meters
                
                #eventually send message saying can't withdraw distance without coarse movement
                if end_voltage < 0:
                    end_voltage = 0

                retract_delay =  int(1e6*self.withdrawDistance / (self.stepwiseApproachSettings['atto_retract_speed'] * self.stepwiseApproachSettings['atto_retract_points']))

                if retract_delay < 100:
                    retract_delay = 100

                print 'Retract delay in microseconds: ' + str(retract_delay)
                #yield self.dac.ramp1(self.Atto_Z_DAC_Out, start_voltage, end_voltage, self.Atto_Retract_Points,retract_delay)
                self.Atto_Z_Voltage = end_voltage
                self.progressBar.setValue(int(100*self.Atto_Z_Voltage))
                self.lineEdit_FineZ.setText(formatNum(self.Atto_Z_Voltage / self.z_volts_to_meters))
            else: 
                z_voltage = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])
                #Find desired end voltage
                end_voltage = z_voltage - self.withdrawDistance * self.z_volts_to_meters

                if end_voltage < 0:
                    end_voltage = 0

                #Find desired retract speed in volts per second
                retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
                yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)

        except Exception as inst:
            print inst
        
    @inlineCallbacks
    def returnToHomePosition(self, c = None):
        try:
            pidapproach_enabled = False
            if self.push_PIDApproach.isEnabled():
                pidapproach_enabled = True
                self.push_PIDApproach.setEnabled(False)

            stepapproach_enabled = False
            if self.push_Approach.isEnabled():
                stepapproach_enabled = True
                self.push_Approach.setEnabled(False)

            retract_speed = self.PIDApproachSettings['atto_retract_speed'] * self.z_volts_to_meters
            yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)
            length = len(self.JPE_Steps)
            for i in range (0,length):
                JPE_Step_Info = self.JPE_Steps[length -1 -i]
                #Go through the steps in reverse direction
                yield self.cpsc.move_z(JPE_Step_Info[0], JPE_Step_Info[1], JPE_Step_Info[2], JPE_Step_Info[3], -1.0*JPE_Step_Info[4])

            self.JPE_Steps = []

            if pidapproach_enabled:
                self.push_PIDApproach.setEnabled(True)

            if stepapproach_enabled:
                self.push_Approach.setEnabled(True)

        except Exception as inst:
            print "Return home error" + str(inst)

    def setWithdrawDistance(self):
        val = readNum(str(self.lineEdit_Withdraw.text()))
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > 24e-6:
                val = 24e-6
            self.withdrawDistance = val
        self.lineEdit_Withdraw.setText(formatNum(self.withdrawDistance))

    @inlineCallbacks
    def monitorZVoltage(self):
        while True:
            z_voltage = yield self.hf.get_aux_output_value(self.PIDApproachSettings['atto_z_output'])
            self.progressBar.setValue(int(1000*(z_voltage/3)))
            self.lineEdit_FineZ.setText(formatNum(z_voltage / self.z_volts_to_meters))

        #self.progressBar.setValue(int(100*self.Atto_Z_Voltage))
        #self.lineEdit_FineZ.setText(formatNum(self.Atto_Z_Voltage / self.z_volts_to_meters))


#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""  
    
    def lockInterface(self):
        self.push_Home.setEnabled(False)
        self.push_Withdraw.setEnabled(False)
        self.push_StartControllers.setEnabled(False)
        self.push_MeasurementSettings.setEnabled(False)
        self.push_Approach.setEnabled(False)
        self.push_Approach_Abort.setEnabled(False)
        self.push_PIDApproach.setEnabled(False)
        self.push_PIDApproach_Abort.setEnabled(False)
        self.push_AdvancedStepApproach.setEnabled(False)
        self.push_AdvancedPIDApproach.setEnabled(False)

        self.push_addField.setEnabled(False)
        self.push_subField.setEnabled(False)
        self.push_addTemp.setEnabled(False)
        self.push_subTemp.setEnabled(False)
        self.push_addFreq.setEnabled(False)
        self.push_subFreq.setEnabled(False)
        
        self.lineEdit_Withdraw.setDisabled(True)
        self.lineEdit_fieldSet.setDisabled(True)
        self.lineEdit_tempSet.setDisabled(True)
        self.lineEdit_freqSet.setDisabled(True)
        self.lineEdit_FineZ.setDisabled(True)
        
        self.fieldSlider.setEnabled(False)
        self.tempSlider.setEnabled(False)
        self.freqSlider.setEnabled(False)

        self.checkBox_Freq.setEnabled(False)
        self.checkBox_Temp.setEnabled(False)
        self.checkBox_Field.setEnabled(False)
        self.checkBox_Scan.setEnabled(False)

        self.radioButton_plus.setEnabled(False)
        self.radioButton_minus.setEnabled(False)
        
    def unlockInterface(self):
        self.push_Home.setEnabled(True)
        self.push_Withdraw.setEnabled(True)
        self.push_StartControllers.setEnabled(True)
        self.push_MeasurementSettings.setEnabled(True)

        self.push_addField.setEnabled(True)
        self.push_subField.setEnabled(True)
        self.push_addTemp.setEnabled(True)
        self.push_subTemp.setEnabled(True)
        self.push_addFreq.setEnabled(True)
        self.push_subFreq.setEnabled(True)

        self.lineEdit_Withdraw.setDisabled(False)
        self.lineEdit_fieldSet.setDisabled(False)
        self.lineEdit_tempSet.setDisabled(False)
        self.lineEdit_freqSet.setDisabled(False)
        self.lineEdit_FineZ.setDisabled(False)
        
        self.fieldSlider.setEnabled(True)
        self.tempSlider.setEnabled(True)
        self.freqSlider.setEnabled(True)

        self.checkBox_Freq.setEnabled(True)
        self.checkBox_Temp.setEnabled(True)
        self.checkBox_Field.setEnabled(True)


        self.radioButton_plus.setEnabled(True)
        self.radioButton_minus.setEnabled(True)

    def unlockStepwiseApproach(self):
        self.push_Approach.setEnabled(True)
        self.push_Approach_Abort.setEnabled(True)
        self.push_AdvancedStepApproach.setEnabled(True)

    def unlockPIDApproach(self):
        self.push_PIDApproach.setEnabled(True)
        self.push_PIDApproach_Abort.setEnabled(True)
        self.push_AdvancedPIDApproach.setEnabled(True)

        self.checkBox_Scan.setEnabled(True)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def closeEvent(self, e):
        if self.hf is not None:
            self.zeroHF2LI_Aux_Out()

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
              
class advancedStepApproachSettings(QtGui.QDialog, Ui_advancedStepApproachSettings):
    def __init__(self,reactor, stepApproachSettings, parent = None):
        super(advancedStepApproachSettings, self).__init__(parent)
        self.setupUi(self)
        self.setupAdditionalUi()
        
        self.pushButton.clicked.connect(self.acceptNewValues)
      
        self.stepApproachSettings = stepApproachSettings
        
        #Load those values into their appropriate GUI item
        self.loadValues()
        
        self.lineEdit_Atto_Z_Step_Size.editingFinished.connect(self.setAtto_Z_Step_Size)
        self.lineEdit_Atto_Z_Points.editingFinished.connect(self.setAtto_Z_Points)
        self.lineEdit_Atto_Z_Delay.editingFinished.connect(self.setAtto_Z_Delay)
        self.lineEdit_Atto_Z_Speed.editingFinished.connect(self.setAtto_Z_Speed)
        self.lineEdit_Atto_Retract_Points.editingFinished.connect(self.setAtto_Retract_Points)
        self.lineEdit_Atto_Retract_Delay.editingFinished.connect(self.setAtto_Retract_Delay)
        self.lineEdit_Atto_Retract_Speed.editingFinished.connect(self.setAtto_Retract_Speed)
        
        self.lineEdit_Approach_MeasTime.editingFinished.connect(self.setApproach_MeasTime)
        self.comboBox_Atto_Z_DAC_Out.currentIndexChanged.connect(self.setAtto_Z_DAC_Out)
      
        self.lineEdit_Temperature.editingFinished.connect(self.setTemperature)
        self.lineEdit_Tip_Height.editingFinished.connect(self.setJPE_Tip_Height)
        self.comboBox_JPE_Address.currentIndexChanged.connect(self.setJPE_Address)
        
        self.lineEdit_JPE_Approach_Steps.editingFinished.connect(self.setJPE_Approach_Steps)
        self.lineEdit_JPE_Approach_Size.editingFinished.connect(self.setJPE_Approach_Size)
        self.lineEdit_JPE_Approach_Freq.editingFinished.connect(self.setJPE_Approach_Freq)
        
        self.lineEdit_JPE_Retract_Steps.editingFinished.connect(self.setJPE_Retract_Steps)
        self.lineEdit_JPE_Retract_Size.editingFinished.connect(self.setJPE_Retract_Size)
        self.lineEdit_JPE_Retract_Freq.editingFinished.connect(self.setJPE_Retract_Freq)
        
    def setupAdditionalUi(self):
        pass

    def loadValues(self):
        self.lineEdit_Atto_Z_Step_Size.setText(formatNum(self.stepApproachSettings['atto_z_step_size'])) 
        self.lineEdit_Atto_Z_Points.setText(formatNum(self.stepApproachSettings['atto_z_step_points'])) 
        self.lineEdit_Atto_Z_Delay.setText(formatNum(self.stepApproachSettings['atto_z_step_points_delay'])) 
        self.lineEdit_Atto_Z_Speed.setText(formatNum(self.stepApproachSettings['atto_z_step_speed'])) 
        self.lineEdit_Atto_Retract_Points.setText(formatNum(self.stepApproachSettings['atto_retract_points'])) 
        self.lineEdit_Atto_Retract_Delay.setText(formatNum(self.stepApproachSettings['atto_retract_points_delay']))
        self.lineEdit_Atto_Retract_Speed.setText(formatNum(self.stepApproachSettings['atto_retract_speed']))
        
        self.lineEdit_Approach_MeasTime.setText(formatNum(self.stepApproachSettings['meastime']))
        self.comboBox_Atto_Z_DAC_Out.setCurrentIndex(self.stepApproachSettings['atto_z_output'] - 1)
        
        self.lineEdit_Temperature.setText(formatNum(self.stepApproachSettings['jpe_temperature']))
        self.lineEdit_Tip_Height.setText(formatNum(self.stepApproachSettings['jpe_tip_height']))
        self.comboBox_JPE_Address.setCurrentIndex(self.stepApproachSettings['jpe_module_address'] - 1)
        
        self.lineEdit_JPE_Approach_Steps.setText(formatNum(self.stepApproachSettings['jpe_approach_steps']))
        self.lineEdit_JPE_Approach_Size.setText(formatNum(self.stepApproachSettings['jpe_approach_size']))
        self.lineEdit_JPE_Approach_Freq.setText(formatNum(self.stepApproachSettings['jpe_approach_freq']))
        
        self.lineEdit_JPE_Retract_Steps.setText(formatNum(self.stepApproachSettings['jpe_retract_steps']))
        self.lineEdit_JPE_Retract_Size.setText(formatNum(self.stepApproachSettings['jpe_retract_size']))
        self.lineEdit_JPE_Retract_Freq.setText(formatNum(self.stepApproachSettings['jpe_retract_freq']))
        
    def setAtto_Z_Step_Size(self):
        val = readNum(str(self.lineEdit_Atto_Z_Step_Size.text()))
        if isinstance(val,float):
            self.stepApproachSettings['atto_z_step_size'] = val
            self.stepApproachSettings['atto_z_step_speed'] = self.stepApproachSettings['atto_z_step_size'] / (self.stepApproachSettings['atto_z_step_points'] * self.stepApproachSettings['atto_z_step_points_delay'])
        self.lineEdit_Atto_Z_Step_Size.setText(formatNum(self.stepApproachSettings['atto_z_step_size']))
        self.lineEdit_Atto_Z_Speed.setText(formatNum(self.stepApproachSettings['atto_z_step_speed']))
        
    def setAtto_Z_Points(self):
        val = readNum(str(self.lineEdit_Atto_Z_Points.text()))
        if isinstance(val,float):
            self.stepApproachSettings['atto_z_step_points'] = val
            self.stepApproachSettings['atto_z_step_speed'] =  self.stepApproachSettings['atto_z_step_size'] / (self.stepApproachSettings['atto_z_step_points'] * self.stepApproachSettings['atto_z_step_points_delay'])
        self.lineEdit_Atto_Z_Points.setText(formatNum(self.stepApproachSettings['atto_z_step_points']))
        self.lineEdit_Atto_Z_Speed.setText(formatNum(self.stepApproachSettings['atto_z_step_speed']))
        
    def setAtto_Z_Delay(self):
        val = readNum(str(self.lineEdit_Atto_Z_Delay.text()))
        if isinstance(val,float):
            self.stepApproachSettings['atto_z_step_points_delay'] = val
            self.stepApproachSettings['atto_z_step_speed'] =  self.stepApproachSettings['atto_z_step_size'] / (self.stepApproachSettings['atto_z_step_points'] * self.stepApproachSettings['atto_z_step_points_delay'])
        self.lineEdit_Atto_Z_Delay.setText(formatNum(self.stepApproachSettings['atto_z_step_points_delay']))
        self.lineEdit_Atto_Z_Speed.setText(formatNum(self.stepApproachSettings['atto_z_step_speed']))
        
    def setAtto_Z_Speed(self):
        val = readNum(str(self.lineEdit_Atto_Z_Speed.text()))
        if isinstance(val,float):
            self.stepApproachSettings['atto_z_step_speed'] = val
            self.stepApproachSettings['atto_z_step_points_delay'] =  self.stepApproachSettings['atto_z_step_size'] / (self.stepApproachSettings['atto_z_step_points'] * self.stepApproachSettings['atto_z_step_speed'])
        self.lineEdit_Atto_Z_Speed.setText(formatNum(self.stepApproachSettings['atto_z_step_speed']))
        self.lineEdit_Atto_Z_Delay.setText(formatNum(self.stepApproachSettings['atto_z_step_points_delay']))
        
    def setAtto_Retract_Delay(self):
        val = readNum(str(self.lineEdit_Atto_Retract_Delay.text()))
        if isinstance(val,float):
            self.stepApproachSettings['atto_retract_points_delay']  = val
            self.stepApproachSettings['atto_retract_speed']  = 24e-6 / (self.stepApproachSettings['atto_retract_points'] *self.stepApproachSettings['atto_retract_points_delay'])
        self.lineEdit_Atto_Retract_Delay.setText(formatNum(self.stepApproachSettings['atto_retract_points_delay']))
        self.lineEdit_Atto_Retract_Speed.setText(formatNum(self.stepApproachSettings['atto_retract_speed']))
        
    def setAtto_Retract_Points(self):
        val = readNum(str(self.lineEdit_Atto_Retract_Points.text()))
        if isinstance(val,float):
            self.stepApproachSettings['atto_retract_points'] = val
            self.stepApproachSettings['atto_retract_speed'] = 24e-6 / (self.stepApproachSettings['atto_retract_points'] *self.stepApproachSettings['atto_retract_points_delay'])
        self.lineEdit_Atto_Retract_Points.setText(formatNum(self.stepApproachSettings['atto_retract_points']))
        self.lineEdit_Atto_Retract_Speed.setText(formatNum(self.stepApproachSettings['atto_retract_speed']))
        
    def setAtto_Retract_Speed(self):
        val = readNum(str(self.lineEdit_Atto_Retract_Speed.text()))
        if isinstance(val,float):
            self.stepApproachSettings['atto_retract_speed'] = val
            self.stepApproachSettings['atto_retract_points_delay'] = 24e-6 / (self.stepApproachSettings['atto_retract_points'] *self.stepApproachSettings['atto_retract_speed'])
        self.lineEdit_Atto_Retract_Speed.setText(formatNum(self.stepApproachSettings['atto_retract_speed']))
        self.lineEdit_Atto_Retract_Delay.setText(formatNum(self.stepApproachSettings['atto_retract_points_delay']))
        
    def setApproach_MeasTime(self):
        val = readNum(str(self.lineEdit_Approach_MeasTime.text()))
        if isinstance(val,float):
            self.stepApproachSettings['meastime'] = val
        self.lineEdit_Approach_MeasTime.setText(formatNum(self.stepApproachSettings['meastime']))
        
    def setAtto_Z_DAC_Out(self):
        self.stepApproachSettings['atto_z_output'] = self.comboBox_Atto_Z_DAC_Out.currentIndex() + 1
        
    def setTemperature(self):
        val = readNum(str(self.lineEdit_Temperature.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_temperature'] = val
        self.lineEdit_Temperature.setText(formatNum(self.stepApproachSettings['jpe_temperature']))
    
    def setJPE_Tip_Height(self):
        val = readNum(str(self.lineEdit_Tip_Height.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_tip_height'] = val
        self.lineEdit_Tip_Height.setText(formatNum(self.stepApproachSettings['jpe_tip_height']))
        
    def setJPE_Address(self):
        self.stepApproachSettings['jpe_module_address'] = self.comboBox_JPE_Address.currentIndex() + 1
    
    def setJPE_Approach_Steps(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Steps.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_approach_steps'] = val
        self.lineEdit_JPE_Approach_Steps.setText(formatNum(self.stepApproachSettings['jpe_approach_steps']))
        
    def setJPE_Approach_Size(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Size.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_approach_size'] = val
        self.lineEdit_JPE_Approach_Size.setText(formatNum(self.stepApproachSettings['jpe_approach_size']))
        
    def setJPE_Approach_Freq(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Freq.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_approach_freq'] = val
        self.lineEdit_JPE_Approach_Freq.setText(formatNum(self.stepApproachSettings['jpe_approach_freq'] ))
        
    def setJPE_Retract_Steps(self):
        val = readNum(str(self.lineEdit_JPE_Retract_Steps.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_retract_steps']  = val
        self.lineEdit_JPE_Retract_Steps.setText(formatNum(self.stepApproachSettings['jpe_retract_steps']))
        
    def setJPE_Retract_Size(self):
        val = readNum(str(self.lineEdit_JPE_Retract_Size.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_retract_size'] = val
        self.lineEdit_JPE_Retract_Size.setText(formatNum(self.stepApproachSettings['jpe_retract_size']))
        
    def setJPE_Retract_Freq(self):
        val = readNum(str(self.lineEdit_JPE_Retract_Freq.text()))
        if isinstance(val,float):
            self.stepApproachSettings['jpe_retract_freq'] = val
        self.lineEdit_JPE_Retract_Freq.setText(formatNum(self.stepApproachSettings['jpe_retract_freq']))
    
    def acceptNewValues(self):
        self.accept()
        
    def getValues(self):
        return self.stepApproachSettings
        
class advancedPIDApproachSettings(QtGui.QDialog, Ui_advancedPIDApproachSettings):
    def __init__(self,reactor, settings, parent = None):
        super(advancedPIDApproachSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.pushButton.clicked.connect(self.acceptNewValues)

        self.PIDApproachSettings = settings

        self.lineEdit_P.editingFinished.connect(self.set_p)
        self.lineEdit_I.editingFinished.connect(self.set_i)
        self.lineEdit_D.editingFinished.connect(self.set_d)

        self.comboBox_Atto_Z_DAC_Out.currentIndexChanged.connect(self.setAtto_Z_DAC_Out)
        self.lineEdit_Atto_Retract_Speed.editingFinished.connect(self.setAtto_Retract_Speed)
        self.lineEdit_Atto_Retract_Time.editingFinished.connect(self.setAtto_Retract_Time)

        self.lineEdit_Temperature.editingFinished.connect(self.setTemperature)
        self.lineEdit_Tip_Height.editingFinished.connect(self.setJPE_Tip_Height)
        self.comboBox_JPE_Address.currentIndexChanged.connect(self.setJPE_Address)
        
        self.lineEdit_JPE_Approach_Steps.editingFinished.connect(self.setJPE_Approach_Steps)
        self.lineEdit_JPE_Approach_Size.editingFinished.connect(self.setJPE_Approach_Size)
        self.lineEdit_JPE_Approach_Freq.editingFinished.connect(self.setJPE_Approach_Freq)
        
        self.lineEdit_JPE_Retract_Steps.editingFinished.connect(self.setJPE_Retract_Steps)
        self.lineEdit_JPE_Retract_Size.editingFinished.connect(self.setJPE_Retract_Size)
        self.lineEdit_JPE_Retract_Freq.editingFinished.connect(self.setJPE_Retract_Freq)

        self.loadValues()
      
    def loadValues(self):
        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p'])) 
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i'])) 
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d'])) 

        self.comboBox_Atto_Z_DAC_Out.setCurrentIndex(self.PIDApproachSettings['atto_z_output'] - 1)

        self.lineEdit_Atto_Retract_Time.setText(formatNum(self.PIDApproachSettings['atto_retract_time']))
        self.lineEdit_Atto_Retract_Speed.setText(formatNum(self.PIDApproachSettings['atto_retract_speed']))
        
        self.lineEdit_Temperature.setText(formatNum(self.PIDApproachSettings['jpe_temperature']))
        self.lineEdit_Tip_Height.setText(formatNum(self.PIDApproachSettings['jpe_tip_height']))
        self.comboBox_JPE_Address.setCurrentIndex(self.PIDApproachSettings['jpe_module_address'] - 1)
        
        self.lineEdit_JPE_Approach_Steps.setText(formatNum(self.PIDApproachSettings['jpe_approach_steps']))
        self.lineEdit_JPE_Approach_Size.setText(formatNum(self.PIDApproachSettings['jpe_approach_size']))
        self.lineEdit_JPE_Approach_Freq.setText(formatNum(self.PIDApproachSettings['jpe_approach_freq']))
        
        self.lineEdit_JPE_Retract_Steps.setText(formatNum(self.PIDApproachSettings['jpe_retract_steps']))
        self.lineEdit_JPE_Retract_Size.setText(formatNum(self.PIDApproachSettings['jpe_retract_size']))
        self.lineEdit_JPE_Retract_Freq.setText(formatNum(self.PIDApproachSettings['jpe_retract_freq']))

    def set_p(self):
        val = readNum(str(self.lineEdit_P.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['p'] = val
        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))

    def set_i(self):
        #notes that i can never be set to 0, otherwise the hidden integrator value jumps back to 0
        #which can lead to dangerous voltage spikes to the attocube. 
        val = readNum(str(self.lineEdit_I.text()))
        if isinstance(val,float):
            if np.abs(val)> 1e-30:
                self.PIDApproachSettings['i'] = val
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))

    def set_d(self):
        val = readNum(str(self.lineEdit_D.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['d'] = val
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))

    def setAtto_Z_DAC_Out(self):
        self.PIDApproachSettings['atto_z_output'] = self.comboBox_Atto_Z_DAC_Out.currentIndex() + 1

    def setAtto_Retract_Speed(self):
        val = readNum(str(self.lineEdit_Atto_Retract_Speed.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['atto_retract_speed'] = val
            self.PIDApproachSettings['atto_retract_time'] = 24e-6 / self.PIDApproachSettings['atto_retract_speed']
        self.lineEdit_Atto_Retract_Speed.setText(formatNum(self.PIDApproachSettings['atto_retract_speed']))
        self.lineEdit_Atto_Retract_Time.setText(formatNum(self.PIDApproachSettings['atto_retract_time']))
        
    def setAtto_Retract_Time(self):
        val = readNum(str(self.lineEdit_Atto_Retract_Time.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['atto_retract_time'] = val
            self.PIDApproachSettings['atto_retract_speed'] = 24e-6 / self.PIDApproachSettings['atto_retract_time']
        self.lineEdit_Atto_Retract_Speed.setText(formatNum(self.PIDApproachSettings['atto_retract_speed']))
        self.lineEdit_Atto_Retract_Time.setText(formatNum(self.PIDApproachSettings['atto_retract_time']))

    def setTemperature(self):
        val = readNum(str(self.lineEdit_Temperature.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_temperature'] = val
        self.lineEdit_Temperature.setText(formatNum(self.PIDApproachSettings['jpe_temperature']))
    
    def setJPE_Tip_Height(self):
        val = readNum(str(self.lineEdit_Tip_Height.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_tip_height'] = val
        self.lineEdit_Tip_Height.setText(formatNum(self.PIDApproachSettings['jpe_tip_height']))
        
    def setJPE_Address(self):
        self.PIDApproachSettings['jpe_module_address'] = self.comboBox_JPE_Address.currentIndex() + 1
    
    def setJPE_Approach_Steps(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Steps.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_approach_steps'] = val
        self.lineEdit_JPE_Approach_Steps.setText(formatNum(self.PIDApproachSettings['jpe_approach_steps']))
        
    def setJPE_Approach_Size(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Size.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_approach_size'] = val
        self.lineEdit_JPE_Approach_Size.setText(formatNum(self.PIDApproachSettings['jpe_approach_size']))
        
    def setJPE_Approach_Freq(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Freq.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_approach_freq'] = val
        self.lineEdit_JPE_Approach_Freq.setText(formatNum(self.PIDApproachSettings['jpe_approach_freq'] ))
        
    def setJPE_Retract_Steps(self):
        val = readNum(str(self.lineEdit_JPE_Retract_Steps.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_retract_steps']  = val
        self.lineEdit_JPE_Retract_Steps.setText(formatNum(self.PIDApproachSettings['jpe_retract_steps']))
        
    def setJPE_Retract_Size(self):
        val = readNum(str(self.lineEdit_JPE_Retract_Size.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_retract_size'] = val
        self.lineEdit_JPE_Retract_Size.setText(formatNum(self.PIDApproachSettings['jpe_retract_size']))
        
    def setJPE_Retract_Freq(self):
        val = readNum(str(self.lineEdit_JPE_Retract_Freq.text()))
        if isinstance(val,float):
            self.PIDApproachSettings['jpe_retract_freq'] = val
        self.lineEdit_JPE_Retract_Freq.setText(formatNum(self.PIDApproachSettings['jpe_retract_freq']))

    def acceptNewValues(self):
        self.accept()
        
    def getValues(self):
        return self.PIDApproachSettings
        

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
        
        self.lineEdit_FT_Freq.editingFinished.connect(self.setFT_Freq)
        self.lineEdit_FT_Amp.editingFinished.connect(self.setFT_Amp)
        
        self.comboBox_FT_Input.currentIndexChanged.connect(self.setFT_Input)
        self.comboBox_FT_Output.currentIndexChanged.connect(self.setFT_Output)
        
        self.lineEdit_F_TC.editingFinished.connect(self.setF_TC)
        
        self.comboBox_F_Demod.currentIndexChanged.connect(self.setF_Demod)
        self.comboBox_F_Harmonic.currentIndexChanged.connect(self.setF_Harmonic)
        
        self.lineEdit_T_TC.editingFinished.connect(self.setT_TC)
        
        self.comboBox_T_Demod.currentIndexChanged.connect(self.setT_Demod)
        self.comboBox_T_Harmonic.currentIndexChanged.connect(self.setT_Harmonic)
        
        self.lineEdit_PLL_Amplitude.editingFinished.connect(self.setPLL_Output_Amplitude)
        self.comboBox_PLL_Output.currentIndexChanged.connect(self.setPLL_Output)

        self.loadValues()
        self.createLoadingColors()

    def setupAdditionalUi(self):
        self.comboBox_PLL_Input.view().setMinimumWidth(100)
        
    def loadValues(self):
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
        
        self.comboBox_FT_Input.setCurrentIndex(self.measSettings['ft_input']-1)
        self.comboBox_FT_Output.setCurrentIndex(self.measSettings['ft_output']-1)
        
        self.lineEdit_FT_Freq.setText(formatNum(self.measSettings['ft_freq']))

        if self.measSettings['ft_output'] == 3:
            self.lineEdit_FT_Amp.setText('N/A')
            self.lineEdit_FT_Amp.setEnabled(False)
        else:
            self.lineEdit_FT_Amp.setText(formatNum(self.measSettings['ft_amplitude']))
            self.lineEdit_FT_Amp.setEnabled(True)
            
        self.comboBox_F_Demod.setCurrentIndex(self.measSettings['field_demod']-1)
        self.comboBox_F_Harmonic.setCurrentIndex(self.measSettings['field_harmonic']-1)
        self.lineEdit_F_TC.setText(formatNum(self.measSettings['field_tc']))
        
        self.comboBox_T_Demod.setCurrentIndex(self.measSettings['temp_demod']-1)
        self.comboBox_T_Harmonic.setCurrentIndex(self.measSettings['temp_harmonic']-1)
        self.lineEdit_T_TC.setText(formatNum(self.measSettings['temp_tc']))

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
        
    def setFT_Freq(self):
        new_freq = str(self.lineEdit_FT_Freq.text())
        val = readNum(new_freq)
        if isinstance(val,float):
            self.measSettings['ft_freq'] = val
        self.lineEdit_FT_Freq.setText(formatNum(self.measSettings['ft_freq']))
        
    def setFT_Amp(self):
        val = readNum(str(self.lineEdit_FT_Amp.text()))
        if isinstance(val,float):
            self.measSettings['ft_amplitude'] = val
        self.lineEdit_FT_Amp.setText(formatNum(self.measSettings['ft_amplitude']))
        
    def setFT_Input(self):
        self.measSettings['ft_input'] = self.comboBox_FT_Input.currentIndex() + 1
        
    def setFT_Output(self):
        self.measSettings['ft_output'] = self.comboBox_FT_Output.currentIndex() + 1
        if self.measSettings['ft_output'] == 3:
            self.lineEdit_FT_Amp.setText('N/A')
            self.lineEdit_FT_Amp.setEnabled(False)
        else:
            self.lineEdit_FT_Amp.setEnabled(True)
            self.lineEdit_FT_Amp.setText(formatNum(self.measSettings['ft_amplitude']))
            
    def setF_Demod(self):
        self.measSettings['field_demod'] = self.comboBox_F_Demod.currentIndex() + 1
        
    def setF_Harmonic(self):
        self.measSettings['ft_harmonic'] = self.comboBox_F_Harmonic.currentIndex() + 1
        
    def setF_TC(self):
        val = readNum(str(self.lineEdit_F_TC.text()))
        if isinstance(val,float):
            self.measSettings['field_tc'] = val
        self.lineEdit_F_TC.setText(formatNum(self.measSettings['field_tc']))
        
    def setT_Demod(self):
        self.measSettings['temp_demod'] = self.comboBox_T_Demod.currentIndex() + 1
        
    def setT_Harmonic(self):
        self.measSettings['temp_harmonic'] = self.comboBox_T_Harmonic.currentIndex() + 1
        
    def setT_TC(self):
        val = readNum(str(self.lineEdit_T_TC.text()))
        if isinstance(val,float):
            self.measSettings['temp_tc'] = val
        self.lineEdit_T_TC.setText(formatNum(self.measSettings['temp_tc']))

    @inlineCallbacks
    def updateSimulation(self):
        try:
            #Waiting for one second seems to work fine for auto calculation to be complete
            yield self.sleep(1)
            #This method doesn't seem to work for anything other than an optimization
            #calculating = True
            #while calculating:
            #    calculating = yield self.hf.get_advisor_calc()
            #    print calculating
            #print 'done calaculating'
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