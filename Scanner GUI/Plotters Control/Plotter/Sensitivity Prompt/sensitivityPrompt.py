from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np


path = sys.path[0] + r"\Plotters Control\Plotter\Sensitivity Prompt"
Ui_SensitivityPrompt, QtBaseClass = uic.loadUiType(path + r"\sensitivityPrompt.ui")

class Sensitivity(QtGui.QDialog, Ui_SensitivityPrompt):
    def __init__(self, dep, ind, reactor):
        super(Sensitivity, self).__init__()
        
        self.depVars = dep
        self.indVars = ind
        self.reactor = reactor
        self.setupUi(self)
        
        self.plotNoise.clicked.connect(self.toggleNS)
        self.plotSens.clicked.connect(self.toggleSN)

        self.okBtn.clicked.connect(self._ok)
        self.cancelBtn.clicked.connect(self._cancel)
        
        
        self.noiseSens = 0

        if len(self.indVars) % 2 == 0:
            for i in self.indVars[int(len(self.indVars) / 2) : len(self.indVars)]:
                self.difIndex.addItem(i)
                self.constIndex.addItem(i)
            for i in self.depVars:
                self.noiseIndex.addItem(i)
                self.depIndex.addItem(i)
    
    def toggleNS(self):
        self.plotSens.setChecked(False)
        self.plotNoise.setChecked(True)
        self.noiseSens = 0
    def toggleSN(self):
        self.plotSens.setChecked(True)
        self.plotNoise.setChecked(False)
        self.noiseSens = 1

    def sensIndicies(self):
        sensIndex = [self.difIndex.currentIndex(), self.constIndex.currentIndex(), self.depIndex.currentIndex(), self.noiseIndex.currentIndex(), self.noiseSens, int(self.convCheck.checkState())]
        return sensIndex
        
    def sensConv(self):
        return [self.gainVal.value(), self.bwVal.value()]

    def _ok(self):
        self.accept()
    def _cancel(self):
        self.reject()
    def closeEvent(self, e):
        self.reject()