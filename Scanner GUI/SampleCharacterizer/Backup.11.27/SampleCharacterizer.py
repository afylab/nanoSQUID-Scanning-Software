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
import math
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

        '''
        """
        # These are scan module specific and shouldn't be relevant here
        self.aspectLocked = True
        self.FrameLocked = True
        self.LinearSpeedLocked = False
        self.DataLocked = True
        self.scanSmooth = True
        self.scanCoordinates = False
        self.dataProcessing = 'Raw'
        self.dataPostProcessing = 'Raw'
        '''
        
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

        self.lineEdit_FourTerminal_NameOutput1.editingFinished.connect(self.UpdateFourTerminal_NameOutput1)
        self.lineEdit_Device_Name.editingFinished.connect(self.UpdateDevice_Name)
        self.lineEdit_FourTerminal_NameInput1.editingFinished.connect(self.UpdateFourTerminal_NameInput1)
        self.lineEdit_FourTerminal_NameInput2.editingFinished.connect(self.UpdateFourTerminal_NameInput2)
        
        
#################FourTerminal sweep default parameter
        self.FourTerminal_ChannelInput=[]
        self.FourTerminal_ChannelOutput=[]
        self.FourTerminal_MinVoltage=-0.1
        self.FourTerminal_MaxVoltage=0.1
        self.FourTerminal_Numberofstep=100
        self.FourTerminalSetting_Numberofsteps_Status="Numberofsteps"
        self.FourTerminal_Delay=0.001
        self.lineEdit_FourTerminal_MinVoltage.setText(formatNum(self.FourTerminal_MinVoltage,6))
        self.lineEdit_FourTerminal_MaxVoltage.setText(formatNum(self.FourTerminal_MaxVoltage,6))
        self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.FourTerminal_Numberofstep,6))
        self.lineEdit_FourTerminal_Delay.setText(formatNum(self.FourTerminal_Delay,6))

#######################################Lineedit Four Terminial
        self.lineEdit_FourTerminal_MinVoltage.editingFinished.connect(self.UpdateFourTerminal_MinVoltage)
        self.lineEdit_FourTerminal_MaxVoltage.editingFinished.connect(self.UpdateFourTerminal_MaxVoltage)
        self.lineEdit_FourTerminal_Numberofstep.editingFinished.connect(self.UpdateFourTerminal_Numberofstep)
        self.lineEdit_FourTerminal_Delay.editingFinished.connect(self.UpdateFourTerminal_Delay)
        self.pushButton_FourTerminal_NoSmTpTSwitch.clicked.connect(self.ToggleFourTerminalFourTerminal_Numberofstep)
        
        self.comboBox_FourTerminal_Output1.currentIndexChanged.connect(self.ChangeFourTerminal_Output1_Channel)
        self.comboBox_FourTerminal_Input1.currentIndexChanged.connect(self.ChangeFourTerminal_Input1_Channel)
        self.comboBox_FourTerminal_Input2.currentIndexChanged.connect(self.ChangeFourTerminal_Input2_Channel)
        
#######################################Few Push Button
        self.pushButton_StartFourTerminalSweep.clicked.connect(self.FourTerminalSweep)
        self.pushButton_StartFourTerminalMagneticFieldSweep.clicked.connect(self.FourTerminalMagneticFieldSweep)
        self.pushButton_StartFourTerminalMagneticFieldAbort.clicked.connect(self.AbortFourTerminalMagneticFieldSweep)

#################Four Terminal Magnetic field sweep default parameter
        self.FourTerminalMagneticFieldSetting_MinimumField=0.0
        self.FourTerminalMagneticFieldSetting_MaximumField=0.01
        self.FourTerminalMagneticFieldSetting_Numberofsteps=2
        self.FourTerminalMagneticFieldSetting_Numberofsteps_Status="Numberofsteps"
        self.FourTerminalMagneticFieldSetting_FieldSweepSpeed=1
        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.setText(formatNum(self.FourTerminalMagneticFieldSetting_MinimumField,6))
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.setText(formatNum(self.FourTerminalMagneticFieldSetting_MaximumField,6))
        self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setText(formatNum(self.FourTerminalMagneticFieldSetting_Numberofsteps,6))
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.setText(formatNum(self.FourTerminalMagneticFieldSetting_FieldSweepSpeed,6))
        
        self.comboBox_FourTerminal_Output1.setCurrentIndex(0)
        self.comboBox_FourTerminal_Input1.setCurrentIndex(1)
        self.comboBox_FourTerminal_Input2.setCurrentIndex(0)
        self.FourTerminal_Output1=self.comboBox_FourTerminal_Output1.currentIndex()
        self.FourTerminal_Input1=self.comboBox_FourTerminal_Input1.currentIndex()
        self.FourTerminal_Input2=self.comboBox_FourTerminal_Input2.currentIndex()
        
        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_MinimumField)
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_MaximumField)
        self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla)
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_FieldSweepSpeed)
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
        self.lineEdit_Lockin_Info_Frequency.editingFinished.connect(self.UpdateFrequency)
        self.UpdateVoltage_LI_Timeconstant()
        self.UpdateCurrent_LI_Timeconstant()
        self.UpdateFrequency()
        
#######################################Check Box magnetic Field Sweep
        self.checkBox_FourTerminalMagneticFieldSetting_MoveLineCut.stateChanged.connect(self.updateCheckBox)
        self.checkBox_FourTerminalMagneticFieldSetting_AutoLevel.stateChanged.connect(self.updateCheckBox)
        self.checkBox_FourTerminalMagneticFieldSetting_BacktoZero.stateChanged.connect(self.updateCheckBox)

        
