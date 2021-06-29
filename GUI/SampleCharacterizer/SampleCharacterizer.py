
import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic #, QtTest
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import numpy as np
import pyqtgraph as pg
import time
import math
from nSOTScannerFormat import readNum, formatNum, printErrorInfo

path = sys.path[0] + r"\SampleCharacterizer"
SampleCharacterizerWindowUI, QtBaseClass = uic.loadUiType(path + r"\SampleCharacterizerWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

class Window(QtWidgets.QMainWindow, SampleCharacterizerWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)

        #Sweep parameters dictionary
        self.sweepParameters = {
            'FourTerminal_MinVoltage': -0.1, #Four terminal measurement minimum voltage in volts. Note, this is used for Landau Fan measurements as well
            'FourTerminal_MaxVoltage': 0.1,  #Four terminal measurement maximum voltage in volts. Note, this is used for Landau Fan measurements as well
            'FourTerminal_VoltageSteps': 100, #Four terminal measurement number of voltage steps. Note, this is used for Landau Fan measurements as well
            'FourTerminal_VoltageSteps_Status': "StepNumber", #Voltage steps are entered in the UI as number of steps (StepNumber) or step size in volts (StepSize)
            'FourTerminal_Delay':0.001, #Four terminal measurement delay betwen voltage points in units of seconds. Note, this is used for Landau Fan measurements as well
            'FieldSweep1D_MinField': 0, #Minumum magnetic field for 1D field sweeps
            'FieldSweep1D_MaxField': 0.1, #Maximum magnetic field for 1D field sweeps
            'FieldSweep1D_FieldSteps': 100, ##NUmber of field points for 1D field sweeps
            'FieldSweep1D_FieldSteps_Status': "StepNumber", #Field steps are entered in the UI as number of steps (StepNumber) or step size in tesla (StepSize)
            'FieldSweep1D_Delay': 0.01, #Delay betwen points in units of seconds
            'FieldSweep1D_SweepSpeed': 0.1, #Field ramp rate for 1D field sweep measurements in T/min
            'landauFan_MinField': 0, #Minimum magnetic field for Landau Fan measurements
            'landauFan_MaxField': 0.01, #Maximum magnetic field for Landau Fan measurements
            'landauFan_FieldSteps': 2, #Number of field points for Landau Fan Measurements
            'landauFan_FieldSteps_Status': "StepNumber", #Field steps are entered in the UI as number of steps (StepNumber) or step size in tesla (StepSize)
            'landauFan_SweepSeed': 0.1, #Field ramp rate for landau Fan measurements in T/min
            'Frequency': 17.777, #Lockin measurement frequency in Hertz
            'Voltage_tc': 1, #Lockin voltage time constant in seconds
            'Current_tc': 1, #Lockin current time constant in seconds
            }

        #Dictionary for converting lock in amplifier exponents
        self.lockInExponentDict= {
         'V':1,
         'mV':10**-3,
         'uV':10**-6,
         'nV':10**-9,
         'uA':10**-6,
         'nA':10**-9,
         'pA':10**-12,
         'fA':10**-15,
         }

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)

        #Initialize and connect GUI elements to change the name of the device being measured, which gets saved into the datasets
        self.Device_Name = 'Device Name'
        self.lineEdit_Device_Name.setText(self.Device_Name)
        self.lineEdit_Device_Name.editingFinished.connect(self.updateDeviceName)

        #Initialize lists to track current and desired DAC outputs
        self.DAC_output = [0.0,0.0,0.0,0.0] #ith entry is current DAC output of the ith channel
        self.DAC_setpoint = [0.0,0.0,0.0,0.0] #ith entry is the desired DAC output of the ith channel

        #Create a python list of QUI labels for the DAC outputs and initalize them to zero
        self.label_DACOout_list = [self.label_DACOut1, self.label_DACOut2, self.label_DACOut3, self.label_DACOut4]
        for i in range(0,4):
            self.label_DACOout_list[i].setText(formatNum(self.DAC_output[i],6))

        #Connect GUI elements for manually setting the DAC ADC setpoint and output voltages
        self.lineEdit_DACOut1.editingFinished.connect(lambda:self.setDACSetpoint(0, self.lineEdit_DACOut1))
        self.lineEdit_DACOut2.editingFinished.connect(lambda:self.setDACSetpoint(1, self.lineEdit_DACOut2))
        self.lineEdit_DACOut3.editingFinished.connect(lambda:self.setDACSetpoint(2, self.lineEdit_DACOut3))
        self.lineEdit_DACOut4.editingFinished.connect(lambda:self.setDACSetpoint(3, self.lineEdit_DACOut4))

        self.pushButton_DACOut1.clicked.connect(lambda:self.setDACOutput(0))
        self.pushButton_DACOut2.clicked.connect(lambda:self.setDACOutput(1))
        self.pushButton_DACOut3.clicked.connect(lambda:self.setDACOutput(2))
        self.pushButton_DACOut4.clicked.connect(lambda:self.setDACOutput(3))

        #Initializel lists of input channels to measure and output channel to sweep.
        self.FourTerminal_ChannelInput = [1, 0]
        self.FourTerminal_ChannelOutput = [0]

        #Connect comboBoxes to update the four terminal input and output channels
        self.comboBox_FourTerminal_Output.currentIndexChanged.connect(self.updateFourTerminalOutput)
        self.comboBox_FourTerminal_Input1.currentIndexChanged.connect(self.updateFourTerminalInput1)
        self.comboBox_FourTerminal_Input2.currentIndexChanged.connect(self.updateFourTerminalInput2)

        #Initialize the GUI with the module default parameters for the four terminal sweep
        self.lineEdit_FourTerminal_MinVoltage.setText(formatNum(self.sweepParameters['FourTerminal_MinVoltage'],6))
        self.lineEdit_FourTerminal_MaxVoltage.setText(formatNum(self.sweepParameters['FourTerminal_MaxVoltage'],6))
        self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.sweepParameters['FourTerminal_VoltageSteps'],6))
        self.lineEdit_FourTerminal_Delay.setText(formatNum(self.sweepParameters['FourTerminal_Delay'],6))

        #Connect lineEdits for changing four terminal sweep parameters
        self.lineEdit_FourTerminal_MinVoltage.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_FourTerminal_MinVoltage, 'FourTerminal_MinVoltage', [-10.0, 10.0]))
        self.lineEdit_FourTerminal_MaxVoltage.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_FourTerminal_MaxVoltage, 'FourTerminal_MaxVoltage', [-10.0, 10.0]))
        self.lineEdit_FourTerminal_Delay.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_FourTerminal_Delay, 'FourTerminal_Delay'))
        self.lineEdit_FourTerminal_Numberofstep.editingFinished.connect(self.updateFourTerminalSteps)

        #Connect pushButton for toggling between inputting voltage step size and voltage number of steps
        self.pushButton_FourTerminalStepSwitch.clicked.connect(self.toggleFourTerminalSteps)

        #Connect comboBoxes for lock in sensitivity / multiplier settings
        self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentIndexChanged.connect(self.updateLockinMultipliers)
        self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentIndexChanged.connect(self.updateLockinMultipliers)
        self.comboBox_Voltage_LI_Sensitivity_Unit.currentIndexChanged.connect(self.updateLockinMultipliers)
        self.comboBox_Voltage_LI_Expand.currentIndexChanged.connect(self.updateLockinMultipliers)
        self.comboBox_Current_LI_Sensitivity_1stdigit.currentIndexChanged.connect(self.updateLockinMultipliers)
        self.comboBox_Current_LI_Sensitivity_2nddigit.currentIndexChanged.connect(self.updateLockinMultipliers)
        self.comboBox_Current_LI_Sensitivity_Unit.currentIndexChanged.connect(self.updateLockinMultipliers)
        self.comboBox_Current_LI_Expand.currentIndexChanged.connect(self.updateLockinMultipliers)

        self.updateLockinMultipliers() #Call this function to ensure that the GUI configuration at startup matches the software

        #Connect lineEdit for lock in frequency and time constants
        self.lineEdit_lockinFrequency.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_lockinFrequency, 'Frequency'))
        self.lineEdit_voltageTC.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_voltageTC, 'Voltage_tc'))
        self.lineEdit_currentTC.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_currentTC, 'Current_tc'))

        #Initialize the GUI with the module default parameters for 1D field sweep tab
        self.lineEdit_1DFieldSweepSetting_MinimumField.setText(formatNum(self.sweepParameters['FieldSweep1D_MinField'], 6))
        self.lineEdit_1DFieldSweepSetting_MaximumField.setText(formatNum(self.sweepParameters['FieldSweep1D_MaxField'], 6))
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.setText(formatNum(self.sweepParameters['FieldSweep1D_FieldSteps'], 6))
        self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed.setText(formatNum(self.sweepParameters['FieldSweep1D_SweepSpeed'], 6))
        self.lineEdit_1DFieldSweepSetting_Delay.setText(formatNum(self.sweepParameters['FieldSweep1D_Delay'], 6))

        #Connect lineEdits for 1D field sweep measurements
        self.lineEdit_1DFieldSweepSetting_MinimumField.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_1DFieldSweepSetting_MinimumField, 'FieldSweep1D_MinField'))
        self.lineEdit_1DFieldSweepSetting_MaximumField.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_1DFieldSweepSetting_MaximumField, 'FieldSweep1D_MaxField'))
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.editingFinished.connect(self.updateFieldSweep1DSteps)
        self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed, 'FieldSweep1D_SweepSpeed'))
        self.lineEdit_1DFieldSweepSetting_Delay.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_1DFieldSweepSetting_Delay, 'FieldSweep1D_Delay'))

        #Connect pushButton for toggling between inputting field step size and field number of steps for the 1D field sweep
        self.pushButton_1DFieldSweepSetting_NoSmTpTSwitch.clicked.connect(self.toggleFieldSweep1DSteps)

        #Initialize the GUI with the module default parameters for the Landau Fan
        self.lineEdit_landauFan_MinField.setText(formatNum(self.sweepParameters['landauFan_MinField'],6))
        self.lineEdit_landauFan_MaxField.setText(formatNum(self.sweepParameters['landauFan_MaxField'],6))
        self.lineEdit_landauFan_Steps.setText(formatNum(self.sweepParameters['landauFan_FieldSteps'],6))
        self.lineEdit_landauFan_FieldSpeed.setText(formatNum(self.sweepParameters['landauFan_SweepSeed'],6))

        #Connect lineEdits for updating Landau fan measurement parameters
        self.lineEdit_landauFan_MinField.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_landauFan_MinField, 'landauFan_MinField'))
        self.lineEdit_landauFan_MaxField.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_landauFan_MaxField, 'landauFan_MaxField'))
        self.lineEdit_landauFan_Steps.editingFinished.connect(self.updateLandauFanSteps)
        self.lineEdit_landauFan_FieldSpeed.editingFinished.connect(lambda: self.updateSweepParameter(self.lineEdit_landauFan_FieldSpeed, 'landauFan_SweepSeed'))

        #Connect pushButton for toggling between inputting field step size and field number of steps for the Landau Fan
        self.pushButton_landauFanStepSwitch.clicked.connect(self.toggleLandauFanSteps)

        #Connect lineEdits and pushButtons for updating Landau Fan linecuts and colorscales
        self.lineEdit_landauFan_FieldLinecut.editingFinished.connect(self.setLandauFanFieldLinecut)
        self.lineEdit_landauFan_GateLinecut.editingFinished.connect(self.setLandauFanGateLinecut)
        self.pushButton_landauFan_AutoLevel.clicked.connect(self.autoLevelFourTerminal2DPlot)

        #Initialize linecut positions
        self.landauFanFieldLinecutPosition, self.landauFanGateLinecutPosition = 0.0, 0.0

        #Landau fan data is a class variable in order to facilitate linecuts interacting with live data
        #Generate landau default data
        self.landauFanResistanceData = np.zeros([self.sweepParameters['landauFan_FieldSteps'], self.sweepParameters['FourTerminal_VoltageSteps']])
        self.landauFanConductanceData = np.zeros([self.sweepParameters['landauFan_FieldSteps'], self.sweepParameters['FourTerminal_VoltageSteps']])
        self.landauFanVoltageData = np.zeros([self.sweepParameters['landauFan_FieldSteps'], self.sweepParameters['FourTerminal_VoltageSteps']])
        self.landauFanCurrentData = np.zeros([self.sweepParameters['landauFan_FieldSteps'], self.sweepParameters['FourTerminal_VoltageSteps']])

        #Generate landau fan field points array for default 2D data
        self.landauFanFieldPoints = np.linspace(self.sweepParameters['landauFan_MinField'],self.sweepParameters['landauFan_MaxField'],self.sweepParameters['landauFan_FieldSteps'])
        #Generate four terminal measurement gate voltage points array for default 2D data
        self.fourTerminalGatePoints = np.linspace(self.sweepParameters['FourTerminal_MinVoltage'],self.sweepParameters['FourTerminal_MaxVoltage'],self.sweepParameters['FourTerminal_VoltageSteps'])

        #Connect pushButtons to start and abort sweeps
        self.pushButton_StartFourTerminalSweep.clicked.connect(lambda: self.startFourTerminalSweep())
        self.pushButton_StartLandauFan.clicked.connect(lambda: self.startLandauFanSweep())
        self.pushButton_Start1DFieldSweep.clicked.connect(lambda: self.startFieldSweep1D())

        self.abortMagneticFieldSweep_Flag = False #By default do not abort a sweep
        self.pushButton_AbortLandauFan.clicked.connect(self.abortMagneticFieldSweep)
        self.pushButton_Abort1DFieldSweep.clicked.connect(self.abortMagneticFieldSweep)

        #Initialize name of datavault file
        self.dvFileName = ""

        self.moveDefault() #Move module to default
        self.setupAdditionalUi() #Set up all the plots that cannot be initialized in QtDesigner

        self.disconnectLabRAD() #Initialize all the labrad connections as false and lock the interface

