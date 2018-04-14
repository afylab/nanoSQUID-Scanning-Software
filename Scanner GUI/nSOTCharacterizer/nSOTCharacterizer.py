from __future__ import division
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
characterGUI = path + r"\character_GUI.ui"
dialogBox = path + r"\sweepCheck.ui"
dacSet = path + "\dacChannels.ui"
acSet = path + r"\acSetting.ui"
prelimSweep = path + r"\preliminarySweep.ui"
toeReminder = path + r"\toeReminder.ui"
serlist = path + r"\requiredServers.ui"


Ui_MainWindow, QtBaseClass = uic.loadUiType(characterGUI)
Ui_DialogBox, QtBaseClass = uic.loadUiType(dialogBox)
Ui_dacSet, QtBaseClass = uic.loadUiType(dacSet)
Ui_acSet, QtBaseClass = uic.loadUiType(acSet)
Ui_prelimSweep, QtBaseClass = uic.loadUiType(prelimSweep)
Ui_toeReminder, QtBaseClass = uic.loadUiType(toeReminder)
Ui_ServerList, QtBaseClass = uic.loadUiType(serlist)

class Window(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)
        #QtGui.QDialog.__init__(self)
        self.parent = parent
        
        self.reactor = reactor
        self.setupUi(self)
        self.setUpPlots()

        self.magnetPower.clear()

        self.plotNoPlot = 0
        self.dacBiasOutChan, self.dacBlinkOutChan, self.voltsOutChan, self.currentOutChan = 1, 2, 4, 3
        self.dacBiasInChan, self.dacDCInChan, self.dacACInChan, self.dacNoiseInChan = 1, 2 ,3 ,4
        self.dacOutputChannels = [self.dacBiasOutChan, self.dacBlinkOutChan, self.voltsOutChan, self.currentOutChan]
        self.dacInputChannels = [self.dacBiasInChan, self.dacDCInChan, self.dacACInChan, self.dacNoiseInChan]
        self.dacChannelList = [self.dacInputChannels, self.dacOutputChannels]
        self.acFreq, self.acAmp = 4.0, 2.0

        self.fieldPos = 0

        self.startSweep.clicked.connect(self.toeCheck)
        self.abortFlag = False
        self.abortSweep.setEnabled(False)
        self.abortSweep.clicked.connect(self.abortion)
        self.prelim.clicked.connect(self.runPrelimSweep)

        self.fieldStepsInc.clicked.connect(self.toggleFieldSteps)
        self.fieldSIStat = True
        self.biasStepsInc.clicked.connect(self.toggleBiasSteps)
        self.biasSIStat = True

        self.liveTracePlot.clicked.connect(self.toggleTraceLineCut)
        self.liveTracePlotStatus = False
        self.liveRetracePlot.clicked.connect(self.toggleRetraceLineCut)
        self.liveRetracePlotStatus = False

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
        
        self.tabsTrace.currentChanged.connect(self.toggleTracePlots)
        self.tabsRetrace.currentChanged.connect(self.toggleRetracePlots)
        
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize to no data to avoid line cut error
        self.isData = False
        
        #By default use dac_adc to blink
        self.blinkDevice = 'DAC ADC'
        
        #Initialize the servers to False
        self.cxn = False
        self.dv = False
        self.dac = False
        self.ips = False
        self.dcbox = False
        
        self.lockInterface()

    def moveDefault(self):
        self.move(550,10)
        
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.dv = dict['dv']
            self.dac = dict['dac_adc']
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        if not self.cxn: 
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.dac:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.dv:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            self.magnetPower.addItem('Toellner 8851')
            self.unlockInterface()

        try:
            self.dcbox = dict['dc_box']
        except:
            pass
        if not not self.dcbox:
            pass
        else:
            #TODO let know somehow that can use DC box
            pass
        
    def connectRemoteLabRAD(self,dict):
        try:
            self.ips = dict['ips120']
        except:
            pass
        if not not self.ips:
            self.magnetPower.addItem('IPS 120-10')
            
    def disconnectLabRAD(self):
        self.magnetPower.removeItem(0)
        if not not self.ips:
            self.magnetPower.removeItem(0)
        self.dv = False
        self.cxn = False
        self.dac = False
        self.ips = False
        self.dcbox = False
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")

            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
    def runPrelimSweep(self):
        self.prelim.setEnabled(False)
        self.prelimSweep = preliminarySweep(self.reactor, self.dv, self.dac, self.dacChannelList, self)
        self.prelimSweep.show()
    
    def reformat(self, number, lineEdit):
        number = float(number)
        reformatted = '{:.2f}'.format(number)
        lineEdit.setText(reformatted)

    def dacSet(self):
        self.dacSetOpen.setEnabled(False)
        self.dacSettings = dacSettings(self)
        if self.dacSettings.exec_():
            print self.dacBiasOutChan, self.dacBlinkOutChan, self.dacBiasInChan, self.dacDCInChan, self.dacACInChan, self.dacNoiseInChan, self.blinkDevice
    
    def acSet(self):
        self.acSetOpen.setEnabled(False)
        self.acSettings = acSettings(self)
        if self.acSettings.exec_():
            print self.acFreq, self.acAmp

    def abortion(self):
        self.abortFlag = True


    def toggleFieldSteps(self):
        if self.fieldSIStat is True:
            self.FieldInc.setText("Millitesla per Step")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
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
                self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
                self.fieldSIStat = False
        else:
            self.FieldInc.setText("Number of Steps")
            self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
            inc = float(self.fieldPointsSetValue.text())
            bMax = float(self.fieldMaxSetValue.text())
            bMin = float(self.fieldMinSetValue.text())
            if inc != 0:
                steps = int(1000 * (bMax - bMin) / (inc)) +1 
                self.fieldPointsSetValue.setText(str(steps))
                self.fieldSIStat = True
            else:
                self.FieldInc.setText("Number of Steps")
                self.FieldInc.setStyleSheet("QLabel#FieldInc {color: rgb(168,168,168); font: 10pt;}")
                self.fieldSIStat = True           
    def toggleBiasSteps(self):
        if self.biasSIStat is True:
            self.BiasInc.setText("Millivolts per Step")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
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
                self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
                self.biasSIStat = False
        else:
            self.BiasInc.setText("Number of Steps")
            self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
            inc = float(self.biasPointsSetValue.text())
            vMax = float(self.biasMaxSetValue.text())
            vMin = float(self.biasMinSetValue.text())
            if inc != 0:
                steps = int(1000 * (vMax - vMin) / (inc))
                self.biasPointsSetValue.setText(str(steps))
                self.biasSIStat = True
            else:
                self.BiasInc.setText("Number of Steps")
                self.BiasInc.setStyleSheet("QLabel#BiasInc {color: rgb(168,168,168); font: 10pt;}")
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
        if float(self.fieldMaxSetValue.text()) < 0 and self.magnetPower.currentText() == 'Toellner 8851':
            self.fieldMaxSetValue.setText('0')
            
        elif -1.25 <= float(self.fieldMaxSetValue.text()) <= 1.25:
            pass
        elif float(self.fieldMaxSetValue.text()) >= 1.25:
            self.fieldMaxSetValue.setText('1.25')


        elif float(self.fieldMaxSetValue.text()) <= -1.25:
            self.fieldMaxSetValue.setText('-1.25')
        print 'here'            
        self.reformat(self.fieldMaxSetValue.text(), self.fieldMaxSetValue)


    def UpdateBMin(self):
        if float(self.fieldMinSetValue.text()) < 0 and self.magnetPower.currentText() == 'Toellner 8851':
            self.fieldMinSetValue.setText('0')    
    
        elif 1.25 >= float(self.fieldMinSetValue.text()) >= -1.25:
            pass
        elif float(self.fieldMinSetValue.text()) >= 1.25:
            self.fieldMinSetValue.setText('1.25')        
            
        elif float(self.fieldMinSetValue.text()) <= -1.25:
            self.fieldMinSetValue.setText('-1.25')
            print 'got ehre'
        print 'here'
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
        self.vTraceLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hTraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vTraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hTraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        
        self.vTraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hTraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vTraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hTraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.vRetraceLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hRetraceLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vRetraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hRetraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
        
        self.vRetraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hRetraceNoiseLine = pg.InfiniteLine(pos = 0, angle = 0, movable = True)
        self.vRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
        self.hRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)

        self.view0 = pg.PlotItem(name = "Field-Bias-DC Volts")
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
        
        self.view1.addItem(self.vTraceNoiseLine, ignoreBounds = True)
        self.view1.addItem(self.hTraceNoiseLine, ignoreBounds =True)


        self.view2 = pg.PlotItem(name = "Field-Bias-DC Volts")
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
        
        self.view3.addItem(self.vRetraceNoiseLine, ignoreBounds = True)
        self.view3.addItem(self.hRetraceNoiseLine, ignoreBounds =True)

        self.IVTracePlot = pg.PlotWidget(parent = self.curbiasTracePlot)
        self.IVTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IVTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.IVTracePlot.showAxis('right', show = True)
        self.IVTracePlot.showAxis('top', show = True)

        self.IBTracePlot = pg.PlotWidget(parent = self.curfieldTracePlot)
        self.IBTracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IBTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.IBTracePlot.showAxis('right', show = True)
        self.IBTracePlot.showAxis('top', show = True)

        self.IVRetracePlot = pg.PlotWidget(parent = self.curbiasRetracePlot)
        self.IVRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IVRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.IVRetracePlot.showAxis('right', show = True)
        self.IVRetracePlot.showAxis('top', show = True)

        self.IBRetracePlot = pg.PlotWidget(parent = self.curfieldRetracePlot)
        self.IBRetracePlot.setGeometry(QtCore.QRect(0, 0, 640, 175))
        self.IBRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.IBRetracePlot.showAxis('right', show = True)
        self.IBRetracePlot.showAxis('top', show = True)
        

        self.tracePlotNow = "bias"
        self.retracePlotNow = "bias"
        self.traceNoiseNow = "bias"
        self.retraceNoiseNow = "bias"
    
    def toeCheck(self):
        self.checkToe = toellnerReminder()
        self.startSweep.setEnabled(False)
        if self.magnetPower.currentText() != 'Toellner 8851':
            self.checkSweep()
        else:
            self.checkToe.show()
            self.checkToe.accepted.connect(self.checkSweep)
            self.checkToe.rejected.connect(self.decline)

    def checkSweep(self):
        sweepMod = self.biasSweepMode.currentIndex()
        blinkMod = self.blink.currentIndex()
        magPower = self.magnetPower.currentText()
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
        
        
        if bPoints != 0:
            tLatent = 5
            T = (np.absolute(self.bMin) + np.absolute(self.bMax)) / (self.bSpeed) + (self.bPoints/self.bSpeed)* (np.absolute(self.bMax - self.bMin) / (self.bPoints)) + (self.bPoints/60) * ( (self.vPoints - 1) * (self.vSpeed/1000000) + float(tLatent))
            hours = int(T / 60) 
            minutes = int(T)%60
            TotalTime = str(hours) + ' hours ' + str(minutes) + ' minutes' 
        
        else:
            TotalTime = "infinite"
        
        self.sweepParameters = [bMin, bMax, bPoints, bSpeed, vMin, vMax, vPoints, vSpeed, TotalTime, sweepMod, blinkMod]
        self.dialog = DialogBox(self.sweepParameters, magPower)
        self.dialog.show()
        self.dialog.accepted.connect(self.initSweep)
        self.dialog.rejected.connect(self.decline)
        #if self.dialog.exec_():
        #    self.initSweep()

    def decline(self):
        self.startSweep.setEnabled(True)
        self.abortSweep.setEnabled(False)

    def toggleTraceLineCut(self):
        if self.liveTracePlotStatus is True:
            self.view0.addItem(self.vTraceLine, ignoreBounds = True)
            self.view0.addItem(self.hTraceLine, ignoreBounds =True)
            self.view1.addItem(self.vTraceNoiseLine, ignoreBounds = True)
            self.view1.addItem(self.hTraceNoiseLine, ignoreBounds = True)
            self.vTraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hTraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.vTraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hTraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.liveTracePlotStatus = False
        elif self.liveTracePlotStatus is False:
            self.view0.removeItem(self.vTraceLine)
            self.view0.removeItem(self.hTraceLine)
            self.view1.removeItem(self.vTraceNoiseLine)
            self.view1.removeItem(self.hTraceNoiseLine)
            self.liveTracePlotStatus = True
    def toggleRetraceLineCut(self):
        if self.liveRetracePlotStatus is True:
            self.view2.addItem(self.vRetraceLine, ignoreBounds = True)
            self.view2.addItem(self.hRetraceLine, ignoreBounds =True)
            self.view3.addItem(self.vRetraceNoiseLine, ignoreBounds = True)
            self.view3.addItem(self.hRetraceNoiseLine, ignoreBounds = True)
            self.vRetraceLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hRetraceLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.vRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateVLineBox)
            self.hRetraceNoiseLine.sigPositionChangeFinished.connect(self.updateHLineBox)
            self.liveRetracePlotStatus = False
        elif self.liveRetracePlotStatus is False:
            self.view2.removeItem(self.vRetraceLine)
            self.view2.removeItem(self.hRetraceLine)
            self.view3.removeItem(self.vRetraceNoiseLine)
            self.view3.removeItem(self.hRetraceNoiseLine)
            self.liveRetracePlotStatus = True

    def updateVLineBox(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.vTraceLine.value()
                self.vCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.vTraceNoiseLine.value()
                self.vCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass            
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.vRetraceLine.value()
                print posRetrace
                self.vCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.vRetraceNoiseLine.value()
                print posRetrace
                self.vCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
    def updateHLineBox(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.hTraceLine.value()
                self.hCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.hTraceNoiseLine.value()
                self.hCutTracePos.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.hRetraceLine.value()
                print posRetrace
                self.hCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.hRetraceNoiseLine.value()
                print posRetrace
                self.hCutRetracePos.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            
    def changeVLine(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.vCutTracePos.value()
                self.vTraceLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.vCutTracePos.value()
                self.vTraceNoiseLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.vCutRetracePos.value()
                self.vRetraceLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.vCutRetracePos.value()
                self.vRetraceNoiseLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
    def changeHLine(self):
        if self.liveTracePlotStatus is True:
            pass
        elif self.liveTracePlotStatus is False:
            if self.tabsTrace.currentIndex() == 0:
                posTrace = self.hCutTracePos.value()
                self.hTraceLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
            elif self.tabsTrace.currentIndex() == 1:
                posTrace = self.hCutTracePos.value()
                self.hTraceNoiseLine.setValue(posTrace)
                if self.isData == True:
                    self.updateBottomTracePlot()
                else:
                    pass
        if self.liveRetracePlotStatus is True:
            pass
        elif self.liveRetracePlotStatus is False:    
            if self.tabsRetrace.currentIndex() == 0:
                posRetrace = self.hCutRetracePos.value()
                self.hRetraceLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
            elif self.tabsRetrace.currentIndex() == 1:
                posRetrace = self.hCutRetracePos.value()
                self.hRetraceNoiseLine.setValue(posRetrace)
                if self.isData == True:
                    self.updateBottomRetracePlot()
                else:
                    pass
    def toggleTracePlots(self):
        self.currentBiasTraceSelect.currentIndexChanged.disconnect(self.toggle_bottomTracePlot)
        self.updateHLineBox()
        self.updateVLineBox()
        self.currentBiasTraceSelect.removeItem(0)
        self.currentBiasTraceSelect.removeItem(0)
        if self.tabsTrace.currentIndex() == 1:
            self.currentBiasTraceSelect.addItem("RMS Noise vs Bias")
            self.currentBiasTraceSelect.addItem("RMS Noise vs Field")
            if self.traceNoiseNow == "bias":
                self.currentBiasTraceSelect.setCurrentIndex(0)
                self.curfieldTracePlot.lower()
                self.curbiasTracePlot.raise_()
                self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.traceNoiseNow == "field":
                self.currentBiasTraceSelect.setCurrentIndex(1)
                self.curbiasTracePlot.lower()
                self.curfieldTracePlot.raise_()
                self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVTracePlot.setLabel('left', 'RMS Noise', units = 'V')
            self.IBTracePlot.setLabel('left', 'RMS Noise', units = 'V')

        elif self.tabsTrace.currentIndex() == 0:
            self.currentBiasTraceSelect.addItem("DC Output vs Bias")
            self.currentBiasTraceSelect.addItem("DC Output vs Field")
            if self.tracePlotNow == "bias":
                self.currentBiasTraceSelect.setCurrentIndex(0)
                self.curfieldTracePlot.lower()
                self.curbiasTracePlot.raise_()
                self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.tracePlotNow == "field":
                self.currentBiasTraceSelect.setCurrentIndex(1)
                self.curbiasTracePlot.lower()
                self.curfieldTracePlot.raise_()
                self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
            self.IBTracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
        self.currentBiasTraceSelect.currentIndexChanged.connect(self.toggle_bottomTracePlot)
    
    def toggleRetracePlots(self):
        self.currentBiasRetraceSelect.currentIndexChanged.disconnect(self.toggle_bottomRetracePlot)
        self.updateHLineBox()
        self.updateVLineBox()
        self.currentBiasRetraceSelect.removeItem(0)
        self.currentBiasRetraceSelect.removeItem(0)
        if self.tabsRetrace.currentIndex() == 1:
            self.currentBiasRetraceSelect.addItem("RMS Noise vs Bias")
            self.currentBiasRetraceSelect.addItem("RMS Noise vs Field")
            if self.retraceNoiseNow == "bias":
                self.currentBiasRetraceSelect.setCurrentIndex(0)
                self.curfieldRetracePlot.lower()
                self.curbiasRetracePlot.raise_()
                self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.retraceNoiseNow == "field":
                self.currentBiasRetraceSelect.setCurrentIndex(1)
                self.curbiasRetracePlot.lower()
                self.curfieldRetracePlot.raise_()
                self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVRetracePlot.setLabel('left', 'RMS Noise', units = 'V')
            self.IBRetracePlot.setLabel('left', 'RMS Noise', units = 'V')
        elif self.tabsRetrace.currentIndex() == 0:
            self.currentBiasRetraceSelect.addItem("DC Output vs Bias")
            self.currentBiasRetraceSelect.addItem("DC Output vs Field")
            if self.retracePlotNow == "bias":
                self.currentBiasRetraceSelect.setCurrentIndex(0)
                self.curfieldRetracePlot.lower()
                self.curbiasRetracePlot.raise_()
                self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            elif self.retracePlotNow == "field":
                self.currentBiasRetraceSelect.setCurrentIndex(1)
                self.curbiasRetracePlot.lower()
                self.curfieldRetracePlot.raise_()
                self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.IVRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')
            self.IBRetracePlot.setLabel('left', 'SSAA DC Output', units = 'V')            
        self.currentBiasRetraceSelect.currentIndexChanged.connect(self.toggle_bottomRetracePlot)
        
    def toggle_bottomTracePlot(self):
        if self.tabsTrace.currentIndex() == 0 and self.tracePlotNow == "field":
            self.tracePlotNow = "bias"
            self.curfieldTracePlot.lower()
            self.curbiasTracePlot.raise_()
            self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
        elif self.tabsTrace.currentIndex() == 0 and self.tracePlotNow == "bias":
            self.tracePlotNow = "field"
            self.curbiasTracePlot.lower()
            self.curfieldTracePlot.raise_()
            self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
        elif self.tabsTrace.currentIndex() == 1 and self.traceNoiseNow == "field":
            self.traceNoiseNow = "bias"
            self.curfieldTracePlot.lower()
            self.curbiasTracePlot.raise_()
            self.IVTracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
        elif self.tabsTrace.currentIndex() == 1 and self.traceNoiseNow == "bias":
            self.traceNoiseNow = "field"
            self.curbiasTracePlot.lower()
            self.curfieldTracePlot.raise_()
            self.IBTracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            if self.isData == True:
                self.updateBottomTracePlot()
            else:
                pass
    def toggle_bottomRetracePlot(self):
        if self.tabsRetrace.currentIndex() == 0 and self.retracePlotNow == "field":
            self.retracePlotNow = "bias"
            self.curfieldRetracePlot.lower()
            self.curbiasRetracePlot.raise_()
            self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass
        elif self.tabsRetrace.currentIndex() == 0 and self.retracePlotNow == "bias":
            self.retracePlotNow = "field"
            self.curbiasRetracePlot.lower()
            self.curfieldRetracePlot.raise_()
            self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass
        elif self.tabsRetrace.currentIndex() == 1 and self.retraceNoiseNow == "field":
            self.retraceNoiseNow = "bias"
            self.curfieldRetracePlot.lower()
            self.curbiasRetracePlot.raise_()
            self.IVRetracePlot.setLabel('bottom', 'Bias Voltage', units = 'V')
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass
        elif self.tabsRetrace.currentIndex() == 1 and self.retraceNoiseNow == "bias":
            self.retraceNoiseNow = "field"
            self.IBRetracePlot.setLabel('bottom', 'Magnetic Field', units = 'T')
            self.curbiasRetracePlot.lower()
            self.curfieldRetracePlot.raise_()
            if self.isData == True:
                self.updateBottomRetracePlot()
            else:
                pass


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
                if self.tabsTrace.currentIndex() == 0:
                    yVals = self.curTraceData[:,p]
                elif self.tabsTrace.currentIndex() == 1:
                    yVals = self.noiseTraceData[:,p]
                self.IBTracePlot.plot(x = xVals, y = yVals, pen = 0.5)
        elif index == 0:
            pos = self.vCutTracePos.value()
            self.IVTracePlot.clear()
            if pos > self.bMax or pos < self.bMin:
                pass
            else:
                p = int(abs(pos - self.bMin) / xscale)
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                if self.tabsTrace.currentIndex() == 0:
                    yVals = self.curTraceData[p]
                elif self.tabsTrace.currentIndex() == 1:
                    yVals = self.noiseTraceData[p]
                self.IVTracePlot.plot(x = xVals, y = yVals, pen = 0.5)
                
    def updateBottomRetracePlot(self):
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
                if self.tabsRetrace.currentIndex() == 0:
                    yVals = self.curRetraceData[:,p]
                elif self.tabsRetrace.currentIndex() == 1:
                    yVals = self.noiseRetraceData[:,p]
                self.IBRetracePlot.plot(x = xVals, y = yVals, pen = 0.5)
        elif index == 0:
            pos = self.vCutRetracePos.value()
            self.IVRetracePlot.clear()
            if pos >= self.bMax or pos <=  self.bMin:
                pass
            else:
                p = int(abs(pos - self.bMin) / xscale)
                xVals = np.linspace(self.vMin, self.vMax, num = self.vPoints)
                if self.tabsRetrace.currentIndex() == 0:
                    yVals = self.curRetraceData[p]
                elif self.tabsRetrace.currentIndex() == 1:
                    yVals = self.noiseRetraceData[p]
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
        self.abortSweep.setEnabled(True)
        self.magnetPower.setEnabled(False)
        self.blink.setEnabled(False)
        self.biasSweepMode.setEnabled(False)
        self.prelim.setEnabled(False)
        self.fieldMinSetValue.setReadOnly(True)
        self.fieldMaxSetValue.setReadOnly(True)
        self.fieldPointsSetValue.setReadOnly(True)
        self.fieldSpeedSetValue.setReadOnly(True)
        self.biasMinSetValue.setReadOnly(True)
        self.biasMaxSetValue.setReadOnly(True)
        self.biasPointsSetValue.setReadOnly(True)
        self.biasSpeedSetValue.setReadOnly(True)
        #self.analyzeData.setEnabled(False)
        self.tracePlot.setImage(self.curTraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.retracePlot.setImage(self.curRetraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = True , autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.liveTracePlotStatus = False
        self.liveRetracePlotStatus = False
        self.toggleRetraceLineCut()
        self.toggleTraceLineCut()
        self.plotNoPlot = 0
        self.abortFlag = False
        if self.magnetPower.currentText() == 'IPS 120-10':
            self.isData = True
            self.ips_sweep()
        elif self.magnetPower.currentText() == 'Toellner 8851':
            self.isData = True
            self.toe_sweep()


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

        if self.sweepMod == 0:
            if self.plotNoPlot%2 == 1:
                i = new_line[0][1]
                new_curData = [(x[5] ) for x in new_line]
                new_noiseData = [x[6] for x in new_line]
                self.curRetraceData[i] = new_curData
                self.noiseRetraceData[i] = new_noiseData
                self.retracePlot.setImage(self.curRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomRetracePlot(i)
                self.plotNoPlot += 1

            elif self.plotNoPlot%2 == 0:
                i = new_line[0][1]
                new_curData = [x[5]     for x in new_line]
                new_noiseData = [x[6] for x in new_line]
                self.curTraceData[i] = new_curData
                self.noiseTraceData[i] = new_noiseData
                self.tracePlot.setImage(self.curTraceData, autoRange = False, autoLevels = True, pos=[self.x0,self.y0],scale=[self.xscale, self.yscale])
                self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomTracePlot(i)
                self.plotNoPlot += 1

        elif self.sweepMod == 1:
            i = new_line[0][1]
            new_curData = [x[5]     for x in new_line]
            new_noiseData = [x[6] for x in new_line]
            if self.plotNoPlot%2 == 1:
                i = new_line[0][0]
                new_curData = [(x[5] ) for x in new_line]
                new_noiseData = [x[6] for x in new_line]
                self.curRetraceData[i] = new_curData
                self.noiseRetraceData[i] = new_noiseData
                self.retracePlot.setImage(self.curRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.noiseRetracePlot.setImage(self.noiseRetraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomRetracePlot(i)
                self.plotNoPlot += 1

            elif self.plotNoPlot%2 == 0:
                i = new_line[0][1]
                new_curData = [x[5]     for x in new_line]
                new_noiseData = [x[6] for x in new_line]
                self.curTraceData[i] = new_curData
                self.noiseTraceData[i] = new_noiseData
                self.tracePlot.setImage(self.curTraceData, autoRange = False, autoLevels = True, pos=[self.x0,self.y0],scale=[self.xscale, self.yscale])
                self.noiseTracePlot.setImage(self.noiseTraceData, autoRange = False, autoLevels = True, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                self.update_bottomTracePlot(i)
                self.plotNoPlot += 1    

       
    @inlineCallbacks
    def toe_sweep(self):
        #Set all relevant parameters here. Code starts below
        B_min = self.bMin
        B_max = self.bMax
        B_points = self.bPoints
        B_rate = self.bSpeed
        Vbias_min = self.vMin
        Vbias_max = self.vMax
        bias_points = self.vPoints
        V_range = abs(Vbias_max - Vbias_min)

        #Converts DAC delay (DAC reads microseconds while GUI input is given in milliseconds)
        delay = float(self.vSpeed) * 1000
        
        #DAC OUTPUTS
        
        #DAC out channel that outputs DC bias (1 through 4)
        DAC_out = self.dacBiasOutChan - 1
        #DAC out channel that switches between 0 and 5 volts to toggle feedback off then on (aka blink)
        DAC_blink = self.dacBlinkOutChan - 1
        #DAC channel that sets the voltage setpoint for the Toellner power supply
        DAC_set_volt = self.voltsOutChan - 1
        #DAC channel that sets the current setpoint for the Toellner power supply
        DAC_set_current = self.currentOutChan - 1
        
        
        #DAC INPUTS
        
        #DAC in channel that reads DC bias (1 through 4)
        DAC_in_ref = self.dacBiasInChan - 1
        #DAC in channel that read DC signal (1 through 4)
        V_out = self.dacDCInChan - 1
        #DAC in channel that read DC signal proportional to AC signal (1 through 4)
        dIdV_out = self.dacACInChan - 1
        #DAC in channel to read noise measurement
        noise = self.dacNoiseInChan - 1


        #AC excitation information for quasi dI/dV measurement. Frequency should be larger than 
        # ~2 kHz to avoid being filtered out by the lock in AC coupling high pass filter.  
        #THIS FUNCTIONALITY IS DISABLED AND MUST BE SET MANUALLY ON THE SR830
        #AC Oscillation amplitude
        vac_amp = self.acAmp
        #Frequency in kilohertz
        frequency = self.acFreq
        '''
        Function to set target magnetic filed on Toellner power supply. Given initial and final field values (B_i and B_f in Tesla) 
        as well as a specified field sweep rate (B_speed in Tesla per minute), the function ramps the Toellner power supply current
        and voltage such that the power supply stays in constant current mode and changes the magnetic field between the appropriate
        values.
         
        '''
        @inlineCallbacks
        def sweep_field(B_i, B_f, B_speed):
            #Toellner voltage set point / DAC voltage out conversion [V_Toellner / V_DAC]
            VV_conv = 3.20
            #Toellner current set point / DAC voltage out conversion [I_Toellner / V_DAC]
            IV_conv = 1.0 

            #Field / Current ratio on the dipper magnet (0.132 [Tesla / Amp])
            IB_conv = 0.132

            #Starting and ending field values in Tesla, use positive field values for now
            B_range = np.absolute(B_f - B_i)

            #Delay between DAC steps in microseconds
            magnet_delay = 5000
            #Converts between microseconds and minutes [us / minute]
            t_conv = 6e07

            #Sets the appropriate DAC buffer ramp parameters
            sweep_steps = int((t_conv * B_range) / (B_speed * magnet_delay))  + 1
            v_start = B_i / (IB_conv * IV_conv)
            v_end = B_f / (IB_conv * IV_conv)

            #Sets an appropraite voltage set point to ensure that the Toellner power supply stays in constant current mode
            # assuming a parasitic resistance of R_p between the power supply and magnet
            overshoot = 5
            R_p = 2
            V_setpoint =  (overshoot * R_p * np.amax([B_i, B_f])) / (VV_conv * IB_conv)
            V_initial = (overshoot * R_p * np.amin([B_i, B_f])) / (VV_conv * IB_conv)
            if V_setpoint > 10.0:
                V_setpoint = 10.0
            else:
                pass
            if V_initial > 10.0:
                V_initial = 10.0
            else:
                pass

            #Ramps the DAC such that the Toellner voltage setpoint stays in constant current mode
            ramp_steps = int(np.absolute(V_setpoint - V_initial) * 1000)
            ramp_delay = 1000
            yield self.dac.buffer_ramp([DAC_set_volt], [DAC_in_ref], [V_initial], [V_setpoint], ramp_steps, ramp_delay)
            
            #Sweeps field from B_i to B_f
            print 'Sweeping field from ' + str(B_i) + ' to ' + str(B_f)+'.'
            yield self.dac.buffer_ramp([DAC_set_current],[DAC_in_ref],[v_start],[v_end], sweep_steps, magnet_delay)
        
        @inlineCallbacks
        def toe_breakSweep(bVal, vVal):
            #Ramps the bias voltage down to zero, sleeps, and ramps the magnetic field back to zero, all very gently
            if vVal != 0:
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [vVal], [0], int(vVal * 1000), 10000)
            else:
                pass
            yield self.sleep(1)
            if bVal != 0:
                yield sweep_field(bVal, 0, 0.1)
                yield self.dac.set_voltage(DAC_set_volt, 0)
            else:
                pass

            self.startSweep.setEnabled(True)
            self.abortSweep.setEnabled(False)
            self.magnetPower.setEnabled(True)
            self.blink.setEnabled(True)
            self.biasSweepMode.setEnabled(True)
            self.prelim.setEnabled(True)
            self.fieldMinSetValue.setReadOnly(False)
            self.fieldMaxSetValue.setReadOnly(False)
            self.fieldPointsSetValue.setReadOnly(False)
            self.fieldSpeedSetValue.setReadOnly(False)
            self.biasMinSetValue.setReadOnly(False)
            self.biasMaxSetValue.setReadOnly(False)
            self.biasPointsSetValue.setReadOnly(False)
            self.biasSpeedSetValue.setReadOnly(False)



        yield self.dv.new("nSOT vs. Bias Voltage and Field", ['Trace Index', 'B Field Index','Bias Voltage Index','B Field','Bias Voltage'],['DC SSAA Output','Noise', 'dI/dV'])
        print 'DataVault setup complete'

        B_space = np.linspace(B_min, B_max, B_points)
        
        
        #Minimum Bias to Maximum Bias Sweep Mode
        if self.sweepMod == 0:

            yield self.dac.set_voltage(DAC_out, 0)
            #If minimum bias voltage is not zero, sweep bias to minimum value, 1mV per step with a reasonably short delay
            if Vbias_min != 0:
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [Vbias_min], int(Vbias_min * 1000), 1000)
            else:
                pass

            
            for i in range(0, B_points):
                
                if i == 0:
                    
                    if self.abortFlag == False:
                        pass
                    else:
                        yield toe_breakSweep(0, Vbias_min)
                        break
                    
                    if B_space[0] != 0:
                        print 'Ramping field to ' + str(B_space[0])+'.'
                        yield sweep_field(0, B_space[0], B_rate)
                    else:
                        pass
                else:
                    if self.abortFlag == False:
                        pass
                    else:
                        yield toe_breakSweep(B_space[i-1], Vbias_min)
                        break
                    yield sweep_field(B_space[i-1], B_space[i], B_rate)
                    
                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])
                
                print 'Blinking prior to sweep'
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], Vbias_min)
                    break
                        
                #Sweep from minimum to maximum bias voltage
                print 'Ramping up nSOT bias voltage from ' + str(Vbias_min) + ' to ' + str(Vbias_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_min], [Vbias_max], bias_points, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data)

                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], Vbias_max)
                    break
                
                #Sweep from maximum to minimum bias voltage
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to ' + str(Vbias_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_max], [Vbias_min], bias_points, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data[::-1])
                
                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], Vbias_min)
                    break
                
            #If minimum bias voltage is not zero, sweep bias back to zero, 1mV per step with a reasonably short delay
            if Vbias_min != 0:
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_min], [0], int(Vbias_min * 1000), 1000)
            else:
                pass
    
            yield self.dac.set_voltage(DAC_out, 0)
            
            #Go to zero field and set power supply voltage setpoint to zero.
            sweep_field(B_space[-1], 0, B_rate)
            yield self.dac.set_voltage(DAC_set_volt, 0)


            self.startSweep.setEnabled(True)
            self.abortSweep.setEnabled(False)
            self.magnetPower.setEnabled(True)
            self.blink.setEnabled(True)

            self.biasSweepMode.setEnabled(True)

            self.prelim.setEnabled(True)

            self.fieldMinSetValue.setReadOnly(False)
            self.fieldMaxSetValue.setReadOnly(False)

            self.fieldPointsSetValue.setReadOnly(False)
            self.fieldSpeedSetValue.setReadOnly(False)
            self.biasMinSetValue.setReadOnly(False)
            self.biasMaxSetValue.setReadOnly(False)
            self.biasPointsSetValue.setReadOnly(False)
            self.biasSpeedSetValue.setReadOnly(False)


        #Zero to Minimum and Maximum Bias Voltage Sweep Mode
        elif self.sweepMod == 1:
        
            positive_points = int((bias_points * Vbias_max) / V_range)
            negative_points = bias_points - positive_points

            
            for i in range (0, B_points):
            
                if i == 0:
                    if B_space[0] != 0:
                        print 'Ramping field to ' + str(B_space[0])+'.'
                        yield sweep_field(0, B_space[0], B_rate)
                    else:
                        pass
                else:
                    yield sweep_field(B_space[i-1], B_space[i], B_rate)

                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])

                #Set bias voltage to zero and blink
                yield self.dac.set_voltage(DAC_out,0)
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], 0)
                    break
                
                #Sweep from zero volts to maximum bias voltage
                print 'Ramping up nSOT bias voltage from zero to ' + str(Vbias_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [Vbias_max], positive_points, delay)
    
                #Reform data and add to data vault
                #formated_data = []
                data_uptrace = []
                for j in range(0, positive_points):
                    data_uptrace.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], Vbias_max)
                    break

                
                #Sweep from maximum bias voltage to zero volts and blink
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_max], [0], positive_points, delay)

                #formated_data = []
                data_upretrace = []
                for j in range(0, positive_points):
                    data_upretrace.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], 0)
                    break
                
                #Sweep from zero volts to minimum bias voltage
                print 'Ramping down nSOT bias voltage from zero to ' + str(Vbias_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [Vbias_min], negative_points, delay)
    
                #Reform data and add to data vault
                #formated_data = []
                data_downtrace = []
                for j in range(0, negative_points):
                    data_downtrace.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                
                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], Vbias_min)
                    break
                
                #Sweep from minimum bias voltage to zero volts
                print 'Ramping nSOT bias voltage up down from ' + str(Vbias_min) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_min], [0], negative_points, delay)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield toe_breakSweep(B_space[i], 0)
                    break

                #Reform data and add to data vault
                #formated_data = []
                data_downretrace = []
                for j in range(0, negative_points):
                    data_downretrace.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                trace_data = []
                retrace_data = []
                trace_data = data_downtrace[::-1] + data_uptrace
                retrace_data = data_downretrace + data_upretrace[::-1]
                
                yield self.dv.add(trace_data)
                yield self.updatePlots(trace_data)
                yield self.dv.add(retrace_data)
                yield self.updatePlots(retrace_data)

            yield self.dac.set_voltage(DAC_out, 0)
            
            #Go to zero field and set power supply voltage setpoint to zero.
            sweep_field(B_space[-1], 0, B_rate)
            yield self.dac.set_voltage(DAC_set_volt, 0)
                

            self.startSweep.setEnabled(True)
            self.abortSweep.setEnabled(False)
            self.magnetPower.setEnabled(True)
            self.blink.setEnabled(True)
            self.biasSweepMode.setEnabled(True)
            self.prelim.setEnabled(True)
            self.fieldMinSetValue.setReadOnly(False)
            self.fieldMaxSetValue.setReadOnly(False)
            self.fieldPointsSetValue.setReadOnly(False)
            self.fieldSpeedSetValue.setReadOnly(False)
            self.biasMinSetValue.setReadOnly(False)
            self.biasMaxSetValue.setReadOnly(False)
            self.biasPointsSetValue.setReadOnly(False)
            self.biasSpeedSetValue.setReadOnly(False)

    @inlineCallbacks
    def blinkFunc(self):
        if self.blinkDevice == 'DAC ADC':
            yield self.dac.set_voltage(self.dacBlinkOutChan - 1, 5)
            yield self.sleep(0.25)
            yield self.dac.set_voltage(self.dacBlinkOutChan - 1, 0)
            yield self.sleep(0.25)
        elif self.blinkDevice == 'DC Box':
            yield self.dcbox.set_voltage(self.dacBlinkOutChan - 1, 5)
            yield self.sleep(0.25)
            yield self.dcbox.set_voltage(self.dacBlinkOutChan - 1, 0)
            yield self.sleep(0.25)

    @inlineCallbacks
    def ips_sweep(self):
        #Set all relevant parameters here. Code starts below
        B_min = self.bMin
        B_max = self.bMax
        B_points = self.bPoints
        B_rate = self.bSpeed
        Vbias_min = self.vMin
        Vbias_max = self.vMax
        bias_points = self.vPoints
        V_range = abs(Vbias_max - Vbias_min)

        #Converts DAC delay (DAC reads microseconds while GUI input is given in milliseconds)
        delay = float(self.vSpeed) * 1000
        
        #DAC OUTPUTS
        
        #DAC out channel that outputs DC bias (1 through 4)
        DAC_out = self.dacBiasOutChan - 1
        #DAC out channel that switches between 0 and 5 volts to toggle feedback off then on (aka blink)
        DAC_blink = self.dacBlinkOutChan - 1
        #DAC channel that sets the voltage setpoint for the Toellner power supply
        DAC_set_volt = self.voltsOutChan - 1
        #DAC channel that sets the current setpoint for the Toellner power supply
        DAC_set_current = self.currentOutChan - 1
        
        
        #DAC INPUTS
        blinkDev = self.blinkDevice
        #DAC in channel that reads DC bias (1 through 4)
        DAC_in_ref = self.dacBiasInChan - 1
        #DAC in channel that read DC signal (1 through 4)
        V_out = self.dacDCInChan - 1
        #DAC in channel that read DC signal proportional to AC signal (1 through 4)
        dIdV_out = self.dacACInChan - 1
        #DAC in channel to read noise measurement
        noise = self.dacNoiseInChan - 1


        #AC excitation information for quasi dI/dV measurement. Frequency should be larger than 
        # ~2 kHz to avoid being filtered out by the lock in AC coupling high pass filter.  
        #THIS FUNCTIONALITY IS DISABLED AND MUST BE SET MANUALLY ON THE SR830
        #AC Oscillation amplitude
        vac_amp = self.acAmp
        #Frequency in kilohertz
        frequency = self.acFreq
        
        @inlineCallbacks
        def ips_breakSweep(bVal, vVal):
            #Ramps the bias voltage down to zero in mV steps, sleeps 1s, then ramps the magnetic field back to zero, all very gently
            if vVal != 0:
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [vVal], [0], int(vVal * 1000), 10000)
            else:
                pass
            yield self.sleep(1)
            if bVal != 0:
                yield self.ips.set_control(3)
                #Go to 0 field
                yield self.ips.set_targetfield(0)
                yield self.ips.set_activity(2)

                #Set control method back to local control 
                yield self.ips.set_control(2)
            else:
                pass
            
            self.startSweep.setEnabled(True)
            self.abortSweep.setEnabled(False)
            self.magnetPower.setEnabled(True)
            self.blink.setEnabled(True)
            self.biasSweepMode.setEnabled(True)
            self.prelim.setEnabled(True)
            self.fieldMinSetValue.setReadOnly(False)
            self.fieldMaxSetValue.setReadOnly(False)
            self.fieldPointsSetValue.setReadOnly(False)
            self.fieldSpeedSetValue.setReadOnly(False)
            self.biasMinSetValue.setReadOnly(False)
            self.biasMaxSetValue.setReadOnly(False)
            self.biasPointsSetValue.setReadOnly(False)
            self.biasSpeedSetValue.setReadOnly(False)


        yield self.dv.new("nSOT vs. Bias Voltage and Field", ['Trace Index', 'B Field Index','Bias Voltage Index','B Field','Bias Voltage'],['DC SSAA Output','Noise', 'dI/dV'])
        print 'DataVault setup complete'

        B_space = np.linspace(B_min,B_max,B_points)
        
        
        #Minimum Bias to Maximum Bias Sweep Mode
        if self.sweepMod == 0:
        
            yield self.ips.set_control(3)
            yield self.sleep(0.25)
            yield self.ips.set_comm_protocol(6)
            yield self.sleep(0.25)
            yield self.ips.set_activity(1)
            yield self.sleep(0.25)
            yield self.ips.set_fieldsweep_rate(B_rate)
            yield self.ips.set_control(2)
            
            yield self.dac.set_voltage(DAC_out, 0)

            
            #If minimum bias voltage is not zero, sweep bias to minimum value, 1mV per step with a reasonably short delay
            if Vbias_min != 0:
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [Vbias_min], int(Vbias_min * 1000), 1000)
            else:
                pass

            
            for i in range(0, B_points):
                yield self.ips.set_control(3)
                yield self.ips.set_targetfield(B_space[i])
                yield self.ips.set_control(2)
                #wait for field to be reached
                while True:
                    yield self.ips.set_control(3)
                    curr_field = yield self.ips.read_parameter(7)
                    yield self.ips.set_control(2)
                    if float(curr_field[1:]) <= B_space[i]+0.00001 and float(curr_field[1:]) >= B_space[i]-0.00001:
                        break
                    yield self.sleep(0.25)
                    
                print 'Starting sweep with magnetic field set to: ' + str(B_space[i])
                
                print 'Blinking prior to sweep'
                yield self.blinkFunc()
                
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i],Vbias_min)
                    break

                #Sweep from minimum to maximum bias voltage
                print 'Ramping up nSOT bias voltage from ' + str(Vbias_min) + ' to ' + str(Vbias_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_min], [Vbias_max], bias_points, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data)
                
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i],Vbias_max)
                    break


                #Sweep from maximum to minimum bias voltage
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to ' + str(Vbias_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_max], [Vbias_min], bias_points, delay)
                
                #Reform data and add to data vault
                formated_data = []
                for j in range(0, bias_points):
                    formated_data.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                yield self.dv.add(formated_data)
                yield self.updatePlots(formated_data[::-1])
                
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i],Vbias_min)
                    break

                    
                
            #If minimum bias voltage is not zero, sweep bias back to zero, 1mV per step with a reasonably short delay
            if Vbias_min != 0:
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_min], [0], int(Vbias_min * 1000), 1000)
            else:
                pass
    
            yield self.dac.set_voltage(DAC_out, 0)
            yield self.sleep(0.25)
            
            #Go to 0 field
            yield self.ips.set_control(3)
            yield self.ips.set_targetfield(0)
            yield self.ips.set_activity(2)

            #Set control method back to local control 
            yield self.ips.set_control(2)


            self.startSweep.setEnabled(True)
            self.abortSweep.setEnabled(False)
            self.magnetPower.setEnabled(True)
            self.blink.setEnabled(True)
            self.biasSweepMode.setEnabled(True)
            self.prelim.setEnabled(True)
            self.fieldMinSetValue.setReadOnly(False)
            self.fieldMaxSetValue.setReadOnly(False)
            self.fieldPointsSetValue.setReadOnly(False)
            self.fieldSpeedSetValue.setReadOnly(False)
            self.biasMinSetValue.setReadOnly(False)
            self.biasMaxSetValue.setReadOnly(False)
            self.biasPointsSetValue.setReadOnly(False)
            self.biasSpeedSetValue.setReadOnly(False)

        #Zero to Minimum and Maximum Bias Voltage Sweep Mode
        elif self.sweepMod == 1:
        
            positive_points = int((bias_points * Vbias_max) / V_range)
            negative_points = bias_points - positive_points
            
            yield self.ips.set_control(3)
            yield self.sleep(0.25)
            yield self.ips.set_comm_protocol(6)
            yield self.sleep(0.25)
            yield self.ips.set_activity(1)
            yield self.sleep(0.25)
            yield self.ips.set_fieldsweep_rate(B_rate)
            yield self.ips.set_control(2)
           
            for i in range (0, B_points):
                yield self.ips.set_control(3)
                yield self.ips.set_targetfield(B_space[i])
                yield self.ips.set_control(2)
                #wait for field to be reached
                while True:
                    yield self.ips.set_control(3)
                    curr_field = yield self.ips.read_parameter(7)
                    yield self.ips.set_control(2)
                    if float(curr_field[1:]) <= B_space[i]+0.00001 and float(curr_field[1:]) >= B_space[i]-0.00001:
                        break
                    yield self.sleep(0.25)
                    
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i], 0)
                    break


                #Set bias voltage to zero and blink
                yield self.dac.set_voltage(DAC_out,0)
                yield self.blinkFunc()
                
                #Sweep from zero volts to maximum bias voltage
                print 'Ramping up nSOT bias voltage from zero to ' + str(Vbias_max) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [Vbias_max], positive_points, delay)
    
                #Reform data and add to data vault
                #formated_data = []
                data_uptrace = []
                for j in range(0, positive_points):
                    data_uptrace.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i],Vbias_max)
                    break

                
                
                #Sweep from maximum bias voltage to zero volts and blink
                print 'Ramping nSOT bias voltage back down from ' + str(Vbias_max) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_max], [0], positive_points, delay)

                #formated_data = []
                data_upretrace = []
                for j in range(0, positive_points):
                    data_upretrace.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)

                    
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i], 0)
                    break

                yield self.blinkFunc()

                
                #Sweep from zero volts to minimum bias voltage
                print 'Ramping down nSOT bias voltage from zero to ' + str(Vbias_min) + '.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [0], [Vbias_min], negative_points, delay)
    
                #Reform data and add to data vault
                #formated_data = []
                data_downtrace = []
                for j in range(0, negative_points):
                    data_downtrace.append((0, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))

                
                #yield dv.add(formated_data)
                #yield self.updatePlots(formated_data)
                
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i],Vbias_min)
                    break

                
                #Sweep from minimum bias voltage to zero volts
                print 'Ramping nSOT bias voltage up down from ' + str(Vbias_min) + ' to zero.'
                dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, V_out, noise, dIdV_out], [Vbias_min], [0], negative_points, delay)

                #Reform data and add to data vault
                #formated_data = []
                data_downretrace = []
                for j in range(0, negative_points):
                    data_downretrace.append((1, i, j, B_space[i], dac_read[0][j], dac_read[1][j], dac_read[2][j], dac_read[3][j]))
                
                trace_data = []
                retrace_data = []
                trace_data = data_downtrace[::-1] + data_uptrace
                retrace_data = data_downretrace + data_upretrace[::-1]
                
                yield self.dv.add(trace_data)
                yield self.updatePlots(trace_data)
                yield self.dv.add(retrace_data)
                yield self.updatePlots(retrace_data)
                
                    
                if self.abortFlag == False:
                    pass
                else:
                    yield ips_breakSweep(B_space[i], 0)
                    break

            yield self.dac.set_voltage(DAC_out, 0)
            
            #Go to 0 field
            yield self.ips.set_control(3)
            yield self.ips.set_targetfield(0)
            yield self.ips.set_activity(2)

            #Set control method back to local control 
            yield self.ips.set_control(2)
                

            self.startSweep.setEnabled(True)
            self.abortSweep.setEnabled(False)
            self.magnetPower.setEnabled(True)
            self.blink.setEnabled(True)
            self.biasSweepMode.setEnabled(True)
            self.prelim.setEnabled(True)
            self.fieldMinSetValue.setReadOnly(False)
            self.fieldMaxSetValue.setReadOnly(False)
            self.fieldPointsSetValue.setReadOnly(False)
            self.fieldSpeedSetValue.setReadOnly(False)
            self.biasMinSetValue.setReadOnly(False)
            self.biasMaxSetValue.setReadOnly(False)
            self.biasPointsSetValue.setReadOnly(False)
            self.biasSpeedSetValue.setReadOnly(False)

    def lockInterface(self):
        #TODO Fill in
        pass
        
    def unlockInterface(self):
        #TODO Fill in
        pass
            
    def closeEvent(self, e):
        pass

