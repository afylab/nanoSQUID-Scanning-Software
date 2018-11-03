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
import copy
from scipy.signal import detrend
#importing a bunch of stuff


################################################################################################################################
#Test everything is still working, test currentindex



path = sys.path[0] + r"\SampleCharacterizer"
SampleCharacterizerWindowUI, QtBaseClass = uic.loadUiType(path + r"\SampleCharacterizerWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way.
sys.path.append(sys.path[0]+'\Resources')
#from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView                #this part not sure, it was throwing an error


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

        self.setupPreliminaryPlot()

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


        self.DAC_Channel= {
         'DAC 1':0,
         'DAC 2':1,
         'DAC 3':2,
         'DAC 4':3,
         'ADC 1':0,# Defining Channel to Number
         'ADC 2':1,
         'ADC 3':2,
         'ADC 4':3,
         }

        self.inputs = {
                'Input 1'                : 1,
                }
        self.outputs = {
                'Output 1'               : 1,          #dictionary not yet used
                'Output 2'               : 2,
        }

        self.randomFill = -0.987654321
        self.numberfastdata=100
        self.numberslowdata=100
        self.lineTime = 64e-3
        #do not know what it means

        self.Preliminary_ChannelInput=[]
        self.Preliminary_ChannelOutput=[]
        self.Preliminary_MinVoltage=float(-1)
        self.Preliminary_MaxVoltage=float(1)
        self.Preliminary_Numberofstep=int(100)
        self.Preliminary_Delay=int(10)
        self.Lineedit_Preliminary_MinVoltage.setText(str(self.Preliminary_MinVoltage))
        self.Lineedit_Preliminary_MaxVoltage.setText(str(self.Preliminary_MaxVoltage))
        self.Lineedit_Preliminary_Numberofstep.setText(str(self.Preliminary_Numberofstep))
        self.Lineedit_Preliminary_Delay.setText(str(self.Preliminary_Delay))

        #preliminary sweep basic parameter

        self.MainMagneticFieldSetting_MinimumField=float(0)
        self.MainMagneticFieldSetting_MaximumField=float(0)
        self.MainMagneticFieldSetting_NumberofstepsandMilifieldperTesla=int(1000)
        self.MainMagneticFieldSetting_FieldSweepSpeed=int(10)

        #Magnetic field sweep basic parameter

        self.comboBox_Preliminary_Output1.setCurrentIndex(0)
        self.comboBox_Preliminary_Input1.setCurrentIndex(0)
        self.comboBox_Preliminary_Input2.setCurrentIndex(1)
        self.comboBox_Preliminary_Input3.setCurrentIndex(4)
        self.Preliminary_Output1=self.comboBox_Preliminary_Output1.currentIndex()
        self.Preliminary_Input1=self.comboBox_Preliminary_Input1.currentIndex()
        self.Preliminary_Input2=self.comboBox_Preliminary_Input2.currentIndex()
        self.Preliminary_Input3=self.comboBox_Preliminary_Input3.currentIndex()


#        self.setupAdditionalUi()    #throwing an error

        self.moveDefault()

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)

#######################################
        self.PushButton_StartSweep.clicked.connect(self.Sweep)
        self.pushButton_DummyConnect.clicked.connect(self.connectLabRAD)
#######################################

#######################################
        self.Lineedit_Preliminary_MinVoltage.editingFinished.connect(self.UpdatePreliminary_MinVoltage)
        self.Lineedit_Preliminary_MaxVoltage.editingFinished.connect(self.UpdatePreliminary_MaxVoltage)
        self.Lineedit_Preliminary_Numberofstep.editingFinished.connect(self.UpdatePreliminary_Numberofstep)
        self.Lineedit_Preliminary_Delay.editingFinished.connect(self.UpdatePreliminary_Delay)
        self.Lineedit_MainMagneticFieldSetting_MinimumField.editingFinished.connect(self.UpdateMainMagneticFieldSetting_MinimumField)
        self.Lineedit_MainMagneticFieldSetting_MaximumField.editingFinished.connect(self.UpdateMainMagneticFieldSetting_MaximumField)
        self.Lineedit_MainMagneticFieldSetting_NumberofstepsandMilifieldperTesla.editingFinished.connect(self.UpdateMainMagneticFieldSetting_NumberofstepsandMilifieldperTesla)
        self.Lineedit_MainMagneticFieldSetting_FieldSweepSpeed.editingFinished.connect(self.UpdateMainMagneticFieldSetting_FieldSweepSpeed)
