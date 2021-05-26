from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np

path = sys.path[0] + r"\PlottersControl\Plotter\Remove Spike Setting"
Ui_DespikesSetting, QtBaseClass = uic.loadUiType(path + r"\DespikeSettings.ui")

class DespikeSet(QtGui.QMainWindow, Ui_DespikesSetting):
    def __init__(self, reactor, parent):
        super(DespikeSet, self).__init__()

        self.reactor = reactor
        self.setupUi(self)
        self.parent = parent
        self.lineEdit_AdjacentPoints.editingFinished.connect(self.UpdateTextEdit)
        self.lineEdit_NumberofSigma.editingFinished.connect(self.UpdateTextEdit)
        self.RefreshTextEdit()

    def UpdateTextEdit(self):
        self.parent.AdjacentPoints = int(self.lineEdit_AdjacentPoints.text())
        self.parent.NumberOfSigma = int(self.lineEdit_NumberofSigma.text())
        self.RefreshTextEdit()

    def RefreshTextEdit(self):
        self.lineEdit_AdjacentPoints.setText(str(self.parent.AdjacentPoints))
        self.lineEdit_NumberofSigma.setText(str(self.parent.NumberOfSigma))

    def moveDefault(self):
        buttonposition = self.parent.pushButton_Despike.mapToGlobal(QtCore.QPoint(0,0))
        buttonx, buttony = buttonposition.x(), buttonposition.y()
        Offset = 50
        self.move(buttonx + Offset, buttony)