#######################################Setting For Plotting
        self.randomFill = -0.987654321
        self.current_field = 0.0
        self.posx , self.posy , self.scalex, self.scaley =(0.0,0.0,0.0,0.0)
        self.FourTerminalverticaLineCutPosition , self.FourTerminalhorizontalLineCutPosition=0.0 , 0.0
        self.AbortFourTerminalMagneticFieldSweep_Flag =False
        self.MoveLineCutFourTerminalMagneticFieldSweep_Flag =True
        self.AutoLevelFourTerminalMagneticFieldSweep_Flag =True
        self.BacktoZeroFourTerminalMagneticFieldSweep_Flag =True


        self.PlotDataFourTerminalResistance2D=np.zeros([self.FourTerminalMagneticFieldSetting_Numberofsteps,self.FourTerminal_Numberofstep])
        self.PlotDataFourTerminalVoltage2D=np.zeros([self.FourTerminalMagneticFieldSetting_Numberofsteps,self.FourTerminal_Numberofstep])
        self.PlotDataFourTerminalCurrent2D=np.zeros([self.FourTerminalMagneticFieldSetting_Numberofsteps,self.FourTerminal_Numberofstep])
        
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

        self.lockInterface()

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
            elif dict['devices']['system']['magnet supply'] == 'IPS 120 Power Supply':
                self.ips = dict['servers']['remote']['ips120']
                
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            
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
    def FourTerminalSweep(self,c=None): #The Four Terminal Sweep without MagneticField
        self.lockInterface()
        try:
            self.ClearFourTerminalPlot() #Clear the plotted content

            self.SetupFourTerminalSweepSetting("No Magnetic Field") #Assign the DAC settings and DataVault parameters
            
            #Creates a new datavault file and updates the image# labels
            yield self.newDataVaultFile("No Magnetic Field")

            yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.currentDAC_Output[self.FourTerminal_ChannelOutput[0]],self.FourTerminal_MinVoltage,10000,100)    #ramp to initial value
            
            #Give a second after the ramp to allow transients to settle before starting the sweep
            yield self.sleep(1)

            self.FourTerminalXaxis=np.linspace(self.FourTerminal_MinVoltage,self.FourTerminal_MaxVoltage,self.FourTerminal_Numberofstep)  #generating list of voltage at which sweeped
            self.dac_read = yield self.Buffer_Ramp_Display(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.FourTerminal_MinVoltage],[self.FourTerminal_MaxVoltage],self.FourTerminal_Numberofstep,self.FourTerminal_Delay*1000000) #dac_read[0] is voltage,dac_read[1] is current potentially

            self.SetupPlot_Data("No Magnetic Field")#self.Plot_Data: a new set of data particularly for ploting

            self.Format_Data("No Magnetic Field")#Take the Buffer_Ramp Data and save it into self.formatted_data

            yield self.dv.add(self.formatted_data)
            
            yield self.plotData1D(self.Plot_Data[1],self.Plot_Data[2],self.sweepFourTerminal_Plot1)
            if self.FourTerminal_Input2!=4:
                 yield self.plotData1D(self.Plot_Data[1],self.Plot_Data[3],self.sweepFourTerminal_Plot2)
                 yield self.plotData1D(self.Plot_Data[1],self.Plot_Data[4],self.sweepFourTerminal_Plot3)

            yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.FourTerminal_MaxVoltage,0.0,10000,100)
        except Exception as inst:
            print inst

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save the screenshot

    @inlineCallbacks
    def FourTerminalMagneticFieldSweep(self,c=None): #The FourTerminal Sweep with Magnetic Field
        self.lockInterface()

        self.ConnectLineCut()
        
        self.MagneticFieldSweepPoints=np.linspace(self.FourTerminalMagneticFieldSetting_MinimumField,self.FourTerminalMagneticFieldSetting_MaximumField,self.FourTerminalMagneticFieldSetting_Numberofsteps)#Generate Magnetic Field Sweep Point
        
        self.SetupPlotParameter()
        
        try:
            self.ClearFourTerminalMagneticFieldPlot()#Clear the plotted content
            
            self.SetupFourTerminalSweepSetting("Magnetic Field")#Assign the DAC settings and DataVault parameters
            
            self.AutoRangeFourTerminal2DPlot()
            
            self.InitializeLineCutPlot()#Set the LineCut to Bottom Left.
            
            yield self.newDataVaultFile("Magnetic Field")
            
            for self.i in range(0,self.FourTerminalMagneticFieldSetting_Numberofsteps):
                if self.AbortFourTerminalMagneticFieldSweep_Flag:
                    print "Abort the Sweep."
                    self.AbortFourTerminalMagneticFieldSweep_Flag = False
                    break

                print 'Starting sweep with magnetic field set to: ' + str(self.MagneticFieldSweepPoints[self.i])

                #Do this properly considering the edge cases
                yield self.rampMagneticField(self.current_field, self.MagneticFieldSweepPoints[self.i], self.FourTerminalMagneticFieldSetting_FieldSweepSpeed)

                #ramp to initial value
                yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.currentDAC_Output[self.FourTerminal_ChannelOutput[0]],self.FourTerminal_MinVoltage,10000,100)

                #Wait for one second to allow transients to settle
                yield self.sleep(1)

                self.FourTerminalXaxis=np.linspace(self.FourTerminal_MinVoltage,self.FourTerminal_MaxVoltage,self.FourTerminal_Numberofstep)  #generating list of voltage at which sweeped
                #self.dac_read = self.FakeDATA(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.FourTerminal_MinVoltage],[self.FourTerminal_MaxVoltage],self.FourTerminal_Numberofstep,self.FourTerminal_Delay)
                
                self.dac_read= yield self.Buffer_Ramp_Display(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.FourTerminal_MinVoltage],[self.FourTerminal_MaxVoltage],self.FourTerminal_Numberofstep,self.FourTerminal_Delay*1000000) #dac_read[0] is voltage,dac_read[1] is current potentially
                
                self.SetupPlot_Data("Magnetic Field")#self.Plot_Data: a new set of data particularly for ploting

                self.Format_Data("Magnetic Field")

                yield self.dv.add(self.formatted_data)
                
                yield self.UpdateFourTerminal2DPlot(self.Plot_Data[4],self.Plot_Data[2],self.Plot_Data[3])#4 is resistance

                
                if self.MoveLineCutFourTerminalMagneticFieldSweep_Flag:  #update Line Cut
                    self.FourTerminalverticaLineCutPosition = self.MagneticFieldSweepPoints[self.i] - self.scalex / 2.0  #Prevent Edge state at end
                    if self.i == 0:
                        self.FourTerminalverticaLineCutPosition = self.MagneticFieldSweepPoints[self.i]
                    self.UpdateFourTerminalMagneticField_LineCutPlot()
                    self.MoveFourTerminalLineCut()
                    #Could be done more properly for this step
                    self.lineEdit_FourTerminalMagneticFieldSetting_MagneticFieldValue.setText(formatNum(self.FourTerminalverticaLineCutPosition))

                
                if self.AutoLevelFourTerminalMagneticFieldSweep_Flag: #Autolevel
                    self.AutoLevelFourTerminal2DPlot()
                
                yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.FourTerminal_MaxVoltage,0.0,10000,100)

            if self.BacktoZeroFourTerminalMagneticFieldSweep_Flag:
                print "Ramp Field Back to Zero"
                yield self.rampMagneticField(self.current_field, 0.0, self.FourTerminalMagneticFieldSetting_FieldSweepSpeed)

        except Exception as inst:
            print inst

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save the screenshot

    def AbortFourTerminalMagneticFieldSweep(self):
        self.AbortFourTerminalMagneticFieldSweep_Flag =True
        
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
                newData = yield self.dac.buffer_ramp(out_list,in_list,[startx],[stopx], self.numberfastdata, self.FourTerminal_Delay*1000000)

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

    def UpdateFourTerminal_MinVoltage(self):
        dummystr=str(self.lineEdit_FourTerminal_MinVoltage.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
            self.FourTerminal_MinVoltage=dummyval
        self.lineEdit_FourTerminal_MinVoltage.setText(formatNum(self.FourTerminal_MinVoltage,6))

    def UpdateFourTerminal_MaxVoltage(self):
        dummystr=str(self.lineEdit_FourTerminal_MaxVoltage.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
            self.FourTerminal_MaxVoltage=dummyval
        self.lineEdit_FourTerminal_MaxVoltage.setText(formatNum(self.FourTerminal_MaxVoltage,6))

    def UpdateFourTerminal_Numberofstep(self):
        dummystr=str(self.lineEdit_FourTerminal_Numberofstep.text())   #read the text
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            if self.FourTerminalSetting_Numberofsteps_Status == "Numberofsteps":   #based on status, dummyval is deterimined and update the Numberof steps parameters
                self.FourTerminal_Numberofstep=int(round(dummyval)) #round here is necessary, without round it cannot do 1001 steps back and force
            if self.FourTerminalSetting_Numberofsteps_Status == "StepSize":
                self.FourTerminal_Numberofstep=int(self.StepSizetoNumberofsteps_Convert(self.FourTerminal_MaxVoltage,self.FourTerminal_MinVoltage,float(dummyval)))
        self.RefreshFourTerminal_Numberofstep()

    def RefreshFourTerminal_Numberofstep(self): #Refresh based on the status change the lineEdit text
        if self.FourTerminalSetting_Numberofsteps_Status == "Numberofsteps":
            self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.FourTerminal_Numberofstep,6))
        else:
            self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.NumberofstepstoStepSize_Convert(self.FourTerminal_MaxVoltage,self.FourTerminal_MinVoltage,self.FourTerminal_Numberofstep),6))

    def ToggleFourTerminalFourTerminal_Numberofstep(self):
        if self.FourTerminalSetting_Numberofsteps_Status == "Numberofsteps":
            self.label_FourTerminalNumberofstep.setText('Volt per Steps')
            self.FourTerminalSetting_Numberofsteps_Status = "StepSize"
            self.RefreshFourTerminal_Numberofstep() #Change the text first
            self.UpdateFourTerminal_Numberofstep()
        else:
            self.label_FourTerminalNumberofstep.setText('Number of Steps')
            self.FourTerminalSetting_Numberofsteps_Status = "Numberofsteps"
            self.RefreshFourTerminal_Numberofstep() #Change the text first
            self.UpdateFourTerminal_Numberofstep()

    def UpdateFourTerminal_Delay(self):
        dummystr=str(self.lineEdit_FourTerminal_Delay.text())
        dummyval=readNum(dummystr, self , True)
        if isinstance(dummyval,float):
            self.FourTerminal_Delay=float(dummyval)
        self.lineEdit_FourTerminal_Delay.setText(formatNum(self.FourTerminal_Delay,6))

    def UpdateDevice_Name(self):
        self.Device_Name=str(self.lineEdit_Device_Name.text())

    def UpdateFourTerminal_NameOutput1(self):
        self.FourTerminal_NameOutput1=str(self.lineEdit_FourTerminal_NameOutput1.text())
        self.updateFourTerminalPlotLabel()

    def UpdateFourTerminal_NameInput1(self):
        self.FourTerminal_NameInput1=str(self.lineEdit_FourTerminal_NameInput1.text())
        self.updateFourTerminalPlotLabel()

    def UpdateFourTerminal_NameInput2(self):
        self.FourTerminal_NameInput2=str(self.lineEdit_FourTerminal_NameInput2.text())
        self.updateFourTerminalPlotLabel()

    def UpdateFourTerminalMagneticFieldSetting_MinimumField(self):
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.FourTerminalMagneticFieldSetting_MinimumField=dummyval
        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.setText(formatNum(self.FourTerminalMagneticFieldSetting_MinimumField,6))
        self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()

    def UpdateFourTerminalMagneticFieldSetting_MaximumField(self):
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.FourTerminalMagneticFieldSetting_MaximumField=dummyval
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.setText(formatNum(self.FourTerminalMagneticFieldSetting_MaximumField,6))
        self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()

    def UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla(self):
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.text())   #read the text
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            if self.FourTerminalMagneticFieldSetting_Numberofsteps_Status == "Numberofsteps":   #based on status, dummyval is deterimined and update the Numberof steps parameters
                self.FourTerminalMagneticFieldSetting_Numberofsteps=int(round(dummyval))
            if self.FourTerminalMagneticFieldSetting_Numberofsteps_Status == "StepSize":
                self.FourTerminalMagneticFieldSetting_Numberofsteps=int(self.StepSizetoNumberofsteps_Convert(self.FourTerminalMagneticFieldSetting_MaximumField,self.FourTerminalMagneticFieldSetting_MinimumField,float(dummyval)))
        self.RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()

    def RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla(self): #Refresh based on the status change the lineEdit text
        if self.FourTerminalMagneticFieldSetting_Numberofsteps_Status == "Numberofsteps":
            self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setText(formatNum(self.FourTerminalMagneticFieldSetting_Numberofsteps,6))
        else:
            self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.setText(formatNum(self.NumberofstepstoStepSize_Convert(self.FourTerminalMagneticFieldSetting_MaximumField,self.FourTerminalMagneticFieldSetting_MinimumField,self.FourTerminalMagneticFieldSetting_Numberofsteps),6))

    def ToggleFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla(self):
        if self.FourTerminalMagneticFieldSetting_Numberofsteps_Status == "Numberofsteps":
            self.label_FourTerminalMagneticFieldSetting_NumberofSteps.setText('Tesla per Steps')
            self.FourTerminalMagneticFieldSetting_Numberofsteps_Status = "StepSize"
            self.RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla() #Change the text first
            self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()
        else:
            self.label_FourTerminalMagneticFieldSetting_NumberofSteps.setText('Number of Steps')
            self.FourTerminalMagneticFieldSetting_Numberofsteps_Status = "Numberofsteps"
            self.RefreshFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla() #Change the text first
            self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla()
       
    def NumberofstepstoStepSize_Convert(self,Max,Min,NoS):
        StepSize=float((Max-Min)/float(NoS-1.0))
        return StepSize

    def StepSizetoNumberofsteps_Convert(self,Max,Min,SS):
        Numberofsteps=int((Max-Min)/float(SS)+1)
        return Numberofsteps

    def UpdateFourTerminalMagneticFieldSetting_FieldSweepSpeed(self):
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.FourTerminalMagneticFieldSetting_FieldSweepSpeed=dummyval
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.setText(formatNum(self.FourTerminalMagneticFieldSetting_FieldSweepSpeed,6))
        
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

    def UpdateFrequency(self):
        dummystr=str(self.lineEdit_Lockin_Info_Frequency.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.Frequency=dummyval
        self.lineEdit_Lockin_Info_Frequency.setText(formatNum(self.Frequency,6))
        
        
    def updateCheckBox(self):
        self.MoveLineCutFourTerminalMagneticFieldSweep_Flag =self.checkBox_FourTerminalMagneticFieldSetting_MoveLineCut.isChecked()
        self.AutoLevelFourTerminalMagneticFieldSweep_Flag =self.checkBox_FourTerminalMagneticFieldSetting_AutoLevel.isChecked()
        self.BacktoZeroFourTerminalMagneticFieldSweep_Flag =self.checkBox_FourTerminalMagneticFieldSetting_BacktoZero.isChecked()
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
            print inst

    def SetupFourTerminalSweepSetting(self,Status):
        #Sets up the lists of inputs and outputs for the dac buffer ramp as well as sets up the names for the columns on datavault
    
        self.FourTerminal_ChannelOutput=[self.FourTerminal_Output1] #Setup for bufferramp function

        self.FourTerminal_ChannelInput=[self.FourTerminal_Input1] #Setup for bufferramp function
        #If FourTerminal_Input2 is 4, then this corresponds to 'None' having been selected on the GUI, in which case it's a two wire measurement
        if self.FourTerminal_Input2!=4:
            self.FourTerminal_ChannelInput.append(self.FourTerminal_Input2)# Create the list of Channel that we read while sweep #setup for bufferramp function

        #datavaultXaxis is the list of independent variables on the sweep
        self.datavaultXaxis=[self.FourTerminal_NameOutput1+' index', self.FourTerminal_NameOutput1]
        if Status == "Magnetic Field":
            self.datavaultXaxis=['Magnetic Field index', self.FourTerminal_NameOutput1+' index', 'Magnetic Field', self.FourTerminal_NameOutput1]
            
        #datavaultYaxis is the list of dependent variables on the sweep
        self.datavaultYaxis=[self.FourTerminal_NameInput1]
        if self.FourTerminal_Input2!=4:  #add additional data if Input2 is not None
            self.datavaultYaxis=[self.FourTerminal_NameInput1, self.FourTerminal_NameInput2, "Resistance"]
            
    def Format_Data(self,Status):
        """
        Format_Data structure:
        #MagneticField Index, Gate Voltage Index, #MagneticField, Gate Voltage, Voltage, #Current, #Resistance
        Plot_Data structure:
        Gate Voltage Index, Gate Voltage, Voltage, #Current, #Resistance, #MagneticField Index, #MagneticField
        """
        self.formatted_data = []
        for j in range(0, self.FourTerminal_Numberofstep):
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
                self.formatted_data[j]+=(resistance,)  #proccessing to Resistance
                self.Plot_Data[4].append(resistance)
                
    @inlineCallbacks
    def newDataVaultFile(self,Status):
        if Status== "Magnetic Field":
            file = yield self.dv.new('FourTerminal MagneticField ' + self.Device_Name, self.datavaultXaxis,self.datavaultYaxis)
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
        yield self.dv.add_parameter('Lock in Frequency(Hz)',float(self.Frequency))

    def SetupPlot_Data(self,Status):
        """
        Plot_Data structure:
        Gate Voltage Index, Gate Voltage, Voltage, #Current, #Resistance, #MagneticField Index, #MagneticField
        """
        self.Plot_Data=[range(0,self.FourTerminal_Numberofstep)]
        self.Plot_Data.append(self.FourTerminalXaxis)
        self.Plot_Data.append([])
        if self.FourTerminal_Input2!=4:
            self.Plot_Data.append([])
            self.Plot_Data.append([])
        if Status == "Magnetic Field":
            self.Plot_Data.append([range(0,self.FourTerminalMagneticFieldSetting_Numberofsteps)])
            self.Plot_Data.append(self.MagneticFieldSweepPoints)

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
    def plotData1D(self,xaxis,yaxis,plot):
        plot.plot(x = xaxis, y = yaxis, pen = 0.5)
        
    def setupAdditionalUi(self):
        self.setupFourTerminalPlot()
        self.setupFourTerminalMagneticFieldResistancePlot()
        self.setupFourTerminalMagneticFieldVoltagePlot()
        self.setupFourTerminalMagneticFieldCurrentPlot()
        self.SetupFourTerminalMageneticField2DPlot()
        self.SetupLineCut()

    def setupFourTerminalPlot(self):
        self.sweepFourTerminal_Plot1 = pg.PlotWidget(parent = self.FourTerminalPlot1)
        self.sweepFourTerminal_Plot1.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepFourTerminal_Plot1.setTitle( self.FourTerminal_NameInput1)
        self.sweepFourTerminal_Plot1.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.sweepFourTerminal_Plot1.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot1.showAxis('right', show = True)
        self.sweepFourTerminal_Plot1.showAxis('top', show = True)
        self.sweepFourTerminal_Plot1.setXRange(0,1)
        self.sweepFourTerminal_Plot1.setYRange(0,2)
        self.sweepFourTerminal_Plot1.enableAutoRange(enable = True)
        self.Layout_FourTerminalPlot1.addWidget(self.sweepFourTerminal_Plot1)

        self.sweepFourTerminal_Plot2 = pg.PlotWidget(parent = self.FourTerminalPlot2)
        self.sweepFourTerminal_Plot2.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepFourTerminal_Plot2.setTitle( self.FourTerminal_NameInput2)
        self.sweepFourTerminal_Plot2.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.sweepFourTerminal_Plot2.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot2.showAxis('right', show = True)
        self.sweepFourTerminal_Plot2.showAxis('top', show = True)
        self.sweepFourTerminal_Plot2.setXRange(0,1)
        self.sweepFourTerminal_Plot2.setYRange(0,2)
        self.sweepFourTerminal_Plot2.enableAutoRange(enable = True)
        self.Layout_FourTerminalPlot2.addWidget(self.sweepFourTerminal_Plot2)

        self.sweepFourTerminal_Plot3 = pg.PlotWidget(parent = self.FourTerminalPlot3)
        self.sweepFourTerminal_Plot3.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepFourTerminal_Plot3.setTitle( 'Resistance')
        self.sweepFourTerminal_Plot3.setLabel('left', 'Resistance', units = 'Ohm')
        self.sweepFourTerminal_Plot3.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot3.showAxis('right', show = True)
        self.sweepFourTerminal_Plot3.showAxis('top', show = True)
        self.sweepFourTerminal_Plot3.setXRange(0,1)
        self.sweepFourTerminal_Plot3.setYRange(0,2)
        self.sweepFourTerminal_Plot3.enableAutoRange(enable = True)
        self.Layout_FourTerminalPlot3.addWidget(self.sweepFourTerminal_Plot3)

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
        
    def setupFourTerminalMagneticFieldResistancePlot(self): # There is a misnomer in my code. I Called the versus field 1D plot as versus "field" as you change the field value line cut. In acutally content of lthe plotttinfg it is actually versus Gata Voltage
        self.view_sweepFourTerminalMagneticField_Resistance_Plot = pg.PlotItem(name = "Four Terminal Resistance versus Magnetic Field Resistance Plot",title = "Resistance")
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.showAxis('top', show = True)
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.showAxis('right', show = True)
        self.sweepFourTerminalMagneticField_Resistance_Plot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Resistance_2DPlot, view = self.view_sweepFourTerminalMagneticField_Resistance_Plot)
        self.sweepFourTerminalMagneticField_Resistance_Plot.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepFourTerminalMagneticField_Resistance_Plot.ui.menuBtn.hide()
        self.sweepFourTerminalMagneticField_Resistance_Plot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.sweepFourTerminalMagneticField_Resistance_Plot.ui.roiBtn.hide()
        self.sweepFourTerminalMagneticField_Resistance_Plot.ui.menuBtn.hide()
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setAspectLocked(False)
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.invertY(False)
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setXRange(-1.25,1.25,0)
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setYRange(-10,10, 0)
        self.Frame_FourTerminalMagneticField_Resistance_2DPlot.close() #necessary for streching the window
        self.Layout_FourTerminalMagneticField_Resistance_2DPlot.addWidget(self.sweepFourTerminalMagneticField_Resistance_Plot)

        self.FourTerminalMagneticField_Resistance_VersusField_Plot = pg.PlotWidget(parent = None)
        self.SetupLineCutMagneticFieldPlot(self.FourTerminalMagneticField_Resistance_VersusField_Plot,self.Layout_FourTerminalMagneticField_Resistance_VersusField,'Resistance','Ohm')

        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot = pg.PlotWidget(parent = None)
        self.SetupLineCutGateVoltagePlot(self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot,self.Layout_FourTerminalMagneticField_Resistance_VersusGateVoltage,'Resistance','Ohm')
    
    def setupFourTerminalMagneticFieldVoltagePlot(self):
        self.view_sweepFourTerminalMagneticField_Voltage_Plot = pg.PlotItem(name = "Four Terminal Voltage versus Magnetic Field Voltage Plot",title = self.FourTerminal_NameInput1)
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.showAxis('top', show = True)
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.showAxis('right', show = True)
        self.sweepFourTerminalMagneticField_Voltage_Plot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Voltage_2DPlot, view = self.view_sweepFourTerminalMagneticField_Voltage_Plot)
        self.sweepFourTerminalMagneticField_Voltage_Plot.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepFourTerminalMagneticField_Voltage_Plot.ui.menuBtn.hide()
        self.sweepFourTerminalMagneticField_Voltage_Plot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.sweepFourTerminalMagneticField_Voltage_Plot.ui.roiBtn.hide()
        self.sweepFourTerminalMagneticField_Voltage_Plot.ui.menuBtn.hide()
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setAspectLocked(False)
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.invertY(False)
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setXRange(-1.25,1.25,0)
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setYRange(-10,10, 0)
        self.Frame_FourTerminalMagneticField_Voltage_2DPlot.close() #necessary for streching the window
        self.Layout_FourTerminalMagneticField_Voltage_2DPlot.addWidget(self.sweepFourTerminalMagneticField_Voltage_Plot)

        self.FourTerminalMagneticField_Voltage_VersusField_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Voltage_VersusField)
        self.SetupLineCutMagneticFieldPlot(self.FourTerminalMagneticField_Voltage_VersusField_Plot,self.Layout_FourTerminalMagneticField_Voltage_VersusField,self.FourTerminal_NameInput1,'V')

        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Voltage_VersusGateVoltage)
        self.SetupLineCutGateVoltagePlot(self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot,self.Layout_FourTerminalMagneticField_Voltage_VersusGateVoltage,self.FourTerminal_NameInput1,'V')

    def setupFourTerminalMagneticFieldCurrentPlot(self):
        self.view_sweepFourTerminalMagneticField_Current_Plot = pg.PlotItem(name = "Four Terminal Current versus Magnetic Field Voltage Plot",title = self.FourTerminal_NameInput2)
        self.view_sweepFourTerminalMagneticField_Current_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Current_Plot.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view_sweepFourTerminalMagneticField_Current_Plot.showAxis('top', show = True)
        self.view_sweepFourTerminalMagneticField_Current_Plot.showAxis('right', show = True)
        self.sweepFourTerminalMagneticField_Current_Plot = pg.ImageView(parent = self.Frame_FourTerminalMagneticField_Current_2DPlot, view = self.view_sweepFourTerminalMagneticField_Current_Plot)
        self.sweepFourTerminalMagneticField_Current_Plot.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepFourTerminalMagneticField_Current_Plot.ui.menuBtn.hide()
        self.sweepFourTerminalMagneticField_Current_Plot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.sweepFourTerminalMagneticField_Current_Plot.ui.roiBtn.hide()
        self.sweepFourTerminalMagneticField_Current_Plot.ui.menuBtn.hide()
        self.view_sweepFourTerminalMagneticField_Current_Plot.setAspectLocked(False)
        self.view_sweepFourTerminalMagneticField_Current_Plot.invertY(False)
        self.view_sweepFourTerminalMagneticField_Current_Plot.setXRange(-1.25,1.25,0)
        self.view_sweepFourTerminalMagneticField_Current_Plot.setYRange(-10,10, 0)
        self.Frame_FourTerminalMagneticField_Current_2DPlot.close() #necessary for streching the window
        self.Layout_FourTerminalMagneticField_Current_2DPlot.addWidget(self.sweepFourTerminalMagneticField_Current_Plot)

        self.FourTerminalMagneticField_Current_VersusField_Plot = pg.PlotWidget(parent = None)
        self.SetupLineCutMagneticFieldPlot(self.FourTerminalMagneticField_Current_VersusField_Plot,self.Layout_FourTerminalMagneticField_Current_VersusField,self.FourTerminal_NameInput2,'A')

        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Current_VersusGateVoltage)
        self.SetupLineCutGateVoltagePlot(self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot,self.Layout_FourTerminalMagneticField_Current_VersusGateVoltage,self.FourTerminal_NameInput2,'A')

    def updateFourTerminalPlotLabel(self):
        self.sweepFourTerminal_Plot1.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.sweepFourTerminal_Plot1.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot2.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.sweepFourTerminal_Plot2.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot3.setLabel('left', 'Resistance', units = 'Ohm')
        self.sweepFourTerminal_Plot3.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setTitle(self.FourTerminal_NameInput1)
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Current_Plot.setTitle(self.FourTerminal_NameInput2)
        self.view_sweepFourTerminalMagneticField_Current_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Current_VersusField_Plot.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusField_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        
    def AutoRangeFourTerminal2DPlot(self):
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        
    def AutoLevelFourTerminal2DPlot(self):
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D, autoRange = False , autoLevels = True, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        
    def ClearFourTerminalPlot(self):
        self.sweepFourTerminal_Plot1.clear()
        self.sweepFourTerminal_Plot2.clear()
        self.sweepFourTerminal_Plot3.clear()

    def ClearFourTerminal2DPlot(self):
        self.sweepFourTerminalMagneticField_Resistance_Plot.clear()
        self.sweepFourTerminalMagneticField_Voltage_Plot.clear()
        self.sweepFourTerminalMagneticField_Current_Plot.clear()
        self.PlotDataFourTerminalResistance2D=np.zeros([self.FourTerminalMagneticFieldSetting_Numberofsteps,self.FourTerminal_Numberofstep])
        self.PlotDataFourTerminalVoltage2D=np.zeros([self.FourTerminalMagneticFieldSetting_Numberofsteps,self.FourTerminal_Numberofstep])
        self.PlotDataFourTerminalCurrent2D=np.zeros([self.FourTerminalMagneticFieldSetting_Numberofsteps,self.FourTerminal_Numberofstep])
        
    def ClearFourTerminalMagneticFieldPlot(self):
        self.ClearFourTerminal2DPlot()
        self.ClearLineCutPlot()
                
    def SetupPlotParameter(self):
        #set up the parameter for ploting, pos and scale
        self.posx, self.posy = ( self.FourTerminalMagneticFieldSetting_MinimumField, self.FourTerminal_MinVoltage)
        self.scalex, self.scaley = ( (self.FourTerminalMagneticFieldSetting_MaximumField-self.FourTerminalMagneticFieldSetting_MinimumField)/self.FourTerminalMagneticFieldSetting_Numberofsteps,(self.FourTerminal_MaxVoltage-self.FourTerminal_MinVoltage)/self.FourTerminal_Numberofstep)

    def SetupFourTerminalMageneticField2DPlot(self):
        
        self.SetupPlotParameter()
        #Associate the Data with each 2D plot
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D, autoRange = True , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        
        #Setup the linecut in the plot
        self.FourTerminalVerticalLinePlotResistance = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.FourTerminalHorizontalLinePlotResistance = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.FourTerminalVerticalLinePlotVoltage = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.FourTerminalHorizontalLinePlotVoltage = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.FourTerminalVerticalLinePlotCurrent = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.FourTerminalHorizontalLinePlotCurrent = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        
