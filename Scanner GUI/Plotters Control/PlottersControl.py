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
import os

path = sys.path[0] + r"\Plotters Control"
sys.path.append(path + r'\Plotter')
sys.path.append(path + r'\Process List')
sys.path.append(path + r'\Multiplier Window')

import plotter
import ProcessWindow
import MultiplierSettings

Ui_CommandCenter, QtBaseClass = uic.loadUiType(path + r"\PlottersControl.ui")

'''
General Property of a Plotter include:
number
Data
PlotData
TraceFlag
DataType
NumberofindexVariables
file = None
directory = None
PlotParameters
file
Parameters
comments
Number_PlotData_X, Number_PlotData_Y
SweepingDirection = ''
'''
class CommandingCenter(QtGui.QMainWindow, Ui_CommandCenter):
    keyPressed = QtCore.pyqtSignal(QtCore.QEvent)

    def __init__(self, reactor, parent = None):
        super(CommandingCenter, self).__init__(parent)

        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        self.PlotterList = [] #PlotterList contains the all the Plotters
        self.ProcessList = ProcessWindow.ProcessWindow(self.reactor, self)

        #Color Code  [0]for Text, [1] for Background
        self.Color_NoData = [QtGui.QColor(131, 131, 131), QtGui.QColor(0, 0, 0)]
        self.Color_ContainData = [QtGui.QColor(0, 0, 0), QtGui.QColor(100, 100, 100)]
        self.Color_ContainPlotData = [QtGui.QColor(0, 0, 0), QtGui.QColor(155, 155, 155)]

        self.subtractMenu = QtGui.QMenu()
        subOverallAvg = QtGui.QAction( "Subtract overall average", self)
        subOverallAvg.triggered.connect(self.subtractOverallAvg)
        self.subtractMenu.addAction(subOverallAvg)
        subPlane = QtGui.QAction( "Subtract planar fit", self)
        subPlane.triggered.connect(self.subtractPlane)
        self.subtractMenu.addAction(subPlane)
        subOverallQuad = QtGui.QAction( "Subtract overall quadratic fit", self)
        subOverallQuad.triggered.connect(self.subtractOverallQuad)
        self.subtractMenu.addAction(subOverallQuad)
        subSelectedAreaAvg = QtGui.QAction( "Subtract selected area average", self)
        subSelectedAreaAvg.triggered.connect(self.subtractSelectedArea)
        self.subtractMenu.addAction(subSelectedAreaAvg)
        subXAvg = QtGui.QAction( "Subtract X average", self)
        subXAvg.triggered.connect(self.subtractXAvg)
        self.subtractMenu.addAction(subXAvg)
        subYAvg = QtGui.QAction( "Subtract Y average", self)
        subYAvg.triggered.connect(self.subtractYAvg)
        self.subtractMenu.addAction(subYAvg)
        subXLinear = QtGui.QAction( "Subtract X linear fit", self)
        subXLinear.triggered.connect(self.subtractXLinear)
        self.subtractMenu.addAction(subXLinear)
        subYLinear = QtGui.QAction( "Subtract Y linear fit", self)
        subYLinear.triggered.connect(self.subtractYLinear)
        self.subtractMenu.addAction(subYLinear)
        subXQuad = QtGui.QAction( "Subtract X quadratic fit", self)
        subXQuad.triggered.connect(self.subtractXQuad)
        self.subtractMenu.addAction(subXQuad)
        subYQuad = QtGui.QAction( "Subtract Y quadratic fit", self)
        subYQuad.triggered.connect(self.subtractYQuad)
        self.subtractMenu.addAction(subYQuad)
        self.pushButton_SubtractOveralAverage.setMenu(self.subtractMenu)

        self.listWidget_Plots.itemDoubleClicked.connect(self.AddtoProcess)
        self.pushButton_Subtract.clicked.connect(lambda: self.Process('Subtract'))
        self.pushButton_Addition.clicked.connect(lambda: self.Process('Addition'))
        self.pushButton_Product.clicked.connect(lambda: self.Process('Product'))
        self.pushButton_Division.clicked.connect(lambda: self.Process('Division'))
        self.pushButton_SetArea.clicked.connect(self.SetSelectedArea)
        self.SelectedArea_Flag = False
        self.pushButton_AddPlotter.clicked.connect(self.AddPlotter)

        #####Multiply
        self.multiplier = 1.0
        self.MultiplyWindow = MultiplierSettings.MultiplierWindow(self.reactor, self)
        self.pushButton_MultiplyAll.clicked.connect(self.MultiplyAll)

        self.pushButton_savePlot.clicked.connect(self.SaveAllPlot)
        
        
        self.keyPressed.connect(self.PressingKey)

        self.pushButton_ConnectLabrad.clicked.connect(self.connectLabRADBackup)

        self.RefreshPlotList()

