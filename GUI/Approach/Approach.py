'''
General Notes:

Everywhere with something I realized I wanted done, I wrote a comment starting with
TODO. Search for those for things to do :)

TODO test how the DAC responds to having a voltage prompted while it's ramping or buffer ramping

'''

import sys
from PyQt5 import QtGui, QtWidgets, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import numpy as np
from collections import deque
from nSOTScannerFormat import readNum, formatNum, printErrorInfo
import time
from traceback import format_exc

path = sys.path[0] + r"\Approach"
ApproachUI, QtBaseClass = uic.loadUiType(path + r"\Approach.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_generalApproachSettings, QtBaseClass = uic.loadUiType(path + r"\generalApproachSettings.ui")
Ui_MeasurementSettings, QtBaseClass = uic.loadUiType(path + r"\MeasurementSettings.ui")

class Window(QtWidgets.QMainWindow, ApproachUI):
    #initialize signals for new data to be plotted in the approach monitor window
    newPLLData = QtCore.pyqtSignal(float, float)
    newAux2Data = QtCore.pyqtSignal(float)
    newZData = QtCore.pyqtSignal(float)

    #initialize signals for telling scan module that we are in constant height or surface
    #feedback scanning mode
    updateFeedbackStatus = QtCore.pyqtSignal(bool)
    updateConstantHeightStatus = QtCore.pyqtSignal(bool)
    autowithdrawStatus = QtCore.pyqtSignal()

    def __init__(self, reactor, parent=None, coarse_output=None):
        super(Window, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        #setup UI elements that cannot be done through QT designer
        self.setupAdditionalUi()

        #move to default location
        self.moveDefault()

        #Connect GUI elements to appropriate methods

        #Referece to the coarse positioner ouput dictionary, check if an axis is enabled.
        if coarse_output is None:
            self.coarse_output_enabled = [True, True, True]
        else:
            self.coarse_output_enabled = coarse_output
        self.approach_type = "Advance" # or "Steps" for single steps (stepANC350)

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)

        #Connect measurement buttons

        self.push_StartControllers.clicked.connect(lambda: self.toggleControllers())
        #Connect advanced setting pop up menues
        self.push_MeasurementSettings.clicked.connect(self.showMeasurementSettings)
        self.push_GenSettings.clicked.connect(self.showGenSettings)

        #Connect GUI elements for updating the frequency threshold
        self.push_addFreq.clicked.connect(lambda: self.incrementFreqThresh())
        self.push_subFreq.clicked.connect(lambda: self.decrementFreqThresh())
        self.radioButton_plus.toggled.connect(lambda: self.setFreqThreshholdSign())
        self.lineEdit_freqSet.editingFinished.connect(self.setFreqThresh)
        self.freqSlider.logValueChanged.connect(self.updateFreqThresh)

        #Connect button and lineEdit for manual approach setting z extension
        self.push_setZExtension.clicked.connect(lambda: self.setZExtension())
        self.lineEdit_Man_Z_Extension.editingFinished.connect(self.set_man_z_extension)
        self.comboBox_ZMultiplier.currentIndexChanged.connect(self.setZMultiplier)

        #Connect lineEdits to update PID parameters
        self.lineEdit_P.editingFinished.connect(self.set_p)
        self.lineEdit_I.editingFinished.connect(self.set_i)
        self.lineEdit_D.editingFinished.connect(self.set_d)

        #Connect lineEdits to update constant height parameter for approach
        self.lineEdit_PID_Const_Height.editingFinished.connect(self.set_pid_const_height)
        self.push_PIDApproachForConstant.clicked.connect(lambda: self.startPIDConstantHeightApproachSequence())
        self.checkBox_autoThreshold.stateChanged.connect(self.setAutoThreshold)
        self.push_setPLLThresh.clicked.connect(lambda: self.setPLLThreshold())

        #Connect GUI elements for approach to maintain feedback with surface
        self.lineEdit_PID_Step_Size.editingFinished.connect(self.set_pid_step_size)
        self.lineEdit_PID_Step_Speed.editingFinished.connect(self.set_pid_step_speed)
        self.push_ApproachForFeedback.clicked.connect(lambda: self.startFeedbackApproachSequence())

        #Connect abort feedback button
        self.push_Abort.clicked.connect(lambda: self.abortApproachSequence())

        #Connect GUI elements for withdrawing
        self.push_Withdraw.clicked.connect(lambda: self.withdraw(self.withdrawDistance))
        self.lineEdit_Withdraw.editingFinished.connect(self.setWithdrawDistance)

        #Connect button setting the current extension as frustrated feedback in constant height mode
        self.push_frustrateFeedback.clicked.connect(lambda: self.setFrustratedFeedback())

        #Initialize all the labrad connections as not connected
        self.anc = False
        self.dac = False
        self.hf = False
        #self.dcbox = False

        #Initialization of various booleans used to keep track of the module status
        self.measuring = False         #Is the PLL measuring
        self.approaching = False       #Is the module approaching
        self.constantHeight = False    #Is the sensor in constant height mode
        self.voltageMultiplied = False #Is the voltage from the Zurich being multiplied down
        self.voltageMultiplier = 0.1   #Stores the Zurich voltage multiplier for scanning in feedback
        self.CPStepping = False        #Are coarse positioners are steppping
        self.withdrawing = False       #Is the tip in the process of being withdraw
        self.autoThresholding = True  #Is the software calculating the frequency threshold for the PID
        self.monitorZ = False          #Should the module monitor the Z voltage

        #intial withdraw distance
        self.withdrawDistance = 2e-6

        #Voltage being sent to Z of attocubes from the scanning DAC-ADC
        self.Atto_Z_Voltage = 0.0

        #Frequency threshold
        self.freqThreshold = 0.4

        #Height at which the previous approach made contact
        self.contactHeight = 0
        self.previous_contactHeight = 0
        #Initialize short arrays locally keeping track of the PLL frequency (deltaFdata)
        #and the z extension of the sensor (zData). These are used to determine
        #whether or not the tip is in contact with the surface.
        #deltafData is set to -200 (as opposed to zeros) because it's the smallest deltaF threshold that can be set.
        #This prevents accidental surface detections from happening
        self.deltaf_track_length = 100
        self.deltafData = deque([-200]*self.deltaf_track_length)

        self.z_track_length = 20
        self.zData = deque([-50e-9]*self.z_track_length)
        self.zTime = np.linspace(self.z_track_length, 1, self.z_track_length)

        '''
        Below is the initialization of all the default measurement settings.
        '''

        #PID Approach module all happens uses PID #1. This is easily changed if necessary in the future, but for now it's hard coded in
        self.PID_Index = 1

        self.measurementSettings = {
                'pll_input'           : 1,         #hf2li input that has the signal for the pll. Set in the DeviceSelect module.
                'pll_output'          : 1,         #hf2li output to be used to completel PLL loop. Set in the DeviceSelect module.
                'meas_pll'            : False,     #Keeps track of whether or not to measure the PLL when clicking `Start measurements'. False until a working point is sent from the TF characterizer module.
                'pll_targetBW'        : 100,       #Target bandwidth for the PID controlling the PLL determined by the PID advisor
                'pll_advisemode'      : 2,         #Sets the PID advisor mode. 0 is just proportional term, 1 just integral, 2 is prop + int, and 3 is full PID
                'pll_centerfreq'      : None,      #center frequency of the pll loop. Populated by the TF characterizer window
                'pll_phase_setpoint'  : None,      #phase setpoint of pll pid loop. Populated by the TF characterizer window
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
                'pll_output_amp'      : 0.001,     #AC excitation output amplitude on the tuning fork
                }

        '''
        Below is the initialization of all the default general approach settingss
        '''
        self.generalSettings = {
                'step_z_output'              : 1,     #output that goes to Z of attocubes from DAC ADC (1 indexed)
                'pid_z_output'               : 1,     #aux output that goes to Z of attocubes from HF2LI (1 indexed)
                'sumboard_toggle'            : 1,     #Output from the DC Box that toggles the summing amplifier (1 indexed)
                'z_mon_input'                : 1,     #Either 1 (aux in 1) or 2 (aux in 2) on the Zurich
                'coarse_positioner'          : 'Attocube ANC350', #Name of the type of coarse positioner being used. Set when connecting to LabRAD
                'step_retract_speed'         : 1e-5,  #speed in m/s when retracting
                'step_retract_time'          : 2.4,   #time required in seconds for full atto retraction
                'pid_retract_speed'          : 1e-5,  #speed in m/s when retracting
                'pid_retract_time'           : 2.4,   #time required in seconds for full atto retraction
                'total_retract_dist'         : 24e-6, #Maximum z extension of the z scanning attocubes in meters. Updated by the PositionCalibration module.
                'auto_retract_dist'          : 2e-6,  #distance in meters retracted in meters when a surface event is triggered in constant height mode
                'auto_retract_points'          : 3,   #points above frequency threshold before auto retraction is trigged
                'atto_distance'              : 6e-6,  #distance in meters to step forward with the coarse positioners. Determined by the resistive encoders
                'atto_delay'                 : 0.1,   #delay between steps.
                'atto_max_steps'             : 500, # The maximum number of steps to take per coarse positioner firing
                'atto_sample_after'          : 0, # each firing measure the caorse positioner after this many steps (letting it equilibrate)
                'atto_equilb_time'           : 30, # Wait this many seconds for the positioners to equilibrate before sampling the coarse positioner location
                'atto_nominal'               : 8e-6, # The nominal displacement to tell the ANC 350 to move curing approach.
        }

        '''
        Below is the initialization of all the default PID Approach Settings
        '''
        self.PIDApproachSettings = {
                'p'                    : 0,       #Proportional term of approach PID
                'i'                    : 1e-7,    #Integral term of approach PID
                'd'                    : 0,       #Derivative term of approach PID
                'step_size'            : 10e-9,   #Step size for feedback approach in meters
                'step_speed'           : 10e-9,   #Step speed for feedback approach in m/s
                'height'               : 5e-6,    #Height for constant height scanning
                'man z extension'      : 0, #Step size for manual approach in meters
                'zigzag safety'        : 200e-9, #Safety margin for the Zig Zag retraction
        }

        #Update GUI elements with the default values for the PID and approach settings
        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))
        self.lineEdit_PID_Step_Size.setText(formatNum(self.PIDApproachSettings['step_size']))
        self.lineEdit_PID_Step_Speed.setText(formatNum(self.PIDApproachSettings['step_speed']))
        self.lineEdit_PID_Const_Height.setText(formatNum(self.PIDApproachSettings['height']))

        self.lineEdit_Man_Z_Extension.setText(formatNum(self.PIDApproachSettings['man z extension']))

        self.lineEdit_freqSet.setText(formatNum(self.freqThreshold))
        self.freqSlider.setPosition(self.freqThreshold)

        #Lock the interface until servers are connected and buttons will work properly.
        self.lockInterface()

    def moveDefault(self):
        self.move(10,170)

    @inlineCallbacks
    def connectLabRAD(self, equip):
        '''
        Receives a dictionary from the DeviceSelect module instructing which hardware to use for what and which outputs to use on
        the specified hardware.
        '''
        try:
            #Create an asynchronous labrad connection to
            from labrad.wrappers import connectAsync
            cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')

            if "ANC350" in equip.servers:
                self.generalSettings['coarse_positioner'] = 'Attocube ANC350'
                self.anc = yield cxn.anc350_server
            else:
                print("'ANC350' not found, LabRAD connection to Appraoch Module Failed.")
                return

            #Connect to the Zurich HF2LI lock in
            if "HF2LI Lockin" in equip.servers:
                svr, ln, device_info, cnt, config = equip.servers["HF2LI Lockin"]
                self.hf = yield cxn.hf2li_server
                yield self.hf.select_device(device_info)

                self.generalSettings['pid_z_output'] = config['pid z out']
                self.generalSettings['sumboard_toggle'] = config['sum board toggle']
                self.generalSettings['z_mon_input'] = config['z monitor']
                self.measurementSettings['pll_input'] = config['pll input']
                self.measurementSettings['pll_output'] = config['pll output']
            else:
                print("'HF2LI Lockin' not found, LabRAD connection to Approach Module Failed.")
                return

            #Connect to the scanning DAC-ADC for z control
            if "Scan DAC" in equip.servers:
                svr, ln, device_info, cnt, config = equip.servers["Scan DAC"]

                #Similarly uses that extra connection so that we can talk to the scan dac at the same time as other dacs
                self.dac = yield cxn.dac_adc
                yield self.dac.select_device(device_info)

                self.generalSettings['step_z_output'] = config['z out']
            else:
                print("'Scan DAC' not found, LabRAD connection to Approach Module Failed.")
                return

            self.t0 = equip.sync_time
            self.last_touchdown_time = 0
            # Setup to save the data for approach debugging.
            self.dv = yield equip.get_datavault()
            file_info = yield self.dv.new("Approach log", ["Start Time (s)"], ["start Z", "end Z", "delta", "num steps"])
            dset = yield self.dv.current_identifier()
            # print("Approach Step Data Saving To:", dset)

            self.dvFileName = file_info[1]
            self.lineEdit_ImageNum.setText(file_info[1].split(" - ")[1]) # second string is unique identifier

            '''
            DC Box used to be used in some cases in conjunction with a summing amplifier.
            All references to it have been commented out pending proof that it is
            a necessary thing to do. Will likely use a DAC-ADC if it becomes useful
            again in the future.
            '''
            #Connect to the DC box to toggle the voltage multiplier board
            # self.dcbox = yield cxn.ad5764_dcbox
            # yield self.dcbox.select_device(dic['devices']['approach and TF']['dc_box'])

            #If we get here properly, make the servers connected square green indicating successfully connecting to LabRAD
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")

            #unlock the interface, but keep GUI elements for the PLL locked until a workingpoint is received from the
            #TF characterizer module
            self.unlockInterface()
            self.lockFreq()

            #This recovers settings from the hardware if the software crashed.
            yield self.loadCurrentState()

            #Start monitoring the Z voltage
            self.monitorZ = True
            self.monitorZVoltage()
        except:
            #Set the connected square to be red indicating that we failed to connect to LabRAD
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            printErrorInfo()

    @inlineCallbacks
    def loadCurrentState(self):
        '''
        Prompts the HF2LI for its settings, loading them up into the software. This enables smooth recovery
        from software crashes. Note, this function does NOT properly account for the voltage multiplier mode
        being anything other than 1.
        '''

        #Get approach PID values from the HF2LI
        P = yield self.hf.get_pid_p(self.PID_Index)
        I = yield self.hf.get_pid_i(self.PID_Index)
        D = yield self.hf.get_pid_d(self.PID_Index)

        #If PID parameters are the Zurich default (ie, the Zurich lock in was power cycled)
        #set to our default values. Otherwise, use the loaded values
        if P == 1.0 and I == 10.0:
            yield self.setPIDParameters()
        else:
            self.PIDApproachSettings['p'] = P/self.z_volts_to_meters
            self.PIDApproachSettings['i'] = I/self.z_volts_to_meters
            self.PIDApproachSettings['d'] = D/self.z_volts_to_meters
            self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))
            self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))
            self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))

        #Determine if either PLLs are on
        pll_on_1 = yield self.hf.get_pll_on(1)
        pll_on_2 = yield self.hf.get_pll_on(2)
        #Either one is on
        if pll_on_1 or pll_on_2:
            #Set 'meas_pll' to True
            self.measurementSettings['meas_pll'] = True

            #Set the pll_output to the appropriate PLL
            if pll_on_1:
                self.measurementSettings['pll_output'] = 1
            else:
                self.measurementSettings['pll_output'] = 2

            #Read and set in software the PLL center frequency, phase setpoint, excitation amplitude, and frequency range
            freq = yield self.hf.get_pll_freqcenter(self.measurementSettings['pll_output'])
            phase = yield self.hf.get_pll_setpoint(self.measurementSettings['pll_output'])
            amp_range = yield self.hf.get_output_range(self.measurementSettings['pll_output'])
            amp_frac = yield self.hf.get_output_amplitude(self.measurementSettings['pll_output'])
            freq_range = yield self.hf.get_pll_freqrange(self.measurementSettings['pll_output'])

            print('Amp range:', amp_range)
            print('Amp frac:', amp_frac)

            self.measurementSettings['pll_centerfreq'] = freq
            self.measurementSettings['pll_phase_setpoint'] = phase
            self.measurementSettings['pll_output_amp'] = amp_range*amp_frac #Output amplitude in the HF2LI is stored as the output range*fraction, instead of anything reasonable
            self.measurementSettings['pll_range'] = freq_range

            #read and set in software the PID values
            pll_p = yield self.hf.get_pll_p(self.measurementSettings['pll_output'])
            pll_i = yield self.hf.get_pll_i(self.measurementSettings['pll_output'])
            pll_d = yield self.hf.get_pll_d(self.measurementSettings['pll_output'])

            self.measurementSettings['pll_p'] = pll_p
            self.measurementSettings['pll_i'] = pll_i
            self.measurementSettings['pll_d'] = pll_d

            #read and set in software the pll input and harmonic
            pll_input = yield self.hf.get_pll_input(self.measurementSettings['pll_output'])
            pll_harmonic = yield self.hf.get_pll_harmonic(self.measurementSettings['pll_output'])

            self.measurementSettings['pll_input'] = int(pll_input)
            self.measurementSettings['pll_harmonic'] = int(pll_harmonic)

            #Read and set in software the pll tc, filter order, and filter bandwidth
            pll_tc = yield self.hf.get_pll_tc(self.measurementSettings['pll_output'])
            pll_filterorder = yield self.hf.get_pll_filterorder(self.measurementSettings['pll_output'])
            pll_filterBW = calculate_FilterBW(pll_filterorder, pll_tc)

            self.measurementSettings['pll_tc'] = pll_tc
            self.measurementSettings['pll_filterorder'] = pll_filterorder
            self.measurementSettings['pll_filterBW'] = pll_filterBW

            #Unlock frequency GUI elements
            self.unlockFreq()

            #Set the start measuring button to have the `on' graphics
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

            self.measuring = True #PLL is measuring is true
            self.push_MeasurementSettings.setEnabled(False) #Disable editting the measurement settings while measuring
            self.monitorPLL() #start monitoring the frequency

        #If the PID is on
        pid_on = yield self.hf.get_pid_on(self.PID_Index)
        if pid_on:
            #Get the frequency setpoint as deltaF from the center frequency
            setpoint = yield self.hf.get_pid_setpoint(self.PID_Index)

            delta_f = setpoint - self.measurementSettings['pll_centerfreq']

            #Set the sign of the deltaF button properly
            if delta_f >0:
                self.radioButton_plus.setChecked(True)
            else:
                self.radioButton_plus.setChecked(False)

            #update the frequency threshold in the software
            self.updateFreqThresh(abs(delta_f))

            #Emit that we're in constant height
            self.updateConstantHeightStatus.emit(True)
            self.constantHeight = True
            self.label_pidApproachStatus.setText('Constant Height')

        self.Atto_Z_Voltage = yield self.dac.read_dac_voltage(self.generalSettings['step_z_output'] - 1)

    def disconnectLabRAD(self):
        self.monitorZ = False #Makes sure to stop monitoring the Z voltage
        self.measuring = False # Stop measuring the PLL signal

        #Set all the servers to false since they are disconnected
        self.anc = False
        self.dac = False
        #self.dcbox = False
        self.hf = False

        #lock the interface when disconnected
        self.lockInterface()
        #Set the connected square to be red indicating that LabRAD is disconnected
        self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")

    def showServersList(self):
        #Open the list of servers that the module requires
        serList = serversList(self.reactor, self)
        serList.exec_()

    def showMeasurementSettings(self):
        '''
        Opens the measurement settings window, giving it the measurementSettings dictionary.
        If changes are accepted, then the measurement settings dictionary is updated with the
        new values.
        '''
        MeasSet = MeasurementSettings(self.reactor, self.measurementSettings.copy(), parent = self, server = self.hf)
        if MeasSet.exec_():
            self.measurementSettings = MeasSet.getValues()

    def showGenSettings(self):
        '''
        Opens the general settings window, giving it the generalSettings dictionary.
        If changes are accepted, then the general settings dictionary is updated with the
        new values.
        '''
        GenSet = generalApproachSettings(self.reactor, self.generalSettings, parent = self, type=self.approach_type)
        if GenSet.exec_():
            self.generalSettings = GenSet.getValues()

    def setupAdditionalUi(self):
        #replace the placeholder freqSlider with a custom log scale slider
        self.freqSlider.close()
        self.freqSlider = MySlider(parent = self.centralwidget)
        self.freqSlider.setGeometry(120,100,260,70)
        self.freqSlider.setMinimum(0)
        self.freqSlider.setMaximum(1000000)
        self.freqSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.freqSlider.setTickPos([0.008, 0.01, 0.02, 0.04,0.06, 0.08, 0.1,0.2,0.4,0.6, 0.8,1, 2, 4, 6, 8, 10, 20, 40, 60, 80, 100, 200])
        self.freqSlider.setNumPos([0.01, 0.1,1,10, 100])
        self.freqSlider.lower()

    def set_voltage_calibration(self, calibration):
        '''
        Update the scanning piezo position to voltage calibration when received from the PositionCalibration module.
        '''
        #This module only moves in the z direction, so only those are populated
        self.z_volts_to_meters = float(calibration[3])
        self.z_meters_max = float(calibration[6])
        self.z_volts_max = float(calibration[9])

        #Relevant values in the generalSettings dictionary are also updated
        self.generalSettings['total_retract_dist'] = self.z_meters_max
        self.generalSettings['pid_retract_time'] = self.z_meters_max / self.generalSettings['pid_retract_speed']
        self.generalSettings['step_retract_time'] = self.z_meters_max / self.generalSettings['step_retract_speed']

        #If the HF2LI server is connected, update the PID parameters (since these are stated in units of meters,
        #updating the calibration requires changing the value of the values in the HF2LI)
        if self.hf != False:
            self.setPIDParameters()

    def setWorkingPoint(self, freq, phase, out, amp):
        #Function called when the working point is set from a signal emitted by the tuning fork characterization module
        #By default, whatever output amplitude was used by the TF characterizer is used here as well (though it can be
        #change from the measurementSettings window)
        self.measurementSettings['pll_centerfreq'] = freq
        self.measurementSettings['pll_phase_setpoint'] = phase
        self.measurementSettings['pll_output'] = out
        self.measurementSettings['pll_output_amp'] = amp

        self.measurementSettings['meas_pll'] = True
        self.unlockFreq()

