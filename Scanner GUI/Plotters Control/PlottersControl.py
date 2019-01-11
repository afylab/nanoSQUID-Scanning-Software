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
sys.path.append(path + r'\Process List')

import plotter
import ProcessWindow

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
        self.ProcessList = ProcessWindow.ProcessWindow(self.reactor, self)

        #Color Code  [0]for Text, [1] for Background
        self.Color_NoData = [QtGui.QColor(131, 131, 131), QtGui.QColor(0, 0, 0)]
        self.Color_ContainData = [QtGui.QColor(0, 0, 0), QtGui.QColor(100, 100, 100)]
        self.Color_ContainPlotData = [QtGui.QColor(0, 0, 0), QtGui.QColor(155, 155, 155)]

        self.listWidget_Plots.itemDoubleClicked.connect(self.AddtoProcess)
        self.pushButton_Subtract.clicked.connect(self.Subtract)
        self.pushButton_AddPlotter.clicked.connect(self.AddPlotter)
        
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

    def disconnectLabRAD(self):
        self.cxn = False
        self.cxn_dv = False
        self.gen_dv = False
        self.dv = False
        self.pushButton_AddPlotter.setEnabled(False)

#####Labrad Related Function

    def ClearListWidget(self):
        self.listWidget_Plots.clear()
        self.ProcessList.ClearListWidget()
        
    def RefreshPlotList(self):
        self.ClearListWidget()
        for plotter in self.PlotterList:
            item = QtGui.QListWidgetItem()
            number = plotter.number
            self.renderItem(item, number)
            self.listWidget_Plots.addItem(item)
        
        self.ProcessList.RefreshPlotList()

            
    def renderItem(self, ListWidgetItem , number): #Based on the plotter.number, dress the Item property
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

        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def GrabPlotterFromNumber(self, number): #return the plotter based on the plotter.number given
        for plotter in self.PlotterList:
            if number == plotter.number:
                return plotter
        
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
                
    def Subtract(self, c = None):
        self.ProcessList.raise_()
        self.ProcessList.show()
        self.ProcessList.label_Operation.setText('Subtract')

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
        parentx, parenty = self.parent.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        parentwidth, parentheight = self.parent.width(), self.parent.height()
        Offset = 10
        self.move(parentx, parenty + Offset)   