class dacSettings(QtGui.QDialog, Ui_dacSet):
    def __init__(self, parent = None):
        super(dacSettings, self).__init__(parent)
        self.window = parent
        self.setupUi(self)

        self.biasOutChannel.setValue(self.window.dacBiasOutChan)
        self.blinkOutChannel.setValue(self.window.dacBlinkOutChan)
        self.voltsOutChannel.setValue(self.window.voltsOutChan)
        self.currentOutChannel.setValue(self.window.currentOutChan)

        self.biasInChannel.setValue(self.window.dacBiasInChan)
        self.dcInChannel.setValue(self.window.dacDCInChan)
        self.acInChannel.setValue(self.window.dacACInChan)
        self.noiseInChannel.setValue(self.window.dacNoiseInChan)

        if not not self.window.dcbox:
            self.comboBox_blinkDevice.addItem('DC Box')
            if self.window.blinkDevice == 'DC Box':
                self.comboBox_blinkDevice.setCurrentIndex(1)

        self.cancelDAC.clicked.connect(self._close)
        self.okDAC.clicked.connect(self._ok)

    def closeEvent(self, e):
        self.window.dacSetOpen.setEnabled(True)
        self.close()

    def _close(self):
        self.window.dacSetOpen.setEnabled(True)
        self.close()
        
    def _ok(self):
        self.inputChans = [self.biasInChannel.value() , self.dcInChannel.value() , self.acInChannel.value() , self.noiseInChannel.value()]
        self.outputChans = [self.biasOutChannel.value(),  self.blinkOutChannel.value(), self.voltsOutChannel.value(), self.currentOutChannel.value()]
        dif_in = [self.inputChans[i] - self.inputChans[j] for i in range(0,4) for j in range(i+1,4) ]
        dif_out = [self.outputChans[i] - self.outputChans[j] for i in range(0,4) for j in range(i+1,4) ]
        if any(int(x) == 0 for x in dif_out):
            print self.outputChans
            self.warning.setText("Output channels must be \n distinct.")
            self.warning.setStyleSheet("QLabel#warning {color: rgb(255,0, 0);}")
        elif any(int(x) == 0 for x in dif_in):
            self.warning.setText("Input channels must be \n distinct.")
            self.warning.setStyleSheet("QLabel#warning {color: rgb(255,0, 0);}")

        else:
            self.window.dacBiasOutChan = self.outputChans[0]
            self.window.dacBlinkOutChan = self.outputChans[1]
            self.window.voltsOutChan = self.outputChans[2]
            self.window.currentOutChan = self.outputChans[3]

            self.window.dacBiasInChan = self.inputChans[0]
            self.window.dacDCInChan = self.inputChans[1]
            self.window.dacACInChan = self.inputChans[2]
            self.window.dacNoiseInChan = self.inputChans[3]

            self.window.blinkDevice = self.comboBox_blinkDevice.currentText()
            
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

