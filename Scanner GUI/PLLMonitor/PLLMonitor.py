import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import time
import pyqtgraph as pg
import numpy as np

path = sys.path[0] + r"\PLLMonitor"
PLLMonitorUI, QtBaseClass = uic.loadUiType(path + r"\PLLMonitor.ui")

class Window(QtGui.QMainWindow, PLLMonitorUI):
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()   

        self.time_offset = 0    
        self.timeData = np.array([])
        self.deltaFData = np.array([])
        self.phaseErrorData = np.array([])

        self.plotTimeRange = 30

        self.push_zeroTime.clicked.connect(self.zeroTime)
        #Requires no labrad connections
        
        self.horizontalSlider.valueChanged[int].connect(self.setPlotTime)

        self.first_data_point = True
        
    def moveDefault(self):    
        self.move(550,10)
            
    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        self.deltaFPlot = pg.PlotWidget(parent = self)
        self.deltaFPlot.setGeometry(15,40,641,271)
        self.deltaFPlot.setLabel('left', 'Delta F', units = 'Hz')
        self.deltaFPlot.setLabel('bottom', 'Time', units = 's')
        self.deltaFPlot.showAxis('right', show = True)
        self.deltaFPlot.showAxis('top', show = True)
        self.deltaFPlot.setTitle('PLL Delta F vs. Time (s)')

        self.phaseErrorPlot = pg.PlotWidget(parent = self)
        self.phaseErrorPlot.setGeometry(15,310,641,271)
        self.phaseErrorPlot.setLabel('left', 'Phase Error', units = u'\N{DEGREE SIGN}')
        self.phaseErrorPlot.setLabel('bottom', 'Time', units = 's')
        self.phaseErrorPlot.showAxis('right', show = True)
        self.phaseErrorPlot.showAxis('top', show = True)
        self.phaseErrorPlot.setTitle('PLL Error vs. Time (s)')

    def updatePlots(self, deltaF, phaseError):
        
        if self.first_data_point:
            self.time_offset = time.clock()
            self.first_data_point = False

        timepoint = time.clock() - self.time_offset

        self.timeData = np.append(self.timeData, timepoint)
        self.deltaFData = np.append(self.deltaFData, deltaF)
        self.phaseErrorData = np.append(self.phaseErrorData, phaseError)
        self.plotPlots()

    def plotPlots(self):
        length = len(self.timeData)
        if length > 1:
            if (self.timeData[length-1] - self.timeData[0]) <= self.plotTimeRange:
                self.deltaFPlot.clear()
                self.deltaFPlot.plot(self.timeData, self.deltaFData)
                self.phaseErrorPlot.clear()
                self.phaseErrorPlot.plot(self.timeData, self.phaseErrorData)
            else:
                a = np.argmin(np.abs(self.timeData - (self.timeData[length-1] - self.plotTimeRange)))
                self.deltaFPlot.clear()
                self.deltaFPlot.plot(self.timeData[a:], self.deltaFData[a:])
                self.phaseErrorPlot.clear()
                self.phaseErrorPlot.plot(self.timeData[a:], self.phaseErrorData[a:])

    def zeroTime(self):
        self.time_offset = time.clock()
        self.timeData = self.timeData - self.timeData[-1]
        self.plotPlots()

    def setPlotTime(self, num):
        self.plotTimeRange = 30 + num
        self.lcdNumber.display(self.plotTimeRange)
        self.plotPlots()
            
    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous 
    # delay that allows other labrad / pyqt methods to run   
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d