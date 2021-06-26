
import sys
from PyQt5 import QtCore, QtGui, QtWidgets, QtTest, uic
import numpy as np
from twisted.internet.defer import inlineCallbacks, Deferred

path = sys.path[0] + r"\CoarseAttocubeControl\Debug Panel"
Ui_DebugWindow, QtBaseClass = uic.loadUiType(path + r"\Debug.ui")

class DebugWindow(QtWidgets.QMainWindow, Ui_DebugWindow):
    def __init__(self, reactor, parent = None):
        super(DebugWindow, self).__init__()
        
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)
        
        self.pushButton_SetAxisOutput.clicked.connect(lambda: self.SetAxisOutput(0, self.checkBox_AxisOutput_Enable.isChecked(), self.checkBox_AxisOutput_AutoDisable.isChecked()))
        
    @inlineCallbacks
    def SetAxisOutput(self, AxisNo, Enable, AutoDisable):
        print(AxisNo, Enable, AutoDisable)
        yield self.parent.anc350.set_axis_output(AxisNo, Enable, AutoDisable)
            
    def moveDefault(self):
        self.move(0, 550)  
