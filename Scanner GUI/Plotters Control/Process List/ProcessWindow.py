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

        self.PlotterList = [[], []]
        self.listWidget_PlotsList = [self.listWidget_PlotsListA, self.listWidget_PlotsListB]
        #Color Code  [0]for Text, [1] for Background
        self.Color_Compatible = [QtGui.QColor(0, 0, 0), QtGui.QColor(170, 255, 0)]
        self.Color_NotCompatible = [QtGui.QColor(0, 0, 0), QtGui.QColor(255, 100, 100)]

        self.listWidget_PlotsList[0].itemDoubleClicked.connect(lambda item: self.RemovePlotListItem(0, item))
        self.listWidget_PlotsList[0].itemChanged.connect(self.DetermineAddition)
        self.listWidget_PlotsList[1].itemDoubleClicked.connect(lambda item: self.RemovePlotListItem(1, item))
        self.listWidget_PlotsList[1].itemChanged .connect(self.DetermineAddition)
        self.pushButton_Process.clicked.connect(self.ProcessData)
        self.pushButton_TransferLeft.clicked.connect(lambda: self.Transfer(1, 0))
        self.pushButton_TransferRight.clicked.connect(lambda: self.Transfer(0, 1))
        self.pushButton_Cancel.clicked.connect(self.Cancel)
        
        self.RefreshPlotList()

    def ClearListWidget(self):
        self.listWidget_PlotsList[0].clear()
        self.listWidget_PlotsList[1].clear()
        
    def RefreshPlotList(self):
        self.ClearListWidget()
        index = 0
        for i in self.PlotterList[0]:
            item = QtGui.QListWidgetItem()
            self.renderItem(item, i, index)
            self.listWidget_PlotsList[0].addItem(item)
            index += 1
            
        index = 0
        for i in self.PlotterList[1]:
            item = QtGui.QListWidgetItem()
            self.renderItem(item, i, index)
            self.listWidget_PlotsList[1].addItem(item)
            index += 1
            
    def renderItem(self, ListWidgetItem , number, processlistindex = 0): #Based on the plotter.number, dress the Item property
        try:
            plotter = self.parent.GrabPlotterFromNumber(number)
            Text = self.parent.PlotterList[number].Title
            ListWidgetItem.setText(Text)
                
            Flag = True
            if len(self.PlotterList[0]) < (processlistindex + 1) or self.PlotterList[1] == [] or self.PlotterList[0] == [] or len(self.PlotterList[1]) < (processlistindex + 1):
                Flag = False
            else:
                numberA, numberB = self.PlotterList[0][processlistindex], self.PlotterList[1][processlistindex]
                plotterA, plotterB = self.parent.GrabPlotterFromNumber(numberA), self.parent.GrabPlotterFromNumber(numberB)
                Ax, Ay = str(plotterA.Number_PlotData_X), str(plotterA.Number_PlotData_Y)
                Bx, By = str(plotterB.Number_PlotData_X), str(plotterB.Number_PlotData_Y)
                if Ax != Bx or Ay != By:#if the data structure does not matches
                    Flag = False
                    
            if plotter.PlotData is None:
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

    def DetermineAddition(self): #Keep Track of Add Items from PlottersControl
        if len(self.PlotterList[0]) < self.listWidget_PlotsList[0].count():
            self.AddtoProcess(self.listWidget_PlotsList[0])
        if len(self.PlotterList[1]) < self.listWidget_PlotsList[1].count():
            self.AddtoProcess(self.listWidget_PlotsList[1])

    def DetermineProcess(self, listwidget):
        pass

    def AddtoProcess(self, listwidget):
        try:
            ItemsToBeAdd = self.parent.listWidget_Plots.selectedItems()
            Indexlist = []
            ContainDataFlag = True
            for item in ItemsToBeAdd:
                index = self.parent.listWidget_Plots.indexFromItem(item).row()
                Indexlist.append(index)
            if ContainDataFlag:
                if listwidget == self.listWidget_PlotsList[0]:
                    for number in Indexlist:
                        self.PlotterList[0].append(number)
                elif listwidget == self.listWidget_PlotsList[1]:
                    for number in Indexlist:
                        self.PlotterList[1].append(number)
                self.RefreshPlotList()
            else:
                self.parent.Feedback('Plotters does not contain data')
        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno
                
    def ProcessData(self, c = None):
        Flag = True   #Check that all data are compatible
        for i in range(self.listWidget_PlotsList[0].count()):
            if self.listWidget_PlotsList[0].item(i).backgroundColor() != self.Color_Compatible[1]:
                Flag = False
                
        
        if Flag:
            for index in range(len(self.PlotterList[0])):
                numberA, numberB = self.PlotterList[0][index], self.PlotterList[1][index]
                plotterA, plotterB = self.parent.GrabPlotterFromNumber(numberA), self.parent.GrabPlotterFromNumber(numberB)
                PlotDataA, PlotDataB  = plotterA.PlotData, plotterB.PlotData,
                operation = ' ' + self.label_Operation.text() + ' '
                if 'Subtract' in operation:
                    PlotDataGenerated = PlotDataA - PlotDataB
                elif 'Division' in operation:
                    PlotDataGenerated = PlotDataA / PlotDataB
                elif 'Addition' in operation:
                    PlotDataGenerated = PlotDataA + PlotDataB
                elif 'Product' in operation:
                    PlotDataGenerated = PlotDataA * PlotDataB
                    
                procedure = plotterA.Title + operation + plotterA.Title
                
                self.parent.AddPlotter()
                self.transferPlotData(self.parent.PlotterList[-1], PlotDataGenerated, procedure, procedure, procedure, plotterA.PlotParameters, [plotterA.comboBox_xAxis.currentText(),plotterA.comboBox_yAxis.currentText()],[plotterA.comboBox_zAxis.currentText()])
                self.parent.PlotterList[-1].RefreshComboIndex()
                self.parent.PlotterList[-1].ParsePlotData()
                self.parent.PlotterList[-1].refreshPlot()
                self.parent.PlotterList[-1].editDataInfo.RefreshInfo()
            self.PlotterList[0], self.PlotterList[1] = [],[]
            self.parent.RefreshInterface()
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

    def RemovePlotListItem(self, number, item):
        index = self.listWidget_PlotsList[number].indexFromItem(item).row()
        self.PlotterList[number].pop(index)
        self.RefreshPlotList()

    def Transfer(self, origin, destiny):
        item = self.listWidget_PlotsList[origin].currentItem()
        if not item is None:
            index = self.listWidget_PlotsList[origin].indexFromItem(item).row()
            if index != -1:
                number = self.PlotterList[origin].pop(index)
                self.PlotterList[destiny].append(number)
            self.RefreshPlotList()

    def Cancel(self):
        self.ClearListWidget()
        self.PlotterList = [[], []]
        self.close()

    def moveDefault(self):
        parentx, parenty = self.parent.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        parentwidth, parentheight = self.parent.width(), self.parent.height()
        Offset = 10
        self.move(parentx, parenty + parentheight + Offset )   
