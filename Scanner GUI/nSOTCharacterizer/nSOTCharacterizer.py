import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading
import copy

path = sys.path[0] + r"\nSOTCharacterizer"
characterGUI = path + "\character_GUI.ui"
dialogBox = path + "\sweepCheck.ui"
plotter = path + "\plotter.ui"
dacSet = path + "\dacChannels.ui"
acSet = path + r"\acSetting.ui"
serlist = path + r"\requiredServers.ui"

Ui_MainWindow, QtBaseClass = uic.loadUiType(characterGUI)
Ui_DialogBox, QtBaseClass = uic.loadUiType(dialogBox)
Ui_Plotter, QtBaseClass = uic.loadUiType(plotter)
Ui_dacSet, QtBaseClass = uic.loadUiType(dacSet)
Ui_acSet, QtBaseClass = uic.loadUiType(acSet)
Ui_ServerList, QtBaseClass = uic.loadUiType(serlist)

class Window(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)
        #QtGui.QDialog.__init__(self)
        self.parent = parent
        
        self.reactor = reactor
        self.setupUi(self)
        self.setUpPlots()
        
        self.plotNoPlot = 0
        self.dacBiasOutChan, self.dacBlinkOutChan = 1, 2
        self.dacBiasInChan, self.dacDCInChan, self.dacACInChan, self.dacNoiseInChan = 1, 2 ,3 ,4
        self.acFreq, self.acAmp = 4.0, 2.0

        self.fieldPos = 0

        self.startSweep.clicked.connect(self.checkSweep)
        self.abortSweep.clicked.connect(self.abortion)

        self.fieldStepsInc.clicked.connect(self.toggleFieldSteps)
        self.fieldSIStat = True
        self.biasStepsInc.clicked.connect(self.toggleBiasSteps)
        self.biasSIStat = True

        self.liveTracePlot.clicked.connect(self.toggleTraceLineCut)
        self.liveTracePlotStatus = False
        self.liveRetracePlot.clicked.connect(self.toggleRetraceLineCut)
        self.liveRetracePlotStatus = False

        self.analyzeData.setEnabled(False)
        self.analyzeData.clicked.connect(self.openNewPlot)

        self.dacSetOpen.clicked.connect(self.dacSet)
        self.acSetOpen.clicked.connect(self.acSet)

        rect = pg.RectROI((0,0),(1,1), movable = True)
        rect.addRotateHandle((0,0),(0.5,0.5))
        rect.addScaleHandle((1,1), (.5,.5), lockAspect = True)

        self.showTraceGrad.hide()
        self.hideTraceGrad.raise_()
        self.hideTraceGrad.clicked.connect(self.shrinkTracePlot)
        self.showTraceGrad.clicked.connect(self.enlargeTracePlot)
        self.showRetraceGrad.hide()
        self.hideRetraceGrad.raise_()
        self.hideRetraceGrad.clicked.connect(self.shrinkRetracePlot)
        self.showRetraceGrad.clicked.connect(self.enlargeRetracePlot)
        #self.view2.addItem(rect)

        self.vCutTracePos.editingFinished.connect(self.changeVLine)
        self.hCutTracePos.editingFinished.connect(self.changeHLine)
        self.vCutRetracePos.editingFinished.connect(self.changeVLine)
        self.hCutRetracePos.editingFinished.connect(self.changeHLine)

        self.currentBiasTraceSelect.currentIndexChanged.connect(self.toggle_bottomTracePlot)
        self.currentBiasRetraceSelect.currentIndexChanged.connect(self.toggle_bottomRetracePlot)

        self.fieldMaxSetValue.editingFinished.connect(self.UpdateBMax)
        self.fieldMinSetValue.editingFinished.connect(self.UpdateBMin)
        self.fieldPointsSetValue.editingFinished.connect(lambda: self.reformat(self.fieldPointsSetValue.text(), self.fieldPointsSetValue))
        self.fieldSpeedSetValue.editingFinished.connect(lambda: self.reformat(self.fieldSpeedSetValue.text(), self.fieldSpeedSetValue))

        self.biasMaxSetValue.editingFinished.connect(self.UpdateVMax)
        self.biasMinSetValue.editingFinished.connect(self.UpdateVMin)
        self.biasPointsSetValue.editingFinished.connect(lambda: self.reformat(self.biasPointsSetValue.text(), self.biasPointsSetValue))
        self.biasSpeedSetValue.editingFinished.connect(lambda: self.reformat(self.biasSpeedSetValue.text(), self.biasSpeedSetValue))

        self.push_Servers.clicked.connect(self.showServersList)
        
        #Intialize the servers to None
        self.cxn = None
        self.dv = None
        self.ips = None
        self.dac = None
        self.serversConnected = False
        
    def moveDefault(self):
        self.move(550,10)
        
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.dv = dict['dv']
            
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            self.serversConnected = True
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            
        if self.dv is None:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            
    def disconnectLabRAD(self):
        self.dv = None
        self.cxn = None
        self.ips = None
        self.dac = None
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
    
    def reformat(self, number, lineEdit):
        number = float(number)
        reformatted = '{:.2f}'.format(number)
        lineEdit.setText(reformatted)

    def dacSet(self):
        self.dacSetOpen.setEnabled(False)
        self.dacSettings = dacSettings(self)
        #self.dacSettings.show()
        if self.dacSettings.exec_():
            print self.dacBiasOutChan, self.dacBlinkOutChan, self.dacBiasInChan, self.dacDCInChan, self.dacACInChan, self.dacNoiseInChan
    
    def acSet(self):
        self.acSetOpen.setEnabled(False)
        self.acSettings = acSettings(self)
        #self.acSettings.show()
        if self.acSettings.exec_():
            print self.acFreq, self.acAmp

    def abortion(self):
        self.startSweep.setEnabled(True)

    def toggleFieldSteps(self):
        if self.fieldSIStat is True:
            self.FieldInc.setText("Millitesla per Step")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(255,255,255); font: 10pt;}")
            steps = float(self.fieldPointsSetValue.text())
            bMax = float(self.fieldMaxSetValue.text())
            bMin = float(self.fieldMinSetValue.text())
            if steps != 0:
                inc = float(1000 * (bMax - bMin) / (steps - 1))
                inc = '{:.2f}'.format(inc)
                self.fieldPointsSetValue.setText(str(inc))
                self.fieldSIStat = False
            else:
                self.FieldInc.setText("Millitesla per Step")
                self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(255,255,255); font: 10pt;}")
                self.fieldSIStat = False
        else:
            self.FieldInc.setText("Number of Steps")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(255,255,255); font: 10pt;}")
            inc = float(self.fieldPointsSetValue.text())
            bMax = float(self.fieldMaxSetValue.text())
            bMin = float(self.fieldMinSetValue.text())
            if inc != 0:
                steps = int(1000 * (bMax - bMin) / (inc)) +1 
                self.fieldPointsSetValue.setText(str(steps))
                self.fieldSIStat = True
            else:
                self.FieldInc.setText("Number of Steps")
                self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(255,255,255); font: 10pt;}")
                self.fieldSIStat = True        
    def toggleBiasSteps(self):
        if self.biasSIStat is True:
            self.BiasInc.setText("Millivolts per Step")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(255,255,255); font: 10pt;}")
            steps = float(self.biasPointsSetValue.text())
            vMax = float(self.biasMaxSetValue.text())
            vMin = float(self.biasMinSetValue.text())
            if steps != 0:
                inc = float(1000 * (vMax - vMin) / (steps))
                inc = '{:.2f}'.format(inc)
                self.biasPointsSetValue.setText(str(inc))
                self.biasSIStat = False
            else:
                self.BiasInc.setText("Millivolts per Step")
                self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(255,255,255); font: 10pt;}")
                self.biasSIStat = False
        else:
            self.BiasInc.setText("Number of Steps")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(255,255,255); font: 10pt;}")
            inc = float(self.biasPointsSetValue.text())
            vMax = float(self.biasMaxSetValue.text())
            vMin = float(self.biasMinSetValue.text())
            if inc != 0:
                steps = int(1000 * (vMax - vMin) / (inc))
                self.biasPointsSetValue.setText(str(steps))
                self.biasSIStat = True
            else:
                self.BiasInc.setText("Number of Steps")
                self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(255,255,255); font: 10pt;}")
                self.biasSIStat = True        


    def openNewPlot(self):
        self.plotter = Plotter()
        self.plotter.show()

    def shrinkTracePlot(self):
        self.tracePlot.ui.histogram.hide()
        self.noiseTracePlot.ui.histogram.hide()
        self.hideTraceGrad.hide()
        self.showTraceGrad.show()
        self.showTraceGrad.raise_()
    def enlargeTracePlot(self):
        self.tracePlot.ui.histogram.show()
        self.noiseTracePlot.ui.histogram.show()
        self.hideTraceGrad.show()
        self.showTraceGrad.hide()    
        self.showTraceGrad.raise_()    
    def shrinkRetracePlot(self):
        self.retracePlot.ui.histogram.hide()
        self.noiseRetracePlot.ui.histogram.hide()
        self.hideRetraceGrad.hide()
        self.showRetraceGrad.show()
        self.showRetraceGrad.raise_()
    def enlargeRetracePlot(self):
        self.retracePlot.ui.histogram.show()
        self.noiseRetracePlot.ui.histogram.show()
        self.hideRetraceGrad.show()
        self.showRetraceGrad.hide()    
        self.showRetraceGrad.raise_()    

    def UpdateBMax(self):
        if -1.25 <= float(self.fieldMaxSetValue.text()) <= 1.25:
            self.reformat(self.fieldMaxSetValue.text(), self.fieldMaxSetValue)
        elif float(self.fieldMaxSetValue.text()) >= 1.25:
            self.fieldMaxSetValue.setText('1.25')
            self.reformat(self.fieldMaxSetValue.text(), self.fieldMaxSetValue)
        elif float(self.fieldMaxSetValue.text()) <= -1.25:
            self.fieldMaxSetValue.setText('-1.25')
            self.reformat(self.fieldMaxSetValue.text(), self.fieldMaxSetValue)

    def UpdateBMin(self):
        if 1.25 >= float(self.fieldMinSetValue.text()) >= -1.25:
            self.reformat(self.fieldMinSetValue.text(), self.fieldMinSetValue)
        elif float(self.fieldMinSetValue.text()) >= 1.25:
            self.fieldMinSetValue.setText('1.25')
            self.reformat(self.fieldMinSetValue.text(), self.fieldMinSetValue)
        elif float(self.fieldMinSetValue.text()) <= -1.25:
            self.fieldMinSetValue.setText('-1.25')
            self.reformat(self.fieldMinSetValue.text(), self.fieldMinSetValue)


    def UpdateVMax(self):
        if -10 <= float(self.biasMaxSetValue.text()) <= 10:
            self.reformat(self.biasMaxSetValue.text(), self.biasMaxSetValue)
        elif float(self.biasMaxSetValue.text()) >= 10:
            self.biasMaxSetValue.setText('10.00')
            self.reformat(self.biasMaxSetValue.text(), self.biasMaxSetValue)
        elif float(self.biasMaxSetValue.text()) <= -10:
            self.biasMaxSetValue.setText('-10.00')
            self.reformat(self.biasMaxSetValue.text(), self.biasMaxSetValue)
    def UpdateVMin(self):
        if 10 >= float(self.biasMinSetValue.text()) >= -10.00:
            self.reformat(self.biasMinSetValue.text(), self.biasMinSetValue)
        elif float(self.biasMinSetValue.text()) >= 10:
            self.biasMinSetValue.setText('10.00')
            self.reformat(self.biasMinSetValue.text(), self.biasMinSetValue)
        elif float(self.biasMinSetValue.text()) <= -10:
            self.biasMinSetValue.setText('-10.00')
            self.reformat(self.biasMinSetValue.text(), self.biasMinSetValue)
    


    def setUpPlots(self):
        self.vTraceLine = pg.InfiniteLine(pos = 0.1, angle = 90, movable = True)
        self.hTraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vTraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hTraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.vRetraceLine = pg.InfiniteLine(pos = 0.1, angle = 90, movable = True)
        self.hRetraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vRetraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hRetraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.view0 = pg.PlotItem(name = "Field-Bias-Current")
        self.view0.setLabel('left', text='Bias Voltage', units = 'V')
        self.view0.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view0.showAxis('top', show = True)
        self.view0.showAxis('right', show = True)
        self.view0.setAspectLocked(lock = False, ratio = 1)
        self.tracePlot = pg.ImageView(parent = self.currentTracePlot, view = self.view0)
        self.tracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.tracePlot.ui.menuBtn.hide()
        self.tracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.tracePlot.ui.roiBtn.hide()
        self.tracePlot.ui.menuBtn.hide()
        self.view0.setAspectLocked(False)
        self.view0.invertY(False)
        self.view0.setXRange(-1.25,1.25,0)
        self.view0.setYRange(-10,10, 0)

        self.view0.addItem(self.vTraceLine, ignoreBounds = True)
        self.view0.addItem(self.hTraceLine, ignoreBounds =True)


        self.view1 = pg.PlotItem(name = "Field-Bias-Noise")
        self.view1.setLabel('left', text='Bias Voltage', units = 'V')
        self.view1.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view1.showAxis('top', show = True)
        self.view1.showAxis('right', show = True)
        self.view1.setAspectLocked(lock = False, ratio = 1)
        self.noiseTracePlot = pg.ImageView(parent = self.noiseTracePlot, view = self.view1)
        self.noiseTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.noiseTracePlot.ui.menuBtn.hide()
        self.noiseTracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.noiseTracePlot.ui.roiBtn.hide()
        self.noiseTracePlot.ui.menuBtn.hide()
        self.view1.setAspectLocked(False)
        self.view1.invertY(False)
        self.view1.setXRange(-1.25,1.25,0)
        self.view1.setYRange(-10,10, 0)


        self.view2 = pg.PlotItem(name = "Field-Bias-Current")
        self.view2.setLabel('left', text='Bias Voltage', units = 'V')
        self.view2.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view2.showAxis('top', show = True)
        self.view2.showAxis('right', show = True)
        self.view2.setAspectLocked(lock = False, ratio = 1)
        self.retracePlot = pg.ImageView(parent = self.currentRetracePlot, view = self.view2)
        self.retracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.retracePlot.ui.menuBtn.hide()
        self.retracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.retracePlot.ui.roiBtn.hide()
        self.retracePlot.ui.menuBtn.hide()
        self.view2.setAspectLocked(False)
        self.view2.invertY(False)
        self.view2.setXRange(-1.25,1.25,0)
        self.view2.setYRange(-10,10, 0)

        self.view2.addItem(self.vRetraceLine, ignoreBounds = True)
        self.view2.addItem(self.hRetraceLine, ignoreBounds =True)


        self.view3 = pg.PlotItem(name = "Field-Bias-Noise")
        self.view3.setLabel('left', text='Bias Voltage', units = 'V')
        self.view3.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.view3.showAxis('top', show = True)
        self.view3.showAxis('right', show = True)
        self.view3.setAspectLocked(lock = False, ratio = 1)
        self.noiseRetracePlot = pg.ImageView(parent = self.noiseRetracePlot, view = self.view3)
        self.noiseRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 522))
        self.noiseRetracePlot.ui.menuBtn.hide()
        self.noiseRetracePlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.noiseRetracePlot.ui.roiBtn.hide()
        self.noiseRetracePlot.ui.menuBtn.hide()
        self.view3.setAspectLocked(False)
        self.view3.invertY(False)
        self.view3.setXRange(-1.25,1.25,0)
        self.view3.setYRange(-10,10, 0)

        self.IVTracePlot = pg.PlotWidget(parent = self.curbiasTracePlot)
        self.IVTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IVTracePlot.setLabel('left', 'Current', units = 'mA')
        self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.IVTracePlot.showAxis('right', show = True)
        self.IVTracePlot.showAxis('top', show = True)

        self.IBTracePlot = pg.PlotWidget(parent = self.curfieldTracePlot)
        self.IBTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IBTracePlot.setLabel('left', 'Current', units = 'mA')
        self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.IBTracePlot.showAxis('right', show = True)
        self.IBTracePlot.showAxis('top', show = True)

        self.IVRetracePlot = pg.PlotWidget(parent = self.curbiasRetracePlot)
        self.IVRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IVRetracePlot.setLabel('left', 'Current', units = 'mA')
        self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.IVRetracePlot.showAxis('right', show = True)
        self.IVRetracePlot.showAxis('top', show = True)

        self.IBRetracePlot = pg.PlotWidget(parent = self.curfieldRetracePlot)
        self.IBRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IBRetracePlot.setLabel('left', 'Current', units = 'mA')
        self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.IBRetracePlot.showAxis('right', show = True)
        self.IBRetracePlot.showAxis('top', show = True)



    def checkSweep(self):
        self.startSweep.setEnabled(False)
        sweepMod = self.biasSweepMode.currentIndex()
        blinkMod = self.blink.currentIndex()
        bMin = float(self.fieldMinSetValue.text())
        bMax = float(self.fieldMaxSetValue.text())
        if self.fieldSIStat is True:
            bPoints = int(float(self.fieldPointsSetValue.text()))
        elif self.fieldSIStat is False:
            bPoints = int(1000 * (bMax - bMin) / (float(self.fieldPointsSetValue.text())))
        bSpeed = float(self.fieldSpeedSetValue.text())
        vMin = float(self.biasMinSetValue.text())
        vMax = float(self.biasMaxSetValue.text())
        if self.biasSIStat is False:
            vPoints = int(1000 * (vMax - vMin) / (float(self.biasPointsSetValue.text())))
        elif self.biasSIStat is True:
            vPoints = int(float(self.biasPointsSetValue.text()))
        vSpeed = float(self.biasSpeedSetValue.text())
        if bMin > bMax:
            self.fieldMinSetValue.setText(str(bMax))
            self.fieldMaxSetValue.setText(str(bMin))
            bMin = float(self.fieldMinSetValue.text())
            bMax = float(self.fieldMaxSetValue.text())
        if vMin > vMax:
            self.biasMinSetValue.setText(str(vMax))
            self.biasMaxSetValue.setText(str(vMin))
            vMin = float(self.biasMinSetValue.text())
            vMax = float(self.biasMaxSetValue.text())
        if sweepMod == 1:
            if vMin < 0 and vMax > 0:
                pass
            else:
                vDefault = max(abs(float(vMin)), abs(float(vMax)))
                vMax = vDefault
                vMin = -vDefault
        if bPoints != 0:
            Nb = 1000 * (float(bMax) - float(bMin)) / float(bPoints)
            TotalTime = int(float(vPoints) * float(vSpeed) * float(Nb) / (1000 * 60))
            TotalTime = str(TotalTime)
        else:
            Nb = 0
            TotalTime = "infinite"
        if vSpeed == '0.0':
            vSpeed = '1'
        else:
            pass
        self.bMin = float(bMin)
        self.bMax = float(bMax)
        self.bPoints = int(bPoints)
        self.bSpeed = float(bSpeed)
        self.vMin = float(vMin)
        self.vMax = float(vMax)
        self.vPoints = int(vPoints)
        self.vSpeed = float(vSpeed)
        self.sweepMod = int(sweepMod)
        self.blinkMod = int(blinkMod)
        self.sweepParameters = [bMin, bMax, bPoints, bSpeed, vMin, vMax, vPoints, vSpeed, TotalTime, sweepMod, blinkMod]
        self.dialog = DialogBox(self.sweepParameters)
        self.dialog.show()
        self.dialog.accepted.connect(self.initSweep)
        self.dialog.rejected.connect(self.decline)
        #if self.dialog.exec_():
        #	self.initSweep()

    def decline(self):
        self.startSweep.setEnabled(True)

    def toggleTraceLineCut(self):
        if self.liveTracePlotStatus is True:
            self.view0.addItem(self.vTraceLine, ignoreBounds = True)
            self.view0.addItem(self.hTraceLine, ignoreBounds =True)
            self.vTraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hTraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.liveTracePlotStatus = False
        elif self.liveTracePlotStatus is False:
            self.view0.removeItem(self.vTraceLine)
            self.view0.removeItem(self.hTraceLine)
            self.liveTracePlotStatus = True
    def toggleRetraceLineCut(self):
        if self.liveRetracePlotStatus is True:
            self.view2.addItem(self.vRetraceLine, ignoreBounds = True)
            self.view2.addItem(self.hRetraceLine, ignoreBounds =True)
            self.vRetraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hRetraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.liveRetracePlotStatus = False
        elif self.liveRetracePlotStatus is False:
            self.view2.removeItem(self.vRetraceLine)
            self.view2.removeItem(self.hRetraceLine)
            self.liveRetracePlotStatus = True

    def updateVLineBox(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            posTrace = self.vTraceLine.value()
            self.vCutTracePos.setValue(posTrace)
            self.updateBottomTracePlot()
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            posRetrace = self.vRetraceLine.value()
            self.vCutRetracePos.setValue(posRetrace)
            self.updateBottomRetracePlot()
    def updateHLineBox(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            posTrace = self.hTraceLine.value()
            self.hCutTracePos.setValue(posTrace)
            self.updateBottomTracePlot()
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            posRetrace = self.hRetraceLine.value()
            self.hCutRetracePos.setValue(posRetrace)
            self.updateBottomRetracePlot()
    def changeVLine(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            posTrace = self.vCutTracePos.value()
            self.vTraceLine.setValue(posTrace)
            self.updateBottomTracePlot()
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            posRetrace = self.vCutRetracePos.value()
            self.vRetraceLine.setValue(posRetrace)
            self.updateBottomRetracePlot()
    def changeHLine(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            posTrace = self.hCutTracePos.value()
            self.hTraceLine.setValue(posTrace)
            self.updateBottomTracePlot()
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:            
            posRetrace = self.hCutRetracePos.value()
            self.hRetraceLine.setValue(posRetrace)
            self.updateBottomRetracePlot()

    def toggle_bottomTracePlot(self):
        if self.currentBiasTraceSelect.currentIndex() == 0:
            self.curfieldTracePlot.lower()
            self.curbiasTracePlot.raise_()
        elif self.currentBiasTraceSelect.currentIndex() == 1:
            self.curbiasTracePlot.lower()
            self.curfieldTracePlot.raise_()
    def toggle_bottomRetracePlot(self):
        if self.currentBiasRetraceSelect.currentIndex() == 0:
            self.curfieldRetracePlot.lower()
            self.curbiasRetracePlot.raise_()
        elif self.currentBiasRetraceSelect.currentIndex() == 1:
            self.curbiasRetracePlot.lower()
            self.curfieldRetracePlot.raise_()


    def updateBottomTracePlot(self):
        index = self.currentBiasTraceSelect.currentIndex()
        x0, x1 = (self.bMin, self.bMax)
        y0, y1 = (self.vMin, self.vMax)
        xscale, yscale = (x1-x0) / (self.curTraceData.shape[0] - 1), (y1-y0) / (self.curTraceData.shape[1] - 1)
        if index == 1:
            pos = self.hCutTracePos.value()
            self.IBTracePlot.clear()
            if pos > self.vMax or pos < self.vMin:
                pass
            else:
                p = int(abs(pos - self.vMin) / yscale)
                xVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
                yVals = self.curTraceData[:,p]
                self.IBTracePlot.plot(x = xVals, y = yVals, pen = 0.5)
        elif index == 0:
            pos = self.vCutTracePos.value()
            self.IVTracePlot.clear()
            if pos > self.bMax or pos < self.bMin:
                pass
            else:
                p = int(abs(pos - self.bMin) / xscale)
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.curTraceData[p]
                self.IVTracePlot.plot(x = xVals, y = yVals, pen = 0.5)


                
    def updateBottomRetracePlot(self):
        print 'updating bottom'
        index = self.currentBiasRetraceSelect.currentIndex()
        x0, x1 = (self.bMin , self.bMax)
        y0, y1 = (self.vMin, self.vMax)
        xscale, yscale = (x1-x0) / (self.curRetraceData.shape[0] - 1), (y1-y0) / (self.curTraceData.shape[1] - 1)
        if index == 1:
            pos = self.hCutRetracePos.value()
            self.IBRetracePlot.clear()
            if pos > self.vMax or pos < self.vMin:
                pass
            else:
                p = int(abs(pos - self.vMin) / yscale)
                xVals = np.linspace(self.bMin, self.bMax, num = self.bPoints)
                yVals = self.curRetraceData[:,p]
                self.IBRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)
        elif index == 0:
            pos = self.vCutRetracePos.value()
            self.IVRetracePlot.clear()
            if pos >= self.bMax or pos <=  self.bMin:
                pass
            else:
                p = int(abs(pos - self.bMin) / xscale)
                print p
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.curRetraceData[p]
                self.IVRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)



        

       
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def initSweep(self):
        self.sweepParameters = self.dialog.sweepParameters
        print self.sweepParameters
        #sweepParameters =[bMin, bMax, bPoints, bSpeed, vMin, vMax, vPoints, vSpeed, TotalTime, sweepMod, blinkMod]
        if self.sweepMod == 1:
            self.positive_points = int((self.vPoints * self.vMax) / abs(self.vMax - self.vMin)) + 1
            self.negative_points = self.vPoints - self.positive_points
        else:
            pass

        self.extent = [self.bMin,self.bMax,self.vMin,self.vMax]
        self.curTraceData = np.zeros([self.bPoints,self.vPoints])
        self.noiseTraceData = np.zeros([self.bPoints,self.vPoints])
        self.curRetraceData = np.zeros([self.bPoints,self.vPoints])
        self.noiseRetraceData = np.zeros([self.bPoints,self.vPoints])
        self.biasVals = np.linspace(float(self.vMin),float(self.vMax), num = int(self.vPoints))
        self.fieldVals = np.linspace(float(self.bMin),float(self.bMax), num = int(self.bPoints))
        self.x0, self.x1 = (self.extent[0], self.extent[1])
        self.y0, self.y1 = (self.extent[2], self.extent[3])
        self.xscale, self.yscale = (self.x1-self.x0) / self.curTraceData.shape[0], (self.y1-self.y0) / self.curTraceData.shape[1]
        self.startSweep.setEnabled(False)
        self.analyzeData.setEnabled(False)
        self.tracePlot.setImage(self.curTraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.retracePlot.setImage(self.curRetraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.liveTracePlotStatus = False
        self.liveRetracePlotStatus = False
        self.toggleRetraceLineCut()
        self.toggleTraceLineCut()
        self.plotNoPlot = 0
        #self.sweep()
        self.test_sweep()

    def update_bottomTracePlot(self, i):
        if self.liveTracePlotStatus is False:
            pass
        elif self.liveTracePlotStatus is True:
            index = self.currentBiasTraceSelect.currentIndex()
            if index == 0:
                print 'bottom trace plot'
                self.IVTracePlot.clear()
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.curTraceData[i]
                self.IVTracePlot.plot(x = xVals, y = yVals, pen = 0.5)
            else:
                pass

    def update_bottomRetracePlot(self, i):
        if self.liveRetracePlotStatus is False:
            pass
        elif self.liveRetracePlotStatus is True:
            index = self.currentBiasRetraceSelect.currentIndex()
            if index == 0:
                self.IVRetracePlot.clear()
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                yVals = self.curRetraceData[i]
                self.IVRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)
            else:
                pass

    def updatePlots(self, new_line):
        #new_line = yield self.dv.get()
        if self.sweepMod == 0:
            if self.plotNoPlot%2 == 1:
                i = new_line[0][0]
                new_curData = [(x[4] ) for x in new_line]
                new_noiseData = [x[6] for x in new_line]
                self.curRetraceData[i] = new_curData
                self.noiseRetraceData[i] = new_noiseData
                self.retracePlot.setImage(self.curRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomRetracePlot(i)
                self.plotNoPlot += 1

            elif self.plotNoPlot%2 == 0:
                i = new_line[0][0]
                new_curData = [x[4]  for x in new_line]
                new_noiseData = [x[6] for x in new_line]
                self.curTraceData[i] = new_curData
                self.noiseTraceData[i] = new_noiseData
                self.tracePlot.setImage(self.curTraceData, autoRange = False, autoLevels = True, pos=[self.x0,self.y0],scale=[self.xscale, self.yscale])
                self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomTracePlot(i)
                self.plotNoPlot += 1

        elif self.sweepMod == 1:
            i = new_line[0][0]
            new_curData = [x[4]  for x in new_line]
            new_noiseData = [x[6] for x in new_line]
            if self.plotNoPlot%4 == 0:  #step 1
                self.curTraceData[i][self.negative_points:self.vPoints] = new_curData
                self.noiseTraceData[i][self.negative_points:self.vPoints] = new_noiseData
                self.tracePlot.setImage(self.curTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomTracePlot(i)
                self.plotNoPlot += 1
            elif self.plotNoPlot%4 == 1:  #step 2
                self.curRetraceData[i][self.negative_points:self.vPoints] = new_curData[::-1]
                self.noiseRetraceData[i][self.negative_points:self.vPoints] = new_noiseData[::-1]
                self.retracePlot.setImage(self.curRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomRetracePlot(i)
                self.plotNoPlot += 1
            elif self.plotNoPlot%4 == 2:  #step 3
                self.curTraceData[i][0:self.negative_points] = new_curData[::-1]
                self.noiseTraceData[i][0:self.negative_points] = new_noiseData[::-1]
                self.tracePlot.setImage(self.curTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomTracePlot(i)
                self.plotNoPlot += 1
            elif self.plotNoPlot%4 == 3:  #step 4
                self.curRetraceData[i][0:self.negative_points] = new_curData
                self.noiseRetraceData[i][0:self.negative_points] = new_noiseData
                self.retracePlot.setImage(self.curRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomRetracePlot(i)
                self.plotNoPlot += 1                   
        
    @inlineCallbacks
    def sweep(self):
        #Set all relevant parameters here. Code starts below
        B_min = self.bMin
        B_max = self.bMax
        B_points = self.bPoints
        B_rate = self.bSpeed
        Vbias_min = self.vMin
        Vbias_max = self.vMax
        bias_points = self.vPoints
        V_range = abs(Vbias_max - Vbias_min)

        #UNITS on delay??
        delay = float(self.vSpeed) * 1000

        #AC excitation information for quasi dI/dV measurement. Frequency should be larger than 
        # ~2 kHz to avoid being filtered out by the lock in AC coupling high pass filter.  
        #AC Oscillation amplitude
        vac_amp = self.acAmp
        #Frequency in kilohertz
        frequency = self.acFreq
        #lockin time constant
        timeconstant = 0.001

        #Choose demodulator, and oscillator for which to record data. Make sure this corresponds to the appropriate input. 
        HF_demod = 1
        HF_osc = 1
        HF_out = 1
        HF_in = 1
        #Choose DAC out channel that outputs DC bias (1 through 4)
        DAC_out = self.dacBiasOutChan - 1
        #Choose DAC in channel that reads DC bias (1 through 4)
        DAC_in_ref = self.dacBiasInChan - 1
        #Choose DAC in channel that read DC signal (1 through 4)
        V_out = self.dacDCInChan - 1
        #Choose DAC in channel that read DC signal proportional to AC signal (1 through 4)
        dIdV_out = self.dacACInChan - 1
        #Choose DAC in channel to read quick and dirty noise measurement
        noise = self.dacNoiseInChan - 1
        #Choose DAC out channel that switches between 0 and 5 volts to toggle feedback off then on (aka blink)
        DAC_blink = self.dacBlinkOutChan - 1

        print 'Values assigned starting labrad connection'
        #Connections made in the LabRad connect module
        from labrad.wrappers import connectAsync
        
        print 'import success'
        
        cxn = yield connectAsync(name = 'New name?')
        
        print 'Async success'
        dv = yield cxn.data_vault
        print 'dataVault setup '
        yield dv.cd('nSOT Testing')
        print 'dataVault setup named'
        yield dv.new("nSOT vs. Bias Voltage and Field", ('i','j','B'),('D','I'))
        print 'dataVault setup fine'
        '''
        hf = cxn.hf2li_server
        hf.detect_devices()
        hf.select_device()
        '''
        '''
        
        ips = yield cxn.ips120_power_supply
        yield ips.select_device()
        dac = yield cxn.dac_adc
        yield dac.select_device()
        dv = yield cxn.data_vault
        
        self.ID_NEWSET = 00001
        self.ID_NEWDATA = 00002
        #yield self.dv.signal__new_dataset(self.ID_NEWSET)
        #yield self.dv.addListener(listener=self.new_dataset, source=None, ID=self.ID_NEWSET)
        #yield self.dv.signal__data_available(self.ID_NEWDATA)
        #yield self.dv.addListener(listener=self.updatePlots, source=None, ID=self.ID_NEWDATA)
            
        print 'Connections success!'
        
        '''
        '''
        #Set the first demodulator to use the first oscillator
        yield hf.set_demod_osc(HF_demod,HF_osc)
        #Set the first demodulator to use the desired input
        yield hf.set_demod_input(HF_demod,HF_in)
        #Turn off AC coupling
        yield hf.set_ac(HF_in,True)
        #Turn on difference mode
        yield hf.set_diff(HF_in,False)
        #Turn off 50 ohm impedance
        yield hf.set_imp50(HF_in,False)
        #Set out amplitude
        yield hf.set_output_range(HF_out,vac_amp)
        output_range = yield hf.get_output_range(HF_out)
        yield hf.set_output_amplitude(HF_out,vac_amp/output_range)
        #Set to desired frequency
        yield hf.set_oscillator_freq(HF_osc, frequency*1000)
        #Set demodulator timeconstant
        yield hf.set_demod_time_constant(HF_demod, timeconstant)
        #Turn on output
        yield hf.set_output(HF_out,True)
        
        
        #Set to remote control
        yield ips.set_control(3)
        print 'ips com correct'
        yield self.sleep(1)
        print 'sleepy'
        #Set to high precision \r\n communication protocl
        yield ips.set_comm_protocol(6)
        yield self.sleep(1)
        print 'End ips init'
      
        #Set to go to set point
        yield ips.set_activity(1)
        self.sleep(1)
   
        yield ips.set_fieldsweep_rate(B_rate)


        print "Data file created"
        '''
        B_space = np.linspace(B_min,B_max,B_points)
    
        if self.sweepMod == 0:
            for i in range(0, B_points):
                print "Next desired magnetic field is: " + str(B_space[i])
                '''
                to test: is this necessary?
                if B_space[i]< 0:
                    yield ips.set_polarity(2)
                else:
                    yield ips.set_polarity(1)
                
                #set B field setpoint
                yield ips.set_targetfield(B_space[i])
                
                
                #wait for field to be reached
                while True:
                    curr_field = yield ips.read_parameter(7)
                    if float(curr_field[1:]) <= B_space[i]+0.0000001 and float(curr_field[1:]) >= B_space[i]-0.0000001:
                        break
                    self.sleep(0.25)
                    
                '''
          
                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])

                
                #START ascending/descending sweep mode
                #set bias to minimum value
                yield dac.set_voltage(DAC_out, Vbias_min)
    
                print 'Blink prior to forwards sweep'
                yield dac.set_voltage(DAC_blink, 5)
                self.sleep(0.25)
                yield dac.set_voltage(DAC_blink, 0)
                self.sleep(0.25)

                #Sweep low to high
                print 'Ramping up nSOT bias voltage from ' + str(Vbias_min) + ' to ' + str(Vbias_max) + '.'
                yield dac.buffer_ramp([DAC_out],[DAC_in_ref, V_out, dIdV_out, noise],[Vbias_min],[Vbias_max],bias_points,delay)
                yield self.sleep(delay * bias_points / 1000000)
                d_tmp = yield dac.serial_poll(4, bias_points)
                print 'buffer ramp success'
                    
                print 'd_read success'  
                # d_tmp = yield d_read.result()
                #d_tmp = d_read
                print 'd_read success 2'
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((i, j, B_space[i], d_tmp[0][j], d_tmp[1][j], d_tmp[2][j], d_tmp[3][j]))
                print 'data vault format success'
                
                yield dv.add(formated_data)
                yield self.updatePlots(formated_data)
                
                print 'data added'
                #Sweep high to low, add data, and blink
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to ' + str(Vbias_min) + '.'
     
                yield dac.buffer_ramp([DAC_out],[DAC_in_ref, V_out, dIdV_out, noise],[Vbias_max],[Vbias_min],bias_points,delay)
                yield self.sleep(delay * bias_points / 1000000)
                d_tmp = yield dac.serial_poll(4, bias_points)

                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((i, j, B_space[i], d_tmp[0][j], d_tmp[1][j], d_tmp[2][j], d_tmp[3][j]))
        
                yield dv.add(formated_data)
                yield self.updatePlots(formated_data[::-1])
    
            yield dac.set_voltage(DAC_out, 0)

            yield ips.set_activity(2)

            yield ips.set_control(2)
            
            self.startSweep.setEnabled(True)
            self.analyzeData.setEnabled(True)

            # END ascending/descending sweep mode

        elif self.sweepMod == 1:
            positive_points = int((bias_points * Vbias_max) / V_range)
            negative_points = bias_points - positive_points
            for i in range (0, B_points):
                print "Next desired magnetic field is: " + str(B_space[i])
        
                if B_space[i]< 0:
                    yield ips.set_polarity(2)
                else:
                    yield ips.set_polarity(1)
    
                #set B field setpoint
                yield ips.set_targetfield(B_space[i])
                
                '''
                #wait for field to be reached
                while True:
                    curr_field = yield ips.read_parameter(7)
                    if float(curr_field[1:]) <= B_space[i]+0.0000001 and float(curr_field[1:]) >= B_space[i]-0.0000001:
                        break
                    self.sleep(0.25)
                '''
                
                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])
                #zero bias and blink

                yield dac.set_voltage(DAC_out,0)


                print 'Blink prior to positive sweep'
                yield dac.set_voltage(DAC_blink, 5)
                self.sleep(0.25)
                yield dac.set_voltage(DAC_blink, 0)
                self.sleep(0.25)
    
                #Sweep zero to high
                print 'Ramping up nSOT bias voltage from zero to ' + str(Vbias_max) + '.'
                yield dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, dIdV_out, noise], [0], [Vbias_max], positive_points, delay)
                yield self.sleep(delay * bias_points / 1000000)
                d_tmp = yield dac.serial_poll(4, positive_points)
    
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, positive_points):
                    formated_data.append((i, j, B_space[i], d_tmp[0][j], d_tmp[1][j], d_tmp[2][j], d_tmp[3][j]))

                yield dv.add(formated_data)
                yield self.updatePlots(formated_data)
                #Sweep high to zero, add data, and blink
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to zero.'
     
                yield dac.buffer_ramp([DAC_out],[DAC_in_ref, V_out, dIdV_out, noise],[Vbias_max],[0],positive_points,delay)
                yield self.sleep(delay * bias_points / 1000000)
                d_tmp = yield dac.serial_poll(4, positive_points)

                formated_data = []
                for j in range(0, positive_points):
                    formated_data.append((i, j, B_space[i], d_tmp[0][j], d_tmp[1][j], d_tmp[2][j], d_tmp[3][j]))

                yield dv.add(formated_data)
                yield self.updatePlots(formated_data)
    
                print 'Blinking prior to negative sweep.'
                yield dac.set_voltage(DAC_blink, 5)
                self.sleep(0.25)
                yield dac.set_voltage(DAC_blink, 0)
                self.sleep(0.25)
                #Sweep zero to low
                print 'Ramping down nSOT bias voltage from zero to ' + str(Vbias_min) + '.'
                yield dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, dIdV_out, noise], [0], [Vbias_min], negative_points, delay)
                yield self.sleep(delay * bias_points / 1000000)
                d_tmp = yield dac.serial_poll(4, negative_points)
    
                #Reform data and add to data vault
                formated_data = []
                for j in range(0,negative_points):
                    formated_data.append((i, j, B_space[i], d_tmp[0][j], d_tmp[1][j], d_tmp[2][j], d_tmp[3][j]))

        
                yield dv.add(formated_data)
                yield self.updatePlots(formated_data)
                #Sweep low to zero, add data, and blink
                print 'Ramping nSOT bias voltage up down from ' + str(Vbias_min) + ' to zero.'
     
                yield dac.buffer_ramp([DAC_out],[DAC_in_ref, V_out, dIdV_out, noise], [Vbias_min],[0], negative_points, delay)
                yield self.sleep(delay * bias_points / 1000000)
                d_tmp = yield dac.serial_poll(4, negative_points)

                formated_data = []
                for j in range(0, negative_points):
                    formated_data.append((i, j, B_space[i], d_tmp[0][j], d_tmp[1][j], d_tmp[2][j], d_tmp[3][j]))
        
                yield dv.add(formated_data)
                yield self.updatePlots(formated_data)
    

            # END zero-max, zero-min sweep mode

    

            #Set to go to 0 field
            yield ips.set_activity(2)

            #Set control method back to local control 
            yield ips.set_control(2)
            
            self.startSweep.setEnabled(True)
            self.analyzeData.setEnabled(True)
    
    @inlineCallbacks
    def test_sweep(self):
        #Set all relevant parameters here. Code starts below
        B_min = self.bMin
        B_max = self.bMax
        B_points = self.bPoints
        B_rate = self.bSpeed
        Vbias_min = self.vMin
        Vbias_max = self.vMax
        bias_points = self.vPoints
        V_range = abs(Vbias_max - Vbias_min)

        #UNITS on delay??
        delay = float(self.vSpeed) / 1000

        #AC excitation information for quasi dI/dV measurement. Frequency should be larger than 
        # ~2 kHz to avoid being filtered out by the lock in AC coupling high pass filter.  
        #AC Oscillation amplitude
        vac_amp = self.acAmp
        #Frequency in kilohertz
        frequency = self.acFreq
        #lockin time constant

        print 'Values assigned starting labrad connection'
        #Connections made in the LabRad connect module
        from labrad.wrappers import connectAsync
        
        print 'import success'
        
        cxn = yield connectAsync(name = 'New name?')
        
        print 'Async success'
        dv = yield cxn.data_vault
        print 'dataVault setup '
        #yield dv.cd('nSOT Testing')
        #print 'dataVault setup named'
        yield dv.new("nSOT vs. Bias Voltage and Field", ('i','j','B', 'V'),('D','I', 'N'))
        print 'dataVault setup fine'

        B_space = np.linspace(B_min,B_max,B_points)
    
        if self.sweepMod == 0:
            for i in range(0, B_points):
          
                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])

                
                #START ascending/descending sweep mode
                #set bias to minimum value

                #Sweep low to high

                d_tmp = yield np.linspace(Vbias_min, Vbias_max, num = bias_points)
                yield self.sleep(delay)

                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((i, j, B_space[i], d_tmp[j], i * d_tmp[j], i * d_tmp[j],  np.random.normal() * d_tmp[j]))
                print 'data vault format success'
                
                yield dv.add(formated_data)
                print 'dv added'
                yield self.updatePlots(formated_data)
                
                print 'data added'
                #Sweep high to low, add data, and blink
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to ' + str(Vbias_min) + '.'
     
                d_tmp = yield np.linspace(Vbias_min, Vbias_max, num = bias_points)
                yield self.sleep(delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((i, j, B_space[i], d_tmp[j], i * d_tmp[j], i * d_tmp[j],  np.random.normal() * d_tmp[j]))
                print 'data vault format success'
                
                yield dv.add(formated_data)
                yield self.updatePlots(formated_data)
            
            self.startSweep.setEnabled(True)
            self.analyzeData.setEnabled(True)
            print 'sweep complete'

            # END ascending/descending sweep mode

        elif self.sweepMod == 1:
            positive_points = int((bias_points * Vbias_max) / V_range)
            negative_points = bias_points - positive_points
            for i in range (0, B_points):

    
                #Sweep zero to high
                print 'Ramping up nSOT bias voltage from zero to ' + str(Vbias_max) + '.'
                d_tmp = yield np.linspace(0, Vbias_max, num = positive_points)
                yield self.sleep(delay)

                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, positive_points):
                    formated_data.append((i, j, B_space[i], d_tmp[j], i * d_tmp[j], i * d_tmp[j],  np.random.normal() * d_tmp[j]))
                print 'data vault format success'
                
                yield dv.add(formated_data)
                print 'dv added'
                yield self.updatePlots(formated_data)
                #Sweep high to zero, add data, and blink
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to zero.'
     
                d_tmp = yield np.linspace(Vbias_max, 0, num = positive_points)
                yield self.sleep(delay)

                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, positive_points):
                    formated_data.append((i, j, B_space[i], d_tmp[j], i * d_tmp[j], i * d_tmp[j],  np.random.normal() * d_tmp[j]))
                print 'data vault format success'
                
                yield dv.add(formated_data)
                print 'dv added'
                yield self.updatePlots(formated_data)


                d_tmp = yield np.linspace(0, Vbias_min, num = negative_points)
                yield self.sleep(delay)

                
                #Reform data and add to data vault
                formated_data = []
                for j in range(1, negative_points):
                    formated_data.append((i, j, B_space[i], d_tmp[j], i * d_tmp[j], i * d_tmp[j],  np.random.normal() * d_tmp[j]))
                print 'data vault format success'
                
                yield dv.add(formated_data)
                print 'dv added'
                yield self.updatePlots(formated_data)
                print 'Ramping nSOT bias voltage up down from ' + str(Vbias_min) + ' to zero.'
     
                d_tmp = yield np.linspace(Vbias_min, 0, num = negative_points)
                yield self.sleep(delay)

                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, negative_points):
                    formated_data.append((i, j, B_space[i], d_tmp[j], i * d_tmp[j], i * d_tmp[j],  np.random.normal() * d_tmp[j]))
                print 'data vault format success'
                
                yield dv.add(formated_data)
                print 'dv added'
                yield self.updatePlots(formated_data)
    

            # END zero-max, zero-min sweep mode
            
            self.startSweep.setEnabled(True)
            self.analyzeData.setEnabled(True)
            print 'sweep complete'

    def closeEvent(self, e):
        pass


        
