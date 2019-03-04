from __future__ import division
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred , returnValue
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading
import copy
import time
import math #useless if not testing
from scipy.signal import detrend
#importing a bunch of stuff


#In retrospec, it is probably not well thought through in term of the long-term plan of organizing it.

################################################################################################################################

path = sys.path[0] + r"\SampleCharacterizer"
SampleCharacterizerWindowUI, QtBaseClass = uic.loadUiType(path + r"\SampleCharacterizerWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way.
sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView


class Window(QtGui.QMainWindow, SampleCharacterizerWindowUI):

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)

        self.Dict_LockIn= {  #A dictionary for lock in amplifier settings
         'V':1,
         'mV':10**-3,
         'uV':10**-6,
         'nV':10**-9,
         'uA':10**-6,
         'nA':10**-9,
         'pA':10**-12,
         'fA':10**-15,
         }
        
        self.Dict_Variable = {
            'FourTerminal_MinVoltage': -0.1,
            'FourTerminal_MaxVoltage': 0.1,
            'FourTerminal_Numberofstep': 100,
            'FourTerminalSetting_Numberofsteps_Status': "Numberofsteps",
            'FourTerminal_Delay':0.001,
            'FieldSweep1D_MinField': 0,
            'FieldSweep1D_MaxField': 1.0,
            'FieldSweep1D_Numberofstep': 100,
            'FieldSweep1DSetting_Numberofsteps_Status': "Numberofsteps",
            'FieldSweep1D_SweepSpeed': 1.0,
            'FourTerminalMagneticFieldSetting_MinimumField': 0,
            'FourTerminalMagneticFieldSetting_MaximumField': 0.01,
            'FourTerminalMagneticFieldSetting_Numberofsteps': 2,
            'FourTerminalMagneticFieldSetting_Numberofsteps_Status': "Numberofsteps",
            'FourTerminalMagneticFieldSetting_FieldSweepSpeed': 1.0
            }
        self.i=0#delete when FakeDATA is removed

###########################################initialize the DAC and set all the Output to 0##################
        self.currentDAC_Output=[0.0,0.0,0.0,0.0]
        self.setpointDAC_Output=[0.0,0.0,0.0,0.0]

        # for i in range(4):                                              Can be implemented when labradconnect is done
            # self.dac.set_voltage(i,0,0)
                    
        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
            
##################Top Right Block########################
        self.label_CentralDAC_DACOUTPUT1_Current.setText(formatNum(self.currentDAC_Output[0],6))
        self.label_CentralDAC_DACOUTPUT2_Current.setText(formatNum(self.currentDAC_Output[1],6))
        self.label_CentralDAC_DACOUTPUT3_Current.setText(formatNum(self.currentDAC_Output[2],6))
        self.label_CentralDAC_DACOUTPUT4_Current.setText(formatNum(self.currentDAC_Output[3],6))

        self.lineEdit_CentralDAC_DACOUTPUT1.editingFinished.connect(lambda:self.Update_CentralDAC_DACOUTPUT(0))
        self.lineEdit_CentralDAC_DACOUTPUT2.editingFinished.connect(lambda:self.Update_CentralDAC_DACOUTPUT(1))
        self.lineEdit_CentralDAC_DACOUTPUT3.editingFinished.connect(lambda:self.Update_CentralDAC_DACOUTPUT(2))
        self.lineEdit_CentralDAC_DACOUTPUT4.editingFinished.connect(lambda:self.Update_CentralDAC_DACOUTPUT(3))

        self.pushButton_CentralDAC_DACOUTPUT1.clicked.connect(lambda:self.Set_CentralDAC_DACOUTPUT(0))
        self.pushButton_CentralDAC_DACOUTPUT2.clicked.connect(lambda:self.Set_CentralDAC_DACOUTPUT(1))
        self.pushButton_CentralDAC_DACOUTPUT3.clicked.connect(lambda:self.Set_CentralDAC_DACOUTPUT(2))
        self.pushButton_CentralDAC_DACOUTPUT4.clicked.connect(lambda:self.Set_CentralDAC_DACOUTPUT(3))

####################################### Top Left
        self.Device_Name='Device Name'
        self.FourTerminal_NameOutput1='Gate Voltage'
        self.FourTerminal_NameInput1='Voltage'
        self.FourTerminal_NameInput2='Current'
        self.lineEdit_Device_Name.setText(self.Device_Name)
        self.lineEdit_FourTerminal_NameOutput1.setText(self.FourTerminal_NameOutput1)
        self.lineEdit_FourTerminal_NameInput1.setText(self.FourTerminal_NameInput1)
        self.lineEdit_FourTerminal_NameInput2.setText(self.FourTerminal_NameInput2)

        self.lineEdit_FourTerminal_NameOutput1.editingFinished.connect(lambda: self.UpdateLineEdit_PlotLabel(self.lineEdit_FourTerminal_NameOutput1, self.FourTerminal_NameOutput1))
        self.lineEdit_FourTerminal_NameInput1.editingFinished.connect(lambda: self.UpdateLineEdit_PlotLabel(self.lineEdit_FourTerminal_NameInput1, self.FourTerminal_NameInput1))
        self.lineEdit_FourTerminal_NameInput2.editingFinished.connect(lambda: self.UpdateLineEdit_PlotLabel(self.lineEdit_FourTerminal_NameInput2, self.FourTerminal_NameInput2))
        self.lineEdit_Device_Name.editingFinished.connect(lambda: self.UpdateLineEdit_General(self.lineEdit_Device_Name, self.Device_Name))

#################FourTerminal sweep default parameter
        self.FourTerminal_ChannelInput=[]
        self.FourTerminal_ChannelOutput=[]

        self.lineEdit_FourTerminal_MinVoltage.setText(formatNum(self.Dict_Variable['FourTerminal_MinVoltage'],6))
        self.lineEdit_FourTerminal_MaxVoltage.setText(formatNum(self.Dict_Variable['FourTerminal_MaxVoltage'],6))
        self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.Dict_Variable['FourTerminal_Numberofstep'],6))
        self.lineEdit_FourTerminal_Delay.setText(formatNum(self.Dict_Variable['FourTerminal_Delay'],6))

#######################################Lineedit Four Terminial
        self.lineEdit_FourTerminal_MinVoltage.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_FourTerminal_MinVoltage, 'FourTerminal_MinVoltage', [-10.0, 10.0]))
        self.lineEdit_FourTerminal_MinVoltage.editingFinished.connect(self.UpdateFourTerminal_Numberofstep)
        self.lineEdit_FourTerminal_MaxVoltage.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_FourTerminal_MaxVoltage, 'FourTerminal_MaxVoltage', [-10.0, 10.0]))
        self.lineEdit_FourTerminal_MaxVoltage.editingFinished.connect(self.UpdateFourTerminal_Numberofstep)
        self.lineEdit_FourTerminal_Numberofstep.editingFinished.connect(self.UpdateFourTerminal_Numberofstep)
        self.lineEdit_FourTerminal_Delay.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_FourTerminal_Delay, 'FourTerminal_Delay'))
        self.pushButton_FourTerminal_NoSmTpTSwitch.clicked.connect(self.ToggleFourTerminalFourTerminal_Numberofstep)
        
        self.comboBox_FourTerminal_Output1.currentIndexChanged.connect(self.ChangeFourTerminal_Output1_Channel)
        self.comboBox_FourTerminal_Input1.currentIndexChanged.connect(self.ChangeFourTerminal_Input1_Channel)
        self.comboBox_FourTerminal_Input2.currentIndexChanged.connect(self.ChangeFourTerminal_Input2_Channel)
        
#######################################Few Push Button
        self.pushButton_StartFourTerminalSweep.clicked.connect(self.FourTerminalSweep)
        self.pushButton_StartFourTerminalMagneticFieldSweep.clicked.connect(self.FourTerminalMagneticFieldSweep)
        self.pushButton_StartFourTerminalMagneticFieldAbort.clicked.connect(self.AbortMagneticFieldSweep)

#######################################Push Button Field Sweep 1D
        self.pushButton_Abort1DFieldSweep.clicked.connect(self.AbortMagneticFieldSweep)
        self.pushButton_Start1DFieldSweep.clicked.connect(self.StartFieldSweep1D)
        self.pushButton_1DFieldSweepSetting_NoSmTpTSwitch.clicked.connect(self.ToggleFieldSweep1D_NumberofstepsandMilifieldperTesla)

        self.lineEdit_1DFieldSweepSetting_MinimumField.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_1DFieldSweepSetting_MinimumField, 'FieldSweep1D_MinField'))
        self.lineEdit_1DFieldSweepSetting_MinimumField.editingFinished.connect(self.UpdateFieldSweep1D_NumberofstepsandMilifieldperTesla)
        self.lineEdit_1DFieldSweepSetting_MaximumField.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_1DFieldSweepSetting_MaximumField, 'FieldSweep1D_MaxField'))
        self.lineEdit_1DFieldSweepSetting_MaximumField.editingFinished.connect(self.UpdateFieldSweep1D_NumberofstepsandMilifieldperTesla)
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.editingFinished.connect(self.UpdateFieldSweep1D_NumberofstepsandMilifieldperTesla)
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed, 'FieldSweep1D_SweepSpeed'))

#################Four Terminal Magnetic field sweep default parameter

        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.setText(formatNum(self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField'],6))
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.setText(formatNum(self.Dict_Variable['FourTerminalMagneticFieldSetting_MaximumField'],6))
        self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setText(formatNum(self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],6))
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.setText(formatNum(self.Dict_Variable['FourTerminalMagneticFieldSetting_FieldSweepSpeed'],6))
        
        self.comboBox_FourTerminal_Output1.setCurrentIndex(0)
        self.comboBox_FourTerminal_Input1.setCurrentIndex(1)
        self.comboBox_FourTerminal_Input2.setCurrentIndex(0)
        self.FourTerminal_Output1=self.comboBox_FourTerminal_Output1.currentIndex()
        self.FourTerminal_Input1=self.comboBox_FourTerminal_Input1.currentIndex()
        self.FourTerminal_Input2=self.comboBox_FourTerminal_Input2.currentIndex()
        
#################Four Terminal Magnetic field sweep Line Edit
        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField, 'FourTerminalMagneticFieldSetting_MinimumField'))
        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla)
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField, 'FourTerminalMagneticFieldSetting_MaximumField'))
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla)
        self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla)
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.editingFinished.connect(lambda: self.UpdateLineEdit_Parameters(self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed, 'FourTerminalMagneticFieldSetting_FieldSweepSpeed'))
        self.pushButton_FourTerminalMagneticFieldSetting_NoSmTpTSwitch.clicked.connect(self.ToggleFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla)

        self.lineEdit_FourTerminalMagneticFieldSetting_MagneticFieldValue.editingFinished.connect(self.SetupLineCutMagneticFieldValue)
        self.lineEdit_FourTerminalMagneticFieldSetting_GateVoltageValue.editingFinished.connect(self.SetupLineCutGateVoltageValue)
        self.pushButton_FourTerminal2D_AutoLevel.clicked.connect(self.AutoLevelFourTerminal2DPlot)