#######################################

        # self.Lineedit_Channel.editingFinished.connect(self.UpdateChannel)

#######################################
        self.comboBox_Preliminary_Output1.currentIndexChanged.connect(self.ChangePreliminary_Output1_Channel)
        self.comboBox_Preliminary_Input1.currentIndexChanged.connect(self.ChangePreliminary_Input1_Channel)
        self.comboBox_Preliminary_Input2.currentIndexChanged.connect(self.ChangePreliminary_Input2_Channel)
        self.comboBox_Preliminary_Input3.currentIndexChanged.connect(self.ChangePreliminary_Input3_Channel)
#######################################

#######################################
        self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentIndexChanged.connect(self.ChangeVoltage_LI_Sensitivity_1stdigit)
        self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentIndexChanged.connect(self.ChangeVoltage_LI_Sensitivity_2nddigit)
        self.comboBox_Voltage_LI_Sensitivity_Unit.currentIndexChanged.connect(self.ChangeVoltage_LI_Sensitivity_Unit)
        self.comboBox_Voltage_LI_Expand.currentIndexChanged.connect(self.ChangeVoltage_LI_Expand)

#######################################
        self.PushButton_done.clicked.connect(self.dummy)

        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None




        #self.lockInterface()


    def setupPreliminaryPlot(self):
        self.sweepPreliminary_Plot1 = pg.PlotWidget(parent = self.PreliminaryPlot1)
        self.sweepPreliminary_Plot1.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepPreliminary_Plot1.setLabel('left', 'DC Feedback Voltage', units = 'V')
        self.sweepPreliminary_Plot1.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.sweepPreliminary_Plot1.showAxis('right', show = True)
        self.sweepPreliminary_Plot1.showAxis('top', show = True)
        self.sweepPreliminary_Plot1.setXRange(0,1)
        self.sweepPreliminary_Plot1.setYRange(0,2)
        self.sweepPreliminary_Plot1.enableAutoRange(enable = True)

        self.sweepPreliminary_Plot2 = pg.PlotWidget(parent = self.PreliminaryPlot2)
        self.sweepPreliminary_Plot2.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepPreliminary_Plot2.setLabel('left', 'DC Feedback Voltage', units = 'V')
        self.sweepPreliminary_Plot2.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.sweepPreliminary_Plot2.showAxis('right', show = True)
        self.sweepPreliminary_Plot2.showAxis('top', show = True)
        self.sweepPreliminary_Plot2.setXRange(0,1)
        self.sweepPreliminary_Plot2.setYRange(0,2)
        self.sweepPreliminary_Plot2.enableAutoRange(enable = True)

        self.sweepPreliminary_Plot3 = pg.PlotWidget(parent = self.PreliminaryPlot3)
        self.sweepPreliminary_Plot3.setGeometry(QtCore.QRect(0, 0, 400, 200))
        self.sweepPreliminary_Plot3.setLabel('left', 'DC Feedback Voltage', units = 'V')
        self.sweepPreliminary_Plot3.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.sweepPreliminary_Plot3.showAxis('right', show = True)
        self.sweepPreliminary_Plot3.showAxis('top', show = True)
        self.sweepPreliminary_Plot3.setXRange(0,1)
        self.sweepPreliminary_Plot3.setYRange(0,2)
        self.sweepPreliminary_Plot3.enableAutoRange(enable = True)


    def moveDefault(self):
        self.move(550,10)

    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            from labrad.wrappers import connectAsync
            self.cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn.data_vault
            self.dac = yield self.cxn.dac_adc
            yield self.dac.select_device(0L)

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

        self.lockInterface()

        self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")






    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()

    def updateDataVaultDirectory(self):
        curr_folder = yield self.gen_dv.cd()
        yield self.dv.cd(curr_folder)


    # def setupAdditionalUi(self):
        # #Set up UI that isn't easily done from Qt Designer
        # self.view = pg.PlotItem(title="Plot")
