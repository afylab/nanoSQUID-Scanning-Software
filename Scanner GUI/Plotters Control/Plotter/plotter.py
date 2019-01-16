from __future__ import division
from lanczos import deriv
import os
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
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

path = sys.path[0] + r"\Plotters Control\Plotter"
sys.path.append(path + r'\Sensitivity Prompt')
sys.path.append(path + r'\Gradient Setting')
sys.path.append(path + r'\ZoomWindow')
sys.path.append(path + r'\Data Vault Explorer')
sys.path.append(path + r'\Data Info')
sys.path.append(path + r'\Remove Spike Setting')
sys.path.append(path + r'\Multiplier Window')
sys.path.append(path + r'\Subtract Constant Window')

import sensitivityPrompt
import gradSettings
import zoomWindow
import dvExplorerWindow
import editDatasetInfo
import DespikeSettings
import MultiplierSettings
import ConstantSubtract

axesSelectGUI = path + r"\axesSelect.ui"
plotter = path + r"\plotter.ui"

Ui_Plotter, QtBaseClass = uic.loadUiType(plotter)
Ui_AxesSelect, QtBaseClass = uic.loadUiType(axesSelectGUI)

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

#####Plotter
class Plotter(QtGui.QMainWindow, Ui_Plotter):
    def __init__(self, reactor, datavault, number, parent = None):
        super(Plotter, self).__init__()
        
        try:
            self.reactor = reactor
            self.number = number
            self.dv = datavault
            self.parent = parent

            self.Data = None
            self.PlotData = None
            self.TraceFlag = None
            self.DataType = 'None'
            self.NumberofindexVariables = 0
            self.Title = 'Plotter ' + str(self.number)
            self.directory = None
            self.PlotParameters = {
                'xMax': 0.0,
                'xMin': 0.0,
                'deltaX': 0.0,
                'xPoints': 0.0,
                'xscale': 0.0,
                'yMax': 0.0,
                'yMin': 0.0,
                'deltaY': 0.0,
                'yPoints': 0.0,
                'yscale': 0.0
            }
            self.AreaSelectedParameters = {
                'xMax': 0.0,
                'xMin': 0.0,
                'yMax': 0.0,
                'yMin': 0.0
            }
            self.file = ''
            self.indVars = []
            self.depVars = []
            self.Parameters = {}
            self.comments = ''
            self.Number_PlotData_X, self.Number_PlotData_Y = 0,0
            self.aspectLocked=False
            self.SweepingIndependentAxis=[]
            self.SweepingDirection = ''
            self.got_util = False

            self.setupUi(self)

            self.setupPlots()

            self.editDataInfo = editDatasetInfo.editDataInfo(self.reactor , self)

            self.lineEdit_vCutPos.editingFinished.connect(self.SetupLineCutverticalposition)
            self.lineEdit_hCutPos.editingFinished.connect(self.SetupLineCuthorizontalposition)

            #Function of select an Area file 
            self.pushButton_SelectArea.clicked.connect(self.SelectArea)
            self.AreaSelected = pg.RectROI((0.0 , 0.0), (1,1))
            self.AreaSelected.setAcceptedMouseButtons(QtCore.Qt.RightButton | QtCore.Qt.LeftButton)
            self.AreaSelected.addScaleHandle((1,1), (.5,.5), lockAspect = False)
            self.Average_SelectedArea = 0.0
            self.SelectedAreaShow = False
            self.AreaSelected.sigRegionChangeFinished.connect(self.RefreshAreaSelected)

            #Function of croping a window
            self.pushButton_CropWindow.clicked.connect(lambda: self.CropWindow(self.AreaSelectedParameters['xMin'], self.AreaSelectedParameters['xMax'], self.AreaSelectedParameters['yMin'], self.AreaSelectedParameters['yMax']))

            #Function of saving matlab file 
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

            #Function Taking gradiant
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

            #Function Despiking
            self.AdjacentPoints, self.NumberOfSigma = 3, 5
            self.DespikeSettingWindow = DespikeSettings.DespikeSet(self.reactor, self)
            self.RemoveSpikesMenu = QtGui.QMenu()
            Despike = QtGui.QAction("Remove Spikes", self)
            DespikeSetting = QtGui.QAction("Setting", self)
            Despike.triggered.connect(self.RemoveSpikes)
            DespikeSetting.triggered.connect(self.RemoveSpikesSettings)
            self.RemoveSpikesMenu.addAction(Despike)
            self.RemoveSpikesMenu.addAction(DespikeSetting)
            self.pushButton_Despike.setMenu(self.RemoveSpikesMenu)

            #####Functions that subtract the data
            self.subtractMenu = QtGui.QMenu()
            subOverallAvg = QtGui.QAction( "Subtract overall average", self)
            subOverallAvg.triggered.connect(self.subtractOverallAvg)
            self.subtractMenu.addAction(subOverallAvg)
            self.ConstantSubtracted = 0.0
            self.SubConstantWindow = ConstantSubtract.SubConstantWindow(self.reactor, self)
            subconstant = QtGui.QAction( "Subtract overall constant", self)
            subconstant.triggered.connect(self.ConstantSubtractedWindow)
            self.subtractMenu.addAction(subconstant)
            subPlane = QtGui.QAction( "Subtract planar fit", self)
            subPlane.triggered.connect(self.subtractPlane)
            self.subtractMenu.addAction(subPlane)
            subOverallQuad = QtGui.QAction( "Subtract overall quadratic fit", self)
            subOverallQuad.triggered.connect(self.subtractOverallQuad)
            self.subtractMenu.addAction(subOverallQuad)
            subSelectedAreaAvg = QtGui.QAction( "Subtract selected area average", self)
            subSelectedAreaAvg.triggered.connect(lambda: self.subtractOverallConstant(self.Average_SelectedArea))
            self.subtractMenu.addAction(subSelectedAreaAvg)
            subXAvg = QtGui.QAction( "Subtract X average", self)
            subXAvg.triggered.connect(self.subtractXAvg)
            self.subtractMenu.addAction(subXAvg)
            subYAvg = QtGui.QAction( "Subtract Y average", self)
            subYAvg.triggered.connect(self.subtractYAvg)
            self.subtractMenu.addAction(subYAvg)
            subXLinear = QtGui.QAction( "Subtract X linear fit", self)
            subXLinear.triggered.connect(self.subtractXLinear)
            self.subtractMenu.addAction(subXLinear)
            subYLinear = QtGui.QAction( "Subtract Y linear fit", self)
            subYLinear.triggered.connect(self.subtractYLinear)
            self.subtractMenu.addAction(subYLinear)
            subXQuad = QtGui.QAction( "Subtract X quadratic fit", self)
            subXQuad.triggered.connect(self.subtractXQuad)
            self.subtractMenu.addAction(subXQuad)
            subYQuad = QtGui.QAction( "Subtract Y quadratic fit", self)
            subYQuad.triggered.connect(self.subtractYQuad)
            self.subtractMenu.addAction(subYQuad)
            self.subtract.setMenu(self.subtractMenu)

            self.multiplier = 1.0
            self.MultiplyWindow = MultiplierSettings.MultiplierWindow(self.reactor, self)
            self.pushButton_Multiply.clicked.connect(self.MultiplyDialog)

            #TraceSelect
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
            self.pushButton_Info.clicked.connect(self.displayInfo)

            self.RefreshInterface()

            #Buttons Enable conditions:
            self.EnableCondition= {}
        except Exception as inst:
            print 'Following error was thrown: ', inst
            print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_refresh: (not self.Data is None),
            self.pushButton_loadData: True,
            self.pushButton_trSelect: self.TraceFlag != None and (not self.Data is None),
            self.pushButton_Multiply: (not self.PlotData is None),
            self.pushButton_Despike: (not self.PlotData is None) and '2DPlot' in self.DataType,
            self.pushButton_Info: True,
            self.pushButton_lockratio: (not self.PlotData is None) and '2DPlot' in self.DataType,
            self.zoom: (not self.PlotData is None) and '2DPlot' in self.DataType,
            self.subtract: (not self.PlotData is None) and '2DPlot' in self.DataType,
            self.gradient: (not self.PlotData is None) and '2DPlot' in self.DataType,
            self.sensitivity: (not self.PlotData is None) and '2DPlot' in self.DataType,
            self.diamCalc: False,
            self.savePlot:(not self.PlotData is None),
            self.pushButton_SelectArea: (not self.PlotData is None and '2DPlot' in self.DataType),
            self.pushButton_CropWindow: (not self.PlotData is None and '2DPlot' in self.DataType)
        }
        
    def RefreshInterface(self):
        self.RefreshFileName()
        self.RefreshTitle()
        self.DetermineEnableConditions()
        for button in self.ButtonsCondition:
            self.ProcessButton(button)

    def RefreshFileName(self):#Index is 0 for trace, 1 for retrace
        self.label_FileName.setText(self.file)

    def RefreshTitle(self):
        self.setWindowTitle(self.Title)

    def ProcessButton(self, button):
        button.setEnabled(self.ButtonsCondition[button])

