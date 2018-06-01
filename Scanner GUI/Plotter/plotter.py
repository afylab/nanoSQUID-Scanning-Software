from __future__ import division
from lanczos import deriv
import os
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
from numpy.fft import rfft
from numpy import argmax, log, mean, c_
from scipy import signal, stats
from scipy.signal import butter, lfilter, freqz
import pyqtgraph as pg
import exceptions
import time
import threading
import copy
import time
import scipy.io as sio

path = sys.path[0] + r"\Plotter"

dirExplorerGUI = path + r"\dvExplorer.ui"
editDatasetInfoGUI = path + r"\editDatasetInfo.ui"
axesSelectGUI = path + r"\axesSelect.ui"
plotter = path + r"\plotter.ui"
sensitivityPrompt = path + r"\sensitivityPrompt.ui"
gradSettings = path + r"\gradSettings.ui"
zoomWindow = path + r"\zoomWindow.ui"

Ui_dvExplorer, QtBaseClass = uic.loadUiType(dirExplorerGUI)
Ui_EditDataInfo, QtBaseClass = uic.loadUiType(editDatasetInfoGUI)
Ui_Plotter, QtBaseClass = uic.loadUiType(plotter)
Ui_AxesSelect, QtBaseClass = uic.loadUiType(axesSelectGUI)
Ui_SensitivityPrompt, QtBaseClass = uic.loadUiType(sensitivityPrompt)
Ui_GradSet, QtBaseClass = uic.loadUiType(gradSettings)
Ui_ZoomWindow, QtBaseClass = uic.loadUiType(zoomWindow)

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class gradSet(QtGui.QDialog, Ui_GradSet):
    def __init__(self, reactor, dataPct):
        super(gradSet, self).__init__()
        
        self.reactor = reactor
        self.setupUi(self)
        self.dataPct = float(dataPct) * 100
        self.dataPercent.setValue(self.dataPct)
        self.okBtn.clicked.connect(self._ok)
        self.cancelBtn.clicked.connect(self._cancel)

    def _ok(self):
        self.accept()
    def _cancel(self):
        self.reject()
    def closeEvent(self, e):
        self.reject()




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

        l = len(self.indVars)
        if l % 2 == 0:
            for i in self.indVars[int(l / 2) : l]:
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