# #        self.view.setLabel('left',text='Y position',units = 'm')
# #        self.view.setLabel('right',text='Y position',units = 'm')
# #        self.view.setLabel('top',text='X position',units = 'm')
# #        self.view.setLabel('bottom',text='X position',units = 'm')
        # self.Plot2D = ScanImageView(parent = self.centralwidget, view = self.view, randFill = self.randomFill)
        # self.view.invertY(False)
        # self.view.setAspectLocked(self.aspectLocked)
        # self.Plot2D.ui.roiBtn.hide()
        # self.Plot2D.ui.menuBtn.hide()
        # self.Plot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        # self.Plot2D.lower()
        # self.PlotArea.close()
        # self.horizontalLayout.addWidget(self.Plot2D)

    def updateHistogramLevels(self, hist):
        mn, mx = hist.getLevels()
        self.Plot2D.ui.histogram.setLevels(mn, mx)

    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous
    # delay that allows other labrad / pyqt methods to run



    @inlineCallbacks
    def Sweep(self,c=None):
        try:
            self.sweepPreliminary_Plot1.clear()
            self.sweepPreliminary_Plot2.clear()
            self.sweepPreliminary_Plot3.clear()

            self.Preliminary_ChannelOutput=[]
            self.Preliminary_ChannelOutput.append(self.Preliminary_Output1)

            self.Preliminary_ChannelInput=[]
            self.Preliminary_ChannelInput.append(self.Preliminary_Input1)
            self.Preliminary_ChannelInput.append(self.Preliminary_Input2)
            if self.Preliminary_Input3!=4:
                self.Preliminary_ChannelInput.append(self.Preliminary_Input3)# Create the list of Channel that we read while sweep

            yield self.sleep(0.1)
            a = yield self.dac.read()
            while a != '':
                print a
                a = yield self.dac.read()

            file_info = yield self.dv.new("Experimenting with SampleCharacterizer", ['Voltage'],['Reading'])
            self.dvFileName = file_info[1]
            # self.lineEdit_ImageNum.setText(file_info[1][0:5])
            session  = ''
            for folder in file_info[0][1:]:
                session = session + '\\' + folder
        # self.lineEdit_ImageDir.setText(r'\.datavault' + session)

            yield self.dac.ramp1(self.Preliminary_ChannelOutput[0],0.0,self.Preliminary_MinVoltage,10000,100)    #ramp to initial value

            yield self.sleep(0.1)
            a = yield self.dac.read()
            while a != '':
                print a
                a = yield self.dac.read()

            yield self.sleep(1)

            dac_read= yield self.dac.buffer_ramp(self.Preliminary_ChannelOutput,self.Preliminary_ChannelInput,[self.Preliminary_MinVoltage],[self.Preliminary_MaxVoltage],self.Preliminary_Numberofstep,self.Preliminary_Delay)

            yield self.sleep(0.1)
            a = yield self.dac.read()
            while a != '':
                print a
                a = yield self.dac.read()
                
            yield self.sleep(1)

            formatted_data = []
            for j in range(0, self.Preliminary_Numberofstep):
                formatted_data.append((j, dac_read[0][j], dac_read[1][j]))
                if self.Preliminary_Input3!=4:  #add additional data if Input2 is not None
                    formatted_data[j]+=(dac_read[2][j])
                    resistance=dac_read[1]/dac_read[2]
                    formatted_data[j]+=(resistance)  #proccessing to Resistance
#            yield self.dv.add(formatted_data)
            yield self.plotPreliminary_Data1(formatted_data)


            yield self.dac.ramp1(self.Preliminary_ChannelOutput[0],self.Preliminary_MaxVoltage,0.0,10000,100)

            print "done"
            if self.Preliminary_Input3!=4:
                 yield self.plotPreliminary_Data2(formatted_data)
                 yield self.plotPreliminary_Data3(formatted_data)
        except Exception as inst:
            print inst

    def dummy(self):
        print self.Preliminary_MinVoltage
        self.dac.set_voltage(self.Preliminary_ChannelOutput,0)
        print "done2"

    def plotPreliminary_Data1(self, data):
        self.data = data
        xVals = [x[1] for x in self.data]
        yVals = [x[2] for x in self.data]
        print xVals
        print yVals
        self.sweepPreliminary_Plot1.plot(x = xVals, y = yVals, pen = 0.5)


    def plotPreliminary_Data2(self, data):
        try:
            self.data = data
            xVals = [x[1] for x in self.data]
            yVals = [x[3] for x in self.data]
            yield self.sweepPreliminary_Plot2.plot(x = xVals, y = yVals, pen = 0.5)
        except Exception as inst:
            print inst

    def plotPreliminary_Data3(self, data):
        self.data = data
        xVals = [x[1] for x in self.data]
        yVals = [x[4] for x in self.data]
        # try:
        self.sweepPreliminary_Plot3.plot(x = xVals, y = yVals, pen = 0.5)

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


            a = yield self.dac.read()
            while a != '':
                print a
                a = yield self.dac.read()

            startfast = self.startOutput1

            for i in range(0,self,numberslowdata):
                startslow = self.startOutput2
                stopfast = self.stopOutput1
                out_list = [self.outputs['Output 1']-1]
                in_list = [self.inputs['Input 1']-1]
                newData = yield self.dac.buffer_ramp(out_list,in_list,[startx],[stopx], self.numberfastdata, self.Preliminary_Delay)

            for j in range(0, self.pixels):
                #Putting in 0 for SSAA voltage (last entry) because not yet being used/read
                formated_data.append((1, j, i, x_voltage[::-1][j], y_voltage[::-1][j], self.data_retrace[0][j,i], self.data_retrace[1][j,i], self.data_retrace[2][j,i]))
                yield self.dv.add(formated_data)
        except:
            print "This is an error message!"


