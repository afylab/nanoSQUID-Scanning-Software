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

        self.aspectLocked = True
        self.FrameLocked = True
        self.LinearSpeedLocked = False
        self.DataLocked = True
        self.scanSmooth = True
        self.scanCoordinates = False
        self.dataProcessing = 'Raw'
        self.dataPostProcessing = 'Raw'

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

        #Might be useful later, currently not in use
        #Defining Channel to Number
        self.DAC_Channel= {
         'DAC 1':0,
         'DAC 2':1,
         'DAC 3':2,
         'DAC 4':3,
         'ADC 1':0,
         'ADC 2':1,
         'ADC 3':2,
         'ADC 4':3,
         }

###########################################initialize the DAC and set all the Output to 0##################
        self.currentDAC_Output=[0.0,0.0,0.0,0.0]
        self.SetpointDAC_Output=[0.0,0.0,0.0,0.0]


        # for i in range(4):                                              Can be implemented when labradconnect is done
            # self.dac.set_voltage(i,0,0)
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



        #FourTerminal sweep default parameter
        self.FourTerminal_ChannelInput=[]
        self.FourTerminal_ChannelOutput=[]
        self.FourTerminal_MinVoltage=-0.1
        self.FourTerminal_MaxVoltage=0.1
        self.FourTerminal_Numberofstep=100
        self.FourTerminalSetting_Numberofsteps_Status="Numberofsteps"
        self.FourTerminal_Delay=10
        self.lineEdit_FourTerminal_MinVoltage.setText(formatNum(self.FourTerminal_MinVoltage,6))
        self.lineEdit_FourTerminal_MaxVoltage.setText(formatNum(self.FourTerminal_MaxVoltage,6))
        self.lineEdit_FourTerminal_Numberofstep.setText(formatNum(self.FourTerminal_Numberofstep,6))
        self.lineEdit_FourTerminal_Delay.setText(formatNum(self.FourTerminal_Delay,6))

        #Magnetic field sweep default parameter
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

        self.randomFill = -0.987654321
        #do not know what it means
        self.numberfastdata=100
        self.numberslowdata=100
        self.dvFileName=""

        self.moveDefault()

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)

#######################################
        self.pushButton_StartFourTerminalSweep.clicked.connect(self.FourTerminalSweep)
        self.pushButton_DummyConnect.clicked.connect(self.connectLabRAD)

#######################################
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

#######################################
        self.lineEdit_FourTerminal_MinVoltage.editingFinished.connect(self.UpdateFourTerminal_MinVoltage)
        self.lineEdit_FourTerminal_MaxVoltage.editingFinished.connect(self.UpdateFourTerminal_MaxVoltage)
        self.lineEdit_FourTerminal_Numberofstep.editingFinished.connect(self.UpdateFourTerminal_Numberofstep)
        self.lineEdit_FourTerminal_Delay.editingFinished.connect(self.UpdateFourTerminal_Delay)
        self.pushButton_FourTerminal_NoSmTpTSwitch.clicked.connect(self.ToggleFourTerminalFourTerminal_Numberofstep)

        self.lineEdit_FourTerminalMagneticFieldSetting_MinimumField.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_MinimumField)
        self.lineEdit_FourTerminalMagneticFieldSetting_MaximumField.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_MaximumField)
        self.lineEdit_FourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla)
        self.lineEdit_FourTerminalMagneticFieldSetting_FieldSweepSpeed.editingFinished.connect(self.UpdateFourTerminalMagneticFieldSetting_FieldSweepSpeed)
        self.pushButton_FourTerminalMagneticFieldSetting_NoSmTpTSwitch.clicked.connect(self.ToggleFourTerminalMagneticFieldSetting_NumberofstepsandMilifieldperTesla)
#######################################

        # self.lineEdit_Channel.editingFinished.connect(self.UpdateChannel)

#######################################
        self.comboBox_FourTerminal_Output1.currentIndexChanged.connect(self.ChangeFourTerminal_Output1_Channel)
        self.comboBox_FourTerminal_Input1.currentIndexChanged.connect(self.ChangeFourTerminal_Input1_Channel)
        self.comboBox_FourTerminal_Input2.currentIndexChanged.connect(self.ChangeFourTerminal_Input2_Channel)
#######################################

