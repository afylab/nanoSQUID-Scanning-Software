from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np

path = sys.path[0] + r"\PlottersControl\Plotter\Subtract Constant Window"
Ui_SubConstant, QtBaseClass = uic.loadUiType(path + r"\ConstantSubtract.ui")

class SubConstantWindow(QtGui.QMainWindow, Ui_SubConstant):
    def __init__(self, reactor, parent):
        super(SubConstantWindow, self).__init__()

        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        self.pushButton_ok.clicked.connect(self.OK)
        self.pushButton_Cancel.clicked.connect(self.Cancel)
        self.lineEdit_Constant.editingFinished.connect(self.ChangeConstant)

    def ChangeConstant(self):
        number = float(self.lineEdit_Constant.text())
        self.parent.ConstantSubtracted = number
        self.lineEdit_Constant.setText(str(number))

    def moveDefault(self):
        buttonposition = self.parent.subtract.mapToGlobal(QtCore.QPoint(0,0))
        buttonx, buttony = buttonposition.x(), buttonposition.y()
        Offset = 50
        self.move(buttonx + Offset, buttony)

    def OK(self):
        self.parent.subtractOverallConstant(self.parent.ConstantSubtracted)
        self.close()

    def Cancel(self):
        self.close()
