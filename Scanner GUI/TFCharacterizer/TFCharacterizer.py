import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import pyqtgraph as pg
import numpy as np
from scipy.optimize import curve_fit


path = sys.path[0] + r"\TFCharacterizer"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\TFCharacterizer.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_advancedSettings, QtBaseClass = uic.loadUiType(path + r"\advancedSettings.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    workingPointSelected = QtCore.pyqtSignal(float, float, int, float)

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.startFreq = 30000
        self.stopFreq = 34000
        self.freqStep = 50
        self.points = 80
        
        self.selectFreq = 32000
        
        self.exAmp = 0.01
        self.timeConst = 0.005
        self.sensitvity = 2
        
        self.input = 1
        self.output = 1
        self.sweep_param = 'oscillator 1'
        self.demod = 1 #demodulator being used

        #initialize advanced lock in settings
        self.bandcontrol = 0
        self.log = False
        self.overlap = False
        self.settle_time = 0.005
        self.settle_acc = 0.001
        self.average_TC = 15 
        self.average_sample = 0
        self.bandwidth = 1000
        self.loopcount = 1
        
        self.freq = None
        self.R = None
        self.phi = None

        self.showFit = True
        
        self.fileName = 'unnnamed'
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()        

        #Connect all the lineEdits
        self.lineEdit_MinFreq.editingFinished.connect(self.updateStartFreq)
        self.lineEdit_MaxFreq.editingFinished.connect(self.updateStopFreq)
        self.lineEdit_freqSelect.editingFinished.connect(self.updateSelectFreq)
        self.lineEdit_deltaF.editingFinished.connect(self.updateStepSize)
        self.lineEdit_timeConst.editingFinished.connect(self.updateTC)
        self.lineEdit_Amplitude.editingFinished.connect(self.updateOutputAmplitude)
        self.lineEdit_sensitivity.editingFinished.connect(self.updateSensitivity)
        self.lineEdit_fileName.editingFinished.connect(self.updateFileName)
        
        #Connect radio buttons
        self.radio_in1.toggled.connect(self.toggleInChannel)
        self.radio_in2.toggled.connect(self.toggleInChannel)
        self.radio_out1.toggled.connect(self.toggleOutChannel)
        self.radio_out2.toggled.connect(self.toggleOutChannel)
        
        #Connect all push buttons
        self.push_fitData.clicked.connect(self.fitCurrData)
        self.push_showFit.clicked.connect(self.toggleFitView)
        self.push_Start.clicked.connect(self.startSweep)
        self.push_Stop.clicked.connect(self.stopSweep)
        self.push_WorkingPoint.clicked.connect(self.selectWorkingPoint)
        self.push_SuggestWorkingPoint.clicked.connect(self.selectAutoWorkingPoint)
        
        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        self.push_advancedSettings.clicked.connect(self.showAdvancedSettings)
        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None
        self.hf = None
        
        #Lock interface until appropriate LabRAD servers are connected
        self.lockInterface()
        
    def moveDefault(self):    
        self.move(550,10)
        
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.dv = dict['dv']
            self.hf = dict['hf2li']
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  
        if not self.cxn: 
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.dv:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.hf:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
            try:
                self.reinitSweep()
            except Exception as inst:
                print inst
            try:
                self.updateOutputAmplitude()
            except Exception as inst:
                print inst
            try:
                self.updateSensitivity()
            except Exception as inst:
                print inst
            try:
                self.updateTC()
            except Exception as inst:
                print inst
            self.unlockInterface()
        
    def disconnectLabRAD(self):
        self.dv = None
        self.cxn = None
        self.hf = None
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.lockInterface()
            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
    def showAdvancedSettings(self):
        values = [self.bandcontrol, self.log, self.overlap, self.settle_time, self.settle_acc, self.average_TC, self.average_sample, self.bandwidth, self.loopcount]
        advSet = advancedSettings(self.reactor, values, parent = self)
        if advSet.exec_():
            values = advSet.getValues()
            self.bandcontrol = values[0]
            self.log = values[1]
            self.overlap = values[2]
            self.settle_time = values[3]
            self.settle_acc = values[4]
            self.average_TC = values[5]
            self.average_sample = values[6]
            self.bandwidth = values[7]
            self.loopcount= values[8]
            self.reinitSweep()
        
    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        self.ampPlot = pg.PlotWidget(parent = self)
        self.ampPlot.setGeometry(10,190,631,451)
        self.ampPlot.setLabel('left', 'Volts', units = 'V')
        self.ampPlot.setLabel('bottom', 'Frequency', units = 'Hz')
        self.ampPlot.showAxis('right', show = True)
        self.ampPlot.showAxis('top', show = True)
        self.ampPlot.setTitle('Amplitude vs. Frequency')
        self.ampPlot.getPlotItem().enableAutoRange('x',False)
        self.ampPlot.setXRange(30000,34000)
        self.ampPlot.getPlotItem().getViewBox().setMouseMode(self.ampPlot.getPlotItem().getViewBox().RectMode)
        self.ampPlot.sigRangeChanged.connect(self.ampRangeChanged)
        
        self.minFreqLine = pg.InfiniteLine(pos = 30000, angle = 90, movable = True)
        self.minFreqLine.sigPositionChanged.connect(self.ampMinChanged)
        self.minFreqLine.sigPositionChangeFinished.connect(self.reinitSweep)
        self.maxFreqLine = pg.InfiniteLine(pos = 34000, angle = 90, movable = True)
        self.maxFreqLine.sigPositionChanged.connect(self.ampMaxChanged)
        self.maxFreqLine.sigPositionChangeFinished.connect(self.reinitSweep)
        self.freqSelectLine = pg.InfiniteLine(pos = 32000, angle = 90, movable = True)
        self.freqSelectLine.sigPositionChanged.connect(self.ampSelectChanged)
        self.freqSelectLine.setPen((255,255,255))
        self.freqSelectLine.setHoverPen((0,0,255))
        
        self.ampPlot.getPlotItem().addItem(self.minFreqLine)
        self.ampPlot.getPlotItem().addItem(self.maxFreqLine)
        self.ampPlot.getPlotItem().addItem(self.freqSelectLine)
        
        self.phasePlot = pg.PlotWidget(parent = self)
        self.phasePlot.setGeometry(650,190,631,451)
        self.phasePlot.setLabel('left', 'Phase', units = 'Degrees')
        self.phasePlot.setLabel('bottom', 'Frequency', units = 'Hz')
        self.phasePlot.showAxis('right', show = True)
        self.phasePlot.showAxis('top', show = True)
        self.phasePlot.setTitle('Phase vs. Frequency')
        self.phasePlot.getPlotItem().enableAutoRange('x',False)
        self.phasePlot.setXRange(30000,34000)
        self.phasePlot.getPlotItem().getViewBox().setMouseMode(self.phasePlot.getPlotItem().getViewBox().RectMode)
        self.phasePlot.sigRangeChanged.connect(self.phaseRangeChanged)
        
        self.minFreqLine2 = pg.InfiniteLine(pos = 30000, angle = 90, movable = True)
        self.minFreqLine2.sigPositionChanged.connect(self.phaseMinChanged)
        self.minFreqLine2.sigPositionChangeFinished.connect(self.reinitSweep)
        self.maxFreqLine2 = pg.InfiniteLine(pos = 34000, angle = 90, movable = True)
        self.maxFreqLine2.sigPositionChanged.connect(self.phaseMaxChanged)
        self.maxFreqLine2.sigPositionChangeFinished.connect(self.reinitSweep)
        self.freqSelectLine2 = pg.InfiniteLine(pos = 32000, angle = 90, movable = True)
        self.freqSelectLine2.sigPositionChanged.connect(self.phaseSelectChanged)
        self.freqSelectLine2.setPen((255,255,255))
        self.freqSelectLine2.setHoverPen((0,0,255))
            
        self.phasePlot.getPlotItem().addItem(self.minFreqLine2)
        self.phasePlot.getPlotItem().addItem(self.maxFreqLine2)
        self.phasePlot.getPlotItem().addItem(self.freqSelectLine2)
          
#----------------------------------------------------------------------------------------------#         
    """ The following section connects all signals."""
          
    def ampMinChanged(self,item):
        self.minFreqLine2.setPos(item.pos())
        self.startFreq = item.pos().x()
        self.lineEdit_MinFreq.setText(formatNum(self.startFreq, 4))
        
    def ampMaxChanged(self,item):
        self.maxFreqLine2.setPos(item.pos())
        self.stopFreq = item.pos().x()
        self.lineEdit_MaxFreq.setText(formatNum(self.stopFreq, 4))
        
    def ampSelectChanged(self,item):
        self.freqSelectLine2.setPos(item.pos())
        self.selectFreq = item.pos().x()
        self.lineEdit_freqSelect.setText(formatNum(self.selectFreq, 4))
        
    def phaseMinChanged(self,item):
        self.minFreqLine.setPos(item.pos())
        self.startFreq = item.pos().x()
        self.lineEdit_MinFreq.setText(formatNum(self.startFreq, 4))
        
    def phaseMaxChanged(self,item):
        self.maxFreqLine.setPos(item.pos())
        self.stopFreq = item.pos().x()
        self.lineEdit_MaxFreq.setText(formatNum(self.stopFreq, 4))
        
    def phaseSelectChanged(self,item):
        self.freqSelectLine.setPos(item.pos())
        self.selectFreq = item.pos().x()
        self.lineEdit_freqSelect.setText(formatNum(self.selectFreq, 4))
        
    def ampRangeChanged(self,item):
        range = item.getPlotItem().getViewBox().viewRange()
        self.phasePlot.setXRange(range[0][0], range[0][1], padding = 0, update = False)
        #self.phasePlot.setYRange(range[1][0], range[1][1], padding = 0, update = False)
        
    def phaseRangeChanged(self,item):
        range = item.getPlotItem().getViewBox().viewRange()
        self.ampPlot.setXRange(range[0][0], range[0][1], padding = 0, update = False)
        #self.ampPlot.setYRange(range[1][0], range[1][1], padding = 0, update = False)
        
#----------------------------------------------------------------------------------------------#         
    """ The following section connects actions related to buttons on the TF window."""
    
    def updateFileName(self):
        self.fileName = str(self.lineEdit_fileName.text())
        
    def updateStartFreq(self):
        new_startFreq = str(self.lineEdit_MinFreq.text())
        val = readNum(new_startFreq)
        if isinstance(val,float):
            self.startFreq = val
            self.minFreqLine.setPos(self.startFreq)
            self.minFreqLine2.setPos(self.startFreq)
            self.points = int(np.abs(self.startFreq-self.stopFreq)/self.freqStep)
            self.reinitSweep()
        self.lineEdit_MinFreq.setText(formatNum(self.startFreq, 4))
    
    def updateStopFreq(self):
        new_stopFreq = str(self.lineEdit_MaxFreq.text())
        val = readNum(new_stopFreq)
        if isinstance(val,float):
            self.stopFreq = val
            self.maxFreqLine.setPos(self.stopFreq)
            self.maxFreqLine2.setPos(self.stopFreq)
            self.points = int(np.abs(self.startFreq-self.stopFreq)/self.freqStep)
            self.reinitSweep()
        self.lineEdit_MaxFreq.setText(formatNum(self.stopFreq, 4))
    
    def updateSelectFreq(self):
        new_selectFreq = str(self.lineEdit_freqSelect.text())
        val = readNum(new_selectFreq)
        if isinstance(val,float):
            self.selectFreq = val
            self.freqSelectLine.setPos(self.selectFreq)
            self.freqSelectLine2.setPos(self.selectFreq)
            self.reinitSweep()
        self.lineEdit_freqSelect.setText(formatNum(self.selectFreq, 4))
        
    def updateStepSize(self):
        new_freqStep = str(self.lineEdit_deltaF.text())
        val = readNum(new_freqStep)
        if isinstance(val,float):
            self.freqStep = val
            self.points = int(np.abs(self.startFreq-self.stopFreq)/self.freqStep)
            self.reinitSweep()
        self.lineEdit_deltaF.setText(formatNum(self.freqStep))
                
    @inlineCallbacks
    def updateSensitivity(self, c = None):
        try:
            new_sens = str(self.lineEdit_sensitivity.text())
            val = readNum(new_sens)
            if isinstance(val,float):
                yield self.hf.set_range(self.input, val)
                range = yield self.hf.get_range(self.input)
                self.sensitvity = range
            self.lineEdit_sensitivity.setText(formatNum(self.sensitvity))
        except Exception as inst:
            print inst
            
    @inlineCallbacks
    def updateOutputAmplitude(self, c = None):
        try:
            new_Amp = str(self.lineEdit_Amplitude.text())
            val = readNum(new_Amp)
            if isinstance(val,float):
                yield self.hf.set_output_range(self.output,val)
                range = yield self.hf.get_output_range(self.output)
                yield self.hf.set_output_amplitude(self.output,val/range)
                self.exAmp = val
            self.lineEdit_Amplitude.setText(formatNum(self.exAmp))
        except Exception as inst:
            print inst
        
    @inlineCallbacks
    def updateTC(self, c = None):
        new_Tc = str(self.lineEdit_timeConst.text())
        val = readNum(new_Tc)
        if isinstance(val, float):
            yield self.hf.set_demod_time_constant(1,val)
            self.timeConst = yield self.hf.get_demod_time_constant(1)
        self.lineEdit_timeConst.setText(formatNum(self.timeConst))
    
    def toggleInChannel(self):
        if self.radio_in1.isChecked():
            self.input = 1
            self.output = 1
            self.sweep_param = 'oscillator 1'
            self.demod = 1
            self.radio_out1.setChecked(True)
            self.reinitSweep()
        elif self.radio_in2.isChecked():
            self.input = 2
            self.output = 2
            self.sweep_param = 'oscillator 2'
            self.demod = 4
            self.radio_out2.setChecked(True)
            self.reinitSweep()
            
    def toggleOutChannel(self):
        if self.radio_out1.isChecked():
            self.output = 1
            self.input = 1
            self.sweep_param = 'oscillator 1'
            self.demod = 1
            self.radio_in1.setChecked(True)
            self.reinitSweep()
        elif self.radio_out2.isChecked():
            self.output = 2
            self.input = 2
            self.sweep_param = 'oscillator 2'
            self.demod = 4
            self.radio_in2.setChecked(True)
            self.reinitSweep()
            
    def selectWorkingPoint(self):
        #linear extrapolation between two nearest data points to the set frequency 
        freq = self.freq[~np.isnan(self.freq)]
        index = np.argmin(np.abs(freq - self.selectFreq))
        
        if self.selectFreq - freq[index] > 0:
            f1 = freq[index]
            f2 = freq[index+1]
            p1 = self.phi_unwrapped[index]
            p2 = self.phi_unwrapped[index+1]
            m = (p1 - p2)/(f1-f2)
            c = -m*f1 + p1
            phase = m*self.selectFreq + c
        elif self.selectFreq - freq[index] <0:
            f1 = self.freq[index-1]
            f2 = self.freq[index]
            p1 = self.phi_unwrapped[index-1]
            p2 = self.phi_unwrapped[index]
            m = (p1 - p2)/(f1-f2)
            c = -m*f1 + p1
            phase = m*self.selectFreq + c
        else:
            phase = self.phi[index]
            
        self.workingPointSelected.emit(self.selectFreq, phase, self.output, self.exAmp)

    def selectAutoWorkingPoint(self):

        phase = phaseFunc(self.ampFitParams[0], *self.phaseFitParams)

        self.workingPointSelected.emit(self.ampFitParams[0], phase, self.output, self.exAmp)

    @inlineCallbacks
    def startSweep(self, c = None):    
        try:
            doneSweeping = False
            yield self.hf.set_output(self.output,True)
            yield self.hf.set_demod(self.demod,True)
            yield self.hf.start_sweep()

            self.push_fitData.setEnabled(False)
            self.push_advancedSettings.setEnabled(False)

            self.minFreqLine.setMovable(False)
            self.maxFreqLine.setMovable(False)
            self.minFreqLine2.setMovable(False)
            self.maxFreqLine2.setMovable(False)

            while not doneSweeping:
                doneSweeping = yield self.hf.sweep_complete()
                self.updateRemainingTime()
                try:
                    data = yield self.hf.read_latest_values()
                    self.plotData(data)
                except Exception as inst:
                    pass
            
            self.updateRemainingTime()
            
            self.push_fitData.setEnabled(True)
            self.push_advancedSettings.setEnabled(True)

            self.minFreqLine.setMovable(True)
            self.maxFreqLine.setMovable(True)
            self.minFreqLine2.setMovable(True)
            self.maxFreqLine2.setMovable(True)
            
            yield self.hf.set_output(self.output,False)
            yield self.hf.set_demod(self.demod,False)
            yield self.dv.new("Tuning Fork Voltage vs. Frequency " + self.fileName,['Frequency'],['Amplitude R', 'Phase Phi'])
            
            formated_data = []
            for j in range(0, self.points):
                formated_data.append((data[1][j],data[2][j],data[3][j]))
        
            yield self.dv.add(formated_data)

            yield self.hf.clear_sweep()
            
        except Exception as inst:
            print inst
    
    @inlineCallbacks
    def updateRemainingTime(self,c = None):
        try:
            time  = yield self.hf.sweep_time_remaining()
            #print time
            self.lineEdit_timeRemaining.setText(formatNum(time))
        except Exception as inst:
            print inst
    
    @inlineCallbacks
    def stopSweep(self, c):
        try:
            yield self.hf.stop_sweep()
            yield self.hf.clear_sweep()
        except Exception as inst:
            print inst
   
    @inlineCallbacks
    def reinitSweep(self,c = None):
        #Uses demodulater 1, might need to change depending on input/output selected
        try:
            yield self.hf.create_sweep_object(self.startFreq, self.stopFreq, self.points, self.sweep_param, self.demod, self.log, self.bandcontrol, self.bandwidth, self.overlap, self.loopcount, self.settle_time, self.settle_acc, self.average_TC, self.average_sample)
        except Exception as inst:
            print inst
            
    def plotData(self, data):
        self.freq = data[1]
        self.R = data[2]
        self.phi_unwrapped = data[3]
        self.phi = 180*np.arctan2(np.tan(np.pi*self.phi_unwrapped/180),1)/np.pi

        try:
            self.ampPlot.removeItem(self.prevAmpPlot)
            self.phasePlot.removeItem(self.prevPhasePlot)
        except Exception as inst:
            pass

        self.prevAmpPlot = self.ampPlot.plot(self.freq,self.R)
        self.prevPhasePlot = self.phasePlot.plot(self.freq,self.phi)
        
    def fitCurrData(self):
        #ideas: scale voltage data up to avoid small values, makes it easier to fit. Then rescale back down. 
        #avoiding small numbers as much as possible is good seems to work fine right now, so not necessary. 
        #But if data fitting is bad in the future this can be a possible fix. 

        '''
        self.startFreq = 32000
        self.stopFreq = 33500
        self.points = 10000
        
        #self.startFreq = 30000
        #self.stopFreq = 34000
        #self.points = 10000
        
        self.freq = np.linspace(self.startFreq, self.stopFreq, self.points)
        #params = [27100, 8100, 2.9e-15, 1.2e-12]
        params = [32838.1, 61670, 0.00670979, 3.7e-5]
        param = [32838.1, 61670, 0.00670979, -3]
        #params = [32838.1, 5000, 0.0067, 3.7e-5]
        #param = [32838.1, 5000, 0.0067]
        self.R = ampFunc(self.freq, *params) + 5e-6*(np.random.rand(self.points)-0.5)
        self.phi = phaseFunc(self.freq, *param) + np.random.rand(self.points)-0.5

        #removes previous data plot and replots it. Doesn't seem necessary
        try:
            self.ampPlot.removeItem(self.prevAmpPlot)
            self.phasePlot.removeItem(self.prevPhasePlot)
        except Exception as inst:
            pass
            
        self.prevAmpPlot = self.ampPlot.plot(self.freq,self.R)
        self.prevPhasePlot = self.phasePlot.plot(self.freq,self.phi)
        '''

        max = np.amax(self.R)
        f0_guess = self.freq[np.argmax(self.R)]
        
        self.ampFitParams, pcov = curve_fit(ampFunc, self.freq, self.R, p0 = [f0_guess, 5000, 0.1, max])
        perr = np.sqrt(np.diag(pcov))

        if self.showFit:
            try: 
                self.ampPlot.removeItem(self.prevAmpFit)
            except:
                pass
            self.prevAmpFit = self.ampPlot.plot(self.freq,ampFunc(self.freq, *self.ampFitParams))

        self.lineEdit_peakF.setText(formatNum(self.ampFitParams[0]))
        self.lineEdit_peakFSig.setText(formatNum(perr[0]))
        self.lineEdit_QFactor.setText(formatNum(self.ampFitParams[1]))
        
        avg = 0
        for i in range(0,10):
            avg = avg + self.phi[i]
        avg = avg/10
        self.phaseFitParams, pcov = curve_fit(phaseFunc, self.freq, self.phi, p0 = [self.ampFitParams[0], self.ampFitParams[1], self.ampFitParams[2], avg-90])
        perr = np.sqrt(np.diag(pcov))

        if self.showFit:
            try:
                self.phasePlot.removeItem(self.prevPhaseFit)
            except:
                pass
            self.prevPhaseFit = self.phasePlot.plot(self.freq,phaseFunc(self.freq, *self.phaseFitParams))

        self.lineEdit_PhasePeakF.setText(formatNum(self.phaseFitParams[0]))
        self.lineEdit_PhasePeakFSig.setText(formatNum(perr[0]))
        self.lineEdit_PhaseQFactor.setText(formatNum(self.phaseFitParams[1]))
        #Maybe iterate fits/starting parameters? 
        
    def toggleFitView(self):
        if self.showFit:
            #hide fit
            try: 
                self.ampPlot.removeItem(self.prevAmpFit)
            except:
                pass
            try:
                self.phasePlot.removeItem(self.prevPhaseFit)
            except:
                pass

            self.push_showFit.setText('Show Fit')
            self.showFit = False
        else:
            #show fit
            try:
                self.prevAmpFit = self.ampPlot.plot(self.freq,ampFunc(self.freq, *self.ampFitParams))
                self.prevPhaseFit = self.phasePlot.plot(self.freq,phaseFunc(self.freq, *self.phaseFitParams))
            except:
                pass

            self.push_showFit.setText('Hide Fit')
            self.showFit = True
#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""
           
    def lockInterface(self):
        self.push_Start.setEnabled(False)
        self.push_Stop.setEnabled(False)
        self.push_fitData.setEnabled(False)
        self.push_WorkingPoint.setEnabled(False)
        self.push_SuggestWorkingPoint.setEnabled(False)
        self.push_advancedSettings.setEnabled(False)
        self.push_showFit.setEnabled(False)
        
        self.lineEdit_MinFreq.setDisabled(True)
        self.lineEdit_MaxFreq.setDisabled(True)
        self.lineEdit_deltaF.setDisabled(True)
        self.lineEdit_Amplitude.setDisabled(True)
        self.lineEdit_timeConst.setDisabled(True)
        self.lineEdit_sensitivity.setDisabled(True)
        self.lineEdit_freqSelect.setDisabled(True)
        
        self.minFreqLine.setMovable(False)
        self.maxFreqLine.setMovable(False)
        self.minFreqLine2.setMovable(False)
        self.maxFreqLine2.setMovable(False)
        self.freqSelectLine.setMovable(False)
        self.freqSelectLine2.setMovable(False)
        
        self.radio_in1.setEnabled(False)
        self.radio_in2.setEnabled(False)
        self.radio_out1.setEnabled(False)
        self.radio_out2.setEnabled(False)

    def unlockInterface(self):
        self.push_Start.setEnabled(True)
        self.push_Stop.setEnabled(True)
        self.push_fitData.setEnabled(True)
        self.push_WorkingPoint.setEnabled(True)
        self.push_SuggestWorkingPoint.setEnabled(True)
        self.push_advancedSettings.setEnabled(True)
        self.push_showFit.setEnabled(True)

        self.lineEdit_MinFreq.setDisabled(False)
        self.lineEdit_MaxFreq.setDisabled(False)
        self.lineEdit_deltaF.setDisabled(False)
        self.lineEdit_Amplitude.setDisabled(False)
        self.lineEdit_timeConst.setDisabled(False)
        self.lineEdit_sensitivity.setDisabled(False)
        self.lineEdit_freqSelect.setDisabled(False)
        
        self.minFreqLine.setMovable(True)
        self.maxFreqLine.setMovable(True)
        self.minFreqLine2.setMovable(True)
        self.maxFreqLine2.setMovable(True)
        self.freqSelectLine.setMovable(True)
        self.freqSelectLine2.setMovable(True)

        self.radio_in1.setEnabled(True)
        self.radio_in2.setEnabled(True)
        self.radio_out1.setEnabled(True)
        self.radio_out2.setEnabled(True)
    
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
    def closeEvent(self, e):
        if self.hf is not None:
            self.hf.clear_sweep()
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        
class advancedSettings(QtGui.QDialog, Ui_advancedSettings):
    def __init__(self,reactor, values,parent = None):
        super(advancedSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.bandcontrol = values[0]
        self.log = values[1]
        self.overlap = values[2]
        self.settle_time = values[3]
        self.settle_acc = values[4]
        self.average_TC = values[5]
        self.average_sample = values[6]
        self.bandwidth = values[7]
        self.loopcount= values[8]
        
        self.loadCurrValues()
        
        self.pushButton.clicked.connect(self.acceptNewValues)
        
        self.lineEdit_settle_time.editingFinished.connect(self.updateSettleTime)
        self.lineEdit_settle_acc.editingFinished.connect(self.updateSettleAcc)
        self.lineEdit_avg_tc.editingFinished.connect(self.updateAvgTC)
        self.lineEdit_avg_sample.editingFinished.connect(self.updateAvgSample)
        self.lineEdit_bandwidth.editingFinished.connect(self.updateBandwidth)
        self.lineEdit_loopcount.editingFinished.connect(self.updateLoopcount)
        
    def updateSettleTime(self):
        new_settle_time = str(self.lineEdit_settle_time.text())
        val = readNum(new_settle_time)
        if isinstance(val, float):
            self.settle_time = val
        self.lineEdit_settle_time.setText(formatNum(self.settle_time))
        
    def updateSettleAcc(self):
        new_settle_acc = str(self.lineEdit_settle_acc.text())
        val = readNum(new_settle_acc)
        if isinstance(val, float):
            self.settle_acc = val
        self.lineEdit_settle_acc.setText(formatNum(self.settle_acc))
    
    def updateAvgTC(self):
        new_avg_tc = str(self.lineEdit_avg_tc.text())
        try:
            self.average_TC = int(new_avg_tc)
        except:
            pass
        self.lineEdit_avg_tc.setText(str(self.average_TC))
        
    def updateAvgSample(self):
        new_avg_sample = str(self.lineEdit_avg_sample.text())
        try:
            self.average_sample = int(new_avg_sample)
        except:
            pass
        self.lineEdit_avg_sample.setText(str(self.average_sample))
        
    def updateBandwidth(self):
        new_bandwidth = str(self.lineEdit_bandwidth.text())
        val = readNum(new_bandwidth)
        if isinstance(val, float):
            self.bandwidth = val
        self.lineEdit_bandwidth.setText(formatNum(self.bandwidth))
        
    def updateLoopcount(self):
        new_loopcount = str(self.lineEdit_loopcount.text())
        try:
            self.loopcount = int(new_loopcount)
        except:
            pass
        self.lineEdit_loopcount.setText(str(self.loopcount))
    
    def acceptNewValues(self):
        if self.radio_Manual.isChecked():
            self.bandcontrol = 0
        elif self.radio_Fixed.isChecked():
            self.bandcontrol = 1
        else:
            self.bandcontrol = 2
            
        if self.checkBox_log.isChecked():
            self.log = True
        else:
            self.log = False
            
        if self.checkBox_overlap.isChecked():
            self.overlap = True
        else:
            self.overlap = False
            
        self.accept()
        
    def getValues(self):
        return [self.bandcontrol, self.log, self.overlap, self.settle_time, self.settle_acc, self.average_TC, self.average_sample, self.bandwidth, self.loopcount]

    def loadCurrValues(self):
        if self.bandcontrol == 0:
            self.radio_Manual.setChecked(True)
        elif self.bandcontrol == 1:
            self.radio_Fixed.setChecked(True)
        else:   
            self.radio_Auto.setChecked(True)
        
        if self.log:
            self.checkBox_log.setChecked(True)
            
        if self.overlap:
            self.checkBox_overlap.setChecked(True)
        
        self.lineEdit_settle_time.setText(formatNum(self.settle_time))
        self.lineEdit_settle_acc.setText(formatNum(self.settle_acc))
        self.lineEdit_avg_tc.setText(str(self.average_TC))
        self.lineEdit_avg_sample.setText(str(self.average_sample))
        self.lineEdit_bandwidth.setText(formatNum(self.bandwidth))
        self.lineEdit_loopcount.setText(str(self.loopcount))
    
#---------------------------------------------------------------------------------------------------------#         
    """ The following section describes the fitting functions for fitting to resonances."""
    
def ampFunc(f, f0, Q, C, V):
    #C = C0 R w0
    w = 2*np.pi*f
    w0 = 2*np.pi*f0
    return V*np.sqrt((1 + ((w/w0)*C*(1 + (Q*w/w0)**2*(1 - (w0/w)**2)**2) - (Q*w/w0)*(1 - (w0/w)**2))**2)/(1 + (Q*w/w0)**2*(1 - (w0/w)**2)**2)**2)
    
def phaseFunc(f, f0, Q, C, off):
    #C = C0 R w0
    w = 2*np.pi*f
    w0 = 2*np.pi*f0
    return off + 180*np.arctan2(((w/w0)*C*(1 + (Q*w/w0)**2*(1 - (w0/w)**2)**2) - (Q*w/w0)*(1 - (w0/w)**2)),1)/np.pi
    