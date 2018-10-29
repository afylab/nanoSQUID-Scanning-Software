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


path = sys.path[0] + r"\DeviceCharacterizer"
DeviceCharacterizerWindowUI, QtBaseClass = uic.loadUiType(path + r"\DeviceCharacterizerWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way. 
sys.path.append(sys.path[0]+'\Resources')
#from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView                #this part not sure, it was throwing an error


class Window(QtGui.QMainWindow, DeviceCharacterizerWindowUI):
    
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
        
        self.setupPlot()
        
        self.inputs = {
                'Input 1'                : 1,         # 1 Indexed DAC input into which the voltage corresponding to the Z atto motion 
                }
                
        self.outputs = {
                'Output 1'               : 1,         # 1 indexed DAC output that goes to constant gain on Z 
                'Output 2'               : 2,         # 1 indexed DAC output that goes to constant gain on Z 

        }
        
        self.randomFill = -0.987654321
        self.numberfastdata=100
        self.numberslowdata=100
        self.lineTime = 64e-3



        self.SweepChannel=int(0)
        self.MinVoltage=float(-1)
        self.MaxVoltage=float(1)
        self.Numberofstep=int(1000)
        self.Delay=int(10)

#        self.setupAdditionalUi()

        self.moveDefault()

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
#######################################
        self.comboBox_Input1.currentIndexChanged.connect(self.setInput1)
        self.comboBox_Output1.currentIndexChanged.connect(self.setOutput1)
        self.comboBox_Output2.currentIndexChanged.connect(self.setOutput2)
        self.PushButton_StartSweep.clicked.connect(self.Sweep)
#######################################

#######################################
        self.Lineedit_MinVoltage.editingFinished.connect(self.UpdateMinVoltage)
        self.Lineedit_MaxVoltage.editingFinished.connect(self.UpdateMaxVoltage)
        self.Lineedit_Numberofstep.editingFinished.connect(self.UpdateNumberofstep)
        self.Lineedit_Delay.editingFinished.connect(self.UpdateDelay)
#######################################
        # self.Lineedit_Channel.editingFinished.connect(self.UpdateChannel)


        self.PushButton_done.clicked.connect(self.dummy)

        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None
        


        
        #self.lockInterface()

        
    def setupPlot(self):
        self.sweepPlot = pg.PlotWidget(parent = self.PreliminaryPlot)
        self.sweepPlot.setGeometry(QtCore.QRect(0, 0, 435, 290))
        self.sweepPlot.setLabel('left', 'DC Feedback Voltage', units = 'V')
        self.sweepPlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.sweepPlot.showAxis('right', show = True)
        self.sweepPlot.showAxis('top', show = True)
        self.sweepPlot.setXRange(0,1)
        self.sweepPlot.setYRange(0,2)
        self.sweepPlot.enableAutoRange(enable = True)
        
        
        
        
    def moveDefault(self):
        self.move(550,10)
        
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.dac = dict['dac_adc']
            #Create another connection for the connection to data vault to prevent 
            #problems of multiple windows trying to write the data vault at the same
            #time
            self.gen_dv = dict['dv']
            from labrad.wrappers import connectAsync
            self.cxn_dv = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn_dv.data_vault
            curr_folder = yield self.gen_dv.cd()
            yield self.dv.cd(curr_folder)
            self.dcbox = dict['dc_box']
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
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
        elif not self.dcbox:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
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

    def setInput1(self):
        self.inputs['Input 1'] = self.comboBox_Input1.currentIndex()+1
        print self.inputs
        
    def setOutput1(self):
        self.outputs['Output 1'] = self.comboBox_Output1.currentIndex()+1
        print self.outputs
        
    def setOutput2(self):
        self.outputs['Output 2'] = self.comboBox_Output2.currentIndex()+1
        print self.outputs


    @inlineCallbacks
    def Sweep(self,c=None):
        yield self.sleep(0.1)
        a = yield self.dac.read()
        while a != '':
            print a
            a = yield self.dac.read()

        file_info = yield self.dv.new("Experimenting with DeviceCharacterizer", ['Voltage'],['Reading'])
        self.dvFileName = file_info[1]
        # self.lineEdit_ImageNum.setText(file_info[1][0:5])
        session  = ''
        for folder in file_info[0][1:]:
            session = session + '\\' + folder
        # self.lineEdit_ImageDir.setText(r'\.datavault' + session)
            

        
        # except Exception as inst:
            # print inst
        self.dac.ramp1(self.SweepChannel,0,self.MinVoltage,10000,100)    #ramp to initial value
        print self.SweepChannel
        print self.MinVoltage
        print self.MaxVoltage
        print self.Numberofstep
        print self.Delay

        dac_read= yield self.dac.buffer_ramp([self.SweepChannel],[0,1],[self.MinVoltage],[self.MaxVoltage],self.Numberofstep,self.Delay)
        
        formatted_data = []
        for j in range(0, self.Numberofstep):
            formatted_data.append((j, dac_read[0][j], dac_read[1][j]))
        yield self.dv.add(formatted_data)
        
        
        print self.SweepChannel
        print self.MaxVoltage
        self.dac.ramp1(self.SweepChannel,self.MaxVoltage,0.0,10000,100)
        
        print "done"
        self.plotSweepData(formatted_data)

    def dummy(self):
        print self.MinVoltage
        self.dac.set_voltage(self.SweepChannel,0)
        print "done2"

    def plotSweepData(self, data):
        self.data = data
        xVals = [x[1] for x in self.data]
        print xVals
        yVals = [x[2] for x in self.data]
        print yVals
        # try:
        self.sweepPlot.plot(x = xVals, y = yVals, pen = 0.5)
            
        # except Exception as inst:
            # print inst

        
        
    @inlineCallbacks
    def update_data(self):
        try:
            #Create data vault file with appropriate parameters
            #Retrace index is 0 for trace, 1 for retrace
            file_info = yield self.dv.new("Device Charactorizing Data " + self.fileName, ['Retrace Index','X Pos. Index','Y Pos. Index','X Pos. Voltage', 'Y Pos. Voltage'],['Z Position',self.inputs['Input 1 name'], self.inputs['Input 2 name']])
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
                newData = yield self.dac.buffer_ramp(out_list,in_list,[startx],[stopx], self.numberfastdata, self.delay)

            for j in range(0, self.pixels):
                #Putting in 0 for SSAA voltage (last entry) because not yet being used/read
                formated_data.append((1, j, i, x_voltage[::-1][j], y_voltage[::-1][j], self.data_retrace[0][j,i], self.data_retrace[1][j,i], self.data_retrace[2][j,i]))
                yield self.dv.add(formated_data)
        except:
            print "This is an error message!"

            
##########################Update All the parameters#################
    def UpdateMinVoltage(self):
        self.MinVoltage=float(str(self.Lineedit_MinVoltage.text()))
        print self.MinVoltage
        
    def UpdateMaxVoltage(self):
        self.MaxVoltage=float(str(self.Lineedit_MaxVoltage.text()))
        
    def UpdateNumberofstep(self):
        self.Numberofstep=int(str(self.Lineedit_Numberofstep.text()))
 
    def UpdateDelay(self):
        self.Delay=int(str(self.Lineedit_Delay.text()))
            
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
        
        