#######################################
        self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentIndexChanged.connect(self.ChangeVoltage_LI_Sensitivity_1stdigit)
        self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentIndexChanged.connect(self.ChangeVoltage_LI_Sensitivity_2nddigit)
        self.comboBox_Voltage_LI_Sensitivity_Unit.currentIndexChanged.connect(self.ChangeVoltage_LI_Sensitivity_Unit)
        self.comboBox_Voltage_LI_Expand.currentIndexChanged.connect(self.ChangeVoltage_LI_Expand)
        self.comboBox_Current_LI_Sensitivity_1stdigit.currentIndexChanged.connect(self.ChangeCurrent_LI_Sensitivity_1stdigit)
        self.comboBox_Current_LI_Sensitivity_2nddigit.currentIndexChanged.connect(self.ChangeCurrent_LI_Sensitivity_2nddigit)
        self.comboBox_Current_LI_Sensitivity_Unit.currentIndexChanged.connect(self.ChangeCurrent_LI_Sensitivity_Unit)
        self.comboBox_Current_LI_Expand.currentIndexChanged.connect(self.ChangeCurrent_LI_Expand)

#######################################
#######################################
        self.Voltage_LI_Multiplier1=0.0
        self.Voltage_LI_Multiplier2=0.0
        self.Voltage_LI_Multiplier3=0.0
        self.Voltage_LI_Multiplier4=0.0
        self.Current_LI_Multiplier1=0.0
        self.Current_LI_Multiplier2=0.0
        self.Current_LI_Multiplier3=0.0
        self.Current_LI_Multiplier4=0.0
        self.ChangeVoltage_LI_Sensitivity_1stdigit()
        self.ChangeVoltage_LI_Sensitivity_2nddigit()
        self.ChangeVoltage_LI_Sensitivity_Unit()
        self.ChangeVoltage_LI_Expand()
        self.ChangeCurrent_LI_Sensitivity_1stdigit()
        self.ChangeCurrent_LI_Sensitivity_2nddigit()
        self.ChangeCurrent_LI_Sensitivity_Unit()
        self.ChangeCurrent_LI_Expand()