#######################################Lock In part
        self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.comboBox_Voltage_LI_Sensitivity_Unit.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.comboBox_Voltage_LI_Expand.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.comboBox_Current_LI_Sensitivity_1stdigit.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.comboBox_Current_LI_Sensitivity_2nddigit.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.comboBox_Current_LI_Sensitivity_Unit.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.comboBox_Current_LI_Expand.currentIndexChanged.connect(self.ChangeLockinSettings)
        self.lineEdit_Voltage_LI_Timeconstant.editingFinished.connect(self.UpdateVoltage_LI_Timeconstant)
        self.lineEdit_Current_LI_Timeconstant.editingFinished.connect(self.UpdateCurrent_LI_Timeconstant)
        self.lineEdit_Lockin_Info_Frequency.editingFinished.connect(lambda: self.UpdateLineEdit_General(self.lineEdit_Lockin_Info_Frequency, 'Frequency'))
        self.UpdateVoltage_LI_Timeconstant()
        self.UpdateCurrent_LI_Timeconstant()
        self.UpdateLineEdit_General(self.lineEdit_Lockin_Info_Frequency, 'Frequency')
        
#######################################Check Box magnetic Field Sweep
        self.checkBox_FourTerminalMagneticFieldSetting_MoveLineCut.stateChanged.connect(self.updateCheckBox)
        self.checkBox_FourTerminalMagneticFieldSetting_AutoLevel.stateChanged.connect(self.updateCheckBox)
        self.checkBox_FourTerminalMagneticFieldSetting_BacktoZero.stateChanged.connect(self.updateCheckBox)
        self.checkBox_FieldSweep1D_Loop.stateChanged.connect(self.updateCheckBox)

#################1D Field Sweep default parameter
        self.lineEdit_1DFieldSweepSetting_MinimumField.setText(formatNum(self.Dict_Variable['FieldSweep1D_MinField'], 6))
        self.lineEdit_1DFieldSweepSetting_MaximumField.setText(formatNum(self.Dict_Variable['FieldSweep1D_MaxField'], 6))
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.setText(formatNum(self.Dict_Variable['FieldSweep1D_Numberofstep'], 6))
        self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed.setText(formatNum(self.Dict_Variable['FieldSweep1D_SweepSpeed'], 6))

#######################################Setting For Plotting
        self.randomFill = -0.987654321
        self.current_field = 0.0
        self.posx , self.posy , self.scalex, self.scaley =(0.0,0.0,0.0,0.0)
        self.FourTerminalverticalLineCutPosition , self.FourTerminalhorizontalLineCutPosition=0.0 , 0.0
        self.AbortMagneticFieldSweep_Flag =False
        self.MoveLineCutFourTerminalMagneticFieldSweep_Flag =True
        self.AutoLevelFourTerminalMagneticFieldSweep_Flag =True
        self.BacktoZeroFourTerminalMagneticFieldSweep_Flag =True

        self.PlotDataFourTerminalResistance2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])
        self.PlotDataFourTerminalConductance2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])
        self.PlotDataFourTerminalVoltage2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])
        self.PlotDataFourTerminalCurrent2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])

        self.dvFileName=""
        self.ChangeLockinSettings()
        self.moveDefault()

#######################################


