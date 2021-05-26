from __future__ import division
import sys
from PyQt4 import QtCore, QtGui, QtTest, uic
import numpy as np
import copy

path = sys.path[0] + r"\PlottersControl\Plotter\ZoomWindow"
Ui_ZoomWindow, QtBaseClass = uic.loadUiType(path + r"\zoomWindow.ui")

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