class Plotter(QtGui.QMainWindow, Ui_Plotter):
    def __init__(self, reactor, parent = None):
        super(Plotter, self).__init__()
        
        self.reactor = reactor
        self.setupUi(self)

        self.showGrad.hide()
        self.diamFrame.hide()
        self.trSelect.hide()


        self.setupPlots()


        self.hideGrad.clicked.connect(self.shrink)
        self.showGrad.clicked.connect(self.enlarge)

        self.refresh.setEnabled(False)
        self.diamCalc.setEnabled(False)
        self.gradient.setEnabled(False)
        self.subtract.setEnabled(False)
        self.sensitivity.setEnabled(False)
        self.zoom.setEnabled(False)
        

        
        self.saveMenu = QtGui.QMenu()
        twoDSave = QtGui.QAction("Save 2D plot", self)
        oneDSave = QtGui.QAction("Save line cut", self)
        oneDSave.triggered.connect(self.matLinePlot)
        twoDSave.triggered.connect(self.matPlot)
        self.saveMenu.addAction(twoDSave)
        self.saveMenu.addAction(oneDSave)
        self.savePlot.setMenu(self.saveMenu)


        self.gradMenu = QtGui.QMenu()
        gradX = QtGui.QAction(QtGui.QIcon("nablaXIcon.png"), "Gradient along x-axis", self)
        gradY = QtGui.QAction(QtGui.QIcon("nablaYIcon.png"), "Gradient along y-axis", self)
        lancSettings = QtGui.QAction("Gradient settings...", self)
        gradX.triggered.connect(self.xDeriv)
        gradY.triggered.connect(self.yDeriv)
        lancSettings.triggered.connect(self.derivSettings)
        self.gradMenu.addAction(gradX)
        self.gradMenu.addAction(gradY)
        self.gradMenu.addAction(lancSettings)
        self.gradient.setMenu(self.gradMenu)
        self.datPct = 0.1

        self.subtractMenu = QtGui.QMenu()
        subAvg = QtGui.QAction( "Subtract constant offset", self)
        subPlane = QtGui.QAction( "Subtract planar fit", self)
        subQuad = QtGui.QAction( "Subtract quadratic fit", self)
        subAvg.triggered.connect(self.subtractAvg)
        subPlane.triggered.connect(self.subtractPlane)
        subQuad.triggered.connect(self.subtractQuad)
        self.subtractMenu.addAction(subAvg)
        self.subtractMenu.addAction(subPlane)
        self.subtractMenu.addAction(subQuad)
        self.subtract.setMenu(self.subtractMenu)
        
        self.trSelectMenu = QtGui.QMenu()
        showTrace = QtGui.QAction("Plot Trace", self)
        showRetrace = QtGui.QAction("Plot Retrace", self)
        self.trSelectMenu.addAction(showTrace)
        self.trSelectMenu.addAction(showRetrace)
        showTrace.triggered.connect(self.plotTrace)
        showRetrace.triggered.connect(self.plotRetrace)
        self.trSelect.setMenu(self.trSelectMenu)


        self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        self.diamCalc.clicked.connect(self.calculateDiam)
        self.sensitivity.clicked.connect(self.promptSensitivity)
        self.zoom.clicked.connect(self.zoomArea)
        self.browse.clicked.connect(self.browseDV)
        self.refresh.clicked.connect(self.refreshPlot)
        self.addPlot.clicked.connect(self.newPlot)
        self.vCutPos.valueChanged.connect(self.changeVertLine)
        self.hCutPos.valueChanged.connect(self.changeHorLine)
        
        self.showGrad.hide()
        self.hideGrad.hide()

        self.Data = None
        self.plotData = None
        self.dv = None
        self.cxn = None
        self.file = None
        self.directory = None
        self.got_util = False
        self.numPlots = 0
        self.numZoomPlots = 0
        
        #self.findPathFunc(self.reactor)
        
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.dv = dict['dv']

            #self.push_Servers.setStyleSheet("#push_Servers{" + 
            #"background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
            pass
            #self.push_Servers.setStyleSheet("#push_Servers{" + 
            #"background: rgb(161, 0, 0);border-radius: 4px;}")
        if not self.cxn: 
            pass
            #self.push_Servers.setStyleSheet("#push_Servers{" + 
            #"background: rgb(161, 0, 0);border-radius: 4px;}")

        elif not self.dv:
            pass
            #self.push_Servers.setStyleSheet("#push_Servers{" + 
            #"background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
            pass
            #self.push_Servers.setStyleSheet("#push_Servers{" + 
            #"background: rgb(0, 170, 0);border-radius: 4px;}")

            
    def disconnectLabRAD(self):

        self.dv = False
        self.cxn = False

        #self.push_Servers.setStyleSheet("#push_Servers{" +  
            #"background: rgb(144, 140, 9);border-radius: 4px;}")
        
    def matLinePlot(self):
        if not self.plotData is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genLineMatFile(fold)
                
    def genLineMatFile(self, fold):
        yData = np.asarray(self.lineYVals)
        xData = np.asarray(self.lineXVals)
        
        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        print 'All data converted. Saving .mat file'
        sio.savemat(fold,{savename:matData})
        matData = None      

        
    def matPlot(self):
        if not self.plotData is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genMatFile(fold)

    def genMatFile(self, fold):
        t = time.time()
        xVals = np.linspace(self.xMin, self.xMax, int(self.xPoints))
        yVals = np.linspace(self.yMin, self.yMax, int(self.yPoints))
        xInd, yInd = np.linspace(0,  self.xPoints - 1,  int(self.xPoints)), np.linspace(0,  self.yPoints - 1, int(self.yPoints))

        zX, zY, zXI, zYI = np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)]), np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)])
        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.plotData.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        print time.time() - t
        savename = fold.split("/")[-1].split('.mat')[0]
        print savename
        print 'All data converted. Saving .mat file'
        sio.savemat(fold,{savename:matData})
        matData = None


    def moveDefault(self):
        self.move(550,10)
        

    def zoomArea(self):
        self.zoom.clicked.disconnect(self.zoomArea)
        self.zoom.clicked.connect(self.rmvZoomArea)
        xAxis = self.viewBig.getAxis('bottom')
        yAxis = self.viewBig.getAxis('left')
        a1, a2 = xAxis.range[0], xAxis.range[1]
        b1, b2 = yAxis.range[0], yAxis.range[1]
        self.zoomRect = pg.RectROI(((a2 + a1) / 2, (b2 + b1) / 2),((a2 - a1) / 2, (b2 - b1) / 2), movable = True)
        self.zoomRect.setAcceptedMouseButtons(QtCore.Qt.LeftButton | QtCore.Qt.RightButton)
        self.zoomRect.addScaleHandle((1,1), (.5,.5), lockAspect = False)
        self.zoomRect.sigClicked.connect(self.QMouseEvent)
        self.mainPlot.addItem(self.zoomRect)
    def rmvZoomArea(self):
        self.mainPlot.removeItem(self.zoomRect)
        self.zoom.clicked.connect(self.zoomArea)
    def QMouseEvent(self, thing, button):
        button = int(str(button)[-2])

        bounds = self.zoomRect.parentBounds()
        x1 = int((bounds.x() - self.xMin) / self.xscale)
        y1 = int((bounds.y() - self.yMin) / self.yscale)
        x2 = int((bounds.x() + bounds.width() - self.xMin) / self.xscale)
        y2 = int((bounds.y() + bounds.height() - self.yMin) / self.yscale)
        if button == 1:
            self.viewBig.setXRange(bounds.x(), bounds.x()+bounds.width())
            self.viewBig.setYRange(bounds.y(),bounds.y() + bounds.height())         
            self.mainPlot.removeItem(self.zoomRect)
            self.zoom.clicked.connect(self.zoomArea)
        elif button ==2:
            self.mainPlot.removeItem(self.zoomRect)
            self.zoom.clicked.connect(self.zoomArea)
            self.plotZoom = self.plotData[x1:x2, y1:y2]
            self.dataZoom = np.asarray([])
            self.indZoomVars = []
            self.depZoomVars = []
            for k in range(x1, x2):
                if len(self.dataZoom)==0:
                    self.dataZoom = self.Data[int(k*self.yPoints + y1) :int(k*self.yPoints + y2)]
                else:
                    self.dataZoom = np.vstack((self.dataZoom, self.Data[int(k*self.yPoints + y1) :int(k*self.yPoints + y2)]))
                
            
            for i in range(0, self.xAxis.count()):
                self.indZoomVars.append(self.xAxis.itemText(i))
            for i in range(0, self.zAxis.count()):
                self.depZoomVars.append(self.zAxis.itemText(i))
            title= str(self.plotTitle.text())
            self.indXVar, self.indYVar, self.depVar = self.xAxis.currentText(), self.yAxis.currentText(), self.zAxis.currentText()
            self.currentIndex = [self.xAxis.currentIndex(), self.yAxis.currentIndex(), self.zAxis.currentIndex()]       
            self.zoomExtent = [bounds.x(), bounds.x() + bounds.width(), bounds.y(), bounds.y() + bounds.height(), self.xscale, self.yscale]
            self.zoomPlot = zoomPlot(self.reactor, self.plotZoom, self.dataZoom, self.zoomExtent, self.indZoomVars, self.depZoomVars, self.currentIndex, title, self)
            self.zoom.setEnabled(False)
            self.zoomPlot.show()
            

            


    def promptSensitivity(self):
        self.sensPrompt = Sensitivity(self.depVars, self.indVars, self.reactor)
        self.sensPrompt.show()
        self.sensPrompt.accepted.connect(self.plotSens)
        print 'great'
    def plotSens(self):

        self.sensIndex = self.sensPrompt.sensIndicies()
        l = int(len(self.indVars) / 2)
        x = self.sensIndex[0]
        y = self.sensIndex[1]
        z = self.sensIndex[2] + len(self.indVars) 
        self.NSselect = self.sensIndex[4]
        self.unitSelect = self.sensIndex[5]
        self.xMax = np.amax(self.Data[::,l+x])
        self.xMin = np.amin(self.Data[::,l+x])
        self.yMax = np.amax(self.Data[::,l+y])
        self.yMin = np.amin(self.Data[::,l+y])
        self.deltaX = self.xMax - self.xMin
        self.deltaY = self.yMax - self.yMin
        self.xPoints = np.amax(self.Data[::,x])+1
        self.yPoints = np.amax(self.Data[::,y])+1
        self.extent = [self.xMin, self.xMax, self.yMin, self.yMax]
        self.x0, self.x1 = self.extent[0], self.extent[1]
        self.y0, self.y1 = self.extent[2], self.extent[3]
        self.xscale, self.yscale = (self.x1-self.x0) / self.xPoints, (self.y1-self.y0) / self.yPoints   
        n = self.sensIndex[3] + len(self.indVars)
        self.plotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        self.noiseData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = float(i[z])
            if i[n] != 0:
                self.noiseData[int(i[x]), int(i[y])] = float(i[n])
            else:
                self.noiseData[int(i[x]), int(i[y])] = 1e-5
        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.yPoints * self.datPct)


        for i in range(0, self.plotData.shape[1]):
            self.plotData[:, i] = deriv(self.plotData[:, i], xVals, N, delta)

        if self.NSselect == 1:
            self.plotData = np.absolute(np.true_divide(self.plotData , self.noiseData))
        else:
            self.plotData = np.absolute(np.true_divide(self.noiseData , self.plotData ))
            self.plotData = np.clip(self.plotData, 0, 1e3)

            
            if self.unitSelect == 2:
                gain, bw = self.sensPrompt.sensConv()[0], self.sensPrompt.sensConv()[1]
                self.plotData = np.true_divide(self.plotData, (gain * np.sqrt(1000 *bw)))
                self.plotData = np.clip(self.plotData, 0, 1e3)
                
        avg = np.average(self.plotData)
        std = np.std(self.plotData)

        self.mainPlot.setImage(self.plotData, autoRange = True , levels = (avg - std, avg+std), autoHistogramRange = False, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.mainPlot.addItem(self.vLine)
        self.mainPlot.addItem(self.hLine)
        self.vLine.setValue(self.xMin)
        self.hLine.setValue(self.yMin)  
        self.vCutPos.setValue(self.xMin)
        self.hCutPos.setValue(self.yMin)
        if self.NSselect == 1:
            self.plotType.setText('Plotted sensitivity.')
            self.vhSelect.addItem('Maximum Sensitivity')
        else:
            self.plotType.setText('Plotted field noise.')   
            self.vhSelect.addItem('Minimum Noise')
            self.vhSelect.addItem('Optimal Bias')
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()

    def plotMaxSens(self):
        if self.NSselect == 1:
            maxSens = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.plotData.shape[0]):
                maxSens = np.append(maxSens, np.amax(self.plotData[i]))
            self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.XZPlot.setLabel('left', 'Maximum Relative Sensitivity')
            self.XZPlot.plot(x = bVals, y = maxSens,pen = 0.5)
            self.lineYVals = maxSens
            self.lineXVals = bVals
        else:
            minNoise = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.plotData.shape[0]):
                minNoise = np.append(minNoise, np.amin(self.plotData[i]))
            self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.XZPlot.setLabel('left', 'Minimum field noise')
            self.XZPlot.plot(x = bVals, y = minNoise,pen = 0.5)
            self.lineYVals = minNoise
            self.lineXVals = bVals
            
    def plotOptBias(self):  
        minNoise = np.array([])
        bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
        vVals =np.linspace(self.yMin, self.yMax, self.yPoints)
        self.XZPlot.clear()
        for i in range(0, self.plotData.shape[0]):
            arg = np.argmin(self.plotData[i])
            minNoise = np.append(minNoise, vVals[arg])
        self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.XZPlot.setLabel('left', 'Optimal Bias', units = 'V')
        self.XZPlot.plot(x = bVals, y = minNoise,pen = 0.5)
        self.lineYVals = minNoise
        self.lineXVals = bVals

    def Ic_ParaRes(self):
        for i in self.Data:
            pass
        for i in range(0, self.plotData.shape[0]):
            V_raw = self.plotData[i]


        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        self.viewBig.setLabel('left', text=self.yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.xAxis.currentText())
        self.XZPlot.setLabel('left', self.zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.xAxis.currentText())
        self.YZPlot.setLabel('left', self.zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.yAxis.currentText())
        self.xMax = np.amax(self.Data[::,l+x])
        self.xMin = np.amin(self.Data[::,l+x])
        self.yMax = np.amax(self.Data[::,l+y])
        self.yMin = np.amin(self.Data[::,l+y])
        self.deltaX = self.xMax - self.xMin
        self.deltaY = self.yMax - self.yMin
        self.xPoints = np.amax(self.Data[::,x])+1
        self.yPoints = np.amax(self.Data[::,y])+1
        self.extent = [self.xMin, self.xMax, self.yMin, self.yMax]
        self.x0, self.x1 = self.extent[0], self.extent[1]
        self.y0, self.y1 = self.extent[2], self.extent[3]
        self.xscale, self.yscale = (self.x1-self.x0) / self.xPoints, (self.y1-self.y0) / self.yPoints   
        self.plotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = i[z]






    def xDeriv(self):
        if self.plotData is None:
            self.plotType.setText("Please plot data.")
            self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        else:
            self.gradient.setFocusPolicy(QtCore.Qt.StrongFocus)
            xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
            delta = abs(self.xMax - self.xMin) / self.xPoints
            N = int(self.xPoints * self.datPct)
            if N < 2:
                self.plotType.setText("Lanczos window too \nsmall.")
                self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")

            else:
                for i in range(0, self.plotData.shape[1]):
                    self.plotData[:, i] = deriv(self.plotData[:,i], xVals, N, delta)    
                self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                print '1'
                self.plotType.setText("Plotted gradient along \nx-axis.")
                self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
                print '2'
                self.clearPlots()
    def yDeriv(self):
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.yMax - self.yMin) / self.yPoints
        N = int(self.yPoints * self.datPct)
        for i in range(0, self.plotData.shape[0]):
            self.plotData[i, :] = deriv(self.plotData[i,:], yVals, N, delta)    
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted gradient along \ny-axis.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def derivSettings(self):
        self.gradSet = gradSet(self.reactor, self.datPct)
        self.gradSet.show()
        self.gradSet.accepted.connect(self.setLancWindow)
    def setLancWindow(self):
        self.datPct = self.gradSet.dataPercent.value() / 100

    def subtractAvg(self):
        avg = np.average(self.plotData)
        self.plotData = self.plotData - avg
        self.plotType.setText("Plotted offset \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractPlane(self):
        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        X = np.c_[self.Data[::, l+x], self.Data[::,l+y], np.ones(self.Data.shape[0])]
        Y = np.ndarray.flatten(self.plotData)
        
        #C = np.linalg.lstsq(X, self.Data[::,z])\
        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            #self.plotData[int(i[x]), int(i[y])] = i[z] - np.dot(C[0], [i[x+l], i[y+l], 1]) 
            self.plotData[int(i[x]), int(i[y])] = self.plotData[int(i[x]), int(i[y])] - np.dot(C[0], [i[x+l], i[y+l], 1])       
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted plane \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractQuad(self):
        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        X = np.c_[np.ones(self.Data.shape[0]), self.Data[::, [l+x, l+y]], np.prod(self.Data[::, [l+x, l+y]], axis = 1), self.Data[::, [l+x, l+y]]**2]
        Y = np.ndarray.flatten(self.plotData)
        #C = np.linalg.lstsq(X, self.Data[::,z])
        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = i[z] - np.dot(C[0], [i[x+l]**2, i[y+l]**2, i[l+x]*i[y+l], i[l+x], i[l+y], 1])     
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted quadratic \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()

    @inlineCallbacks
    def findPathFunc(self, c):
        '''
        from labrad.wrappers import connectAsync
        try:
            self.cxn  = yield connectAsync(name = 'name')
            self.dv = yield self.cxn.data_vault
            print 'connected'
        except:
            print 'Either no LabRad connection or DataVault connection.'
        import labrad.util
        '''
        print 'getting nodename'
        nodename = self.util.getNodeName()        
        self.reg = yield self.cxn.registry
        name = yield self.dv.name
        yield self.reg.cd('', 'Servers', name, 'Repository')
        self.os_path = yield self.reg.get(nodename)
        yield self.reg.cd('')
        print 'path found'
        yield self.openDVExplorerFunc(self.reactor)
    
    
    @inlineCallbacks
    def browseDV(self, c = None):
        print 'browser open init'
        if self.got_util == False:
            import labrad.util as util
            self.util = util
            yield self.sleep(3)
            self.got_util = True
        yield self.findPathFunc(self.reactor)

        
    @inlineCallbacks
    def openDVExplorerFunc(self, c):
        yield self.sleep(0.1)
        self.refresh.setEnabled(False)
        self.dvExplorer = dataVaultExplorer(self.dv, self.os_path, self.reactor)
        self.dvExplorer.show()
        self.dvExplorer.accepted.connect(lambda: self.loadData(self.reactor))
        self.dvExplorer.rejected.connect(self.reenableRefresh)
        
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def reenableRefresh(self):
        if self.Data is None:
            pass
        else:
            self.refresh.setEnabled(True)

    def split(self, arr, cond):
      return [arr[cond], arr[~cond]]


    @inlineCallbacks
    def loadData(self, c):
        self.xAxis.clear()
        self.yAxis.clear()
        self.zAxis.clear()

        self.plotType.setText("\nLoading data...")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        #Initialized data set to none
        self.Data = None
        self.traceData = None
        selfretraceData = None
        result = self.dvExplorer.dataSetInfo()
        print result
        self.file = result[0]
        self.directory = result[1]
        self.indVars = result[2][0]
        l = len(self.indVars)
        self.depVars =result[2][1]
        self.plotTitle.setText(str(self.file))
        self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(131,131,131); font: 11pt;}")
        #Load a data set with no trace/retrace index
        if l % 2 == 0:
            self.dataFlag = None
            for i in self.indVars[int(l / 2) : l]:
                self.xAxis.addItem(i)
                self.yAxis.addItem(i)
            for i in self.depVars:
                self.zAxis.addItem(i)
            t = time.time()
            yield self.dv.open(self.file)
            print 'opened set'
            t1 = time.time()
            print t1 - t
            #self.Data = yield self.dv.get()
            #self.Data = np.asarray(self.Data)

            getFlag = True
            self.Data = np.array([])
            while getFlag == True:
                line = yield self.dv.get(1000L)

                try:
                    if len(self.Data) != 0 and len(line) > 0:
                        self.Data = np.vstack((self.Data, line))                        
                    elif len(self.Data) == 0 and len(line) > 0:
                        self.Data = np.asarray(line)
                    else:
                        getFlag = False
                except:
                    getFlag = False
            
            print 'got set'
            t = time.time()
            print t - t1

            self.mainPlot.clear()
            self.refresh.setEnabled(True)
            self.diamCalc.setEnabled(True)
            self.gradient.setEnabled(True)
            self.subtract.setEnabled(True)
            self.sensitivity.setEnabled(True)
            self.trSelect.hide()

            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            self.plotType.setText("")
            self.refresh.setToolTip('Data set loaded. Select axes and click refresh to plot.')
            QtGui.QToolTip.showText(pt, 'Data set loaded. Select axes and click refresh to plot.')
            self.zoom.setEnabled(False)
            self.clearPlots()
            self.plotType.clear()
        #Load a data set with a trace/retrace index
        elif l % 2 == 1 and self.indVars[0] == 'Trace Index' or self.indVars[0] == 'Retrace Index':
            self.indVars = self.indVars[1::]
            for i in self.indVars[int(l / 2): l]:
                self.xAxis.addItem(i)
                self.yAxis.addItem(i)
            for i in self.depVars:
                self.zAxis.addItem(i)
            t = time.time()
            yield self.dv.open(self.file)
            print 'opened set'
            t1 = time.time()
            print t1 - t
            self.Data = yield self.dv.get()
            self.Data = np.asarray(self.Data)
            print 'got set'
            t = time.time()
            print t - t1
            self.traceData, self.retraceData = self.split(self.Data, self.Data[:,0] == 1)
            self.traceData = np.delete(self.traceData,0,1)
            self.retraceData = np.delete(self.retraceData,0,1)

            #Deletes the unsorted data set to free up memory
            self.Data = self.traceData
            self.dataFlag = 0
            self.mainPlot.clear()
            self.refresh.setEnabled(True)
            self.diamCalc.setEnabled(True)
            self.gradient.setEnabled(True)
            self.subtract.setEnabled(True)
            self.sensitivity.setEnabled(True)
            self.trSelect.show()
            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            self.plotType.setText("")
            self.refresh.setToolTip('Data set loaded. Select axes and click refresh to plot.')
            QtGui.QToolTip.showText(pt, 'Data set loaded. Select axes and click refresh to plot.')
            self.zoom.setEnabled(False)
            self.clearPlots()
            self.plotType.clear()           
        else:
            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            QtGui.QToolTip.showText(pt, 'Data set format is incompatible with the plotter.')




    def refreshPlot(self):
        if self.vhSelect.count() > 2: 
            for i in range(2, self.vhSelect.count()):
                self.vhSelect.removeItem(i)
        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        self.viewBig.setLabel('left', text=self.yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.xAxis.currentText())
        self.XZPlot.setLabel('left', self.zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.xAxis.currentText())
        self.YZPlot.setLabel('left', self.zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.yAxis.currentText())
        self.xMax = np.amax(self.Data[::,l+x])
        self.xMin = np.amin(self.Data[::,l+x])
        self.yMax = np.amax(self.Data[::,l+y])
        self.yMin = np.amin(self.Data[::,l+y])
        self.deltaX = self.xMax - self.xMin
        self.deltaY = self.yMax - self.yMin
        self.xPoints = np.amax(self.Data[::,x])+1
        self.yPoints = np.amax(self.Data[::,y])+1
        self.extent = [self.xMin, self.xMax, self.yMin, self.yMax]
        self.x0, self.x1 = self.extent[0], self.extent[1]
        self.y0, self.y1 = self.extent[2], self.extent[3]
        self.xscale, self.yscale = (self.x1-self.x0) / self.xPoints, (self.y1-self.y0) / self.yPoints   
        self.plotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = i[z]
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        if self.dataFlag == 0:
            title = self.file + " (Trace)"
            self.plotTitle.setText(str(title))
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(131,131,131); font: 11pt;}")
        elif self.dataFlag == 1:
            title = self.file + " (Retrace)"
            self.plotTitle.setText(str(title))
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(131,131,131); font: 11pt;}")
        self.zoom.setEnabled(True)
        self.clearPlots()
        self.plotType.clear()
    
    def plotTrace(self):
        self.Data = self.traceData
        self.dataFlag = 0
    
    def plotRetrace(self):
        self.Data = self.retraceData
        self.dataFlag = 1

    def clearPlots(self):
        if self.plotData is None:
            pass
        else:
            self.vLine.setValue(self.xMin)
            self.hLine.setValue(self.yMin)
            self.vCutPos.setValue(self.xMin)
            self.hCutPos.setValue(self.yMin)
            self.YZPlot.clear()
            self.XZPlot.clear()
            

    def setupPlots(self):
        self.vLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.viewBig = pg.PlotItem(name = "Plot")
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

        self.XZPlot = pg.PlotWidget(parent = self.XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.YZPlotArea)
        self.YZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.YZPlot.showAxis('right', show = True)
        self.YZPlot.showAxis('top', show = True)

    def hideDiamFrame(self):
        self.diamFrame.hide()
        self.diamCalc.clicked.connect(self.calculateDiam)
        self.diamCalc.clicked.disconnect(self.hideDiamFrame)
        self.checkFourier.stateChanged.disconnect(self.showFourier)
        self.checkAvg.stateChanged.disconnect(self.showAvg)
        if self.checkFourier.isChecked():
            self.checkFourier.setCheckState(False)
            self.mainPlot.removeItem(self.rect)
        if self.checkAvg.isChecked():
            for i in self.avgLines:
                self.mainPlot.removeItem(i)
            self.avgLines = []
            self.avgLinePos = []
            self.checkAvg.setCheckState(False)  
            self.mainPlot.addItem(self.vLine)
            self.mainPlot.addItem(self.hLine)   

    def calculateDiam(self):
        self.diamCalc.clicked.disconnect(self.calculateDiam)
        self.diamCalc.clicked.connect(self.hideDiamFrame)
        self.phi_0 = float(2.0678338e-15)
        self.diamFrame.show()
        self.fourierEst.setReadOnly(True)
        self.avgEst.setReadOnly(True)
        self.checkFourier.stateChanged.connect(self.showFourier)
        self.checkAvg.stateChanged.connect(self.showAvg)
    def showFourier(self):
        if self.checkFourier.isChecked():
            xAxis = self.viewBig.getAxis('bottom')
            yAxis = self.viewBig.getAxis('left')
            a1, a2 = xAxis.range[0], xAxis.range[1]
            b1, b2 = yAxis.range[0], yAxis.range[1]
            self.rect = pg.RectROI(((a2 + a1) / 2, (b2 + b1) / 2),((a2 - a1) / 2, (b2 - b1) / 2), movable = True)
            self.rect.addScaleHandle((1,1), (.5,.5), lockAspect = False)
            self.mainPlot.addItem(self.rect)
            self.fourierCalc.clicked.connect(self.rectCoords)
        else:
            self.mainPlot.removeItem(self.rect)
    def rectCoords(self):
        bounds = self.rect.parentBounds()

        x1 = int((bounds.x() - self.xMin) / self.xscale)
        y1 = int((bounds.y() - self.yMin) / self.yscale)
        x2 = int((bounds.x() + bounds.width() - self.xMin) / self.xscale)
        y2 = int((bounds.y() + bounds.height() - self.yMin) / self.yscale)

        dataSubSet = self.plotData[x1:x2, y1:y2]
        h = self.xPoints / (self.xMax - self.xMin)
        f = np.array([])
        for i in range(0, dataSubSet.shape[1]):
            spect, freq = signal.welch(dataSubSet[:,i], h, nperseg = dataSubSet.shape[0])
            peak = argmax(freq)
            max_f = spect[peak]
            f = np.append(f, max_f)
        f = stats.mode(f)[0]
        print f
        diameter = int(np.round(2 * 10e8 * np.sqrt(self.phi_0 * f / np.pi), decimals = 0))
        self.fourierEst.setText(str(diameter))
    def showAvg(self):
        if self.checkAvg.isChecked() is True:
            self.mainPlot.removeItem(self.vLine)
            self.mainPlot.removeItem(self.hLine)
            self.avgAddLine.clicked.connect(self.addAvgLine)
            xAxis = self.viewBig.getAxis('bottom')
            a1, a2 = xAxis.range[0], xAxis.range[1]
            self.line0 = pg.InfiniteLine(pos = 0.625 * (a2 - a1) + a1 , angle = 90, movable = True)
            self.line1 = pg.InfiniteLine(pos = 0.375 * (a2 - a1) + a1 , angle = 90, movable = True)
            #self.line2 = pg.InfiniteLine(pos = 0.625 * self.deltaX + self.xMin , angle = 90, movable = True)
            #self.line3 = pg.InfiniteLine(pos = 0.75 * self.deltaX + self.xMin , angle = 90, movable = True)
            self.avgLines = [self.line0, self.line1]
            self.updateAvgLinePos()
            self.avgCalc.clicked.connect(self.updateAvgEst)
            for i in self.avgLines:
                self.mainPlot.addItem(i)
            self.updateAvgLinePos()
        else:
            for i in self.avgLines:
                self.mainPlot.removeItem(i)
            self.avgLines = []
            self.avgLinePos = np.asarray([])
            print self.avgLinePos
            self.avgAddLine.clicked.disconnect(self.addAvgLine)
            self.mainPlot.addItem(self.vLine)
            self.mainPlot.addItem(self.hLine)


    def updateAvgLinePos(self):
        self.avgLinePos = np.sort(np.asarray([i.pos()[0] for i in self.avgLines]))
        print self.avgLinePos

    def addAvgLine(self):
        print 'done'
        i = 'self.line' + str(len(self.avgLines))
        i = pg.InfiniteLine(pos = self.avgLinePos[0] - 0.1 * (self.avgLinePos[-1] - self.avgLinePos[0]), angle = 90, movable = True)
        self.mainPlot.addItem(i)
        self.avgLines.append(i)
        self.updateAvgLinePos()

    def updateAvgEst(self):
        self.updateAvgLinePos()
        self.avgDist = np.average(np.absolute(np.diff(self.avgLinePos, axis = 0)))
        print self.avgDist
        diameter = int(np.round(2 * 10e8 * np.sqrt(self.phi_0 / (self.avgDist * np.pi)), decimals = 0))
        self.avgEst.setText(str(diameter))





    def shrink(self):
        self.resize(650, 740)
        #self.mainPlot.ui.histogram.hide()
        self.hideGrad.hide()
        self.showGrad.show()
    def enlarge(self):
        self.resize(790, 740)
        #self.mainPlot.ui.histogram.show()
        self.hideGrad.show()
        self.showGrad.hide()



    def toggleBottomPlot(self):
        if self.vhSelect.currentIndex() == 0:
            pos = self.hLine.value()
            self.YZPlotArea.lower()
            self.updateXZPlot(pos)
        elif self.vhSelect.currentIndex() == 1:
            pos = self.vLine.value()
            self.XZPlotArea.lower()
            self.updateYZPlot(pos)  
        elif self.vhSelect.currentIndex() ==2:
            self.YZPlotArea.lower()
            self.plotMaxSens()
        elif self.vhSelect.currentIndex() ==3:
            self.YZPlotArea.lower()
            self.plotOptBias()              

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
                xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
                yVals = self.plotData[:,p]
                self.XZPlot.plot(x = xVals, y = yVals, pen = 0.5)
                self.lineYVals = yVals
                self.lineXVals = xVals


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
                xVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
                yVals = self.plotData[p]
                self.YZPlot.plot(x = xVals, y = yVals, pen = 0.5)
                self.lineYVals = yVals
                self.lineXVals = xVals


    def newPlot(self):
        self.numPlots += 1
        self.newPlot = subPlot(self.dv, self.os_path, self.numPlots, self.reactor)
        self.newPlot.show()



