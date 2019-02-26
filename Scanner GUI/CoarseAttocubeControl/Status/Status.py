from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np

path = sys.path[0] + r"\CoarseAttocubeControl\Status"
Ui_StatusWindow, QtBaseClass = uic.loadUiType(path + r"\Status.ui")

class StatusWindow(QtGui.QMainWindow, Ui_StatusWindow):
    def __init__(self, reactor, parent = None):
        super(StatusWindow, self).__init__()
        
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)
        
        self.Connect = [self.pushButton_Connected_1, self.pushButton_Connected_2, self.pushButton_Connected_3]
        self.Enable = [self.pushButton__Enabled_1, self.pushButton__Enabled_2, self.pushButton__Enabled_3]
        self.Moving = [self.pushButton__Moving_1, self.pushButton__Moving_2, self.pushButton__Moving_3]
        self.TargetReach = [self.pushButton__TargetReached_1, self.pushButton__TargetReached_2, self.pushButton__TargetReached_3]
        self.EotForward = [self.pushButton__EndofTravelForward_1, self.pushButton__EndofTravelForward_2, self.pushButton__EndofTravelForward_3]
        self.EotBackward = [self.pushButton__EndofTravelBackward_1, self.pushButton__EndofTravelBackward_2, self.pushButton__EndofTravelBackward_3]
        self.Error = [self.pushButton__Error_1, self.pushButton__Error_2, self.pushButton__Error_3]

        self.Buttons = [self.Connect, self.Enable, self.Moving, self.TargetReach, self.EotForward, self.EotBackward, self.Error]
        
    def ChangeStatus(self, AxisNo, statusarray):
        for i in range(7):
            if statusarray[i] == 1:
                color = 'green'
            else:
                color = 'red'
            Style = 'background:' + color + ';\nborder: 2px solid rgb(0,0,150);\nborder-radius: 5px'
            self.Buttons[i][AxisNo].setStyleSheet(Style)
            
    def moveDefault(self):
        self.move(0, 550)  
