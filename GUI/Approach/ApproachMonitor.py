import sys
from PyQt5 import QtGui, QtWidgets, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import time
import pyqtgraph as pg
import numpy as np
from .DetachableTabWidget import DetachableTabWidget

path = sys.path[0] + r"\Approach"
ApproachMonitorUI, QtBaseClass = uic.loadUiType(path + r"\ApproachMonitor.ui")

class Window(QtWidgets.QMainWindow, ApproachMonitorUI):

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)

        #setup UI elements that cannot be done through QT designer
        self.setupAdditionalUi()

        #move to default location
        self.moveDefault()

        #t=0 time in plots
        self.time_offset = 0

        #initiallize empty np arrays for data to be plotted.
        #Right now, these grow infinitely large. Maybe worth
        #limiting their size at some point
        self.pllTimeData = np.array([])
        self.deltaFData = np.array([])
        self.phaseErrorData = np.array([])

        self.aux2TimeData = np.array([])
        self.aux2Data = np.array([])

        self.zTimeData = np.array([])
        self.zCoarseTimeData = np.array([])
        self.zData = np.array([])
        self.zCoarseData = np.array([])

        #Time range to plot
        self.plotTimeRange = 30

        #When the following is true, the code sets self.time_offset = time.clock.
        #This only occurs for the first datapoint sent to this module
        self.first_data_point = True

        #super secret counter for super secret reasons
        self.counter = 0

        #Connect GUI elements to appropriate functions
        self.push_zeroTime.clicked.connect(self.zeroTime)
        self.horizontalSlider.valueChanged[int].connect(self.setPlotTime)

    def moveDefault(self):
        self.move(550,10)
        self.resize(600,500)

    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer. Initializes detachable tabs
        #that can be dragged around and adds plots to them setting the axes labels properly.
        self.dTabWidget = DetachableTabWidget()
        style = '''QTabWidget::pane { border: 0; }
                    QTabBar::tab{background: black;
                    color: rgb(168,168,168);
                    }
                    QTabBar::tab:selected {background: rgb(50,50,50);}
                    '''
        self.dTabWidget.setStyleSheet(style)

        self.centralwidget.layout().addWidget(self.dTabWidget)

        self.deltaFPlot = pg.PlotWidget(parent = self)
        self.deltaFPlot.setLabel('left', 'Delta F', units = 'Hz')
        self.deltaFPlot.setLabel('bottom', 'Time', units = 's')
        self.deltaFPlot.showAxis('right', show = True)
        self.deltaFPlot.showAxis('top', show = True)
        self.deltaFPlot.setTitle('PLL Delta F vs. Time (s)')
        self.phaseErrorPlot = pg.PlotWidget(parent = self)
        self.phaseErrorPlot.setLabel('left', 'Phase Error', units = '\N{DEGREE SIGN}')
        self.phaseErrorPlot.setLabel('bottom', 'Time', units = 's')
        self.phaseErrorPlot.showAxis('right', show = True)
        self.phaseErrorPlot.showAxis('top', show = True)
        self.phaseErrorPlot.setTitle('PLL Error vs. Time (s)')
        tab1 = QtWidgets.QWidget()
        tab1_layout = QtWidgets.QVBoxLayout()
        tab1_layout.addWidget(self.deltaFPlot)
        tab1_layout.addWidget(self.phaseErrorPlot)
        tab1.setLayout(tab1_layout)
        self.dTabWidget.addTab(tab1, 'PLL Monitor')

        self.zPlot = pg.PlotWidget(parent = self)
        self.zPlot.setLabel('left', 'Atto. Z Extension', units = 'm')
        self.zPlot.setLabel('bottom', 'Time', units = 's')
        self.zPlot.showAxis('right', show = True)
        self.zPlot.showAxis('top', show = True)
        self.zPlot.setTitle('Atto. Z Extension (m) vs. Time (s)')
        tab2 = QtWidgets.QWidget()
        tab2_layout = QtWidgets.QVBoxLayout()
        tab2_layout.addWidget(self.zPlot)
        tab2.setLayout(tab2_layout)
        self.dTabWidget.addTab(tab2, 'Z Monitor')

        self.aux2Plot = pg.PlotWidget(parent = self)
        self.aux2Plot.setLabel('left', 'Aux 2 Input', units = 'V')
        self.aux2Plot.setLabel('bottom', 'Time', units = 's')
        self.aux2Plot.showAxis('right', show = True)
        self.aux2Plot.showAxis('top', show = True)
        self.aux2Plot.setTitle('Aux 2 Input vs. Time (s)')
        tab3 = QtWidgets.QWidget()
        tab3_layout = QtWidgets.QVBoxLayout()
        tab3_layout.addWidget(self.aux2Plot)
        tab3.setLayout(tab3_layout)
        self.dTabWidget.addTab(tab3, 'Aux Input Monitor')
        
        self.ZCoarsePlot = pg.PlotWidget(parent = self)
        self.ZCoarsePlot.setLabel('left', 'Z Coarse Positioner', units = 'm')
        self.ZCoarsePlot.setLabel('bottom', 'Time', units = 's')
        self.ZCoarsePlot.showAxis('right', show = True)
        self.ZCoarsePlot.showAxis('top', show = True)
        self.ZCoarsePlot.setTitle('Z Coarse Positioner (m) vs. Time (s)')
        tab4 = QtWidgets.QWidget()
        tab4_layout = QtWidgets.QVBoxLayout()
        tab4_layout.addWidget(self.ZCoarsePlot)
        tab4.setLayout(tab4_layout)
        self.dTabWidget.addTab(tab4, 'Z Coarse Positioner Monitor')

        self.zPlaceholder.close()
        self.aux2Placeholder.close()
        self.deltaFPlaceholder.close()
        self.phasePlaceholder.close()
        self.ZcoarsePlaceholder.close()
        self.tabWidget.close()

    def updatePLLPlots(self, deltaF, phaseError):
        # Updates the PLL plots with new deltaF and phaseError datapoints received from the approach module
        if self.first_data_point:
            self.time_offset = time.time()
            self.first_data_point = False

        timepoint = time.time() - self.time_offset

        self.pllTimeData = np.append(self.pllTimeData, timepoint)
        self.deltaFData = np.append(self.deltaFData, deltaF)
        self.phaseErrorData = np.append(self.phaseErrorData, phaseError)

        #The module plots at most 3 hours worth of data. If more than that is stored, shorten the data list
        if self.pllTimeData[-1] - self.pllTimeData[0] > 10800:
            a = np.argmin(np.abs(self.pllTimeData - (self.pllTimeData[-1] - 10800)))
            self.pllTimeData = self.pllTimeData[a:]
            self.deltaFData = self.deltaFData[a:]
            self.phaseErrorData = self.phaseErrorData[a:]

        self.plotPLL()

    def updateAux2Plot(self,volts):
        # Updates the Aux input 2 plots with voltage datapoints received from the approach module
        if self.first_data_point:
            self.time_offset = time.time()
            self.first_data_point = False

        timepoint = time.time() - self.time_offset

        self.aux2TimeData = np.append(self.aux2TimeData, timepoint)
        self.aux2Data = np.append(self.aux2Data, volts)

        #The module plots at most 3 hours worth of data. If more than that is stored, shorten the data list
        if self.aux2TimeData[-1] - self.aux2TimeData[0] > 10800:
            a = np.argmin(np.abs(self.aux2TimeData - (self.aux2TimeData[-1] - 10800)))
            self.aux2TimeData = self.aux2TimeData[a:]
            self.aux2Data = self.aux2Data[a:]

        self.plotAux2()

    def updateZPlot(self,z_meters):
        # Updates the z extension plots with datapoints received from the approach module
        if self.first_data_point:
            self.time_offset = time.time()
            self.first_data_point = False

        timepoint = time.time() - self.time_offset

        self.zTimeData = np.append(self.zTimeData, timepoint)
        self.zData = np.append(self.zData, z_meters)

        #The module plots at most 3 hours worth of data. If more than that is stored, shorten the data list
        if self.zTimeData[-1] - self.zTimeData[0] > 10800:
            a = np.argmin(np.abs(self.zTimeData - (self.zTimeData[-1] - 10800)))
            self.zTimeData = self.zTimeData[a:]
            self.zData = self.zData[a:]

        self.plotZ()
    
    def updateZCoarsePlot(self,z_meters):
        # Updates the z extension plots with datapoints received from the approach module
        if self.first_data_point:
            self.time_offset = time.time()
            self.first_data_point = False

        timepoint = time.time() - self.time_offset

        self.zCoarseTimeData = np.append(self.zCoarseTimeData, timepoint)
        self.zCoarseData = np.append(self.zCoarseData, z_meters)

        #The module plots at most 3 hours worth of data. If more than that is stored, shorten the data list
        if self.zCoarseTimeData[-1] - self.zCoarseTimeData[0] > 10800:
            a = np.argmin(np.abs(self.zCoarseTimeData - (self.zCoarseTimeData[-1] - 10800)))
            self.zCoarseTimeData = self.zCoarseTimeData[a:]
            self.zCoarseData = self.zCoarseData[a:]

        self.plotZCoarse()

    def plotPlots(self):
        #Refresh all the plots
        self.plotPLL()
        self.plotAux2()
        self.plotZ()
        self.plotZCoarse()

    def plotPLL(self):
        #Refresh the PLL plots
        length = len(self.pllTimeData)
        if length > 1:
            #Plot all datapoints if they occured in less time than the specified plotTimeRange
            if (self.pllTimeData[-1] - self.pllTimeData[0]) <= self.plotTimeRange:
                self.deltaFPlot.clear()
                self.deltaFPlot.plot(self.pllTimeData, self.deltaFData)
                self.phaseErrorPlot.clear()
                self.phaseErrorPlot.plot(self.pllTimeData, self.phaseErrorData)
            #Otherwise only plot those that occurred in the specified plotTimeRange
            else:
                a = np.argmin(np.abs(self.pllTimeData - (self.pllTimeData[-1] - self.plotTimeRange)))
                self.deltaFPlot.clear()
                self.deltaFPlot.plot(self.pllTimeData[a:], self.deltaFData[a:])
                self.phaseErrorPlot.clear()
                self.phaseErrorPlot.plot(self.pllTimeData[a:], self.phaseErrorData[a:])

    def plotAux2(self):
        #Refresh the Aux 2 plot
        length = len(self.aux2TimeData)
        if length > 1:
            #Plot all datapoints if they occured in less time than the specified plotTimeRange
            if (self.aux2TimeData[-1] - self.aux2TimeData[0]) <= self.plotTimeRange:
                self.aux2Plot.clear()
                self.aux2Plot.plot(self.aux2TimeData, self.aux2Data)
            #Otherwise only plot those that occurred in the specified plotTimeRange
            else:
                a = np.argmin(np.abs(self.aux2TimeData - (self.aux2TimeData[-1] - self.plotTimeRange)))
                self.aux2Plot.clear()
                self.aux2Plot.plot(self.aux2TimeData[a:], self.aux2Data[a:])

    def plotZ(self):
        #Refresh the z extension plot
        length = len(self.zTimeData)
        if length > 1:
            #Plot all datapoints if they occured in less time than the specified plotTimeRange
            if (self.zTimeData[-1] - self.zTimeData[0]) <= self.plotTimeRange:
                self.zPlot.clear()
                self.zPlot.plot(self.zTimeData, self.zData)
            #Otherwise only plot those that occurred in the specified plotTimeRange
            else:
                a = np.argmin(np.abs(self.zTimeData - (self.zTimeData[-1] - self.plotTimeRange)))
                self.zPlot.clear()
                self.zPlot.plot(self.zTimeData[a:], self.zData[a:])
    
    def plotZCoarse(self):
        #Refresh the z extension plot
        length = len(self.zCoarseTimeData)
        if length > 1: #Plot all datapoints if they occured in less time than the specified plotTimeRange
            if (self.zCoarseTimeData[-1] - self.zCoarseTimeData[0]) <= self.plotTimeRange:
                self.ZCoarsePlot.clear()
                self.ZCoarsePlot.plot(self.zCoarseTimeData, self.zCoarseData)
            else: #Otherwise only plot those that occurred in the specified plotTimeRange
                a = np.argmin(np.abs(self.zCoarseTimeData - (self.zCoarseTimeData[-1] - self.plotTimeRange)))
                self.ZCoarsePlot.clear()
                self.ZCoarsePlot.plot(self.zCoarseTimeData[a:], self.zCoarseData[a:])

    def zeroTime(self):
        #Get the time relative to the offset when the function is run
        timepoint = time.time() - self.time_offset

        #super secret code
        if timepoint < 0.25:
            self.counter = self.counter + 1
            if self.counter >= 2:
                self.flashSQUID()
        else:
            self.counter = 0

        #Shift all the time data to be zero at the current time point
        if len(self.pllTimeData) > 0:
            self.pllTimeData = self.pllTimeData - timepoint
        if len(self.aux2TimeData) > 0:
            self.aux2TimeData = self.aux2TimeData - timepoint
        if len(self.zTimeData) > 0:
            self.zTimeData = self.zTimeData - timepoint
        if len(self.zCoarseTimeData) > 0:
            self.zCoarseTimeData = self.zCoarseTimeData - timepoint

        #Set the current time to be the new offset
        self.time_offset = time.time()

        #Update all the plots
        self.plotPlots()

    def setPlotTime(self, num):
        #Changes the plotTimeRange and updates the plots when changed
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
        #super secret
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