##########################              Plot Related functions                 #############

##########################              LineCut Related functions                 #############
    def InitializeLineCutPlot(self):
        self.FourTerminalverticaLineCutPosition = self.FourTerminalMagneticFieldSetting_MinimumField
        self.FourTerminalhorizontalLineCutPosition = self.FourTerminal_MinVoltage
        self.MoveFourTerminalLineCut()

    def SetupLineCutMagneticFieldValue(self): #Corresponding to change in lineEdit
        dummystr=str(self.lineEdit_FourTerminalMagneticFieldSetting_MagneticFieldValue.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.FourTerminalVerticalLinePlotResistance.setValue(dummyval)
            self.FourTerminalVerticalLinePlotVoltage.setValue(dummyval)
            self.FourTerminalVerticalLinePlotCurrent.setValue(dummyval)            
        self.FourTerminalverticaLineCutPosition=dummyval
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
        #print self.FourTerminalverticaLineCutPosition
        #print self.FourTerminalMagneticFieldSetting_MinimumField
        #print self.scalex
        xindex = int((self.FourTerminalverticaLineCutPosition - self.FourTerminalMagneticFieldSetting_MinimumField)/self.scalex)
        yindex = int((self.FourTerminalhorizontalLineCutPosition - self.FourTerminal_MinVoltage)/self.scaley)

        self.ClearLineCutPlot()


        self.FourTerminalMagneticField_Resistance_VersusField_Plot.plot(x=self.PlotDataFourTerminalResistance2D[xindex], y=self.Plot_Data[1], pen = 0.5)
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.plot(x=self.MagneticFieldSweepPoints,y=self.PlotDataFourTerminalResistance2D[:,yindex],pen = 0.5)
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.plot(x=self.PlotDataFourTerminalVoltage2D[xindex], y=self.Plot_Data[1], pen = 0.5)
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.plot(x=self.MagneticFieldSweepPoints,y=self.PlotDataFourTerminalVoltage2D[:,yindex],pen = 0.5)
        self.FourTerminalMagneticField_Current_VersusField_Plot.plot(x=self.PlotDataFourTerminalCurrent2D[xindex], y=self.Plot_Data[1], pen = 0.5)
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.plot(x=self.MagneticFieldSweepPoints,y=self.PlotDataFourTerminalCurrent2D[:,yindex],pen = 0.5)
        
    def UpdateFourTerminal2DPlot(self,newResistancedata,newVoltagedata,newCurrentdata):
        #Add data to the Plotted 2D Data
        self.PlotDataFourTerminalResistance2D[self.i] = newResistancedata
        self.PlotDataFourTerminalVoltage2D[self.i] = newVoltagedata
        self.PlotDataFourTerminalCurrent2D[self.i] = newCurrentdata
                
        #Update the Plot with new Data
        self.sweepFourTerminalMagneticField_Resistance_Plot.setImage(self.PlotDataFourTerminalResistance2D, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Voltage_Plot.setImage(self.PlotDataFourTerminalVoltage2D, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])
        self.sweepFourTerminalMagneticField_Current_Plot.setImage(self.PlotDataFourTerminalCurrent2D, autoRange = False , autoLevels = False, pos=[self.posx, self.posy],scale=[self.scalex, self.scaley])        
        
    def ChangeFourTerminalLineCutValue(self,LineCut): #Take a input to determine if it is change from editing lineEdit or changing the linecut in the graph
        #Update the value if change from moving
        if LineCut == self.FourTerminalVerticalLinePlotResistance or LineCut == self.FourTerminalVerticalLinePlotVoltage or  LineCut == self.FourTerminalVerticalLinePlotCurrent:
            self.FourTerminalverticaLineCutPosition=LineCut.value()

        if LineCut == self.FourTerminalHorizontalLinePlotResistance or LineCut == self.FourTerminalHorizontalLinePlotVoltage or  LineCut == self.FourTerminalHorizontalLinePlotCurrent:
            self.FourTerminalhorizontalLineCutPosition=LineCut.value()
        #Update the text
        self.lineEdit_FourTerminalMagneticFieldSetting_MagneticFieldValue.setText(formatNum(self.FourTerminalverticaLineCutPosition))
        self.lineEdit_FourTerminalMagneticFieldSetting_GateVoltageValue.setText(formatNum(self.FourTerminalhorizontalLineCutPosition))
        
        #Update the position according to the value
        self.MoveFourTerminalLineCut()
        
        #Update the Linecut Plot with newly edited value of position
        self.UpdateFourTerminalMagneticField_LineCutPlot()
        
    def MoveFourTerminalLineCut(self):
        self.FourTerminalVerticalLinePlotResistance.setValue(float(self.FourTerminalverticaLineCutPosition))
        self.FourTerminalVerticalLinePlotVoltage.setValue(float(self.FourTerminalverticaLineCutPosition))
        self.FourTerminalVerticalLinePlotCurrent.setValue(float(self.FourTerminalverticaLineCutPosition))  
        self.FourTerminalHorizontalLinePlotResistance.setValue(float(self.FourTerminalhorizontalLineCutPosition))
        self.FourTerminalHorizontalLinePlotVoltage.setValue(float(self.FourTerminalhorizontalLineCutPosition))
        self.FourTerminalHorizontalLinePlotCurrent.setValue(float(self.FourTerminalhorizontalLineCutPosition))
            
    def SetupLineCut(self):
        """
        self.FourTerminalverticaLineCutPosition
        self.FourTerminalhorizontalLineCutPosition
        """
        # if self.FourTerminalLineCut:
            # print "removing protocal"
            # self.sweepFourTerminalMagneticField_Resistance_Plot.removeItem(self.FourTerminalVerticalLinePlotResistance)
            # self.sweepFourTerminalMagneticField_Resistance_Plot.removeItem(self.FourTerminalHorizontalLinePlotResistance)
            # self.sweepFourTerminalMagneticField_Voltage_Plot.removeItem(self.FourTerminalVerticalLinePlotVoltage)
            # self.sweepFourTerminalMagneticField_Voltage_Plot.removeItem(self.FourTerminalHorizontalLinePlotVoltage)
            # self.sweepFourTerminalMagneticField_Current_Plot.removeItem(self.FourTerminalVerticalLinePlotCurrent)
            # self.sweepFourTerminalMagneticField_Current_Plot.removeItem(self.FourTerminalHorizontalLinePlotCurrent)
        self.sweepFourTerminalMagneticField_Resistance_Plot.addItem(self.FourTerminalVerticalLinePlotResistance, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Resistance_Plot.addItem(self.FourTerminalHorizontalLinePlotResistance, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Voltage_Plot.addItem(self.FourTerminalVerticalLinePlotVoltage, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Voltage_Plot.addItem(self.FourTerminalHorizontalLinePlotVoltage, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Current_Plot.addItem(self.FourTerminalVerticalLinePlotCurrent, ignoreBounds = True)
        self.sweepFourTerminalMagneticField_Current_Plot.addItem(self.FourTerminalHorizontalLinePlotCurrent, ignoreBounds = True)
    
    def ConnectLineCut(self):
        self.FourTerminalVerticalLinePlotResistance.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalVerticalLinePlotResistance))
        self.FourTerminalHorizontalLinePlotResistance.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalHorizontalLinePlotResistance))
        self.FourTerminalVerticalLinePlotVoltage.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalVerticalLinePlotVoltage))
        self.FourTerminalHorizontalLinePlotVoltage.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalHorizontalLinePlotVoltage))
        self.FourTerminalVerticalLinePlotCurrent.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalVerticalLinePlotCurrent))
        self.FourTerminalHorizontalLinePlotCurrent.sigPositionChangeFinished.connect(lambda:self.ChangeFourTerminalLineCutValue(self.FourTerminalHorizontalLinePlotCurrent))
        #This is not used for now self.FourTerminalLineCut = True
        
    def ClearLineCutPlot(self):
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.clear()
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
        for i in range(0,len(Input)):
            fake.append([])
            for j in range (0,NoS):
                fake[i].append(i+j+self.i+2)
        return fake
               
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