######This part is awfully weird, revise when see it.############
    def matLinePloth(self):
        if (not self.PlotData is None):
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
        if (not self.PlotData is None):
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
        if (not self.PlotData is None):
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genMatFile(fold)

    def genMatFile(self, fold):
        t = time.time()
        xVals = np.linspace(self.PlotParameters['xMin'], self.PlotParameters['xMax'], int(self.PlotParameters['xPoints']))
        yVals = np.linspace(self.PlotParameters['yMin'], self.PlotParameters['yMax'], int(self.PlotParameters['yPoints']))
        xInd, yInd = np.linspace(0,     self.PlotParameters['xPoints'] - 1,    int(self.PlotParameters['xPoints'])), np.linspace(0,    self.PlotParameters['yPoints'] - 1, int(self.PlotParameters['yPoints']))

        zX, zY, zXI, zYI = np.ones([1,int(self.PlotParameters['yPoints'])]), np.ones([1,int(self.PlotParameters['xPoints'])]), np.ones([1,int(self.PlotParameters['yPoints'])]), np.ones([1,int(self.PlotParameters['xPoints'])])
        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.PlotData.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold,{savename:matData})
        matData = None
##################

    def SelectArea(self):
        self.SelectedAreaShow = not self.SelectedAreaShow
        if self.SelectedAreaShow:
            self.mainPlot.addItem(self.AreaSelected)
        else:
            self.mainPlot.removeItem(self.AreaSelected)

    def RefreshAreaSelected(self):
        self.RefreshSelecedAreaProperty()
        self.RedefineSelectedAreaData()
        self.editDataInfo.RefreshInfo()

    def SetDefaultSelectedAreaPos(self):
        xAxis = self.viewBig.getAxis('bottom')
        yAxis = self.viewBig.getAxis('left')
        xMin, xMax = self.PlotParameters['xMin'], self.PlotParameters['xMax']
        yMin, yMax = self.PlotParameters['yMin'], self.PlotParameters['yMax']
        self.AreaSelected.setPos([xMin, yMin])
        self.AreaSelected.setSize([(xMax - xMin) / 2, (yMax - yMin) / 2])

    def RefreshSelecedAreaProperty(self):
        if '2DPlot' in self.DataType:
            bounds = self.AreaSelected.parentBounds()#Return the bounding rectangle of this ROI in the coordinate system of its parent. 
            self.AreaSelectedParameters['xMin'] = int((bounds.x() - self.PlotParameters['xMin']) / self.PlotParameters['xscale'])
            self.AreaSelectedParameters['yMin'] = int((bounds.y() - self.PlotParameters['yMin']) / self.PlotParameters['yscale'])
            self.AreaSelectedParameters['xMax'] = int((bounds.x() + bounds.width() - self.PlotParameters['xMin']) / self.PlotParameters['xscale'])
            self.AreaSelectedParameters['yMax'] = int((bounds.y() + bounds.height() - self.PlotParameters['yMin']) / self.PlotParameters['yscale'])
            self.RedefineSelectedAreaData()
        else:
            pass
    
    def RedefineSelectedAreaData(self):
        if not self.PlotData is None:
            xMin, xMax = self.AreaSelectedParameters['xMin'], self.AreaSelectedParameters['xMax']
            yMin, yMax = self.AreaSelectedParameters['yMin'], self.AreaSelectedParameters['yMax']
            Dimx, Dimy = self.PlotParameters['xPoints'], self.PlotParameters['yPoints']
            if xMin >= 0 and xMax < Dimx and yMin >= 0 and yMax < Dimy:
                self.Data_SelectedArea = self.PlotData[xMin:xMax, yMin:yMax]
                self.Average_SelectedArea = np.average(self.Data_SelectedArea)
            else:
                self.Average_SelectedArea = 0.0
        else:
            pass

