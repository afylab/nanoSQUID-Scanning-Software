from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np

path = sys.path[0] + r"\Plotters Control\Multiplier Window"
Ui_MultiplierWindow, QtBaseClass = uic.loadUiType(path + r"\MultiplierSettings.ui")

class MultiplierWindow(QtGui.QMainWindow, Ui_MultiplierWindow):
    def __init__(self, reactor, parent):
        super(MultiplierWindow, self).__init__()
        
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        self.pushButton_ok.clicked.connect(self.OK)
        self.pushButton_Cancel.clicked.connect(self.Cancel)
        self.lineEdit_Multiplier.editingFinished.connect(self.ChangeMultiplier)


    def ChangeMultiplier(self):
        number = float(self.lineEdit_Multiplier.text())
        self.parent.multiplier = number
        self.lineEdit_Multiplier.setText(str(number))

    def moveDefault(self):
        buttonposition = self.parent.pushButton_MultiplySelected.mapToGlobal(QtCore.QPoint(0,0))
        buttonx, buttony = buttonposition.x(), buttonposition.y()
        Offset = 50
        self.move(buttonx + Offset, buttony)  

    def OK(self):
        self.parent.MultiplySelectedPlotData(self.parent.multiplier)
        self.close()

    def Cancel(self):
        self.close()
