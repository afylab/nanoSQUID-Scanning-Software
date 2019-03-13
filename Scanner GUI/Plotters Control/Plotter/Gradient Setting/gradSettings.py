from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np

path = sys.path[0] + r"\Plotters Control\Plotter\Gradient Setting"
Ui_GradSet, QtBaseClass = uic.loadUiType(path + r"\gradSettings.ui")

class gradSet(QtGui.QDialog, Ui_GradSet):
    def __init__(self, reactor, SideDataNumber, PolyFitOrder, EdgeNumber):
        super(gradSet, self).__init__()
        
        self.reactor = reactor
        self.setupUi(self)
        self.SideDataNumber_Value = int(SideDataNumber)
        self.PolyFitOrder_Value = int(PolyFitOrder)
        self.EdgeNumber_Value = int(EdgeNumber)
        self.dataNumber.setValue(self.SideDataNumber_Value)
        self.PolyFitOrder.setValue(self.PolyFitOrder_Value)
        self.EdgeNumber.setValue(self.EdgeNumber_Value)
        self.okBtn.clicked.connect(self._ok)
        self.cancelBtn.clicked.connect(self._cancel)

    def _ok(self):
        self.accept()
    def _cancel(self):
        self.reject()
    def closeEvent(self, e):
        self.reject()