################## This part create a window on the plot and you can drage it around, click on it will rescale the plot
    def zoomArea(self):
        self.zoom.clicked.disconnect(self.zoomArea)
        self.zoom.clicked.connect(self.rmvZoomArea)
        xAxis = self.viewBig.getAxis('bottom')
        yAxis = self.viewBig.getAxis('left')
        a1, a2 = xAxis.range[0], xAxis.range[1]
        b1, b2 = yAxis.range[0], yAxis.range[1]
        self.zoomRect = pg.RectROI(((a2 + a1) / 2, (b2 + b1) / 2),((a2 - a1) / 2, (b2 - b1) / 2), movable = True)
        self.zoomRect.setAcceptedMouseButtons(QtCore.Qt.RightButton | QtCore.Qt.LeftButton)
        self.zoomRect.addScaleHandle((1,1), (.5,.5), lockAspect = False)
        self.zoomRect.sigClicked.connect(self.QMouseEvent)
        self.mainPlot.addItem(self.zoomRect)
        
    def rmvZoomArea(self):
        self.mainPlot.removeItem(self.zoomRect)
        self.zoom.clicked.connect(self.zoomArea)

    def QMouseEvent(self, thing, button, c =None, d =None):
        print thing , button,c,d
        button = int(str(button)[-2])#1 for left, 2 for right

        bounds = self.zoomRect.parentBounds()
        x1 = int((bounds.x() - self.PlotParameters['xMin']) / self.PlotParameters['xscale'])
        y1 = int((bounds.y() - self.PlotParameters['yMin']) / self.PlotParameters['yscale'])
        x2 = int((bounds.x() + bounds.width() - self.PlotParameters['xMin']) / self.PlotParameters['xscale'])
        y2 = int((bounds.y() + bounds.height() - self.PlotParameters['yMin']) / self.PlotParameters['yscale'])
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
                    self.dataZoom = self.Data[int(k*self.PlotParameters['yPoints'] + y1) :int(k*self.PlotParameters['yPoints'] + y2)]
                else:
                    self.dataZoom = np.vstack((self.dataZoom, self.Data[int(k*self.PlotParameters['yPoints'] + y1) :int(k*self.PlotParameters['yPoints'] + y2)]))
                
            for i in range(0, self.comboBox_xAxis.count()):
                self.indZoomVars.append(self.comboBox_xAxis.itemText(i))
            for i in range(0, self.comboBox_zAxis.count()):
                self.depZoomVars.append(self.comboBox_zAxis.itemText(i))
            title= str(self.label_FileName.text())
            self.indXVar, self.indYVar, self.depVar = self.comboBox_xAxis.currentText(), self.comboBox_yAxis.currentText(), self.comboBox_zAxis.currentText()
            self.currentIndex = [self.comboBox_xAxis.currentIndex(), self.comboBox_yAxis.currentIndex(), self.comboBox_zAxis.currentIndex()]        
            self.zoomExtent = [bounds.x(), bounds.x() + bounds.width(), bounds.y(), bounds.y() + bounds.height(), self.PlotParameters['xscale'], self.PlotParameters['yscale']]
            self.zoomPlot = zoomWindow.zoomPlot(self.reactor, self.plotZoom, self.dataZoom, self.zoomExtent, self.indZoomVars, self.depZoomVars, self.currentIndex, title, self)
            self.zoom.setEnabled(False)
            self.zoomPlot.show()