#######################################
        #Initialize all the labrad connections as none
        self.cxn = False
        self.dv = False
        self.dac = False

        self.setupAdditionalUi()

        # self.lockInterface()#Change when not testing

    def moveDefault(self):
        self.move(550,10)

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
            self.dac.select_device(dict['devices']['sample']['dac_adc'])
                
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
                
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            
            self.current_field = yield self.ips.read_parameter(7)#Read the field

            self.unlockInterface()
        except Exception as inst:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  
            #print 'nsot labrad connect', inst
            #exc_type, exc_obj, exc_tb = sys.exc_info()
            #print 'line num ', exc_tb.tb_lineno
        
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
        serList = serversList(self.reactor, self)
        serList.exec_()

    def updateDataVaultDirectory(self):
        curr_folder = yield self.gen_dv.cd()
        yield self.dv.cd(curr_folder)

    def updateHistogramLevels(self, hist):
        mn, mx = hist.getLevels()
        self.Plot2D.ui.histogram.setLevels(mn, mx)
        
    @inlineCallbacks
    def StartFieldSweep1D(self,c=None): #1D sweep as a function of magnetic field #This function is unique
        self.lockInterface()
        try:
            self.ClearFieldSweep1DPlot() #Clear the plotted content

            self.SetupFourTerminalSweepSetting('MagneticField1D') #Assign the DAC settings and DataVault parameters
            
            #Creates a new datavault file and updates the image# labels
            yield self.newDataVaultFile("MagneticField1D")
            
            self.FieldSweep1DXaxis = np.linspace(self.Dict_Variable['FieldSweep1D_MinField'], self.Dict_Variable['FieldSweep1D_MaxField'], self.Dict_Variable['FieldSweep1D_Numberofstep'])
            
            self.SetupPlot_Data("MagneticField1D")#self.Plot_Data: a new set of data particularly for ploting

            print 'Ramp to initial field ' + str(self.Dict_Variable['FieldSweep1D_MinField']) + 'T'
            # yield self.rampMagneticField(self.current_field, self.Dict_Variable['FieldSweep1D_MinField'], self.Dict_Variable['FieldSweep1D_SweepSpeed'])

            self.formatted_data = []

            for self.i in range(0,self.Dict_Variable['FieldSweep1D_Numberofstep']):

            # self.dac_read = self.FakeDATA(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.Dict_Variable['FourTerminal_MinVoltage']],[self.Dict_Variable['FourTerminal_MaxVoltage']],self.Dict_Variable['FourTerminal_Numberofstep'],self.Dict_Variable['FourTerminal_Delay'])
                if self.AbortMagneticFieldSweep_Flag:
                    print "Abort the Sweep."
                    self.AbortMagneticFieldSweep_Flag = False
                    break

                print 'Set magnetic field  to: ' + str(self.FieldSweep1DXaxis[self.i])
                # yield self.rampMagneticField(self.current_field, self.FieldSweep1DXaxis[self.i], self.Dict_Variable['FieldSweep1D_SweepSpeed'])

                reading = []
                for channel in self.FourTerminal_ChannelInput:
                    # reading.append(self.dac.read_voltage(channel))
                    reading.append(self.i)

                DummyVoltage=self.Convert_Real_Voltage(reading[0])
                self.formatted_data.append((self.i, self.FieldSweep1DXaxis[self.i], DummyVoltage))
                self.Plot_Data[2][self.i] = DummyVoltage
                if self.FourTerminal_Input2!=4: 
                    DummyCurrent=self.Convert_Real_Current(reading[1])
                    self.formatted_data[self.i]+=(DummyCurrent,)
                    self.Plot_Data[3][self.i] = DummyCurrent
                    resistance=self.Calculate_Resistance(DummyVoltage,DummyCurrent)
                    if resistance == 0 :
                        Conductance = 0.0
                    else:
                        Conductance = 1/resistance
                    self.formatted_data[self.i]+=(resistance,)  #proccessing to Resistance
                    self.formatted_data[self.i]+=(Conductance,)  #proccessing to Conductance
                    self.Plot_Data[4][self.i] = resistance
                    self.Plot_Data[5][self.i] = Conductance
                
                self.plotData1D(self.Plot_Data[1],self.Plot_Data[2],self.FieldSweep1D_Plot1, 'r')
                if self.FourTerminal_Input2!=4:
                     self.plotData1D(self.Plot_Data[1],self.Plot_Data[3],self.FieldSweep1D_Plot2, 'r') #xaxis, yaxis, plot
                     self.plotData1D(self.Plot_Data[1],self.Plot_Data[4],self.FieldSweep1D_Plot3, 'r') #xaxis, yaxis, plot
                     self.plotData1D(self.Plot_Data[1],self.Plot_Data[5],self.FieldSweep1D_Plot4, 'r') #xaxis, yaxis, plot
                 
            yield self.dv.add(self.formatted_data)
            
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save the screenshot


    @inlineCallbacks
    def FourTerminalSweep(self,c=None): #The Four Terminal Sweep without MagneticField
        self.lockInterface()
        try:
            self.ClearFourTerminalPlot() #Clear the plotted content

            self.SetupFourTerminalSweepSetting("No Magnetic Field") #Assign the DAC settings and DataVault parameters
            
            #Creates a new datavault file and updates the image# labels
            yield self.newDataVaultFile("No Magnetic Field")

            yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.currentDAC_Output[self.FourTerminal_ChannelOutput[0]],self.Dict_Variable['FourTerminal_MinVoltage'],10000,100)    #ramp to initial value
            
            #Give a second after the ramp to allow transients to settle before starting the sweep
            yield self.sleep(1)

            self.FourTerminalXaxis=np.linspace(self.Dict_Variable['FourTerminal_MinVoltage'],self.Dict_Variable['FourTerminal_MaxVoltage'],self.Dict_Variable['FourTerminal_Numberofstep'])  #generating list of voltage at which sweeped
            self.dac_read = yield self.Buffer_Ramp_Display(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.Dict_Variable['FourTerminal_MinVoltage']],[self.Dict_Variable['FourTerminal_MaxVoltage']],self.Dict_Variable['FourTerminal_Numberofstep'],self.Dict_Variable['FourTerminal_Delay']*1000000) #dac_read[0] is voltage,dac_read[1] is current potentially
            # self.dac_read = self.FakeDATA(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.Dict_Variable['FourTerminal_MinVoltage']],[self.Dict_Variable['FourTerminal_MaxVoltage']],self.Dict_Variable['FourTerminal_Numberofstep'],self.Dict_Variable['FourTerminal_Delay'])

            self.SetupPlot_Data("No Magnetic Field")#self.Plot_Data: a new set of data particularly for ploting

            self.Format_Data("No Magnetic Field")#Take the Buffer_Ramp Data and save it into self.formatted_data

            yield self.dv.add(self.formatted_data)
            
            yield self.plotData1D(self.Plot_Data[1], self.Plot_Data[2], self.sweepFourTerminal_Plot1)
            if self.FourTerminal_Input2!=4:
                 yield self.plotData1D(self.Plot_Data[1],self.Plot_Data[3],self.sweepFourTerminal_Plot2) #xaxis, yaxis, plot
                 yield self.plotData1D(self.Plot_Data[1],self.Plot_Data[4],self.sweepFourTerminal_Plot3) #xaxis, yaxis, plot
                 yield self.plotData1D(self.Plot_Data[1],self.Plot_Data[5],self.sweepFourTerminal_Plot4) #xaxis, yaxis, plot
                 
            yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.Dict_Variable['FourTerminal_MaxVoltage'],0.0,10000,100)
        except Exception as inst:
            print inst

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save the screenshot

    @inlineCallbacks
    def FourTerminalMagneticFieldSweep(self,c=None): #The FourTerminal Sweep with Magnetic Field
        self.lockInterface()

        self.ConnectLineCut()
        
        self.MagneticFieldSweepPoints=np.linspace(self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField'],self.Dict_Variable['FourTerminalMagneticFieldSetting_MaximumField'],self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'])#Generate Magnetic Field Sweep Point
        
        self.SetupPlotParameter()
        
        try:
            self.ClearFourTerminalMagneticFieldPlot()#Clear the plotted content
            
            self.SetupFourTerminalSweepSetting("Magnetic Field")#Assign the DAC settings and DataVault parameters
            
            self.AutoRangeFourTerminal2DPlot()
            
            self.InitializeLineCutPlot()#Set the LineCut to Bottom Left.
            
            yield self.newDataVaultFile("Magnetic Field")
            
            for self.i in range(0,self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps']):
                if self.AbortMagneticFieldSweep_Flag:
                    print "Abort the Sweep."
                    self.AbortMagneticFieldSweep_Flag = False
                    break

                print 'Starting sweep with magnetic field set to: ' + str(self.MagneticFieldSweepPoints[self.i])

                #Do this properly considering the edge cases
                yield self.rampMagneticField(self.current_field, self.MagneticFieldSweepPoints[self.i], self.Dict_Variable['FourTerminalMagneticFieldSetting_FieldSweepSpeed'])

                #ramp to initial value
                yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.currentDAC_Output[self.FourTerminal_ChannelOutput[0]],self.Dict_Variable['FourTerminal_MinVoltage'],10000,100)

                #Wait for one second to allow transients to settle
                yield self.sleep(1)

                self.FourTerminalXaxis=np.linspace(self.Dict_Variable['FourTerminal_MinVoltage'],self.Dict_Variable['FourTerminal_MaxVoltage'],self.Dict_Variable['FourTerminal_Numberofstep'])  #generating list of voltage at which sweeped
                # self.dac_read = self.FakeDATA(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.Dict_Variable['FourTerminal_MinVoltage']],[self.Dict_Variable['FourTerminal_MaxVoltage']],self.Dict_Variable['FourTerminal_Numberofstep'],self.Dict_Variable['FourTerminal_Delay'])
                
                self.dac_read= yield self.Buffer_Ramp_Display(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.Dict_Variable['FourTerminal_MinVoltage']],[self.Dict_Variable['FourTerminal_MaxVoltage']],self.Dict_Variable['FourTerminal_Numberofstep'],self.Dict_Variable['FourTerminal_Delay']*1000000) #dac_read[0] is voltage,dac_read[1] is current potentially
                
                self.SetupPlot_Data("Magnetic Field")#self.Plot_Data: a new set of data particularly for ploting

                self.Format_Data("Magnetic Field")

                yield self.dv.add(self.formatted_data)
                
                yield self.UpdateFourTerminal2DPlot(self.Plot_Data[4],self.Plot_Data[2],self.Plot_Data[3] ,self.Plot_Data[5]) #4 is resistance, 5 the Conductance

                if self.MoveLineCutFourTerminalMagneticFieldSweep_Flag:  #update Line Cut
                    self.FourTerminalhorizontalLineCutPosition = self.MagneticFieldSweepPoints[self.i] - self.scaley / 2.0  #Prevent Edge state at end
                    if self.i == 0:
                        self.FourTerminalhorizontalLineCutPosition = self.MagneticFieldSweepPoints[self.i]
                    self.UpdateFourTerminalMagneticField_LineCutPlot()
                    self.MoveFourTerminalLineCut()
                    #Could be done more properly for this step
                    self.lineEdit_FourTerminalMagneticFieldSetting_MagneticFieldValue.setText(formatNum(self.FourTerminalhorizontalLineCutPosition))

                if self.AutoLevelFourTerminalMagneticFieldSweep_Flag: #Autolevel
                    self.AutoLevelFourTerminal2DPlot()
                
                yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.Dict_Variable['FourTerminal_MaxVoltage'],0.0,10000,100)

            if self.BacktoZeroFourTerminalMagneticFieldSweep_Flag:
                print "Ramp Field Back to Zero"
                yield self.rampMagneticField(self.current_field, 0.0, self.Dict_Variable['FourTerminalMagneticFieldSetting_FieldSweepSpeed'])

        except Exception as inst:
            print inst

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save the screenshot

    def AbortMagneticFieldSweep(self):
        self.AbortMagneticFieldSweep_Flag =True
        
    @inlineCallbacks
    def rampMagneticField(self, start, end, rate):
        #Eventually add "if ips" vs. "if toellner"
        '''
        Initialize communication protocal. only needs to be done once and should be done in the labrad connect module. These lines should be deleteable
        ###########Black Box#############
        yield self.ips.set_control(3)
        yield self.ips.set_comm_protocol(6)
        yield self.ips.set_control(2)
        
        yield self.sleep(0.25)
        '''
        if self.dac_toe != None:
            pass

        elif self.ips != None:
            yield self.ips.set_control(3)
            yield self.ips.set_fieldsweep_rate(rate)
            yield self.ips.set_control(2)
            
            t0 = time.time() #Keep track of starting time for setting the field
            yield self.ips.set_control(3)
            yield self.ips.set_targetfield(end) #Set the setpoin
            yield self.ips.set_control(2)
            
            yield self.ips.set_control(3)
            yield self.ips.set_activity(1) #Put ips in go to setpoint mode
            yield self.ips.set_control(2)
            
            print 'Setting field to ' + str(end)
            while True:
                yield self.ips.set_control(3)#
                self.current_field = yield self.ips.read_parameter(7)#Read the field
                yield self.ips.set_control(2)#
                #if within 10 uT of the desired field, break out of the loop
                if float(self.current_field[1:]) <= end +0.00001 and float(self.current_field[1:]) >= end -0.00001:#
                    break
                #if after one second we still haven't reached the desired field, then reset the field setpoint and activity
                if time.time() - t0 > 1:
                    yield self.ips.set_control(3)
                    yield self.ips.set_targetfield(end)
                    yield self.ips.set_control(2)
                    
                    yield self.ips.set_control(3)
                    yield self.ips.set_activity(1)
                    yield self.ips.set_control(2)
                    t0 = time.time()
                    print 'restarting loop'
        
        elif self.ami != None:
            print 'Setting field to ' + str(end)
            self.ami.conf_field_targ(end)
            self.ami.ramp()
            target_field = float(self.ami.get_field_targ())
            actual_field = float(self.ami.get_field_mag())
            while abs(target_field - actual_field) > 1e-3:
                time.sleep(2)
                actual_field = float(self.ami.get_field_mag())
            print 'Field set to ' + str(end)

        self.current_field = end
        
    def saveDataToSessionFolder(self):
        try:
            p = QtGui.QPixmap.grabWindow(self.winId())
            a = p.save(self.sessionFolder + '\\' + self.dvFileName + '.jpg','jpg')
            if not a:
                print "Error saving Scan data picture"
        except Exception as inst:
            print 'Scan error: ', inst
            print 'on line: ', sys.exc_traceback.tb_lineno

    @inlineCallbacks
    def update_data(self):
        try:
            #Create data vault file with appropriate parameters
            #Retrace index is 0 for trace, 1 for retrace
            file_info = yield self.dv.new("Sample Charactorizing Data " + self.fileName, ['Retrace Index','X Pos. Index','Y Pos. Index','X Pos. Voltage', 'Y Pos. Voltage'],['Z Position',self.inputs['Input 1 name'], self.inputs['Input 2 name']])
            self.dvFileName = file_info[1]
            self.lineEdit_ImageNum.setText(file_info[1][0:5])
            session  = ''
            for folder in file_info[0][1:]:
                session = session + '\\' + folder
            self.lineEdit_ImageDir.setText(r'\.datavault' + session)

            yield self.ClearBufferedData()

            startfast = self.startOutput1

            for i in range(0,self,numberslowdata):
                startslow = self.startOutput2
                stopfast = self.stopOutput1
                out_list = [self.outputs['Output 1']-1]
                in_list = [self.inputs['Input 1']-1]
                newData = yield self.dac.buffer_ramp(out_list,in_list,[startx],[stopx], self.numberfastdata, self.Dict_Variable['FourTerminal_Delay']*1000000)

            for j in range(0, self.pixels):
                #Putting in 0 for SSAA voltage (last entry) because not yet being used/read
                formatted_data.append((1, j, i, x_voltage[::-1][j], y_voltage[::-1][j], self.data_retrace[0][j,i], self.data_retrace[1][j,i], self.data_retrace[2][j,i]))
                yield self.dv.add(formatted_data)
        except:
            print "This is an error message!"