#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section connects actions related to updating GUI elements in the main module."""

    def set_p(self):
        #Read the P parameter from the lineEdit and set it
        val = readNum(str(self.lineEdit_P.text()), self, True)
        if isinstance(val,float):
            self.PIDApproachSettings['p'] = val
            self.setPIDParameters()
        self.lineEdit_P.setText(formatNum(self.PIDApproachSettings['p']))

    def set_i(self):
        #Read the I parameter from the lineEdit and set it
        #note that i can never be set to 0, otherwise the hidden integrator value jumps back to 0
        #which can lead to dangerous voltage spikes to the attocube.
        val = readNum(str(self.lineEdit_I.text()), self, True)
        if isinstance(val,float):
            if np.abs(val)> 1e-30:
                self.PIDApproachSettings['i'] = val
                self.setPIDParameters()
        self.lineEdit_I.setText(formatNum(self.PIDApproachSettings['i']))

    def set_d(self):
        #Read the D parameter from the lineEdit and set it
        val = readNum(str(self.lineEdit_D.text()), self, True)
        if isinstance(val,float):
            self.PIDApproachSettings['d'] = val
            self.setPIDParameters()
        self.lineEdit_D.setText(formatNum(self.PIDApproachSettings['d']))

    def set_pid_const_height(self, val = None):
        #Set the constant height parameter. If there's an input, so to that value. Otherwise
        #read from the lineEdit.
        if val is None:
            val = readNum(str(self.lineEdit_PID_Const_Height.text()), self, True)
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > self.generalSettings['total_retract_dist']:
                val = self.generalSettings['total_retract_dist']
            self.PIDApproachSettings['height'] = val
        self.lineEdit_PID_Const_Height.setText(formatNum(self.PIDApproachSettings['height']))

    def set_pid_step_size(self):
        #Read the step size parameter from the lineEdit and set it
        val = readNum(str(self.lineEdit_PID_Step_Size.text()), self, True)
        if isinstance(val,float):
            self.PIDApproachSettings['step_size'] = val
        self.lineEdit_PID_Step_Size.setText(formatNum(self.PIDApproachSettings['step_size']))

    def set_pid_step_speed(self):
        #Read the step speed parameter from the lineEdit and set it
        val = readNum(str(self.lineEdit_PID_Step_Speed.text()), self, True)
        if isinstance(val,float):
            self.PIDApproachSettings['step_speed'] = val
        self.lineEdit_PID_Step_Speed.setText(formatNum(self.PIDApproachSettings['step_speed']))

    def set_man_z_extension(self):
        #Read the desired z extension from the lineEdit and set it
        val = readNum(str(self.lineEdit_Man_Z_Extension.text()), self, True)
        if isinstance(val,float):
            self.PIDApproachSettings['man z extension'] = val
        self.lineEdit_Man_Z_Extension.setText(formatNum(self.PIDApproachSettings['man z extension'],5))

    @inlineCallbacks
    def updateFreqThresh(self, value = 0):
        #Update the frequency threshold to the provided value by setting the slider position, updating the text in the lineEdit,
        #and actually setting the threshold on the Zurich PID
        try:
            self.freqThreshold = value
            self.lineEdit_freqSet.setText(formatNum(self.freqThreshold))
            self.freqSlider.setPosition(self.freqThreshold)
            yield self.setFreqThreshholdSign()
        except:
            printErrorInfo()

    @inlineCallbacks
    def setFreqThreshholdSign(self):
        #Set the frequency threshold taking into account the sign determined by the radioButtons. Radio buttons are
        #necessary only because the slider is log scale, which is nice for viewing a wide range of values for deltaFthresh.
        #One could imagine having a linear slider and simplifying this a little
        if self.measurementSettings['pll_centerfreq'] is not None and not self.withdrawing:
            if self.radioButton_plus.isChecked():
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] + self.freqThreshold)
            else:
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] - self.freqThreshold)

    @inlineCallbacks
    def setFreqThresh(self):
        #Set the frequency threshold when set by changing the value in the lineEdit
        val = readNum(str(self.lineEdit_freqSet.text()))
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
        #Increment the frequency threshold when the `+' is clicked
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
        #Decrement the frequency threshold when the `+- is clicked
        if self.radioButton_plus.isChecked():
            val = self.freqThreshold * 0.99
        else:
            val = self.freqThreshold * 1.01

        if val < 0.008:
            val = 0.008
        elif val > 200:
            val = 200

        yield self.updateFreqThresh(value = val)

    def setWithdrawDistance(self):
        #Read the withdraw distance parameter from the lineEdit and set it
        val = readNum(str(self.lineEdit_Withdraw.text()), self, True)
        if isinstance(val,float):
            if val < 0:
                val = 0
            elif val > self.generalSettings['total_retract_dist']:
                val = self.generalSettings['total_retract_dist']
            self.withdrawDistance = val
        self.lineEdit_Withdraw.setText(formatNum(self.withdrawDistance))

    def setZMultiplier(self):
        #Update the Z voltage multiplier values for a feedback approach
        if self.comboBox_ZMultiplier.currentIndex() == 0:
            self.voltageMultiplier = 1
        elif self.comboBox_ZMultiplier.currentIndex() == 1:
            self.voltageMultiplier = 0.4
        elif self.comboBox_ZMultiplier.currentIndex() == 2:
            self.voltageMultiplier = 0.1

    def setAutoThreshold(self):
        #Update auto thresholding parameters with the checkbox in the module
        self.autoThresholding = self.checkBox_autoThreshold.isChecked()