#GUI Window for reminding user to turn Toellner output on
class toellnerReminder(QtGui.QDialog, Ui_toeReminder):
    def __init__(self, parent = None):
        super(toellnerReminder, self).__init__(parent)
        self.window = parent
        self.setupUi(self)
        
        self.yes.clicked.connect(self.continueSweep)
        self.no.clicked.connect(self.backUp)
        
    def continueSweep(self):
        self.accept()
        
    def backUp(self):
        self.reject()
        
    def closeEvent(self, e):
        self.reject()

        

        
        

#GUI Window for finalizing sweep parameters, inherits the list of sweep parameters from the MainWindow checkSweep function
class DialogBox(QtGui.QDialog, Ui_DialogBox):
    def __init__(self, sweepParameters, magPower, parent = None):
        super(DialogBox, self).__init__(parent)
        self.window = parent
        self.setupUi(self)
        self.sweepParameters = sweepParameters
        self.magnetPower = magPower
        
        self.fieldMinValue.setText(str(self.sweepParameters[0]))
        self.fieldMinValue.setStyleSheet("QLabel#fieldMinValue {color: rgb(168,168,168);}")
        self.fieldMaxValue.setText(str(self.sweepParameters[1]))
        self.fieldMaxValue.setStyleSheet("QLabel#fieldMaxValue {color: rgb(168,168,168);}")
        self.fieldIncValue.setText(str(self.sweepParameters[2]))
        self.fieldIncValue.setStyleSheet("QLabel#fieldIncValue {color: rgb(168,168,168);}")
        self.fieldSpeedValue.setText(str(self.sweepParameters[3]))
        self.fieldSpeedValue.setStyleSheet("QLabel#fieldSpeedValue {color: rgb(168,168,168);}")

        self.biasMinValue.setText(str(self.sweepParameters[4]))
        self.biasMinValue.setStyleSheet("QLabel#biasMinValue {color: rgb(168,168,168);}")
        self.biasMaxValue.setText(str(self.sweepParameters[5]))
        self.biasMaxValue.setStyleSheet("QLabel#biasMaxValue {color: rgb(168,168,168);}")
        self.biasIncValue.setText(str(self.sweepParameters[6]))
        self.biasIncValue.setStyleSheet("QLabel#biasIncValue {color: rgb(168,168,168);}")
        self.biasSpeedValue.setText(str(self.sweepParameters[7]))
        self.biasSpeedValue.setStyleSheet("QLabel#biasSpeedValue {color: rgb(168,168,168);}")
        
        if self.magnetPower == 'IPS 120-10':
            self.magnetPowerSupply.setText('Oxford IPS 120-10 Magnet Power Supply')
            self.magnetPowerSupply.setStyleSheet("QLabel#magnetPowerSupply {color: rgb(168,168,168);}")
        elif self.magnetPower == 'Toellner 8851':
            self.magnetPowerSupply.setText('Toellner 8851 Power Supply')
            self.magnetPowerSupply.setStyleSheet("QLabel#magnetPowerSupply {color: rgb(168,168,168);}")
        if self.sweepParameters[9] == 0:
            self.sweepModeSetting.setText('Max to Min')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(168,168,168);}")
        elif self.sweepParameters[9] ==1:
            self.sweepModeSetting.setText('Min to Max')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(168,168,168);}")
        elif self.sweepParameters[9] ==2:
            self.sweepModeSetting.setText('Zero to Max/Min')
            self.sweepModeSetting.setStyleSheet("QLabel#sweepModeSetting {color: rgb(168,168,168);}")

        if self.sweepParameters[10] == 0:
            self.blinkOrNot.setText('Enabled')
            self.blinkOrNot.setStyleSheet("QLabel#blinkOrNot {color: rgb(168,168,168);}")
        elif self.sweepParameters[10] == 1:
            self.blinkOrNot.setText('Disabled')
            self.blinkOrNot.setStyleSheet("QLabel#blinkOrNot {color: rgb(168,168,168);}")
        if self.sweepParameters[8] != "infinite":
            self.sweepTime.setText(self.sweepParameters[8])
            self.sweepTime.setStyleSheet("QLabel#sweepTime {color: rgb(168,168,168);}")
        else:
            self.sweepTime.setTextFormat(1)
            self.sweepTime.setText('<html><head/><body><p><span style=" font-size:10pt; color:#ffffff;">&#8734;</span></p></body></html>')

        self.startSweepReally.clicked.connect(self.testSweep)
        self.beIndecisive.clicked.connect(self.exitDialog)

    #If accepted, runs the sweep
    def testSweep(self):
        self.accept()
    def exitDialog(self):
        #self.window.startSweep.setEnabled(True)
        self.reject()
    def closeEvent(self, e):
        self.window.startSweep.setEnabled(True)
        self.window.abortSweep.setEnabled(False)