#####Labrad Related Function
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.gen_dv = dict['servers']['local']['dv']
            
            from labrad.wrappers import connectAsync
            self.cxn_pc = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn_pc.data_vault
            self.pushButton_AddPlotter.setEnabled(True)
        except:
            pass

    @inlineCallbacks
    def connectLabRADBackup(self, c):
        try:
            from labrad.wrappers import connectAsync
            self.cxn_pc = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn_pc.data_vault
            self.pushButton_AddPlotter.setEnabled(True)
            self.Feedback('Data Vault Connected')
        except:
            pass

    def disconnectLabRAD(self):
        self.cxn = False
        self.cxn_dv = False
        self.gen_dv = False
        self.dv = False
        self.pushButton_AddPlotter.setEnabled(False)

#####Labrad Related Function

#####Save Matlab file Related Function
    def SaveAllPlot(self):
        fold = str(QtGui.QFileDialog.getExistingDirectory(self, directory = os.getcwd()))
        print fold
        for plotter in self.PlotterList:
            plotter.genMatFile(fold + '/' + plotter.file)
#####Save Matlab file Related Function

    def ClearListWidget(self):
        self.listWidget_Plots.clear()
        self.ProcessList.ClearListWidget()
        
    def RefreshPlotList(self):
        try:
            self.ClearListWidget()
            for plotter in self.PlotterList:
                item = QtGui.QListWidgetItem()
                number = plotter.number
                self.renderItem(item, number)
                self.listWidget_Plots.addItem(item)

            self.ProcessList.RefreshPlotList()
        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def renderItem(self, ListWidgetItem , number): #Based on the plotter.number, dress the Item property
        try:
            plotter = self.GrabPlotterFromNumber(number)
            index = self.PlotterList.index(plotter)
            Text = self.PlotterList[index].Title
            ListWidgetItem.setText(Text)
            
            if isinstance(plotter.Data, np.ndarray): #Check if it contains data
                ListWidgetItem.setTextColor(self.Color_ContainData[0])
                ListWidgetItem.setBackgroundColor(self.Color_ContainData[1])
            else:
                ListWidgetItem.setTextColor(self.Color_NoData[0])
                ListWidgetItem.setBackgroundColor(self.Color_NoData[1])
                ListWidgetItem.setToolTip('No Data Loaded')

            if isinstance(plotter.PlotData, np.ndarray) or isinstance(plotter.PlotData, list):#Check if it contains PlotData
                ListWidgetItem.setTextColor(self.Color_ContainPlotData[0])
                ListWidgetItem.setBackgroundColor(self.Color_ContainPlotData[1])
                x, y = str(plotter.Number_PlotData_X), str(plotter.Number_PlotData_Y)
                ListWidgetItem.setToolTip('X: ' + x + '; ' + 'Y: ' + y)

        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def GrabPlotterFromNumber(self, number): #return the plotter based on the plotter.number given
        for plotter in self.PlotterList:
            if number == plotter.number:
                return plotter 
        
    def MaximizePlotter(self, item):
        index = self.listWidget_Plots.indexFromItem(item).row()
        self.PlotterList[index].showMaximized()

    def AddtoProcess(self, item):
        try:
            if item.backgroundColor() == self.Color_ContainPlotData[1]:#Only Proceed with data contained
                index = self.listWidget_Plots.indexFromItem(item).row()
                number = self.PlotterList[index].number
                if  self.ProcessList.listWidget_PlotsListA.count() <= self.ProcessList.listWidget_PlotsListB.count():
                    self.ProcessList.PlotsListA.append(number)
                else:
                    self.ProcessList.PlotsListB.append(number)
            else:
                print "Only Add to Process if Data is loaded"

            self.RefreshPlotList()
            
        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno
                
    def Process(self, Process, c = None):
        if self.ProcessList.label_Operation.text() == Process: #If the operation changed, kill the current list
            pass
        else:
            self.ProcessList.ClearListWidget()
            self.ProcessList.PlotsListA, self.ProcessList.PlotsListB = [], []

        self.ProcessList.raise_()
        self.ProcessList.moveDefault()
        self.ProcessList.show()
        self.ProcessList.label_Operation.setText(Process)

    def transferPlotData(self, plotter, PlotData, comments, filename, title, PlotParameters, indVars, depVars):
        plotter.PlotData = PlotData
        plotter.comments = ['faketime','fakeuser',comments]
        plotter.file = filename
        plotter.DataType = "2DPlot Reconstitute"
        plotter.Title = title
        plotter.PlotParameters = PlotParameters
        plotter.indVars = indVars
        plotter.depVars = depVars

    def AddPlotter(self):
        try:
            ii= -1 #0 is MainPlot, so the number start with 
            while True:
                ii +=1
                if ii not in [item.number for item in self.PlotterList]: #info[0] is label of plot
                    break
            self.PlotterList.append(plotter.Plotter(self.reactor, self.dv, ii, self))
            self.PlotterList[-1].moveDefault()
            self.PlotterList[-1].show()
            self.RefreshPlotList()

        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno        

    def RemovePlotsListAItem(self, item):
        index = self.listWidget_PlotsListA.indexFromItem(item).row()
        self.PlotsListA.pop(index)
        self.RefreshPlotList()

    def RemovePlotsListBItem(self, item):
        index = self.listWidget_PlotsListB.indexFromItem(item).row()
        self.PlotsListB.pop(index)
        self.RefreshPlotList()

    def SetSelectedArea(self):
        if self.SelectedArea_Flag == False:
            self.plotter_AreaSelected = self.PlotterList[-1]
            self.Feedback('Selected Area change in ' + self.plotter_AreaSelected.Title + ' is globally applied')
            self.plotter_AreaSelected.AreaSelected.sigRegionChangeFinished.connect(lambda: self.ApplySelectedArea(self.plotter_AreaSelected))
            self.plotter_AreaSelected.raise_()
            self.SelectedArea_Flag = True
        else:
            self.Feedback('Selected Area change in ' + self.plotter_AreaSelected.Title + ' is disconnected from other plotters')
            self.plotter_AreaSelected.AreaSelected.sigRegionChangeFinished.disconnect()
            self.SelectedArea_Flag = False


    def ApplySelectedArea(self, plotterchanged,):
        AreaSelectedParameters = plotterchanged.AreaSelectedParameters
        pos = plotterchanged.AreaSelected.pos()
        size = plotterchanged.AreaSelected.size()
        for plotter in self.PlotterList:
            if plotter != plotterchanged:
                plotter.AreaSelectedParameters = AreaSelectedParameters
                plotter.AreaSelected.setSize(size)
                plotter.AreaSelected.setPos(pos)

