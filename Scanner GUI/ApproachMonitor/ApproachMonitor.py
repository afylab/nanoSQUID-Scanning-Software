import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import time
import pyqtgraph as pg
import numpy as np

path = sys.path[0] + r"\ApproachMonitor"
ApproachMonitorUI, QtBaseClass = uic.loadUiType(path + r"\ApproachMonitor.ui")

class Window(QtGui.QMainWindow, ApproachMonitorUI):
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()   

        self.time_offset = 0    
        self.pllTimeData = np.array([])
        self.deltaFData = np.array([])
        self.phaseErrorData = np.array([])

        self.dcTimeData = np.array([])
        self.dcData = np.array([])
        
        self.acTimeData = np.array([])
        self.acData = np.array([])
        
        self.zTimeData = np.array([])
        self.zData = np.array([])
        
        self.plotTimeRange = 30

        self.counter = 0
        
        self.push_zeroTime.clicked.connect(self.zeroTime)
        #Requires no labrad connections
        
        self.horizontalSlider.valueChanged[int].connect(self.setPlotTime)

        self.first_data_point = True
        
    def moveDefault(self):    
        self.move(550,10)
        self.resize(600,500)
            
    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        self.deltaFPlot = pg.PlotWidget(parent = self)
        self.deltaFPlot.setLabel('left', 'Delta F', units = 'Hz')
        self.deltaFPlot.setLabel('bottom', 'Time', units = 's')
        self.deltaFPlot.showAxis('right', show = True)
        self.deltaFPlot.showAxis('top', show = True)
        self.deltaFPlot.setTitle('PLL Delta F vs. Time (s)')

        self.phaseErrorPlot = pg.PlotWidget(parent = self)
        self.phaseErrorPlot.setLabel('left', 'Phase Error', units = u'\N{DEGREE SIGN}')
        self.phaseErrorPlot.setLabel('bottom', 'Time', units = 's')
        self.phaseErrorPlot.showAxis('right', show = True)
        self.phaseErrorPlot.showAxis('top', show = True)
        self.phaseErrorPlot.setTitle('PLL Error vs. Time (s)')
        
        self.tab.layout().addWidget(self.deltaFPlot)
        self.tab.layout().addWidget(self.phaseErrorPlot)
        
        self.deltaFPlaceholder.close()
        self.phasePlaceholder.close()
        
        self.fdbkDCPlot = pg.PlotWidget(parent = self)
        self.fdbkDCPlot.setLabel('left', 'Feedback DC', units = 'V')
        self.fdbkDCPlot.setLabel('bottom', 'Time', units = 's')
        self.fdbkDCPlot.showAxis('right', show = True)
        self.fdbkDCPlot.showAxis('top', show = True)
        self.fdbkDCPlot.setTitle('Feedback DC vs. Time (s)')

        self.fdbkACPlot = pg.PlotWidget(parent = self)
        self.fdbkACPlot.setLabel('left', 'Feedback AC', units = 'V')
        self.fdbkACPlot.setLabel('bottom', 'Time', units = 's')
        self.fdbkACPlot.showAxis('right', show = True)
        self.fdbkACPlot.showAxis('top', show = True)
        self.fdbkACPlot.setTitle('Feedback AC vs. Time (s)')
        
        self.tab_2.layout().addWidget(self.fdbkDCPlot)
        self.tab_2.layout().addWidget(self.fdbkACPlot)
        
        self.dcPlaceholder.close()
        self.acPlaceholder.close()
        
        self.zPlot = pg.PlotWidget(parent = self)
        self.zPlot.setGeometry(15,40,641,271)
        self.zPlot.setLabel('left', 'Attocube Z Extension', units = 'm')
        self.zPlot.setLabel('bottom', 'Time', units = 's')
        self.zPlot.showAxis('right', show = True)
        self.zPlot.showAxis('top', show = True)
        self.zPlot.setTitle('Attocube Z Extension (m) vs. Time (s)')
        
        self.tab_3.layout().addWidget(self.zPlot)
        
        self.zPlaceholder.close()
        
    def updatePLLPlots(self, deltaF, phaseError):
        if self.first_data_point:
            self.time_offset = time.clock()
            self.first_data_point = False

        timepoint = time.clock() - self.time_offset

        self.pllTimeData = np.append(self.pllTimeData, timepoint)
        self.deltaFData = np.append(self.deltaFData, deltaF)
        self.phaseErrorData = np.append(self.phaseErrorData, phaseError)
        self.plotPLL()
        
    def updateFdbkDCPlot(self,dc):
        if self.first_data_point:
            self.time_offset = time.clock()
            self.first_data_point = False

        timepoint = time.clock() - self.time_offset

        self.dcTimeData = np.append(self.dcTimeData, timepoint)
        self.dcData = np.append(self.dcData, dc)
        self.plotFdbkDC()
        
    def updateFdbkACPlot(self,ac):
        if self.first_data_point:
            self.time_offset = time.clock()
            self.first_data_point = False

        timepoint = time.clock() - self.time_offset
        
        self.acTimeData = np.append(self.acTimeData, timepoint)
        self.acData = np.append(self.acData, ac)
        self.plotFdbkAC()
        
    def updateZPlot(self,z_meters):
        if self.first_data_point:
            self.time_offset = time.clock()
            self.first_data_point = False

        timepoint = time.clock() - self.time_offset
        
        self.zTimeData = np.append(self.zTimeData, timepoint)
        self.zData = np.append(self.zData, z_meters)
        self.plotZ()
        
    def plotPlots(self):
        self.plotPLL()
        self.plotFdbkDC()
        self.plotFdbkAC()
        self.plotZ()
        
    def plotPLL(self):
        length = len(self.pllTimeData)
        if length > 1:
            if (self.pllTimeData[length-1] - self.pllTimeData[0]) <= self.plotTimeRange:
                self.deltaFPlot.clear()
                self.deltaFPlot.plot(self.pllTimeData, self.deltaFData)
                self.phaseErrorPlot.clear()
                self.phaseErrorPlot.plot(self.pllTimeData, self.phaseErrorData)
            else:
                a = np.argmin(np.abs(self.pllTimeData - (self.pllTimeData[length-1] - self.plotTimeRange)))
                self.deltaFPlot.clear()
                self.deltaFPlot.plot(self.pllTimeData[a:], self.deltaFData[a:])
                self.phaseErrorPlot.clear()
                self.phaseErrorPlot.plot(self.pllTimeData[a:], self.phaseErrorData[a:])

    def plotFdbkDC(self):
        length = len(self.dcTimeData)
        if length > 1:
            if (self.dcTimeData[length-1] - self.dcTimeData[0]) <= self.plotTimeRange:
                self.fdbkDCPlot.clear()
                self.fdbkDCPlot.plot(self.dcTimeData, self.dcData)
            else:
                a = np.argmin(np.abs(self.dcTimeData - (self.dcTimeData[length-1] - self.plotTimeRange)))
                self.fdbkDCPlot.clear()
                self.fdbkDCPlot.plot(self.dcTimeData[a:], self.dcData[a:])
    
    def plotFdbkAC(self):
        length = len(self.acTimeData)
        if length > 1:
            if (self.acTimeData[length-1] - self.acTimeData[0]) <= self.plotTimeRange:
                self.fdbkACPlot.clear()
                self.fdbkACPlot.plot(self.acTimeData, self.acData)
            else:
                a = np.argmin(np.abs(self.acTimeData - (self.acTimeData[length-1] - self.plotTimeRange)))
                self.fdbkACPlot.clear()
                self.fdbkACPlot.plot(self.acTimeData[a:], self.acData[a:])
                
    def plotZ(self):
        length = len(self.zTimeData)
        if length > 1:
            if (self.zTimeData[length-1] - self.zTimeData[0]) <= self.plotTimeRange:
                self.zPlot.clear()
                self.zPlot.plot(self.zTimeData, self.zData)
            else:
                a = np.argmin(np.abs(self.zTimeData - (self.zTimeData[length-1] - self.plotTimeRange)))
                self.zPlot.clear()
                self.zPlot.plot(self.zTimeData[a:], self.zData[a:])
    
    def zeroTime(self):
        curr_time = time.clock()
        if curr_time - self.time_offset < 0.25:
            self.counter = self.counter + 1
            if self.counter >= 2:
                self.flashSQUID()
        else:
            self.counter = 0
            
        self.time_offset = time.clock()
        if len(self.pllTimeData) > 0:
            self.pllTimeData = self.pllTimeData - self.pllTimeData[-1]
        if len(self.dcTimeData) > 0:
            self.dcTimeData = self.dcTimeData - self.dcTimeData[-1]
        if len(self.acTimeData) > 0:
            self.acTimeData = self.acTimeData - self.acTimeData[-1]
        if len(self.zTimeData) > 0:
            self.zTimeData = self.zTimeData - self.zTimeData[-1]
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
        
    @inlineCallbacks
    def flashSQUID(self):
        style = '''
                QPushButton#push_zeroTime{
                image:url(:/nSOTScanner/Pictures/SQUIDRotated.png);
                background:black;
                }
                '''
        self.push_zeroTime.setStyleSheet(style)
        
        yield self.sleep(1)
    
        style = '''QPushButton:pressed#push_zeroTime{
                color: rgb(168,168,168);
                background-color:rgb(95,107,166);
                border: 1px solid rgb(168,168,168);
                border-radius: 5px
                }

                QPushButton#push_zeroTime{
                color: rgb(168,168,168);
                background-color:rgb(0,0,0);
                border: 1px solid rgb(168,168,168);
                border-radius: 5px
                }
                '''
        self.push_zeroTime.setStyleSheet(style)
        
        
        
        