#######################################

        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None

        self.setupAdditionalUi()

        self.lockInterface()



    def moveDefault(self):
        self.move(550,10)

    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            from labrad.wrappers import connectAsync
            self.cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn.data_vault
            self.dac = yield self.cxn.dac_adc
            yield self.dac.select_device(0L)   #################################you should change this
            self.remotecxn = yield connectAsync(host = '4KMonitor', password = 'pass')

            self.ips = self.remotecxn.ips120_power_supply
            
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except Exception as inst:
            print inst
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        if not self.cxn:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.dac:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.dv:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
            print "Connection Finished"
            self.unlockInterface()

    def disconnectLabRAD(self):
        self.cxn = False
        self.cxn_dv = False
        self.dac = False
        self.gen_dv = False
        self.dv = False
        self.dc_box = False
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

    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous
    # delay that allows other labrad / pyqt methods to run



    @inlineCallbacks
    def FourTerminalSweep(self,c=None):
        self.lockInterface()

        try:
            self.ClearFourTerminalPlot() #Clear the ploted content

            self.SetupFourTerminalSweepSetting("No Magnetic Field") #Assign the DAC settings and DataVault parameters
            
            yield self.ClearBufferedData() #necessary for ramping

            file_info = yield self.dv.new('FourTerminal ' + self.Device_Name, self.datavaultXaxis,self.datavaultYaxis) #this line of code cannot be put into the function
            self.SetupFourTerminalDataVault(file_info , "No Magnetic Field") #Setup DataVault

            yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.currentDAC_Output[self.FourTerminal_ChannelOutput[0]],self.FourTerminal_MinVoltage,10000,100)    #ramp to initial value

            yield self.sleep(1)

            FourTerminalXaxis=np.linspace(self.FourTerminal_MinVoltage,self.FourTerminal_MaxVoltage,self.FourTerminal_Numberofstep)  #generating list of voltage at which sweeped
            dac_read= yield self.Buffer_Ramp_Display(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.FourTerminal_MinVoltage],[self.FourTerminal_MaxVoltage],self.FourTerminal_Numberofstep,self.FourTerminal_Delay) #dac_read[0] is voltage,dac_read[1] is current potentially

            formatted_data = []
            for j in range(0, self.FourTerminal_Numberofstep):
                DummyVoltage=float(dac_read[0][j])/10.0*self.MultiplierVoltage
                formatted_data.append((j, FourTerminalXaxis[j],DummyVoltage))
                if self.FourTerminal_Input2!=4:  #add additional data if Input2 is not None
                    DummyCurrent=float(dac_read[1][j])/10.0*self.MultiplierCurrent
                    formatted_data[j]+=(DummyCurrent,)
                    if DummyCurrent != 0.0:
                        resistance=float(DummyVoltage/DummyCurrent) #generating resisitance
                    else:
                        resistance=float(DummyVoltage/0.0000000001)# Prevent bug as "float cannot be divide by zero"
                    formatted_data[j]+=(resistance,)  #proccessing to Resistance

            yield self.dv.add(formatted_data)
            yield self.plotFourTerminal_Data1(formatted_data)

            yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.FourTerminal_MaxVoltage,0.0,10000,100)

            if self.FourTerminal_Input2!=4:
                 yield self.plotFourTerminal_Data2(formatted_data)
                 yield self.plotFourTerminal_Data3(formatted_data)
        except Exception as inst:
            print inst

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save the screenshot

    def FourTerminalMagneticFieldSweep(self,c=None):
        self.lockInterface()
        
        self.MagneticFieldSweepPoints=np.linspace(self.FourTerminalMagneticFieldSetting_MinimumField,self.FourTerminalMagneticFieldSetting_MaximumField,self.FourTerminalMagneticFieldSetting_Numberofsteps)

        try:
            self.ClearFourTerminalMagneticFieldPlot()

            self.SetupFourTerminalSweepSetting("Magnetic Field")

            yield self.ClearBufferedData()
            
            file_info = yield self.dv.new('FourTerminal versus MagneticField ' + self.Device_Name, self.datavaultXaxis,self.datavaultYaxis)
            self.SetupFourTerminalDataVault(file_info , "Magnetic Field")

            ###########Black Box#############
            yield self.ips.set_control(3)
            yield self.ips.set_comm_protocol(6)
            yield self.ips.set_control(2)
            
            yield self.sleep(0.25)
            
            yield self.ips.set_control(3)
            yield self.ips.set_fieldsweep_rate(self.FourTerminalMagneticFieldSetting_FieldSweepSpeed)
            yield self.ips.set_control(2)
            ###########Black Box#############
            
            for i in range(0,self.FourTerminalMagneticFieldSetting_Numberofsteps):
                t0 = time.time() #?????
                yield self.ips.set_control(3) #
                yield self.ips.set_targetfield(self.MagneticFieldSweepPoints[i])#
                yield self.ips.set_control(2)#
                #
                yield self.ips.set_control(3)#
                yield self.ips.set_activity(1)#
                yield self.ips.set_control(2)#
                
                print 'Setting field to ' + str(self.MagneticFieldSweepPoints[i])
                while True:
                    yield self.ips.set_control(3)#
                    curr_field = yield self.ips.read_parameter(7)#
                    yield self.ips.set_control(2)#
                    if float(curr_field[1:]) <= self.MagneticFieldSweepPoints[i]+0.00001 and float(curr_field[1:]) >= self.MagneticFieldSweepPoints[i]-0.00001:#
                        break
                    if time.time() - t0 > 1:#
                        yield self.ips.set_control(3)#
                        yield self.ips.set_targetfield(self.MagneticFieldSweepPoints[i])#
                        yield self.ips.set_control(2)#
                        
                        yield self.ips.set_control(3)#
                        yield self.ips.set_activity(1)#
                        yield self.ips.set_control(2)#
                        t0 = time.time()#
                        print 'restarting loop'#
                    yield self.sleep(0.25)#

                print 'Starting sweep with magnetic field set to: ' + str(self.MagneticFieldSweepPoints[i])

                yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.currentDAC_Output[self.FourTerminal_ChannelOutput[0]],self.FourTerminal_MinVoltage,10000,100)    #ramp to initial value

                yield self.sleep(1)

                FourTerminalXaxis=np.linspace(self.FourTerminal_MinVoltage,self.FourTerminal_MaxVoltage,self.FourTerminal_Numberofstep)  #generating list of voltage at which sweeped
                dac_read= yield self.Buffer_Ramp_Display(self.FourTerminal_ChannelOutput,self.FourTerminal_ChannelInput,[self.FourTerminal_MinVoltage],[self.FourTerminal_MaxVoltage],self.FourTerminal_Numberofstep,self.FourTerminal_Delay) #dac_read[0] is voltage,dac_read[1] is current potentially

                formatted_data = []
                for j in range(0, self.FourTerminal_Numberofstep):
                    DummyVoltage=float(dac_read[0][j])/10.0*self.MultiplierVoltage
                    formatted_data.append((i , j , self.MagneticFieldSweepPoints[i], FourTerminalXaxis[j],DummyVoltage))
                    if self.FourTerminal_Input2!=4:  #add additional data if Input2 is not None
                        DummyCurrent=float(dac_read[1][j])/10.0*self.MultiplierCurrent
                        formatted_data[j]+=(DummyCurrent,)
                        resistance=float(DummyVoltage/DummyCurrent) #generating resisitance
                        formatted_data[j]+=(resistance,)  #proccessing to Resistance

                yield self.dv.add(formatted_data)
                yield self.plotFourTerminal_Data1(formatted_data)

                yield self.Ramp1_Display(self.FourTerminal_ChannelOutput[0],self.FourTerminal_MaxVoltage,0.0,10000,100)

                if self.FourTerminal_Input2!=4:
                     yield self.plotFourTerminal_Data2(formatted_data)
                     yield self.plotFourTerminal_Data3(formatted_data)
        except Exception as inst:
            print inst

        self.unlockInterface()
        yield self.sleep(0.25)
        self.saveDataToSessionFolder() #save the screenshot
        
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
                newData = yield self.dac.buffer_ramp(out_list,in_list,[startx],[stopx], self.numberfastdata, self.FourTerminal_Delay)

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
                self.SetpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT1.setText(formatNum(self.SetpointDAC_Output[ChannelPort],6))
        if ChannelPort==1:
            dummystr=str(self.lineEdit_CentralDAC_DACOUTPUT2.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
                self.SetpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT2.setText(formatNum(self.SetpointDAC_Output[ChannelPort],6))
        if ChannelPort==2:
            dummystr=str(self.lineEdit_CentralDAC_DACOUTPUT3.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
                self.SetpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT3.setText(formatNum(self.SetpointDAC_Output[ChannelPort],6))
        if ChannelPort==3:
            dummystr=str(self.lineEdit_CentralDAC_DACOUTPUT4.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float) and dummyval<=10.0 and dummyval >=-10.0:
                self.SetpointDAC_Output[ChannelPort]=dummyval
            self.lineEdit_CentralDAC_DACOUTPUT4.setText(formatNum(self.SetpointDAC_Output[ChannelPort],6))

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
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            self.FourTerminal_Delay=int(dummyval)
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

    def ChangeVoltage_LI_Sensitivity_1stdigit(self):
        self.Voltage_LI_Multiplier1=int(self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentText())
        self.UpdateMultiplier()

    def ChangeVoltage_LI_Sensitivity_2nddigit(self):
        self.Voltage_LI_Multiplier2=int(self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentText())
        self.UpdateMultiplier()

    def ChangeVoltage_LI_Sensitivity_Unit(self):
        self.Voltage_LI_Multiplier3=float(self.Dict_LockIn[str(self.comboBox_Voltage_LI_Sensitivity_Unit.currentText())])
        self.UpdateMultiplier()

    def ChangeVoltage_LI_Expand(self):
        self.Voltage_LI_Multiplier4=float(self.comboBox_Voltage_LI_Expand.currentText())
        self.UpdateMultiplier()

    def ChangeCurrent_LI_Sensitivity_1stdigit(self):
        self.Current_LI_Multiplier1=int(self.comboBox_Current_LI_Sensitivity_1stdigit.currentText())
        self.UpdateMultiplier()

    def ChangeCurrent_LI_Sensitivity_2nddigit(self):
        self.Current_LI_Multiplier2=int(self.comboBox_Current_LI_Sensitivity_2nddigit.currentText())
        self.UpdateMultiplier()

    def ChangeCurrent_LI_Sensitivity_Unit(self):
        self.Current_LI_Multiplier3=float(self.Dict_LockIn[str(self.comboBox_Current_LI_Sensitivity_Unit.currentText())])
        self.UpdateMultiplier()

    def ChangeCurrent_LI_Expand(self):
        self.Current_LI_Multiplier4=float(self.comboBox_Current_LI_Expand.currentText())
        self.UpdateMultiplier()

    def UpdateMultiplier(self):  #function that defines the Lock-in Setting
        self.MultiplierVoltage=self.Voltage_LI_Multiplier1*self.Voltage_LI_Multiplier2*self.Voltage_LI_Multiplier3*self.Voltage_LI_Multiplier4
        self.MultiplierCurrent=self.Current_LI_Multiplier1*self.Current_LI_Multiplier2*self.Current_LI_Multiplier3*self.Current_LI_Multiplier4

        ##########################Update All the parameters#################

##########################Peculiar Function only defined in SampleCharacterizer#############
    @inlineCallbacks
    def Ramp1_Display(self,SweepPort,Startingpoint,Endpoint,Numberofsteps,Delay,c=None): #this is a function that morph ramp1 and add codes for controlling the display
        try:
            yield self.ClearBufferedData()

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
            self.ClearBufferedData()
            self.UpdateDAC_Current_Label(ChannelOutput[0],'Sweeping')
            data= yield self.dac.buffer_ramp(ChannelOutput,ChannelInput,Min,Max,Numberofsteps,Delay)
            self.UpdateDAC_Current_Label(ChannelOutput[0],Max)
            self.ClearBufferedData()
            returnValue(data)
        except Exception as inst:
            print inst

    @inlineCallbacks
    def ClearBufferedData(self): #necessary for long ramp(ramp function does not read all the data)
        yield self.sleep(0.1)
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
            yield self.Ramp1_Display(ChannelPort,self.currentDAC_Output[ChannelPort],self.SetpointDAC_Output[ChannelPort],10000,100)
        except Exception as inst:
            print inst

    def SetupFourTerminalSweepSetting(self,Status):
        self.FourTerminal_ChannelOutput=[]
        self.FourTerminal_ChannelOutput.append(self.FourTerminal_Output1)#setup for bufferramp function

        self.FourTerminal_ChannelInput=[]
        self.FourTerminal_ChannelInput.append(self.FourTerminal_Input1)#setup for bufferramp function

        if self.FourTerminal_Input2!=4:
            self.FourTerminal_ChannelInput.append(self.FourTerminal_Input2)# Create the list of Channel that we read while sweep #setup for bufferramp function

        self.datavaultXaxis=[]
        if Status == "Magnetic Field":
            self.datavaultXaxis.append('Magnetic Field index')# This part is for setting correct datavault input
        self.datavaultXaxis.append(self.FourTerminal_NameOutput1+' index')
        if Status == "Magnetic Field":
            self.datavaultXaxis.append('Magnetic Field')
        self.datavaultXaxis.append(self.FourTerminal_NameOutput1)
        
        self.datavaultYaxis=[]
        self.datavaultYaxis.append(self.FourTerminal_NameInput1)
        if self.FourTerminal_Input2!=4:  #add additional data if Input2 is not None
            self.datavaultYaxis.append(self.FourTerminal_NameInput2)#Yaxis is misnamed for independent variables
            self.datavaultYaxis.append("Resistance")#replace name one day
#change for resistance later                self.datavaultYaxis.append(self.FourTerminal_NameInput3)
        
    def SetupFourTerminalDataVault(self,file,Status):

        self.dvFileName = file[1] # read the name
        self.lineEdit_ImageNumber.setText(file[1][0:5])
        session  = ''
        for folder in file[0][1:]:
            session = session + '\\' + folder
        self.lineEdit_ImageDir.setText(r'\.datavault' + session)

##########################Peculiar Function only defined in SampleCharacterizer#############
        
        
##########################              Plot Related functions                 #############
    def plotFourTerminal_Data1(self, data):
        self.data = data
        xVals = [x[1] for x in self.data]
        yVals = [x[2] for x in self.data]
        self.sweepFourTerminal_Plot1.plot(x = xVals, y = yVals, pen = 0.5)


    def plotFourTerminal_Data2(self, data):
        self.data = data
        xVals = [x[1] for x in self.data]
        yVals = [x[3] for x in self.data]
        self.sweepFourTerminal_Plot2.plot(x = xVals, y = yVals, pen = 0.5)

    def plotFourTerminal_Data3(self, data):
        self.data = data
        xVals = [x[1] for x in self.data]
        yVals = [x[4] for x in self.data]
        self.sweepFourTerminal_Plot3.plot(x = xVals, y = yVals, pen = 0.5)
        
    def setupAdditionalUi(self):
        self.setupFourTerminalPlot()
        self.setupFourTerminalMagneticFieldResistancePlot()
        self.setupFourTerminalMagneticFieldVoltagePlot()
        self.setupFourTerminalMagneticFieldCurrentPlot()

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

    def setupFourTerminalMagneticFieldResistancePlot(self):
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

        self.FourTerminalMagneticField_Resistance_VersusField_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Resistance_VersusField)
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.setLabel('left', 'Resistance', units = 'Ohm')
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.showAxis('right', show = True)
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.showAxis('top', show = True)
        
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Resistance_VersusGateVoltage)
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.setLabel('left', 'Resistance', units = 'Ohm')
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.showAxis('right', show = True)
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.showAxis('top', show = True)
        
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
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.showAxis('right', show = True)
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.showAxis('top', show = True)
        
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Voltage_VersusGateVoltage)
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.showAxis('right', show = True)
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.showAxis('top', show = True)
        
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

        self.FourTerminalMagneticField_Current_VersusField_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Current_VersusField)
        self.FourTerminalMagneticField_Current_VersusField_Plot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.FourTerminalMagneticField_Current_VersusField_Plot.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusField_Plot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.FourTerminalMagneticField_Current_VersusField_Plot.showAxis('right', show = True)
        self.FourTerminalMagneticField_Current_VersusField_Plot.showAxis('top', show = True)
        
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot = pg.PlotWidget(parent = self.Frame_FourTerminalMagneticField_Current_VersusGateVoltage)
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.showAxis('right', show = True)
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.showAxis('top', show = True)
        
    def updateFourTerminalPlotLabel(self):
        self.sweepFourTerminal_Plot1.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.sweepFourTerminal_Plot1.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot2.setLabel('left', self.FourTerminal_NameInput2, units = 'V')
        self.sweepFourTerminal_Plot2.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.sweepFourTerminal_Plot3.setLabel('left', 'Resistance', units = 'V')
        self.sweepFourTerminal_Plot3.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Resistance_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Voltage_Plot.setTitle(self.FourTerminal_NameInput1)
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput1, units = 'V')
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        self.view_sweepFourTerminalMagneticField_Current_Plot.setTitle(self.FourTerminal_NameInput2)
        self.view_sweepFourTerminalMagneticField_Current_Plot.setLabel('left', text=self.FourTerminal_NameOutput1, units = 'V')
        self.FourTerminalMagneticField_Current_VersusField_Plot.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setLabel('left', self.FourTerminal_NameInput2, units = 'A')
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.setLabel('bottom', self.FourTerminal_NameOutput1, units = 'V')
        
    def ClearFourTerminalPlot(self):
        self.sweepFourTerminal_Plot1.clear()
        self.sweepFourTerminal_Plot2.clear()
        self.sweepFourTerminal_Plot3.clear()

    def ClearFourTerminalMagneticFieldPlot(self):
        self.sweepFourTerminalMagneticField_Resistance_Plot.clear()
        self.FourTerminalMagneticField_Resistance_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Resistance_VersusGateVoltage_Plot.clear()
        self.sweepFourTerminalMagneticField_Voltage_Plot.clear()
        self.FourTerminalMagneticField_Voltage_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Voltage_VersusGateVoltage_Plot.clear()
        self.sweepFourTerminalMagneticField_Current_Plot.clear()
        self.FourTerminalMagneticField_Current_VersusField_Plot.clear()
        self.FourTerminalMagneticField_Current_VersusGateVoltage_Plot.clear()

            
##########################              Plot Related functions                 #############


    def updateHistogramLevels(self, hist):
        mn, mx = hist.getLevels()
        self.Plot2D.ui.histogram.setLevels(mn, mx)
        #self.autoLevels = False

    def setSessionFolder(self, folder):
        self.sessionFolder = folder

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
        self.pushButton_StartFourTerminalSweep.setEnabled(True)

        self.lineEdit_CentralDAC_DACOUTPUT1.setEnabled(True)
        self.lineEdit_CentralDAC_DACOUTPUT2.setEnabled(True)
        self.lineEdit_CentralDAC_DACOUTPUT3.setEnabled(True)
        self.lineEdit_CentralDAC_DACOUTPUT4.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT1.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT2.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT3.setEnabled(True)
        self.pushButton_CentralDAC_DACOUTPUT4.setEnabled(True)

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