##########################Update All the parameters#################
    def UpdatePreliminary_MinVoltage(self):
        self.Preliminary_MinVoltage=float(str(self.Lineedit_Preliminary_MinVoltage.text()))

    def UpdatePreliminary_MaxVoltage(self):
        self.Preliminary_MaxVoltage=float(str(self.Lineedit_Preliminary_MaxVoltage.text()))

    def UpdatePreliminary_Numberofstep(self):
        self.Preliminary_Numberofstep=int(str(self.Lineedit_Preliminary_Numberofstep.text()))

    def UpdatePreliminary_Delay(self):
        self.Preliminary_Delay=int(str(self.Lineedit_Preliminary_Delay.text()))

    def UpdateMainMagneticFieldSetting_MinimumField(self):
        self.MainMagneticFieldSetting_MinimumField=float(str(self.Lineedit_MainMagneticFieldSetting_MinimumField.text()))

    def UpdateMainMagneticFieldSetting_MaximumField(self):
        self.MainMagneticFieldSetting_MaximumField=float(str(self.Lineedit_MainMagneticFieldSetting_MaximumField.text()))

    def UpdateMainMagneticFieldSetting_NumberofstepsandMilifieldperTesla(self):
        self.MainMagneticFieldSetting_NumberofstepsandMilifieldperTesla=int(str(self.Lineedit_MainMagneticFieldSetting_NumberofstepsandMilifieldperTesla.text()))

    def UpdateMainMagneticFieldSetting_FieldSweepSpeed(self):
        self.MainMagneticFieldSetting_FieldSweepSpeed=int(str(self.Lineedit_MainMagneticFieldSetting_FieldSweepSpeed.text()))

    def ChangePreliminary_Output1_Channel(self):
        self.Preliminary_Output1=self.comboBox_Preliminary_Output1.currentIndex()

    def ChangePreliminary_Input1_Channel(self):
        self.Preliminary_Input1=self.comboBox_Preliminary_Input1.currentIndex()

    def ChangePreliminary_Input2_Channel(self):
        self.Preliminary_Input2=self.comboBox_Preliminary_Input2.currentIndex()

    def ChangePreliminary_Input3_Channel(self):
        self.Preliminary_Input3=self.comboBox_Preliminary_Input3.currentIndex()

    def ChangeVoltage_LI_Sensitivity_1stdigit(self):
        self.Voltage_LI_Multiplier1=int(self.comboBox_Voltage_LI_Sensitivity_1stdigit.currentText())

    def ChangeVoltage_LI_Sensitivity_2nddigit(self):
        self.Voltage_LI_Multiplier2=int(self.comboBox_Voltage_LI_Sensitivity_2nddigit.currentText())

    def ChangeVoltage_LI_Sensitivity_Unit(self):
        self.Voltage_LI_Multiplier3=int(Dict_LockIn(str(self.comboBox_Voltage_LI_Sensitivity_Unit.currentText())))

    def ChangeVoltage_LI_Expand(self):
        self.Voltage_LI_Multiplier4=int(self.comboBox_Voltage_LI_Expand.currentText())



        ##########################Update All the parameters#################


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
        self.comboBox_Input1.setEnabled(False)
        self.comboBox_Output1.setEnabled(False)
        self.comboBox_Output2.setEnabled(False)

    def unlockInterface(self):
        self.comboBox_Input1.setEnabled(True)
        self.comboBox_Output1.setEnabled(True)
        self.comboBox_Output2.setEnabled(True)

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