class preliminarySweep(QtGui.QDialog, Ui_prelimSweep):
    def __init__(self, reactor, dv, dac, dacChannels, parent = None):
        super(preliminarySweep, self).__init__(parent)
        self.window = parent
        self.reactor = reactor
        self.setupUi(self)
        
        self.setupPlot()
        self.dv = dv
        self.dac = dac
        
        self.dacOutputs = dacChannels[0]
        self.dacInputs = dacChannels[1]

        self.critCurr.setReadOnly(True)
        self.parRes.setReadOnly(True)
        self.newSweep.setEnabled(False)

        self.startSweep.clicked.connect(lambda: self.sweep(self.reactor))
        self.newSweep.clicked.connect(self.refreshSweep)
        self.closeWin.clicked.connect(self._close)



    def refreshSweep(self):
        self.startSweep.setEnabled(True)
        self.newSweep.setEnabled(False)

    def setupPlot(self):
        self.sweepPlot = pg.PlotWidget(parent = self.plotSweep)
        self.sweepPlot.setGeometry(QtCore.QRect(0, 0, 435, 290))
        self.sweepPlot.setLabel('left', 'DC Feedback Voltage', units = 'V')
        self.sweepPlot.setLabel('bottom', 'Bias Voltage', units = 'V')
        self.sweepPlot.showAxis('right', show = True)
        self.sweepPlot.showAxis('top', show = True)
        self.sweepPlot.setXRange(0,1)
        self.sweepPlot.setYRange(0,2)
        self.sweepPlot.enableAutoRange(enable = True)
        
    def plotSweepData(self, data):
        self.data = data
        xVals = [x[1] for x in self.data]
        yVals = [x[2] for x in self.data]
        
        self.sweepPlot.plot(x = xVals, y = yVals, pen = 0.5)
        
        absX = np.absolute(xVals)
        zeroVolts = np.amin(absX)
        zeroIndex = np.argmin(absX)
        bigHalf = np.amax([len(xVals) - zeroIndex -1, zeroIndex])

        
        
        chi = 0
        if bigHalf>zeroIndex:
            j = zeroIndex + 5
            while chi / (len(xVals) - 2) < 1e-5 and j<len(xVals):
                p, chi, _, _, _ = np.polyfit(xVals[zeroIndex:j], yVals[zeroIndex:j], 1, full = True)
                j += 1
            j = int(0.9 * j)
            p, chi, _, _, _ = np.polyfit(xVals[zeroIndex:j], yVals[zeroIndex:j], 1, full = True)

                
        else:
            j = zeroIndex - 5
            while chi / (len(xVals) - 2) < 1e-5 and j >= 0:
                p, chi, _, _, _ = np.polyfit(xVals[j:zeroIndex], yVals[j:zeroIndex], 1, full = True)
                j -= 1
            j = int(0.9 * j)
            p, chi, _, _, _ = np.polyfit(xVals[j:zeroIndex], yVals[j:zeroIndex], 1, full = True)

        biasRes = float(self.biasRes.value())*1000
        shuntRes = float(self.shuntRes.value())
        ssaaRes = float(self.ssaaRes.value())*1000
        winding = float(self.ssaaWinding.value())

        alpha = shuntRes / (shuntRes + biasRes)

        print len(xVals)
        print j, zeroIndex
        deltaV_DAC = np.absolute(xVals[j] - xVals[zeroIndex])

        deltaV_F = np.absolute(yVals[j] - yVals[zeroIndex])

        if deltaV_F == 0:
            pass
        else:
            ratio = np.absolute(deltaV_DAC / deltaV_F)
            r = np.round(alpha * (winding * ssaaRes * ratio - biasRes), decimals = 1)
            self.parRes.setText(str(r))

        
    def sleep(self, secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
    def _close(self):
        self.window.prelim.setEnabled(True)
        self.close()
    def closeEvent(self, e):
        self.window.prelim.setEnabled(True)
        self.close()

    @inlineCallbacks
    def sweep(self, c):
        try:
            self.startSweep.setEnabled(False)
            self.sweepPlot.clear()
            
            #Sets sweep parameters
            biasMin = float(self.biasStart.value())
            biasMax = float(self.biasEnd.value())
            biasRange = abs(biasMax - biasMin)
            
            biasPoints = int(self.sweepPoints.value())
            delay = int(self.delay.value() * 1000)
            
            #Sets DAC Channels
            DAC_out = self.dacOutputs[0] - 1
            DAC_blink = self.dacOutputs[1] - 1
            
            DAC_in_ref = self.dacInputs[0] - 1
            DAC_in_sig = self.dacInputs[1] - 1
            DAC_in_noise = self.dacInputs[3] - 1
            
            yield self.dv.new("nSOT Preliminary Sweep", ['Bias Voltage Index','Bias Voltage'],['DC SSAA Output','Noise'])
            print 'DataVault setup complete'
            
            yield self.dac.set_voltage(DAC_out, 0)
            try:
                yield self.window.blinkFunc()
            except Exception as inst:
                print inst
                print 'Blinks the problem yo'

            if biasMin != 0:
                yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [0], [biasMin], int(biasMin * 1000), 1000)
                yield self.sleep(1)
            #Do sweep
            print 'Ramping up nSOT bias voltage from ' + str(biasMin) + ' to ' + str(biasMax) + '.'
            dac_read = yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [biasMin], [biasMax], biasPoints, delay)

            formatted_data = []
            for j in range(0, biasPoints):
                    formatted_data.append((j, dac_read[0][j], dac_read[1][j], dac_read[2][j]))
            yield self.dv.add(formatted_data)

            self.plotSweepData(formatted_data)

            #Return to zero voltage gently
            yield self.dac.buffer_ramp([DAC_out], [DAC_in_ref, DAC_in_sig, DAC_in_noise], [biasMax], [0], int(biasMax * 1000), 1000)
            yield self.sleep(0.25)
            yield self.dac.set_voltage(DAC_out, 0)

            self.newSweep.setEnabled(True)
        except Exception as inst:
            print inst

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))