##########################Update All the parameters#################

    def Update_CentralDAC_DACOUTPUT(self,ChannelPort):     #Set the OutputValue
        if ChannelPort==0:
            dummystr=str(self.lineEdit_CentralDAC_DACOUTPUT1.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
                self.setpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT1.setText(formatNum(self.setpointDAC_Output[ChannelPort],6))
        if ChannelPort==1:
            dummystr=str(self.lineEdit_CentralDAC_DACOUTPUT2.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
                self.setpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT2.setText(formatNum(self.setpointDAC_Output[ChannelPort],6))
        if ChannelPort==2:
            dummystr=str(self.lineEdit_CentralDAC_DACOUTPUT3.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
                self.setpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT3.setText(formatNum(self.setpointDAC_Output[ChannelPort],6))
        if ChannelPort==3:
            dummystr=str(self.lineEdit_CentralDAC_DACOUTPUT4.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
                self.setpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT4.setText(formatNum(self.setpointDAC_Output[ChannelPort],6))

    def UpdateFourTerminal_Numberofstep(self):
        dummystr=str(self.lineEdit_FourTerminal_Numberofstep.text())   #read the text
        dummyval=readNum(dummystr, self , False)
        print self.Dict_Variable['FourTerminal_MaxVoltage'], self.Dict_Variable['FourTerminal_MinVoltage']
        if isinstance(dummyval,float):
            if self.Dict_Variable['FourTerminalSetting_Numberofsteps_Status'] == "Numberofsteps":   #based on status, dummyval is deterimined and update the Numberof steps parameters
                self.Dict_Variable['FourTerminal_Numberofstep']=int(round(dummyval)) #round here is necessary, without round it cannot do 1001 steps back and force
            if self.Dict_Variable['FourTerminalSetting_Numberofsteps_Status'] == "StepSize":
                self.Dict_Variable['FourTerminal_Numberofstep']=int(self.StepSizetoNumberofsteps_Convert(self.Dict_Variable['FourTerminal_MaxVoltage'],self.Dict_Variable['FourTerminal_MinVoltage'],float(dummyval)))
        self.RefreshFourTerminal_Numberofstep()

    def RefreshFourTerminal_Numberofstep(self): #Refresh based on the status change the lineEdit text
        if self.Dict_Variable['FourTerminalSetting_Numberofsteps_Status'] == "Numberofsteps":
            self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.Dict_Variable['FourTerminal_Numberofstep'],6))
        else:
            self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.NumberofstepstoStepSize_Convert(self.Dict_Variable['FourTerminal_MaxVoltage'],self.Dict_Variable['FourTerminal_MinVoltage'],self.Dict_Variable['FourTerminal_Numberofstep']),6))

    def ToggleFourTerminalFourTerminal_Numberofstep(self):
        if self.Dict_Variable['FourTerminalSetting_Numberofsteps_Status'] == "Numberofsteps":
            self.label_FourTerminalNumberofstep.setText('Volt per Steps')
            self.Dict_Variable['FourTerminalSetting_Numberofsteps_Status'] = "StepSize"
            self.RefreshFourTerminal_Numberofstep() #Change the text first
            self.UpdateFourTerminal_Numberofstep()
        else:
            self.label_FourTerminalNumberofstep.setText('Number of Steps')
            self.Dict_Variable['FourTerminalSetting_Numberofsteps_Status'] = "Numberofsteps"
            self.RefreshFourTerminal_Numberofstep() #Change the text first
            self.UpdateFourTerminal_Numberofstep()

    def UpdateLineEdit_General(self, lineEdit, key):
        self.Dict_Variable[key] = str(lineEdit.text())

    def UpdateLineEdit_PlotLabel(self, lineEdit, key):
        self.Dict_Variable[key] = str(lineEdit.text())
        self.updateFourTerminalPlotLabel()

    def UpdateLineEdit_Parameters(self, lineEdit, key, range = None):
        dummystr=str(lineEdit.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            if range == None:
                self.Dict_Variable[key] = dummyval
            elif dummyval >= range[0] and dummyval <= range[1]:
                self.Dict_Variable[key] = dummyval
        lineEdit.setText(formatNum(self.Dict_Variable[key], 6))

    def UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla(self):
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.text())   #read the text
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            if self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps_Status'] == "Numberofsteps":   #based on status, dummyval is deterimined and update the Numberof steps parameters
                self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps']=int(round(dummyval))
            if self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps_Status'] == "StepSize":
                self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps']=int(self.StepSizetoNumberofsteps_Convert(self.Dict_Variable['FourTerminalMagneticFieldSetting_MaximumField'],self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField'],float(dummyval)))
        self.RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()

    def RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla(self): #Refresh based on the status change the lineEdit text
        if self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps_Status'] == "Numberofsteps":
            self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setText(formatNum(self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],6))
        else:
            self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setText(formatNum(self.NumberofstepstoStepSize_Convert(self.Dict_Variable['FourTerminalMagneticFieldSetting_MaximumField'],self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField'],self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps']),6))

    def ToggleFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla(self):
        if self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps_Status'] == "Numberofsteps":
            self.label_FourTerminalMagneticFieldSetting_NumberofSteps.setText('Tesla per Steps')
            self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps_Status'] = "StepSize"
            self.RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla() #Change the text first
            self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()
        else:
            self.label_FourTerminalMagneticFieldSetting_NumberofSteps.setText('Number of Steps')
            self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps_Status'] = "Numberofsteps"
            self.RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla() #Change the text first
            self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()

    def UpdateFieldSweep1D_NumberofstepsandMilifieldperTesla(self):
        dummystr=str(self.lineEdit_1DFieldSweepSetting_Numberofsteps.text())   #read the text
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            if self.Dict_Variable['FieldSweep1DSetting_Numberofsteps_Status'] == "Numberofsteps":   #based on status, dummyval is deterimined and update the Numberof steps parameters
                self.Dict_Variable['FieldSweep1D_Numberofstep']=int(round(dummyval))
            if self.Dict_Variable['FieldSweep1DSetting_Numberofsteps_Status'] == "StepSize":
                self.Dict_Variable['FieldSweep1D_Numberofstep']=int(self.StepSizetoNumberofsteps_Convert(self.Dict_Variable['FieldSweep1D_MaxField'],self.Dict_Variable['FieldSweep1D_MinField'], float(dummyval)))
        self.RefreshFieldSweep1D_NumberofstepsandMilifieldperTesla()

    def RefreshFieldSweep1D_NumberofstepsandMilifieldperTesla(self): #Refresh based on the status change the lineEdit text
        if self.Dict_Variable['FieldSweep1DSetting_Numberofsteps_Status'] == "Numberofsteps":
            self.lineEdit_1DFieldSweepSetting_Numberofsteps.setText(formatNum(self.Dict_Variable['FieldSweep1D_Numberofstep'],6))
        else:
            self.lineEdit_1DFieldSweepSetting_Numberofsteps.setText(formatNum(self.NumberofstepstoStepSize_Convert(self.Dict_Variable['FieldSweep1D_MaxField'],self.Dict_Variable['FieldSweep1D_MinField'],self.Dict_Variable['FieldSweep1D_Numberofstep']),6))

    def ToggleFieldSweep1D_NumberofstepsandMilifieldperTesla(self):
        if self.Dict_Variable['FieldSweep1DSetting_Numberofsteps_Status'] == "Numberofsteps":
            self.label_FieldSweep1D_NumberofStep.setText('Tesla per Steps')
            self.Dict_Variable['FieldSweep1DSetting_Numberofsteps_Status'] = "StepSize"
            self.RefreshFieldSweep1D_NumberofstepsandMilifieldperTesla() #Change the text first
            self.UpdateFieldSweep1D_NumberofstepsandMilifieldperTesla()
        else:
            self.label_FieldSweep1D_NumberofStep.setText('Number of Steps')
            self.Dict_Variable['FieldSweep1DSetting_Numberofsteps_Status'] = "Numberofsteps"
            self.RefreshFieldSweep1D_NumberofstepsandMilifieldperTesla() #Change the text first
            self.UpdateFieldSweep1D_NumberofstepsandMilifieldperTesla()    

    def NumberofstepstoStepSize_Convert(self,Max,Min,NoS):
        StepSize=float(abs(Max-Min)/float(NoS-1.0))
        return StepSize

    def StepSizetoNumberofsteps_Convert(self,Max,Min,SS):
        Numberofsteps=int((Max-Min)/float(SS)+1)
        return Numberofsteps

    def ChangeFourTerminal_Output1_Channel(self):
        self.FourTerminal_Output1=self.comboBox_FourTerminal_Output1.currentIndex()

    def ChangeFourTerminal_Input1_Channel(self):
        self.FourTerminal_Input1=self.comboBox_FourTerminal_Input1.currentIndex()

    def ChangeFourTerminal_Input2_Channel(self):
        self.FourTerminal_Input2=self.comboBox_FourTerminal_Input2.currentIndex()

    def ChangeLockinSettings(self):
        Voltage_LI_Multiplier1=int(self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentText())
        Voltage_LI_Multiplier2=int(self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentText())
        Voltage_LI_Multiplier3=float(self.Dict_LockIn[str(self.comboBox_Voltage_LI_Sensitivity_Unit.currentText())])
        Voltage_LI_Multiplier4=float(self.comboBox_Voltage_LI_Expand.currentText())
        Current_LI_Multiplier1=int(self.comboBox_Current_LI_Sensitivity_1stdigit.currentText())
        Current_LI_Multiplier2=int(self.comboBox_Current_LI_Sensitivity_2nddigit.currentText())
        Current_LI_Multiplier3=float(self.Dict_LockIn[str(self.comboBox_Current_LI_Sensitivity_Unit.currentText())])
        Current_LI_Multiplier4=float(self.comboBox_Current_LI_Expand.currentText())
        #Update Multiplier for Voltage and Current
        self.MultiplierVoltage=Voltage_LI_Multiplier1*Voltage_LI_Multiplier2*Voltage_LI_Multiplier3*Voltage_LI_Multiplier4  
        self.MultiplierCurrent=Current_LI_Multiplier1*Current_LI_Multiplier2*Current_LI_Multiplier3*Current_LI_Multiplier4
		
    def UpdateVoltage_LI_Timeconstant(self):
        dummystr=str(self.lineEdit_Voltage_LI_Timeconstant.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.Voltage_LI_Timeconstant=dummyval
        self.lineEdit_Voltage_LI_Timeconstant.setText(formatNum(self.Voltage_LI_Timeconstant,6))
        
    def UpdateCurrent_LI_Timeconstant(self):
        dummystr=str(self.lineEdit_Current_LI_Timeconstant.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.Current_LI_Timeconstant=dummyval
        self.lineEdit_Current_LI_Timeconstant.setText(formatNum(self.Current_LI_Timeconstant,6))

        
        
    def updateCheckBox(self):
        self.MoveLineCutFourTerminalMagneticFieldSweep_Flag =self.checkBox_FourTerminalMagneticFieldSetting_MoveLineCut.isChecked()
        self.AutoLevelFourTerminalMagneticFieldSweep_Flag =self.checkBox_FourTerminalMagneticFieldSetting_AutoLevel.isChecked()
        self.BacktoZeroFourTerminalMagneticFieldSweep_Flag =self.checkBox_FourTerminalMagneticFieldSetting_BacktoZero.isChecked()
        self.FieldSweep1D_LoopFlag =self.checkBox_FieldSweep1D_Loop.isChecked()

        ##########################Update All the parameters#################

##########################Peculiar Function only defined in SampleCharacterizer#############
    @inlineCallbacks
    def Ramp1_Display(self,SweepPort,Startingpoint,Endpoint,Numberofsteps,Delay,c=None): #this is a function that morph ramp1 and add codes for controlling the display
        try:
            self.UpdateDAC_Current_Label(SweepPort,'Sweeping')
            yield self.dac.ramp1(SweepPort,Startingpoint,Endpoint,Numberofsteps,Delay)
            self.UpdatecurrentDAC_Output(SweepPort,Endpoint)
            self.UpdateDAC_Current_Label(SweepPort,self.currentDAC_Output[SweepPort])

            yield self.ClearBufferedData()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def Buffer_Ramp_Display(self,ChannelOutput,ChannelInput,Min,Max,Numberofsteps,Delay):  #this is a function that morph buffer_ramp and add codes for controlling the display
        try:
            self.UpdateDAC_Current_Label(ChannelOutput[0],'Sweeping')
            data= yield self.dac.buffer_ramp(ChannelOutput,ChannelInput,Min,Max,Numberofsteps,Delay)
            self.UpdateDAC_Current_Label(ChannelOutput[0],Max)
            
            returnValue(data)
        except Exception as inst:
            print inst

    @inlineCallbacks
    def ClearBufferedData(self): #Needs to be called after a long dac.ramp1 (as the ramp function does not read all the data)
        a = yield self.dac.read()
        while a != '':
            print a
            a = yield self.dac.read() 

    def UpdatecurrentDAC_Output(self, Port, voltage): #This is a function that update the current Port Output within the software
        self.currentDAC_Output[Port]=voltage

    def UpdateDAC_Current_Label(self,Channel,Content):
        if isinstance(Content,float):
            if Channel==0:
                self.label_CentralDAC_DACOUTPUT1_Current.setText(formatNum(self.currentDAC_Output[Channel],6))
            if Channel==1:
                self.label_CentralDAC_DACOUTPUT2_Current.setText(formatNum(self.currentDAC_Output[Channel],6))
            if Channel==2:
                self.label_CentralDAC_DACOUTPUT3_Current.setText(formatNum(self.currentDAC_Output[Channel],6))
            if Channel==3:
                self.label_CentralDAC_DACOUTPUT4_Current.setText(formatNum(self.currentDAC_Output[Channel],6))
        if Content=='Sweeping':
            if Channel==0:
                self.label_CentralDAC_DACOUTPUT1_Current.setText('Sweeping')
            if Channel==1:
                self.label_CentralDAC_DACOUTPUT2_Current.setText('Sweeping')
            if Channel==2:
                self.label_CentralDAC_DACOUTPUT3_Current.setText('Sweeping')
            if Channel==3:
                self.label_CentralDAC_DACOUTPUT4_Current.setText('Sweeping')

    @inlineCallbacks
    def Set_CentralDAC_DACOUTPUT(self,ChannelPort,c=None):  #bufferramp to the point in 1s
        try:
            yield self.Ramp1_Display(ChannelPort,self.currentDAC_Output[ChannelPort],self.setpointDAC_Output[ChannelPort],10000,100)
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno

    def SetupFourTerminalSweepSetting(self,Status):
        #Sets up the lists of inputs and outputs for the dac buffer ramp as well as sets up the names for the columns on datavault
    
        if Status == 'MagneticField1D':
            self.FourTerminal_ChannelOutput = ['Magnetic Field']
        else:
            self.FourTerminal_ChannelOutput=[self.FourTerminal_Output1] #Setup for bufferramp function

        self.FourTerminal_ChannelInput=[self.FourTerminal_Input1] #Setup for bufferramp function
        #If FourTerminal_Input2 is 4, then this corresponds to 'None' having been selected on the GUI, in which case it's a two wire measurement
        if self.FourTerminal_Input2!=4:
            self.FourTerminal_ChannelInput.append(self.FourTerminal_Input2)# Create the list of Channel that we read while sweep #setup for bufferramp function

        #datavaultXaxis is the list of independent variables on the sweep
        if Status == 'MagneticField1D':
            self.datavaultXaxis=['Magnetic Field index', 'Magnetic Field']
        else:
            self.datavaultXaxis=[self.FourTerminal_NameOutput1+' index', self.FourTerminal_NameOutput1]

        if Status == "Magnetic Field":
            self.datavaultXaxis=['Magnetic Field index', self.FourTerminal_NameOutput1+' index', 'Magnetic Field', self.FourTerminal_NameOutput1]
            
        #datavaultYaxis is the list of dependent variables on the sweep
        self.datavaultYaxis=[self.FourTerminal_NameInput1]
        if self.FourTerminal_Input2!=4:  #add additional data if Input2 is not None
            self.datavaultYaxis=[self.FourTerminal_NameInput1, self.FourTerminal_NameInput2, "Resistance" , "Conductance"]
            
    def Format_Data(self, Status):
        """
        Format_Data structure:
        #MagneticField Index, Gate Voltage Index, #MagneticField, Gate Voltage, Voltage, #Current, #Resistance
        Plot_Data structure:
        Gate Voltage Index, Gate Voltage, Voltage, #Current, #Resistance, #MagneticField Index, #MagneticField
        """
        self.formatted_data = []
        for j in range(0, self.Dict_Variable['FourTerminal_Numberofstep']):
            DummyVoltage=self.Convert_Real_Voltage(self.dac_read[0][j])
            if Status == "Magnetic Field":
                self.formatted_data.append((self.i,j,self.MagneticFieldSweepPoints[self.i],self.FourTerminalXaxis[j],DummyVoltage))
            else: 
                self.formatted_data.append((j, self.FourTerminalXaxis[j],DummyVoltage))
            self.Plot_Data[2].append(DummyVoltage)
            if self.FourTerminal_Input2!=4:  #add additional data if Input2 is not None
                DummyCurrent=self.Convert_Real_Current(self.dac_read[1][j])
                self.formatted_data[j]+=(DummyCurrent,)
                self.Plot_Data[3].append(DummyCurrent)
                resistance=self.Calculate_Resistance(DummyVoltage,DummyCurrent)
                if resistance == 0 :
                    Conductance = 0.0
                else:
                    Conductance = 1/resistance
                self.formatted_data[j]+=(resistance,)  #proccessing to Resistance
                self.Plot_Data[4].append(resistance)
                self.formatted_data[j]+=(Conductance,)  #proccessing to Conductance
                self.Plot_Data[5].append(Conductance)
                
    @inlineCallbacks
    def newDataVaultFile(self, Status):
        if Status== "Magnetic Field":
            file = yield self.dv.new('FourTerminal MagneticField ' + self.Device_Name, self.datavaultXaxis,self.datavaultYaxis)
        elif Status== "MagneticField1D":
            file = yield self.dv.new('1D Magnetic Field ' + self.Device_Name, self.datavaultXaxis,self.datavaultYaxis)
        else:
            file = yield self.dv.new('FourTerminal ' + self.Device_Name, self.datavaultXaxis,self.datavaultYaxis)
            
        self.dvFileName = file[1] # read the name
        self.lineEdit_ImageNumber.setText(file[1][0:5])
        session  = ''
        for folder in file[0][1:]:
            session = session + '\\' + folder
        self.lineEdit_ImageDir.setText(r'\.datavault' + session)

        yield self.dv.add_parameter('Voltage Lock in Sensitivity (V)',self.MultiplierVoltage)
        yield self.dv.add_parameter('Voltage Lock in Expand',float(self.comboBox_Voltage_LI_Expand.currentText()))
        yield self.dv.add_parameter('Current Lock in Sensitivity (A)',self.MultiplierCurrent)
        yield self.dv.add_parameter('Current Lock in Expand',float(self.comboBox_Current_LI_Expand.currentText()))
        yield self.dv.add_parameter('Voltage Lock in Time Constant(s)',float(self.Voltage_LI_Timeconstant))
        yield self.dv.add_parameter('Current Lock in Time Constant(s)',float(self.Current_LI_Timeconstant))
        yield self.dv.add_parameter('Lock in Frequency(Hz)',float(self.Dict_Variable['Frequency']))
        if Status== "MagneticField1D":
            yield self.dv.add_parameter('DAC Voltage 1',float(self.lineEdit_CentralDAC_DACOUTPUT1.text()))
            yield self.dv.add_parameter('DAC Voltage 2',float(self.lineEdit_CentralDAC_DACOUTPUT2.text()))
            yield self.dv.add_parameter('DAC Voltage 3',float(self.lineEdit_CentralDAC_DACOUTPUT3.text()))
            yield self.dv.add_parameter('DAC Voltage 4',float(self.lineEdit_CentralDAC_DACOUTPUT4.text()))

    def SetupPlot_Data(self,Status):
        try:
            """
            Plot_Data structure:
            Gate Voltage Index, Gate Voltage, Voltage, #Current, #Resistance, #Conductance #MagneticField Index, #MagneticField
            (Magnetic Field Index), Magnetic Field
            """
            if Status != 'MagneticField1D':
                self.Plot_Data=[range(0,self.Dict_Variable['FourTerminal_Numberofstep'])]
                self.Plot_Data.append(self.FourTerminalXaxis)
            else:
                self.Plot_Data=[range(0,self.Dict_Variable['FieldSweep1D_Numberofstep'])]
                self.Plot_Data.append(self.FieldSweep1DXaxis)

            self.Plot_Data.append([])
            if self.FourTerminal_Input2!=4:
                self.Plot_Data.append([])#Current
                self.Plot_Data.append([])#Resistance
                self.Plot_Data.append([])#Conductance
            if Status == "Magnetic Field":
                self.Plot_Data.append([range(0,self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'])])
                self.Plot_Data.append(self.MagneticFieldSweepPoints)
            if Status == 'MagneticField1D' and self.FourTerminal_Input2!=4:
                self.Plot_Data[2] = np.zeros(self.Dict_Variable['FieldSweep1D_Numberofstep'])
                self.Plot_Data[3] = np.zeros(self.Dict_Variable['FieldSweep1D_Numberofstep'])
                self.Plot_Data[4] = np.zeros(self.Dict_Variable['FieldSweep1D_Numberofstep'])
                self.Plot_Data[5] = np.zeros(self.Dict_Variable['FieldSweep1D_Numberofstep'])
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno

    def Convert_Real_Voltage(self,reading): #Take the DAC reading and convert it to real unit (V)
        Real_Voltage=float(reading)/10.0*self.MultiplierVoltage
        return Real_Voltage
            
    def Convert_Real_Current(self,reading): #Take the DAC reading and convert it to real unit (A)
        Real_Current=float(reading)/10.0*self.MultiplierCurrent
        return Real_Current
            
    def Calculate_Resistance(self,voltage,current): #Take the DAC reading and convert it to real unit (A)
        if current != 0.0:
            resistance=float(voltage/current) #generating resisitance
        else:
            resistance=float(voltage/0.0000000001)# Prevent bug as "float cannot be divide by zero"
        return resistance

##########################Peculiar Function only defined in SampleCharacterizer#############
        
        
##########################              Plot Related functions                 #############
    def plotData1D(self,xaxis,yaxis,plot, color = 0.5):
        plot.plot(x = xaxis, y = yaxis, pen = color)
        
    def setupAdditionalUi(self):
        self.setupFourTerminalPlot()
        self.setupFieldSweep1DPlot()
        self.setupFourTerminalMagneticFieldResistancePlot()
        self.setupFourTerminalMagneticFieldVoltagePlot()
        self.setupFourTerminalMagneticFieldCurrentPlot()
        self.setupFourTerminalMagneticFieldConductancePlot()
        self.SetupFourTerminalMageneticField2DPlot()
        self.SetupLineCut()

    def setupFourTerminalPlot(self):
        self.sweepFourTerminal_Plot1 = pg.PlotWidget(parent = self.frame_FourTerminalPlot1)
        self.Setup1DPlot(self.sweepFourTerminal_Plot1, self.Layout_FourTerminalPlot1, self.FourTerminal_NameInput1, self.FourTerminal_NameInput1, "V", self.FourTerminal_NameOutput1, "V")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

        self.sweepFourTerminal_Plot2 = pg.PlotWidget(parent = self.frame_FourTerminalPlot2)
        self.Setup1DPlot(self.sweepFourTerminal_Plot2, self.Layout_FourTerminalPlot2, self.FourTerminal_NameInput2, self.FourTerminal_NameInput2, "A", self.FourTerminal_NameOutput1,"V" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

        self.sweepFourTerminal_Plot3 = pg.PlotWidget(parent = self.frame_FourTerminalPlot3)
        self.Setup1DPlot(self.sweepFourTerminal_Plot3, self.Layout_FourTerminalPlot3, 'Resistance', 'Resistance', "Ohm", self.FourTerminal_NameOutput1,"V" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        
        self.sweepFourTerminal_Plot4 = pg.PlotWidget(parent = self.frame_FourTerminalPlot4)
        self.Setup1DPlot(self.sweepFourTerminal_Plot4, self.Layout_FourTerminalPlot4, 'Conductance', 'Conductance', "S", self.FourTerminal_NameOutput1,"V" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    def setupFieldSweep1DPlot(self):
        self.FieldSweep1D_Plot1 = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FieldSweep1D_Plot1, self.verticalLayout_1DFieldSweepPlot1, self.FourTerminal_NameInput1, self.FourTerminal_NameInput1, "V", 'MagneticField', "T")#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

        self.FieldSweep1D_Plot2 = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FieldSweep1D_Plot2, self.verticalLayout_1DFieldSweepPlot2, self.FourTerminal_NameInput2, self.FourTerminal_NameInput2, "A", 'MagneticField',"T" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

        self.FieldSweep1D_Plot3 = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FieldSweep1D_Plot3, self.verticalLayout_1DFieldSweepPlot3, 'Resistance', 'Resistance', "Ohm", 'MagneticField',"T" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        
        self.FieldSweep1D_Plot4 = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FieldSweep1D_Plot4, self.verticalLayout_1DFieldSweepPlot4, 'Conductance', 'Conductance', "S", 'MagneticField',"T" )#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit


    def Setup1DPlot(self, Plot, Layout , Title , yaxis , yunit, xaxis, xunit):
        Plot.setGeometry(QtCore.QRect(0, 0, 400, 200))
        Plot.setTitle( Title)
        Plot.setLabel('left', yaxis, units = yunit)
        Plot.setLabel('bottom', xaxis, units = xunit)
        Plot.showAxis('right', show = True)
        Plot.showAxis('top', show = True)
        Plot.setXRange(0,1)
        Plot.setYRange(0,2)
        Plot.enableAutoRange(enable = True)
        Layout.addWidget(Plot)
        
    def Setup2DPlot(self, Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView ):
        Plot.setLabel('left', yaxis, units = yunit)
        Plot.setLabel('bottom', xaxis, units = xunit)
        Plot.showAxis('top', show = True)
        Plot.showAxis('right', show = True)
        Plot.setAspectLocked(False)
        Plot.invertY(False)
        Plot.setXRange(-1.25,1.25,0)
        Plot.setYRange(-10,10, 0)
        PlotView.setGeometry(QtCore.QRect(0, 0, 400, 200))
        PlotView.ui.menuBtn.hide()
        PlotView.ui.histogram.item.gradient.loadPreset('bipolar')
        PlotView.ui.roiBtn.hide()
        PlotView.ui.menuBtn.hide()

        Frame.close() #necessary for streching the window
        Layout.addWidget(PlotView)
        
    def SetupLineCutMagneticFieldPlot(self,Plot,Layout,yaxisName,Unit):
        Plot.setGeometry(QtCore.QRect(0, 0, 9999, 999))
        Plot.setLabel('left', self.FourTerminal_NameOutput1, units = 'V' )
        Plot.setLabel('bottom',yaxisName, units = Unit)
        Plot.showAxis('right', show = True)
        Plot.showAxis('top', show = True)
        Layout.addWidget(Plot)
        
    def SetupLineCutGateVoltagePlot(self,Plot,Layout,yaxisName,Unit):
        Plot.setGeometry(QtCore.QRect(0, 0, 9999, 999))
        Plot.setLabel('left', yaxisName, units = Unit)
        Plot.setLabel('bottom', 'Magnetic Field', units = 'T')
        Plot.showAxis('right', show = True)
        Plot.showAxis('top', show = True)
        Layout.addWidget(Plot)
        
    def setupFourTerminalMagneticFieldResistancePlot(self): 
        #Setup 2D first
        self.view_sweepFourTerminalMagneticField_Resistance_Plot = pg.PlotItem(name = "Four Terminal Resistance versus Magnetic Field Resistance Plot",title = "Resistance")
        self.sweepFourTerminalMagneticField_Resistance_Plot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Resistance_2DPlot, view = self.view_sweepFourTerminalMagneticField_Resistance_Plot)
        
        self.Setup2DPlot(self.view_sweepFourTerminalMagneticField_Resistance_Plot, "Magnetic Field", 'T', self.FourTerminal_NameOutput1, 'V', self.Frame_FourTerminalMagneticField_Resistance_2DPlot, self.Layout_FourTerminalMagneticField_Resistance_2DPlot, self.sweepFourTerminalMagneticField_Resistance_Plot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView

        #Setup Linecut
        self.FourTerminalMagneticField_Resistance_VersusField_Plot = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FourTerminalMagneticField_Resistance_VersusField_Plot, self.Layout_FourTerminalMagneticField_Resistance_VersusField, None, "Magnetic Field", 'T', 'Resistance','Ohm')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit


        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot, self.Layout_FourTerminalMagneticField_Resistance_VersusGateVoltage, None,'Resistance','Ohm', self.FourTerminal_NameOutput1, 'V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
    
    def setupFourTerminalMagneticFieldVoltagePlot(self):
        self.view_sweepFourTerminalMagneticField_Voltage_Plot = pg.PlotItem(name = "Four Terminal Voltage versus Magnetic Field Voltage Plot",title = self.FourTerminal_NameInput1)
        self.sweepFourTerminalMagneticField_Voltage_Plot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Voltage_2DPlot, view = self.view_sweepFourTerminalMagneticField_Voltage_Plot)

        self.Setup2DPlot(self.view_sweepFourTerminalMagneticField_Voltage_Plot, "Magnetic Field", 'T', self.FourTerminal_NameOutput1, 'V', self.Frame_FourTerminalMagneticField_Voltage_2DPlot, self.Layout_FourTerminalMagneticField_Voltage_2DPlot, self.sweepFourTerminalMagneticField_Voltage_Plot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView

        self.FourTerminalMagneticField_Voltage_VersusField_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Voltage_VersusField)
        self.Setup1DPlot(self.FourTerminalMagneticField_Voltage_VersusField_Plot, self.Layout_FourTerminalMagneticField_Voltage_VersusField, None, "Magnetic Field", 'T', self.FourTerminal_NameInput1,'V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Voltage_VersusGateVoltage)
        self.Setup1DPlot(self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot, self.Layout_FourTerminalMagneticField_Voltage_VersusGateVoltage, None, self.FourTerminal_NameInput1,'V', self.FourTerminal_NameOutput1, 'V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

    def setupFourTerminalMagneticFieldCurrentPlot(self):
        self.view_sweepFourTerminalMagneticField_Current_Plot = pg.PlotItem(name = "Four Terminal Current versus Magnetic Field Voltage Plot",title = self.FourTerminal_NameInput2)
        self.sweepFourTerminalMagneticField_Current_Plot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Current_2DPlot, view = self.view_sweepFourTerminalMagneticField_Current_Plot)

        self.Setup2DPlot(self.view_sweepFourTerminalMagneticField_Current_Plot, "Magnetic Field", 'T', self.FourTerminal_NameOutput1, 'V', self.Frame_FourTerminalMagneticField_Current_2DPlot, self.Layout_FourTerminalMagneticField_Current_2DPlot, self.sweepFourTerminalMagneticField_Current_Plot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView

        self.FourTerminalMagneticField_Current_VersusField_Plot = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FourTerminalMagneticField_Current_VersusField_Plot, self.Layout_FourTerminalMagneticField_Current_VersusField, None, "Magnetic Field", 'T', self.FourTerminal_NameInput2,'A')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit

        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Current_VersusGateVoltage)
        
        self.Setup1DPlot(self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot, self.Layout_FourTerminalMagneticField_Current_VersusGateVoltage, None, self.FourTerminal_NameInput2,'A', self.FourTerminal_NameOutput1, 'V')  #Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        
    def setupFourTerminalMagneticFieldConductancePlot(self):
        #Setup 2D first
        self.view_sweepFourTerminalMagneticField_Conductance_Plot = pg.PlotItem(name = "Four Terminal Conductance versus Magnetic Field Voltage Plot",title = "Conductance")
        self.sweepFourTerminalMagneticField_Conductance_Plot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Conductance_2DPlot, view = self.view_sweepFourTerminalMagneticField_Conductance_Plot)
        
        self.Setup2DPlot(self.view_sweepFourTerminalMagneticField_Conductance_Plot, "Magnetic Field", 'T', self.FourTerminal_NameOutput1, 'V', self.Frame_FourTerminalMagneticField_Conductance_2DPlot, self.Layout_FourTerminalMagneticField_Conductance_2DPlot, self.sweepFourTerminalMagneticField_Conductance_Plot ) #Plot, yaxis, yunit, xaxis, xunit , Frame , Layout , PlotView

        #Setup Linecut
        self.FourTerminalMagneticField_Conductance_VersusField_Plot = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FourTerminalMagneticField_Conductance_VersusField_Plot, self.Layout_FourTerminalMagneticField_Conductance_VersusField, None, "Magnetic Field", 'T', 'Conductance','S')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit


        self.FourTerminalMagneticField_Conductance_VersusGateVoltage_Plot = pg.PlotWidget(parent = None)
        self.Setup1DPlot(self.FourTerminalMagneticField_Conductance_VersusGateVoltage_Plot, self.Layout_FourTerminalMagneticField_Conductance_VersusGateVoltage, None,'Conductance','S', self.FourTerminal_NameOutput1, 'V')#Plot, Layout , Title , yaxis , yunit, xaxis ,xunit
        
    def updateFourTerminalPlotLabel(self):
        self.sweepFourTerminal_Plot1.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.sweepFourTerminal_Plot1.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot2.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.sweepFourTerminal_Plot2.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot3.setLabel('left', 'Resistance', units = 'Ohm')
        self.sweepFourTerminal_Plot3.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot4.setLabel('left', 'Conductance', units = 'S')
        self.sweepFourTerminal_Plot4.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setLabel('bottom', text=self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setLabel('bottom', text=self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setLabel('bottom', text=self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setTitle(self.FourTerminal_NameInput1)
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.setLabel('bottom', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Current_Plot.setTitle(self.FourTerminal_NameInput2)
        self.view_sweepFourTerminalMagneticField_Current_Plot.setLabel('bottom', text=self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Current_VersusField_Plot.setLabel('bottom', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        
    def AutoRangeFourTerminal2DPlot(self):
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Conductance_Plot.setImage(self.PlotDataFourTerminalConductance2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        
    def AutoLevelFourTerminal2DPlot(self):
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Conductance_Plot.setImage(self.PlotDataFourTerminalConductance2D.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D.T, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        
    def ClearFourTerminalPlot(self):
        self.sweepFourTerminal_Plot1.clear()
        self.sweepFourTerminal_Plot2.clear()
        self.sweepFourTerminal_Plot3.clear()
        self.sweepFourTerminal_Plot4.clear()

    def ClearFourTerminal2DPlot(self):
        self.sweepFourTerminalMagneticField_Resistance_Plot.clear()
        self.sweepFourTerminalMagneticField_Voltage_Plot.clear()
        self.sweepFourTerminalMagneticField_Current_Plot.clear()
        self.sweepFourTerminalMagneticField_Conductance_Plot.clear()
        self.PlotDataFourTerminalResistance2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])
        self.PlotDataFourTerminalVoltage2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])
        self.PlotDataFourTerminalCurrent2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])
        self.PlotDataFourTerminalConductance2D=np.zeros([self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'],self.Dict_Variable['FourTerminal_Numberofstep']])
        
    def ClearFourTerminalMagneticFieldPlot(self):
        self.ClearFourTerminal2DPlot()
        self.ClearLineCutPlot()
                
    def ClearFieldSweep1DPlot(self):
        self.FieldSweep1D_Plot1.clear()
        self.FieldSweep1D_Plot2.clear()
        self.FieldSweep1D_Plot3.clear()
        self.FieldSweep1D_Plot4.clear()

    def SetupPlotParameter(self):
        #set up the parameter for ploting, pos and scale
        self.posx, self.posy = (self.Dict_Variable['FourTerminal_MinVoltage'] , self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField'])
        self.scalex, self.scaley = ((self.Dict_Variable['FourTerminal_MaxVoltage']-self.Dict_Variable['FourTerminal_MinVoltage'])/self.Dict_Variable['FourTerminal_Numberofstep'], (self.Dict_Variable['FourTerminalMagneticFieldSetting_MaximumField']-self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField'])/self.Dict_Variable['FourTerminalMagneticFieldSetting_Numberofsteps'])

    def SetupFourTerminalMageneticField2DPlot(self):
        self.SetupPlotParameter()
        #Associate the Data with each 2D plot
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Conductance_Plot.setImage(self.PlotDataFourTerminalConductance2D.T, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])

        #Setup the linecut in the plot
        self.FourTerminalVerticalLinePlotResistance = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.FourTerminalHorizontalLinePlotResistance = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.FourTerminalVerticalLinePlotVoltage = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.FourTerminalHorizontalLinePlotVoltage = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.FourTerminalVerticalLinePlotCurrent = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.FourTerminalHorizontalLinePlotCurrent = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.FourTerminalVerticalLinePlotConductance = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.FourTerminalHorizontalLinePlotConductance = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        
##########################              Plot Related functions                 #############

##########################              LineCut Related functions                 #############
    def InitializeLineCutPlot(self):
        self.FourTerminalverticalLineCutPosition = self.Dict_Variable['FourTerminal_MinVoltage']
        self.FourTerminalhorizontalLineCutPosition = self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField']
        self.MoveFourTerminalLineCut()

    def SetupLineCutMagneticFieldValue(self): #Corresponding to change in lineEdit
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_MagneticFieldValue.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.FourTerminalVerticalLinePlotResistance.setValue(dummyval)
            self.FourTerminalVerticalLinePlotVoltage.setValue(dummyval)
            self.FourTerminalVerticalLinePlotCurrent.setValue(dummyval)            
        self.FourTerminalverticalLineCutPosition=dummyval
        time.sleep(1)
        self.ChangeFourTerminalLineCutValue("")
         
    def SetupLineCutGateVoltageValue(self): #Corresponding to change in lineEdit
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_GateVoltageValue.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.FourTerminalHorizontalLinePlotResistance.setValue(dummyval)
            self.FourTerminalHorizontalLinePlotVoltage.setValue(dummyval)
            self.FourTerminalHorizontalLinePlotCurrent.setValue(dummyval)
        self.FourTerminalhorizontalLineCutPosition=dummyval
        self.ChangeFourTerminalLineCutValue("")

    def UpdateFourTerminalMagneticField_LineCutPlot(self): #Update the Plot based on position of LineCut
        xindex = int((self.FourTerminalverticalLineCutPosition - self.Dict_Variable['FourTerminal_MinVoltage'])/self.scalex)
        yindex = int((self.FourTerminalhorizontalLineCutPosition - self.Dict_Variable['FourTerminalMagneticFieldSetting_MinimumField'])/self.scaley)
        
        self.ClearLineCutPlot()
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.plot(x=self.MagneticFieldSweepPoints,y=self.PlotDataFourTerminalResistance2D[:,xindex],pen = 0.5)
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.plot(x=self.Plot_Data[1], y=self.PlotDataFourTerminalResistance2D[yindex], pen = 0.5)
        self.FourTerminalMagneticField_Conductance_VersusField_Plot.plot(x=self.MagneticFieldSweepPoints,y=self.PlotDataFourTerminalConductance2D[:,xindex],pen = 0.5)
        self.FourTerminalMagneticField_Conductance_VersusGateVoltage_Plot.plot(x=self.Plot_Data[1], y=self.PlotDataFourTerminalConductance2D[yindex], pen = 0.5)
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.plot(x=self.MagneticFieldSweepPoints,y=self.PlotDataFourTerminalVoltage2D[:,xindex],pen = 0.5)
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.plot(x=self.Plot_Data[1], y=self.PlotDataFourTerminalVoltage2D[yindex], pen = 0.5)
        self.FourTerminalMagneticField_Current_VersusField_Plot.plot(x=self.MagneticFieldSweepPoints,y=self.PlotDataFourTerminalCurrent2D[:,xindex],pen = 0.5)
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.plot(x=self.Plot_Data[1], y=self.PlotDataFourTerminalCurrent2D[yindex], pen = 0.5)
        
    def UpdateFourTerminal2DPlot(self,newResistancedata,newVoltagedata,newCurrentdata,newConductancedata):
        #Add data to the Plotted 2D Data
        self.PlotDataFourTerminalResistance2D[self.i] = newResistancedata
        self.PlotDataFourTerminalVoltage2D[self.i] = newVoltagedata
        self.PlotDataFourTerminalCurrent2D[self.i] = newCurrentdata
        self.PlotDataFourTerminalConductance2D[self.i] = newConductancedata
                
        #Update the Plot with new Data
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])        
        self.sweepFourTerminalMagneticField_Conductance_Plot.setImage(self.PlotDataFourTerminalConductance2D.T, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])        
        
    def ChangeFourTerminalLineCutValue(self,LineCut): #Take a input to determine if it is change from editing lineEdit or changing the linecut in the graph
        #Update the value if change from moving
        if LineCut == self.FourTerminalVerticalLinePlotResistance or LineCut == self.FourTerminalVerticalLinePlotVoltage or  LineCut == self.FourTerminalVerticalLinePlotCurrent or LineCut == self.FourTerminalVerticalLinePlotConductance:
            self.FourTerminalverticalLineCutPosition=LineCut.value()

        if LineCut == self.FourTerminalHorizontalLinePlotResistance or LineCut == self.FourTerminalHorizontalLinePlotVoltage or  LineCut == self.FourTerminalHorizontalLinePlotCurrent or LineCut == self.FourTerminalHorizontalLinePlotConductance :
            self.FourTerminalhorizontalLineCutPosition=LineCut.value()
        #Update the text
        self.lineEdit_FourTerminalMagneticFieldSetting_MagneticFieldValue.setText(formatNum(self.FourTerminalverticalLineCutPosition))
        self.lineEdit_FourTerminalMagneticFieldSetting_GateVoltageValue.setText(formatNum(self.FourTerminalhorizontalLineCutPosition))
        
        #Update the position according to the value
        self.MoveFourTerminalLineCut()
        
        #Update the Linecut Plot with newly edited value of position
        self.UpdateFourTerminalMagneticField_LineCutPlot()
        
    def MoveFourTerminalLineCut(self):
        self.FourTerminalVerticalLinePlotResistance.setValue(float(self.FourTerminalverticalLineCutPosition))
        self.FourTerminalVerticalLinePlotConductance.setValue(float(self.FourTerminalverticalLineCutPosition))
        self.FourTerminalVerticalLinePlotVoltage.setValue(float(self.FourTerminalverticalLineCutPosition))
        self.FourTerminalVerticalLinePlotCurrent.setValue(float(self.FourTerminalverticalLineCutPosition))  
        self.FourTerminalHorizontalLinePlotResistance.setValue(float(self.FourTerminalhorizontalLineCutPosition))
        self.FourTerminalHorizontalLinePlotConductance.setValue(float(self.FourTerminalhorizontalLineCutPosition))
        self.FourTerminalHorizontalLinePlotVoltage.setValue(float(self.FourTerminalhorizontalLineCutPosition))
        self.FourTerminalHorizontalLinePlotCurrent.setValue(float(self.FourTerminalhorizontalLineCutPosition))
            
    def SetupLineCut(self):
        """
        self.FourTerminalverticalLineCutPosition
        self.FourTerminalhorizontalLineCutPosition
        """
        self.sweepFourTerminalMagneticField_Resistance_Plot.addItem(self.FourTerminalVerticalLinePlotResistance, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Resistance_Plot.addItem(self.FourTerminalHorizontalLinePlotResistance, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Conductance_Plot.addItem(self.FourTerminalVerticalLinePlotConductance, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Conductance_Plot.addItem(self.FourTerminalHorizontalLinePlotConductance, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Voltage_Plot.addItem(self.FourTerminalVerticalLinePlotVoltage, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Voltage_Plot.addItem(self.FourTerminalHorizontalLinePlotVoltage, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Current_Plot.addItem(self.FourTerminalVerticalLinePlotCurrent, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Current_Plot.addItem(self.FourTerminalHorizontalLinePlotCurrent, ignoreBounds = True)
    
    def ConnectLineCut(self):
        self.FourTerminalVerticalLinePlotResistance.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalVerticalLinePlotResistance))
        self.FourTerminalHorizontalLinePlotResistance.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalHorizontalLinePlotResistance))
        self.FourTerminalVerticalLinePlotConductance.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalVerticalLinePlotConductance))
        self.FourTerminalHorizontalLinePlotConductance.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalHorizontalLinePlotConductance))
        self.FourTerminalVerticalLinePlotVoltage.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalVerticalLinePlotVoltage))
        self.FourTerminalHorizontalLinePlotVoltage.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalHorizontalLinePlotVoltage))
        self.FourTerminalVerticalLinePlotCurrent.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalVerticalLinePlotCurrent))
        self.FourTerminalHorizontalLinePlotCurrent.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalHorizontalLinePlotCurrent))
        #This is not used for now self.FourTerminalLineCut = True
        
    def ClearLineCutPlot(self):
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.clear()
        self.FourTerminalMagneticField_Conductance_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Conductance_VersusGateVoltage_Plot.clear()
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.clear()
        self.FourTerminalMagneticField_Current_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.clear()
        