#----------------------------------------------------------------------------------------------#
    """ The following section has standard server connection and GUI functions"""

    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.gen_dv = dict['servers']['local']['dv']

            #Create another connection for the connection to data vault to prevent
            #problems of multiple windows trying to write the data vault at the same
            #time
            from labrad.wrappers import connectAsync
            self.cxn_sample = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn_sample.data_vault
            curr_folder = yield self.gen_dv.cd()
            yield self.dv.cd(curr_folder)

            self.dac = yield self.cxn_sample.dac_adc
            yield self.dac.select_device(dict['devices']['sample']['dac_adc'])

            #Eventually make this module compatible with Toellner, for now it is not
            if dict['devices']['system']['magnet supply'] == 'Toellner Power Supply':
                self.dac_toe = dict['servers']['local']['dac_adc']
                self.ips = None
                self.ami = None
            elif dict['devices']['system']['magnet supply'] == 'IPS 120 Power Supply':
                self.dac_toe = None
                self.ips = dict['servers']['remote']['ips120']
                self.ami = None
            elif dict['devices']['system']['magnet supply'] == 'AMI 430 Power Supply':
                self.dac_toe = None
                self.ips = None
                self.ami = dict['servers']['local']['ami_430']
            else:
                raise Exception

            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")

            self.unlockInterface()
        except Exception:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")

    def disconnectLabRAD(self):
        self.cxn = False
        self.gen_dv = False

        self.cxn_sample = False
        self.dv = False
        self.dac = False
        self.dac_toe = False
        self.ips = False

        self.lockInterface()

        self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")

    def showServersList(self):
        #Open pop up window with list of servers required for this module
        serList = serversList(self.reactor, self)
        serList.exec_()

    def updateDataVaultDirectory(self):
        #Update the datavault directory of the local datavault server to match the rest of the software
        curr_folder = yield self.gen_dv.cd()
        yield self.dv.cd(curr_folder)

    def updateDeviceName(self):
        self.Device_Name = str(self.lineEdit_Device_Name.text())

    def moveDefault(self):
        self.move(550,10) #Move module to the specified position

    def setSessionFolder(self, folder):
        self.sessionFolder = folder