class editDataInfo(QtGui.QDialog, Ui_EditDataInfo):
    def __init__(self, dataset, dv, os_path, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(editDataInfo, self).__init__(parent)


        self.reactor = reactor
        self.setupUi(self)
        self.dv = dv
        self.dataSet = dataset
        self.os_path = os_path

        self.ok.clicked.connect(self.updateComments)
        self.cancel.clicked.connect(self.exitEdit)

        self.name.setWordWrap(True)
        self.currentComs.setReadOnly(True)
        self.setupTags(self.reactor)

    @inlineCallbacks
    def setupTags(self, c):
        name = yield self.dv.get_name()
        params = yield self.dv.get_parameters()
        coms = yield self.dv.get_comments()
        self.name.setText(name)
        self.name.setStyleSheet("QLabel#name {color: rgb(131,131,131);}")
        self.parameters.setText(str(params))
        self.parameters.setStyleSheet("QLabel#parameters {color: rgb(131,131,131);}")
        path = yield self.dv.cd()
        os_addon = self.os_path
        if len(path) == 1:
            os_path = self.os_path + '\\' + name + '.csv'
            
        else:
            for i in path[1::]:
                os_addon = os_addon + '\\' + i + '.dir'
                print os_addon
            os_addon = os_addon + '\\' + name + '.csv'
        try:    
            stat = int(os.stat(str(os_addon)).st_size / 1000)
            self.fileSize.setText(str(stat))
            self.fileSize.setStyleSheet("QLabel#fileSize {color: rgb(131,131,131);}")
        except:
            pass
        if str(coms) == '[]':
            self.currentComs.setText("(None)")
        else:
            s = ""
            for i in coms:
                s += str(i[2]) + "\n\n" 
            self.currentComs.setText(str(s))

    @inlineCallbacks
    def updateComments(self, c):
        coms = str(self.comments.toPlainText())
        if coms == '':
            pass
        else:
            yield self.dv.add_comment(coms)
        self.close()
    def exitEdit(self):
        self.close()



class dataVaultExplorer(QtGui.QDialog, Ui_dvExplorer):
    def __init__(self, dv, os_path, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(dataVaultExplorer, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        self.dv = dv 
        self.os_path = os_path

        self.currentDir.setReadOnly(True)
        self.currentFile.setReadOnly(True)
        self.curDir = ''

        self.popDirs(self.reactor)

        self.dirList.itemDoubleClicked.connect(self.updateDirs)
        self.fileList.itemClicked.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(self.displayInfo)
        self.back.clicked.connect(self.backUp)
        self.home.clicked.connect(self.goHome)
        self.refresh.clicked.connect(self.popDirs)
        self.addDir.clicked.connect(self.makeDir)
        self.select.clicked.connect(self.selectDirFile)
        self.cancelSelect.clicked.connect(self.closeWindow)

    @inlineCallbacks
    def popDirs(self, c):
        self.dirList.clear()
        self.fileList.clear()
        l = yield self.dv.dir()
        for i in l[0]:
            self.dirList.addItem(i)
        for i in l[1]:
            self.fileList.addItem(i)
        if self.curDir == '':
            self.currentDir.setText('Root')
            self.dirName.setText('Root')
            self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")
        else:
            self.currentDir.setText(self.curDir)
            self.dirName.setText(self.curDir)
            self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")


    @inlineCallbacks
    def updateDirs(self, subdir):
        subdir = str(subdir.text())
        self.curDir = subdir
        yield self.dv.cd(subdir, False)
        self.popDirs(self.reactor)

    @inlineCallbacks
    def backUp(self, c):
        if self.curDir == '':
            pass
        else:
            self.currentFile.clear()
            direct = yield self.dv.cd()
            back = direct[0:-1]
            self.curDir = back[-1]
            yield self.dv.cd(back)
            self.popDirs(self.reactor)

    @inlineCallbacks
    def goHome(self, c):
        self.currentFile.clear()
        yield self.dv.cd('')
        self.curDir = ''
        self.popDirs(self.reactor)


    @inlineCallbacks
    def makeDir(self, c):
        direct, ok = QtGui.QInputDialog.getText(self, "Make directory", "Directory Name: " )
        if ok:
            yield self.dv.mkdir(str(direct))
            self.popDirs(self.reactor)

    @inlineCallbacks
    def displayInfo(self, c):
        dataSet = str(self.currentFile.text())
        yield self.dv.open(str(dataSet))
        self.editDataInfo = editDataInfo(dataSet, self.dv, self.os_path, c)
        self.editDataInfo.show()

    def fileSelect(self):
        file = self.fileList.currentItem()
        self.currentFile.setText(file.text())


    def dataSetInfo(self):
        info =[self.file, self.directory, self.variables]
        print 'info retrieved'
        return info

    @inlineCallbacks
    def selectDirFile(self, c):
        print 'got here'
        self.file = str(self.currentFile.text())
        print 'got here1'
        self.directory = yield self.dv.cd()
        print 'got here2'
        try:
            yield self.dv.open(self.file)
        except Exception as inst:
            print 'Following error was thrown: '
            print inst
            print 'Error thrown on line: '
            print sys.exc_traceback.tb_lineno
        print 'got here3'
        variables = yield self.dv.variables()
        self.indVars = []
        self.depVars = []
        print 'got here4'
        for i in variables[0]:
            self.indVars.append(str(i[0]))
        for i in variables[1]:
            self.depVars.append(str(i[0]))
        print 'got here5'
        self.variables = [self.indVars, self.depVars]
        print self.variables
        
        self.accept()


    def closeWindow(self):
        self.reject()

class subPlot(QtGui.QDialog, Ui_Plotter):
    def __init__(self, dv, os_path, numPlots, reactor):
        super(subPlot, self).__init__()
        
        self.reactor = reactor
        self.dv = dv
        self.os_path = os_path
        self.numPlots = numPlots
        self.setupUi(self)
        self.window = window
        self.setWindowTitle('Subplot ' + str(self.numPlots))

        self.showGrad.hide()
        self.diamFrame.hide()


        self.setupPlots()

        self.hideGrad.clicked.connect(self.shrink)
        self.showGrad.clicked.connect(self.enlarge)

        self.refresh.setEnabled(False)
        self.diamCalc.setEnabled(False)
        self.gradient.setEnabled(False)
        self.subtract.setEnabled(False)
        self.sensitivity.setEnabled(False)
        self.zoom.setEnabled(False)

        self.gradMenu = QtGui.QMenu()
        gradX = QtGui.QAction(QtGui.QIcon("nablaXIcon.png"), "Gradient along x-axis", self)
        gradY = QtGui.QAction(QtGui.QIcon("nablaYIcon.png"), "Gradient along y-axis", self)
        lancSettings = QtGui.QAction("Gradient settings...", self)
        gradX.triggered.connect(self.xDeriv)
        gradY.triggered.connect(self.yDeriv)
        lancSettings.triggered.connect(self.derivSettings)
        self.gradMenu.addAction(gradX)
        self.gradMenu.addAction(gradY)
        self.gradMenu.addAction(lancSettings)
        self.gradient.setMenu(self.gradMenu)
        self.datPct = 0.1

        self.subtractMenu = QtGui.QMenu()
        subAvg = QtGui.QAction( "Subtract constant offset", self)
        subPlane = QtGui.QAction( "Subtract planar fit", self)
        subQuad = QtGui.QAction( "Subtract quadratic fit", self)
        subAvg.triggered.connect(self.subtractAvg)
        subPlane.triggered.connect(self.subtractPlane)
        subQuad.triggered.connect(self.subtractQuad)
        self.subtractMenu.addAction(subAvg)
        self.subtractMenu.addAction(subPlane)
        self.subtractMenu.addAction(subQuad)
        self.subtract.setMenu(self.subtractMenu)


        self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        self.diamCalc.clicked.connect(self.calculateDiam)
        self.sensitivity.clicked.connect(self.promptSensitivity)
        self.browse.clicked.connect(self.browseDV)
        self.refresh.clicked.connect(self.refreshPlot)
        self.addPlot.clicked.connect(self.newPlot)
        self.vCutPos.valueChanged.connect(self.changeVertLine)
        self.hCutPos.valueChanged.connect(self.changeHorLine)

        self.Data = None
        self.file = None
        self.directory = None

    def promptSensitivity(self):
        self.sensPrompt = Sensitivity(self.depVars, self.indVars, self.reactor)
        self.sensPrompt.show()
        self.sensPrompt.accepted.connect(self.plotSens)
        print 'great'
    def plotSens(self):
        self.sensIndex = self.sensPrompt.sensIndicies()
        print self.sensIndex
        l = int(len(self.indVars) / 2)
        x = self.sensIndex[0]
        y = self.sensIndex[1]
        z = self.sensIndex[2] + len(self.indVars) 
        print x,y,z
        self.xMax = np.amax(self.Data[::,l+x])
        self.xMin = np.amin(self.Data[::,l+x])
        self.yMax = np.amax(self.Data[::,l+y])
        self.yMin = np.amin(self.Data[::,l+y])
        self.deltaX = self.xMax - self.xMin
        self.deltaY = self.yMax - self.yMin
        self.xPoints = np.amax(self.Data[::,x])+1
        self.yPoints = np.amax(self.Data[::,y])+1
        self.extent = [self.xMin, self.xMax, self.yMin, self.yMax]
        self.x0, self.x1 = self.extent[0], self.extent[1]
        self.y0, self.y1 = self.extent[2], self.extent[3]
        self.xscale, self.yscale = (self.x1-self.x0) / self.xPoints, (self.y1-self.y0) / self.yPoints   
        n = self.sensIndex[3] + len(self.indVars)
        self.plotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        self.noiseData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = i[z]
            if i[n] != 0:
                self.noiseData[int(i[x]), int(i[y])] = i[n]
            else:
                self.noiseData[int(i[x]), int(i[y])] = 1e-5
        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.yPoints * self.datPct)
        for i in range(0, self.plotData.shape[1]):
            self.plotData[:, i] = deriv(self.plotData[:, i], xVals, N, delta)
            for j in range(0,self.plotData.shape[0]):
                self.plotData[j, i] = self.plotData[j,i] / self.noiseData[j,i]
            #self.plotData[:, i, 0] = np.absolute(self.plotData[:, i, 0] / self.plotData[:, i, 1])
        #self.plotData = np.delete(self.plotData[:,:,1], np.s_[:0], 0)
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.mainPlot.addItem(self.vLine)
        self.mainPlot.addItem(self.hLine)
        self.vLine.setValue(self.xMin)
        self.hLine.setValue(self.yMin)  
        self.vCutPos.setValue(self.xMin)
        self.hCutPos.setValue(self.yMin)
        self.plotType.setText('Plotted sensitivity.')           
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()



    def xDeriv(self):

        self.gradient.setFocusPolicy(QtCore.Qt.StrongFocus)
        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.xPoints * self.datPct)
        for i in range(0, self.plotData.shape[1]):
            self.plotData[:, i] = deriv(self.plotData[:,i], xVals, N, delta)    
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted gradient along \nx-axis.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def yDeriv(self):

        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.yMax - self.yMin) / self.yPoints
        N = int(self.yPoints * self.datPct)
        for i in range(0, self.plotData.shape[0]):
            self.plotData[i, :] = deriv(self.plotData[i,:], yVals, N, delta)    
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted gradient along \ny-axis.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def derivSettings(self):
        self.gradSet = gradSet(self.reactor, self.datPct)
        self.gradSet.show()
        self.gradSet.accepted.connect(self.setLancWindow)
    def setLancWindow(self):
        self.datPct = self.gradSet.dataPercent.value() / 100

    def subtractAvg(self):

        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        X = np.empty([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            X[int(i[x]), int(i[y])] = i[z]
        avg = np.average(X)
        self.plotData = X - avg
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted offset \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractPlane(self):

        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        X = np.c_[self.Data[::, l+x], self.Data[::,l+y], np.ones(self.Data.shape[0])]
        C = np.linalg.lstsq(X, self.Data[::,z])
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = i[z] - np.dot(C[0], [i[x+l], i[y+l], 1])      
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted plane \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractQuad(self):

        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        X = np.c_[np.ones(self.Data.shape[0]), self.Data[::, [l+x, l+y]], np.prod(self.Data[::, [l+x, l+y]], axis = 1), self.Data[::, [l+x, l+y]]**2]
        C = np.linalg.lstsq(X, self.Data[::,z])
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = i[z] - np.dot(C[0], [i[x+l]**2, i[y+l]**2, i[l+x]*i[y+l], i[l+x], i[l+y], 1])     
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted quadratic \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()


    def browseDV(self):
        self.refresh.setEnabled(False)
        self.dvExplorer = dataVaultExplorer(self.dv, self.os_path, reactor)
        self.dvExplorer.show()
        self.dvExplorer.accepted.connect(lambda: self.loadData(self.reactor))
        self.dvExplorer.rejected.connect(self.reenableRefresh)

    def reenableRefresh(self):
        if self.Data == None:
            pass
        else:
            self.refresh.setEnabled(True)


    @inlineCallbacks
    def loadData(self, c):
        self.xAxis.clear()
        self.yAxis.clear()
        self.zAxis.clear()

        self.plotType.setText("\nLoading data...")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")

        result = self.dvExplorer.dataSetInfo()
        print result
        self.file = result[0]
        self.directory = result[1]
        self.indVars = result[2][0]
        l = len(self.indVars)
        self.depVars =result[2][1]
        self.plotTitle.setText(str(self.file))
        self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(131,131,131); font: 11pt;}")
        if l % 2 == 0:
            for i in self.indVars[int(l / 2) : l]:
                self.xAxis.addItem(i)
                self.yAxis.addItem(i)
            for i in self.depVars:
                self.zAxis.addItem(i)
            t = time.time()
            yield self.dv.open(self.file)
            print 'opened set'
            t1 = time.time()
            print t1 - t
            self.Data = yield self.dv.get()
            self.Data = np.asarray(self.Data)
            print 'got set'
            t = time.time()
            print t - t1
            self.mainPlot.clear()
            self.refresh.setEnabled(True)
            self.diamCalc.setEnabled(True)
            self.gradient.setEnabled(True)
            self.subtract.setEnabled(True)
            self.sensitivity.setEnabled(True)
            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            self.plotType.setText("")
            self.refresh.setToolTip('Data set loaded. Select axes and click refresh to plot.')
            QtGui.QToolTip.showText(pt, 'Data set loaded. Select axes and click refresh to plot.')
        else:
            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            QtGui.QToolTip.showText(pt, 'Data set format is incompatible with the plotter.')




    def refreshPlot(self):

        l = int(len(self.indVars) / 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + len(self.indVars) 
        self.viewBig.setLabel('left', text=self.yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.xAxis.currentText())
        self.XZPlot.setLabel('left', self.zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.xAxis.currentText())
        self.YZPlot.setLabel('left', self.zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.yAxis.currentText())
        self.xMax = np.amax(self.Data[::,l+x])
        self.xMin = np.amin(self.Data[::,l+x])
        self.yMax = np.amax(self.Data[::,l+y])
        self.yMin = np.amin(self.Data[::,l+y])
        self.deltaX = self.xMax - self.xMin
        self.deltaY = self.yMax - self.yMin
        self.xPoints = np.amax(self.Data[::,x])+1
        self.yPoints = np.amax(self.Data[::,y])+1
        self.extent = [self.xMin, self.xMax, self.yMin, self.yMax]
        self.x0, self.x1 = self.extent[0], self.extent[1]
        self.y0, self.y1 = self.extent[2], self.extent[3]
        self.xscale, self.yscale = (self.x1-self.x0) / self.xPoints, (self.y1-self.y0) / self.yPoints   
        self.plotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.plotData[int(i[x]), int(i[y])] = i[z]
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.clearPlots()

    def clearPlots(self):
        self.vLine.setValue(self.xMin)
        self.hLine.setValue(self.yMin)
        self.vCutPos.setValue(self.xMin)
        self.hCutPos.setValue(self.yMin)
        self.YZPlot.clear()
        self.XZPlot.clear()
        self.plotType.clear()

    def setupPlots(self):
        self.vLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.viewBig = pg.PlotItem(name = "Plot")
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

        self.XZPlot = pg.PlotWidget(parent = self.XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.YZPlotArea)
        self.YZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.YZPlot.showAxis('right', show = True)
        self.YZPlot.showAxis('top', show = True)

    def hideDiamFrame(self):
        self.diamFrame.hide()
        self.diamCalc.clicked.connect(self.calculateDiam)
        self.diamCalc.clicked.disconnect(self.hideDiamFrame)
        self.checkFourier.stateChanged.disconnect(self.showFourier)
        self.checkAvg.stateChanged.disconnect(self.showAvg)
        if self.checkFourier.isChecked():
            self.checkFourier.setCheckState(False)
            self.mainPlot.removeItem(self.rect)
        if self.checkAvg.isChecked():
            for i in self.avgLines:
                self.mainPlot.removeItem(i)
            self.avgLines = []
            self.avgLinePos = []
            self.checkAvg.setCheckState(False)  
            self.mainPlot.addItem(self.vLine)
            self.mainPlot.addItem(self.hLine)   

    def calculateDiam(self):
        self.rect = pg.RectROI(((self.xMax + self.xMin) / 2, (self.yMax + self.yMin) / 2),((self.deltaX) / 2, (self.deltaY) / 2), movable = True)
        self.rect.addScaleHandle((1,1), (.5,.5), lockAspect = False)

        self.diamCalc.clicked.disconnect(self.calculateDiam)
        self.diamCalc.clicked.connect(self.hideDiamFrame)
        self.phi_0 = float(2.0678338e-15)
        self.diamFrame.show()
        self.fourierEst.setReadOnly(True)
        self.avgEst.setReadOnly(True)
        self.checkFourier.stateChanged.connect(self.showFourier)
        self.checkAvg.stateChanged.connect(self.showAvg)
    def showFourier(self):
        if self.checkFourier.isChecked():
            self.mainPlot.addItem(self.rect)
            self.fourierCalc.clicked.connect(self.rectCoords)
        else:
            self.mainPlot.removeItem(self.rect)
    def rectCoords(self):
        bounds = self.rect.parentBounds()

        x1 = int((bounds.x() - self.xMin) / self.xscale)
        y1 = int((bounds.y() - self.yMin) / self.yscale)
        x2 = int((bounds.x() + bounds.width() - self.xMin) / self.xscale)
        y2 = int((bounds.y() + bounds.height() - self.yMin) / self.yscale)

        dataSubSet = self.plotData[x1:x2, y1:y2]
        h = self.xPoints / (self.xMax - self.xMin)
        f = np.array([])
        for i in range(0, dataSubSet.shape[1]):
            spect, freq = signal.welch(dataSubSet[:,i], h, nperseg = dataSubSet.shape[0])
            peak = argmax(freq)
            max_f = spect[peak]
            f = np.append(f, max_f)
        f = stats.mode(f)[0]
        print f
        diameter = int(np.round(2 * 10e8 * np.sqrt(self.phi_0 * f / np.pi), decimals = 0))
        self.fourierEst.setText(str(diameter))
    def showAvg(self):
        if self.checkAvg.isChecked() is True:
            self.mainPlot.removeItem(self.vLine)
            self.mainPlot.removeItem(self.hLine)
            self.avgAddLine.clicked.connect(self.addAvgLine)
            self.line0 = pg.InfiniteLine(pos = 0.25 * self.deltaX + self.xMin , angle = 90, movable = True)
            self.line1 = pg.InfiniteLine(pos = 0.375 * self.deltaX + self.xMin , angle = 90, movable = True)
            self.line2 = pg.InfiniteLine(pos = 0.625 * self.deltaX + self.xMin , angle = 90, movable = True)
            self.line3 = pg.InfiniteLine(pos = 0.75 * self.deltaX + self.xMin , angle = 90, movable = True)
            self.avgLines = [self.line0, self.line1, self.line2, self.line3]
            self.updateAvgLinePos()
            self.avgCalc.clicked.connect(self.updateAvgEst)
            for i in self.avgLines:
                self.mainPlot.addItem(i)
            self.updateAvgLinePos()
        else:
            for i in self.avgLines:
                self.mainPlot.removeItem(i)
            print 'yes'
            self.avgLines = []
            self.avgLinePos = []
            self.mainPlot.addItem(self.vLine)
            self.mainPlot.addItem(self.hLine)


    def updateAvgLinePos(self):
        self.avgLinePos = np.sort(np.asarray([i.pos()[0] for i in self.avgLines]))
        print self.avgLinePos

    def addAvgLine(self):
        i = 'self.line' + str(len(self.avgLines))
        i = pg.InfiniteLine(pos = self.avgLinePos[0] - 0.01 * (self.avgLinePos[-1] - self.avgLinePos[0]), angle = 90, movable = True)
        self.mainPlot.addItem(i)
        self.avgLines.append(i)
        self.updateAvgLinePos()

    def updateAvgEst(self):
        self.updateAvgLinePos()
        self.avgDist = np.average(np.absolute(np.diff(self.avgLinePos, axis = 0)))
        print self.avgDist
        diameter = int(np.round(2 * 10e8 * np.sqrt(self.phi_0 / (self.avgDist * np.pi)), decimals = 0))
        self.avgEst.setText(str(diameter))





    def shrink(self):
        self.resize(650, 740)
        #self.mainPlot.ui.histogram.hide()
        self.hideGrad.hide()
        self.showGrad.show()
    def enlarge(self):
        self.resize(790, 740)
        #self.mainPlot.ui.histogram.show()
        self.hideGrad.show()
        self.showGrad.hide()



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
                xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
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
                xVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
                yVals = self.plotData[p]
                self.YZPlot.plot(x = xVals, y = yVals, pen = 0.5)

    def newPlot(self):
        self.numPlots += 1
        self.newPlot = subPlot(self.dv, self.os_path, self.numPlots, self.reactor)
        self.newPlot.show()

class zoomPlot(QtGui.QDialog, Ui_ZoomWindow):
    def __init__(self, reactor, plotData, dataSubset, zoomExtent, indVars, depVars, currentIndex, title, parent = None):
        super(zoomPlot, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.window = parent

        self.showGrad.hide()
        self.diamFrame.hide()



        self.Data = copy.copy(dataSubset)

        indexOffsets = np.array([])
        for ii in range(0, len(indVars)):
            indexOffsets = np.append(indexOffsets, self.Data[0,ii])
        while len(indexOffsets) != len(self.Data[0]):
            indexOffsets = np.append(indexOffsets, 0)
        self.Data = self.Data - indexOffsets
        print np.amax(self.Data[::,0]), np.amax(self.Data[::,1])
        self.oData = copy.copy(plotData)
        self.extent = zoomExtent
        self.xMin, self.xMax = self.extent[0], self.extent[1]
        self.yMin, self.yMax = self.extent[2], self.extent[3]
        self.xscale, self.yscale = self.extent[4], self.extent[5]
        self.xPoints, self.yPoints = self.oData.shape[0], self.oData.shape[1]
        self.indVars = indVars
        self.depVars = depVars

        for i in self.indVars:
            self.xAxis.addItem(i)
            self.yAxis.addItem(i)
        for i in self.depVars:
            self.zAxis.addItem(i)
        self.initIndex = currentIndex
        self.xAxis.setCurrentIndex(self.initIndex[0])
        self.yAxis.setCurrentIndex(self.initIndex[1])
        self.zAxis.setCurrentIndex(self.initIndex[2])

        self.setupPlots()
        
        self.back.clicked.connect(self.revert)

        self.hideGrad.clicked.connect(self.shrink)
        self.showGrad.clicked.connect(self.enlarge)
        
        self.plotTitle.setText(title)
        self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(131,131,131); font: 11pt;}")

        self.savePlot.clicked.connect(self.matPlot)
        
        self.gradMenu = QtGui.QMenu()
        gradX = QtGui.QAction(QtGui.QIcon("nablaXIcon.png"), "Gradient along x-axis", self)
        gradY = QtGui.QAction(QtGui.QIcon("nablaYIcon.png"), "Gradient along y-axis", self)
        lancSettings = QtGui.QAction("Gradient settings...", self)
        gradX.triggered.connect(self.xDeriv)
        gradY.triggered.connect(self.yDeriv)
        lancSettings.triggered.connect(self.derivSettings)
        self.gradMenu.addAction(gradX)
        self.gradMenu.addAction(gradY)
        self.gradMenu.addAction(lancSettings)
        self.gradient.setMenu(self.gradMenu)
        self.datPct = 0.1
        
        self.saveMenu = QtGui.QMenu()
        twoDSave = QtGui.QAction("Save 2D plot", self)
        oneDSave = QtGui.QAction("Save line cut", self)
        oneDSave.triggered.connect(self.matLinePlot)
        twoDSave.triggered.connect(self.matPlot)
        self.saveMenu.addAction(twoDSave)
        self.saveMenu.addAction(oneDSave)
        self.savePlot.setMenu(self.saveMenu)
        
        self.showGrad.hide()
        self.hideGrad.hide()

        self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        self.sensitivity.clicked.connect(self.promptSensitivity)
        self.refresh.clicked.connect(self.refreshPlot)
        self.vCutPos.valueChanged.connect(self.changeVertLine)
        self.hCutPos.valueChanged.connect(self.changeHorLine)
        
    def revert(self):
        self.clearPlots()
        self.plotType.clear()
        self.zoomPlot = self.oData
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted original \ndata selection.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        if self.vhSelect.count() > 2: 
            while self.vhSelect.count()>2:
                
                self.vhSelect.removeItem(2)

    def refreshPlot(self):
        
        if self.vhSelect.count() > 2: 
            while self.vhSelect.count()>2:
                
                self.vhSelect.removeItem(2)
        l = int(len(self.indVars) * 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + l
        self.xPoints, self.yPoints = int(np.amax(self.Data[::,x])) + 1, int(np.amax(self.Data[::,y])) + 1
        self.viewBig.setLabel('left', text=self.yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.xAxis.currentText())
        self.XZPlot.setLabel('left', self.zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.xAxis.currentText())
        self.YZPlot.setLabel('left', self.zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.yAxis.currentText())
        self.zoomPlot = np.zeros([int(self.xPoints), int(self.yPoints)])
        
        for i in self.Data:
            
            self.zoomPlot[int(i[x]), int(i[y])] = i[z]
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.clearPlots()
        self.plotType.clear()   




    def clearPlots(self):
        if self.zoomPlot is None:
            pass
        else:
            self.vLine.setValue(self.xMin)
            self.hLine.setValue(self.yMin)
            self.vCutPos.setValue(self.xMin)
            self.hCutPos.setValue(self.yMin)
            self.YZPlot.clear()
            self.XZPlot.clear()
            

    def setupPlots(self):
        self.zoomPlot = self.oData
        


        self.vLine = pg.InfiniteLine(pos = self.xMin, angle = 90, movable = True)
        self.hLine = pg.InfiniteLine(pos = self.yMin, angle = 0, movable = True)

        self.viewBig = pg.PlotItem(name = "Plot")
        self.viewBig.showAxis('top', show = True)
        self.viewBig.showAxis('right', show = True)
        self.viewBig.setAspectLocked(lock = False, ratio = 1)
        self.mainPlot = pg.ImageView(parent = self.mainPlotArea, view = self.viewBig)
        self.mainPlot.setGeometry(QtCore.QRect(0, 0, 750, 450))
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.mainPlot.ui.roiBtn.hide()
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.setImage(self.oData, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.viewBig.setAspectLocked(False)
        self.viewBig.invertY(False)

        self.viewBig.addItem(self.vLine, ignoreBounds = True)
        self.viewBig.addItem(self.hLine, ignoreBounds =True)
        self.vLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.XZPlot = pg.PlotWidget(parent = self.XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.YZPlotArea)
        self.YZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.YZPlot.showAxis('right', show = True)
        self.YZPlot.showAxis('top', show = True)
        
    def matLinePlot(self):
        if not self.zoomPlot is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genLineMatFile(fold)
                
    def genLineMatFile(self, fold):
        yData = np.asarray(self.lineYVals)
        xData = np.asarray(self.lineXVals)
        
        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        print 'All data converted. Saving .mat file'
        sio.savemat(fold,{savename:matData})
        matData = None      

    def matPlot(self):
        if not self.zoomPlot is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genMatFile(fold)

    def genMatFile(self, fold):
        t = time.time()
        xVals = np.linspace(self.xMin, self.xMax, int(self.xPoints))
        yVals = np.linspace(self.yMin, self.yMax, int(self.yPoints))
        xInd, yInd = np.linspace(0,  self.xPoints - 1,  int(self.xPoints)), np.linspace(0,  self.yPoints - 1, int(self.yPoints))

        zX, zY, zXI, zYI = np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)]), np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)])
        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.zoomPlot.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        savename = fold.split("/")[-1].split('.mat')[0]
        print 'All data converted. Saving .mat file'
        sio.savemat(fold,{savename:matData})
        matData = None

    def xDeriv(self):

        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.xPoints * self.datPct)
        for i in range(0, self.zoomPlot.shape[1]):
            self.zoomPlot[:, i] = deriv(self.zoomPlot[:,i], xVals, N, delta)    
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted gradient \nalong x-axis.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def yDeriv(self):

        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.yMax - self.yMin) / self.yPoints
        N = int(self.yPoints * self.datPct)
        for i in range(0, self.zoomPlot.shape[0]):
            self.zoomPlot[i, :] = deriv(self.zoomPlot[i,:], yVals, N, delta)    
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted gradient \nalong y-axis.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
        
    def derivSettings(self):
        self.gradSet = gradSet(self.reactor)
        self.gradSet.show()
        self.gradSet.accepted.connect(self.setLancWindow)
    def setLancWindow(self):
        self.datPct = self.gradSet.dataPercent.value() / 100

    def subtractAvg(self):

        avg = np.average(self.zoomPlot)
        self.zoomPlot = self.zoomPlot - avg
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted offset \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractPlane(self):

        l = int(len(self.indVars) * 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + l
        X = np.c_[self.Data[::, l+x], self.Data[::,l+y], np.ones(self.Data.shape[0])]
        Y = np.ndarray.flatten(self.zoomPlot)
        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            self.zoomPlot[int(i[x]), int(i[y])] = self.zoomPlot[int(i[x]), int(i[y])] - np.dot(C[0], [i[x+l], i[y+l], 1])       
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted plane \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractQuad(self):

        l = int(len(self.indVars) * 2)
        x = self.xAxis.currentIndex()
        y = self.yAxis.currentIndex()
        z = self.zAxis.currentIndex() + l
        X = np.c_[np.ones(self.Data.shape[0]), self.Data[::, [l+x, l+y]], np.prod(self.Data[::, [l+x, l+y]], axis = 1), self.Data[::, [l+x, l+y]]**2]
        Y = np.ndarray.flatten(self.plotData)
        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            self.zoomPlot[int(i[x]), int(i[y])] = i[z] - np.dot(C[0], [i[x+l]**2, i[y+l]**2, i[l+x]*i[y+l], i[l+x], i[l+y], 1])     
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.plotType.setText("Plotted quadratic \nsubtracted data.")
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
        
    def promptSensitivity(self):
        ind = range(0,len(self.indVars)) + self.indVars
        #deps = range(0,len(self.depVars)) + self.depVars
        self.sensPrompt = Sensitivity(self.depVars, ind, self.reactor)
        self.sensPrompt.show()
        self.sensPrompt.accepted.connect(self.plotSens)
        print 'great'
        
    def plotSens(self):

        self.sensIndex = self.sensPrompt.sensIndicies()
        l = int(len(self.indVars) * 2)
        x = self.sensIndex[0]
        y = self.sensIndex[1]
        z = self.sensIndex[2] + l
        self.NSselect = self.sensIndex[4]
        self.unitSelect = self.sensIndex[5]
        self.xMax = np.amax(self.Data[::,int(l/2) + x])
        self.xMin = np.amin(self.Data[::,int(l/2) + x])
        self.yMax = np.amax(self.Data[::,int(l/2) + y])
        self.yMin = np.amin(self.Data[::,int(l/2) + y])
        self.deltaX = self.xMax - self.xMin
        self.deltaY = self.yMax - self.yMin
        self.xPoints = np.amax(self.Data[::,x])+1
        self.yPoints = np.amax(self.Data[::,y])+1
        self.extent = [self.xMin, self.xMax, self.yMin, self.yMax]
        self.x0, self.x1 = self.extent[0], self.extent[1]
        self.y0, self.y1 = self.extent[2], self.extent[3]
        self.xscale, self.yscale = float((self.x1-self.x0) / self.xPoints), float((self.y1-self.y0) / self.yPoints)
        
        n = self.sensIndex[3] + l
        self.zoomPlot = np.zeros([int(self.xPoints), int(self.yPoints)])
        self.noiseData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.zoomPlot[int(i[x]), int(i[y])] = float(i[z])
            
            if i[n] != 0:
                self.noiseData[int(i[x]), int(i[y])] = float(i[n])
            else:
                self.noiseData[int(i[x]), int(i[y])] = 1e-3
        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        #print xVals
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        print 'xPoints: ', self.xPoints
        print 'yPoints: ', self.yPoints
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.xPoints * self.datPct)

        for i in range(0, self.zoomPlot.shape[1]):
            self.zoomPlot[:, i] = deriv(self.zoomPlot[:, i], xVals, N, delta)
            for pt in range(0, len(self.zoomPlot[:,i])):
                if self.zoomPlot[pt,i] == 0:
                    
                    self.zoomPlot[pt,i] = 1e-3
                    
        if self.NSselect == 1:
            self.plotData = np.absolute(np.true_divide(self.zoomPlot , self.noiseData))
        else:
            self.zoomPlot = np.absolute(np.true_divide(self.noiseData , self.zoomPlot ))
            self.zoomPlot = np.clip(self.zoomPlot, 0, 1e3)

            
            if self.unitSelect == 2:
                gain, bw = self.sensPrompt.sensConv()[0], self.sensPrompt.sensConv()[1]
                self.zoomPlot = np.true_divide(self.zoomPlot, (.364 * gain * np.sqrt(1000 *bw)))
                self.zoomPlot = np.clip(self.zoomPlot, 0, 1e3)
        '''
        if self.NSselect == 1:
            self.zoomPlot = np.minimum(np.absolute(np.divide(self.zoomPlot , self.noiseData)), 1e5)
        else:
            self.zoomPlot = np.minimum(np.absolute(np.divide(self.noiseData , self.zoomPlot )), 1e5)
        '''

        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.mainPlot.addItem(self.vLine)
        self.mainPlot.addItem(self.hLine)
        self.vLine.setValue(self.xMin)
        self.hLine.setValue(self.yMin)  
        self.vCutPos.setValue(self.xMin)
        self.hCutPos.setValue(self.yMin)
        if self.NSselect == 1:
            self.plotType.setText('Plotted sensitivity.')
            self.vhSelect.addItem('Maximum Sensitivity')
        else:
            self.plotType.setText('Plotted field noise.')   
            self.vhSelect.addItem('Minimum Noise')
            self.vhSelect.addItem('Optimal Bias')
        self.plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")    
        
    def plotMaxSens(self):
        if self.NSselect == 1:
            maxSens = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.zoomPlot.shape[0]):
                maxSens = np.append(maxSens, np.amax(self.zoomPlot[i]))
            self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.XZPlot.setLabel('left', 'Maximum Relative Sensitivity')
            self.XZPlot.plot(x = bVals, y = maxSens,pen = 0.5)
            self.lineYVals = maxSens
            self.lineXVals = bVals
        else:
            minNoise = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.zoomPlot.shape[0]):
                minNoise = np.append(minNoise, np.amin(self.zoomPlot[i]))
            self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.XZPlot.setLabel('left', 'Minimum field noise')
            self.XZPlot.plot(x = bVals, y = minNoise,pen = 0.5)
            self.lineYVals = minNoise
            self.lineXVals = bVals
    
    def plotOptBias(self):  
        minNoise = np.array([])
        bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
        vVals =np.linspace(self.yMin, self.yMax, self.yPoints)
        self.XZPlot.clear()
        for i in range(0, self.zoomPlot.shape[0]):
            arg = np.argmin(self.zoomPlot[i])
            minNoise = np.append(minNoise, vVals[arg])
        self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.XZPlot.setLabel('left', 'Optimal Bias', units = 'V')
        self.XZPlot.plot(x = bVals, y = minNoise,pen = 0.5)
        self.lineYVals = minNoise
        self.lineXVals = bVals





    def shrink(self):
        self.resize(640, 740)
        self.hideGrad.hide()
        self.showGrad.show()
    def enlarge(self):
        self.resize(790, 740)
        self.hideGrad.show()
        self.showGrad.hide()



    def toggleBottomPlot(self):
        if self.vhSelect.currentIndex() == 0:
            pos = self.hLine.value()
            self.YZPlotArea.lower()
            self.updateXZPlot(pos)

        elif self.vhSelect.currentIndex() == 1:
            pos = self.vLine.value()
            self.XZPlotArea.lower()
            self.updateYZPlot(pos)  

        elif self.vhSelect.currentIndex() ==2:
            self.YZPlotArea.lower()
            self.plotMaxSens()

        elif self.vhSelect.currentIndex() ==3:
            self.YZPlotArea.lower()
            self.plotOptBias()
            

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
            if pos > self.yMax or pos < self.yMin:
                self.XZPlot.clear()
            else:
                p = int(abs((pos - self.yMin)) / self.yscale)
                xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
                yVals = self.zoomPlot[:,p]
                self.XZPlot.plot(x = xVals, y = yVals, pen = 0.5)
            self.lineYVals = yVals
            self.lineXVals = xVals


    def updateYZPlot(self, pos):
        index = self.vhSelect.currentIndex()
        print index
        if index == 0:
            pass
        elif index == 1:
            self.YZPlot.clear()
            if pos > self.xMax or pos < self.xMin:
                self.YZPlot.clear()
            else:
                p = int(abs((pos - self.xMin)) / self.xscale)
                xVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
                yVals = self.zoomPlot[p]
                self.YZPlot.plot(x = xVals, y = yVals, pen = 0.5)
            self.lineYVals = yVals
            self.lineXVals = xVals
                
    def closeEvent(self, e):
        self.window.zoom.setEnabled(True)



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