#####Subtract Related Function
    def subtractOverallAvg(self):
        for plotter in self.PlotterList:
            plotter.subtractOverallAvg()
            
    def subtractPlane(self):
        for plotter in self.PlotterList:
            plotter.subtractPlane()        

    def subtractOverallQuad(self):
        for plotter in self.PlotterList:
            plotter.subtractOverallQuad()        
            
    def subtractXAvg(self):
        for plotter in self.PlotterList:
            plotter.subtractXAvg()     
            
    def subtractYAvg(self):
        for plotter in self.PlotterList:
            plotter.subtractYAvg()     
            
    def subtractXLinear(self):
        for plotter in self.PlotterList:
            plotter.subtractXLinear() 
            
    def subtractYLinear(self):
        for plotter in self.PlotterList:
            plotter.subtractYLinear()
            
    def subtractXQuad(self):
        for plotter in self.PlotterList:
            plotter.subtractXQuad() 
            
    def subtractYQuad(self):
        for plotter in self.PlotterList:
            plotter.subtractYLinear()         

    def subtractSelectedArea(self):
        for plotter in self.PlotterList:
            plotter.subtractOverallConstant(plotter.Average_SelectedArea)
#####Subtract Related Function
   
    def MultiplyAll(self):
        self.MultiplyWindow.moveDefault()
        self.MultiplyWindow.show()

    def MultiplyAllPlotData(self, multiplier):
        for plotter in self.PlotterList:
            NewData = plotter.PlotData * multiplier
            plotter.PlotData = NewData
            plotter.Plot_Data()

    def keyPressEvent(self, event):
        super(CommandingCenter, self).keyPressEvent(event)
        self.keyPressed.emit(event) 

    def PressingKey(self, event):
        print event.key()
        if event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace:
            item = self.listWidget_Plots.currentItem()
            if not item is None:
                index = self.listWidget_Plots.indexFromItem(item).row()
                self.DeletePlotter(index)
    
    def DeletePlotter(self, index):
        self.PlotterList[index].close()

    def CopyPlotter(self, plotter):
        pass

    def Feedback(self, str):
        self.label_Feedback.setText(str)

    def moveDefault(self):
        self.move(10,170)
