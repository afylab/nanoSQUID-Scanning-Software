from PyQt4 import QtGui, QtCore
from twisted.internet.defer import inlineCallbacks
import twisted
import numpy as np
import pyqtgraph as pg
import exceptions

import DrawSquareWindowUI



class Window(QtGui.QMainWindow, DrawSquareWindowUI.Ui_MainWindow):
    
    def __init__(self, reactor, parent=None):
        
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.moveDefault()

        self.push_DrawSquare.clicked.connect(self.updateSquare)
        
        self.topLeft = (10,15)
        self.bottomLeft = (10,115)
        self.topRight = (110,15)
        self.bottomRight = (110,115)
        
        self.viewScanArea = True
        
    def setupAdditionalUi(self):
        a = 1
    
        
    def moveDefault(self):    
        self.move(550,10)
        
    def paintEvent(self, e):
        if self.viewScanArea:
            qp = QtGui.QPainter()
            qp.begin(self)
            self.drawSquare(qp)
            qp.end()
        
    def drawSquare(self, qp):
        pen = QtGui.QPen(QtGui.QColor(200, 0, 0), 2, QtCore.Qt.DashLine) 
        qp.setPen(pen)

        qp.drawLine(self.topLeft[0], self.topLeft[1], self.topRight[0], self.topRight[1])
        qp.drawLine(self.topLeft[0], self.topLeft[1], self.bottomLeft[0], self.bottomLeft[1])
        qp.drawLine(self.topRight[0], self.topRight[1], self.bottomRight[0], self.bottomRight[1])
        qp.drawLine(self.bottomLeft[0], self.bottomRight[1], self.bottomRight[0], self.bottomRight[1])

    def updateSquare(self):
        self.topLeft = (15,25)
        self.bottomLeft = (10,115)
        self.topRight = (125,15)
        self.bottomRight = (110,115)
        
        self.repaint()



