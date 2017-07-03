from __future__ import division
from lanczos import deriv
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
from numpy.fft import rfft
from numpy import argmax, log, mean
from scipy import signal, stats
from scipy.signal import butter, lfilter, freqz
import pyqtgraph as pg
import exceptions
import time
import threading
import copy
import csv
import time
import dirExplorer
    
path = sys.path[0] + r"\Plotter"
#Ui_dvExplorer, QtBaseClass = uic.loadUiType(path + r"\dvExplorer.ui")
#Ui_EditDataInfo, QtBaseClass = uic.loadUiType(path + r"\editDatasetInfo.ui")

Ui_AxesSelect, QtBaseClass = uic.loadUiType(path + r"\axesSelect.ui")
Ui_Plotter, QtBaseClass = uic.loadUiType(path + r"\plotter.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

class Plotter(QtGui.QMainWindow, Ui_Plotter):
    def __init__(self, reactor, parent = None):
        super(Plotter, self).__init__(parent)
        
        self.parent = parent
        self.reactor = reactor
        self.setupUi(self)

        self.showGrad.hide()
        self.diamCalc.setIcon(QtGui.QIcon("diameter.png"))

        self.setupPlots()

        self.hideGrad.clicked.connect(self.shrink)
        self.showGrad.clicked.connect(self.enlarge)

        self.plotOptions.currentIndexChanged.connect(self.changePlot)

        self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        
        self.diamCalc.clicked.connect(self.calculateDiam)
        self.browse.clicked.connect(self.browseDV)
        self.addPlot.clicked.connect(self.newPlot)
        self.vCutPos.valueChanged.connect(self.changeVertLine)
        self.hCutPos.valueChanged.connect(self.changeHorLine)
        
        self.push_Servers.clicked.connect(self.showServersList)

        self.Data = None
        self.dv = None
        self.cxn = None
        self.file = None
        self.directory = None
        self.numPlots = 0
        
    def moveDefault(self):
        self.move(550,10)

    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.dv = dict['dv']
            
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            
        if self.dv is None:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            
    def disconnectLabRAD(self):
        self.dv = None
        self.cxn = None
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()

    def browseDV(self):
        self.dvExplorer = dirExplorer.dataVaultExplorer(self.dv, self.reactor)
        self.dvExplorer.show()
        self.dvExplorer.accepted.connect(lambda: self.loadData(self.reactor))

    @inlineCallbacks
    def loadData(self, c):
        try:
            result = self.dvExplorer.dirFileVars()
            print result
            self.file = result[0]
        except:
            self.file = self.dvExplorer.file
            print self.file
        t = time.time()
        yield self.dv.open(self.file)
        self.dataName = yield self.dv.get_name()
        self.dataVars = yield self.dv.variables()
        print 'opened set'
        t1 = time.time()
        print t1 - t
        self.Data = yield self.dv.get()
        print 'got set'
        t = time.time()
        print t - t1
        #Grabs first and last data points to find min and max values
        self.bMax = self.Data[-1][2] #max(x[2] for x in self.Data)
        self.bMin =  self.Data[0][2] #min(x[2] for x in self.Data)
        self.vMax = self.Data[-1][3] #max(x[3] for x in self.Data)
        self.vMin = self.Data[0][3] #min(x[3] for x in self.Data)
        self.Data = np.asarray(self.Data)
        print 'calc params'
        t1 = time.time()
        print t1 - t
        self.bPoints = int(self.Data[-1][0]) + 1
        self.vPoints = int(self.Data[-1][1]) + 1
        self.extent = [self.bMin, self.bMax, self.vMin, self.vMax]
        self.deltaV = float((self.vMax - self.vMin) / self.vPoints)
        self.deltaB = float((self.bMax - self.bMin) / self.bPoints)
        self.x0, self.x1 = (self.extent[0], self.extent[1])
        self.y0, self.y1 = (self.extent[2], self.extent[3])
        self.xscale, self.yscale = (self.x1-self.x0) / self.bPoints, (self.y1-self.y0) / self.vPoints
        print self.bMin, self.bMax, self.vMin, self.vMax, self.bPoints, self.vPoints
        print self.Data[0][2], self.Data[-1][2], self.Data[0][3], self.Data[-1][3]
        self.plotData = np.empty([self.bPoints, self.vPoints])
        print 'made empty matrix'
        t = time.time()
        print t - t1
        for i in self.Data:
            self.plotData[int(i[0]), int(i[1])] = i[4]
        print 'reformed data' 
        t1 = time.time()
        print t1 - t
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        print 'plotted'
        t = time.time()
        print t - t1
        self.vLine.setValue(self.bMin)
        self.hLine.setValue(self.vMin)

    def rectCoords(self):
        bounds = self.rect.parentBounds()
        print self.rect.parentBounds()

        x1 = int((bounds.x() - self.bMin) / self.xscale)
        y1 = int((bounds.y() - self.vMin) / self.yscale)
        x2 = int((bounds.x() + bounds.width() - self.bMin) / self.xscale)
        y2 = int((bounds.y() + bounds.height() - self.vMin) / self.yscale)
        print x1, y1, x2, y2
        dataSubSet = self.plotData[x1:x2, y1:y2]
        t = time.time()
        h = self.bPoints / (self.bMax - self.bMin)
        f = np.array([])
        for i in range(0, dataSubSet.shape[1]):
            spect, freq = signal.welch(dataSubSet[:,i], h, nperseg = dataSubSet.shape[0])
            peak = argmax(freq)
            max_f = spect[peak]
            f = np.append(f, max_f)
        f = stats.mode(f)[0]
        phi_0 = 2.0678338e-15
        print 2 * np.sqrt(phi_0 * f / np.pi)
        t1 = time.time()
        print t1 - t

        width = np.linspace(.01 * h, .1 * h, num = 10)
        f = np.array([])
        for i in range(0, dataSubSet.shape[1]):
            peaks = signal.find_peaks_cwt(dataSubSet[:,i], width)
            if len(peaks) > 1:
                f = np.append(f, np.round(np.diff(peaks), decimals = 4))

        free = stats.mode(f)[0]
        print 2 * np.sqrt((h * phi_0 ) / (np.pi * free))
        t2 = time.time()
        print t2 - t1

        dat = np.array([])
        
        dMin = np.amin(dataSubSet[:,0])
        vals = np.linspace(0, + dMin, num = 200)
        for i in range(0, len(vals)):
            line = dataSubSet[:,0] - vals[i]
            cross = np.where(np.diff(np.signbit(line)))[0]
            if len(cross) > 2:
                cross = np.asarray([cross[i+2] - cross[i] for i in range(0, 1)])
                dat = np.append(dat, cross[cross>1])
                print 'added'
            else:
                pass
        dat = dat / h	
        print dat[dat>.01]
        free = stats.mode(dat)[0]
        print 2 * np.sqrt(( phi_0 ) / (np.pi * free))
        t3 = time.time()
        print t3 - t2

        
    def setupPlots(self):
        #plotData = self.Data
        #self.plotData =plotData
        self.vLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.viewBig = pg.PlotItem(name = "Plot")
        self.viewBig.setLabel('left', text='Bias Voltage', units = 'V')
        self.viewBig.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.viewBig.showAxis('top', show = True)
        self.viewBig.showAxis('right', show = True)
        self.viewBig.setAspectLocked(lock = False, ratio = 1)
        self.mainPlot = pg.ImageView(parent = self.mainPlotArea, view = self.viewBig)
        self.mainPlot.setGeometry(QtCore.QRect(0, 0, 750, 450))
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.mainPlot.ui.roiBtn.hide()
        self.mainPlot.ui.menuBtn.hide()
        self.viewBig.setAspectLocked(False)
        self.viewBig.invertY(False)
        self.viewBig.setXRange(-1.25, 1.25)
        self.viewBig.setYRange(-10, 10)

        self.viewBig.addItem(self.vLine, ignoreBounds = True)
        self.viewBig.addItem(self.hLine, ignoreBounds =True)


        self.viewSmallX = pg.PlotItem(name = "Current-Bias")
        self.XZPlot = pg.PlotWidget(parent = self.XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.setLabel('left', 'DC Volts', units = 'V')
        self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.YZPlotArea)
        self.YZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.YZPlot.setLabel('left', 'DC Volts', units = 'V')
        self.YZPlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.YZPlot.showAxis('right', show = True)
        self.YZPlot.showAxis('top', show = True)

    def calculateDiam(self):
        self.rect = pg.RectROI(((self.bMax + self.bMin) / 2, (self.vMax + self.vMin) / 2),((self.bMax - self.bMin) / 2, (self.vMax - self.vMin) / 2), movable = True)
        self.rect.addScaleHandle((1,1), (.5,.5), lockAspect = False)
        self.rect.sigRegionChangeFinished.connect(self.rectCoords)
        self.mainPlot.addItem(self.rect)

        #for i in range(0, self.Data.shape[1]):

    def shrink(self):
        self.mainPlot.ui.histogram.hide()
        self.hideGrad.hide()
        self.showGrad.show()
    def enlarge(self):
        self.mainPlot.ui.histogram.show()
        self.hideGrad.show()
        self.showGrad.hide()

    def changePlot(self):
        if self.plotOptions.currentIndex() == 0:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[4]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("DC Output vs Bias Voltage and Magnetic Field")
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 1:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[5]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("dI/dV vs Bias Voltage and Magnetic Field")
            self.XZPlot.setLabel('left', 'dI/dV', units = 'A/V')
            self.YZPlot.setLabel('left', 'dI/dV', units = 'A/V')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 2:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[4]
            bVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
            delta = abs(self.bMax - self.bMin) / self.bPoints
            N = int(self.bPoints / 10)
            t = time.time()
            for i in range(0, self.plotData.shape[1]):
                self.plotData[:, i] = deriv(self.plotData[:,i], bVals, N, delta)	
            t1 = time.time()
            print 'time to deriv '
            print t1 - t		
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            t = time.time()
            print 'time to plot'
            print t - t1
            self.plotTitle.setText("dV/dB vs Bias Voltage and Magnetic Field")
            self.XZPlot.setLabel('left', 'dV/dB', units = 'V/T')
            self.YZPlot.setLabel('left', 'dV/dB', units = 'V/T')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 3:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[6]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("Noise vs Bias Voltage and Magnetic Field")
            self.XZPlot.setLabel('left', 'Noise', units = 'V')
            self.YZPlot.setLabel('left', 'Noise', units = 'V')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 4:
            bVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
            delta = abs(self.bMax - self.bMin) / self.bPoints
            N = int(self.bPoints / 10)
            for i in range(0, self.plotData.shape[1]):
                self.plotData[:, i] = deriv(self.plotData[:,i], bVals, N, delta)
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = self.plotdata[int(i[0]), int(i[1])] / i[6]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("Sensitivity vs Bias Voltage and Magnetic Field")
            self.YZPlot.setLabel('left', 'Sensitivity', units = '1/T')
            self.YZPlot.setLabel('left', 'Sensitivity', units = '1/T')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")

        if self.vhSelect.currentIndex() == 0:
            self.updateXZPlot(self.hLine.value())
        elif self.vhSelect.currentIndex() == 1:
            self.updateYZPlot(self.vLine.value())

    def toggleBottomPlot(self):
        if self.vhSelect.currentIndex() == 0:
            pos = self.hLine.value()
            self.YZPlotArea.lower()
            #self.XZPlotArea._raise()
            self.updateXZPlot(pos)
        elif self.vhSelect.currentIndex() == 1:
            pos = self.vLine.value()
            self.XZPlotArea.lower()
            #self.YZPlotArea._raise()
            self.updateYZPlot(pos)            

    def changeVertLine(self):
        pos = self.vCutPos.value()
        self.vLine.setValue(pos)
        self.updateYZPlot(pos)
    def changeHorLine(self):
        pos = self.hCutPos.value()
        self.hLine.setValue(pos)
        self.updateXZPlot(pos)

    def updateVLineBox(self):
        pos = self.vLine.value()
        self.vCutPos.setValue(float(pos))
        self.updateYZPlot(pos)
    def updateHLineBox(self):
        pos = self.hLine.value()
        self.hCutPos.setValue(float(pos))
        self.updateXZPlot(pos)


    def updateXZPlot(self, pos):
        index = self.vhSelect.currentIndex()
        if index == 1:
            pass
        elif index == 0:
            self.XZPlot.clear()
            if pos > self.y1 or pos < self.y0:
                self.XZPlot.clear()
            else:
                p = int(abs((pos - self.y0)) / self.yscale)
                xVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
                yVals = self.plotData[:,p]
                self.XZPlot.plot(x = xVals, y = yVals, pen = 0.5)


    def updateYZPlot(self, pos):
        index = self.vhSelect.currentIndex()
        if index == 0:
            pass
        elif index == 1:
            self.YZPlot.clear()
            if pos > self.x1 or pos < self.x0:
                self.YZPlot.clear()
            else:
                p = int(abs((pos - self.x0)) / self.xscale)
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.plotData[p]
                self.YZPlot.plot(x = xVals, y = yVals, pen = 0.5)

    def newPlot(self):
        self.numPlots += 1
        self.newPlot = subPlot(self.reactor,self)
        self.newPlot.show()

    def closeEvent(self, e):
        pass
        
class selectPlotAxes(QtGui.QDialog, Ui_AxesSelect):
    def __init__(self, file, dv, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(selectPlotAxes, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        self.dv = dv
        self.file = file
        self.popVars(reactor)

        self.okAxes.clicked.connect(self.doneAxes)
        self.cancelAxes.clicked.connect(self.stopAxes)

    @inlineCallbacks
    def popVars(self, c):
        yield self.dv.open(self.file)
        variables = yield self.dv.variables()

        for i in variables[0]:
            self.xVars.addItem(str(i[0]))
            self.yVars.addItem(str(i[0]))
        for i in variables[1]:
            self.zVars.addItem(str(i[0]))

    def stopAxes(self):
        self.reject()
        #self.close()
    def doneAxes(self):
        self.accept()
        #self.close()
    def plotVars(self):
        xVar = self.xVars.currentIndex()
        yVar = self.yVars.currentIndex()
        zVar = self.zVars.currentIndex() + self.xVars.count()
        return [xVar, yVar, zVar]

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))

class subPlot(QtGui.QDialog, Ui_Plotter):
    def __init__(self, reactor,parent = None):
        super(subPlot, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.window = parent
        self.setWindowTitle('Subplot ' + str(self.window.numPlots))

        self.showGrad.hide()
        self.diamCalc.setIcon(QtGui.QIcon("diameter.png"))

        self.rect = pg.RectROI((0,0),(0.1,0.1), movable = True)
        self.rect.addScaleHandle((1,1), (.5,.5), lockAspect = False)
        self.rect.sigRegionChangeFinished.connect(self.rectCoords)

        self.setupPlots()
        self.hideGrad.clicked.connect(self.shrink)
        self.showGrad.clicked.connect(self.enlarge)

        self.plotOptions.currentIndexChanged.connect(self.changePlot)

        self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        
        self.diamCalc.clicked.connect(self.calculateDiam)
        self.browse.clicked.connect(self.browseDV)
        self.addPlot.clicked.connect(self.newPlot)
        self.vCutPos.valueChanged.connect(self.changeVertLine)
        self.hCutPos.valueChanged.connect(self.changeHorLine)

        self.Data = None
        self.file = None
        self.directory = None
        #self.cxn = self.window.cxn
        #self.dv = self.window.dv

    def browseDV(self):
        self.dvExplorer = dirExplorer.dataVaultExplorer(reactor)
        self.dvExplorer.show()
        if self.dvExplorer.exec_():
            self.loadData(reactor)

    @inlineCallbacks
    def loadData(self, c):
        try:
            self.dv = self.window.dv
            yield self.dv.open(self.window.file)
        except Exception as inst:
            print type(inst)
            print inst.args
            print inst
        self.Data = yield self.dv.get()
        print self.Data
        self.bMax = max(x[2] for x in self.Data)
        self.bMin =  min(x[2] for x in self.Data)
        self.vMax = max(x[3] for x in self.Data)
        self.vMin = min(x[3] for x in self.Data)
        self.bPoints = int(self.Data[-1][0]) + 1
        self.vPoints = int(self.Data[-1][1]) + 1
        self.extent = [self.bMin, self.bMax, self.vMin, self.vMax]
        self.deltaV = float((self.vMax - self.vMin) / self.vPoints)
        self.deltaB = float((self.bMax - self.bMin) / self.bPoints)
        self.x0, self.x1 = (self.extent[0], self.extent[1])
        self.y0, self.y1 = (self.extent[2], self.extent[3])
        self.xscale, self.yscale = (self.x1-self.x0) / self.bPoints, (self.y1-self.y0) / self.vPoints
        print self.bMin, self.bMax, self.vMin, self.vMax, self.bPoints, self.vPoints
        self.plotData = np.empty([self.bPoints, self.vPoints])
        for i in self.Data:
            self.plotData[int(i[0]), int(i[1])] = i[4]
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.vLine.setValue(self.bMin)
        self.hLine.setValue(self.vMin)

    def rectCoords(self):
        bounds = self.rect.parentBounds()
        print bounds
        x1 = self.extent[0] + bounds.topRight[0]*self.xscale
        y1 = self.extent[2] + bounds.topRight[1]*self.yscale
        x2 = self.extent[0] + bounds.bottomLeft[0]*self.xscale
        y2 = self.extent[2] + bounds.bottomLeft[1]*self.yscale 

    def setupPlots(self):
        #plotData = self.Data
        #self.plotData =plotData
        self.vLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.viewBig = pg.PlotItem(name = "Plot")
        self.viewBig.setLabel('left', text='Bias Voltage', units = 'V')
        self.viewBig.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.viewBig.showAxis('top', show = True)
        self.viewBig.showAxis('right', show = True)
        self.viewBig.setAspectLocked(lock = False, ratio = 1)
        self.mainPlot = pg.ImageView(parent = self.mainPlotArea, view = self.viewBig)
        self.mainPlot.setGeometry(QtCore.QRect(0, 0, 750, 450))
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.mainPlot.ui.roiBtn.hide()
        self.mainPlot.ui.menuBtn.hide()
        self.viewBig.setAspectLocked(False)
        self.viewBig.invertY(False)
        self.viewBig.setXRange(-1.25, 1.25)
        self.viewBig.setYRange(-10, 10)

        self.viewBig.addItem(self.vLine, ignoreBounds = True)
        self.viewBig.addItem(self.hLine, ignoreBounds =True)


        self.viewSmallX = pg.PlotItem(name = "Current-Bias")
        self.XZPlot = pg.PlotWidget(parent = self.XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.setLabel('left', 'DC Volts', units = 'V')
        self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.YZPlotArea)
        self.YZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.YZPlot.setLabel('left', 'DC Volts', units = 'V')
        self.YZPlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.YZPlot.showAxis('right', show = True)
        self.YZPlot.showAxis('top', show = True)

    def calculateDiam(self):
        self.viewBig.addItem(self.rect)

        #for i in range(0, self.Data.shape[1]):

    def shrink(self):
        self.mainPlot.ui.histogram.hide()
        self.hideGrad.hide()
        self.showGrad.show()
    def enlarge(self):
        self.mainPlot.ui.histogram.show()
        self.hideGrad.show()
        self.showGrad.hide()

    def changePlot(self):
        if self.plotOptions.currentIndex() == 0:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[4]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("DC Output vs Bias Voltage and Magnetic Field")
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 1:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[5]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("dI/dV vs Bias Voltage and Magnetic Field")
            self.XZPlot.setLabel('left', 'dI/dV', units = 'A/V')
            self.YZPlot.setLabel('left', 'dI/dV', units = 'A/V')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 2:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[4]
            bVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
            delta = abs(self.bMax - self.bMin) / self.bPoints
            N = int(self.bPoints / 10)
            for i in range(0, self.plotData.shape[1]):
                self.plotData[:, i] = deriv(self.plotData[:,i], bVals, N, delta)			
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("dV/dB vs Bias Voltage and Magnetic Field")
            self.XZPlot.setLabel('left', 'dV/dB', units = 'V/T')
            self.YZPlot.setLabel('left', 'dV/dB', units = 'V/T')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 3:
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = i[6]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("Noise vs Bias Voltage and Magnetic Field")
            self.XZPlot.setLabel('left', 'Noise', units = 'V')
            self.YZPlot.setLabel('left', 'Noise', units = 'V')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 4:
            bVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
            delta = abs(self.bMax - self.bMin) / self.bPoints
            N = int(self.bPoints / 10)
            for i in range(0, self.plotData.shape[1]):
                self.plotData[:, i] = deriv(self.plotData[:,i], bVals, N, delta)
            for i in self.Data:
                self.plotData[int(i[0]), int(i[1])] = self.plotdata[int(i[0]), int(i[1])] / i[6]
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("Sensitivity vs Bias Voltage and Magnetic Field")
            self.YZPlot.setLabel('left', 'Sensitivity', units = '1/T')
            self.YZPlot.setLabel('left', 'Sensitivity', units = '1/T')
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")

        if self.vhSelect.currentIndex() == 0:
            self.updateXZPlot(self.hLine.value())
        elif self.vhSelect.currentIndex() == 1:
            self.updateYZPlot(self.vLine.value())

    def toggleBottomPlot(self):
        if self.vhSelect.currentIndex() == 0:
            pos = self.hLine.value()
            self.YZPlotArea.lower()
            #self.XZPlotArea._raise()
            self.updateXZPlot(pos)
        elif self.vhSelect.currentIndex() == 1:
            pos = self.vLine.value()
            self.XZPlotArea.lower()
            #self.YZPlotArea._raise()
            self.updateYZPlot(pos)            

    def changeVertLine(self):
        pos = self.vCutPos.value()
        self.vLine.setValue(pos)
        self.updateYZPlot(pos)
    def changeHorLine(self):
        pos = self.hCutPos.value()
        self.hLine.setValue(pos)
        self.updateXZPlot(pos)

    def updateVLineBox(self):
        pos = self.vLine.value()
        self.vCutPos.setValue(float(pos))
        self.updateYZPlot(pos)
    def updateHLineBox(self):
        pos = self.hLine.value()
        self.hCutPos.setValue(float(pos))
        self.updateXZPlot(pos)


    def updateXZPlot(self, pos):
        index = self.vhSelect.currentIndex()
        if index == 1:
            pass
        elif index == 0:
            self.XZPlot.clear()
            if pos > self.y1 or pos < self.y0:
                self.XZPlot.clear()
            else:
                p = int(abs((pos - self.y0)) / self.yscale)
                xVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
                yVals = self.plotData[:,p]
                self.XZPlot.plot(x = xVals, y = yVals, pen = 0.5)


    def updateYZPlot(self, pos):
        index = self.vhSelect.currentIndex()
        if index == 0:
            pass
        elif index == 1:
            self.YZPlot.clear()
            if pos > self.x1 or pos < self.x0:
                self.YZPlot.clear()
            else:
                p = int(abs((pos - self.x0)) / self.xscale)
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.plotData[p]
                self.YZPlot.plot(x = xVals, y = yVals, pen = 0.5)

    def newPlot(self):
        self.window.numPlots += 1
        self.newPlot = subPlot(self)
        self.newPlot.show()

if __name__ == "__main__":
    app = QtGui.QApplication([])
    from qtreactor import pyqt4reactor
    pyqt4reactor.install()
    from twisted.internet import reactor
    window = Plotter(reactor)
    window.show()
    reactor.run()

'''
#Print Error
try:
    yield 'something'
except Exception as inst:
    print type(inst)
    print inst.args
    print inst
'''