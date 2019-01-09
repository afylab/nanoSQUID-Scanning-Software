from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np

path = sys.path[0] + r"\Plotters Control\Plotter\Gradient Setting"
Ui_GradSet, QtBaseClass = uic.loadUiType(path + r"\gradSettings.ui")

class gradSet(QtGui.QDialog, Ui_GradSet):
    def __init__(self, reactor, dataPct):
        super(gradSet, self).__init__()
        
        self.reactor = reactor
        self.setupUi(self)
        self.dataPct = float(dataPct) * 100
        self.dataPercent.setValue(self.dataPct)
        self.okBtn.clicked.connect(self._ok)
        self.cancelBtn.clicked.connect(self._cancel)

    def _ok(self):
        self.accept()
    def _cancel(self):
        self.reject()
    def closeEvent(self, e):
        self.reject()