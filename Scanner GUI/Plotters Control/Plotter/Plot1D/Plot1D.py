from __future__ import division
import os
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import scipy.io as sio
from nSOTScannerFormat import readNum, formatNum

path = sys.path[0] + r"\Plotters Control\Plotter\Plot1D"
Ui_Plot1D, QtBaseClass = uic.loadUiType(path + r"\Plot1D.ui")

class Plot1D(QtGui.QMainWindow, Ui_Plot1D):
    def __init__(self, reactor, Name, parent = None ):
        super(Plot1D, self).__init__()
        self.setupUi(self)

        self.reactor = reactor
        self.Name = Name
        self.label_Name.setText(self.Name)
        self.setWindowTitle(self.Name)
        self.parent = parent
        self.Unit = {
            'Optimal Bias': 'V',
            'Optimal Sensitivity': u'\u221a' + 'Hz' + '/T',
            'Optimal Noise': 'T/' + u'\u221a' + 'Hz'
        }

        self.LineVisible = False
        self.lineEdit_LineCutPosition.editingFinished.connect(self.SetupLineCutposition)
        self.pushButton_Show.clicked.connect(self.ShowLine)
        self.pushButton_SaveMatlab.clicked.connect(self.PlotMatLab)
        self.pushButton_Switch.clicked.connect(self.SwitchData)
        if self.Name != 'Optimal Sensitivity':
            self.pushButton_Switch.hide()
        self.Line = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.Plot = pg.PlotWidget(parent = None)
        self.SetupPlot()
        self.Line.sigPositionChangeFinished.connect(self.ChangeLineCutValue)

    def SwitchData(self):
        self.Plot.removeItem(self.PlotShown)
        self.YData = [1.0/data for data in self.YData]
        if self.Name == 'Optimal Sensitivity':
            self.Name = 'Optimal Noise'
        elif self.Name == 'Optimal Noise':
            self.Name = 'Optimal Sensitivity'
        self.SetupLabels()
        self.label_Name.setText(self.Name)
        self.setWindowTitle(self.Name)
        self.PlotData(self.XData, self.YData)

    def ChangeLineCutValue(self):
        self.position=self.Line.value()
        self.lineEdit_LineCutPosition.setText(formatNum(self.position))
        self.Line.setValue(float(self.position))

    def SetupLineCutposition(self):
        try:
            dummystr=str(self.lineEdit_LineCutPosition.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float):
                self.position=dummyval
            self.lineEdit_LineCutPosition.setText(formatNum(self.position))
            self.Line.setValue(float(self.position))
    
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
    
    def SetupPlot(self):
        self.Plot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.Plot.showAxis('right', show = True)
        self.Plot.showAxis('top', show = True)
        self.Layout_Plot.addWidget(self.Plot)
        self.SetupLabels()
    
    def SetupLabels(self):
        self.Plot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.Plot.setLabel('left', self.Name, units = self.Unit[self.Name])

    def PlotData(self, dataX, dataY):
        self.XData = dataX
        self.YData = dataY
        if self.Name == 'Optimal Bias':
            color = 'r'
        elif self.Name == 'Optimal Sensitivity' or self.Name == 'Optimal Noise':
            color = 'b'

        self.PlotShown = self.Plot.plot(x = dataX, y = dataY, pen = color)
        print self.Name
        print self.XData
        print self.YData

    def ShowLine(self):
        if self.LineVisible:
            self.Plot.removeItem(self.Line)
        elif not self.LineVisible:
            self.Plot.addItem(self.Line)
        self.LineVisible = not self.LineVisible

    def PlotMatLab(self):
        fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
        if fold:
            XData = np.asarray(self.XData)
            YData = np.asarray(self.YData)
    
            matData = np.transpose(np.vstack((XData, YData)))
            savename = fold.split("/")[-1].split('.mat')[0]
            sio.savemat(fold,{savename:matData})
            matData = None                

    def moveDefault(self):
        parentx, parenty = self.parent.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        parentwidth, parentheight = self.parent.width(), self.parent.height()
        Offset = 400
        if self.Name == 'Optimal Sensitivity':
            self.move(parentx + parentwidth/2, parenty + parentheight/2) 
        elif self.Name == 'Optimal Bias':
            self.move(parentx + parentwidth/2, parenty + parentheight/2 + Offset) 