##################

    def promptSensitivity(self):
        self.sensPrompt = sensitivityPrompt.Sensitivity(self.depVars, self.indVars, self.reactor)
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
        self.PlotParameters['xMax'] = np.amax(self.Data[::,l+x])
        self.PlotParameters['xMin'] = np.amin(self.Data[::,l+x])
        self.PlotParameters['yMax'] = np.amax(self.Data[::,l+y])
        self.PlotParameters['yMin'] = np.amin(self.Data[::,l+y])
        self.PlotParameters['deltaX'] = self.PlotParameters['xMax'] - self.PlotParameters['xMin']
        self.PlotParameters['deltaY'] = self.PlotParameters['yMax'] - self.PlotParameters['yMin']
        self.PlotParameters['xPoints'] = np.amax(self.Data[::,x])+1
        self.PlotParameters['yPoints'] = np.amax(self.Data[::,y])+1
        self.PlotParameters['xscale'], self.PlotParameters['yscale'] = (self.PlotParameters['xMax']-self.PlotParameters['xMin']) / self.PlotParameters['xPoints'], (self.PlotParameters['yMax']-self.PlotParameters['yMin']) / self.PlotParameters['yPoints']    
        n = self.sensIndex[3] + len(self.indVars)
        self.PlotData = np.zeros([int(self.PlotParameters['xPoints']), int(self.PlotParameters['yPoints'])])
        self.noiseData = np.zeros([int(self.PlotParameters['xPoints']), int(self.PlotParameters['yPoints'])])
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = float(i[z])
            if i[n] != 0:
                self.noiseData[int(i[x]), int(i[y])] = float(i[n])
            else:
                self.noiseData[int(i[x]), int(i[y])] = 1e-5
        xVals = np.linspace(self.PlotParameters['xMin'], self.PlotParameters['xMax'], num = self.PlotParameters['xPoints'])
        yVals = np.linspace(self.PlotParameters['yMin'], self.PlotParameters['yMax'], num = self.PlotParameters['yPoints'])
        delta = abs(self.PlotParameters['xMax'] - self.PlotParameters['xMin']) / self.PlotParameters['xPoints']
        N = int(self.PlotParameters['yPoints'] * self.datPct)

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

        self.mainPlot.setImage(self.PlotData, autoRange = True , levels = (avg - std, avg+std), autoHistogramRange = False, pos=[self.PlotParameters['xMin'], self.PlotParameters['yMin']],scale=[self.PlotParameters['xscale'], self.PlotParameters['yscale']])
        self.mainPlot.addItem(self.vLine)
        self.mainPlot.addItem(self.hLine)
        self.vLine.setValue(self.PlotParameters['xMin'])
        self.hLine.setValue(self.PlotParameters['yMin'])    
        if self.NSselect == 1:
            self.Feedback('Plotted sensitivity.')
            self.vhSelect.addItem('Maximum Sensitivity')
        else:
            self.Feedback('Plotted field noise.')    
            self.vhSelect.addItem('Minimum Noise')
            self.vhSelect.addItem('Optimal Bias')
        self.ResetLineCutPlots()

    def plotMaxSens(self):
        if self.NSselect == 1:
            maxSens = np.array([])
            bVals = np.linspace(self.PlotParameters['xMin'], self.PlotParameters['xMax'], self.PlotParameters['xPoints'])
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
            bVals = np.linspace(self.PlotParameters['xMin'], self.PlotParameters['xMax'], self.PlotParameters['xPoints'])
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
        bVals = np.linspace(self.PlotParameters['xMin'], self.PlotParameters['xMax'], self.PlotParameters['xPoints'])
        vVals =np.linspace(self.PlotParameters['yMin'], self.PlotParameters['yMax'], self.PlotParameters['yPoints'])
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
        self.PlotParameters['xMax'] = np.amax(self.Data[::,l+x])
        self.PlotParameters['xMin'] = np.amin(self.Data[::,l+x])
        self.PlotParameters['yMax'] = np.amax(self.Data[::,l+y])
        self.PlotParameters['yMin'] = np.amin(self.Data[::,l+y])
        self.PlotParameters['deltaX'] = self.PlotParameters['xMax'] - self.PlotParameters['xMin']
        self.PlotParameters['deltaY'] = self.PlotParameters['yMax'] - self.PlotParameters['yMin']
        self.PlotParameters['xPoints'] = np.amax(self.Data[::,x])+1
        self.PlotParameters['yPoints'] = np.amax(self.Data[::,y])+1
        self.PlotParameters['xscale'], self.PlotParameters['yscale'] = (self.PlotParameters['xMax']-self.PlotParameters['xMin']) / self.PlotParameters['xPoints'], (self.PlotParameters['yMax']-self.PlotParameters['yMin']) / self.PlotParameters['yPoints']    
        self.PlotData = np.zeros([int(self.PlotParameters['xPoints']), int(self.PlotParameters['yPoints'])])
        for i in self.Data:
            self.PlotData[int(i[x]), int(i[y])] = i[z]

    def xDeriv(self):
        if self.PlotData is None:
            self.Feedback("Please plot data.")
        else:
            self.gradient.setFocusPolicy(QtCore.Qt.StrongFocus)
            xVals = np.linspace(self.PlotParameters['xMin'], self.PlotParameters['xMax'], num = self.PlotParameters['xPoints'])
            delta = abs(self.PlotParameters['xMax'] - self.PlotParameters['xMin']) / self.PlotParameters['xPoints']
            N = int(self.PlotParameters['xPoints'] * self.datPct)
            if N < 2:
                self.Feedback("Lanczos window too small.")

            else:
                for i in range(0, self.PlotData.shape[1]):
                    self.PlotData[:, i] = deriv(self.PlotData[:,i], xVals, N, delta)    
                self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.PlotParameters['xMin'], self.PlotParameters['yMin']],scale=[self.PlotParameters['xscale'], self.PlotParameters['yscale']])
                self.Feedback("Plotted gradient along x-axis.")
                self.ResetLineCutPlots()
                
    def yDeriv(self):
        yVals = np.linspace(self.PlotParameters['yMin'], self.PlotParameters['yMax'], num = self.PlotParameters['yPoints'])
        delta = abs(self.PlotParameters['yMax'] - self.PlotParameters['yMin']) / self.PlotParameters['yPoints']
        N = int(self.PlotParameters['yPoints'] * self.datPct)
        for i in range(0, self.PlotData.shape[0]):
            self.PlotData[i, :] = deriv(self.PlotData[i,:], yVals, N, delta)    
        self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.PlotParameters['xMin'], self.PlotParameters['yMin']],scale=[self.PlotParameters['xscale'], self.PlotParameters['yscale']])
        self.Feedback("Plotted gradient along y-axis.")
        self.ResetLineCutPlots()
        
    def derivSettings(self):
        self.gradSet = gradSettings.gradSet(self.reactor, self.datPct)
        self.gradSet.show()
        self.gradSet.accepted.connect(self.setLancWindow)
        
    def setLancWindow(self):
        self.datPct = self.gradSet.dataPercent.value() / 100

