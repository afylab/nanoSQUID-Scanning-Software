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
from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView

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


#####GradSet
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

        
#####Sensitivity

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

#####Plotter

class Plotter(QtGui.QMainWindow, Ui_Plotter):
    def __init__(self, reactor, parent = None):
        super(Plotter, self).__init__()
        
        self.reactor = reactor
        self.setupUi(self)

        self.pushButton_trSelect.hide()

        self.setupPlots()

        self.pushButton_refresh.setEnabled(False)
        self.diamCalc.setEnabled(False)
        self.gradient.setEnabled(False)
        self.subtract.setEnabled(False)
        self.sensitivity.setEnabled(False)
        self.zoom.setEnabled(False)
        
        self.lineEdit_vCutPos.editingFinished.connect(self.SetupLineCutverticalposition)
        self.lineEdit_hCutPos.editingFinished.connect(self.SetupLineCuthorizontalposition)

        self.saveMenu = QtGui.QMenu()
        twoDSave = QtGui.QAction("Save 2D plot", self)
        twoDSave.triggered.connect(self.matPlot)
        oneDSaveh = QtGui.QAction("Save horizontal line cut", self)
        oneDSaveh.triggered.connect(self.matLinePloth)
        oneDSavev = QtGui.QAction("Save vertical line cut", self)
        oneDSavev.triggered.connect(self.matLinePlotv)
        self.saveMenu.addAction(twoDSave)
        self.saveMenu.addAction(oneDSaveh)
        self.saveMenu.addAction(oneDSavev)
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

        #####Functions that subtract the data
        self.subtractMenu = QtGui.QMenu()
        subOverallAvg = QtGui.QAction( "Subtract overall average", self)
        subXAvg = QtGui.QAction( "Subtract X average", self)
        subYAvg = QtGui.QAction( "Subtract Y average", self)
        subPlane = QtGui.QAction( "Subtract planar fit", self)
        subOverallQuad = QtGui.QAction( "Subtract overall quadratic fit", self)
        subXQuad = QtGui.QAction( "Subtract X quadratic fit", self)
        subYQuad = QtGui.QAction( "Subtract Y quadratic fit", self)
        subOverallAvg.triggered.connect(self.subtractOverallAvg)
        subXAvg.triggered.connect(self.subtractXAvg)
        subYAvg.triggered.connect(self.subtractYAvg)
        subPlane.triggered.connect(self.subtractPlane)
        subOverallQuad.triggered.connect(self.subtractOverallQuad)
        subXQuad.triggered.connect(self.subtractXQuad)
        subYQuad.triggered.connect(self.subtractYQuad)
        self.subtractMenu.addAction(subOverallAvg)
        self.subtractMenu.addAction(subXAvg)
        self.subtractMenu.addAction(subYAvg)
        self.subtractMenu.addAction(subPlane)
        self.subtractMenu.addAction(subOverallQuad)
        self.subtractMenu.addAction(subXQuad)
        self.subtractMenu.addAction(subYQuad)
        self.subtract.setMenu(self.subtractMenu)
        
        self.trSelectMenu = QtGui.QMenu()
        showTrace = QtGui.QAction("Plot Trace", self)
        showRetrace = QtGui.QAction("Plot Retrace", self)
        self.trSelectMenu.addAction(showTrace)
        self.trSelectMenu.addAction(showRetrace)
        showTrace.triggered.connect(self.plotTrace)
        showRetrace.triggered.connect(self.plotRetrace)
        self.pushButton_trSelect.setMenu(self.trSelectMenu)


        # self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        self.pushButton_lockratio.clicked.connect(self.ToggleAspectRatio)
        self.sensitivity.clicked.connect(self.promptSensitivity)
        self.zoom.clicked.connect(self.zoomArea)
        self.pushButton_loadData.clicked.connect(self.browseDV)
        self.pushButton_refresh.clicked.connect(self.refreshPlot)
        self.addPlot.clicked.connect(self.newPlot)

        self.Data = None
        self.PlotData = None
        self.dv = None
        self.cxn = None
        self.file = None
        self.directory = None
        self.got_util = False
        self.numPlots = 0
        self.numZoomPlots = 0
        
        self.aspectLocked=False

    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.gen_dv = dict['servers']['local']['dv']
            
            from labrad.wrappers import connectAsync
            self.cxn_dv = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn_dv.data_vault

        except:
            pass

    def disconnectLabRAD(self):
        self.cxn = False
        self.cxn_dv = False
        self.gen_dv = False
        self.dv = False
        
    def moveDefault(self):
        self.move(550,10)

######This part is awfully wierd, revise when see it.############
    def matLinePloth(self):
        if not self.PlotData is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genLineMatFileh(fold)
                
    def genLineMatFileh(self, fold):
        XZyData = np.asarray(self.LineCutXZYVals)
        XZxData = np.asarray(self.LineCutXZXVals)

        
        xData, yData = XZxData, XZyData ###This part need to be modified
        
        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None
        
    def matLinePlotv(self):
        if not self.PlotData is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genLineMatFilev(fold)
                
    def genLineMatFilev(self, fold):
        YZyData = np.asarray(self.LineCutYZYVals)
        YZxData = np.asarray(self.LineCutYZXVals)
        
        xData, yData = YZxData, YZyData ###This part need to be modified
        
        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None
        

    def matPlot(self):
        if not self.PlotData is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genMatFile(fold)

    def genMatFile(self, fold):
        t = time.time()
        xVals = np.linspace(self.xMin, self.xMax, int(self.xPoints))
        yVals = np.linspace(self.yMin, self.yMax, int(self.yPoints))
        xInd, yInd = np.linspace(0,     self.xPoints - 1,    int(self.xPoints)), np.linspace(0,    self.yPoints - 1, int(self.yPoints))

        zX, zY, zXI, zYI = np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)]), np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)])
        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.PlotData.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None
##################
   
################## This part create a window on the plot and you can drage it around, click on it will rescale the plot
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
            self.plotZoom = self.PlotData[x1:x2, y1:y2]
            self.dataZoom = np.asarray([])
            self.indZoomVars = []
            self.depZoomVars = []
            for k in range(x1, x2):
                if len(self.dataZoom)==0:
                    self.dataZoom = self.Data[int(k*self.yPoints + y1) :int(k*self.yPoints + y2)]
                else:
                    self.dataZoom = np.vstack((self.dataZoom, self.Data[int(k*self.yPoints + y1) :int(k*self.yPoints + y2)]))
                
            for i in range(0, self.comboBox_xAxis.count()):
                self.indZoomVars.append(self.comboBox_xAxis.itemText(i))
            for i in range(0, self.comboBox_zAxis.count()):
                self.depZoomVars.append(self.comboBox_zAxis.itemText(i))
            title= str(self.plotTitle.text())
            self.indXVar, self.indYVar, self.depVar = self.comboBox_xAxis.currentText(), self.comboBox_yAxis.currentText(), self.comboBox_zAxis.currentText()
            self.currentIndex = [self.comboBox_xAxis.currentIndex(), self.comboBox_yAxis.currentIndex(), self.comboBox_zAxis.currentIndex()]        
            self.zoomExtent = [bounds.x(), bounds.x() + bounds.width(), bounds.y(), bounds.y() + bounds.height(), self.xscale, self.yscale]
            self.zoomPlot = zoomPlot(self.reactor, self.plotZoom, self.dataZoom, self.zoomExtent, self.indZoomVars, self.depZoomVars, self.currentIndex, title, self)
            self.zoom.setEnabled(False)
            self.zoomPlot.show()