class dacSettings(QtGui.QDialog, Ui_dacSet):
    def __init__(self,parent = None):
        super(dacSettings, self).__init__(parent)

        self.setupUi(self)
        self.window = parent

        self.biasOutChannel.setText(str(self.window.dacBiasOutChan))
        self.blinkOutChannel.setText(str(self.window.dacBlinkOutChan))

        self.biasInChannel.setText(str(self.window.dacBiasInChan))
        self.dcInChannel.setText(str(self.window.dacDCInChan))
        self.acInChannel.setText(str(self.window.dacACInChan))
        self.noiseInChannel.setText(str(self.window.dacNoiseInChan))


        self.cancelDAC.clicked.connect(self._close)
        self.okDAC.clicked.connect(self._ok)

    def closeEvent(self, e):
        self.window.dacSetOpen.setEnabled(True)
        self.close()

    def _close(self):
        self.window.dacSetOpen.setEnabled(True)
        self.close()
    def _ok(self):
        self.inputChans = [int(self.biasInChannel.text()) , int(self.dcInChannel.text()) , int(self.acInChannel.text()) , int(self.noiseInChannel.text())]
        self.outputChans = [int(self.biasOutChannel.text()),  int(self.blinkOutChannel.text())]
        dif = [self.inputChans[i] - self.inputChans[j] for i in range(0,4) for j in range(i+1,4) ]
        if any(x>4 or x<1 for x in self.outputChans):
            self.warning.setText("Output channels must be \n between 1 and 4.")
            self.warning.setStyleSheet("QLabel#warning {color: rgb(255,0, 0);}")
        elif any(x>4 or x<1 for x in self.inputChans):
            self.warning.setText("Input channels must be \n between 1 and 4.")
            self.warning.setStyleSheet("QLabel#warning {color: rgb(255,0, 0);}") 
        elif int(self.biasOutChannel.text()) == int(self.blinkOutChannel.text()):
            self.warning.setText("Output channels must be  \n distinct.")
            self.warning.setStyleSheet("QLabel#warning {color: rgb(255,0, 0);}")
        elif any(int(x) == 0 for x in dif):
            self.warning.setText("Input channels must be \n distinct.")
            self.warning.setStyleSheet("QLabel#warning {color: rgb(255,0, 0);}")

        else:
            self.window.dacBiasOutChan = int(self.biasOutChannel.text())
            self.window.dacBlinkOutChan = int(self.blinkOutChannel.text())

            self.window.dacBiasInChan = self.inputChans[0]
            self.window.dacDCInChan = self.inputChans[1]
            self.window.dacACInChan = self.inputChans[2]
            self.window.dacNoiseInChan = self.inputChans[3]

            self.window.dacSetOpen.setEnabled(True)
            self.accept()
            self.close()

