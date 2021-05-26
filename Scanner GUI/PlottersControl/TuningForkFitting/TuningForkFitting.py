from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np
import scipy
import math

path = sys.path[0] + r"\PlottersControl\TuningForkFitting"
Ui_FittingWindow, QtBaseClass = uic.loadUiType(path + r"\TuningForkFittingWindow.ui")

class ACFittingWindow(QtGui.QMainWindow, Ui_FittingWindow):
    def __init__(self, reactor, parent, button):
        super(ACFittingWindow, self).__init__()

        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)
        self.button = button

        self.pushButton_Ok.clicked.connect(self.ProceedFitting)
        self.step = 0
        self.Feedback('Select Tuning Fork Data')

    def ProceedFitting(self):
        print self.step
        itemlist = self.parent.listWidget_Plots.selectedItems()
        if len(itemlist) == 1:
            index = self.parent.listWidget_Plots.indexFromItem(itemlist[0]).row()
            if self.parent.PlotterList[index].PlotData is not None:
                plotdata = self.parent.PlotterList[index].PlotData
                if self.step == 0:
                    print 'a'
                    self.ACData = plotdata
                    self.Feedback('Select derivative in x')
                    self.step = 1
                elif self.step == 1:
                    print 'b'
                    self.xData = plotdata
                    self.Feedback('Select derivative in y')
                    self.step = 2
                elif self.step == 2:
                    print 'c'
                    self.yData = plotdata
                    if self.ACData.shape == self.xData.shape and self.xData.shape == self.yData.shape:
                        self.FitTuningForkData()
                    else:
                        self.Feedback('Check shape of Data')
                    self.step = 0
            else:
                self.Feedback('PlotData is None')
        else:
            self.Feedback('Please select one plotter')

    def FitTuningForkData(self):
        Fit = scipy.optimize.minimize(self.SquareDifference_Weight, [1.0, 1.0], method = str(self.comboBox_Method.currentText()))
        Success = Fit.success
        if Success:
            fitparameter = Fit.x
            self.Feedback('Fit successful, X component is ' + str(fitparameter[0]) + ' and Y component is ' + str(fitparameter[1]))
            self.lineEdit_Amplitude.setText(str(math.sqrt(fitparameter[0] ** 2 + fitparameter[1] ** 2) * 1000.0))
            self.lineEdit_Angle.setText(str(180.0 / math.pi * math.atan2(fitparameter[0], fitparameter[1])))
        elif not Success:
            self.Feedback('Failure: ' + str(Fit.message))

    def SquareDifference_Weight(self, weight):
        gain = float(self.lineEdit_Gain.text())
        DataSubtracted = self.ACData.flatten() * 1000.0 - weight[0] * self.xData.flatten() * 1000.0 - weight[1] * self.yData.flatten() * 1000.0
        Square = np.sum(np.square(DataSubtracted))
        return Square

    def Feedback(self,string):
        self.label_Feedback.setText(string)

    def moveDefault(self):
        buttonposition = self.button.mapToGlobal(QtCore.QPoint(0,0))
        buttonx, buttony = buttonposition.x(), buttonposition.y()
        Offset = 50
        self.move(buttonx + Offset, buttony)
