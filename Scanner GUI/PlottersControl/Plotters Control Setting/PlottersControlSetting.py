from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np

path = sys.path[0] + r"\PlottersControl\Plotters Control Setting"
Ui_SettingWindow, QtBaseClass = uic.loadUiType(path + r"\PlottersControlSetting.ui")

from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView

class SettingWindow(QtGui.QMainWindow, Ui_SettingWindow):
    def __init__(self, reactor, parent, button):
        super(SettingWindow, self).__init__()

        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)
        self.button = button

        self.Setting_Parameter = {
            'NumberHistogramBin': 20,
            'ScaleFactor': 5.36,
            'Offset': 0.0
        }

        self.lineEdit_NumberHistogramBin.editingFinished.connect(lambda: self.UpdateParameter('NumberHistogramBin', self.lineEdit_NumberHistogramBin))
        self.lineEdit_ScaleFactor.editingFinished.connect(lambda: self.UpdateParameter('ScaleFactor', self.lineEdit_ScaleFactor))
        self.lineEdit_Offset.editingFinished.connect(lambda: self.UpdateParameter('Offset', self.lineEdit_Offset))


        self.UpdateParameter('NumberHistogramBin', self.lineEdit_NumberHistogramBin)
        self.UpdateParameter('ScaleFactor', self.lineEdit_ScaleFactor)
        self.UpdateParameter('Offset', self.lineEdit_Offset)

    def UpdateParameter(self, key, lineEdit, range = None):
        dummystr=str(lineEdit.text())
        dummyval=readNum(dummystr, self , False)
        if isinstance(dummyval,float):
            if range == None:
                self.Setting_Parameter[key] = dummyval
            elif dummyval >= range[0] and dummyval <= range[1]:
                self.Setting_Parameter[key] = dummyval
        lineEdit.setText(formatNum(self.Setting_Parameter[key], 6))

    def moveDefault(self):
        buttonposition = self.button.mapToGlobal(QtCore.QPoint(0,0))
        buttonx, buttony = buttonposition.x(), buttonposition.y()
        Offset = 50
        self.move(buttonx + Offset, buttony)