##########################              LineCut Related functions                 #############

    def updateHistogramLevels(self, hist):
        mn, mx = hist.getLevels()
        self.Plot2D.ui.histogram.setLevels(mn, mx)
        #self.autoLevels = False

    def setSessionFolder(self, folder):
        self.sessionFolder = folder

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
        self.lineEdit_FourTerminal_NameOutput1.setEnabled(False)
        self.lineEdit_FourTerminal_NameInput1.setEnabled(False)
        self.lineEdit_FourTerminal_NameInput2.setEnabled(False)
        self.lineEdit_FourTerminal_MinVoltage.setEnabled(False)
        self.lineEdit_FourTerminal_MaxVoltage.setEnabled(False)
        self.lineEdit_FourTerminal_Numberofstep.setEnabled(False)
        self.lineEdit_FourTerminal_Delay.setEnabled(False)
        self.pushButton_FourTerminal_NoSmTpTSwitch.setEnabled(False)

        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.setEnabled(False)
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.setEnabled(False)
        self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setEnabled(False)
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.setEnabled(False)
        self.pushButton_FourTerminalMagneticFieldSetting_NoSmTpTSwitch.setEnabled(False)
        self.pushButton_StartFourTerminalMagneticFieldSweep.setEnabled(False)

        self.comboBox_FourTerminal_Output1.setEnabled(False)
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
        self.lineEdit_Voltage_LI_Timeconstant.setEnabled(False)
        self.lineEdit_Current_LI_Timeconstant.setEnabled(False)
        self.lineEdit_Lockin_Info_Frequency.setEnabled(False)

        self.pushButton_Start1DFieldSweep.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_MinimumField.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_MaximumField.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.setEnabled(False)
        self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed.setEnabled(False)
        
        self.pushButton_StartFourTerminalSweep.setEnabled(False)

        self.lineEdit_CentralDAC_DACOUTPUT1.setEnabled(False)
        self.lineEdit_CentralDAC_DACOUTPUT2.setEnabled(False)
        self.lineEdit_CentralDAC_DACOUTPUT3.setEnabled(False)
        self.lineEdit_CentralDAC_DACOUTPUT4.setEnabled(False)
        self.pushButton_CentralDAC_DACOUTPUT1.setEnabled(False)
        self.pushButton_CentralDAC_DACOUTPUT2.setEnabled(False)
        self.pushButton_CentralDAC_DACOUTPUT3.setEnabled(False)
        self.pushButton_CentralDAC_DACOUTPUT4.setEnabled(False)

    def unlockInterface(self):
        self.lineEdit_FourTerminal_NameOutput1.setEnabled(True)
        self.lineEdit_FourTerminal_NameInput1.setEnabled(True)
        self.lineEdit_FourTerminal_NameInput2.setEnabled(True)
        self.lineEdit_FourTerminal_MinVoltage.setEnabled(True)
        self.lineEdit_FourTerminal_MaxVoltage.setEnabled(True)
        self.lineEdit_FourTerminal_Numberofstep.setEnabled(True)
        self.lineEdit_FourTerminal_Delay.setEnabled(True)
        self.pushButton_FourTerminal_NoSmTpTSwitch.setEnabled(True)

        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.setEnabled(True)
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.setEnabled(True)
        self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setEnabled(True)
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.setEnabled(True)
        self.pushButton_FourTerminalMagneticFieldSetting_NoSmTpTSwitch.setEnabled(True)
        self.pushButton_StartFourTerminalMagneticFieldSweep.setEnabled(True)

        self.comboBox_FourTerminal_Output1.setEnabled(True)
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
        self.lineEdit_Voltage_LI_Timeconstant.setEnabled(True)
        self.lineEdit_Current_LI_Timeconstant.setEnabled(True)
        self.lineEdit_Lockin_Info_Frequency.setEnabled(True)
        
        self.pushButton_Start1DFieldSweep.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_MinimumField.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_MaximumField.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_Numberofsteps.setEnabled(True)
        self.lineEdit_1DFieldSweepSetting_FieldSweepSpeed.setEnabled(True)

        self.pushButton_StartFourTerminalSweep.setEnabled(True)

        self.lineEdit_CentralDAC_DACOUTPUT1.setEnabled(True)
        self.lineEdit_CentralDAC_DACOUTPUT2.setEnabled(True)
        self.lineEdit_CentralDAC_DACOUTPUT3.setEnabled(True)
        self.lineEdit_CentralDAC_DACOUTPUT4.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT1.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT2.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT3.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT4.setEnabled(True)

#####################################This is fake data generation code, replacing buffer_ramp
    def FakeDATA(self,Output,Input,Min,Max,NoS,Delay): 
        fake=[]
        xpoints= np.linspace( Min, Max, NoS)
        for i in range(0,len(Input)):
            fake.append([])
            for j in range (0,NoS):
                fake[i].append((1/(abs(xpoints[j])+.5))+(math.cos(0.25/(self.i+0.01)*(0.01+xpoints[j]))+1))
        return fake
               
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