#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section connects actions related to toggling measurements."""

    @inlineCallbacks
    def toggleControllers(self):
        #Originally, we considered approaching on various signals in addition to the PLL. These have since been removed.
        #The structure of the function was to enable toggling measuring multiple `controllers' for the approach.
        #Approaching with the PLL worked well enough, that it's the only one left.
        try:
            #Do not allow measurement of the controllers to be toggled while approaching
            if not self.approaching:
                #If not measuring, measure
                if not self.measuring:
                    #Update button graphics
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
                    #Don't allow measurement settings to be changed while measuring
                    self.push_MeasurementSettings.setEnabled(False)
                    #If measuring with the PLL is ready
                    if self.measurementSettings['meas_pll']:
                        #Set the PLL settings
                        yield self.setHF2LI_PLL_Settings()
                        #Monitor frequency
                        self.monitorPLL()
                #If measuring, stop measuring
                else:
                    #Update button graphics
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
                    #Allow measurement settings to be changed while not measuring
                    self.push_MeasurementSettings.setEnabled(True)

                    #Wait 100ms for frequency measurement loop to stop running after self.measuring is set to False
                    yield self.sleep(0.1)
                    #Then update the button indicating whether or not the PLL is locked
                    self.push_Locked.setStyleSheet("""#push_Locked{
                            background: rgb(161, 0, 0);
                            border-radius: 5px;
                            }""")

                    #Turn the approaching PID off (which should already be off, but you can never be too safe!)
                    yield self.hf.set_pid_on(self.PID_Index, False)
            else:
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setIcon(QtWidgets.QMessageBox.Information)
                msgBox.setWindowTitle('Measurements Necessary')
                msgBox.setText("\r\n You cannot stop measuring mid-approach. Safely abort the approach before stopping the measurements.")
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()
        except:
            printErrorInfo()

    @inlineCallbacks
    def setHF2LI_PLL_Settings(self):
        '''Sets all the required settings for the PLL on the HF2LI without turning on the PLL'''
        if self.hf is None:
            print("HF2LI server not connected")
            return
        try:
            #first disable autoSettings
            yield self.hf.set_pll_autocenter(self.measurementSettings['pll_output'],False)
            yield self.hf.set_pll_autotc(self.measurementSettings['pll_output'],False)
            yield self.hf.set_pll_autopid(self.measurementSettings['pll_output'],False)

            #set the PLL input, center frequency, phase setpoint, frequency range, harmonic, tc and filter order
            yield self.hf.set_pll_input(self.measurementSettings['pll_output'],self.measurementSettings['pll_input'])
            yield self.hf.set_pll_freqcenter(self.measurementSettings['pll_output'], self.measurementSettings['pll_centerfreq'])
            yield self.hf.set_pll_setpoint(self.measurementSettings['pll_output'],self.measurementSettings['pll_phase_setpoint'])
            yield self.hf.set_pll_freqrange(self.measurementSettings['pll_output'],self.measurementSettings['pll_range'])
            yield self.hf.set_pll_harmonic(self.measurementSettings['pll_output'],self.measurementSettings['pll_harmonic'])
            yield self.hf.set_pll_tc(self.measurementSettings['pll_output'],self.measurementSettings['pll_tc'])
            yield self.hf.set_pll_filterorder(self.measurementSettings['pll_output'],self.measurementSettings['pll_filterorder'])

            #set the PLL pid values
            yield self.hf.set_pll_p(self.measurementSettings['pll_output'],self.measurementSettings['pll_p'])
            yield self.hf.set_pll_i(self.measurementSettings['pll_output'],self.measurementSettings['pll_i'])
            yield self.hf.set_pll_d(self.measurementSettings['pll_output'],self.measurementSettings['pll_d'])

            #Sets the output amplitude for the PLL AC output. the HF2LI has its output amplitude set by changing the output range,
            #then setting the amplitude as a fraction of that range.
            yield self.hf.set_output_range(self.measurementSettings['pll_output'],self.measurementSettings['pll_output_amp'])
            output_range = yield self.hf.get_output_range(self.measurementSettings['pll_output'])
            yield self.hf.set_output_amplitude(self.measurementSettings['pll_output'],self.measurementSettings['pll_output_amp']/output_range)
        except:
            printErrorInfo()

    @inlineCallbacks
    def monitorPLL(self):
        '''Starts the loop that monitors the resonant frequency measured by the PLL.'''
        try:
            #Turn on output and start PLL
            yield self.hf.set_output(self.measurementSettings['pll_output'], True)
            yield self.hf.set_pll_on(self.measurementSettings['pll_output'])

            #Whenever restarting the PLL and its measurement, reset deltaFdata
            #(which is used to determine whether or not the surface has been contacted)
            self.deltafData = deque([-200]*self.deltaf_track_length)

            while self.measuring:
                #Each loop while measuring reads the deltaf, phaseError, and lock status of the PLL
                try:
                    deltaf = yield self.hf.get_pll_freqdelta(self.measurementSettings['pll_output'])
                    phaseError = yield self.hf.get_pll_error(self.measurementSettings['pll_output'])
                    locked = yield self.hf.get_pll_lock(self.measurementSettings['pll_output'])

                    #Update the lineedits
                    self.lineEdit_freqCurr.setText(formatNum(deltaf))
                    self.lineEdit_phaseError.setText(formatNum(phaseError))

                    #Update the PLL locked graphic
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

                    #Emit PLL data point (to the Approach Monitor module)
                    self.newPLLData.emit(deltaf, phaseError)
                except labrad.RuntimeError: # Error communicating with the Zurich, register as a bad point in deltaf
                    deltaf = -20
                    phaseError = 0
                    print("Error communicating with Zurich")
                    print(format_exc())

                #Add frequency data to deltaf list only if not stepping with the coarse positioners\
                #The steps are rough enough that they cause spikes in the PLL that should not be used
                #to determine if the surface has been contacted
                if not self.CPStepping:
                    self.deltafData.appendleft(deltaf)
                    self.deltafData.pop()

                #If the module is in constant heigh mode
                if self.constantHeight:
                    #Track the number of points in the last 200 points that are above the frequency threshold
                    points_above_freq_thresh = 0
                    for f in self.deltafData:
                        if self.radioButton_plus.isChecked():
                            points_above_freq_thresh = points_above_freq_thresh + (f > self.freqThreshold)
                        else:
                            points_above_freq_thresh = points_above_freq_thresh + (f > (-1.0*self.freqThreshold))

                    #If the number of points is large enough, auto retract to safeguard the tip
                    if points_above_freq_thresh >= self.generalSettings['auto_retract_points']:
                        print('auto withdrew')
                        yield self.withdraw(self.generalSettings['auto_retract_dist']) #withdrawing takes the module out of constantHeight mode
                        self.autowithdrawStatus.emit()

            #When done measuring, turn off the PLL and the output
            yield self.hf.set_pll_off(self.measurementSettings['pll_output'])
            yield self.hf.set_output(self.measurementSettings['pll_output'], False)
        except:
            printErrorInfo()

    @inlineCallbacks
    def monitorZVoltage(self):
        #Sleep 2 seconds before starting monitoring to allow everything else to start up properly
        yield self.sleep(2)
        while self.monitorZ:
            try:
                #Reads a copy of the voltage going to the Z attocube scanner
                #This is the sum of the Zurich voltage output (times the multiplier)
                #and the DAC-ADC Z voltage output
                z_voltage = yield self.hf.get_aux_input_value(self.generalSettings['z_mon_input'])

                #Update the progress bar if z_voltage > 0 (small ofsets can sometimes make it less than 0)
                if z_voltage >= 0:
                    self.progressBar.setValue(int(1000.0*(z_voltage/self.z_volts_max)))
                    self.progressBar.update()
                else:
                    self.progressBar.setValue(0)
                    self.progressBar.update()

                #Update the value of the z extension
                z_meters = z_voltage / self.z_volts_to_meters
                self.lineEdit_FineZ.setText(formatNum(z_meters, 3))
                #Emit a new Z datapoint for the approach monitoring module
                self.newZData.emit(z_meters)

                #Keep track of the zData for surface contact determination
                self.zData.appendleft(z_meters)
                self.zData.pop()

                #Also monitor the other aux input in case anything useful is hooked up to it
                try:
                    aux2_voltage = yield self.hf.get_aux_input_value(self.generalSettings['z_mon_input']%2+1)
                    self.newAux2Data.emit(aux2_voltage)
                except:
                    print("Error reading aux2 voltage")

                #Wait 100ms before going through the loop again
                yield self.sleep(0.1)
            except:
                yield self.sleep(0.1)
                printErrorInfo()

