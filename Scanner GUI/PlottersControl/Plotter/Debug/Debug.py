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

path = sys.path[0] + r"\PlottersControl\Plotter\Debug"
Ui_Debug, QtBaseClass = uic.loadUiType(path + r"\Debug.ui")

class DebugPanel(QtGui.QMainWindow, Ui_Debug):
    def __init__(self, reactor, button, parent = None ):
        super(DebugPanel, self).__init__()
        self.setupUi(self)

        self.reactor = reactor
        self.parent = parent
        self.button = button

        self.pushButton_StandardDeviation.clicked.connect(self.PrintStandardDeviation)

    def PrintStandardDeviation(self):
        data = self.parent.PlotData
        std = np.std(data)
        print std

    def moveDefault(self):
        buttonx, buttony = self.button.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        Offset = 50
        self.move(buttonx + Offset, buttony)
