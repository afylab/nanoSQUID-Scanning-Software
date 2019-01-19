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

path = sys.path[0] + r"\Plotters Control\Process List"
Ui_ProcessWindow, QtBaseClass = uic.loadUiType(path + r"\ProcessWindow.ui")


class ProcessWindow(QtGui.QMainWindow, Ui_ProcessWindow):
    def __init__(self, reactor, parent = None):
        super(ProcessWindow, self).__init__(parent)

        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        self.PlotsListA, self.PlotsListB = [], [] #PlotsListA and PlotsListB contain the Plotter.number

        #Color Code  [0]for Text, [1] for Background
        self.Color_Compatible = [QtGui.QColor(0, 0, 0), QtGui.QColor(170, 255, 0)]
        self.Color_NotCompatible = [QtGui.QColor(0, 0, 0), QtGui.QColor(255, 100, 100)]

        self.listWidget_PlotsListA.itemDoubleClicked.connect(self.RemovePlotsListAItem)
        self.listWidget_PlotsListB.itemDoubleClicked.connect(self.RemovePlotsListBItem)
        self.pushButton_Process.clicked.connect(self.ProcessData)
        self.pushButton_TransferLeft.clicked.connect(self.TransferLeft)
        self.pushButton_TransferRight.clicked.connect(self.TransferRight)
        
        self.RefreshPlotList()

    def ClearListWidget(self):
        self.listWidget_PlotsListA.clear()
        self.listWidget_PlotsListB.clear()
        
    def RefreshPlotList(self):
        self.ClearListWidget()
        index = 0
        for i in self.PlotsListA:
            item = QtGui.QListWidgetItem()
            self.renderItem(item, i, index)
            self.listWidget_PlotsListA.addItem(item)
            index += 1
            
        index = 0
        for i in self.PlotsListB:
            item = QtGui.QListWidgetItem()
            self.renderItem(item, i, index)
            self.listWidget_PlotsListB.addItem(item)
            index += 1
            
    def renderItem(self, ListWidgetItem , number, processlistindex = 0): #Based on the plotter.number, dress the Item property
        try:
            plotter = self.parent.GrabPlotterFromNumber(number)
            Text = self.parent.PlotterList[number].Title
            ListWidgetItem.setText(Text)
                
            Flag = True
            if len(self.PlotsListA) < (processlistindex + 1) or self.PlotsListB == [] or self.PlotsListA == [] or len(self.PlotsListB) < (processlistindex + 1):
                Flag = False
            else:
                numberA, numberB = self.PlotsListA[processlistindex], self.PlotsListB[processlistindex]
                plotterA, plotterB = self.parent.GrabPlotterFromNumber(numberA), self.parent.GrabPlotterFromNumber(numberB)
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

    def AddToProcess(self, item, process = 'Add'):
        try:
            if process == 'Transfer':
                pass
            elif process == 'Add' and item.backgroundColor() == self.Color_ContainPlotData[1]:#Only Proceed with data contained
                index = self.listWidget_Plots.indexFromItem(item).row()
                number = self.parent.PlotterList[index].number
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
        Flag = True   #Check that all data are compatible
        for i in range(self.listWidget_PlotsListA.count()):
            if self.listWidget_PlotsListA.item(i).backgroundColor() != self.Color_Compatible[1]:
                Flag = False
        
        if Flag:
            for index in range(len(self.PlotsListA)):
                numberA, numberB = self.PlotsListA[index], self.PlotsListB[index]
                plotterA, plotterB = self.parent.GrabPlotterFromNumber(numberA), self.parent.GrabPlotterFromNumber(numberB)
                PlotDataA, PlotDataB  = plotterA.PlotData, plotterB.PlotData,
                operation = ' ' + self.label_Operation.text() + ' '
                if 'Subtract' in operation:
                    PlotDataGenerated = PlotDataA - PlotDataB
                elif 'Division' in operation:
                    PlotDataGenerated = PlotDataA / PlotDataB
                
                procedure = plotterA.Title + operation + plotterA.Title
                
                self.parent.AddPlotter()
                self.transferPlotData(self.parent.PlotterList[-1], PlotDataGenerated, procedure, procedure, procedure, plotterA.PlotParameters, [plotterA.comboBox_xAxis.currentText(),plotterA.comboBox_yAxis.currentText()],[plotterA.comboBox_zAxis.currentText()])
                self.parent.PlotterList[-1].RefreshComboIndex()
                self.parent.PlotterList[-1].ParsePlotData()
                self.parent.PlotterList[-1].refreshPlot()
                self.parent.PlotterList[-1].editDataInfo.RefreshInfo()
            self.PlotsListA, self.PlotsListB = [],[]
            self.parent.RefreshPlotList()
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

    def RemovePlotsListAItem(self, item):
        index = self.listWidget_PlotsListA.indexFromItem(item).row()
        self.PlotsListA.pop(index)
        self.RefreshPlotList()

    def RemovePlotsListBItem(self, item):
        index = self.listWidget_PlotsListB.indexFromItem(item).row()
        self.PlotsListB.pop(index)
        self.RefreshPlotList()

    def TransferLeft(self):
        item = self.listWidget_PlotsListB.currentItem()
        if not item is None:
            index = self.listWidget_PlotsListB.indexFromItem(item).row()
            if index != -1:
                number = self.PlotsListB.pop(index)
                self.PlotsListA.append(number)
            self.RefreshPlotList()

    def TransferRight(self):
        item = self.listWidget_PlotsListA.currentItem()
        if not item is None:
            index = self.listWidget_PlotsListA.indexFromItem(item).row()
            if index != -1:
                number = self.PlotsListA.pop(index)
                self.PlotsListB.append(number)
            self.RefreshPlotList()
            
    def moveDefault(self):
        parentx, parenty = self.parent.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        parentwidth, parentheight = self.parent.width(), self.parent.height()
        Offset = 10
        self.move(parentx, parenty + parentheight + Offset )   