#--------------------------------------------------------------------------------------------------------------------------#
    """ The following section contains the PID approach sequence and all related functions."""

    @inlineCallbacks
    def abortApproachSequence(self):
        self.approaching = False
        #Turn off PID (just does nothing if it's already off)
        yield self.hf.set_pid_on(self.PID_Index, False)
        print("Aborting the Approach")
        self.label_pidApproachStatus.setText('Idle - Aborted')

    @inlineCallbacks
    def startPIDApproachSequence(self):
        '''
        Starts a PID approach sequence. Once contact with the surface has been made, the function is done.
        This function is called either as part of the Constant Height PID approach, or Feedback PID Approach
        functions, which handle what happens after the surface has been contacted.

        TODO: think about zeroing the Z dac voltage before running this for 1 to 1 function. But also
        keep in mind the fact that, while scanning and moving around on a plane, we want to be able to
        touchdown with this sequence (which would require not zeroing it).
        '''
        try:
            if self.measuring: #If measuring the PLL
                self.approaching = True

                #Set PID off for initialization
                yield self.hf.set_pid_on(self.PID_Index, False)

                #Update status label
                self.label_pidApproachStatus.setText('Approaching with Zurich')

                #Initializes all the PID settings
                yield self.setHF2LI_PID_Settings()

                #Set the output range to be 0 to the max z voltage, which is specified by the temperature of operation from the PositionCalibration module
                yield self.setPIDOutputRange(self.z_volts_max)

                #Reset the zData and deltaFdata arrays. This prevents the software from thinking it hit the surface because of
                #the approach prior to the coarse positioners setpping
                self.zData = deque([-50e-9]*self.z_track_length)
                self.deltafData = deque([-200]*self.deltaf_track_length)

                #Disable to setPLL threshold button until the queue of deltafdata has been replenished. Spamming the set threshhold
                #button after starting an approach will yield spurradic results until the initalized values are gone
                self.disableSetThreshold(30)

                #Turn on PID to start the approach
                yield self.hf.set_pid_on(self.PID_Index, True)

                while self.approaching:
                    #Check if the surface has been contacted.
                    if self.madeSurfaceContact():
                        #If so, update the status and break from the loop
                        self.label_pidApproachStatus.setText('Surface contacted')
                        break

                    #Check if we maxed out the output voltage

                    #Get the output voltage of the HF2LI (this is JUST the HF2LI voltage output not, not the sum with the DAC-ADC z voltage contribution)
                    z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

                    #If the voltage is at the maximum (or within a milliVolt)
                    if z_voltage >= (self.z_volts_max - 0.001) and self.approaching:
                        #Stop the PID
                        yield self.hf.set_pid_on(self.PID_Index, False)

                        #Retract the sensor by setting the value of the PID's integrator to 0
                        self.label_pidApproachStatus.setText('Retracting Attocubes')
                        #Find desired retract speed in volts per second
                        retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                        yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)

                        #If still approaching step forward with the coarse positioners
                        if self.approaching:
                            yield self.stepCoarsePositioners()

                        #If approaching and autoThresholding, then wait for 30 seconds before resetting the PLL threshold
                        if self.approaching and self.autoThresholding:
                            self.label_pidApproachStatus.setText('Collecting data for threshold.')
                            #Wait for 30 seconds for  self.zData and self.deltaFdata to get new values
                            # Can incorporate the time the coarse positioner was equilibrating if applicable
                            if self.generalSettings['atto_equilb_time'] > 0 and self.approach_type != "Steps" :
                                dt = 30 - self.generalSettings['atto_equilb_time']
                                if dt > 0:
                                    yield self.sleep(dt)
                            else:
                                yield self.sleep(30)
                            yield self.setPLLThreshold()
                        else:
                            #Reset the zData and deltaFdata arrays. This prevents the software from thinking it hit the surface because of
                            #the approach prior to the coarse positioners setpping
                            self.zData = deque([-50e-9]*self.z_track_length)
                            self.deltafData = deque([-200]*self.deltaf_track_length)

                        if self.approaching:
                            #Turn PID back on and continue approaching
                            yield self.hf.set_pid_on(self.PID_Index, True)
                            self.label_pidApproachStatus.setText('Approaching with Zurich')

            else: #If not measuring the PLL, throw a warning
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setIcon(QtWidgets.QMessageBox.Information)
                msgBox.setWindowTitle('Start PLL to Approach')
                msgBox.setText("\r\n You cannot approach until the PLL has been started.")
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()
        except:
            print("Gen PID Approach Error:")
            printErrorInfo()

    @inlineCallbacks
    def setHF2LI_PID_Settings(self):
        try:
            #PID Approach module all happens on PID #1. Easily changed if necessary in the future (or toggleable). But for now it's
            #hard coded in (initialized at start)

            #Set PID parameters
            yield self.setPIDParameters()
            #Sets the output signal type to be an auxiliary output offset
            yield self.hf.set_pid_output_signal(self.PID_Index, 3)
            #Sets the correct channel of the aux output
            yield self.hf.set_pid_output_channel(self.PID_Index, self.generalSettings['pid_z_output'])

            #Sets the PID input signal to be an oscillator frequency
            yield self.hf.set_pid_input_signal(self.PID_Index, 10)
            #Sets the oscillator frequency to be the same as the one for which the PLL is running
            yield self.hf.set_pid_input_channel(self.PID_Index, self.measurementSettings['pll_output'])

            #Set the setpoint, noting whether it should be plus or minus as specified in the GUI
            if self.radioButton_plus.isChecked():
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] + self.freqThreshold)
            else:
                yield self.hf.set_pid_setpoint(self.PID_Index, self.measurementSettings['pll_centerfreq'] - self.freqThreshold)
        except:
            print("Set PID settings error")
            printErrorInfo()

    @inlineCallbacks
    def setPIDParameters(self):
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
        except:
            print("PID errror:")
            printErrorInfo()

    @inlineCallbacks
    def setPIDOutputRange(self, max_voltage):
        if max_voltage >= 0:
            #Set the output range to be 0 to 'max' V.
            yield self.hf.set_pid_output_center(self.PID_Index, float(max_voltage)/2)
            yield self.hf.set_pid_output_range(self.PID_Index, float(max_voltage)/2)
            if max_voltage == 0:
                print('Warning, frustrated feedback output range is zero.')
            returnValue(True)
        else:
            #If for some reason trying to go into the negative voltages, at least withdraw as far as possible with the Zurich
            print('Settings output range to be negative!')
            retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters / self.voltageMultiplier
            yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)
            returnValue(False)

    @inlineCallbacks
    def disableSetThreshold(self, time):
        #Disable the set threshold button for the specified amount of time in seconds
        self.push_setPLLThresh.setEnabled(False)
        yield self.sleep(time)
        self.push_setPLLThresh.setEnabled(True)

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
            print('Surface contact made with points above frequency threshhold algorithm.')
            return True

        #The second algorith fits a line to the past 20 z positions. If the slope of the line is less than 0
        #then presume we made contact.
        slope, offset = np.polyfit(self.zTime, self.zData, 1)
        # Sometimes a small negative value on ADC when fully retracted will cause it to detect contact even when fully retracted
        # stalling out an approach sequency. Require that there be at leat 50 nm extension before this algorithm triggerens
        mn = np.mean(self.zData)
        if slope < -1e-10 and mn > 50e-9:
            print('Surface contact made with negative z slope algorithm with slope: ', slope)
            return True

        return False

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

        try:
            #Lock GUI elements that could mess up this function if they are editted while withdrawing
            self.lockWithdrawSensitiveInputs()
            if curr_val is None:
                curr_val = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

            #Only allow withdrawing, ie, lowering the voltage
            if 0 <= val and val <= curr_val:
                #Get the HF2LI device ID in order to be able to do latency minimizing commands
                dev_ID = yield self.hf.list_devices()
                dev_ID = dev_ID[0][1]

                #Calculate center and range to withdraw exactly desired amount
                center = (curr_val - val)/2 + val
                vrange = (curr_val - val)/2

                #Make sure the pid is off when setting up the integrator changing
                yield self.hf.set_pid_on(self.PID_Index, False)

                #The input signal (aux output 4), is always left as 0 Volt output.
                #This means that the rate at which the voltage changes is this setpoint (-'speed') times the integrator
                #value (1 /s). So, this changes the voltage at a rate of 'speed' V/s.
                settings = [['/%s/pids/%d/center' % (dev_ID, self.PID_Index-1), str(center)], #set the center of the pid range
                            ['/%s/pids/%d/range' % (dev_ID, self.PID_Index-1), str(vrange)], #set the magnitude of the pid range
                            ['/%s/pids/%d/input' % (dev_ID, self.PID_Index-1), '5'], #set the input signal of the PID to be aux outputs
                            ['/%s/pids/%d/inputchannel' % (dev_ID, self.PID_Index-1), '3'], #set the signal to be aux output 4 (4-1 = 3 since zero indexed)
                            ['/%s/pids/%d/p' % (dev_ID, self.PID_Index-1), '0'], #Set p = 0
                            ['/%s/pids/%d/i' % (dev_ID, self.PID_Index-1), '1'], #set i = 1
                            ['/%s/pids/%d/d' % (dev_ID, self.PID_Index-1), '0'], #set d = 0
                            ['/%s/auxouts/%d/outputselect' % (dev_ID, 4-1), '-1'], #Set aux out 4 to manual mode so that it's value is locked to 0
                            ['/%s/pids/%d/setpoint' % (dev_ID, self.PID_Index-1),str(-speed)]] #set setpoint to -speed

                #Next two inputs set the PID output to be the aux output with the right channel. Probably not necessary
                #Following can be added back in if necessary
                # ['/%s/pids/%d/output' % (dev_ID, self.PID_Index-1), '3'],
                # ['/%s/pids/%d/outputchannel' % (dev_ID, self.PID_Index-1), str(self.generalSettings['pid_z_output']-1)]
                # print(settings)
                yield self.hf.set_settings(settings)

                #Turn on PID
                yield self.hf.set_pid_on(self.PID_Index, True)

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

            #Unlock the sensitive GUI elements
            self.unlockWithdrawSensitiveInputs()
        except:
            printErrorInfo()

    @inlineCallbacks
    def stepCoarsePositioners(self):
        #Programmed with this structure back when we have multiple coarse positioner options.
        if self.generalSettings['coarse_positioner'] == 'Attocube ANC350':
            if self.coarse_output_enabled[2]:
                if self.approach_type == "Steps":
                    yield self.stepANC350()
                else:
                    yield self.advanceANC350() #self.stepANC350()
            else:
                print("Z Coarse Positioner Disabled, Ending Approach Sequence")
                self.approaching = False


    @inlineCallbacks
    def advanceANC350(self):
        '''
        A modified version of stepANC350 that uses the ANC 350 internal closed loop instead of
        calling a number of single steps. This ensures that pulses are actually being fired at the nominal
        frequency.
        '''
        #Set module to coarse positioners are stepping
        self.CPStepping = True
        self.label_pidApproachStatus.setText('Stepping with ANC350')

        start_time = time.time()-self.t0

        #Assume axis 3 is the z axis. Set the output to be on, and to turn off automatically when end of travel is reached
        yield self.anc.set_axis_output(2, True, True)

        #Get the starting position in z before stepping
        sum = 0
        for i in range(10): # Encoders can be noisy, Average over 1s
            z = yield self.anc.get_position(2)
            sum += z
            yield self.sleep(0.1)
        pos_start = sum/10
        if pos_start < 0e-6:
            yield self.abortApproachSequence()
            return

        freq =  yield self.anc.get_frequency(2)
        # Time to wait for a given number of pulses to fire, in seconds
        wait_time = self.generalSettings['atto_sample_after']/freq

        num_steps = 0
        delta = 0
        while delta < self.generalSettings['atto_distance'] and self.approaching:
            if num_steps >= self.generalSettings['atto_max_steps']:
                print("Reached Maximum number of steps")
                break

            #Give axis number and direction (False forward, True is backwards)
            try:
                self.label_pidApproachStatus.setText('Firing Positioners')
                yield self.anc.set_target_position(2, self.generalSettings['atto_nominal'])
                yield self.anc.start_auto_move(2, True, True) # Start auto movement
                # Wait a certain amount of time for all the pulses to fire, then check
                t0 = time.time()
                t1 = t0
                while t1-t0 < wait_time:
                    yield self.sleep(self.generalSettings['atto_delay'])
                    if not self.approaching: # Check for aborts
                        break
                    t1 = time.time()
                yield self.anc.start_auto_move(2, False, True) # Stop auto move
                num_steps += (t1-t0)*freq
            except:
                print("Error could not move with ANC 350, turning off output")
                yield self.anc.start_auto_move(2, False, True) # Stop auto move
                printErrorInfo()
            # Equilibrate then measure
            self.label_pidApproachStatus.setText('Equilibrating Encoders')
            for i in range(int(self.generalSettings['atto_equilb_time'])):
                if not self.approaching:
                    break
                yield self.sleep(1)
            sum = 0
            for i in range(10): # Encoders can be noisy, Average over 1s
                z = yield self.anc.get_position(2)
                sum += z
                yield self.sleep(0.1)
            pos_curr = sum/10

            delta = pos_curr - pos_start
            # print(pos_start, pos_curr, num_steps, delta) # For debugging
            if pos_curr < 50e-6:
                yield self.abortApproachSequence()
                break
            self.label_pidApproachStatus.setText('Stepping with ANC350')

        print("Moving a distance of " + str(delta) + " took " + str(num_steps) + " steps.")
        self.dv.add(start_time, pos_start, pos_curr, num_steps, delta)

        #Once done, set coarse positioners stepping to be false
        self.CPStepping = False


    @inlineCallbacks
    def stepANC350(self):
        #Set module to coarse positioners are stepping
        self.CPStepping = True
        self.label_pidApproachStatus.setText('Stepping with ANC350')

        #Assume axis 3 is the z axis. Set the output to be on, and to turn off automatically when end of travel is reached
        yield self.anc.set_axis_output(2, True, True)

        #Get the starting position in z before stepping
        pos_start = yield self.anc.get_position(2)
        num_steps = 0
        delta = 0
        while delta < self.generalSettings['atto_distance'] and self.approaching:
            #Give axis number and direction (False forward, True is backwards)
            yield self.anc.start_single_step(2, False)
            #Wait for the positioners to settle before reading their position
            yield self.sleep(self.generalSettings['atto_delay'])
            pos_curr = yield self.anc.get_position(2)
            if pos_curr < 50e-6:
                yield self.abortApproachSequence()
                break
            delta = pos_curr - pos_start
            num_steps += 1
        print("Moving a distance of " + str(delta) + " took " + str(num_steps) + " steps.")
        self.dv.add(time.time()-self.t0, pos_start, pos_curr, num_steps, delta)

        #Once done, set coarse positioners stepping to be false
        self.CPStepping = False

    @inlineCallbacks
    def stepANC350_Alternate(self):
        '''
        An alternate version of stepANC350 that works more like advanceANC350 but uses single steps
        '''
        #Set module to coarse positioners are stepping
        self.CPStepping = True
        self.label_pidApproachStatus.setText('Stepping with ANC350')

        start_time = time.time()-self.t0

        #Assume axis 3 is the z axis. Set the output to be on, and to turn off automatically when end of travel is reached
        yield self.anc.set_axis_output(2, True, True)

        #Get the starting position in z before stepping
        pos_start = yield self.anc.get_position(2)
        if pos_start < 0e-6:
            yield self.abortApproachSequence()
            return

        num_steps = 0
        sub_steps = 0
        delta = 0
        while delta < self.generalSettings['atto_distance'] and self.approaching:
            if num_steps >= self.generalSettings['atto_max_steps']:
                print("Reached Maximum number of steps")
                break
            #Give axis number and direction (False forward, True is backwards)
            yield self.anc.start_single_step(2, False)
            #Wait for the positioners to settle before reading their position
            yield self.sleep(self.generalSettings['atto_delay'])
            pos_curr = yield self.anc.get_position(2)
            if pos_curr < 50e-6:
                yield self.abortApproachSequence()
                break

            # After a certain number of steps, equilibrate then sample to make sure you aren't overshot
            sub_steps += 1
            if self.generalSettings['atto_sample_after'] > 0 and sub_steps >= self.generalSettings['atto_sample_after']:
                for i in range(int(self.generalSettings['atto_equilb_time'])):
                    if not self.approaching:
                        break
                    yield self.sleep(1)
                pos_curr = yield self.anc.get_position(2)
                sub_steps = 0

            delta = pos_curr - pos_start
            num_steps += 1

        # After done let positioners equilibrate and measure how far you went
        # Don't measure if you just equilibrated/measured last iteration
        if self.generalSettings['atto_equilb_time'] > 0 and sub_steps != 0:
            for i in range(int(self.generalSettings['atto_equilb_time'])):
                if not self.approaching:
                    break
                yield self.sleep(1)
            pos_curr = yield self.anc.get_position(2)
            delta = pos_curr - pos_start
        print("Moving a distance of " + str(delta) + " took " + str(num_steps) + " steps.")
        self.dv.add(start_time, pos_start, pos_curr, num_steps, delta)

        #Once done, set coarse positioners stepping to be false
        self.CPStepping = False

    @inlineCallbacks
    def setPLLThreshold(self):
        #Find the mean and standard deviation of the data that exists
        #This should just be the mean and std of the past 100 data points taken
        mean = np.mean(self.deltafData)
        std = np.std(self.deltafData)

        current_time = time.time()-self.t0
        # If 30 seconds has not passed since the last touchdown show a warning.
        if current_time - self.last_touchdown_time < 30:
            msgBox = QtWidgets.QMessageBox(self)
            msgBox.setIcon(QtWidgets.QMessageBox.Information)
            msgBox.setWindowTitle('Warning')
            msgBox.setText("\r\n Cannot set PLL threshold less than 30 seconds after a touchdown.")
            msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
            msgBox.exec_()
            return

        print("Mean and standard deviation of past 100 points: ", mean, std)

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

        print("New threshold determined by 4 std above the mean: ", new_thresh)

        yield self.updateFreqThresh(value = new_thresh)

    @inlineCallbacks
    def setZExtension(self):
        '''Sets the Z extension from the Zurich. Does not take into account the DACADC
        voltage'''

        #Turn off PID for initialization
        yield self.hf.set_pid_on(self.PID_Index, False)
        #Make sure voltage isn't multiplied
        yield self.resetVoltageMultiplier()

        #Gets the current z extension
        z_voltage = yield self.hf.get_aux_input_value(self.generalSettings['z_mon_input'])
        z_meters = z_voltage / self.z_volts_to_meters

        #If current z extension is greater than the desired extension, withdraw
        delta = z_meters - self.PIDApproachSettings['man z extension']
        if delta > 0:
            #Eventually have it withdraw the proper amount
            yield self.withdraw(delta)
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
    def startPIDConstantHeightApproachSequence(self):
        try:
            #First emit signal saying we are no longer in contact with the surface, either at constant height
            #for feedback
            self.updateConstantHeightStatus.emit(False)
            self.constantHeight = False
            self.updateFeedbackStatus.emit(False)

            #Makes sure we're not in a divded voltage mode
            yield self.resetVoltageMultiplier()

            #Bring us to the surface
            yield self.startPIDApproachSequence()

            if self.approaching:
                #Read the voltage being output by the PID
                self.previous_contactHeight = self.contactHeight
                z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

                self.contactHeight = z_voltage / self.z_volts_to_meters

                #Determine voltage to which we want to retract to be at the provided constant height
                end_voltage = z_voltage - self.PIDApproachSettings['height'] * self.z_volts_to_meters
                #Find desired retract speed in volts per second
                retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                #Go to the position. The PID will be turned off by calling the set integrator command
                yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)

                #Set range such that maximally extended is at the proper distance from the surface.
                #result is true if we successfully set the range.
                #returns false otherwise, meaning that we made contact with the sample
                #too close to be able to set the range properly
                result = yield self.setPIDOutputRange(end_voltage)
                self.last_touchdown_time = time.time()-self.t0
                # Print out the current surface hight, round to nearest second and nm for easy computation
                print('time, surface height, creep:', round(self.last_touchdown_time), round(self.contactHeight/1e-6, 3), round((self.previous_contactHeight-self.contactHeight)/1e-6, 3))

                if result:
                    #Turn PID back on so that if there's drift or the sample is taller than expected,
                    #the PID will retract the tip
                    yield self.hf.set_pid_on(self.PID_Index, True)

                    #Reset the deltaFdata arrays. This prevents the software from interpreting the surface contact from approach
                    #as an accidental contact resulting in autowithdrawl in the zmonitoring loop.
                    self.deltafData = deque([-200]*self.deltaf_track_length)

                    #Emit that we can now scan in constant height mode
                    self.updateConstantHeightStatus.emit(True)
                    self.constantHeight = True
                    self.label_pidApproachStatus.setText('Constant Height')
                    self.approaching = False
                else:
                    self.label_pidApproachStatus.setText('Could not extend to desired height')
                    self.approaching = False

        except:
            printErrorInfo()

    @inlineCallbacks
    def LimitedApproachSequence(self, max_extension_volts):
        '''
        Starts a PID approach sequence to advance a limited distance given by max_extension_volts.
        If surface contact has been made function returns 0.
        If the function reaches max_extension it returns 1.
        If the function reaches the maximum possible extension and does not find the surface, it retracts
        completely and returns -1, indicating the Approach failed. Does not advance the course positioners.
        '''
        try:
            if self.measuring: #If measuring the PLL

                #Set PID off for initialization
                yield self.hf.set_pid_on(self.PID_Index, False)

                #Update status label
                self.label_pidApproachStatus.setText('Approaching with Zurich')

                #Initializes all the PID settings
                yield self.setHF2LI_PID_Settings()

                #Set the output range to be 0 to the max z voltage, which is specified by the temperature of operation from the PositionCalibration module
                yield self.setPIDOutputRange(self.z_volts_max)

                z_volts_max_extend = min([max_extension_volts, self.z_volts_max]) # Don't extend past the maximum.

                #Reset the zData and deltaFdata arrays. This prevents the software from thinking it hit the surface because of
                #the approach prior before extension.
                self.zData = deque([-50e-9]*self.z_track_length)
                self.deltafData = deque([-200]*self.deltaf_track_length)

                #Disable to setPLL threshold button until the queue of deltafdata has been replenished. Spamming the set threshhold
                #button after starting an approach will yield spurradic results until the initalized values are gone
                self.disableSetThreshold(30)

                if not self.approaching: # For safety
                    return -1

                #Turn on PID to start the approach
                yield self.hf.set_pid_on(self.PID_Index, True)

                while self.approaching:
                    #Check if the surface has been contacted.
                    if self.madeSurfaceContact():
                        #If so, update the status and break from the loop
                        self.label_pidApproachStatus.setText('Surface contacted')
                        return 0

                    #Check if we maxed out the output voltage

                    #Get the output voltage of the HF2LI (this is JUST the HF2LI voltage output not, not the sum with the DAC-ADC z voltage contribution)
                    z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

                    #If the voltage is at the maximum possible (or within a milliVolt)
                    if z_voltage >= (self.z_volts_max - 0.001) and self.approaching:
                        print("Surface not found, retracting attocubes.")
                        #Stop the PID
                        yield self.hf.set_pid_on(self.PID_Index, False)

                        #Retract the sensor by setting the value of the PID's integrator to 0
                        self.label_pidApproachStatus.setText('Retracting Attocubes')
                        #Find desired retract speed in volts per second
                        retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                        yield self.setHF2LI_PID_Integrator(val = 0, speed = retract_speed)


                        #Reset the zData and deltaFdata arrays. This prevents the software from thinking it hit the surface because of
                        #the approach prior to retraction
                        self.zData = deque([-50e-9]*self.z_track_length)
                        self.deltafData = deque([-200]*self.deltaf_track_length)
                        return -1
                    elif z_voltage >= z_volts_max_extend and self.approaching:
                        #Reset the zData and deltaFdata arrays. This prevents the software from thinking it hit the surface because of
                        #the approach prior to retraction
                        self.zData = deque([-50e-9]*self.z_track_length)
                        self.deltafData = deque([-200]*self.deltaf_track_length)

                        return 1
            else: #If not measuring the PLL, throw a warning
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setIcon(QtWidgets.QMessageBox.Information)
                msgBox.setWindowTitle('Start PLL to Approach')
                msgBox.setText("\r\n You cannot approach until the PLL has been started.")
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()
            return -1 # Error
        except:
            print("Gen PID Approach Error:")
            printErrorInfo()
            return -1 # Error

    @inlineCallbacks
    def startZigZagApproach(self, advance_dist, pullback_dist):
        '''
        Move towards the surface using a "zig-zag" pattern where you advance a short amount, then retract
        in series with a positive trend, until you hit the surface.

        Once surface contact is made the tip will pull back 100nm quickly as a safety measure. It will
        then reverse the Zig Zag pattern, pulling back by advance_dist then approaching by pullback_dist
        until the desired height is reached.

        pullback_dist should be less than advance_dist, won't exxecute otherwise.
        '''
        try:
            if pullback_dist >= advance_dist:
                print("Error pullback distance needs to be less than advance distance. Cannot ZigZag.")
                return
            #First emit signal saying we are no longer in contact with the surface, either at constant height
            #for feedback
            self.updateConstantHeightStatus.emit(False)
            self.constantHeight = False
            self.updateFeedbackStatus.emit(False)

            #Makes sure we're not in a divded voltage mode
            yield self.resetVoltageMultiplier()

            #Bring us to the surface
            self.approaching = True
            while self.approaching:
                # Advance a step
                z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
                state = yield self.LimitedApproachSequence(z_voltage + advance_dist * self.z_volts_to_meters)
                if state == 0 and self.approaching: # Hit the surface, zigzag back then enter constant heigh mode
                    #Read the voltage being output by the PID
                    z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

                    self.contactHeight = z_voltage / self.z_volts_to_meters

                    #Determine voltage to which we want to retract to be at the provided constant height
                    zzretract_done = False
                    final_voltage = z_voltage - self.PIDApproachSettings['height'] * self.z_volts_to_meters
                    if self.PIDApproachSettings['height'] < self.PIDApproachSettings['zigzag safety']:
                        end_voltage = final_voltage
                        zzretract_done = True
                    else:
                        end_voltage = z_voltage - self.PIDApproachSettings['zigzag safety'] * self.z_volts_to_meters

                    #Find desired retract speed in volts per second
                    retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                    #Go to the position. The PID will be turned off by calling the set integrator command
                    yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)

                    # Do a Zig-Zag retraction
                    retract_speed = 0.1*self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                    while not zzretract_done:
                        z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
                        end_voltage = z_voltage - advance_dist * self.z_volts_to_meters
                        if end_voltage <= final_voltage:
                            end_voltage = final_voltage
                            zzretract_done = True
                            print("Zig Zag Finished, retracting to desired height")

                        #Go to the position. The PID will be turned off by calling the set integrator command
                        yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)

                        # Move foreward by pullback_dist
                        if not zzretract_done:
                            z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
                            state = yield self.LimitedApproachSequence(z_voltage + pullback_dist * self.z_volts_to_meters)
                            if state != 1:
                                self.approaching = False
                                print("Error in zigzag retract. LimitedApproachSequence returned with state", state)
                                print("Retracting to desired height for safety.")
                                retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                                yield self.setHF2LI_PID_Integrator(val = final_voltage, speed = retract_speed)
                                zzretract_done = True

                    #Set range such that maximally extended is at the proper distance from the surface.
                    #result is true if we successfully set the range.
                    #returns false otherwise, meaning that we made contact with the sample
                    #too close to be able to set the range properly
                    result = yield self.setPIDOutputRange(end_voltage)

                    if result:
                        #Turn PID back on so that if there's drift or the sample is taller than expected,
                        #the PID will retract the tip
                        yield self.hf.set_pid_on(self.PID_Index, True)

                        #Reset the deltaFdata arrays. This prevents the software from interpreting the surface contact from approach
                        #as an accidental contact resulting in autowithdrawl in the zmonitoring loop.
                        self.deltafData = deque([-200]*self.deltaf_track_length)

                        #Emit that we can now scan in constant height mode
                        self.updateConstantHeightStatus.emit(True)
                        self.constantHeight = True
                        self.label_pidApproachStatus.setText('Constant Height')
                    else:
                        self.label_pidApproachStatus.setText('Could not extend to desired height')
                    self.approaching = False
                elif state == 1 and self.approaching: # Advanced, didn't hit surface. Pullback the given amount.
                    #Read the voltage being output by the PID
                    z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])

                    #Determine voltage to which we want to retract to be at the provided constant height
                    end_voltage = z_voltage - pullback_dist * self.z_volts_to_meters
                    end_voltage = max(end_voltage, 0) # Don't try and go negative
                    #Retract at 1/10th the normal speed.
                    retract_speed = 0.1*self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters
                    #Go to the position. The PID will be turned off by calling the set integrator command
                    yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed)
                else: # Otherwise something went wrong, stop appraoching
                    self.label_pidApproachStatus.setText('Could not ZigZag to surface.')
                    self.approaching = False
        except:
            printErrorInfo()

    @inlineCallbacks
    def resetVoltageMultiplier(self):
        #Function makes sure that the voltage multiplier is set to 1
        if self.voltageMultiplied == True:
            #Withdraw completely before switching to multiplier of 1
            yield self.withdraw(self.z_meters_max)
            #yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 0)
            self.voltageMultiplied = False

    @inlineCallbacks
    def startFeedbackApproachSequence(self):
        try:
            '''
            This function assumes that we are already within the DAC extension range of the surface.  It was written a long
            time ago and has not been tested in forever. Do not trust!
            '''

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

            #Read voltage from just the DAC-ADC
            self.Atto_Z_Voltage = yield self.dac.read_dac_voltage(self.generalSettings['step_z_output'] - 1)

            #If the voltage is not yet in the multiplied mode and it needs to be,
            #then we need to withdraw fully to do so safely
            if not self.voltageMultiplied and self.voltageMultiplier < 1:
                #Withdraw fully. This zeros both the Zurich and DAC voltage.
                yield self.withdraw(self.z_meters_max)

            #If the voltage is multiplied, but needs to not be, then we also
            #need to withdraw
            if self.voltageMultiplied and self.voltageMultiplier == 1:
                #Withdraw fully. This zeros both the Zurich and DAC voltage.
                yield self.withdraw(self.z_meters_max)

            #start PID approach sequence
            self.approaching = True

            if self.approaching:
                #Make sure the PID is off
                yield self.hf.set_pid_on(self.PID_Index, False)

                '''
                Note all references to the DC Box commented out below, until we
                know if the summing amplifier is needed.
                '''
                #If the multiplier is less than one, toggle the sum board
                if self.voltageMultiplier < 1 and not self.voltageMultiplied:
                    #The choice between 0.4 and 0.1 is done through selecting a different sum box. Make sure
                    #the selected option matches the hardware
                    # yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 2.5)
                    self.voltageMultiplied = True
                elif self.voltageMultiplier == 1 and self.voltageMultiplied:
                    #yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 0)
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
                            # yield self.dcbox.set_voltage(self.generalSettings['sumboard_toggle']-1, 0)
                            self.voltageMultiplied = False

                            self.approaching = False
                            break

                        #Take a step forward as specified by the stepwise approach advanced settings
                        speed = self.PIDApproachSettings['step_speed']*self.z_volts_to_meters
                        yield self.setDAC_Voltage(start_voltage, end_voltage, speed)

                    self.approaching = False
                    self.comboBox_ZMultiplier.setEnabled(True)
                except:
                    print("Feedback Sequence 2 error:")
                    printErrorInfo()
        except:
            print("Feedback Sequence error:")
            printErrorInfo()

    @inlineCallbacks
    def setDAC_Voltage(self, start, end, speed):
        '''
        Smoothly ramps between two voltage points at the desired speed provided in volts/s
        '''
        if float(start) != float(end) and end >=0:
            #points required to make smooth ramp of 300 microvolt steps (the limit of 16 bit dac)
            points = np.abs(int((start-end) / (300e-6)))
            #delay in microseconds between each point to get the right speed
            delay = int(300 / speed)

            yield self.dac.ramp1(self.generalSettings['step_z_output'] - 1, float(start), float(end), points, delay)
            #This sleep step is necessary because the ramp1 command on the DAC-ADCs is bad. It returns a value signaling
            #that the ramp is done. But, if the ramp takes longer than the serial communuication timeout of ~1s, then
            #it times out before finishing. In an asynchronous environment, this risks other commands being sent to the
            #DAC while it is rampiing unless we deliberate call the following sleep command.
            yield self.sleep(points * delay / 1e6)
            self.Atto_Z_Voltage = float(end)

            #If ramp1 times out, then the buffer doesn't get cleared properly and it needs to be done here
            #This occurs if the ramp time is ~1s or greater.
            if points * delay / 1e6 > 0.9:
                a = yield self.dac.read()
                while a != '':
                    a = yield self.dac.read()

    @inlineCallbacks
    def withdraw(self, dist):
        '''
        The z extension on the scanner piezos comes from a sum of an output voltage
        of the zurich HF2LI and the DAC-ADC. The withdraw function starts by
        withdrawing by ramping down the Zurich voltage, then, if the required
        distance has not been withdrawn, continues by ramping down the DAC-ADCs
        voltage
        '''
        try:
            #Signal that we are no longer approaching
            self.approaching = False

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
            # dac_z_value = yield self.dac.read_dac_voltage(self.generalSettings['step_z_output'] - 1)
            # if isinstance(dac_z_value,float):
            #     self.Atto_Z_Voltage = dac_z_value

            #update labels on the GUI
            self.label_pidApproachStatus.setText('Withdrawing')

            #Keep track of how much distance still needs to be withdrawn after each step
            withdrawDistance = dist

            #if the zurich voltage is non zero
            if z_voltage >= 0.001:
                #Find desired end voltage of the zurich
                end_voltage = z_voltage - withdrawDistance * self.z_volts_to_meters
                if self.voltageMultiplied:
                    end_voltage = z_voltage - withdrawDistance * self.z_volts_to_meters/self.voltageMultiplier

                #If we need to withdraw by more than just the voltage from the Zurich, keep track of how much
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

                #Get the desired retract speed in volts per second
                retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters

                #If output voltage is being multiplied down, divide the speed by the down multiplication factor
                if self.voltageMultiplied:
                    retract_speed = retract_speed/self.voltageMultiplier

                yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed, curr_val = z_voltage)

            #If there's a voltage from the scanning DAC-ADC and we still need to withdraw to reach the withdraw distance goal
            print('WithdrawDistance and Atto_Z_Voltage are:') #ADDED FOR DEBUGGING
            print(withdrawDistance) #ADDED FOR DEBUGGING
            print(self.Atto_Z_Voltage) #ADDED FOR DEBUGGING
            if self.Atto_Z_Voltage > 0 and withdrawDistance > 0:
                start_voltage = self.Atto_Z_Voltage
                end_voltage = self.Atto_Z_Voltage - withdrawDistance * self.z_volts_to_meters

                if end_voltage < 0:
                    end_voltage = 0
                    #distance being withdrawn by DAC
                    withdrawDistance = start_voltage / self.z_volts_to_meters

                #speed in volts / second
                speed = self.generalSettings['step_retract_speed']*self.z_volts_to_meters
                yield self.setDAC_Voltage(start_voltage, end_voltage, speed)

            #The voltage from the DAC-ADC can be negative resulting from tilt corrections on the scan module.
            #If the overall voltage on the piezos is negative for an extended period of time, this can damage them.
            #If there's an overall negative voltage bias on the piezos, zero it.
            z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
            if z_voltage + self.Atto_Z_Voltage < 0:
                #speed in volts / second
                speed = self.generalSettings['step_retract_speed']*self.z_volts_to_meters
                yield self.setDAC_Voltage(self.Atto_Z_Voltage, -z_voltage, speed)

            self.push_Withdraw.setEnabled(True)
            self.push_ApproachForFeedback.setEnabled(True)
            self.push_PIDApproachForConstant.setEnabled(True)

            self.label_pidApproachStatus.setText('Idle - Withdrawn')
        except:
            printErrorInfo()

    @inlineCallbacks
    def emergency_withdraw(self, dist):
        '''
        The z extension on the scanner piezos comes from a sum of an output voltage
        of the zurich HF2LI and the DAC-ADC. The withdraw function starts by
        withdrawing by ramping down the Zurich voltage, then, if the required
        distance has not been withdrawn, continues by ramping down the DAC-ADCs
        voltage
        '''
        try:
            #Signal that we are no longer approaching
            self.approaching = False

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
            # self.Atto_Z_Voltage = dac_z_value

            #update labels on the GUI
            self.label_pidApproachStatus.setText('Withdrawing')

            #Keep track of how much distance still needs to be withdrawn after each step
            withdrawDistance = dist

            #if the zurich voltage is non zero
            if z_voltage >= 0.001:
                #Find desired end voltage of the zurich
                end_voltage = z_voltage - withdrawDistance * self.z_volts_to_meters
                if self.voltageMultiplied:
                    end_voltage = z_voltage - withdrawDistance * self.z_volts_to_meters/self.voltageMultiplier

                #If we need to withdraw by more than just the voltage from the Zurich, keep track of how much
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

                #Get the desired retract speed in volts per second
                retract_speed = self.generalSettings['pid_retract_speed'] * self.z_volts_to_meters

                #If output voltage is being multiplied down, divide the speed by the down multiplication factor
                if self.voltageMultiplied:
                    retract_speed = retract_speed/self.voltageMultiplier

                yield self.setHF2LI_PID_Integrator(val = end_voltage, speed = retract_speed, curr_val = z_voltage)

            #If there's a voltage from the scanning DAC-ADC and we still need to withdraw to reach the withdraw distance goal
            print('WithdrawDistance and Atto_Z_Voltage are:') #ADDED FOR DEBUGGING
            print(withdrawDistance) #ADDED FOR DEBUGGING
            print(self.Atto_Z_Voltage) #ADDED FOR DEBUGGING
            if self.Atto_Z_Voltage > 0 and withdrawDistance > 0:
                start_voltage = self.Atto_Z_Voltage
                end_voltage = self.Atto_Z_Voltage - withdrawDistance * self.z_volts_to_meters

                if end_voltage < 0:
                    end_voltage = 0
                    #distance being withdrawn by DAC
                    withdrawDistance = start_voltage / self.z_volts_to_meters

                #speed in volts / second
                speed = self.generalSettings['step_retract_speed']*self.z_volts_to_meters
                yield self.setDAC_Voltage(start_voltage, end_voltage, speed)

            #The voltage from the DAC-ADC can be negative resulting from tilt corrections on the scan module.
            #If the overall voltage on the piezos is negative for an extended period of time, this can damage them.
            #If there's an overall negative voltage bias on the piezos, zero it.
            z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
            if z_voltage + self.Atto_Z_Voltage < 0:
                #speed in volts / second
                speed = self.generalSettings['step_retract_speed']*self.z_volts_to_meters
                yield self.setDAC_Voltage(self.Atto_Z_Voltage, -z_voltage, speed)

            self.push_Withdraw.setEnabled(True)
            self.push_ApproachForFeedback.setEnabled(True)
            self.push_PIDApproachForConstant.setEnabled(True)

            self.label_pidApproachStatus.setText('Idle - Withdrawn')
        except:
            printErrorInfo()


    @inlineCallbacks
    def initializePID(self):
        '''
        Deprecated Function: kept around in case it's useful.

        This function ensures the integrator value of the PID is set such that the starting output voltage is 0 volts.
        By default, when the range is from 0 to 3 V, the starting output voltage is 1.5V; this fixes that problem.
        Also sets the output range from 0 to z_volts_max, which is the temperature dependent voltage range.

        09/02/2019 I cannot reproduce the starting output voltage being the center. It appears now that the voltage
        stays the same if possible when changing the PID center and range. I don't know how this would have been addressed
        given that no firmware update has been pushed. Anyways, this function is now no longer being called. I'm leaving it
        in the code in case it becomes relevant in the future.
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
        except:
            printErrorInfo()

    @inlineCallbacks
    def zeroHF2LI_Aux_Out(self):
        '''
        Deprecated Function: kept around in case it's useful.
        This function zeros all of the HF2LI aux outputs.
        '''
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

        except:
            printErrorInfo()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""

    def setApproachSettings(distance=None, stepdelay=None, maxsteps=None, sampleafter=None, equilbtime=None):
        '''
        Change the general approach settings
        '''
        if isinstance(distance,float):
            self.generalApproachSettings['atto_distance'] = distance
        if isinstance(stepdelay,float):
            self.generalApproachSettings['atto_delay'] = stepdelay
        if isinstance(maxsteps,float):
            self.generalApproachSettings['atto_max_steps'] = maxsteps
        if isinstance(sampleafter,float):
            self.generalApproachSettings['atto_sample_after'] = sampleafter
        if isinstance(equilbtime,float):
            self.generalApproachSettings['atto_equilb_time'] = equilbtime

    def setHeight(self, height):
        #Set the height to be withdrawn after surface contact with a constant height PID approach
        self.set_pid_const_height(height)

    @inlineCallbacks
    def approachConstHeight(self):
        #Approach for constant height with PID
        yield self.startPIDConstantHeightApproachSequence()

    def getContactPosition(self):
        #Get the z extension of the previous surface contact
        return self.contactHeight

    @inlineCallbacks
    def setFrustratedFeedback(self):
        '''
        Turns on the PLL and PID with frustrated feedback at the current z extension.
        '''
        #Turn off PID for initialization
        yield self.hf.set_pid_on(self.PID_Index, False)

        #Gets the current z extension
        z_voltage = yield self.hf.get_aux_output_value(self.generalSettings['pid_z_output'])
        #z_meters = z_voltage / self.z_volts_to_meters

        #Initializes all the PID settings
        yield self.setHF2LI_PID_Settings()

        #Set the output range to be 0 to the current z voltage
        success = yield self.setPIDOutputRange(z_voltage)

        if success:
            #Turn on PID to start the approach
            yield self.hf.set_pid_on(self.PID_Index, True)

            #Emit signal allowing for constant height scanning
            self.constantHeight = True
            self.updateConstantHeightStatus.emit(True)
            self.label_pidApproachStatus.setText('Constant Height')
        else:
            self.label_pidApproachStatus.setText('Frustrating Error')

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def lockInterface(self):
        #Renders it impossible to interact with all the GUI elements in the main module
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

        self.push_frustrateFeedback.setDisabled(True)

        self.lineEdit_Withdraw.setDisabled(True)

        self.lineEdit_FineZ.setDisabled(True)
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
        #Locks the GUI elements for changing PLL / PID frequency threshhold
        self.lineEdit_freqSet.setDisabled(True)
        self.freqSlider.setEnabled(False)
        self.radioButton_plus.setEnabled(False)
        self.radioButton_minus.setEnabled(False)

    def lockWithdrawSensitiveInputs(self):
        #Locks all GUI elements that should't be changed while withdrawing
        self.lockFreq()
        self.lineEdit_P.setDisabled(True)
        self.lineEdit_I.setDisabled(True)
        self.lineEdit_D.setDisabled(True)
        self.push_setPLLThresh.setDisabled(True)
        self.push_addFreq.setDisabled(True)
        self.push_subFreq.setDisabled(True)

    def unlockInterface(self):
        #Unlocks everything
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

        self.push_frustrateFeedback.setDisabled(False)

        self.lineEdit_Withdraw.setDisabled(False)

        self.lineEdit_FineZ.setDisabled(False)
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
        #Unlocks frequency GUI elements
        self.lineEdit_freqSet.setDisabled(False)
        self.freqSlider.setEnabled(True)
        self.radioButton_plus.setEnabled(True)
        self.radioButton_minus.setEnabled(True)

    def unlockWithdrawSensitiveInputs(self):
        #Unlocks withdraw sensitive GUI elements
        if self.measurementSettings['meas_pll']:
            self.unlockFreq()
        self.lineEdit_P.setDisabled(False)
        self.lineEdit_I.setDisabled(False)
        self.lineEdit_D.setDisabled(False)
        self.push_setPLLThresh.setDisabled(False)
        self.push_addFreq.setDisabled(False)
        self.push_subFreq.setDisabled(False)

    def updateScanningStatus(self, status):
        if status:
            self.label_pidApproachStatus.setText('Scanning')
        else:
            self.label_pidApproachStatus.setText('Idle - Scan Ended')

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)

class generalApproachSettings(QtWidgets.QDialog, Ui_generalApproachSettings):
    def __init__(self, reactor, settings, parent = None, type=None):
        super(generalApproachSettings, self).__init__(parent)
        self.setupUi(self)

        self.generalApproachSettings = settings

        #Connect all the GUI elements
        self.pushButton.clicked.connect(self.acceptNewValues)

        self.lineEdit_Step_Retract_Speed.editingFinished.connect(self.setStep_Retract_Speed)
        self.lineEdit_Step_Retract_Time.editingFinished.connect(self.setStep_Retract_Time)

        self.lineEdit_PID_Retract_Speed.editingFinished.connect(self.setPID_Retract_Speed)
        self.lineEdit_PID_Retract_Time.editingFinished.connect(self.setPID_Retract_Time)

        self.lineEdit_AutoRetractDist.editingFinished.connect(self.setAutoRetractDist)
        self.lineEdit_AutoRetractPoints.editingFinished.connect(self.setAutoRetractPoints)

        self.lineEdit_Atto_Distance.editingFinished.connect(self.setAttoDist)
        self.lineEdit_Atto_Delay.editingFinished.connect(self.setAttoDelay)

        if type == "Steps":
            self.lineEdit_Atto_MaxSteps.setHidden(True)
            self.lineEdit_Atto_SampleSteps.setHidden(True)
            self.lineEdit_Atto_Equilib.setHidden(True)
            self.lineEdit_Atto_Nominal.setHidden(True)
        else:
            self.lineEdit_Atto_MaxSteps.editingFinished.connect(self.setAttoMaxSteps)
            self.lineEdit_Atto_SampleSteps.editingFinished.connect(self.setAttoSampleAfter)
            self.lineEdit_Atto_Equilib.editingFinished.connect(self.setAttoEquilib)
            self.lineEdit_Atto_Nominal.editingFinished.connect(self.setAttoNominal)

        #Display the loaded input settings into the GUI
        self.loadValues()

    def loadValues(self):
        #Update each lineEdit with the values specified by the input settings
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))

        self.lineEdit_AutoRetractDist.setText(formatNum(self.generalApproachSettings['auto_retract_dist']))
        self.lineEdit_AutoRetractPoints.setText(formatNum(self.generalApproachSettings['auto_retract_points']))

        self.lineEdit_Atto_Distance.setText(formatNum(self.generalApproachSettings['atto_distance']))
        self.lineEdit_Atto_Delay.setText(formatNum(self.generalApproachSettings['atto_delay']))
        self.lineEdit_Atto_Nominal.setText(formatNum(self.generalApproachSettings['atto_nominal']))

        self.lineEdit_Atto_MaxSteps.setText(formatNum(self.generalApproachSettings['atto_max_steps']))
        self.lineEdit_Atto_SampleSteps.setText(formatNum(self.generalApproachSettings['atto_sample_after']))
        self.lineEdit_Atto_Equilib.setText(formatNum(self.generalApproachSettings['atto_equilb_time']))

    def setAttoMaxSteps(self):
        val = readNum(str(self.lineEdit_Atto_MaxSteps.text()))
        if isinstance(val,float):
            self.generalApproachSettings['atto_max_steps'] = val
        self.lineEdit_Atto_MaxSteps.setText(formatNum(self.generalApproachSettings['atto_max_steps']))

    def setAttoSampleAfter(self):
        val = readNum(str(self.lineEdit_Atto_SampleSteps.text()))
        if isinstance(val,float):
            self.generalApproachSettings['atto_sample_after'] = val
        self.lineEdit_Atto_SampleSteps.setText(formatNum(self.generalApproachSettings['atto_sample_after']))

    def setAttoEquilib(self):
        val = readNum(str(self.lineEdit_Atto_Equilib.text()))
        if isinstance(val,float):
            self.generalApproachSettings['atto_equilb_time'] = val
        self.lineEdit_Atto_Equilib.setText(formatNum(self.generalApproachSettings['atto_equilb_time']))

    def setStep_Retract_Speed(self):
        #Set the retracting speed in m/s when withdrawing with the DAC-ADC
        val = readNum(str(self.lineEdit_Step_Retract_Speed.text()), self, True)
        if isinstance(val,float):
            self.generalApproachSettings['step_retract_speed'] = val
            self.generalApproachSettings['step_retract_time'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['step_retract_speed']
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))

    def setStep_Retract_Time(self):
        #Set the time in seconds to fully retract from full extension when withdrawing with the DAC-ADC
        val = readNum(str(self.lineEdit_Step_Retract_Time.text()))
        if isinstance(val,float):
            self.generalApproachSettings['step_retract_time'] = val
            self.generalApproachSettings['step_retract_speed'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['step_retract_time']
        self.lineEdit_Step_Retract_Speed.setText(formatNum(self.generalApproachSettings['step_retract_speed']))
        self.lineEdit_Step_Retract_Time.setText(formatNum(self.generalApproachSettings['step_retract_time']))

    def setPID_Retract_Speed(self):
        #Set the retracting speed in m/s when withdrawing with the DAC-ADC
        val = readNum(str(self.lineEdit_PID_Retract_Speed.text()), self, True)
        if isinstance(val,float):
            self.generalApproachSettings['pid_retract_speed'] = val
            self.generalApproachSettings['pid_retract_time'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['pid_retract_speed']
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))

    def setPID_Retract_Time(self):
        #Set the time in seconds to fully retract from full extension when withdrawing with the HF2LI
        val = readNum(str(self.lineEdit_PID_Retract_Time.text()))
        if isinstance(val,float):
            self.generalApproachSettings['pid_retract_time'] = val
            self.generalApproachSettings['pid_retract_speed'] = self.generalApproachSettings['total_retract_dist'] / self.generalApproachSettings['pid_retract_time']
        self.lineEdit_PID_Retract_Speed.setText(formatNum(self.generalApproachSettings['pid_retract_speed']))
        self.lineEdit_PID_Retract_Time.setText(formatNum(self.generalApproachSettings['pid_retract_time']))

    def setAutoRetractDist(self):
        #Set the distance to auto retract when the frequency monitor notices an event while in constant height mode
        val = readNum(str(self.lineEdit_AutoRetractDist.text()), self, True)
        if isinstance(val,float):
            self.generalApproachSettings['auto_retract_dist'] = val
        self.lineEdit_AutoRetractDist.setText(formatNum(self.generalApproachSettings['auto_retract_dist']))

    def setAutoRetractPoints(self):
        #Set the number of PLL points that neeed to be above the set frequency threshold to trigger an auto retraction event
        val = readNum(str(self.lineEdit_AutoRetractPoints.text()))
        if isinstance(val,float):
            self.generalApproachSettings['auto_retract_points'] = int(val)
        self.lineEdit_AutoRetractPoints.setText(formatNum(self.generalApproachSettings['auto_retract_points']))

    def setAttoDist(self):
        #Set the distance in meters that the attocube `coarse positioners attempt to move forward at each step of the woodpecker approach
        val = readNum(str(self.lineEdit_Atto_Distance.text()))
        if isinstance(val,float):
            self.generalApproachSettings['atto_distance'] = val
        self.lineEdit_Atto_Distance.setText(formatNum(self.generalApproachSettings['atto_distance']))

    def setAttoDelay(self):
        #Set the delay time between steps taken by the attocube coarse positioners
        val = readNum(str(self.lineEdit_Atto_Delay.text()))
        if isinstance(val,float):
            self.generalApproachSettings['atto_delay'] = val
        self.lineEdit_Atto_Delay.setText(formatNum(self.generalApproachSettings['atto_delay']))

    def setAttoNominal(self):
        #Set the noninal ANC 350 Displacement
        val = readNum(str(self.lineEdit_Atto_Nominal.text()))
        if isinstance(val,float):
            self.generalApproachSettings['atto_nominal'] = val
        self.lineEdit_Atto_Nominal.setText(formatNum(self.generalApproachSettings['atto_nominal']))

    def acceptNewValues(self):
        self.accept()

    def getValues(self):
        return self.generalApproachSettings

class MeasurementSettings(QtWidgets.QDialog, Ui_MeasurementSettings):
    def __init__(self,reactor, measSettings, parent = None, server = None):
        super(MeasurementSettings, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.measSettings = measSettings
        self.hf = server

        #Connect all the GUi elements to their python functions
        self.pushButton.clicked.connect(self.acceptNewValues)

        self.push_AdvisePID.clicked.connect(self.advisePID)

        self.lineEdit_TargetBW.editingFinished.connect(self.setPLL_TargetBW)
        self.lineEdit_PLL_Range.editingFinished.connect(self.setPLL_Range)
        self.lineEdit_PLL_TC.editingFinished.connect(self.setPLL_TC)
        self.lineEdit_PLL_FilterBW.editingFinished.connect(self.setPLL_FilterBW)
        self.lineEdit_PLL_P.editingFinished.connect(self.setPLL_P)
        self.lineEdit_PLL_I.editingFinished.connect(self.setPLL_I)
        self.lineEdit_PLL_D.editingFinished.connect(self.setPLL_D)

        self.comboBox_PLL_Advise.currentIndexChanged.connect(self.setPLL_AdviseMode)
        self.comboBox_PLL_FilterOrder.currentIndexChanged.connect(lambda: self.setPLL_FilterOrder())
        self.comboBox_PLL_Harmonic.currentIndexChanged.connect(lambda: self.setPLL_Harmonic())
        self.comboBox_PLL_Input.currentIndexChanged.connect(self.setPLL_Input)

        self.lineEdit_PLL_Amplitude.editingFinished.connect(self.setPLL_Output_Amplitude)
        self.comboBox_PLL_Output.currentIndexChanged.connect(self.setPLL_Output)

        self.loadValues()
        self.createLoadingColors()

    def setupAdditionalUi(self):
        self.comboBox_PLL_Input.view().setMinimumWidth(100)

    def loadValues(self):
        #Loads the latest values of the MeasurementSettings into the GUI
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

    def setPLL_TargetBW(self):
        #update the target bandwidth of the PLL
        val = readNum(str(self.lineEdit_TargetBW.text()))
        if isinstance(val,float):
            self.measSettings['pll_targetBW'] = val
        self.lineEdit_TargetBW.setText(formatNum(self.measSettings['pll_targetBW']))

    def setPLL_Range(self):
        #Set the range of frequencies aroudn the frequency center the PLL can access
        val = readNum(str(self.lineEdit_PLL_Range.text()))
        if isinstance(val,float):
            self.measSettings['pll_range'] = val
        self.lineEdit_PLL_Range.setText(formatNum(self.measSettings['pll_range']))

    @inlineCallbacks
    def setPLL_TC(self):
        #Set the PLL time constant
        val = readNum(str(self.lineEdit_PLL_TC.text()), self, True)
        if isinstance(val,float):
            self.measSettings['pll_tc'] = val
            self.measSettings['pll_filterBW'] = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_tc'])
            yield self.hf.set_advisor_tc(self.measSettings['pll_tc'])
            yield self.updateSimulation()
        self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))

    @inlineCallbacks
    def setPLL_FilterBW(self):
        #Set the PLL filter bandwidth
        val = readNum(str(self.lineEdit_PLL_FilterBW.text()))
        if isinstance(val,float):
            self.measSettings['pll_filterBW']  = val
            self.measSettings['pll_tc']  = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_filterBW'])
            yield self.hf.set_advisor_tc(self.measSettings['pll_tc'])
            yield self.updateSimulation()
        self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))

    @inlineCallbacks
    def setPLL_P(self):
        #Set the PLL proportional term
        val = readNum(str(self.lineEdit_PLL_P.text()))
        if isinstance(val,float):
            self.measSettings['pll_p'] = val
            yield self.hf.set_advisor_p(self.measSettings['pll_p'])
            yield self.updateSimulation()
        self.lineEdit_PLL_P.setText(formatNum(self.measSettings['pll_p'], 3))

    @inlineCallbacks
    def setPLL_I(self):
        #Set the PLL integral term
        val = readNum(str(self.lineEdit_PLL_I.text()))
        if isinstance(val,float):
            self.measSettings['pll_i'] = val
            yield self.hf.set_advisor_i(self.measSettings['pll_i'])
            yield self.updateSimulation()
        self.lineEdit_PLL_I.setText(formatNum(self.measSettings['pll_i'], 3))

    @inlineCallbacks
    def setPLL_D(self):
        #Set the PLL derivative term
        val = readNum(str(self.lineEdit_PLL_D.text()))
        if isinstance(val,float):
            self.measSettings['pll_d'] = val
            yield self.hf.set_advisor_d(self.measSettings['pll_d'])
            yield self.updateSimulation()
        self.lineEdit_PLL_D.setText(formatNum(self.measSettings['pll_d'], 3))

    def setPLL_Input(self):
        #Set the input of the PLL
        self.measSettings['pll_input'] = self.comboBox_PLL_Input.currentIndex() + 1

    def setPLL_Output(self):
        #Set the output of the PLL
        self.measSettings['pll_output'] = self.comboBox_PLL_Output.currentIndex() + 1

    def setPLL_Output_Amplitude(self):
        #Set the output amplitude of the PLL's AC excitation
        val = readNum(str(self.lineEdit_PLL_Amplitude.text()), self, True)
        if isinstance(val,float):
            self.measSettings['pll_output_amp'] = val
        self.lineEdit_PLL_Amplitude.setText(formatNum(self.measSettings['pll_output_amp']))

    @inlineCallbacks
    def setPLL_Harmonic(self):
        #Set the harmonic of the input frequency. Always set to 1 so far
        self.measSettings['pll_harmonic'] = self.comboBox_PLL_Harmonic.currentIndex() + 1
        yield self.hf.set_advisor_harmonic(self.measSettings['pll_harmonic'])
        yield self.updateSimulation()

    @inlineCallbacks
    def setPLL_FilterOrder(self):
        #Set the filter order of the PLL
        self.measSettings['pll_filterorder'] = self.comboBox_PLL_FilterOrder.currentIndex() + 1
        self.measSettings['pll_filterBW'] = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_tc'])
        self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))
        yield self.hf.set_advisor_filterorder(self.measSettings['pll_filterorder'])
        yield self.updateSimulation()

    def setPLL_AdviseMode(self):
        #Set the PLL PID term advising mode. (0 is P, 1 is I, 2 is PI, and 3 is PID)
        self.measSettings['pll_adivsemode'] = self.comboBox_PLL_Advise.currentIndex()

    @inlineCallbacks
    def updateSimulation(self):
        '''The HF2LI server has functions for simulating the PLL PID bandiwdth
        and phase margin. This updates the GUI with the newly simulated values'''
        try:
            #Waiting for one second seems to work fine for auto calculation to be complete
            yield self.sleep(1)
            #Gets the PLL PID phase margin and simulated bandwidth
            pm = yield self.hf.get_advisor_pm()
            bw = yield self.hf.get_advisor_simbw()

            #Update dictionary and GUI
            self.measSettings['pll_pm'] = pm
            self.measSettings['pll_simBW'] = bw
            self.lineEdit_PLL_PM.setText(formatNum(pm))
            self.lineEdit_PLL_SimBW.setText(formatNum(bw))

            #Check to see if new parameters are stable
            yield self.updateStability()
        except:
            printErrorInfo()

    @inlineCallbacks
    def updateStability(self):
        '''Uses HF2LI simulation to check if PID parameter would lead to a stable PLL'''
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
        '''Compute PLL PID parameters using the HF2LI simulation for the target bandwidth and
        PID advising mode. Also runs a graphic while the HF2LI server is calculating'''
        try:
            self.PID_advice = False
            self.computePIDParameters()
            self.displayCalculatingGraphics()
        except:
            printErrorInfo()

    @inlineCallbacks
    def computePIDParameters(self):
        '''Compute PLL PID parameters using the HF2LI simulation for the target bandwidth and
        PID advising mode'''
        try:
            #Run the PID advisor
            self.PID_advice = yield self.hf.advise_pll_pid(self.measSettings['pll_output'], self.measSettings['pll_targetBW'],self.measSettings['pll_advisemode'])

            #Set the measSettings to those determined from the advisor
            self.measSettings['pll_p'] = yield self.hf.get_advisor_p()
            self.measSettings['pll_i'] = yield self.hf.get_advisor_i()
            self.measSettings['pll_d'] = yield self.hf.get_advisor_d()
            self.measSettings['pll_simBW'] = yield self.hf.get_advisor_simbw()
            self.measSettings['pll_rate']  = yield self.hf.get_advisor_rate()
            self.measSettings['pll_pm'] = yield self.hf.get_advisor_pm()
            self.measSettings['pll_tc'] = yield self.hf.get_advisor_tc()
            self.measSettings['pll_filterBW'] = calculate_FilterBW(self.measSettings['pll_filterorder'], self.measSettings['pll_tc'])

            #Update the GUI with the new settings
            self.lineEdit_PLL_P.setText(formatNum(self.measSettings['pll_p'], 3))
            self.lineEdit_PLL_I.setText(formatNum(self.measSettings['pll_i'], 3))
            self.lineEdit_PLL_D.setText(formatNum(self.measSettings['pll_d'], 3))
            self.lineEdit_PLL_PM.setText(formatNum(self.measSettings['pll_pm']))
            self.lineEdit_PLL_SimBW.setText(formatNum(self.measSettings['pll_simBW']))
            self.lineEdit_PLL_FilterBW.setText(formatNum(self.measSettings['pll_filterBW']))
            self.lineEdit_PLL_Rate.setText(formatNum(self.measSettings['pll_rate'], 3))
            self.lineEdit_PLL_TC.setText(formatNum(self.measSettings['pll_tc']))

            self.updateStability()
        except:
            printErrorInfo()

    @inlineCallbacks
    def displayCalculatingGraphics(self):
        '''Changes the color of the AdvisePID pushButton while calculations
        are not finished. The colors are defined in the createLoadingColors
        function'''
        try:
            i = 0
            while not self.PID_advice:
                self.push_AdvisePID.setStyleSheet(self.sheets[i])
                yield self.sleep(0.025)
                i = (i+1)%80
            self.push_AdvisePID.setStyleSheet(self.sheets[0])
        except:
            printErrorInfo()


    def createLoadingColors(self):
        '''Creates a list of stylesheets with a gradient of grey to black. This
        will be used when the advisePID button is pressed to indicate that
        it is processing.'''

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

    def getValues(self):
        #returns new measurement Settings
        return self.measSettings

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class MySlider(QtWidgets.QSlider):
    '''
    Creates a log scale slider bar.
    '''
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
        #size = self.size()
        contents = self.contentsRect()
        width = contents.width()
        #height = contents.height()
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
    #Function to calculate the filter bandwidth as a function of the filter order.
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