##################Manipulating Plot Data
    def subtractOverallAvg(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Average')
        self.Feedback("Subtracted Overall Average")
        self.Plot_Data()

    def ConstantSubtractedWindow(self):
        self.SubConstantWindow.raise_()
        self.SubConstantWindow.moveDefault()
        self.SubConstantWindow.show()

    def subtractOverallConstant(self, number):
        if not self.PlotData is None:
            NewData = self.PlotData - number
            self.PlotData = NewData
            self.Plot_Data()
            feedback = "Subtracted Constatnt: " + str(number)
            self.Feedback(feedback)
        else:
            pass

    def subtractPlane(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Plane')
        self.Feedback("Subtracted Overall Plane Fit")
        self.Plot_Data()

    def subtractOverallQuad(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Quadratic')
        self.Feedback("Subtracted Overall Quadratic Fit")
        self.Plot_Data()
        
    def subtractXAvg(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Average')
        self.Feedback("Subtracted Line Average in X")
        self.Plot_Data()
        
    def subtractYAvg(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Average').T
        self.Feedback("Subtracted Line Average in Y")
        self.Plot_Data()

    def subtractXLinear(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Linear')
        self.Feedback("Subtracted Linear Fit in X")
        self.Plot_Data()
    
    def subtractYLinear(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Linear').T
        self.Feedback("Subtracted Linear Fit in Y")
        self.Plot_Data()

    def subtractXQuad(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Quadratic')
        self.Feedback("Subtracted Quadratic Fit in X")
        self.Plot_Data()
    
    def subtractYQuad(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Quadratic').T
        self.Feedback("Subtracted Quadratic Fit in Y")
        self.Plot_Data()
        
##################

    def MultiplyDialog(self):
        self.MultiplyWindow.moveDefault()
        self.MultiplyWindow.show()

    def MultiplyPlotData(self, multiplier):
        NewData = self.PlotData * multiplier
        self.PlotData = NewData
        self.Plot_Data()
        

    @inlineCallbacks
    def browseDV(self, c = None):
        try:
            yield self.sleep(0.1)
            self.dvExplorer = dvExplorerWindow.dataVaultExplorer(self.dv, self.reactor)
            yield self.dvExplorer.popDirs()
            self.dvExplorer.show()
            self.dvExplorer.accepted.connect(lambda: self.loadData(self.reactor))
        except Exception as inst:
            print 'Following error was thrown: ', inst
            print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def ClearcomboBox(self):
        self.comboBox_xAxis.clear()
        self.comboBox_yAxis.clear()
        self.comboBox_zAxis.clear()
      
    def ClearData(self):
        self.Data = None
        self.traceData = None
        self.retraceData = None
        self.Number_PlotData_X, self.Number_PlotData_Y = 0,0
        self.SweepingDirection = ''

    def ReadParameters(self, parameters): #parameters comes in tuples ('key' , 'value')
        try:
            paramsDict = {}
            if parameters !=None: #There are some files that give a None here
                for i in parameters:
                    paramsDict[i[0]] = i[1] #i[0] is key, i[1] is value
            return paramsDict
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
                
    def ParseDatainfo(self, info):#Read the data structure and determine the strategy for reading it
        try:
            DataInfo = info#[self.file, self.directory, self.variables, self.parameters, self.comments]
            file = DataInfo[0]
            directory = DataInfo[1]
            indVars = DataInfo[2][0]
            depVars = DataInfo[2][1]
            paramsDict = self.ReadParameters(DataInfo[3])
            comments = DataInfo[4]
            TraceFlag = None #None for no Trace/Retrace, 0 for trace, 1 for retrace
            NumberofindexVariables = 0
            
            if len(indVars)-NumberofindexVariables == 1:
                DataType = "1DPlot"
            else:
                DataType = "2DPlot"
                
            for i in indVars:
                if i == 'Trace Index' or i == 'Retrace Index':
                    TraceFlag = 0 #default set traceflag to trace
            for i in indVars:
                if "index" in i or "Index" in i:
                    NumberofindexVariables +=1
                    
            return file, directory, indVars, depVars, paramsDict, comments, DataType, TraceFlag, NumberofindexVariables
             
            
            self.editDataInfo.RefreshInfo()

        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

    def setPlotInfo(self, file, directory, indVars, depVars, paramsDict, comments, DataType, TraceFlag = None, NumberofindexVariables = 0):
        self.file = file
        self.directory = directory
        self.indVars = indVars
        self.depVars = depVars
        self.Parameters = paramsDict
        self.comments = comments
        self.DataType = DataType
        self.TraceFlag = TraceFlag
        self.NumberofindexVariables = NumberofindexVariables
        
    @inlineCallbacks
    def ReadData(self):#Read all the data in datavault and stack them in order
        try:
            getFlag = True
            rawData = np.array([])
            while getFlag == True:
                line = yield self.dv.get(1000L)

                try:
                    if len(rawData) != 0 and len(line) > 0:
                        rawData = np.vstack((rawData, line))                        
                    elif len(rawData) == 0 and len(line) > 0:
                        rawData = np.asarray(line)
                    else:
                        getFlag = False
                except:
                    getFlag = False
            
            feedback = 'Get Set Finished.'
            self.Feedback(feedback)
            returnValue(rawData) 
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

    def RefreshComboIndex(self):
        try:
            if "2DPlot" in self.DataType:
                for i in self.indVars[self.NumberofindexVariables: len(self.indVars)]:
                    self.comboBox_xAxis.addItem(i)
                    self.comboBox_yAxis.addItem(i)
                    self.comboBox_xAxis.setCurrentIndex(0)#Default
                    self.comboBox_yAxis.setCurrentIndex(1)#Default
            elif "1DPlot" in self.DataType:
                self.comboBox_xAxis.addItem(self.indVars[self.NumberofindexVariables])
                self.comboBox_xAxis.setCurrentIndex(0)#Default

            for i in self.depVars:
                self.comboBox_zAxis.addItem(i)
                self.comboBox_zAxis.setCurrentIndex(0)#Default

        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

    def split(self, arr, cond):
        return [arr[cond], arr[~cond]]

    def ProcessRawData(self, rawData):####
        try:
            if self.TraceFlag == 0 or self.TraceFlag == 1:
                self.indVars=self.indVars[1::]
                self.NumberofindexVariables -=1
                self.traceData, self.retraceData = self.split(rawData, rawData[:,0] == 0)
                self.traceData = np.delete(self.traceData,0,1)
                self.retraceData = np.delete(self.retraceData,0,1)
                if self.TraceFlag == 0:
                    ProcessedData = self.traceData
                elif self.TraceFlag == 1:
                    ProcessedData = self.retraceData
                    
            elif self.TraceFlag == None:
                ProcessedData = rawData 
            else:
                pt = self.mapToGlobal(QtCore.QPoint(410,-10))
                QtGui.QToolTip.showText(pt, 'Data set format is incompatible with the plotter.')
                ProcessedData = None 
            return ProcessedData

                
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
        
    def setData(self, data, info):
        self.ClearcomboBox()
        self.ClearData()
        self.setData(data)
        self.setPlotInfo(info)#file, directory, indVars, depVars, paramsDict, comments, DataType, TraceFlag = None, NumberofindexVariables = 0
    
        #buttons appropriately
        
    @inlineCallbacks
    def loadData(self, c):
        try:
            self.ClearcomboBox()
                    
            #Initialized data set to none
            self.ClearData()
            
            #Determine the Data Structure, there can be Trace/Retrace or Index/nonIndex
            dvInfo = self.dvExplorer.dataSetInfo()
            file, directory, indVars, depVars, paramsDict, comments, DataType, TraceFlag, NumberofindexVariables = self.ParseDatainfo(dvInfo)
            
            rawData = yield self.ReadData()
            
            self.setPlotInfo(file, directory, indVars, depVars, paramsDict, comments, DataType, TraceFlag, NumberofindexVariables) #file, directory, indVars, depVars, paramsDict, comments, DataType, TraceFlag = None, NumberofindexVariables = 0
            
            self.Data = self.ProcessRawData(rawData)

            ### Assumptions, we have trace/retrace for only 2DPlot
            ### Assumptions, index are in the beginning of the lists
            #This logically follows from setPlotInfo, put it there
            self.RefreshComboIndex()
            #self.TraceFlag gives whether there are trace, self.NumberofindexVariables gives the number of index and should also be where the data starts in self.Data,   self.DataType gives the type of DataPlot
            #Also put this in setPlotInfo
            
            self.mainPlot.clear()
                
            self.ResetLineCutPlots()
            
            self.RefreshInterface()
            self.editDataInfo.RefreshInfo()
            self.parent.RefreshPlotList()

        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
                
    def SetPlotLabel(self):
        self.viewBig.setLabel('left', text=self.comboBox_yAxis.currentText())
        self.viewBig.setLabel('bottom', text=self.comboBox_xAxis.currentText())
        self.XZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.comboBox_xAxis.currentText())
        self.YZPlot.setLabel('left', self.comboBox_yAxis.currentText())
        self.YZPlot.setLabel('bottom',self.comboBox_zAxis.currentText())

    def SetupPlotParameter(self):
        try:
            self.PlotParameters['xMax'] = np.amax(self.Data[::,self.NumberofindexVariables+self.xIndex])
            self.PlotParameters['xMin'] = np.amin(self.Data[::,self.NumberofindexVariables+self.xIndex])
            self.PlotParameters['deltaX'] = self.PlotParameters['xMax'] - self.PlotParameters['xMin']
            self.PlotParameters['xPoints'] = np.amax(self.Data[::,self.xIndex])+1  #look up the index
            self.PlotParameters['xscale']  = (self.PlotParameters['xMax']-self.PlotParameters['xMin']) / self.PlotParameters['xPoints'] 
            self.PlotParameters['yMin'] = 0.0
        
            if "2DPlot" in self.DataType:
                self.PlotParameters['yMax'] = np.amax(self.Data[::,self.NumberofindexVariables+self.yIndex])
                self.PlotParameters['yMin'] = np.amin(self.Data[::,self.NumberofindexVariables+self.yIndex])
                self.PlotParameters['deltaY'] = self.PlotParameters['yMax'] - self.PlotParameters['yMin']
                self.PlotParameters['yPoints'] = np.amax(self.Data[::,self.yIndex])+1
                self.PlotParameters['yscale'] = (self.PlotParameters['yMax']-self.PlotParameters['yMin']) / self.PlotParameters['yPoints']
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
                
    def SetupPlotData(self):
        try:
            if "2DPlot" in self.DataType:
                self.PlotData = np.zeros([int(self.PlotParameters['xPoints']), int(self.PlotParameters['yPoints'])])
                for i in self.Data:
                    if self.comboBox_yAxis.currentText() == "None":
                        self.PlotData[int(i[self.xIndex]), 0] = i[self.zIndex]
                    else:
                        self.PlotData[int(i[self.xIndex]), int(i[self.yIndex])] = i[self.zIndex]
            elif "1DPlot" in self.DataType:
                self.PlotData = [[],[]] #0 for x, 1 for y
                for i in self.Data:
                    self.PlotData[0].append(i[self.NumberofindexVariables])
                    self.PlotData[1].append(i[self.zIndex])
            
            self.parent.RefreshPlotList()

        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
        
    def Plot_Data(self):
        if "2DPlot" in self.DataType:
            self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.PlotParameters['xMin'], self.PlotParameters['yMin']],scale=[self.PlotParameters['xscale'], self.PlotParameters['yscale']])
            self.ResetLineCutPlots()

        elif "1DPlot" in self.DataType:
            self.LineCutXZYVals = self.PlotData[1]
            self.LineCutXZXVals = self.PlotData[0]
            self.XZPlot.plot(x = self.LineCutXZXVals, y = self.LineCutXZYVals, pen = 0.5)

        self.editDataInfo.RefreshInfo()

    def DetermineSweepingIndependentAxis(self): #Assumptions: independent Variables saved firstly
        self.SweepingIndependentAxis = []
        for i in range(len(self.indVars)):
            if self.Data[1][i] != self.Data[0][i]:
                self.SweepingIndependentAxis.append(self.indVars[i])
        if self.xAxis_Name in self.SweepingIndependentAxis:
            self.SweepingDirection = "x"
        else:
            self.SweepingDirection = "y"

    def ParsePlotData(self):# Get Information on the PlotData
        try:
            if "2DPlot" in self.DataType:
                self.Number_PlotData_X, self.Number_PlotData_Y = np.array(self.PlotData).shape
                if not "Reconstitute" in self.DataType:
                    self.SweepingIndependentAxis=[]
                    self.DetermineSweepingIndependentAxis()

            if '1DPlot' in self.DataType:
                self.Number_PlotData_X, self.Number_PlotData_Y = len(self.PlotData[0]), 0
            
            self.editDataInfo.RefreshInfo()

        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
                
    def refreshPlot(self):
        try:
            self.ClearLineCutPlot()
            
            self.xIndex = self.comboBox_xAxis.currentIndex()
            self.yIndex = self.comboBox_yAxis.currentIndex()
            self.zIndex = self.comboBox_zAxis.currentIndex() + len(self.indVars) 
            self.xAxis_Name = self.comboBox_xAxis.currentText()
            self.yAxis_Name = self.comboBox_yAxis.currentText()
            
            
            self.SetPlotLabel()
            
            if not "Reconstitute" in self.DataType:
                self.SetupPlotParameter()
                self.SetupPlotData()
                self.ParsePlotData()

            self.Plot_Data()
            self.SetDefaultSelectedAreaPos()
            
            self.Feedback('Plot Refreshed')
            self.RefreshInterface()

        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

    def plotTrace(self):
        self.TraceFlag = 0
        self.Data = self.traceData
        self.refreshPlot()
        self.Feedback('Plot Trace')

    def plotRetrace(self):
        self.TraceFlag = 1
        self.Data = self.retraceData
        self.refreshPlot()
        self.Feedback('Plot Retrace')

    def ResetLineCutPlots(self):
        if self.PlotData is None:
            pass
        else:
            self.vLine.setValue(self.PlotParameters['xMin'])
            self.hLine.setValue(self.PlotParameters['yMin'])
            self.verticalposition=self.PlotParameters['xMin']
            self.horizontalposition=self.PlotParameters['yMin']
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
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    def SetupLineCuthorizontalposition(self):
        try:
            dummystr=str(self.lineEdit_hCutPos.text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float):
                self.horizontalposition=dummyval
            self.ChangeLineCutValue("")
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
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
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    def MoveLineCut(self):
        try:
            self.vLine.setValue(float(self.verticalposition))
            self.hLine.setValue(float(self.horizontalposition))
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    def ClearLineCutPlot(self):
        try:
            self.XZPlot.clear()
            self.YZPlot.clear()
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    def ConnectLineCut(self):
        try:
            self.vLine.sigPositionChangeFinished.connect(lambda:self.ChangeLineCutValue(self.vLine))
            self.hLine.sigPositionChangeFinished.connect(lambda:self.ChangeLineCutValue(self.hLine))
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    def SetupLineCut(self):
        try:
            self.viewBig.addItem(self.vLine, ignoreBounds = True)
            self.viewBig.addItem(self.hLine, ignoreBounds =True)
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    def Setup1DPlot(self, Plot, Layout ):
        try:
            Plot.setGeometry(QtCore.QRect(0, 0, 635, 200))
            Plot.showAxis('right', show = True)
            Plot.showAxis('top', show = True)
            Layout.addWidget(Plot)
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

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
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    def updateLineCutPlot(self):
        try:
            self.ClearLineCutPlot()
            if self.horizontalposition > self.PlotParameters['yMax'] or self.horizontalposition < self.PlotParameters['yMin']:
                self.XZPlot.clear()
            else:
                yindex = int(abs((self.horizontalposition - self.PlotParameters['yMin'])) / self.PlotParameters['yscale'])
                self.LineCutXZXVals = np.linspace(self.PlotParameters['xMin'], self.PlotParameters['xMax'], num = self.PlotParameters['xPoints'])
                self.LineCutXZYVals = self.PlotData[:,yindex]
                self.XZPlot.plot(x = self.LineCutXZXVals, y = self.LineCutXZYVals, pen = 0.5)
         
            if self.verticalposition > self.PlotParameters['xMax'] or self.verticalposition < self.PlotParameters['xMin']:
                self.YZPlot.clear()
            else:
                xindex = int(abs((self.verticalposition - self.PlotParameters['xMin'])) / self.PlotParameters['xscale'])
                self.LineCutYZXVals = self.PlotData[xindex]
                self.LineCutYZYVals = np.linspace(self.PlotParameters['yMin'], self.PlotParameters['yMax'], num = self.PlotParameters['yPoints'])
                self.YZPlot.plot(x = self.LineCutYZXVals, y = self.LineCutYZYVals, pen = 0.5)
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
    # @inlineCallbacks
    def displayInfo(self, c):
        try:
            self.editDataInfo.RefreshInfo()
            self.editDataInfo.moveDefault()
            self.editDataInfo.show()
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
            
            
    def get_standard_distribution(self, x, y): #Find data's adjacent mean and standard deviation
        side = self.AdjacentPoints
        if self.SweepingDirection == 'x':
            if abs(x - 0) > side and abs(x - (self.Number_PlotData_X - 1)) > side:
                data = [item[y] for item in self.PlotData][x - side:x + side +1]
            elif abs(x - 0) <= side:
                data = [item[y] for item in self.PlotData][0: 2*side + 1]
            elif abs(x - (self.Number_PlotData_X - 1)) <= side:
                data = [item[y] for item in self.PlotData][(self.Number_PlotData_X - 1) - (2*side + 1):(self.Number_PlotData_X - 1)]
        elif self.SweepingDirection == 'y':
            if abs(y - 0) > side and abs(y - (self.Number_PlotData_Y - 1)) >side:
                data = self.PlotData[x][y - side : y + side + 1]
            elif abs(y - 0) <= side:
                data = self.PlotData[x][0: 2*side + 1]
            elif abs(y - (self.Number_PlotData_Y - 1)) <= side:
                data = self.PlotData[x][(self.Number_PlotData_Y - 1) - (2*side + 1):(self.Number_PlotData_Y - 1)]
        data.pop(3)
        return np.mean(data), np.std(data)

        
    def LinearExtrapolate(self, x, y): #Find what data should be based on neighbor
        if self.SweepingDirection == 'x':
            if x == 0:
                value = 2*self.PlotData[x+1][y]-self.PlotData[x+2][y]
            elif x == self.Number_PlotData_X - 1:
                value = 2*self.PlotData[x-1][y]-self.PlotData[x-2][y]
            else:
                value = (self.PlotData[x-1][y]+self.PlotData[x+1][y]) / 2
        if self.SweepingDirection == 'y':
            if y == 0:
                value = 2*self.PlotData[x][y+1]-self.PlotData[x][y+2]
            elif y == self.Number_PlotData_Y - 1:
                value = 2*self.PlotData[x][y-1]-self.PlotData[x][y-2]
            else:
                value = (self.PlotData[x][y-1]+self.PlotData[x][y+1]) / 2
        return value
        
    def RemoveSpikes(self):
        feedback = "Start to remove spikes with parameters: " + str(self.AdjacentPoints) + ' , ' + str(self.NumberOfSigma)
        self.Feedback(feedback)
        number = 0
        list = []
        for i in range(self.Number_PlotData_X ):
            for j in range(self.Number_PlotData_Y ):
                avg, std = self.get_standard_distribution(i,j)
                if std != 0 and abs(self.PlotData[i][j] - avg) > self.NumberOfSigma * std:
                    number += 1
                    list.append([i,j, abs(self.PlotData[i][j] - avg) / float(std)])
                    self.PlotData[i][j] = self.LinearExtrapolate(i,j)
        self.Plot_Data()
        feedback = "Remove Spikes Finished, Flattened " + str(number) + " data."
        self.Feedback(feedback)

    def RemoveSpikesSettings(self):
        self.DespikeSettingWindow.show()
        self.DespikeSettingWindow.raise_()
        
    def ToggleAspectRatio(self):
        self.aspectLocked = not self.aspectLocked
        if self.aspectLocked == False:
            self.viewBig.setAspectLocked(False)
        else:
            self.viewBig.setAspectLocked(True, ratio = 1)

    def CropWindow(self, xMinIndex, xMaxIndex, yMinIndex, yMaxIndex):
        CropData = self.PlotData[xMinIndex:xMaxIndex, yMinIndex:yMaxIndex]
        xMin_Past = self.PlotParameters['xMin']
        xMax_Past = self.PlotParameters['xMax']
        yMin_Past = self.PlotParameters['yMin']
        yMax_Past = self.PlotParameters['yMax']
        xPoints_Past = self.PlotParameters['xPoints']
        yPoints_Past = self.PlotParameters['yPoints'] 

        self.PlotParameters['xMin'] = (xMax_Past - xMin_Past)/ xPoints_Past * xMinIndex + xMin_Past
        self.PlotParameters['xMax'] = (xMax_Past - xMin_Past)/ xPoints_Past * xMaxIndex + xMin_Past
        self.PlotParameters['yMin'] = (yMax_Past - yMin_Past)/ yPoints_Past * yMinIndex + yMin_Past
        self.PlotParameters['yMax'] = (yMax_Past - yMin_Past)/ yPoints_Past * yMaxIndex + yMin_Past
        self.PlotParameters['deltaX'] = self.PlotParameters['xMax'] - self.PlotParameters['xMin']
        self.PlotParameters['xPoints'] = xMaxIndex - xMinIndex 
        self.PlotParameters['xscale']  = (self.PlotParameters['xMax']-self.PlotParameters['xMin']) / self.PlotParameters['xPoints'] 
        self.PlotParameters['deltaY'] = self.PlotParameters['yMax'] - self.PlotParameters['yMin']
        self.PlotParameters['yPoints'] = yMaxIndex - yMinIndex 
        self.PlotParameters['yscale'] = (self.PlotParameters['yMax']-self.PlotParameters['yMin']) / self.PlotParameters['yPoints']
        
        self.PlotData = CropData
        self.Plot_Data()
        self.RefreshInterface()

    def Feedback(self, string):
        self.label_Feeedback.setText(string) 

    def moveDefault(self):
        parentx, parenty = self.parent.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        parentwidth, parentheight = self.parent.width(), self.parent.height()
        Offset = self.number * 50 + 10
        self.move(parentx + parentwidth + Offset, parenty)         
        
    def closeEvent(self, e):
        self.parent.PlotterList.remove(self)
        self.CloseSubWindow()
        self.parent.RefreshPlotList()
        self.close()
    
    def CloseSubWindow(self):
        if hasattr(self, 'editDataInfo'):
            self.editDataInfo.close()
        if hasattr(self, 'sensPrompt'):
            self.sensPrompt.close()
        if hasattr(self, 'gradSet'):
            self.gradSet.close()
        if hasattr(self, 'dvExplorer'):
            self.dvExplorer.close()
        if hasattr(self, 'DespikeSettingWindow'):
            self.DespikeSettingWindow.close()
        if hasattr(self, 'MultiplyWindow'):
            self.MultiplyWindow.close()
        if hasattr(self, 'SubConstantWindow'):
            self.SubConstantWindow.close() 

if __name__ == "__main__":
    app = QtGui.QApplication([])
    from qtreactor import pyqt4reactor
    pyqt4reactor.install()
    from twisted.internet import reactor
    window = Plotter(reactor)
    window.show()
    reactor.run()
