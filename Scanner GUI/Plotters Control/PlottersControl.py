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

path = sys.path[0] + r"\Plotters Control"
sys.path.append(path + r'\Plotter')

import plotter

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
    def __init__(self, reactor, parent = None):
        super(CommandingCenter, self).__init__(parent)

        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        self.PlotterList = [] #PlotterList contains the all the Plotters
        self.PlotsListA, self.PlotsListB = [], [] #PlotsListA and PlotsListB contain the Plotter.number

        #Color Code  [0]for Text, [1] for Background
        self.Color_NoData = [QtGui.QColor(131, 131, 131), QtGui.QColor(0, 0, 0)]
        self.Color_ContainData = [QtGui.QColor(0, 0, 0), QtGui.QColor(100, 100, 100)]
        self.Color_ContainPlotData = [QtGui.QColor(0, 0, 0), QtGui.QColor(155, 155, 155)]
        self.Color_Compatible = [QtGui.QColor(0, 0, 0), QtGui.QColor(170, 255, 0)]
        self.Color_NotCompatible = [QtGui.QColor(0, 0, 0), QtGui.QColor(255, 100, 100)]
        

        self.listWidget_Plots.itemDoubleClicked.connect(self.AddToProcess)
        self.listWidget_PlotsListA.itemDoubleClicked.connect(self.RemovePlotsListAItem)
        self.listWidget_PlotsListB.itemDoubleClicked.connect(self.RemovePlotsListBItem)
        self.pushButton_Process.clicked.connect(self.ProcessData)
        self.pushButton_AddPlotter.clicked.connect(self.AddPlotter)
        
        self.RefreshPlotList()

        self.pushButton_AddPlotter.setEnabled(True)

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

    def disconnectLabRAD(self):
        self.cxn = False
        self.cxn_dv = False
        self.gen_dv = False
        self.dv = False
        self.pushButton_AddPlotter.setEnabled(False)

#####Labrad Related Function

    def ClearListWidget(self):
        self.listWidget_Plots.clear()
        self.listWidget_PlotsListA.clear()
        self.listWidget_PlotsListB.clear()
        
    def RefreshPlotList(self):
        self.ClearListWidget()
        for plotter in self.PlotterList:
            item = QtGui.QListWidgetItem()
            number = plotter.number
            self.renderItem(item, number)
            self.listWidget_Plots.addItem(item)
            
        index = 0
        for i in self.PlotsListA:
            item = QtGui.QListWidgetItem()
            self.renderItem(item, i, 'ProcessList', index)
            self.listWidget_PlotsListA.addItem(item)
            index += 1
            
        index = 0
        for i in self.PlotsListB:
            item = QtGui.QListWidgetItem()
            self.renderItem(item, i, 'ProcessList', index)
            self.listWidget_PlotsListB.addItem(item)
            index += 1
            
    def renderItem(self, ListWidgetItem , number, type = 'MainList', processlistindex = 0): #Based on the plotter.number, dress the Item property
        try:
            plotter = self.GrabPlotterFromNumber(number)
            Text = self.PlotterList[number].Title
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
                
            if type == 'ProcessList': #For processing Plot list, we need index to assist
                Flag = True
                if len(self.PlotsListA) < (processlistindex + 1) or self.PlotsListB == [] or self.PlotsListA == [] or len(self.PlotsListB) < (processlistindex + 1):
                    Flag = False
                else:
                    numberA, numberB = self.PlotsListA[processlistindex], self.PlotsListB[processlistindex]
                    plotterA, plotterB = self.GrabPlotterFromNumber(numberA), self.GrabPlotterFromNumber(numberB)
                    Ax, Ay = str(plotterA.Number_PlotData_X), str(plotterA.Number_PlotData_Y)
                    Bx, By = str(plotterB.Number_PlotData_X), str(plotterB.Number_PlotData_Y)
                    if Ax != Bx or Ay != By:#if the data structure does not matches
                        Flag = False
                        
                if Flag:
                    ListWidgetItem.setTextColor(self.Color_Compatible[0])
                    ListWidgetItem.setBackgroundColor(self.Color_Compatible[1])#Light red for not compatible
                else:
                    ListWidgetItem.setTextColor(self.Color_NotCompatible[0])
                    ListWidgetItem.setBackgroundColor(self.Color_NotCompatible[1])#Light red for not compatible
                    
        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def GrabPlotterFromNumber(self, number): #return the plotter based on the plotter.number given
        for plotter in self.PlotterList:
            if number == plotter.number:
                return plotter
        
    def AddToProcess(self, item, process = 'Add'):
        try:
            if process == 'Transfer':
                pass
            elif process == 'Add' and item.backgroundColor() == self.Color_ContainPlotData[1]:#Only Proceed with data contained
                index = self.listWidget_Plots.indexFromItem(item).row()
                number = self.PlotterList[index].number
                if  self.listWidget_PlotsListA.count() <= self.listWidget_PlotsListB.count():
                    self.PlotsListA.append(number)
                else:
                    self.PlotsListB.append(number)
            else:
                print "Only Add to Process if Data is loaded"
                
            self.RefreshPlotList()
            
        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno
                
    def ProcessData(self, c = None):
        Flag = True
        for i in range(self.listWidget_PlotsListA.count()):
            if self.listWidget_PlotsListA.item(i).backgroundColor() != self.Color_Compatible[1]:
                Flag = False
        
        if Flag:
            for index in range(len(self.PlotsListA)):
                numberA, numberB = self.PlotsListA[index], self.PlotsListB[index]
                plotterA, plotterB = self.GrabPlotterFromNumber(numberA), self.GrabPlotterFromNumber(numberB)
                PlotDataA, PlotDataB  = plotterA.PlotData, plotterB.PlotData,
                PlotDataGenerated = PlotDataA - PlotDataB
                
                operation = ' Subtract '
                procedure = plotterA.Title + operation + plotterA.Title
                
                self.AddPlotter()
                self.transferPlotData(self.PlotterList[-1], PlotDataGenerated, procedure, procedure, procedure, plotterA.PlotParameters, [plotterA.comboBox_xAxis.currentText(),plotterA.comboBox_yAxis.currentText()],[plotterA.comboBox_zAxis.currentText()])
                self.PlotterList[-1].RefreshComboIndex()
                self.PlotterList[-1].ParsePlotData()
                self.PlotterList[-1].refreshPlot()
                self.PlotterList[-1].editDataInfo.RefreshInfo()
            self.PlotsListA, self.PlotsListB = [],[]
            self.RefreshPlotList()
        else:
            print "Data not Compatible"

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

    def moveDefault(self):
        self.move(550,10)
        if not self.dv is None:
            self.AddPlotter()