class acSettings(QtGui.QDialog, Ui_acSet):
    def __init__(self, parent = None):
        super(acSettings, self).__init__(parent)
        self.setupUi(self)

        self.window = parent

        self.acFreqValue.setText(str(self.window.acFreq))
        self.acAmpValue.setText(str(self.window.acAmp))

        self.cancelACSet.clicked.connect(self._close)
        self.okACSet.clicked.connect(self._ok)

    def closeEvent(self, e):
        self.window.acSetOpen.setEnabled(True)
        self.close()

    def _close(self):
        self.window.acSetOpen.setEnabled(True)
        self.close()
    def _ok(self):
        self.window.acFreq = float(self.acFreqValue.text())
        self.window.acAmp = float(self.acAmpValue.text())
        self.window.acSetOpen.setEnabled(True)
        self.close()


class Plotter(QtGui.QDialog, Ui_Plotter):
    def __init__(self):
        super(Plotter, self).__init__()
        self.window = window
        self.setupUi(self)

        self.showGrad.hide()
        self.diamCalc.setIcon(QtGui.QIcon("diameter.png"))

        self.window = window

        self.Data = copy.copy(self.window.curTraceData)
        self.noiseData =copy.copy(self.window.noiseTraceData)
        self.extent = [self.window.bMin, self.window.bMax, self.window.vMin, self.window.vMax]
        self.deltaV = float((self.window.vMax - self.window.vMin) / self.window.vPoints)
        self.deltaB = float((self.window.bMax - self.window.bMin) / self.window.bPoints)
        self.x0, self.x1 = (self.extent[0], self.extent[1])
        self.y0, self.y1 = (self.extent[2], self.extent[3])
        self.xscale, self.yscale = (self.x1-self.x0) / self.Data.shape[0], (self.y1-self.y0) / self.Data.shape[1]

        self.rect = pg.RectROI((0,0),(0.1,0.1), movable = True)
        self.rect.addScaleHandle((1,1), (.5,.5), lockAspect = False)
        self.rect.sigRegionChangeFinished.connect(self.rectCoords)

        self.setupPlots()
        self.hideGrad.clicked.connect(self.shrink)
        self.showGrad.clicked.connect(self.enlarge)

        self.plotOptions.currentIndexChanged.connect(self.changePlot)
        #self.traceOptions.currentIndexChanged.connect(self.changeTrace)

        self.vhSelect.currentIndexChanged.connect(self.toggleBottomPlot)
        
        self.diamCalc.clicked.connect(self.calculateDiam)
        self.addPlot.clicked.connect(self.newPlot)
        self.vCutPos.valueChanged.connect(self.changeVertLine)
        self.hCutPos.valueChanged.connect(self.changeHorLine)

    def rectCoords(self):
        bounds = self.rect.parentBounds()
        print bounds
        x1 = self.extent[0] + bounds.topRight[0]*self.xscale
        y1 = self.extent[2] + bounds.topRight[1]*self.yscale
        x2 = self.extent[0] + bounds.bottomLeft[0]*self.xscale
        y2 = self.extent[2] + bounds.bottomLeft[1]*self.yscale 

    def setupPlots(self):
        plotData = self.Data
        self.plotData =plotData
        self.vLine = pg.InfiniteLine(pos = (self.window.bMax + self.window.bMin) / 2, angle = 90, movable = True)
        self.hLine = pg.InfiniteLine(pos = (self.window.vMax + self.window.vMin) / 2, angle = 0, movable = True)
        self.vLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.biasVals = np.linspace(float(self.window.vMin),float(self.window.vMax), num = int(self.window.vPoints))
        self.fieldVals = np.linspace(float(self.window.bMin),float(self.window.bMax), num = int(self.window.bPoints))

        self.viewBig = pg.PlotItem(name = "Plot")
        self.viewBig.setLabel('left', text='Bias Voltage', units = 'V')
        self.viewBig.setLabel('bottom', text='Magnetic Field', units = 'T')
        self.viewBig.showAxis('top', show = True)
        self.viewBig.showAxis('right', show = True)
        self.viewBig.setAspectLocked(lock = False, ratio = 1)
        self.viewBig.invertY(False)
        self.mainPlot = pg.ImageView(parent = self.mainPlotArea, view = self.viewBig)
        self.mainPlot.setGeometry(QtCore.QRect(0, 0, 750, 450))
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.mainPlot.ui.roiBtn.hide()
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.viewBig.setAspectLocked(False)
        self.viewBig.setXRange(self.window.bMin,self.window.bMax,0.1)
        self.viewBig.setYRange(self.window.vMin,self.window.vMax, 0.1)

        self.viewBig.addItem(self.vLine, ignoreBounds = True)
        self.viewBig.addItem(self.hLine, ignoreBounds =True)


        self.viewSmallX = pg.PlotItem(name = "Current-Bias")
        self.XZPlot = pg.PlotWidget(parent = self.XZPlotArea)
        self.XZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.XZPlot.setLabel('left', 'Current', units = 'mA')
        self.XZPlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.XZPlot.showAxis('right', show = True)
        self.XZPlot.showAxis('top', show = True)

        self.YZPlot = pg.PlotWidget(parent = self.YZPlotArea)
        self.YZPlot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.YZPlot.setLabel('left', 'Current', units = 'mA')
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
            self.plotData = self.Data
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("Current vs Bias Voltage and Magnetic Field")
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 1:
            self.plotData = np.gradient(self.Data, self.deltaV, axis = 1)
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("dI/dV vs Bias Voltage and Magnetic Field")
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 2:
            self.plotData = np.gradient(self.Data, self.deltaB, axis = 0)
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("dI/dB vs Bias Voltage and Magnetic Field")
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 3:
            self.plotData = self.noiseData
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("Noise vs Bias Voltage and Magnetic Field")
            self.plotTitle.setStyleSheet("QLabel#plotTitle {color: rgb(255,255,255); font: 11pt;}")
        elif self.plotOptions.currentIndex() == 4:
            sens_noise = self.noiseData
            dIdB = np.gradient(self.Data, self.deltaB, axis = 0)
            data = copy.copy(self.Data)
            for i in range(0, self.Data.shape[0]):
                for j in range(0, self.Data.shape[1]):
                    if sens_noise[i,j] != 0:
                        data[i,j] = dIdB[i,j]/ sens_noise[i,j]
                    elif sens_noise[i,j] == 0:
                        data[i,j] = 1000
            self.plotData = data
            self.mainPlot.setImage(self.plotData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
            self.plotTitle.setText("Sensitivity vs Bias Voltage and Magnetic Field")
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
        print 'what'
        index = self.vhSelect.currentIndex()
        if index == 1:
            pass
        elif index == 0:
            self.XZPlot.clear()
            #extent = [bMin, bMax, vMin, vMax]
            x0, x1 = (float(self.extent[0]), float(self.extent[1]))
            y0, y1 = (float(self.extent[2]), float(self.extent[3]))
            xscale, yscale = 1.0*(x1-x0) / self.Data.shape[0], 1.0 * (y1-y0) / self.Data.shape[1]
            if pos > y1 or pos < y0:
                print 'this'
                self.XZPlot.clear()
            else:
                print 'that'
                p = int(abs((pos - y0)) / yscale)
                xVals = self.fieldVals
                yVals = self.Data[:,p]
                self.XZPlot.plot(x = xVals, y = yVals, pen = 0.5)


    def updateYZPlot(self, pos):
        print 'how'
        index = self.vhSelect.currentIndex()
        if index == 0:
            pass
        elif index == 1:
            self.YZPlot.clear()
            #extent = [bMin, bMax, vMin, vMax]
            x0, x1 = (float(self.extent[0]), float(self.extent[1]))
            y0, y1 = (float(self.extent[2]), float(self.extent[3]))
            xscale, yscale = 1.0*(x1-x0) / self.Data.shape[0], 1.0 * (y1-y0) / self.Data.shape[1]
            if pos > x1 or pos < x0:
                self.YZPlot.clear()
            else:
                p = int(abs((pos - x0)) / xscale)
                xVals = self.biasVals
                yVals = self.Data[p]
                self.YZPlot.plot(x = xVals, y = yVals, pen = 0.5)




#    def changeTrace(self):



    def newPlot(self):
        self.newPlot = Plotter()
        self.newPlot.show()


#GUI Window for finalizing sweep parameters, inherits the list of sweep parameters from the MainWindow checkSweep function
class DialogBox(QtGui.QDialog, Ui_DialogBox):
    def __init__(self, sweepParameters):
        super(DialogBox, self).__init__()
        self.window = window
        self.setupUi(self)
        #self.sweepParameters = self.window.sweepParameters
        self.sweepParameters = sweepParameters

        self.fieldMinValue.setText(str(self.sweepParameters[0]))
        self.fieldMinValue.setStyleSheet("QLabel#fieldMinValue {color: rgb(255,255,255);}")
        self.fieldMaxValue.setText(str(self.sweepParameters[1]))
        self.fieldMaxValue.setStyleSheet("QLabel#fieldMaxValue {color: rgb(255,255,255);}")
        self.fieldIncValue.setText(str(self.sweepParameters[2]))
        self.fieldIncValue.setStyleSheet("QLabel#fieldIncValue {color: rgb(255,255,255);}")
        self.fieldSpeedValue.setText(str(self.sweepParameters[3]))
        self.fieldSpeedValue.setStyleSheet("QLabel#fieldSpeedValue {color: rgb(255,255,255);}")

        self.biasMinValue.setText(str(self.sweepParameters[4]))
        self.biasMinValue.setStyleSheet("QLabel#biasMinValue {color: rgb(255,255,255);}")
        self.biasMaxValue.setText(str(self.sweepParameters[5]))
        self.biasMaxValue.setStyleSheet("QLabel#biasMaxValue {color: rgb(255,255,255);}")
        self.biasIncValue.setText(str(self.sweepParameters[6]))
        self.biasIncValue.setStyleSheet("QLabel#biasIncValue {color: rgb(255,255,255);}")
        self.biasSpeedValue.setText(str(self.sweepParameters[7]))
        self.biasSpeedValue.setStyleSheet("QLabel#biasSpeedValue {color: rgb(255,255,255);}")

        if self.sweepParameters[9] == 0:
            self.sweepModeSetting.setText('Max to Min')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(255,255,255);}")
        elif self.sweepParameters[9] ==1:
            self.sweepModeSetting.setText('Min to Max')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(255,255,255);}")
        elif self.sweepParameters[9] ==2:
            self.sweepModeSetting.setText('Zero to Max/Min')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(255,255,255);}")

        if self.sweepParameters[10] == 0:
            self.blinkOrNot.setText('Enabled')
            self.blinkOrNot.setStyleSheet("QLabel#blinkOrNot {color: rgb(255,255,255);}")
        elif self.sweepParameters[10] == 1:
            self.blinkOrNot.setText('Disabled')
            self.blinkOrNot.setStyleSheet("QLabel#blinkOrNot {color: rgb(255,255,255);}")
        if self.sweepParameters[8] != "infinite":
            self.sweepTime.setText(self.sweepParameters[8])
            self.sweepTime.setStyleSheet("QLabel#sweepTime {color: rgb(255,255,255);}")
        else:
            self.sweepTime.setTextFormat(1)
            self.sweepTime.setText('<html><head/><body><p><span style=" font-size:10pt; color:#ffffff;">&#8734;</span></p></body></html>')

        self.startSweepReally.clicked.connect(self.testSweep)
        self.beIndecisive.clicked.connect(self.exitDialog)

    #If accepted, runs the sweep
    def testSweep(self):
        self.accept()
        #self.close()
    def exitDialog(self):
        #self.window.startSweep.setEnabled(True)
        self.reject()
        #self.close()
    def closeEvent(self, e):
        self.window.startSweep.setEnabled(True)

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))