#----------------------------------------------------------------------------------------------#
    """ The following section initializes the additional UI elements, namely all the plots"""

    def setupAdditionalUi(self):
        self.setupFourTerminalPlots() #Initializes the plots for the four terminal resistance tab
        self.setupFieldSweep1DPlots() #Intializes plots for the magnetic field 1D field sweep measurements tab
        self.setupLandauFanPlots() #Initializes plots for the Landau fan measurement tab

    def setup1DPlot(self, plot, layout , title , yaxis , yunit, xaxis, xunit):
        #Function to simpify formatting the 1D plot axes, title, etc...
        plot.setGeometry(QtCore.QRect(0, 0, 400, 200))
        plot.setTitle(title)
        plot.setLabel('left', yaxis, units = yunit)
        plot.setLabel('bottom', xaxis, units = xunit)
        plot.showAxis('right', show = True)
        plot.showAxis('top', show = True)
        plot.setXRange(0,1)
        plot.setYRange(0,2)
        plot.enableAutoRange(enable = True)
        layout.addWidget(plot)

    def setup2DPlot(self, plot, yaxis, yunit, xaxis, xunit , frame , layout , plotView ):
        #Function to simpify formatting the 2D plot axes, title, etc...
        plot.setLabel('left', yaxis, units = yunit)
        plot.setLabel('bottom', xaxis, units = xunit)
        plot.showAxis('top', show = True)
        plot.showAxis('right', show = True)
        plot.setAspectLocked(False)
        plot.invertY(False)
        plot.setXRange(-1.25,1.25,0)
        plot.setYRange(-10,10, 0)
        plotView.setGeometry(QtCore.QRect(0, 0, 400, 200))
        plotView.ui.menuBtn.hide()
        plotView.ui.histogram.item.gradient.loadPreset('bipolar')
        plotView.ui.roiBtn.hide()
        plotView.ui.menuBtn.hide()

        frame.close() #necessary for streching the window
        layout.addWidget(plotView)

    def setupFourTerminalPlots(self):
        #Create the plots
        self.fourTerminalPlot1 = pg.PlotWidget()
        self.fourTerminalPlot2 = pg.PlotWidget()
        self.fourTerminalPlot3 = pg.PlotWidget()
        self.fourTerminalPlot4 = pg.PlotWidget()

        #Set up the plot parameters including the GUI layout in which the should be placed, axes names and units
        self.setup1DPlot(self.fourTerminalPlot1, self.Layout_FourTerminalPlot1, 'Voltage', 'Voltage', "V", 'Gate Voltage', "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.fourTerminalPlot2, self.Layout_FourTerminalPlot2, 'Current', 'Current', "A", 'Gate Voltage',"V" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.fourTerminalPlot3, self.Layout_FourTerminalPlot3, 'Resistance', 'Resistance', "Ohm", 'Gate Voltage',"V" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.fourTerminalPlot4, self.Layout_FourTerminalPlot4, 'Conductance', 'Conductance', "S", 'Gate Voltage',"V" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    def setupFieldSweep1DPlots(self):
        #Create the plots
        self.fieldSweep1DPlot1 = pg.PlotWidget()
        self.fieldSweep1DPlot2 = pg.PlotWidget()
        self.fieldSweep1DPlot3 = pg.PlotWidget()
        self.fieldSweep1DPlot4 = pg.PlotWidget()

        #Set up the plot parameters including the GUI layout in which the should be placed, axes names and units
        self.setup1DPlot(self.fieldSweep1DPlot1, self.verticalLayout_1DFieldSweepPlot1, 'Voltage', 'Voltage', "V", 'MagneticField', "T")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.fieldSweep1DPlot2, self.verticalLayout_1DFieldSweepPlot2, 'Current', 'Current', "A", 'MagneticField',"T" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.fieldSweep1DPlot3, self.verticalLayout_1DFieldSweepPlot3, 'Resistance', 'Resistance', "Ohm", 'MagneticField',"T" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.fieldSweep1DPlot4, self.verticalLayout_1DFieldSweepPlot4, 'Conductance', 'Conductance', "S", 'MagneticField',"T" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    def setupLandauFanPlots(self):
        #First set up 2D plots
        self.setupLandauFan2DPlots()
        #Then set up the 1D plots for the linecut data
        self.setupLandauFan1DPlots()
        #Finally, set up the linecut objects themselves
        self.setupLandauFanLinecuts()

    def setupLandauFan2DPlots(self):
        #Start by creating pg view objects for them
        self.view_landauFanResistance = pg.PlotItem(name = "Four Terminal Resistance versus Magnetic Field Resistance Plot",title = "Resistance")
        self.view_landauFanVoltage = pg.PlotItem(name = "Four Terminal Voltage versus Magnetic Field Voltage Plot",title = 'Voltage')
        self.view_landauFanCurrent = pg.PlotItem(name = "Four Terminal Current versus Magnetic Field Voltage Plot",title = 'Current')
        self.view_landauFanConductance = pg.PlotItem(name = "Four Terminal Conductance versus Magnetic Field Voltage Plot",title = "Conductance")

        #Initialize the Image View Objects (2D plotter)
        self.landauFanResistancePlot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Resistance_2DPlot, view = self.view_landauFanResistance)
        self.landauFanVoltagePlot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Voltage_2DPlot, view = self.view_landauFanVoltage)
        self.landauFanCurrentPlot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Current_2DPlot, view = self.view_landauFanCurrent)
        self.landauFanConductancePlot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Conductance_2DPlot, view = self.view_landauFanConductance)

        #Format the 2D plots
        self.setup2DPlot(self.view_landauFanResistance, "Magnetic Field", 'T', 'Gate Voltage', 'V', self.Frame_FourTerminalMagneticField_Resistance_2DPlot, self.Layout_FourTerminalMagneticField_Resistance_2DPlot, self.landauFanResistancePlot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView
        self.setup2DPlot(self.view_landauFanVoltage, "Magnetic Field", 'T', 'Gate Voltage', 'V', self.Frame_FourTerminalMagneticField_Voltage_2DPlot, self.Layout_FourTerminalMagneticField_Voltage_2DPlot, self.landauFanVoltagePlot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView
        self.setup2DPlot(self.view_landauFanCurrent, "Magnetic Field", 'T', 'Gate Voltage', 'V', self.Frame_FourTerminalMagneticField_Current_2DPlot, self.Layout_FourTerminalMagneticField_Current_2DPlot, self.landauFanCurrentPlot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView
        self.setup2DPlot(self.view_landauFanConductance, "Magnetic Field", 'T', 'Gate Voltage', 'V', self.Frame_FourTerminalMagneticField_Conductance_2DPlot, self.Layout_FourTerminalMagneticField_Conductance_2DPlot, self.landauFanConductancePlot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView

        #Plot the default data so that the ImageView is not empty
        self.updateImageViewScale() #Updates the pos and scale factors for proper plotting
        self.landauFanResistancePlot.setImage(self.landauFanResistanceData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanVoltagePlot.setImage(self.landauFanVoltageData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanCurrentPlot.setImage(self.landauFanCurrentData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanConductancePlot.setImage(self.landauFanConductanceData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])

    def updateImageViewScale(self):
        #set up the parameter for ploting, pos and scale
        self.posx, self.posy = (self.sweepParameters['FourTerminal_MinVoltage'], self.sweepParameters['landauFan_MinField'])
        self.scalex, self.scaley = ((self.sweepParameters['FourTerminal_MaxVoltage']-self.sweepParameters['FourTerminal_MinVoltage'])/self.sweepParameters['FourTerminal_VoltageSteps'], (self.sweepParameters['landauFan_MaxField']-self.sweepParameters['landauFan_MinField'])/self.sweepParameters['landauFan_FieldSteps'])

    def setupLandauFan1DPlots(self):
        #Initialize 1D plots of linecut through the 2D plots
        self.landauFanResistancevsFieldPlot = pg.PlotWidget(parent = None) #Linecut along the magnetic field axis
        self.landauFanResistancevsGatePlot = pg.PlotWidget(parent = None) #Linecut along the gate voltage axis
        self.landauFanVoltagevsFieldPlot = pg.PlotWidget(parent = None)
        self.landauFanVoltagevsGatePlot = pg.PlotWidget(parent = None)
        self.landauFanCurrentvsFieldPlot = pg.PlotWidget(parent = None)
        self.landauFanCurrentvsGatePlot = pg.PlotWidget(parent = None)
        self.landauFanConductancevsFieldPlot = pg.PlotWidget(parent = None)
        self.landauFanConductancevsGatePlot = pg.PlotWidget(parent = None)

        #Set up the linecut plot axes
        self.setup1DPlot(self.landauFanResistancevsFieldPlot, self.Layout_FourTerminalMagneticField_Resistance_VersusField, None, "Magnetic Field", 'T', 'Resistance','Ohm')#Plot, Layout , Title , yaxis , yunit, xaxis ,
        self.setup1DPlot(self.landauFanResistancevsGatePlot, self.Layout_FourTerminalMagneticField_Resistance_VersusGateVoltage, None,'Resistance','Ohm', 'Gate Voltage', 'V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.landauFanVoltagevsFieldPlot, self.Layout_FourTerminalMagneticField_Voltage_VersusField, None, "Magnetic Field", 'T', 'Voltage','V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.landauFanVoltagevsGatePlot, self.Layout_FourTerminalMagneticField_Voltage_VersusGateVoltage, None, 'Voltage','V', 'Gate Voltage', 'V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.landauFanCurrentvsFieldPlot, self.Layout_FourTerminalMagneticField_Current_VersusField, None, "Magnetic Field", 'T', 'Current','A')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.landauFanCurrentvsGatePlot, self.Layout_FourTerminalMagneticField_Current_VersusGateVoltage, None, 'Current','A', 'Gate Voltage', 'V')  #Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.landauFanConductancevsFieldPlot, self.Layout_FourTerminalMagneticField_Conductance_VersusField, None, "Magnetic Field", 'T', 'Conductance','S')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        self.setup1DPlot(self.landauFanConductancevsGatePlot, self.Layout_FourTerminalMagneticField_Conductance_VersusGateVoltage, None,'Conductance','S', 'Gate Voltage', 'V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    def setupLandauFanLinecuts(self):
        #Initialize the line objects for linecuts
        self.landauFanResistancevsFieldLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.landauFanResistancevsGateLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.landauFanVoltagevsFieldLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.landauFanVoltagevsGateLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.landauFanCurrentvsFieldLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.landauFanCurrentvsGateLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.landauFanConductancevsFieldLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.landauFanConductancevsGateLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)

        #Add the line objects to the 2D plot objects
        self.landauFanResistancePlot.addItem(self.landauFanResistancevsFieldLine, ignoreBounds = True)
        self.landauFanResistancePlot.addItem(self.landauFanResistancevsGateLine, ignoreBounds = True)
        self.landauFanConductancePlot.addItem(self.landauFanConductancevsFieldLine, ignoreBounds = True)
        self.landauFanConductancePlot.addItem(self.landauFanConductancevsGateLine, ignoreBounds = True)
        self.landauFanVoltagePlot.addItem(self.landauFanVoltagevsFieldLine, ignoreBounds = True)
        self.landauFanVoltagePlot.addItem(self.landauFanVoltagevsGateLine, ignoreBounds = True)
        self.landauFanCurrentPlot.addItem(self.landauFanCurrentvsFieldLine, ignoreBounds = True)
        self.landauFanCurrentPlot.addItem(self.landauFanCurrentvsGateLine, ignoreBounds = True)

        #Connect the line objects to the appropriate functions updating the linecut plots when the objects are moved
        self.landauFanResistancevsFieldLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanFieldLinecuts(self.landauFanResistancevsFieldLine))
        self.landauFanConductancevsFieldLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanFieldLinecuts(self.landauFanConductancevsFieldLine))
        self.landauFanVoltagevsFieldLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanFieldLinecuts(self.landauFanVoltagevsFieldLine))
        self.landauFanCurrentvsFieldLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanFieldLinecuts(self.landauFanCurrentvsFieldLine))

        self.landauFanResistancevsGateLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanGateLinecuts(self.landauFanResistancevsGateLine))
        self.landauFanConductancevsGateLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanGateLinecuts(self.landauFanConductancevsGateLine))
        self.landauFanVoltagevsGateLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanGateLinecuts(self.landauFanVoltagevsGateLine))
        self.landauFanCurrentvsGateLine.sigPositionChangeFinished.connect(lambda:self.updateLandauFanGateLinecuts(self.landauFanCurrentvsGateLine))

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for updating linecuts through the 2D Landau fan plots"""

    def setLandauFanFieldLinecut(self):
        #Called when the FieldLinecut linedit is changed
        val = readNum(str(self.lineEdit_landauFan_FieldLinecut.text()))
        if isinstance(val,float):
            self.landauFanFieldLinecutPosition = val
        self.lineEdit_landauFan_FieldLinecut.setText(formatNum(self.landauFanFieldLinecutPosition, 6))
        self.setLandauFanLinecutPosition() #Update the position according to the value
        self.updateLandauFanLinecutPlots() #Update the Linecut Plot with newly edited value of position

    def setLandauFanGateLinecut(self):
        #Called when the GateLinecut linedit is changed
        val = readNum(str(self.lineEdit_landauFan_GateLinecut.text()))
        if isinstance(val,float):
            self.landauFanGateLinecutPosition = val
        self.lineEdit_landauFan_GateLinecut.setText(formatNum(self.landauFanGateLinecutPosition, 6))
        self.setLandauFanLinecutPosition() #Update the position according to the value
        self.updateLandauFanLinecutPlots() #Update the Linecut Plot with newly edited value of position

    def updateLandauFanFieldLinecuts(self, LineCut):
        #Called when the FieldLinecut line object is moved
        self.landauFanFieldLinecutPosition = LineCut.value() #Update the value when the user changes the position of the line
        self.lineEdit_landauFan_FieldLinecut.setText(formatNum(self.landauFanFieldLinecutPosition)) #Update the text
        self.setLandauFanLinecutPosition() #Update the position according to the value
        self.updateLandauFanLinecutPlots() #Update the Linecut Plot with newly edited value of position

    def updateLandauFanGateLinecuts(self, LineCut):
        #Called when the GateLinecut line object is moved
        self.landauFanGateLinecutPosition=LineCut.value() #Update the value when the user changes the position of the line
        self.lineEdit_landauFan_GateLinecut.setText(formatNum(self.landauFanGateLinecutPosition)) #Update the text
        self.setLandauFanLinecutPosition() #Update the position according to the value
        self.updateLandauFanLinecutPlots() #Update the Linecut Plot with newly edited value of position

    def setLandauFanLinecutPosition(self):
        #Set the position of all the field linecuts objects
        self.landauFanResistancevsFieldLine.setValue(float(self.landauFanFieldLinecutPosition))
        self.landauFanConductancevsFieldLine.setValue(float(self.landauFanFieldLinecutPosition))
        self.landauFanVoltagevsFieldLine.setValue(float(self.landauFanFieldLinecutPosition))
        self.landauFanCurrentvsFieldLine.setValue(float(self.landauFanFieldLinecutPosition))

        #Set the position of all the gate linecuts objects
        self.landauFanResistancevsGateLine.setValue(float(self.landauFanGateLinecutPosition))
        self.landauFanConductancevsGateLine.setValue(float(self.landauFanGateLinecutPosition))
        self.landauFanVoltagevsGateLine.setValue(float(self.landauFanGateLinecutPosition))
        self.landauFanCurrentvsGateLine.setValue(float(self.landauFanGateLinecutPosition))

    def updateLandauFanLinecutPlots(self):
        #Update the linecut plots based on position of LineCut. First find the index of the line closest
        #to the specified linecut position
        #note, a field linecut has a constant gate voltage position and a gate linecut has a constant field position
        xindex = int((self.landauFanFieldLinecutPosition - self.sweepParameters['FourTerminal_MinVoltage'])/self.scalex)
        yindex = int((self.landauFanGateLinecutPosition - self.sweepParameters['landauFan_MinField'])/self.scaley)

        #Make sure the indices are within the available range
        if xindex > self.sweepParameters['FourTerminal_VoltageSteps']-1:
            xindex = self.sweepParameters['FourTerminal_VoltageSteps']-1;
        elif xindex < 0:
            xindex = 0

        if yindex > self.sweepParameters['landauFan_FieldSteps']-1:
            yindex = self.sweepParameters['landauFan_FieldSteps']-1;
        elif yindex < 0:
            yindex = 0

        #Clear the linecut plots before adding new data
        self.clearLineCutPlots()

        #Plot the linecuts vs magnetic field
        self.landauFanResistancevsFieldPlot.plot(x = self.landauFanResistanceData[:,xindex], y = self.landauFanFieldPoints, pen = 0.5)
        self.landauFanConductancevsFieldPlot.plot(x = self.landauFanConductanceData[:,xindex], y = self.landauFanFieldPoints, pen = 0.5)
        self.landauFanVoltagevsFieldPlot.plot(x = self.landauFanVoltageData[:,xindex], y = self.landauFanFieldPoints, pen = 0.5)
        self.landauFanCurrentvsFieldPlot.plot(x = self.landauFanCurrentData[:,xindex], y = self.landauFanFieldPoints, pen = 0.5)

        #Plot linecut vs gate voltage
        self.landauFanResistancevsGatePlot.plot(x = self.fourTerminalGatePoints, y = self.landauFanResistanceData[yindex], pen = 0.5)
        self.landauFanConductancevsGatePlot.plot(x = self.fourTerminalGatePoints, y = self.landauFanConductanceData[yindex], pen = 0.5)
        self.landauFanVoltagevsGatePlot.plot(x = self.fourTerminalGatePoints, y = self.landauFanVoltageData[yindex], pen = 0.5)
        self.landauFanCurrentvsGatePlot.plot(x = self.fourTerminalGatePoints, y = self.landauFanCurrentData[yindex], pen = 0.5)

    def clearLineCutPlots(self):
        self.landauFanResistancevsFieldPlot.clear()
        self.landauFanResistancevsGatePlot.clear()
        self.landauFanConductancevsFieldPlot.clear()
        self.landauFanConductancevsGatePlot.clear()
        self.landauFanVoltagevsFieldPlot.clear()
        self.landauFanVoltagevsGatePlot.clear()
        self.landauFanCurrentvsFieldPlot.clear()
        self.landauFanCurrentvsGatePlot.clear()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for updating and clearing plots"""

    def plotFourTerminalData(self, plot_data, color = 0.5):
        yield self.fourTerminalPlot1.plot(plot_data[0], plot_data[1], pen = color)
        if np.size(self.FourTerminal_ChannelInput)!=4:
            yield self.fourTerminalPlot2.plot(plot_data[0], plot_data[2], pen = color)
            yield self.fourTerminalPlot3.plot(plot_data[0], plot_data[3], pen = color)
            yield self.fourTerminalPlot4.plot(plot_data[0], plot_data[4], pen = color)

    def clearFourTerminalPlots(self):
        self.fourTerminalPlot1.clear()
        self.fourTerminalPlot2.clear()
        self.fourTerminalPlot3.clear()
        self.fourTerminalPlot4.clear()

    def plotFieldSweep1DData(self, plot_data, color):
        self.fieldSweep1DPlot1.plot(plot_data[1], plot_data[2], pen = color)
        if np.size(self.FourTerminal_ChannelInput)!=4:
            self.fieldSweep1DPlot2.plot(plot_data[1], plot_data[3], pen = color)
            self.fieldSweep1DPlot3.plot(plot_data[1], plot_data[4], pen = color)
            self.fieldSweep1DPlot4.plot(plot_data[1], plot_data[5], pen = color)

    def clearFieldSweep1DPlots(self):
        self.fieldSweep1DPlot1.clear()
        self.fieldSweep1DPlot2.clear()
        self.fieldSweep1DPlot3.clear()
        self.fieldSweep1DPlot4.clear()

    def updateLandauFan2DPlots(self, index, plot_data):
        #index is the magnetic field line numbers
        #plot_data[0] is a 1D array of the independent variable, the gate voltage
        #plot_data[1] is a 1D array of measured voltages
        #plot_data[2] is a 1D array of measured currents
        #plot_data[3] is a 1D array of measured resistances
        #plot_data[4] is a 1D array of measured conductances

        #Add data to the Plotted 2D Data
        self.landauFanVoltageData[index] = plot_data[1]
        self.landauFanCurrentData[index] = plot_data[2]
        self.landauFanResistanceData[index] = plot_data[3]
        self.landauFanConductanceData[index] = plot_data[4]

        #Update the 2D plots with new data
        self.landauFanResistancePlot.setImage(self.landauFanResistanceData.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanVoltagePlot.setImage(self.landauFanVoltageData.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanCurrentPlot.setImage(self.landauFanCurrentData.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanConductancePlot.setImage(self.landauFanConductanceData.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])

    def autoRangeFourTerminal2DPlot(self):
        #Sets the x and y axis range of the 2D plots to be snug around the dataset
        self.landauFanResistancePlot.setImage(self.landauFanResistanceData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanConductancePlot.setImage(self.landauFanConductanceData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanVoltagePlot.setImage(self.landauFanVoltageData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanCurrentPlot.setImage(self.landauFanCurrentData.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])

    def autoLevelFourTerminal2DPlot(self):
        #Replots the data with a colorscale with extents just above and below the max/min data
        self.landauFanResistancePlot.setImage(self.landauFanResistanceData.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanConductancePlot.setImage(self.landauFanConductanceData.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanVoltagePlot.setImage(self.landauFanVoltageData.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.landauFanCurrentPlot.setImage(self.landauFanCurrentData.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])

    def clearLandauFan2DPlots(self):
        self.landauFanResistancePlot.clear()
        self.landauFanVoltagePlot.clear()
        self.landauFanCurrentPlot.clear()
        self.landauFanConductancePlot.clear()

    def clearLandauFanPlots(self):
        self.clearLandauFan2DPlots()
        self.clearLineCutPlots()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for updating the four terminal sweep parameters"""

    def updateSweepParameter(self, lineEdit, key, range = None):
        val = readNum(str(lineEdit.text())) #Read the text from the provided lineEdit
        if isinstance(val,float): #If it's a proper number, update the sweep Parameter dictionary
            if range == None:
                self.sweepParameters[key] = val
            elif val >= range[0] and val <= range[1]: #Check that the number is within the proper range
                self.sweepParameters[key] = val
            self.updateSweepSteps()
        #Set the linedit to the formatted value. If it was input incorrectly, this resets the lineEdit to the previous value
        lineEdit.setText(formatNum(self.sweepParameters[key], 6))

    def updateSweepSteps(self):
        #Update the steps in all the sweeps, as these can change depending on which sweep parameters were editted
        #Calling this every time any parameter is updated is slightly unnecessary, but makes the code concise
        self.updateFourTerminalSteps() #Updates steps for the fourterminal sweep
        self.updateFieldSweep1DSteps() #Updates steps for the 1D field sweep sweep
        self.updateLandauFanSteps() #Update steps for Landau fan sweep

    def updateFourTerminalSteps(self):
        #Updates the four terminal steps. This gets its own function to allow the UI to toggle between entering StepNumber and StepSize
        val = readNum(str(self.lineEdit_FourTerminal_Numberofstep.text()))
        if isinstance(val,float):
            #Software toggle between the lineEdit switching the number of step and the size of the steps
            if self.sweepParameters['FourTerminal_VoltageSteps_Status'] == "StepNumber":  #If setting the number of sets, do that
                self.sweepParameters['FourTerminal_VoltageSteps']=int(round(val)) #round here is necessary, without round it cannot do 1001 steps back and force
            if self.sweepParameters['FourTerminal_VoltageSteps_Status'] == "StepSize": #If setting the step size, do that
                self.sweepParameters['FourTerminal_VoltageSteps']=self.calcStepNumber(self.sweepParameters['FourTerminal_MaxVoltage'],self.sweepParameters['FourTerminal_MinVoltage'],float(val))
        self.setFourTerminalStepsText()

    def setFourTerminalStepsText(self):
        #Refresh four terminal step lineEdit based on the status change the lineEdit text
        if self.sweepParameters['FourTerminal_VoltageSteps_Status'] == "StepNumber":
            self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.sweepParameters['FourTerminal_VoltageSteps'],6))
        else:
            self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.calcStepSize(self.sweepParameters['FourTerminal_MaxVoltage'],self.sweepParameters['FourTerminal_MinVoltage'],self.sweepParameters['FourTerminal_VoltageSteps']),6))

    def toggleFourTerminalSteps(self):
        #Toggle between entering StepNumber and StepSize in the UI for Four Terminal measurements
        if self.sweepParameters['FourTerminal_VoltageSteps_Status'] == "StepNumber":
            self.label_FourTerminalNumberofstep.setText('Volt per Steps')
            self.sweepParameters['FourTerminal_VoltageSteps_Status'] = "StepSize"
            self.setFourTerminalStepsText()
        else:
            self.label_FourTerminalNumberofstep.setText('Number of Steps')
            self.sweepParameters['FourTerminal_VoltageSteps_Status'] = "StepNumber"
            self.setFourTerminalStepsText()

    def calcStepSize(self, Max, Min, NoS):
        #Calculate the step size from a max, min, and number of steps
        StepSize=float(abs(Max-Min)/float(NoS-1.0))
        return StepSize

    def calcStepNumber(self,Max,Min,SS):
        #Calculates the number of steps given a max, min and step size
        stepnumber=int((Max-Min)/float(SS)+1)
        return stepnumber

    def updateFourTerminalOutput(self):
        #Updates the Output channels. The syntax for commands to the DAC-ADC requires this to be a list
        #This module only ramps one output voltage, so it's a length 1 list with the appropriate index
        self.FourTerminal_ChannelOutput[0] = self.comboBox_FourTerminal_Output.currentIndex()

    def updateFourTerminalInput1(self):
        #Updates the Input channels. The syntax for commands to the DAC-ADC requires this to be a list
        #This module measures one or two inputs.
        #This function updates the first element of the input list is the appropriate index
        self.FourTerminal_ChannelInput[0] = self.comboBox_FourTerminal_Input1.currentIndex()

    def updateFourTerminalInput2(self):
        #Updates the Input channels. The syntax for commands to the DAC-ADC requires this to be a list
        #This module measures one or two inputs.
        #This function updates the second element of the inputs list.
        #The combo box index of 4 corresponds to "No input 2" having been selected in the GUI, in which
        #case the input list should only have one element.
        ind = self.comboBox_FourTerminal_Input2.currentIndex() #The index
        len = np.size(self.FourTerminal_ChannelInput) #Length of channel list

        if ind < 4 and len == 2:
            self.FourTerminal_ChannelInput[1] = ind
        elif ind < 4 and len == 1:
            self.FourTerminal_ChannelInput.append(ind)
        elif ind == 4 and len == 2:
            self.FourTerminal_ChannelInput.pop()
        elif ind == 4 and len ==1:
            pass

    def updateLockinMultipliers(self):
        #Update Multiplier for Voltage and Current from the comboBoxes
        Voltage_LI_Multiplier1=int(self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentText())
        Voltage_LI_Multiplier2=int(self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentText())
        Voltage_LI_Multiplier3=float(self.lockInExponentDict[str(self.comboBox_Voltage_LI_Sensitivity_Unit.currentText())])
        Voltage_LI_Multiplier4=float(self.comboBox_Voltage_LI_Expand.currentText())
        Current_LI_Multiplier1=int(self.comboBox_Current_LI_Sensitivity_1stdigit.currentText())
        Current_LI_Multiplier2=int(self.comboBox_Current_LI_Sensitivity_2nddigit.currentText())
        Current_LI_Multiplier3=float(self.lockInExponentDict[str(self.comboBox_Current_LI_Sensitivity_Unit.currentText())])
        Current_LI_Multiplier4=float(self.comboBox_Current_LI_Expand.currentText())

        self.lockinVoltageMultiplier = Voltage_LI_Multiplier1*Voltage_LI_Multiplier2*Voltage_LI_Multiplier3*Voltage_LI_Multiplier4
        self.lockinCurrentMultiplier = Current_LI_Multiplier1*Current_LI_Multiplier2*Current_LI_Multiplier3*Current_LI_Multiplier4

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for updating the 1D field sweep settings"""

    def updateFieldSweep1DSteps(self):
        #Updates the 1D field sweep steps. This gets its own function to allow the UI to toggle between entering StepNumber and StepSize
        val = readNum(str(self.lineEdit_1DFieldSweepSetting_Numberofsteps.text()))
        if isinstance(val,float):
            if self.sweepParameters['FieldSweep1D_FieldSteps_Status'] == "StepNumber":   #based on status, dummyval is deterimined and update the Numberof steps parameters
                self.sweepParameters['FieldSweep1D_FieldSteps']=int(round(val))
            if self.sweepParameters['FieldSweep1D_FieldSteps_Status'] == "StepSize":
                self.sweepParameters['FieldSweep1D_FieldSteps']=int(self.calcStepNumber(self.sweepParameters['FieldSweep1D_MaxField'],self.sweepParameters['FieldSweep1D_MinField'], float(val)))
        self.setFieldSweep1DStepsText()

    def setFieldSweep1DStepsText(self):
        #Update the lineEdit taking into account the GUI display status
        if self.sweepParameters['FieldSweep1D_FieldSteps_Status'] == "StepNumber":
            self.lineEdit_1DFieldSweepSetting_Numberofsteps.setText(formatNum(self.sweepParameters['FieldSweep1D_FieldSteps'],6))
        else:
            self.lineEdit_1DFieldSweepSetting_Numberofsteps.setText(formatNum(self.calcStepSize(self.sweepParameters['FieldSweep1D_MaxField'],self.sweepParameters['FieldSweep1D_MinField'],self.sweepParameters['FieldSweep1D_FieldSteps']),6))

    def toggleFieldSweep1DSteps(self):
        #Toggle between GUI StepNumber and StepSize input for field points in the 1D field sweep tab
        if self.sweepParameters['FieldSweep1D_FieldSteps_Status'] == "StepNumber":
            self.label_FieldSweep1D_NumberofStep.setText('Tesla per Steps')
            self.sweepParameters['FieldSweep1D_FieldSteps_Status'] = "StepSize"
            self.setFieldSweep1DStepsText() #Change the text first
        else:
            self.label_FieldSweep1D_NumberofStep.setText('Number of Steps')
            self.sweepParameters['FieldSweep1D_FieldSteps_Status'] = "StepNumber"
            self.setFieldSweep1DStepsText() #Change the text first

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for updating the landauFan settings"""

    def updateLandauFanSteps(self):
        #Updates the landau fan steps. This gets its own function to allow the UI to toggle between entering StepNumber and StepSize
        val = readNum(str(self.lineEdit_landauFan_Steps.text()))
        if isinstance(val,float):
            if self.sweepParameters['landauFan_FieldSteps_Status'] == "StepNumber":   #based on status, dummyval is deterimined and update the Numberof steps parameters
                self.sweepParameters['landauFan_FieldSteps']=int(round(val))
            if self.sweepParameters['landauFan_FieldSteps_Status'] == "StepSize":
                self.sweepParameters['landauFan_FieldSteps']=int(self.calcStepNumber(self.sweepParameters['landauFan_MaxField'],self.sweepParameters['landauFan_MinField'],float(val)))
        self.setLandauFanStepsText()

    def setLandauFanStepsText(self):
        #Update the lineEdit taking into account the GUI display status
        if self.sweepParameters['landauFan_FieldSteps_Status'] == "StepNumber":
            self.lineEdit_landauFan_Steps.setText(formatNum(self.sweepParameters['landauFan_FieldSteps'],6))
        else:
            self.lineEdit_landauFan_Steps.setText(formatNum(self.calcStepSize(self.sweepParameters['landauFan_MaxField'],self.sweepParameters['landauFan_MinField'],self.sweepParameters['landauFan_FieldSteps']),6))

    def toggleLandauFanSteps(self):
        #Toggle between GUI StepNumber and StepSize input for field points in the landau fan tab
        if self.sweepParameters['landauFan_FieldSteps_Status'] == "StepNumber":
            self.label_landauFan_FieldSteps.setText('Tesla per Steps')
            self.sweepParameters['landauFan_FieldSteps_Status'] = "StepSize"
            self.setLandauFanStepsText() #Change the text first
        else:
            self.label_landauFan_FieldSteps.setText('Number of Steps')
            self.sweepParameters['landauFan_FieldSteps_Status'] = "StepNumber"
            self.setLandauFanStepsText() #Change the text first

#----------------------------------------------------------------------------------------------#
    """ The following section a functions for manually setting DAC output voltages"""

    @inlineCallbacks
    def setDACOutput(self, channel):
        #Set the DAC output using the ramp1 command that updates the GUI
        #Ramps from the current value to the desired (setpoint) value
        try:
            yield self.ramp1_display(channel, self.DAC_output[channel], self.DAC_setpoint[channel], 10000, 100)
        except:
            printErrorInfo()

    def setDACSetpoint(self, channel, lineEdit):
        #Set the DAC setpoint
        val = readNum(str(lineEdit.text()))
        if isinstance(val, float) and val <= 10.0 and val >= -10.0:
            self.DAC_setpoint[channel] = val
        lineEdit.setText(formatNum(self.DAC_setpoint[channel],6))

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for running sweeps and saving their data"""

    @inlineCallbacks
    def newDataVaultFile(self, sweep_type):
        #Creates a new data vault file. The 'sweep_type' parameter changes the name and parameters of the file
        #appropriately for different sweep modes

        #datavaultYaxis is the list of dependent variables on the sweep
        datavaultYaxis = ["Voltage"]
        if np.size(self.FourTerminal_ChannelInput) == 2:  #add additional data if Input 2 is not None
            datavaultYaxis=["Voltage", "Current", "Resistance", "Conductance"]

        #datavaultXaxis is the list of independent variables on the sweep
        if sweep_type == 'MagneticField1D': #1D field sweep sweep
            datavaultXaxis=['Magnetic Field index', 'Magnetic Field']
            file = yield self.dv.new('1D Magnetic Field ' + self.Device_Name, datavaultXaxis, datavaultYaxis)
        elif sweep_type == "Landau Fan":
            datavaultXaxis=['Magnetic Field index', 'Gate Voltage index', 'Magnetic Field', 'Gate Voltage']
            file = yield self.dv.new('FourTerminal MagneticField ' + self.Device_Name, datavaultXaxis, datavaultYaxis)
        else: #Four Terminal measurement
            datavaultXaxis=['Gate Voltage index', 'Gate Voltage']
            file = yield self.dv.new('FourTerminal ' + self.Device_Name, datavaultXaxis, datavaultYaxis)

        self.dvFileName = file[1] #read the name
        self.lineEdit_ImageNumber.setText(file[1][0:5])
        session  = ''
        for folder in file[0][1:]:
            session = session + '\\' + folder
        self.lineEdit_ImageDir.setText(r'\.datavault' + session)

        yield self.dv.add_parameter('Voltage Lock in Sensitivity (V)', self.lockinVoltageMultiplier)
        yield self.dv.add_parameter('Voltage Lock in Expand', str(self.comboBox_Voltage_LI_Expand.currentText()))
        yield self.dv.add_parameter('Current Lock in Sensitivity (A)', self.lockinCurrentMultiplier)
        yield self.dv.add_parameter('Current Lock in Expand', str(self.comboBox_Current_LI_Expand.currentText()))
        yield self.dv.add_parameter('Voltage Lock in Time Constant(s)', self.sweepParameters['Voltage_tc'])
        yield self.dv.add_parameter('Current Lock in Time Constant(s)', self.sweepParameters['Current_tc'])
        yield self.dv.add_parameter('Lock in Frequency(Hz)', float(self.sweepParameters['Frequency']))
        if sweep_type == "MagneticField1D":
            yield self.dv.add_parameter('DAC Voltage 1',str(self.lineEdit_DACOut1.text()))
            yield self.dv.add_parameter('DAC Voltage 2',str(self.lineEdit_DACOut2.text()))
            yield self.dv.add_parameter('DAC Voltage 3',str(self.lineEdit_DACOut3.text()))
            yield self.dv.add_parameter('DAC Voltage 4',str(self.lineEdit_DACOut4.text()))

    def formatData(self, min, max, points, data, fieldIndex = None, sweep_type = "FourTerminal"):
        """
        Formats the provided buffer ramp data for data vault and plotting.
        The data is either 1 or 2, 1D arrays of measurements made at corresponding gate voltages,
        specified by the min voltage, max voltage, and number of points.
        When the sweep_type is specified to be "Landau Fan", the data is formatted assuming it
        corresponds to a line at field of a Landau Fan

        Data for datavault is a list of touples with all the necessary information.
        Data for plotting is a list of 1D arrays with entries corresponding to the gate voltage,
        measured voltage, current, resistance, and conductance
        """

        formatted_data = [] #Data formatted properly to be added to datavault
        plot_data = [] #Data formatted properly to enable easy plotting

        for i in range(0,5):
            #plot_data has 5 columns. gate voltage points, measured voltage, current, resistance, and conductance
            plot_data.append(np.zeros(points))

        #Generate gate voltage point array from input variables
        plot_data[0] = np.linspace(min, max, points)

        #interate through all the points in the buffer ramp
        for j in range(0, points):
            #Calculate real voltage from the measured voltage
            voltage = self.calculateRealVoltage(data[0][j])

            #Add touples to formatted data for data vault with voltage data
            if sweep_type == "Landau Fan":
                formatted_data.append((fieldIndex, j, self.landauFanFieldPoints[self.i], self.fourTerminalGatePoints[j], voltage))
            else:
                formatted_data.append((j, plot_data[0][j], voltage))

            #Add the data to the 1D array in the plot data
            plot_data[1][j] = voltage

            if np.size(self.FourTerminal_ChannelInput) == 2:  #add additional data if Input2 is not None
                #First convert measured voltage to a real current
                current = self.calculateRealCurrent(data[1][j])

                #Calculate the resistance and conductance from the voltage and current values
                resistance, conductance =self.calculateResistance(voltage,current)

                #Add the values to both the data vault and plotting formatted datasets
                formatted_data[i] += (current, resistance, conductance,)

                plot_data[2][i] = current
                plot_data[3][i] = resistance
                plot_data[4][i] = conductance

        return [formatted_data, plot_data]

    @inlineCallbacks
    def startFourTerminalSweep(self):
        #The Four Terminal Sweep versus gate voltage at a constant magnetic field
        self.lockInterface() #Lock the GUI while sweeping to prevent user from changing sweep parameters mid sweep
        try:
            self.clearFourTerminalPlots() #Remove previous data from the four terminal sweep plots

            #Make local shorter variables for voltage sweep parameters
            points = self.sweepParameters['FourTerminal_VoltageSteps']
            max = self.sweepParameters['FourTerminal_MaxVoltage']
            min = self.sweepParameters['FourTerminal_MinVoltage']
            delay = self.sweepParameters['FourTerminal_Delay']*1000000 #Get delay in units of microseconds

            #Creates a new "Four Terminal" measurment datavault file and updates the image number and directory lineEdits
            yield self.newDataVaultFile("Four Terminal")

            #First ramp the output voltage of the gate channel from the current output voltage value to the starting voltage of the sweep
            yield self.ramp1_display(self.FourTerminal_ChannelOutput[0], self.DAC_output[self.FourTerminal_ChannelOutput[0]],
                                     self.sweepParameters['FourTerminal_MinVoltage'], 10000, 100)

            #Wait a second after the ramp to allow transients to settle before starting the sweep
            yield self.sleep(1)

            #Do a buffer ramp with the DAC-ADC
            #dac_read[0] is the measured voltage array, dac_read[1] is the measured current array
            dac_read = yield self.buffer_ramp_display(self.FourTerminal_ChannelOutput, self.FourTerminal_ChannelInput, [min], [max], points, delay)

            #Take the buffer ramp data and format it both for saving to data vault and plotting
            formatted_data, plot_data = self.formatData(min, max, points, dac_read)

            #Add the data to data vault
            yield self.dv.add(formatted_data)

            #Plot the data
            yield self.plotFourTerminalData(plot_data)

            #Ramp the output gate voltage back down to zero after the sweep is done
            yield self.ramp1_display(self.FourTerminal_ChannelOutput[0],self.sweepParameters['FourTerminal_MaxVoltage'],0.0,10000,100)
        except:
            printErrorInfo()

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save a screenshot of the data

        #Return the formatted_data so that, if called from scripting window, it can be saved into another datavault file
        returnValue(formatted_data)

    @inlineCallbacks
    def startFieldSweep1D(self):
        #Performs a measurement of the lock ins with a varying magnetic field at constant gate voltage
        #If the 'loop' checkbox is checked, this sweeps in both directions investigating the presence of hysteresis

        self.lockInterface() #Lock the GUI while sweeping to prevent user from changing sweep parameters mid sweep
        self.abortMagneticFieldSweep_Flag = False #By default, the sweep is not aborted

        try:
            self.clearFieldSweep1DPlots() #First remove previous data from 1D field sweep
            plot_data = yield self.fieldSweep1D('Up') #Do a field sweep from the minimum to maximum field. This saves the data to data vault
            self.plotFieldSweep1DData(plot_data, 'r') #Plot the hysteresis sweep results. Red line corresponds to sweeping "Up", from min to max

            #If the 'loop' checkbox is checked and the sweep has not been aborted, run a sweep in the other direction
            if self.checkBox_FieldSweep1D_Loop.isChecked() and self.abortMagneticFieldSweep_Flag == False:
                yield self.sleep(1) #Wait a second for everything to settle before sweeping in the other direction
                plot_data = yield self.fieldSweep1D('Down') #Do the field sweep from the maximum to the minimum field
                self.plotFieldSweep1DData(plot_data, 'b') #Plot the hysteresis sweep results. Blue line corresponds to sweeping "Down", from max to min

            #If the 'ZeroField' checkbox is checked and the sweep has not been aborted, zero the magnetic field
            if self.checkBox_FieldSweep1D_ZeroField.isChecked() and self.abortMagneticFieldSweep_Flag == False:
                print('Set magnetic field  to: ' + str(0))
                yield self.rampMagneticField(0, self.sweepParameters['FieldSweep1D_SweepSpeed'])

        except:
            printErrorInfo()

        self.unlockInterface() #unlock the interface when done
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #Save a screenshot of the data

    @inlineCallbacks
    def fieldSweep1D(self, direction):
        #Function both does a 1D field sweep and formats all the data as required for data vault
        #and plotting. The data is added directly to data vault, and the plotting data is returned

        #If sweeping "up" go from mininum to maximum field
        if direction == 'Up':
            start = self.sweepParameters['FieldSweep1D_MinField']
            stop = self.sweepParameters['FieldSweep1D_MaxField']
        #If sweeping "down" go from maximum to minimum
        else:
            start = self.sweepParameters['FieldSweep1D_MaxField']
            stop = self.sweepParameters['FieldSweep1D_MinField']

        #Make local shorter variables for number of points and speed of the field ramp
        points = self.sweepParameters['FieldSweep1D_FieldSteps']
        speed = self.sweepParameters['FieldSweep1D_SweepSpeed']
        delay = self.sweepParameters['FieldSweep1D_Delay']

        self.abortMagneticFieldSweep_Flag = False #By default, the sweep is not aborted

        print('1D Magnetic Field sweep from ', start, ' (T) to ', stop, ' (T) with ramp speed', speed, ' (T/min).')

        try:
            yield self.newDataVaultFile("MagneticField1D") #Creates a new datavault file and updates the image number and directory lineEdits

            formatted_data = [] #Data formatted properly to be added to datavault
            plot_data = [] #Data formatted properly to enable easy plotting

            for i in range(0,5):
                plot_data.append(np.zeros(points)) #plot_data has 5 columns. field points, measured voltage, current, resistance, and conductance

            #Generate field points array from known variables
            fieldPoints = np.linspace(start, stop, points)
            #Make the first column of the plot_data the field points
            plot_data[0] = fieldPoints

            #Loop through all the field points
            for i in range(0, points):
                #Abort loop if Abort flag has been raised
                if self.abortMagneticFieldSweep_Flag:
                    print("Abort the Sweep.")
                    break

                #Set the magnetic field to the next point
                print('Set magnetic field  to: ' + str(fieldPoints[i]))
                yield self.rampMagneticField(fieldPoints[i], speed)

                #Wait the required delay before measuring
                yield self.sleep(delay)

                reading = [] #Create a short list of 1 or 2 values corresponding to the voltage and current readings
                for channel in self.FourTerminal_ChannelInput:
                    val = yield self.dac.read_voltage(channel)
                    reading.append(val)

                voltage = self.calculateRealVoltage(reading[0]) #Convert first reading to a real voltage using the set multipliers
                formatted_data.append((i, fieldPoints[i], voltage)) #Add it to the data vault formatted data array
                plot_data[1][i] = voltage #and the plot data

                #If a current was also measured, then add the following data
                if np.size(self.FourTerminal_ChannelInput) == 2:
                    #First convert measured voltage to a real current
                    current = self.calculateRealCurrent(reading[1])

                    #Calculate the resistance and conductance from the voltage and current values
                    resistance, conductance =self.calculateResistance(voltage,current)

                    #Add the values to both the data vault and plotting formatted datasets
                    formatted_data[i] += (current, resistance, conductance)

                    plot_data[2][i] = current
                    plot_data[3][i] = resistance
                    plot_data[4][i] = conductance

            #Add data to datavault.
            #If the sweep is aborted midway, this will add the data that was taken
            yield self.dv.add(formatted_data)

            #Return the plot_data
            returnValue(plot_data)

        except:
            printErrorInfo()

    @inlineCallbacks
    def startLandauFanSweep(self):
        #The FourTerminal Sweep with Magnetic Field. This is a Landau fan

        self.lockInterface() #Lock the GUI while sweeping to prevent user from changing sweep parameters mid sweep

        #Create shorter local variable names
        bmin = self.sweepParameters['landauFan_MinField']
        bmax = self.sweepParameters['landauFan_MaxField']
        bpoints = self.sweepParameters['landauFan_FieldSteps']
        bspeed = self.sweepParameters['landauFan_SweepSeed']

        vmin = self.sweepParameters['FourTerminal_MinVoltage']
        vmax = self.sweepParameters['FourTerminal_MaxVoltage']
        vpoints = self.sweepParameters['FourTerminal_VoltageSteps']
        vdelay = self.sweepParameters['FourTerminal_Delay']*1000000 #Get delay in microseconds

        #Create class variables for the voltage and field axes.
        #The 2D plot data are class variables so that the linecuts can interact with the 2D plots
        self.landauFanFieldPoints = np.linspace(bmin, bmax, bpoints) #Generate magnetic field sweep point array
        self.fourTerminalGatePoints = np.linspace(vmin, vmax, vpoints) #Generating gate voltage speed points array

        #Generate landau zero data
        self.landauFanResistanceData = np.zeros([bpoints, vpoints])
        self.landauFanConductanceData = np.zeros([bpoints, vpoints])
        self.landauFanVoltageData = np.zeros([bpoints, vpoints])
        self.landauFanCurrentData = np.zeros([bpoints, vpoints])

        self.clearLandauFanPlots() #Clear all the LandauFanPlots, 2D and 1D alike
        self.updateImageViewScale() #Recalculate the position and scale for the 2D plots
        self.autoRangeFourTerminal2DPlot() #plots the zero data and sets the range of the 2D plot appropriately around it

        self.abortMagneticFieldSweep_Flag = False #Set sweep abort flag to false

        try:
            #Create new data vault file for Landau Fan style data
            yield self.newDataVaultFile("Landau Fan")

            for i in range(0,self.sweepParameters['landauFan_FieldSteps']):

                #If abort sweep flag is raised, break out of the loop
                if self.abortMagneticFieldSweep_Flag:
                    print("Abort the Sweep.")
                    break

                print('Starting sweep with magnetic field set to: ' + str(self.landauFanFieldPoints[self.i]))

                #Go to the next field
                yield self.rampMagneticField(self.landauFanFieldPoints[i], bspeed)

                #If abort sweep flag is raised, break out of the loop
                if self.abortMagneticFieldSweep_Flag:
                    print("Abort the Sweep.")
                    break

                #ramp to initial output voltage value from current value
                yield self.ramp1_display(self.FourTerminal_ChannelOutput[0],self.DAC_output[self.FourTerminal_ChannelOutput[0]], vmin, 10000, 100)

                #Wait one second to allow transients to settle
                yield self.sleep(1)

                #If abort sweep flag is raised, break out of the loop
                if self.abortMagneticFieldSweep_Flag:
                    print("Abort the Sweep.")
                    break

                #Perform a buffer ramp and format the data
                dac_read = yield self.buffer_ramp_display(self.FourTerminal_ChannelOutput, self.FourTerminal_ChannelInput, [vmin], [vmax], vpoints, vdelay)
                formatted_data, plot_data = self.formatData(vmin, vmax, vpoints, dac_read, i, "Landau Fan")

                #Add the formatted data to datavault
                yield self.dv.add(self.formatted_data)

                #Update the 2D plots. This also adds the latest line of data to the self.landauFanData instances
                yield self.updateLandauFan2DPlots(i, plot_data)

                #If the update linecut checkbox is checked
                if self.checkBox_landauFan_LatestLinecut.isChecked():
                    #Set the desired position of the gateLinecut
                    self.landauFanGateLinecutPosition = self.landauFanFieldPoints[i]
                    #Update the lineEdit with the new field
                    self.lineEdit_landauFan_GateLinecut.setText(formatNum(self.landauFanGateLinecutPosition, 6))
                    #Update the linecut plots for the new linecut and then update the position of the linecut objects
                    self.updateLandauFanLinecutPlots()
                    self.setLandauFanLinecutPosition()

                #If the autoLevel checkbox is checked, autoLevel the 2D plots
                if self.checkBox_landauFan_AutoLevel.isChecked():
                    self.autoLevelFourTerminal2DPlot()

                #Ramp the output voltage back to zero before continuing in the loop and changing the magnetic field
                yield self.ramp1_display(self.FourTerminal_ChannelOutput[0],self.sweepParameters['FourTerminal_MaxVoltage'],0.0,10000,100)

            #After the landau fan is done, if the zero field checkbox is checked ramp the field back to zero
            if self.checkBox_landauFan_ZeroField.isChecked():
                print("Ramp Field Back to Zero")
                yield self.rampMagneticField(0.0, self.sweepParameters['landauFan_SweepSeed'])

        except:
            printErrorInfo()

        self.unlockInterface() #Unlock the interface when done
        yield self.sleep(0.25) #Wait a quarter second before saving a screenshot
        self.saveDataToSessionFolder() #save the screenshot

    def abortMagneticFieldSweep(self):
        self.abortMagneticFieldSweep_Flag = True

    @inlineCallbacks
    def rampMagneticField(self, end, rate):
        '''Ramp the magnetic field to 'end' in units of Tesla, at a rate of 'rate' in T/minute
        This function is only compatible with the ips120 power supply. Eventually, specific magnet power supplies should
        be abstracted into a magnetPowerSupply object since the software is likely to operate with different power supplies
        on different set ups.
        '''
        try:
            yield self.gotoSetIPS(end, rate) #Set the setpoint and update the IPS mode to sweep to field

            print('Setting field to ' + str(end))

            #Only finish running the gotoField function when the field is reached
            t0 = time.time() #Keep track of starting time for setting the field
            while True:
                #if after one second we still haven't reached the desired field, then reset the field setpoint
                #Sometimes communication is buggy and repeated attempts helps
                if time.time() - t0 > 1:
                    print('restarting loop')
                    yield self.gotoSetIPS(end, rate)
                    t0 = time.time()
                yield self.sleep(0.25)
                curr_field = yield self.ips.read_parameter(7)
                #if within 10 uT of the desired field, break out of the loop
                if float(curr_field[1:]) <= end + 0.00001 and float(curr_field[1:]) >= end - 0.00001:
                    break
                elif self.abortMagneticFieldSweep_Flag:
                    break

        except:
            printErrorInfo()

    @inlineCallbacks
    def goToSetpointIPS(self, B, rate):
        yield self.ips.set_control(3) #Set IPS to remote communication (prevents user from using the front panel)
        yield self.ips.set_fieldsweep_rate(rate) #Set IPS ramp rate in T/min
        yield self.ips.set_targetfield(B) #Set targetfield to desired field in T
        yield self.ips.set_activity(1) #Set IPS mode to ramping instead of hold
        yield self.ips.set_control(2) #Set IPS to local control (allows user to edit IPS from the front panel)

    def saveDataToSessionFolder(self):
        try:
            p = QtGui.QPixmap.grabWindow(self.winId())
            a = p.save(self.sessionFolder + '\\' + self.dvFileName + '.jpg','jpg')
            if not a:
                print("Error saving Scan data picture")
        except:
            printErrorInfo()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for setting the DAC-ADC voltage at the same time as the UI"""

    @inlineCallbacks
    def ramp1_display(self, DAC_channel, start, end, steps, delay):
        #Function uses the DAC-ADC ramp1 function and updates the GUI
        #Delay is provided in units of microseconds
        try:
            self.label_DACOout_list[DAC_channel].setText('Sweeping')
            yield self.dac.ramp1(DAC_channel, start, end, steps, delay)
            self.DAC_output[DAC_channel] = end
            self.label_DACOout_list[DAC_channel].setText(formatNum(end, 6))

            #Ramp1 does not clear the buffer properly if the ramp takes more than 1s (the timeout
            #of serial communication)
            if steps*delay/1e6  > 0.7:
                yield self.clearBufferedData()
        except:
            printErrorInfo()

    @inlineCallbacks
    def clearBufferedData(self):
        #Needs to be called after a long dac.ramp1 (as the ramp function does not read all the data)
        a = yield self.dac.read()
        while a != '':
            print(a)
            a = yield self.dac.read()

    @inlineCallbacks
    def buffer_ramp_display(self, DAC_Out_Channels, DAC_In_Channels, start, stop, steps, delay):
        #Performs a buffer ramp and updates the GUI appropriately
        try:
            self.label_DACOout_list[DAC_Out_Channels[0]].setText('Sweeping')
            data = yield self.dac.buffer_ramp(DAC_Out_Channels, DAC_In_Channels, start, stop, steps, delay)
            self.label_DACOout_list[DAC_Out_Channels[0]].setText(formatNum(stop, 6))
            returnValue(data)
        except:
            printErrorInfo()

    def calculateRealVoltage(self,reading):
        #Take the DAC reading and convert it to real unit (V)
        realVoltage=float(reading)/10.0*self.lockinVoltageMultiplier
        return realVoltage

    def calculateRealCurrent(self,reading): \
        #Take the DAC reading and convert it to real unit (A)
        realCurrent=float(reading)/10.0*self.lockinCurrentMultiplier
        return realCurrent

    def calculateResistance(self, voltage, current):
        #Take the DAC voltage and current readings and convert them to resistance / conductance
        if current != 0.0:
            resistance=float(voltage/current) # generating resistance
        else:
            resistance=float(voltage/0.0000000001)# Prevent divide by zero bug

        if resistance != 0:
            conductance = 1/resistance
        else:
            conductance = 0

        return [resistance, conductance]

#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""

    def setFourTermMinVoltage(self, vmin):
        self.lineEdit_FourTerminal_MinVoltage.setText(formatNum(vmin))
        self.updateSweepParameter(self.lineEdit_FourTerminal_MinVoltage, 'FourTerminal_MinVoltage', [-10.0, 10.0])

    def setFourTermMaxVoltage(self, vmax):
        self.lineEdit_FourTerminal_MaxVoltage.setText(formatNum(vmax))
        self.updateSweepParameter(self.lineEdit_FourTerminal_MaxVoltage, 'FourTerminal_MaxVoltage', [-10.0, 10.0])

    def setFourTermVoltagePoints(self, points):
        if self.sweepParameters['FourTerminal_VoltageSteps_Status'] == "StepSize":
            self.toggleFourTerminalSteps()
        self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(points))
        self.updateFourTerminalSteps()

    def setFourTermVoltageStepSize(self, vstep):
        if self.sweepParameters['FourTerminal_VoltageSteps_Status'] == "StepNumber":
            self.toggleFourTerminalSteps()
        self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(vstep))
        self.updateFourTerminalSteps()

    def setFourTermDelay(self, delay):
        self.lineEdit_FourTerminal_Delay.setText(formatNum(delay))
        self.updateSweepParameter(self.lineEdit_FourTerminal_Delay, 'FourTerminal_Delay')

    def setFourTermOutput(self, output):
        self.comboBox_FourTerminal_Output.setCurrentIndex(output-1)
        self.FourTerminal_ChannelOutput[0] = output-1

    def setFourTermVoltageInput(self, input):
        self.comboBox_FourTerminal_Input1.setCurrentIndex(input-1)
        self.FourTerminal_ChannelInput[0] = input-1

    def setFourTermCurrentInput(self, input):
        self.comboBox_FourTerminal_Input2.setCurrentIndex(input-1)
        self.updateFourTerminalInput2()

    @inlineCallbacks
    def rampOutputVoltage(self, channel, vfinal, points, delay):
        #Convert delay from seconds to microseconds.
        delay = int(delay*1e6)
        channel = channel - 1
        yield self.ramp1_display(channel, self.DAC_output[channel], vfinal, points, delay)

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def lockInterface(self):
        self.lineEdit_FourTerminal_Output.setEnabled(False)
        self.lineEdit_FourTerminal_Input1.setEnabled(False)
        self.lineEdit_FourTerminal_Input2.setEnabled(False)
        self.lineEdit_FourTerminal_MinVoltage.setEnabled(False)
        self.lineEdit_FourTerminal_MaxVoltage.setEnabled(False)
        self.lineEdit_FourTerminal_Numberofstep.setEnabled(False)
        self.lineEdit_FourTerminal_Delay.setEnabled(False)
        self.pushButton_FourTerminalStepSwitch.setEnabled(False)

        self.lineEdit_landauFan_MinField.setEnabled(False)
        self.lineEdit_landauFan_MaxField.setEnabled(False)
        self.lineEdit_landauFan_Steps.setEnabled(False)
        self.lineEdit_landauFan_FieldSpeed.setEnabled(False)
        self.pushButton_landauFanStepSwitch.setEnabled(False)
        self.pushButton_StartLandauFan.setEnabled(False)

        self.comboBox_FourTerminal_Output.setEnabled(False)
        self.comboBox_FourTerminal_Input1.setEnabled(False)
        self.comboBox_FourTerminal_Input2.setEnabled(False)
        self.comboBox_Voltage_LI_Sensitivity_1stdigit.setEnabled(False)
        self.comboBox_Voltage_LI_Sensitivity_2nddigit.setEnabled(False)
        self.comboBox_Voltage_LI_Expand.setEnabled(False)
        self.comboBox_Voltage_LI_Sensitivity_Unit.setEnabled(False)
        self.comboBox_Current_LI_Sensitivity_1stdigit.setEnabled(False)
        self.comboBox_Current_LI_Sensitivity_2nddigit.setEnabled(False)
        self.comboBox_Current_LI_Sensitivity_Unit.setEnabled(False)
        self.comboBox_Current_LI_Expand.setEnabled(False)
        self.lineEdit_voltageTC.setEnabled(False)
        self.lineEdit_currentTC.setEnabled(False)
        self.lineEdit_lockinFrequency.setEnabled(False)

        self.pushButton_Start1DFieldSweep.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_MinimumField.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_MaximumField.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_Delay.setEnabled(False)

        self.pushButton_StartFourTerminalSweep.setEnabled(False)

        self.lineEdit_DACOut1.setEnabled(False)
        self.lineEdit_DACOut2.setEnabled(False)
        self.lineEdit_DACOut3.setEnabled(False)
        self.lineEdit_DACOut4.setEnabled(False)
        self.pushButton_DACOut1.setEnabled(False)
        self.pushButton_DACOut2.setEnabled(False)
        self.pushButton_DACOut3.setEnabled(False)
        self.pushButton_DACOut4.setEnabled(False)

    def unlockInterface(self):
        self.lineEdit_FourTerminal_Output.setEnabled(True)
        self.lineEdit_FourTerminal_Input1.setEnabled(True)
        self.lineEdit_FourTerminal_Input2.setEnabled(True)
        self.lineEdit_FourTerminal_MinVoltage.setEnabled(True)
        self.lineEdit_FourTerminal_MaxVoltage.setEnabled(True)
        self.lineEdit_FourTerminal_Numberofstep.setEnabled(True)
        self.lineEdit_FourTerminal_Delay.setEnabled(True)
        self.pushButton_FourTerminalStepSwitch.setEnabled(True)

        self.lineEdit_landauFan_MinField.setEnabled(True)
        self.lineEdit_landauFan_MaxField.setEnabled(True)
        self.lineEdit_landauFan_Steps.setEnabled(True)
        self.lineEdit_landauFan_FieldSpeed.setEnabled(True)
        self.pushButton_landauFanStepSwitch.setEnabled(True)
        self.pushButton_StartLandauFan.setEnabled(True)

        self.comboBox_FourTerminal_Output.setEnabled(True)
        self.comboBox_FourTerminal_Input1.setEnabled(True)
        self.comboBox_FourTerminal_Input2.setEnabled(True)
        self.comboBox_Voltage_LI_Sensitivity_1stdigit.setEnabled(True)
        self.comboBox_Voltage_LI_Sensitivity_2nddigit.setEnabled(True)
        self.comboBox_Voltage_LI_Sensitivity_Unit.setEnabled(True)
        self.comboBox_Voltage_LI_Expand.setEnabled(True)
        self.comboBox_Current_LI_Sensitivity_1stdigit.setEnabled(True)
        self.comboBox_Current_LI_Sensitivity_2nddigit.setEnabled(True)
        self.comboBox_Current_LI_Sensitivity_Unit.setEnabled(True)
        self.comboBox_Current_LI_Expand.setEnabled(True)
        self.lineEdit_voltageTC.setEnabled(True)
        self.lineEdit_currentTC.setEnabled(True)
        self.lineEdit_lockinFrequency.setEnabled(True)

        self.pushButton_Start1DFieldSweep.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_MinimumField.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_MaximumField.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_Delay.setEnabled(True)

        self.pushButton_StartFourTerminalSweep.setEnabled(True)

        self.lineEdit_DACOut1.setEnabled(True)
        self.lineEdit_DACOut2.setEnabled(True)
        self.lineEdit_DACOut3.setEnabled(True)
        self.lineEdit_DACOut4.setEnabled(True)
        self.pushButton_DACOut1.setEnabled(True)
        self.pushButton_DACOut2.setEnabled(True)
        self.pushButton_DACOut3.setEnabled(True)
        self.pushButton_DACOut4.setEnabled(True)

    def FakeDATA(self,Output,Input,Min,Max,NoS,Delay):
        #debugging function. Can be used to replace DAC buffer ramp function to test
        #module functionality without connecting to hardware
        fake=[]
        xpoints= np.linspace( Min, Max, NoS)
        for i in range(0,len(Input)):
            fake.append([])
            for j in range (0,NoS):
                fake[i].append((1/(abs(xpoints[j])+.5))+(math.cos(0.25/(self.i+0.01)*(0.01+xpoints[j]))+1))
        return fake

class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