##################

    def promptSensitivity(self):
        self.sensPrompt = Sensitivity(self.depVars, self.indVars, self.reactor)
        self.sensPrompt.show()
        self.sensPrompt.accepted.connect(self.plotSens)
        
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
        self.PlotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        self.noiseData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = float(i[z])
            if i[n] != 0:
                self.noiseData[int(i[x]), int(i[y])] = float(i[n])
            else:
                self.noiseData[int(i[x]), int(i[y])] = 1e-5
        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.yPoints * self.datPct)


        for i in range(0, self.PlotData.shape[1]):
            self.PlotData[:, i] = deriv(self.PlotData[:, i], xVals, N, delta)

        if self.NSselect == 1:
            self.PlotData = np.absolute(np.true_divide(self.PlotData , self.noiseData))
        else:
            self.PlotData = np.absolute(np.true_divide(self.noiseData , self.PlotData ))
            self.PlotData = np.clip(self.PlotData, 0, 1e3)

            
            if self.unitSelect == 2:
                gain, bw = self.sensPrompt.sensConv()[0], self.sensPrompt.sensConv()[1]
                self.PlotData = np.true_divide(self.PlotData, (gain * np.sqrt(1000 *bw)))
                self.PlotData = np.clip(self.PlotData, 0, 1e3)
                
        avg = np.average(self.PlotData)
        std = np.std(self.PlotData)

        self.mainPlot.setImage(self.PlotData, autoRange = True , levels = (avg - std, avg+std), autoHistogramRange = False, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.mainPlot.addItem(self.vLine)
        self.mainPlot.addItem(self.hLine)
        self.vLine.setValue(self.xMin)
        self.hLine.setValue(self.yMin)    
        if self.NSselect == 1:
            self.label_plotType.setText('Plotted sensitivity.')
            self.vhSelect.addItem('Maximum Sensitivity')
        else:
            self.label_plotType.setText('Plotted field noise.')    
            self.vhSelect.addItem('Minimum Noise')
            self.vhSelect.addItem('Optimal Bias')
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.ResetLineCutPlots()

    def plotMaxSens(self):
        if self.NSselect == 1:
            maxSens = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.PlotData.shape[0]):
                maxSens = np.append(maxSens, np.amax(self.PlotData[i]))
            self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.XZPlot.setLabel('left', 'Maximum Relative Sensitivity')
            self.XZPlot.plot(x = bVals, y = maxSens,pen = 0.5)
            self.lineYVals = maxSens
            self.lineXVals = bVals
        else:
            minNoise = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.PlotData.shape[0]):
                minNoise = np.append(minNoise, np.amin(self.PlotData[i]))
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
        for i in range(0, self.PlotData.shape[0]):
            arg = np.argmin(self.PlotData[i])
            minNoise = np.append(minNoise, vVals[arg])
        self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.XZPlot.setLabel('left', 'Optimal Bias', units = 'V')
        self.XZPlot.plot(x = bVals, y = minNoise,pen = 0.5)
        self.lineYVals = minNoise
        self.lineXVals = bVals

    def Ic_ParaRes(self):
        for i in self.Data:
            pass
        for i in range(0, self.PlotData.shape[0]):
            V_raw = self.PlotData[i]

        l = int(len(self.indVars) / 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + len(self.indVars) 
        self.viewBig.setLabel('left', text=self.comboBox_yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.comboBox_xAxis.currentText())
        self.XZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.comboBox_xAxis.currentText())
        self.YZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.comboBox_yAxis.currentText())
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
        self.PlotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = i[z]

    def xDeriv(self):
        if self.PlotData is None:
            self.label_plotType.setText("Please plot data.")
            self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        else:
            self.gradient.setFocusPolicy(QtCore.Qt.StrongFocus)
            xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
            delta = abs(self.xMax - self.xMin) / self.xPoints
            N = int(self.xPoints * self.datPct)
            if N < 2:
                self.label_plotType.setText("Lanczos window too \nsmall.")
                self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")

            else:
                for i in range(0, self.PlotData.shape[1]):
                    self.PlotData[:, i] = deriv(self.PlotData[:,i], xVals, N, delta)    
                self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.label_plotType.setText("Plotted gradient along \nx-axis.")
                self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
                self.ResetLineCutPlots()
                
    def yDeriv(self):
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.yMax - self.yMin) / self.yPoints
        N = int(self.yPoints * self.datPct)
        for i in range(0, self.PlotData.shape[0]):
            self.PlotData[i, :] = deriv(self.PlotData[i,:], yVals, N, delta)    
        self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted gradient along \ny-axis.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.ResetLineCutPlots()
        
    def derivSettings(self):
        self.gradSet = gradSet(self.reactor, self.datPct)
        self.gradSet.show()
        self.gradSet.accepted.connect(self.setLancWindow)
        
    def setLancWindow(self):
        self.datPct = self.gradSet.dataPercent.value() / 100

        
##################Manipulating Plot Data
    def subtractOverallAvg(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Average')
        self.RePlotData()
        
    def subtractXAvg(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Average')
        self.RePlotData()
        
    def subtractYAvg(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Average').T
        self.RePlotData()

    def subtractPlane(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Plane')
        self.RePlotData()

    def subtractOverallQuad(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Quadratic')
        self.RePlotData()

    def subtractXQuad(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Linear')
        self.RePlotData()
    
    def subtractYQuad(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Linear').T
        self.RePlotData()
        
##################

    @inlineCallbacks
    def browseDV(self, c = None):
        try:
            yield self.sleep(0.1)
            self.pushButton_refresh.setEnabled(False)
            self.dvExplorer = dataVaultExplorer(self.dv,self.reactor)
            self.dvExplorer.show()
            self.dvExplorer.accepted.connect(lambda: self.loadData(self.reactor))
            self.dvExplorer.rejected.connect(self.reenableRefresh)
        except Exception as inst:
            print inst

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
            self.pushButton_refresh.setEnabled(True)

    def split(self, arr, cond):
      return [arr[cond], arr[~cond]]

    def ClearcomboBox(self):
        self.comboBox_xAxis.clear()
        self.comboBox_yAxis.clear()
        self.comboBox_zAxis.clear()
      
    def ClearData(self):
        self.Data = None
        self.traceData = None
        self.retraceData = None

    def ParseDatainfo(self):#Read the data structure and determine the strategy for reading it
        try:
            DataInfo = self.dvExplorer.dataSetInfo()
            self.file = DataInfo[0]
            print "DataInfo"
            self.directory = DataInfo[1]
            self.indVars = DataInfo[2][0]
            print "Independent Variables:", self.indVars
            self.depVars =DataInfo[2][1]
            print "Dependent Variables:", self.depVars

            self.TraceFlag = None #None for no Trace/Retrace, 0 for trace, 1 for retrace
            self.NumberofindexVariables = 0
            
            for i in self.indVars:
                if i == 'Trace Index' or i == 'Retrace Index':
                    self.TraceFlag = 0 #default set traceflag to trace
            for i in self.indVars:
                if "index" in i or "Index" in i:
                    self.NumberofindexVariables +=1
            
            print "Parsing data finished"
            
            if self.TraceFlag != None:
                print "Contains trace/retrace"
            elif self.TraceFlag == None:
                print "No trace/retrace"
                
            if self.NumberofindexVariables != 0:
                print "Contains index", self.NumberofindexVariables
            else:
                print "No index"

            if len(self.indVars)-self.NumberofindexVariables == 1:
                print "Data is 1D"
                self.DataPlotType = "1DPlot"
            else:
                print "Data is 2D"
                self.DataPlotType = "2DPlot"

        except Exception as inst:
            print inst

    @inlineCallbacks
    def ReadData(self):#Read all the data in datavault and stack them in order
        try:
            t1 = time.time()
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
            
            print 'Get Set Finished'
            t = time.time()
            print 'Time taken to get set', t - t1
        except Exception as inst:
            print inst

    def AddComboIndex(self):
        try:
            if self.DataPlotType == "2DPlot":
                for i in self.indVars[self.NumberofindexVariables: len(self.indVars)]:
                    self.comboBox_xAxis.addItem(i)
                    self.comboBox_yAxis.addItem(i)
                    
            if self.DataPlotType == "1DPlot":
                self.comboBox_xAxis.addItem(self.indVars[self.NumberofindexVariables])
        
            for i in self.depVars:
                    self.comboBox_zAxis.addItem(i)
        except Exception as inst:
            print inst
            
    def SetupTitle(self):            #Retrace index is 0 for trace, 1 for retrace
        if self.TraceFlag == 0:
            Title = self.file + "(Trace)"
        elif self.TraceFlag == 1:
            Title = self.file + "(Retrace)"
        elif self.TraceFlag == None:
            Title = self.file
        self.plotTitle.setText(Title)
        self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(131,131,131); font: 11pt;}")

    def ProcessData(self):
        try:
            if self.TraceFlag == 0 or self.TraceFlag == 1:
                self.indVars=self.indVars[1::]
                self.NumberofindexVariables -=1
                self.traceData, self.retraceData = self.split(self.Data, self.Data[:,0] == 1)
                self.traceData = np.delete(self.traceData,0,1)
                self.retraceData = np.delete(self.retraceData,0,1)
                if self.TraceFlag == 0:
                    self.Data = self.traceData
                elif self.TraceFlag == 1:
                    self.Data = self.retraceData

            elif self.TraceFlag == None and self.NumberofindexVariables == 1:
                pass
            else:
                pt = self.mapToGlobal(QtCore.QPoint(410,-10))
                QtGui.QToolTip.showText(pt, 'Data set format is incompatible with the plotter.')
                
        except exceptions as inst:
            print inst
        

            
    @inlineCallbacks
    def loadData(self, c):
        try:
            
            self.ClearcomboBox()
        
            self.label_plotType.setText("\nLoading data...")
            self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
            
            #Initialized data set to none
            self.ClearData()
        
            #Determine the Data Structure, there can be Trace/Retrace or Index/nonIndex
            self.ParseDatainfo()
            #self.TraceFlag gives whether there are trace, self.NumberofindexVariables gives the number of index and should also be where the data starts in self.Data,   self.DataPlotType gives the type of DataPlot
        
            self.SetupTitle()
            
            yield self.ReadData()
            
            self.ProcessData()
        
            ### Assumptions, we have trace/retrace for only 2DPlot
            ### Assumptions, index are in the beginning of the lists
            self.AddComboIndex()
                
            self.mainPlot.clear()
            self.pushButton_refresh.setEnabled(True)
            self.diamCalc.setEnabled(True)
            self.gradient.setEnabled(True)
            self.subtract.setEnabled(True)
            self.sensitivity.setEnabled(True)
            
            if self.TraceFlag == None:
                self.pushButton_trSelect.hide()
            else:
                self.pushButton_trSelect.show()
                
            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            self.label_plotType.setText("")
            self.pushButton_refresh.setToolTip('Data set loaded. Select axes and click refresh to plot.')
            QtGui.QToolTip.showText(pt, 'Data set loaded. Select axes and click refresh to plot.')
            self.zoom.setEnabled(False)
            self.ResetLineCutPlots()
            self.label_plotType.clear()            
        except Exception as inst:
                print 'Following error was thrown: '
                print inst
                print 'Error thrown on line: '
                print sys.exc_traceback.tb_lineno
                
    def SetPlotLabel(self):
        self.viewBig.setLabel('left', text=self.comboBox_yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.comboBox_xAxis.currentText())
        self.XZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.comboBox_xAxis.currentText())
        self.YZPlot.setLabel('left', self.comboBox_yAxis.currentText())
        self.YZPlot.setLabel('bottom',self.comboBox_zAxis.currentText())

    def SetupPlotParameter(self):
        self.xMax = np.amax(self.Data[::,self.NumberofindexVariables+self.xIndex])
        self.xMin = np.amin(self.Data[::,self.NumberofindexVariables+self.xIndex])
        self.deltaX = self.xMax - self.xMin
        self.xPoints = np.amax(self.Data[::,self.xIndex])+1  #look up the index
        self.x0, self.x1 = self.xMin, self.xMax
        self.xscale  = (self.x1-self.x0) / self.xPoints 
        self.yMin = 0.0

        
        
        if self.DataPlotType == "2DPlot":
            self.yMax = np.amax(self.Data[::,self.NumberofindexVariables+self.yIndex])
            self.yMin = np.amin(self.Data[::,self.NumberofindexVariables+self.yIndex])
            self.deltaY = self.yMax - self.yMin
            self.yPoints = np.amax(self.Data[::,self.yIndex])+1
            self.y0, self.y1 = self.yMin, self.yMax
            self.yscale = (self.y1-self.y0) / self.yPoints

    def SetupPlotData(self):
        try:
            if self.DataPlotType == "2DPlot":
                self.PlotData = np.zeros([int(self.xPoints), int(self.yPoints)])
                for i in self.Data:
                    if self.comboBox_yAxis.currentText() == "None":
                        self.PlotData[int(i[self.xIndex]), 0] = i[self.zIndex]
                    else:
                        self.PlotData[int(i[self.xIndex]), int(i[self.yIndex])] = i[self.zIndex]
            elif self.DataPlotType == "1DPlot":
                self.PlotData = [[],[]] #0 for x, 1 for y
                for i in self.Data:
                    self.PlotData[0].append(i[self.NumberofindexVariables])
                    self.PlotData[1].append(i[self.zIndex])

        except Exception as inst:
            print inst

    def Plot_Data(self):
        if self.DataPlotType == "2DPlot":
            self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.ResetLineCutPlots()
            self.zoom.setEnabled(True)

        elif self.DataPlotType == "1DPlot":
            self.LineCutXZYVals = self.PlotData[1]
            self.LineCutXZXVals = self.PlotData[0]
            self.XZPlot.plot(x = self.LineCutXZXVals, y = self.LineCutXZYVals, pen = 0.5)
            
    def refreshPlot(self):
        try:
            self.ClearLineCutPlot()

            if self.TraceFlag == 0:
                self.Data = self.traceData
            elif self.TraceFlag == 1:
                self.Data = self.retraceData

            self.xIndex = self.comboBox_xAxis.currentIndex()
            self.yIndex = self.comboBox_yAxis.currentIndex()
            self.zIndex = self.comboBox_zAxis.currentIndex() + len(self.indVars) 
            
            self.SetPlotLabel()
            self.SetupPlotParameter()
            self.SetupPlotData()

            self.Plot_Data()

            self.SetupTitle()
            
            self.label_plotType.clear()
        except Exception as inst:
            print inst
        
    def RePlotData(self):
        self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])

    def plotTrace(self):
        self.TraceFlag = 0
        self.refreshPlot()
    
    def plotRetrace(self):
        self.TraceFlag = 1
        self.refreshPlot()

    def ResetLineCutPlots(self):
        if self.PlotData is None:
            pass
        else:
            self.vLine.setValue(self.xMin)
            self.hLine.setValue(self.yMin)
            self.verticalposition=self.xMin
            self.horizontalposition=self.yMin
            self.ClearLineCutPlot()

##################line Cut Related functions
    def SetupLineCutverticalposition(self):
        try:
            dummystr=str(self.lineEdit_vCutPos.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float):
                self.verticalposition=dummyval
            self.ChangeLineCutValue("")
        except Exception as inst:
            print inst
            
    def SetupLineCuthorizontalposition(self):
        try:
            dummystr=str(self.lineEdit_hCutPos.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float):
                self.horizontalposition=dummyval
            self.ChangeLineCutValue("")
        except Exception as inst:
            print inst
            
    def ChangeLineCutValue(self, LineCut):
        try:
            if LineCut == self.vLine:
                self.verticalposition=LineCut.value()
            if LineCut == self.hLine:
                self.horizontalposition=LineCut.value()
                
            self.lineEdit_vCutPos.setText(formatNum(self.verticalposition))
            self.lineEdit_hCutPos.setText(formatNum(self.horizontalposition))
            self.MoveLineCut()
            self.updateLineCutPlot()
        except Exception as inst:
            print inst
            
    def MoveLineCut(self):
        try:
            self.vLine.setValue(float(self.verticalposition))
            self.hLine.setValue(float(self.horizontalposition))
        except Exception as inst:
            print inst
            
    def ClearLineCutPlot(self):
        try:
            self.XZPlot.clear()
            self.YZPlot.clear()
        except Exception as inst:
            print inst
            
    def ConnectLineCut(self):
        try:
            self.vLine.sigPositionChangeFinished.connect(lambda:self.ChangeLineCutValue(self.vLine))
            self.hLine.sigPositionChangeFinished.connect(lambda:self.ChangeLineCutValue(self.hLine))
        except Exception as inst:
            print inst
            
    def SetupLineCut(self):
        try:
            self.viewBig.addItem(self.vLine, ignoreBounds = True)
            self.viewBig.addItem(self.hLine, ignoreBounds =True)
        except Exception as inst:
            print inst
            
    def Setup1DPlot(self, Plot, Layout ):
        try:
            Plot.setGeometry(QtCore.QRect(0, 0, 635, 200))
            Plot.showAxis('right', show = True)
            Plot.showAxis('top', show = True)
            Layout.addWidget(Plot)
        except Exception as inst:
            print inst

    def setupPlots(self):
        try:
            self.vLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
            self.hLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
          
            self.viewBig = pg.PlotItem(name = "Plot")
            self.viewBig.showAxis('top', show = True)
            self.viewBig.showAxis('right', show = True)
            self.viewBig.setAspectLocked(lock = False, ratio = 1)
            self.mainPlot = pg.ImageView(parent = self.frame_mainPlotArea, view = self.viewBig)
            self.mainPlot.setGeometry(QtCore.QRect(0, 0, 750, 450))
            self.mainPlot.ui.menuBtn.hide()
            self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
            self.mainPlot.ui.roiBtn.hide()
            self.mainPlot.ui.menuBtn.hide()
            self.viewBig.setAspectLocked(False)
            self.viewBig.invertY(False)
            self.viewBig.setXRange(-1.25, 1.25)
            self.viewBig.setYRange(-10, 10)
            self.frame_mainPlotArea.close()
            self.Layout_mainPlotArea.addWidget(self.mainPlot)
          
            self.XZPlot = pg.PlotWidget(parent = self.frame_XZPlotArea)
            self.Setup1DPlot(self.XZPlot ,self.Layout_XZPlotArea)
          
            self.YZPlot = pg.PlotWidget(parent = self.frame_YZPlotArea)
            self.Setup1DPlot(self.YZPlot ,self.Layout_YZPlotArea)
            
            self.SetupLineCut()
            self.ConnectLineCut()
        except Exception as inst:
            print inst
            
    def updateLineCutPlot(self):
        try:
            self.ClearLineCutPlot()
            if self.horizontalposition > self.y1 or self.horizontalposition < self.y0:
                self.XZPlot.clear()
            else:
                yindex = int(abs((self.horizontalposition - self.y0)) / self.yscale)
                self.LineCutXZXVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
                self.LineCutXZYVals = self.PlotData[:,yindex]
                self.XZPlot.plot(x = self.LineCutXZXVals, y = self.LineCutXZYVals, pen = 0.5)
         
            if self.verticalposition > self.x1 or self.verticalposition < self.x0:
                self.YZPlot.clear()
            else:
                xindex = int(abs((self.verticalposition - self.x0)) / self.xscale)
                self.LineCutYZXVals = self.PlotData[xindex]
                self.LineCutYZYVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
                self.YZPlot.plot(x = self.LineCutYZXVals, y = self.LineCutYZYVals, pen = 0.5)
        except Exception as inst:
            print inst

    def ToggleAspectRatio(self):
        self.aspectLocked = not self.aspectLocked
        if self.aspectLocked:
            self.viewBig.setAspectLocked(False)
            self.pushButton_lockratio.setStyleSheet("""#pushButton_lockratio{menu-indicator:{image:none}}

#pushButton_lockratio{
image:url(:/nSOTScanner/Pictures/ratio.png);
background: black;
border: 0px solid rgb(95,107,166);
}
""")
        else:
            self.viewBig.setAspectLocked(True, ratio = 1)
            self.pushButton_lockratio.setStyleSheet("""#pushButton_lockratio{menu-indicator:{image:none}}

#pushButton_lockratio{
image:url(:/nSOTScanner/Pictures/ratio.png);
background: black;
border: 2px solid rgb(95,107,166);
}
""")            
            
    def newPlot(self):
        try:
            self.numPlots += 1
            self.newplot=subPlotter(self.reactor, self.dv, None)
            self.newplot.show()
            self.newplot.setWindowTitle('subPlotter ' + str(self.numPlots))
            
        except Exception as inst:
            print inst
            
class subPlotter(Plotter):
    def __init__(self, reactor, datavault, parent = None):
        super(Plotter, self).__init__()
        
        self.reactor = reactor
        self.setupUi(self)

        self.pushButton_trSelect.hide()

        self.setupPlots()

        self.pushButton_refresh.setEnabled(False)
        self.diamCalc.setEnabled(False)
        self.gradient.setEnabled(False)
        self.subtract.setEnabled(False)
        self.sensitivity.setEnabled(False)
        self.zoom.setEnabled(False)
        
        self.lineEdit_vCutPos.editingFinished.connect(self.SetupLineCutverticalposition)
        self.lineEdit_hCutPos.editingFinished.connect(self.SetupLineCuthorizontalposition)

        self.saveMenu = QtGui.QMenu()
        twoDSave = QtGui.QAction("Save 2D plot", self)
        twoDSave.triggered.connect(self.matPlot)
        oneDSaveh = QtGui.QAction("Save horizontal line cut", self)
        oneDSaveh.triggered.connect(self.matLinePloth)
        oneDSavev = QtGui.QAction("Save vertical line cut", self)
        oneDSavev.triggered.connect(self.matLinePlotv)
        self.saveMenu.addAction(twoDSave)
        self.saveMenu.addAction(oneDSaveh)
        self.saveMenu.addAction(oneDSavev)
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

        #####Functions that subtract the data
        self.subtractMenu = QtGui.QMenu()
        subOverallAvg = QtGui.QAction( "Subtract overall average", self)
        subXAvg = QtGui.QAction( "Subtract X average", self)
        subYAvg = QtGui.QAction( "Subtract Y average", self)
        subPlane = QtGui.QAction( "Subtract planar fit", self)
        subOverallQuad = QtGui.QAction( "Subtract overall quadratic fit", self)
        subXQuad = QtGui.QAction( "Subtract X quadratic fit", self)
        subYQuad = QtGui.QAction( "Subtract Y quadratic fit", self)
        subOverallAvg.triggered.connect(self.subtractOverallAvg)
        subXAvg.triggered.connect(self.subtractXAvg)
        subYAvg.triggered.connect(self.subtractYAvg)
        subPlane.triggered.connect(self.subtractPlane)
        subOverallQuad.triggered.connect(self.subtractOverallQuad)
        subXQuad.triggered.connect(self.subtractXQuad)
        subYQuad.triggered.connect(self.subtractYQuad)
        self.subtractMenu.addAction(subOverallAvg)
        self.subtractMenu.addAction(subXAvg)
        self.subtractMenu.addAction(subYAvg)
        self.subtractMenu.addAction(subPlane)
        self.subtractMenu.addAction(subOverallQuad)
        self.subtractMenu.addAction(subXQuad)
        self.subtractMenu.addAction(subYQuad)
        self.subtract.setMenu(self.subtractMenu)
        
        self.trSelectMenu = QtGui.QMenu()
        showTrace = QtGui.QAction("Plot Trace", self)
        showRetrace = QtGui.QAction("Plot Retrace", self)
        self.trSelectMenu.addAction(showTrace)
        self.trSelectMenu.addAction(showRetrace)
        showTrace.triggered.connect(self.plotTrace)
        showRetrace.triggered.connect(self.plotRetrace)
        self.pushButton_trSelect.setMenu(self.trSelectMenu)


        # self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        self.pushButton_lockratio.clicked.connect(self.ToggleAspectRatio)
        self.sensitivity.clicked.connect(self.promptSensitivity)
        self.zoom.clicked.connect(self.zoomArea)
        self.pushButton_loadData.clicked.connect(self.browseDV)
        self.pushButton_refresh.clicked.connect(self.refreshPlot)
        self.addPlot.clicked.connect(self.newPlot)

        self.Data = None
        self.PlotData = None
        self.dv = datavault
        self.cxn = None
        self.file = None
        self.directory = None
        self.got_util = False
        self.numPlots = 0
        self.numZoomPlots = 0
        
        self.aspectLocked=False
        
        self.addPlot.hide()
        
class editDataInfo(QtGui.QDialog, Ui_EditDataInfo):
    def __init__(self, dataset, dv, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(editDataInfo, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)

        self.dv = dv
        self.dataSet = dataset

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
    def __init__(self, dv, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(dataVaultExplorer, self).__init__(parent)
        self.setupUi(self)

        self.reactor = reactor
        self.dv = dv 


        self.currentDir.setReadOnly(True)
        self.currentFile.setReadOnly(True)
        self.curDir = ''
        try:
            self.popDirs(self.reactor)
        except Exception as inst:
            print 'Following error was thrown: '
            print inst
            print 'Error thrown on line: '
            print sys.exc_traceback.tb_lineno

        self.dirList.itemDoubleClicked.connect(self.updateDirs)
        self.fileList.itemClicked.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(self.displayInfo)
        self.back.clicked.connect(self.backUp)
        self.home.clicked.connect(self.goHome)
        self.pushButton_dvexplorer_refresh.clicked.connect(self.popDirs)
        self.addDir.clicked.connect(self.makeDir)
        self.select.clicked.connect(self.selectDirFile)
        self.cancelSelect.clicked.connect(self.closeWindow)

    @inlineCallbacks
    def popDirs(self, c = None):
        try:
            self.dirList.clear()
            self.fileList.clear()
        except Exception as inst:
            print 'Following error was thrown: '
            print inst
            print 'Error thrown on line: '
            print sys.exc_traceback.tb_lineno
        try:
            l = yield self.dv.dir()
        except Exception as inst:
            print 'Following error was thrown: '
            print inst
            print 'Error thrown on line: '
            print sys.exc_traceback.tb_lineno
        try:
            for i in l[0]:
                self.dirList.addItem(i)
            for i in l[1]:
                self.fileList.addItem(i)
        except Exception as inst:
            print 'Following error was thrown: '
            print inst
            print 'Error thrown on line: '
            print sys.exc_traceback.tb_lineno
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
        self.editDataInfo = editDataInfo(dataSet, self.dv, c)
        self.editDataInfo.show()

    def fileSelect(self):
        file = self.fileList.currentItem()
        self.currentFile.setText(file.text())

    def dataSetInfo(self):
        info =[self.file, self.directory, self.variables]
        return info

    @inlineCallbacks
    def selectDirFile(self, c):
        self.file = str(self.currentFile.text())
        self.directory = yield self.dv.cd()
        try:
            yield self.dv.open(self.file)
        except Exception as inst:
            print 'Following error was thrown: '
            print inst
            print 'Error thrown on line: '
            print sys.exc_traceback.tb_lineno
        variables = yield self.dv.variables()
        self.indVars = []
        self.depVars = []
        for i in variables[0]:
            self.indVars.append(str(i[0]))
        for i in variables[1]:
            self.depVars.append(str(i[0]))
        self.variables = [self.indVars, self.depVars]
        
        self.accept()

    def closeWindow(self):
        self.reject()

class subPlot(QtGui.QMainWindow, Ui_Plotter):
    def __init__(self, dv,    numPlots, reactor, parent = None):
        super(subPlot, self).__init__(parent)
        self.setupUi(self)

        self.reactor = reactor
        self.dv = dv
        self.numPlots = numPlots
        self.window = parent
        self.setWindowTitle('Subplot ' + str(self.numPlots))

        self.pushButton_trSelect.hide()


        self.setupPlots()



        self.pushButton_refresh.setEnabled(False)
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
        self.pushButton_trSelect.setMenu(self.trSelectMenu)


        self.sensitivity.clicked.connect(self.promptSensitivity)
        self.zoom.clicked.connect(self.zoomArea)
        self.pushButton_loadData.clicked.connect(self.browseDV)
        self.pushButton_refresh.clicked.connect(self.refreshPlot)
        self.addPlot.clicked.connect(self.newPlot)
        

        self.Data = None
        self.PlotData = None
        self.file = None
        self.directory = None
        self.got_util = False
        self.numPlots = 0
        self.numZoomPlots = 0
    
      
    def matLinePlot(self):
        if not self.PlotData is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genLineMatFile(fold)
                
    def genLineMatFile(self, fold):
        yData = np.asarray(self.lineYVals)
        xData = np.asarray(self.lineXVals)
        
        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None        

    def matPlot(self):
        if not self.PlotData is None:
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genMatFile(fold)

    def genMatFile(self, fold):
        t = time.time()
        xVals = np.linspace(self.xMin, self.xMax, int(self.xPoints))
        yVals = np.linspace(self.yMin, self.yMax, int(self.yPoints))
        xInd, yInd = np.linspace(0,     self.xPoints - 1,    int(self.xPoints)), np.linspace(0,    self.yPoints - 1, int(self.yPoints))

        zX, zY, zXI, zYI = np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)]), np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)])
        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.PlotData.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        savename = fold.split("/")[-1].split('.mat')[0]
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
            self.plotZoom = self.PlotData[x1:x2, y1:y2]
            self.dataZoom = np.asarray([])
            self.indZoomVars = []
            self.depZoomVars = []
            for k in range(x1, x2):
                if len(self.dataZoom)==0:
                    self.dataZoom = self.Data[int(k*self.yPoints + y1) :int(k*self.yPoints + y2)]
                else:
                    self.dataZoom = np.vstack((self.dataZoom, self.Data[int(k*self.yPoints + y1) :int(k*self.yPoints + y2)]))
                
            for i in range(0, self.comboBox_xAxis.count()):
                self.indZoomVars.append(self.comboBox_xAxis.itemText(i))
            for i in range(0, self.comboBox_zAxis.count()):
                self.depZoomVars.append(self.comboBox_zAxis.itemText(i))
            title= str(self.plotTitle.text())
            self.indXVar, self.indYVar, self.depVar = self.comboBox_xAxis.currentText(), self.comboBox_yAxis.currentText(), self.comboBox_zAxis.currentText()
            self.currentIndex = [self.comboBox_xAxis.currentIndex(), self.comboBox_yAxis.currentIndex(), self.comboBox_zAxis.currentIndex()]        
            self.zoomExtent = [bounds.x(), bounds.x() + bounds.width(), bounds.y(), bounds.y() + bounds.height(), self.xscale, self.yscale]
            self.zoomPlot = zoomPlot(self.reactor, self.plotZoom, self.dataZoom, self.zoomExtent, self.indZoomVars, self.depZoomVars, self.currentIndex, title, self)
            self.zoom.setEnabled(False)
            self.zoomPlot.show()

    def promptSensitivity(self):
        self.sensPrompt = Sensitivity(self.depVars, self.indVars, self.reactor)
        self.sensPrompt.show()
        self.sensPrompt.accepted.connect(self.plotSens)
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
        self.PlotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        self.noiseData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = float(i[z])
            if i[n] != 0:
                self.noiseData[int(i[x]), int(i[y])] = float(i[n])
            else:
                self.noiseData[int(i[x]), int(i[y])] = 1e-5
        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.yPoints * self.datPct)


        for i in range(0, self.PlotData.shape[1]):
            self.PlotData[:, i] = deriv(self.PlotData[:, i], xVals, N, delta)

        if self.NSselect == 1:
            self.PlotData = np.absolute(np.true_divide(self.PlotData , self.noiseData))
        else:
            self.PlotData = np.absolute(np.true_divide(self.noiseData , self.PlotData ))
            self.PlotData = np.clip(self.PlotData, 0, 1e3)

            
            if self.unitSelect == 2:
                gain, bw = self.sensPrompt.sensConv()[0], self.sensPrompt.sensConv()[1]
                self.PlotData = np.true_divide(self.PlotData, (gain * np.sqrt(1000 *bw)))
                self.PlotData = np.clip(self.PlotData, 0, 1e3)
                
        avg = np.average(self.PlotData)
        std = np.std(self.PlotData)

        self.mainPlot.setImage(self.PlotData, autoRange = True , levels = (avg - std, avg+std), autoHistogramRange = False, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.mainPlot.addItem(self.vLine)
        self.mainPlot.addItem(self.hLine)
        self.vLine.setValue(self.xMin)
        self.hLine.setValue(self.yMin)    
        self.vCutPos.setValue(self.xMin)
        self.hCutPos.setValue(self.yMin)
        if self.NSselect == 1:
            self.label_plotType.setText('Plotted sensitivity.')
            self.vhSelect.addItem('Maximum Sensitivity')
        else:
            self.label_plotType.setText('Plotted field noise.')    
            self.vhSelect.addItem('Minimum Noise')
            self.vhSelect.addItem('Optimal Bias')
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def plotMaxSens(self):
        if self.NSselect == 1:
            maxSens = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.PlotData.shape[0]):
                maxSens = np.append(maxSens, np.amax(self.PlotData[i]))
            self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.XZPlot.setLabel('left', 'Maximum Relative Sensitivity')
            self.XZPlot.plot(x = bVals, y = maxSens,pen = 0.5)
            self.lineYVals = maxSens
            self.lineXVals = bVals
        else:
            minNoise = np.array([])
            bVals = np.linspace(self.xMin, self.xMax, self.xPoints)
            self.XZPlot.clear()
            for i in range(0, self.PlotData.shape[0]):
                minNoise = np.append(minNoise, np.amin(self.PlotData[i]))
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
        for i in range(0, self.PlotData.shape[0]):
            arg = np.argmin(self.PlotData[i])
            minNoise = np.append(minNoise, vVals[arg])
        self.XZPlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.XZPlot.setLabel('left', 'Optimal Bias', units = 'V')
        self.XZPlot.plot(x = bVals, y = minNoise,pen = 0.5)
        self.lineYVals = minNoise
        self.lineXVals = bVals

    def Ic_ParaRes(self):
        for i in self.Data:
            pass
        for i in range(0, self.PlotData.shape[0]):
            V_raw = self.PlotData[i]

        l = int(len(self.indVars) / 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + len(self.indVars) 
        self.viewBig.setLabel('left', text=self.comboBox_yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.comboBox_xAxis.currentText())
        self.XZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.comboBox_xAxis.currentText())
        self.YZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.comboBox_yAxis.currentText())
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
        self.PlotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = i[z]

    def xDeriv(self):
        if self.PlotData is None:
            self.label_plotType.setText("Please plot data.")
            self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        else:
            self.gradient.setFocusPolicy(QtCore.Qt.StrongFocus)
            xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
            delta = abs(self.xMax - self.xMin) / self.xPoints
            N = int(self.xPoints * self.datPct)
            if N < 2:
                self.label_plotType.setText("Lanczos window too \nsmall.")
                self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")

            else:
                for i in range(0, self.PlotData.shape[1]):
                    self.PlotData[:, i] = deriv(self.PlotData[:,i], xVals, N, delta)    
                self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.label_plotType.setText("Plotted gradient along \nx-axis.")
                self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
                self.clearPlots()
                
    def yDeriv(self):
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.yMax - self.yMin) / self.yPoints
        N = int(self.yPoints * self.datPct)
        for i in range(0, self.PlotData.shape[0]):
            self.PlotData[i, :] = deriv(self.PlotData[i,:], yVals, N, delta)    
        self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted gradient along \ny-axis.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
        
    def derivSettings(self):
        self.gradSet = gradSet(self.reactor, self.datPct)
        self.gradSet.show()
        self.gradSet.accepted.connect(self.setLancWindow)
        
    def setLancWindow(self):
        self.datPct = self.gradSet.dataPercent.value() / 100

    def subtractAvg(self):
        avg = np.average(self.PlotData)
        self.PlotData = self.PlotData - avg
        self.label_plotType.setText("Plotted offset \nsubtracted data.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
        
    def subtractPlane(self):
        l = int(len(self.indVars) / 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + len(self.indVars) 
        X = np.c_[self.Data[::, l+x], self.Data[::,l+y], np.ones(self.Data.shape[0])]
        Y = np.ndarray.flatten(self.PlotData)
        

        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = self.PlotData[int(i[x]), int(i[y])] - np.dot(C[0], [i[x+l], i[y+l], 1])        
        self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted plane \nsubtracted data.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
        
    def subtractQuad(self):
        l = int(len(self.indVars) / 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + len(self.indVars) 
        X = np.c_[np.ones(self.Data.shape[0]), self.Data[::, [l+x, l+y]], np.prod(self.Data[::, [l+x, l+y]], axis = 1), self.Data[::, [l+x, l+y]]**2]
        Y = np.ndarray.flatten(self.PlotData)
        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = i[z] - np.dot(C[0], [i[x+l]**2, i[y+l]**2, i[l+x]*i[y+l], i[l+x], i[l+y], 1])        
        self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted quadratic \nsubtracted data.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()

    @inlineCallbacks
    def browseDV(self, c = None):
        yield self.sleep(0.1)
        self.pushButton_refresh.setEnabled(False)
        try:
            self.dvExplorer = dataVaultExplorer(self.dv, self.reactor)
            self.dvExplorer.show()
        except Exception as inst:
            print 'Following error was thrown: '
            print inst
            print 'Error thrown on line: '
            print sys.exc_traceback.tb_lineno
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
            self.pushButton_refresh.setEnabled(True)

    def split(self, arr, cond):
      return [arr[cond], arr[~cond]]

    @inlineCallbacks
    def loadData(self, c):
        self.comboBox_xAxis.clear()
        self.comboBox_yAxis.clear()
        self.comboBox_zAxis.clear()

        self.label_plotType.setText("\nLoading data...")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        #Initialized data set to none
        self.Data = None
        self.traceData = None
        self.retraceData = None
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
                self.comboBox_xAxis.addItem(i)
                self.comboBox_yAxis.addItem(i)
            for i in self.depVars:
                self.comboBox_zAxis.addItem(i)
            t = time.time()
            yield self.dv.open(self.file)
            print 'opened set'
            t1 = time.time()
            print t1 - t
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
            self.pushButton_refresh.setEnabled(True)
            self.diamCalc.setEnabled(True)
            self.gradient.setEnabled(True)
            self.subtract.setEnabled(True)
            self.sensitivity.setEnabled(True)
            self.pushButton_trSelect.hide()

            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            self.label_plotType.setText("")
            self.pushButton_refresh.setToolTip('Data set loaded. Select axes and click refresh to plot.')
            QtGui.QToolTip.showText(pt, 'Data set loaded. Select axes and click refresh to plot.')
            self.zoom.setEnabled(False)
            self.clearPlots()
            self.label_plotType.clear()
        #Load a data set with a trace/retrace index
        elif l % 2 == 1 and self.indVars[0] == 'Trace Index' or self.indVars[0] == 'Retrace Index':
            self.indVars = self.indVars[1::]
            for i in self.indVars[int(l / 2): l]:
                self.comboBox_xAxis.addItem(i)
                self.comboBox_yAxis.addItem(i)
            for i in self.depVars:
                self.comboBox_zAxis.addItem(i)
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
            self.pushButton_refresh.setEnabled(True)
            self.diamCalc.setEnabled(True)
            self.gradient.setEnabled(True)
            self.subtract.setEnabled(True)
            self.sensitivity.setEnabled(True)
            self.pushButton_trSelect.show()
            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            self.label_plotType.setText("")
            self.pushButton_refresh.setToolTip('Data set loaded. Select axes and click refresh to plot.')
            QtGui.QToolTip.showText(pt, 'Data set loaded. Select axes and click refresh to plot.')
            self.zoom.setEnabled(False)
            self.clearPlots()
            self.label_plotType.clear()            
        else:
            pt = self.mapToGlobal(QtCore.QPoint(410,-10))
            QtGui.QToolTip.showText(pt, 'Data set format is incompatible with the plotter.')

    def refreshPlot(self):
        if self.vhSelect.count() > 2: 
            self.vhSelect.setCurrentIndex(0)
            while self.vhSelect.count()>2:                
                self.vhSelect.removeItem(2)
        l = int(len(self.indVars) / 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + len(self.indVars) 
        self.viewBig.setLabel('left', text=self.comboBox_yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.comboBox_xAxis.currentText())
        self.XZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.comboBox_xAxis.currentText())
        self.YZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.comboBox_yAxis.currentText())
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
        self.PlotData = np.zeros([int(self.xPoints), int(self.yPoints)])
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = i[z]
        self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
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
        self.label_plotType.clear()
    
    def plotTrace(self):
        self.Data = self.traceData
        self.dataFlag = 0
    
    def plotRetrace(self):
        self.Data = self.retraceData
        self.dataFlag = 1

    def clearPlots(self):
        if self.PlotData is None:
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
        self.mainPlot = pg.ImageView(parent = self.frame_mainPlotArea, view = self.viewBig)
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

        self.XZPlot = pg.PlotWidget(parent = self.frame_XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.frame_YZPlotArea)
        self.YZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.YZPlot.showAxis('right', show = True)
        self.YZPlot.showAxis('top', show = True)
         

    def toggleBottomPlot(self):
        if self.vhSelect.currentIndex() == 0:
            pos = self.hLine.value()
            self.frame_YZPlotArea.lower()
            self.updateXZPlot(pos)
        elif self.vhSelect.currentIndex() == 1:
            pos = self.vLine.value()
            self.frame_XZPlotArea.lower()
            self.updateYZPlot(pos)    
        elif self.vhSelect.currentIndex() ==2:
            self.frame_YZPlotArea.lower()
            self.plotMaxSens()
        elif self.vhSelect.currentIndex() ==3:
            self.frame_YZPlotArea.lower()
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
                yVals = self.PlotData[:,p]
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
                yVals = self.PlotData[p]
                self.YZPlot.plot(x = xVals, y = yVals, pen = 0.5)
                self.lineYVals = yVals 
                self.lineXVals = xVals

    def newPlot(self):
        self.numPlots += 1
        self.newPlot = subPlot(self.dv, self.numPlots, self.reactor, self.window)
        self.newPlot.show()

    def closeEvent(self, e):
        self.close()
        

class zoomPlot(QtGui.QDialog, Ui_ZoomWindow):
    def __init__(self, reactor, PlotData, dataSubset, zoomExtent, indVars, depVars, currentIndex, title, parent = None):
        super(zoomPlot, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)

        self.window = parent

        self.diamFrame.hide()

        self.Data = copy.copy(dataSubset)

        indexOffsets = np.array([])
        for ii in range(0, len(indVars)):
            indexOffsets = np.append(indexOffsets, self.Data[0,ii])
        while len(indexOffsets) != len(self.Data[0]):
            indexOffsets = np.append(indexOffsets, 0)
        self.Data = self.Data - indexOffsets
        self.oData = copy.copy(PlotData)
        self.extent = zoomExtent
        self.xMin, self.xMax = self.extent[0], self.extent[1]
        self.yMin, self.yMax = self.extent[2], self.extent[3]
        self.xscale, self.yscale = self.extent[4], self.extent[5]
        self.xPoints, self.yPoints = self.oData.shape[0], self.oData.shape[1]
        self.indVars = indVars
        self.depVars = depVars

        for i in self.indVars:
            self.comboBox_xAxis.addItem(i)
            self.comboBox_yAxis.addItem(i)
        for i in self.depVars:
            self.comboBox_zAxis.addItem(i)
        self.initIndex = currentIndex
        self.comboBox_xAxis.setCurrentIndex(self.initIndex[0])
        self.comboBox_yAxis.setCurrentIndex(self.initIndex[1])
        self.comboBox_zAxis.setCurrentIndex(self.initIndex[2])

        self.setupPlots()
        
        self.back.clicked.connect(self.revert)

        
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
        

        self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        self.sensitivity.clicked.connect(self.promptSensitivity)
        self.pushButton_refresh.clicked.connect(self.refreshPlot)
        self.vCutPos.valueChanged.connect(self.changeVertLine)
        self.hCutPos.valueChanged.connect(self.changeHorLine)
        
    def revert(self):
        self.clearPlots()
        self.label_plotType.clear()
        self.zoomPlot = self.oData
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted original \ndata selection.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        if self.vhSelect.count() > 2: 
            self.vhSelect.setCurrentIndex(0)
            while self.vhSelect.count()>2:                
                self.vhSelect.removeItem(2)

    def refreshPlot(self):
        
        if self.vhSelect.count() > 2: 
            self.vhSelect.setCurrentIndex(0)
            while self.vhSelect.count()>2:                
                self.vhSelect.removeItem(2)
        l = int(len(self.indVars) * 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + l
        self.xPoints, self.yPoints = int(np.amax(self.Data[::,x])) + 1, int(np.amax(self.Data[::,y])) + 1
        self.viewBig.setLabel('left', text=self.comboBox_yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.comboBox_xAxis.currentText())
        self.XZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.comboBox_xAxis.currentText())
        self.YZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.YZPlot.setLabel('bottom', self.comboBox_yAxis.currentText())
        self.zoomPlot = np.zeros([int(self.xPoints), int(self.yPoints)])
        
        for i in self.Data:
            
            self.zoomPlot[int(i[x]), int(i[y])] = i[z]
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.clearPlots()
        self.label_plotType.clear()    

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
        self.mainPlot = pg.ImageView(parent = self.frame_mainPlotArea, view = self.viewBig)
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

        self.XZPlot = pg.PlotWidget(parent = self.frame_XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.frame_YZPlotArea)
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
        xInd, yInd = np.linspace(0,     self.xPoints - 1,    int(self.xPoints)), np.linspace(0,    self.yPoints - 1, int(self.yPoints))

        zX, zY, zXI, zYI = np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)]), np.ones([1,int(self.yPoints)]), np.ones([1,int(self.xPoints)])
        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.zoomPlot.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None

    def xDeriv(self):

        xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.xPoints * self.datPct)
        for i in range(0, self.zoomPlot.shape[1]):
            self.zoomPlot[:, i] = deriv(self.zoomPlot[:,i], xVals, N, delta)    
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted gradient \nalong x-axis.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def yDeriv(self):

        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.yMax - self.yMin) / self.yPoints
        N = int(self.yPoints * self.datPct)
        for i in range(0, self.zoomPlot.shape[0]):
            self.zoomPlot[i, :] = deriv(self.zoomPlot[i,:], yVals, N, delta)    
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted gradient \nalong y-axis.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
        
    def derivSettings(self):
        self.gradSet = gradSet(self.reactor, self.datPct)
        self.gradSet.show()
        self.gradSet.accepted.connect(self.setLancWindow)
    def setLancWindow(self):
        self.datPct = self.gradSet.dataPercent.value() / 100

    def subtractAvg(self):

        avg = np.average(self.zoomPlot)
        self.zoomPlot = self.zoomPlot - avg
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.xMin, self.yMin],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted offset \nsubtracted data.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractPlane(self):

        l = int(len(self.indVars) * 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + l
        X = np.c_[self.Data[::, l+x], self.Data[::,l+y], np.ones(self.Data.shape[0])]
        Y = np.ndarray.flatten(self.zoomPlot)
        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            self.zoomPlot[int(i[x]), int(i[y])] = self.zoomPlot[int(i[x]), int(i[y])] - np.dot(C[0], [i[x+l], i[y+l], 1])        
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted plane \nsubtracted data.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
    def subtractQuad(self):

        l = int(len(self.indVars) * 2)
        x = self.comboBox_xAxis.currentIndex()
        y = self.comboBox_yAxis.currentIndex()
        z = self.comboBox_zAxis.currentIndex() + l
        X = np.c_[np.ones(self.Data.shape[0]), self.Data[::, [l+x, l+y]], np.prod(self.Data[::, [l+x, l+y]], axis = 1), self.Data[::, [l+x, l+y]]**2]
        Y = np.ndarray.flatten(self.PlotData)
        C = np.linalg.lstsq(X, Y)
        for i in self.Data:
            self.zoomPlot[int(i[x]), int(i[y])] = i[z] - np.dot(C[0], [i[x+l]**2, i[y+l]**2, i[l+x]*i[y+l], i[l+x], i[l+y], 1])        
        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.label_plotType.setText("Plotted quadratic \nsubtracted data.")
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")
        self.clearPlots()
        
    def promptSensitivity(self):
        ind = range(0,len(self.indVars)) + self.indVars
        self.sensPrompt = Sensitivity(self.depVars, ind, self.reactor)
        self.sensPrompt.show()
        self.sensPrompt.accepted.connect(self.plotSens)
        
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
        yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints)
        delta = abs(self.xMax - self.xMin) / self.xPoints
        N = int(self.xPoints * self.datPct)

        for i in range(0, self.zoomPlot.shape[1]):
            self.zoomPlot[:, i] = deriv(self.zoomPlot[:, i], xVals, N, delta)
            for pt in range(0, len(self.zoomPlot[:,i])):
                if self.zoomPlot[pt,i] == 0:
                    
                    self.zoomPlot[pt,i] = 1e-3
                    
        if self.NSselect == 1:
            self.PlotData = np.absolute(np.true_divide(self.zoomPlot , self.noiseData))
        else:
            self.zoomPlot = np.absolute(np.true_divide(self.noiseData , self.zoomPlot ))
            self.zoomPlot = np.clip(self.zoomPlot, 0, 1e3)

            
            if self.unitSelect == 2:
                gain, bw = self.sensPrompt.sensConv()[0], self.sensPrompt.sensConv()[1]
                self.zoomPlot = np.true_divide(self.zoomPlot, (.364 * gain * np.sqrt(1000 *bw)))
                self.zoomPlot = np.clip(self.zoomPlot, 0, 1e3)

        self.mainPlot.setImage(self.zoomPlot, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.mainPlot.addItem(self.vLine)
        self.mainPlot.addItem(self.hLine)
        self.vLine.setValue(self.xMin)
        self.hLine.setValue(self.yMin)    
        self.vCutPos.setValue(self.xMin)
        self.hCutPos.setValue(self.yMin)
        if self.NSselect == 1:
            self.label_plotType.setText('Plotted sensitivity.')
            self.vhSelect.addItem('Maximum Sensitivity')
        else:
            self.label_plotType.setText('Plotted field noise.')    
            self.vhSelect.addItem('Minimum Noise')
            self.vhSelect.addItem('Optimal Bias')
        self.label_plotType.setStyleSheet("QLabel#plotType {color: rgb(131,131,131); font: 9pt;}")    
        
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


    def toggleBottomPlot(self):
        if self.vhSelect.currentIndex() == 0:
            pos = self.hLine.value()
            self.frame_YZPlotArea.lower()
            self.updateXZPlot(pos)

        elif self.vhSelect.currentIndex() == 1:
            pos = self.vLine.value()
            self.frame_XZPlotArea.lower()
            self.updateYZPlot(pos)    

        elif self.vhSelect.currentIndex() ==2:
            self.frame_YZPlotArea.lower()
            self.plotMaxSens()

        elif self.vhSelect.currentIndex() ==3:
            self.frame_YZPlotArea.lower()
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