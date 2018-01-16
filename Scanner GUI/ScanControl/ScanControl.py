import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import twisted
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading
from scipy.signal import detrend

path = sys.path[0] + r"\ScanControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\ScanControlWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData

'''
THINGS TO DO:
Make sure no scan more than maximum area
'''

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.aspectLocked = True
        self.FrameLocked = True
        self.LinearSpeedLocked = False
        self.DataLocked = True
        self.scanCoordinates = False
        self.dataProcessing = 'Raw'
        self.dataPostProcessing = 'Raw'
        
        self.reactor = reactor
        self.setupUi(self)
        
        #initialize scanning area and plotted data information
        #Lower left corner of the square (assuming unrotated)
        self.x = -2.5e-6
        self.y = -2.5e-6
        #Center of the square
        self.Xc = 0.0
        self.Yc = 0.0
        #Height and width of scanning square
        self.H = 5e-6
        self.W = 5e-6
        #Angle of scanning square
        self.angle = 0.0
        
        #Keep track of plotted data location / angle so that we can also plot it in scan coordinates
        self.currAngle = 0.0
        self.currXc = 0.0
        self.currYc = 0.0
        self.currH = 2e-5
        self.currW = 2e-5
        self.curr_x = -1e-5
        self.curr_y = -1e-5
        self.currLine = 0

        #Number of pixels taken in each direction, and the ratio of pixels to lines
        self.pixels = 256
        self.lines = 256
        self.PixelsAspectRatio = 1.0
        
        #Measurement time information
        self.FrameTime = 32.76
        self.linearSpeed = 78.13e-6
        self.lineTime = 64e-3
        
        '''
        #The following should no longer be necessary anywhere
        self.x_volts_to_meters = 3/ 50e-6 #50 microns corresponds to 3 volts, units of volts per meter. Default room temperature
        self.y_volts_to_meters = 3/ 50e-6
        self.z_volts_to_meters = 3/ 24e-6 #24 microns corresponds to 3 volts, units of volts per meter. Default room temperature
        self.x_meters_max = 50e-6
        self.y_meters_max = 50e-6
        self.z_meters_max = 24e-6
        self.x_volts_max = 3
        self.y_volts_max = 3
        self.z_volts_max = 3
        '''

        #Initial attocube position
        self.Atto_X_Voltage = 0.0
        self.Atto_Y_Voltage = 0.0
        self.Atto_Z_Voltage = 0.0
        
        #Tilt in x and y direction
        self.x_tilt = 0
        self.y_tilt = 0
        
        #Flag to indicate whether or not we're scanning
        self.scanning = False
        
        #Name of the file to be saved
        self.fileName = 'unnamed'

        #Initialize the Scan Mode
        self.scanMode = 'Constant Height'
        self.FeedbackReady = False
        self.ConstantHeightReady = False

        #Channel 0 corresponds to height, and 1 to magnetic field
        self.channel = 0
                
        #Set up rest of UI (must be done after initializing default values)
        self.setupAdditionalUi()
        self.setupScanningArea()
        self.moveDefault()
        
        #Connect the buttons to the appropriate methods
        self.push_FrameLock.clicked.connect(self.toggleFrameLock)
        self.push_SpeedLock.clicked.connect(self.toggleSpeedLock)
        self.push_DataLock.clicked.connect(self.toggleDataLock)
        self.push_autoRange.clicked.connect(self.autoRange)
        self.push_autoLevel.clicked.connect(self.autoLevel)
        self.push_aspectLocked.clicked.connect(self.toggleAspect)
        self.push_scanCoordinates.clicked.connect(self.toggleCoordinates)
        self.push_apply2DFit.clicked.connect(self.apply2DFit)
        self.push_setView.clicked.connect(self.setView)
        self.push_Scan.clicked.connect(self.startScan)
        self.push_Abort.clicked.connect(self.abortScan)
        
        #Connect lineEdits
        self.lineEdit_Xc.editingFinished.connect(self.updateXc)
        self.lineEdit_Yc.editingFinished.connect(self.updateYc)
        self.lineEdit_H.editingFinished.connect(self.updateH)
        self.lineEdit_W.editingFinished.connect(self.updateW)
        self.lineEdit_Angle.editingFinished.connect(self.updateAngle)
        self.lineEdit_Pixels.editingFinished.connect(self.updatePixels)
        self.lineEdit_Lines.editingFinished.connect(self.updateLines)
        self.lineEdit_LineTime.editingFinished.connect(self.updateLineTime)
        self.lineEdit_Linear.editingFinished.connect(self.updateLinearSpeed)
        self.lineEdit_FileName.editingFinished.connect(self.updateFileName)
        self.lineEdit_XTilt.editingFinished.connect(self.updateXTilt)
        self.lineEdit_YTilt.editingFinished.connect(self.updateYTilt)

        self.checkBox.toggled.connect(self.toggleROIVisibility)
                
        self.comboBox_Processing.activated[str].connect(self.selectProcessing)
        self.comboBox_PostProcessing.activated[str].connect(self.selectPostProcessing)
        self.comboBox_scanMode.activated[str].connect(self.updateScanMode)
        self.comboBox_Channel.activated[str].connect(self.selectChannel)
        
        #ROI in trace plot
        self.ROI.sigRegionChanged.connect(self.updateROI)
        #ROI in mini plot
        self.ROI2.sigRegionChanged.connect(self.updateROI2)
        #ROI in retrace plot
        self.ROI3.sigRegionChanged.connect(self.updateROI3)
        
        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize all the labrad connections as false
        self.cxn = False
        self.dv = False
        self.dac = False
        self.hf = False
        self.ips = False
        
        self.lockInterface()
        
    def moveDefault(self):    
        self.move(10,170)
        
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.dac = dict['dac_adc']
            self.dv = dict['dv']
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
            self.unlockInterface()
            
    def disconnectLabRAD(self):
        self.dv = False
        self.cxn = False
        self.ips = False
        self.dac = False
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
    def setupAdditionalUi(self):
        #Initial read only configuration of line edits
        self.lineEdit_Linear.setReadOnly(False)
        self.lineEdit_LineTime.setReadOnly(True)
        
        #Have drop down view be wider than the real view to see all the entries
        self.comboBox_PostProcessing.view().setMinimumWidth(130)

        #Set up main plot
        self.view = pg.PlotItem(title="Trace")
        self.view.setLabel('left',text='Y position',units = 'm')
        self.view.setLabel('right',text='Y position',units = 'm')
        self.view.setLabel('top',text='X position',units = 'm')
        self.view.setLabel('bottom',text='X position',units = 'm')
        self.Plot2D = pg.ImageView(parent = self.centralwidget, view = self.view)
        self.view.invertY(False)
        self.Plot2D.setGeometry(QtCore.QRect(240, 90, 650, 650))
        self.view.setAspectLocked(self.aspectLocked)
        self.Plot2D.ui.roiBtn.hide()
        self.Plot2D.ui.menuBtn.hide()
        self.Plot2D.ui.histogram.hide()
        self.Plot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        self.Plot2D.lower()
        self.PlotArea.close()
        
        #Set up retrace plot
        self.view3 = pg.PlotItem(title="Retrace")
        self.view3.setLabel('left',text='Y position',units = 'm')
        self.view3.setLabel('right',text='Y position',units = 'm')
        self.view3.setLabel('top',text='X position',units = 'm')
        self.view3.setLabel('bottom',text='X position',units = 'm')
        self.Plot2D_Retrace = pg.ImageView(parent = self.centralwidget, view = self.view3)
        self.view3.invertY(False)
        self.Plot2D_Retrace.setGeometry(QtCore.QRect(910, 90, 765, 650))
        self.view3.setAspectLocked(self.aspectLocked)
        self.Plot2D_Retrace.ui.roiBtn.hide()
        self.Plot2D_Retrace.ui.menuBtn.hide()
        self.Plot2D_Retrace.ui.histogram.item.gradient.loadPreset('bipolar')
        self.Plot2D_Retrace.lower()
        self.PlotArea_2.close()
        
        #Set up mini plot for maximum scan range
        self.view2 = pg.PlotItem(title='Full Scan Range')
        self.view2.setLabel('left',text='Y position',units = 'm')
        self.view2.setLabel('right',text='Y position',units = 'm')
        self.view2.setLabel('top',text='X position',units = 'm')
        self.view2.setLabel('bottom',text='X position',units = 'm')
        self.view2.enableAutoRange(self.view2.getViewBox().XYAxes, enable = False)
        self.MiniPlot2D = pg.ImageView(parent = self.centralwidget, view = self.view2)
        self.view2.invertY(False)
        self.MiniPlot2D.setGeometry(QtCore.QRect(5, 715, 228, 228))
        self.MiniPlot2D.ui.roiBtn.hide()
        self.MiniPlot2D.ui.menuBtn.hide()
        self.MiniPlot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        self.MiniPlot2D.ui.histogram.hide()
        self.view2.setMouseEnabled(False,False)
        self.MiniPlot2D.lower()
        self.MiniPlotArea.close()
        
        #15.2 to avoid pixel overlapping with axes, hiding them
        self.view2.setXRange(-15.2e-6,15e-6,0)
        self.view2.setYRange(-15e-6,15.2e-6,0)
        self.view2.hideButtons()
        self.view2.setMenuEnabled(False)
        
        #Determine plot scales
        self.xscale, self.yscale = self.currW / self.lines, self.currH / self.pixels
        
        #Create default dataset for initial plots. lines x pixels x 2 (Z info and B info)
        pxsize = (2, self.lines,self.pixels)
        #data and data_retrace contain only the raw data
        self.data = np.zeros(pxsize)
        self.data_retrace = np.zeros(pxsize)
        #plotData and plotData_retrace contain processed data for graphing
        self.plotData = np.zeros(pxsize)[0]
        self.plotData_retrace = np.zeros(pxsize)[0]
        
        #Load default empty image into all three plots
        self.Plot2D.setImage(self.plotData, autoRange = False, autoLevels = False, pos=[self.curr_x, self.curr_y],scale=[self.xscale, self.yscale])
        self.Plot2D.show()
        self.Plot2D_Retrace.setImage(self.plotData_retrace, autoRange = False, autoLevels = False, pos=[self.curr_x, self.curr_y],scale=[self.xscale, self.yscale])
        self.Plot2D_Retrace.show()
        self.MiniPlot2D.setImage(self.plotData, autoRange = False, autoLevels = False, pos=[self.curr_x, self.curr_y],scale=[self.xscale, self.yscale])
        self.MiniPlot2D.show()
        
        #Connect retrace plot histogram to the other two plots
        self.Plot2D_Retrace.ui.histogram.sigLevelsChanged.connect(self.updateHistogramLevels)
        self.Plot2D_Retrace.ui.histogram.sigLookupTableChanged.connect(self.updateHistogramLookup)
        
        #Connect the trace and retrace plots view ranges
        self.sigRangeChangedEmitted = False
        self.view.sigRangeChanged.connect(self.traceRangeChanged)
        self.view3.sigRangeChanged.connect(self.retraceRangeChanged)
        
        #Set up UI that isn't easily done from Qt Designer
        self.traceLinePlot = pg.PlotWidget(parent = self)
        self.traceLinePlot.setGeometry(240,745,630,200)
        self.traceLinePlot.setLabel('left', 'Z Voltage', units = 'V')
        self.traceLinePlot.setLabel('bottom', 'Position', units = 'm')
        self.traceLinePlot.showAxis('right', show = True)
        self.traceLinePlot.showAxis('top', show = True)
        self.PlotArea_3.hide()

        self.retraceLinePlot = pg.PlotWidget(parent = self)
        self.retraceLinePlot.setGeometry(910,745,630,200)
        self.retraceLinePlot.setLabel('left', 'Z Voltage', units = 'V')
        self.retraceLinePlot.setLabel('bottom', 'Position', units = 'm')
        self.retraceLinePlot.showAxis('right', show = True)
        self.retraceLinePlot.showAxis('top', show = True)
        self.PlotArea_4.hide()

    def setupScanningArea(self):
        #Testing stuff
        self.ROI = pg.RectROI((-2.5e-6,-2.5e-6),(5e-6,5e-6), movable = True)
        self.ROI2 = pg.RectROI((-2.5e-6,-2.5e-6),(5e-6,5e-6), movable = True)
        self.ROI3 = pg.RectROI((-2.5e-6,-2.5e-6),(5e-6,5e-6), movable = True)
        
        self.view.addItem(self.ROI)
        self.view2.addItem(self.ROI2)
        self.view3.addItem(self.ROI3)
        
        #Remove default handles and add desired handles. 
        self.ROI.removeHandle(self.ROI.indexOfHandle(self.ROI.getHandles()[0]))
        self.ROI.addRotateHandle((0,0),(0.5,0.5), name = 'Rotate')
        self.ROI.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
        
        self.ROI2.removeHandle(self.ROI2.indexOfHandle(self.ROI2.getHandles()[0]))
        self.ROI2.addRotateHandle((0,0),(0.5,0.5), name = 'Rotate')
        self.ROI2.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
        
        self.ROI3.removeHandle(self.ROI2.indexOfHandle(self.ROI2.getHandles()[0]))
        self.ROI3.addRotateHandle((0,0),(0.5,0.5), name = 'Rotate')
        self.ROI3.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
        
    def updateHistogramLevels(self, hist):
        mn, mx = hist.getLevels()
        self.MiniPlot2D.ui.histogram.setLevels(mn, mx)
        self.Plot2D.ui.histogram.setLevels(mn, mx)
        
    def updateHistogramLookup(self,hist):
        self.MiniPlot2D.ui.histogram.imageItem().setLookupTable(hist.getLookupTable)
        self.Plot2D.ui.histogram.imageItem().setLookupTable(hist.getLookupTable)

    def set_voltage_calibration(self, calibration):
        self.x_volts_to_meters = float(calibration[1])
        self.y_volts_to_meters = float(calibration[2])
        self.z_volts_to_meters = float(calibration[3])
        self.x_meters_max = float(calibration[4])
        self.y_meters_max = float(calibration[5])
        self.z_meters_max = float(calibration[6])
        self.x_volts_max = float(calibration[7])
        self.y_volts_max = float(calibration[8])
        self.z_volts_max = float(calibration[9])

        print self.x_volts_to_meters
        print self.y_volts_to_meters
        print self.z_volts_to_meters 
        print self.x_meters_max 
        print self.y_meters_max
        print self.z_meters_max 
        print self.x_volts_max
        print self.y_volts_max 
        print self.z_volts_max 
        print 'ScanControl Set'

        #self.view2.setXRange(-self.x_meters_max/2 - 2.0e-7,self.x_meters_max/2,0)
        #self.view2.setYRange(-self.y_meters_max/2,self.y_meters_max/2 + 2.0e-7,0)


        
#----------------------------------------------------------------------------------------------#         
    """ The following section connects actions related to buttons on the Scan Control window."""
        
    def toggleFrameLock(self):
        if self.FrameLocked == True:
            self.push_FrameLock.setStyleSheet("#push_FrameLock{"+
            "image:url(:/nSOTScanner/Pictures/unlock.png);background: black;}")
            self.FrameLocked = False
            self.ROI.removeHandle(1)
            self.ROI.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = False)
            self.ROI2.removeHandle(1)
            self.ROI2.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = False)
        else:
            self.push_FrameLock.setStyleSheet("#push_FrameLock{"+
            "image:url(:/nSOTScanner/Pictures/lock.png);background: black;}")
            self.FrameLocked = True
            self.ROI.removeHandle(1)
            self.ROI.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
            self.ROI2.removeHandle(1)
            self.ROI2.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
            
    def toggleSpeedLock(self):
        if self.LinearSpeedLocked == False:
            self.push_SpeedLock.move(170,322)
            self.LinearSpeedLocked = True
            self.lineEdit_Linear.setReadOnly(True)
            self.lineEdit_LineTime.setReadOnly(False)
        else:
            self.push_SpeedLock.move(170,352)
            self.LinearSpeedLocked = False
            self.lineEdit_Linear.setReadOnly(False)
            self.lineEdit_LineTime.setReadOnly(True)
            
    def toggleDataLock(self):
        if self.DataLocked == True:
            self.push_DataLock.setStyleSheet("#push_DataLock{"+
            "image:url(:/nSOTScanner/Pictures/unlock.png);background: black;}")
            self.DataLocked = False
        else:
            self.push_DataLock.setStyleSheet("#push_DataLock{"+
            "image:url(:/nSOTScanner/Pictures/lock.png);background: black;}")
            self.DataLocked = True
            
    def autoRange(self):
        self.Plot2D.autoRange()
        self.Plot2D_Retrace.autoRange()
        
    def autoLevel(self):    
        self.Plot2D_Retrace.autoLevels()
    
    def toggleAspect(self):
        if self.aspectLocked:
            self.aspectLocked = False
            self.view.setAspectLocked(False)
            self.view3.setAspectLocked(False)
            self.push_aspectLocked.setText(str('Lock Aspect'))
        else:
            self.aspectLocked = True
            self.view.setAspectLocked(True, ratio = 1)
            self.view3.setAspectLocked(True, ratio = 1)
            self.push_aspectLocked.setText(str('Unlock Aspect'))
            
    def toggleCoordinates(self):
        if self.scanCoordinates:
            self.scanCoordinates = False
            self.update_gph()
            self.moveROI()
            self.moveROI3()
            self.push_scanCoordinates.setText('View Scan Coord.')
        else:
            self.scanCoordinates = True
            self.update_gph()
            self.moveROI()
            self.moveROI3()
            self.push_scanCoordinates.setText('View Atto Coord.')
            
    def selectProcessing(self, string):
        self.dataProcessing = string
        self.refreshPlotData()

    def selectPostProcessing(self, string):
        self.dataPostProcessing = string
        
    def selectChannel(self,string):
        if string == 'Z (V)':
            self.channel = 0
        elif string == 'B (T)':
            self.channel = 1
        self.refreshPlotData()
        
    def refreshPlotData(self):
        if self.dataProcessing == 'Raw':
            self.plotData = np.copy(self.data[self.channel])
            self.plotData_retrace = np.copy(self.data_retrace[self.channel])
        elif self.dataProcessing == 'Subtract Average':
            self.plotData = processImageData(np.copy(self.data[self.channel]), 'Subtract Line Average')
            self.plotData_retrace = processImageData(np.copy(self.data_retrace[self.channel]), 'Subtract Line Average')
        elif self.dataProcessing == 'Subtract Linear Fit':
            self.plotData = processImageData(np.copy(self.data[self.channel]), 'Subtract Line Linear')
            self.plotData_retrace = processImageData(np.copy(self.data_retrace[self.channel]), 'Subtract Line Linear')
        elif self.dataProcessing == 'Subtract Parabolic Fit':
            self.plotData = processImageData(np.copy(self.data[self.channel]), 'Subtract Line Quadratic')
            self.plotData_retrace = processImageData(np.copy(self.data_retrace[self.channel]), 'Subtract Line Quadratic')
        self.update_gph()
        
    def apply2DFit(self):
        if self.dataPostProcessing == 'Raw':
            self.plotData = np.copy(self.data[self.channel])
            self.plotData_retrace = np.copy(self.data_retrace[self.channel])
        else:
            self.plotData = processImageData(np.copy(self.plotData), self.dataPostProcessing)
            self.plotData_retrace = processImageData(np.copy(self.plotData_retrace), self.dataPostProcessing)
        self.update_gph()
            
    #----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to drawing the scanning square and updating 
        the plots."""
                    
    def updateROI(self,input):
        #Use rules for updating GUI for when the first ROI is changed
        self.updateScanArea(input)
        self.updateGUI()
        #Then move the second ROI to match
        self.moveROI2()
        self.moveROI3()
        
    def updateROI2(self,input):
        #Use rules for updating GUI for when the second ROI is changed
        self.updateScanArea2(input)
        self.updateGUI()
        #Then move the first ROI to match
        self.moveROI()  
        self.moveROI3()
        
    def updateROI3(self,input):
        #Use rules for updating GUI for when the second ROI is changed
        self.updateScanArea(input)
        self.updateGUI()
        #Then move the first ROI to match
        self.moveROI() 
        self.moveROI2()
        
    def updateScanArea(self, input):
        size = input.size()
        self.W = size.x()
        self.H = size.y()
        
        if self.scanCoordinates:
            inputAngle = input.angle()
            self.angle = inputAngle + self.currAngle
            pos = input.pos()
            posx = -self.W*np.cos(inputAngle*np.pi/180)/2 + self.H*np.sin(inputAngle*np.pi/180)/2
            posy = -self.H*np.cos(inputAngle*np.pi/180)/2 - self.W*np.sin(inputAngle*np.pi/180)/2
            self.Xc = (pos.x() - posx) * np.cos(self.currAngle*np.pi/180) - (pos.y() - posy) * np.sin(self.currAngle*np.pi/180) + self.currXc
            self.Yc = (pos.y() - posy) * np.cos(self.currAngle*np.pi/180) + (pos.x() - posx) * np.sin(self.currAngle*np.pi/180) + self.currYc
            self.x = self.Xc - self.W*np.cos(self.angle*np.pi/180)/2 + self.H*np.sin(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
        else: 
            self.angle = input.angle()
            pos = input.pos()
            self.x = pos.x()
            self.y = pos.y()
            self.Xc = self.x - self.H*np.sin(self.angle*np.pi/180)/2 + self.W*np.cos(self.angle*np.pi/180)/2
            self.Yc = self.y + self.H*np.cos(self.angle*np.pi/180)/2 + self.W*np.sin(self.angle*np.pi/180)/2
        
    def updateScanArea2(self, input):
        size = input.size()
        self.W = size.x()
        self.H = size.y()
        
        self.angle = input.angle()
        pos = input.pos()
        self.x = pos.x()
        self.y = pos.y()
        self.Xc = self.x - self.H*np.sin(self.angle*np.pi/180)/2 + self.W*np.cos(self.angle*np.pi/180)/2
        self.Yc = self.y + self.H*np.cos(self.angle*np.pi/180)/2 + self.W*np.sin(self.angle*np.pi/180)/2
        
    def updateGUI(self):
        self.updateLineEdits()
        self.updateSpeed()
        
    def moveROI(self):
        self.ROI.setSize([self.W, self.H], update = False, finish = False)
        if self.scanCoordinates:
            angle = self.angle-self.currAngle
            self.ROI.setAngle(angle, update = False, finish = False)
            x = (self.Xc - self.currXc)*np.cos(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.sin(self.currAngle*np.pi/180) + self.H*np.sin(angle*np.pi/180)/2 - self.W*np.cos(angle*np.pi/180)/2 
            y = -(self.Xc - self.currXc)*np.sin(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.cos(self.currAngle*np.pi/180) - self.H*np.cos(angle*np.pi/180)/2 - self.W*np.sin(angle*np.pi/180)/2 
            self.ROI.setPos([x, y], update = False, finish = False)
        else: 
            self.ROI.setAngle(self.angle, update = False, finish = False)
            self.ROI.setPos([self.x, self.y], update = False, finish = False)
        self.updateHandles(self.ROI)
    
    def moveROI2(self):
        self.ROI2.setPos([self.x, self.y], update = False, finish = False)
        self.ROI2.setSize([self.W, self.H], update = False, finish = False)
        self.ROI2.setAngle(self.angle, update = False, finish = False)
        self.updateHandles(self.ROI2)
        
    def moveROI3(self):
        self.ROI3.setSize([self.W, self.H], update = False, finish = False)
        if self.scanCoordinates:
            angle = self.angle-self.currAngle
            self.ROI3.setAngle(angle, update = False, finish = False)
            x = (self.Xc - self.currXc)*np.cos(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.sin(self.currAngle*np.pi/180) + self.H*np.sin(angle*np.pi/180)/2 - self.W*np.cos(angle*np.pi/180)/2 
            y = -(self.Xc - self.currXc)*np.sin(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.cos(self.currAngle*np.pi/180) - self.H*np.cos(angle*np.pi/180)/2 - self.W*np.sin(angle*np.pi/180)/2 
            self.ROI3.setPos([x, y], update = False, finish = False)
        else: 
            self.ROI3.setAngle(self.angle, update = False, finish = False)
            self.ROI3.setPos([self.x, self.y], update = False, finish = False)
        self.updateHandles(self.ROI3)
        
    def updateHandles(self, ROI):
        for h in ROI.handles:
            if h['item'] in ROI.childItems():
                p = h['pos']
                h['item'].setPos(h['pos'] * ROI.state['size'])     
            ROI.update()
            
    def toggleROIVisibility(self):
        if self.checkBox.isChecked():
            self.view.addItem(self.ROI)
            self.view3.addItem(self.ROI3)
        else:
            self.view.removeItem(self.ROI)
            self.view3.removeItem(self.ROI3)
            
    def traceRangeChanged(self, input):
        if not self.sigRangeChangedEmitted:
            range = input.viewRange()
            self.sigRangeChangedEmitted = True
            self.view3.setRange(xRange = range[0], yRange = range[1], padding =  0, update = False)
        else:
            self.sigRangeChangedEmitted = False
            
    def retraceRangeChanged(self, input):
        if not self.sigRangeChangedEmitted:
            range = input.viewRange()
            self.sigRangeChangedEmitted = True
            self.view.setRange(xRange = range[0], yRange = range[1], padding =  0, update = False)
        else:
            self.sigRangeChangedEmitted = False
            
    def setView(self):
        x_range, y_range = self.view.viewRange()
        if self.scanCoordinates:
            #Set the appropriate information
            self.angle = self.currAngle
            self.W = x_range[1] - x_range[0]
            self.H = y_range[1] - y_range[0]
            posx = -self.W/2
            posy = -self.H/2
            self.Xc = (x_range[0] - posx) * np.cos(self.currAngle*np.pi/180) - (y_range[0] - posy) * np.sin(self.currAngle*np.pi/180) + self.currXc
            self.Yc = (y_range[0] - posy) * np.cos(self.currAngle*np.pi/180) + (x_range[0] - posx) * np.sin(self.currAngle*np.pi/180) + self.currYc
            self.x = self.Xc - self.W*np.cos(self.angle*np.pi/180)/2 + self.H*np.sin(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            
            #update all the lines
            updateLineEdits()
            
            #Update ROIs
            self.moveROIs()

        else:
            #Set the appropriate information
            self.angle = 0
            self.W = x_range[1] - x_range[0]
            self.H = y_range[1] - y_range[0]
            self.Xc = (x_range[1] + x_range[0])/2
            self.Yc = (y_range[1] + y_range[0])/2
            self.x = x_range[0]
            self.y = y_range[0]
            
            #update all the lines
            self.updateLineEdits()
            
            #Update ROIs
            self.moveROIs()

    def updateLineEdits(self):
        self.lineEdit_W.setText(formatNum(self.W))
        self.lineEdit_H.setText(formatNum(self.H))
        self.lineEdit_Xc.setText(formatNum(self.Xc))
        self.lineEdit_Yc.setText(formatNum(self.Yc))
        self.lineEdit_Angle.setText(formatNum(self.angle))

    def moveROIs(self):
        self.moveROI()
        self.moveROI2()
        self.moveROI3()
#----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to updating scan parameters from
        the line edits."""  
        
    def updateXc(self):
        new_Xc = str(self.lineEdit_Xc.text())
        val = readNum(new_Xc)
        if isinstance(val,float):
            self.Xc = val
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.moveROIs()
        self.lineEdit_Xc.setText(formatNum(self.Xc))
        
    def updateYc(self):
        new_Yc = str(self.lineEdit_Yc.text())
        val = readNum(new_Yc)
        if isinstance(val,float):
            self.Yc = val
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROIs()
        self.lineEdit_Yc.setText(formatNum(self.Yc))
        
    def updateAngle(self):
        new_Angle = str(self.lineEdit_Angle.text())
        val = readNum(new_Angle)
        if isinstance(val,float):
            self.angle = val
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROIs()
        self.lineEdit_Angle.setText(formatNum(self.angle))
        
    def updateH(self):
        new_H = str(self.lineEdit_H.text())
        val = readNum(new_H)
        if isinstance(val,float):
            self.H = val
            if self.FrameLocked:
                self.W = self.H
                self.lineEdit_W.setText(formatNum(self.W))
                self.updateSpeed()
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROIs()
        self.lineEdit_H.setText(formatNum(self.H))
            
    def updateW(self):
        new_W = str(self.lineEdit_W.text())
        val = readNum(new_W)
        if isinstance(val,float):
            self.W = val
            if self.FrameLocked:
                self.H = self.W
                self.lineEdit_H.setText(formatNum(self.H))
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROIs()
            self.updateSpeed()
        self.lineEdit_W.setText(formatNum(self.W))
        
    def updateSpeed(self):
        if self.LinearSpeedLocked:
            self.lineTime = self.W / self.linearSpeed
            self.lineEdit_LineTime.setText(formatNum(self.lineTime))
            self.FrameTime = 2*self.lines * self.lineTime
            self.lineEdit_FrameTime.setText(formatNum(self.FrameTime))
        else: 
            self.linearSpeed = self.W / self.lineTime
            self.lineEdit_Linear.setText(formatNum(self.linearSpeed))
        
    def updatePixels(self):
        new_Pixels = str(self.lineEdit_Pixels.text())
        val = readNum(new_Pixels)
        if isinstance(val,float):
            self.pixels = int(val)
            if self.DataLocked:
                self.lines = int(val/self.PixelsAspectRatio)
                self.lineEdit_Lines.setText(formatNum(self.lines))
                self.FrameTime = self.lines * self.lineTime
                self.lineEdit_FrameTime.setText(formatNum(self.FrameTime))
            else:
                self.PixelsAspectRatio = float(self.pixels)/float(self.lines)
        self.lineEdit_Pixels.setText(formatNum(self.pixels))
        
    def updateLines(self):
        new_Lines = str(self.lineEdit_Lines.text())
        val = readNum(new_Lines)
        if isinstance(val,float):
            self.lines = int(val)
            if self.DataLocked:
                self.pixels = int(val*self.PixelsAspectRatio)
                self.lineEdit_Pixels.setText(formatNum(self.pixels))
            else:
                self.PixelsAspectRatio = float(self.pixels)/float(self.lines)
            self.FrameTime = self.lines * self.lineTime
            self.lineEdit_FrameTime.setText(formatNum(self.FrameTime))
        self.lineEdit_Lines.setText(formatNum(self.lines))
        
    def updateLinearSpeed(self):
        new_LinearSpeed = str(self.lineEdit_Linear.text())
        val = readNum(new_LinearSpeed)
        if isinstance(val,float):
            self.linearSpeed = val
            self.lineTime = self.W/self.linearSpeed
            self.lineEdit_LineTime.setText(formatNum(self.lineTime))
            self.FrameTime = self.lineTime * self.lines
            self.lineEdit_FrameTime.setText(formatNum(self.FrameTime))
        self.lineEdit_Linear.setText(formatNum(self.linearSpeed))
        self.updateScanParameters()

    def updateLineTime(self):
        new_LineTime = str(self.lineEdit_LineTime.text())
        val = readNum(new_LineTime)
        if isinstance(val,float):
            self.lineTime = val
            self.linearSpeed = self.W/self.lineTime
            self.lineEdit_Linear.setText(formatNum(self.linearSpeed))
            self.FrameTime = self.lineTime * self.lines
            self.lineEdit_FrameTime.setText(formatNum(self.FrameTime))
        self.lineEdit_LineTime.setText(formatNum(self.lineTime))
        self.updateScanParameters()

    def updateFileName(self):
        self.fileName = str(self.lineEdit_FileName.text())
        
    def updateXTilt(self):
        val = readNum(str(self.lineEdit_XTilt.text()))
        if isinstance(val,float):
            self.x_tilt = val*np.pi / 180
        self.lineEdit_XTilt.setText(formatNum(self.x_tilt))

    def updateYTilt(self):
        val = readNum(str(self.lineEdit_YTilt.text()))
        if isinstance(val,float):
            self.y_tilt = val*np.pi / 180
        self.lineEdit_YTilt.setText(formatNum(self.y_tilt))

    def updateScanMode(self, string):
        if string == 'Constant Height':
            self.scanMode = 'Constant Height'
            self.lineEdit_XTilt.setEnabled(True)
            self.lineEdit_YTilt.setEnabled(True)
            if self.ConstantHeightReady:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
            else:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)
        elif string == 'Feedback':
            self.scanMode = 'Feedback'
            self.lineEdit_XTilt.setEnabled(False)
            self.lineEdit_YTilt.setEnabled(False)
            if self.FeedbackReady:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
            else:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)

    def updateFeedbackStatus(self, status):
        if status:
            self.FeedbackReady = True
            if self.scanMode == 'Feedback':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
        else:
            self.FeedbackReady = False
            if self.scanMode == 'Feedback':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)

    def updateConstantHeightStatus(self, status):
        if status:
            self.ConstantHeightReady = True
            if self.scanMode == 'Constant Height':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
        else:
            self.ConstantHeightReady = False
            if self.scanMode == 'Constant Height':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)
#----------------------------------------------------------------------------------------------#      
    """ The following section has scanning functions and live graph updating."""  
        
    def abortScan(self):
        self.scanning = False

    def startScan(self):
        try:
            print 'Starting Scan Protocol'
            #Set scan values
            self.currAngle = self.angle
            self.currXc = self.Xc
            self.currYc = self.Yc
            self.currW = self.W
            self.currH = self.H
            self.curr_x = self.x
            self.curr_y = self.y
            
            #Determine plot scales
            self.xscale, self.yscale = self.currW / self.lines, self.currH / self.pixels
            
            #If necessary, update ROIs
            if self.scanCoordinates:
                self.moveROI()
                self.moveROI3()
                
            #Initialize empty data sets
            pxsize = (2, self.lines,self.pixels)
            self.data = np.zeros(pxsize)
            self.data_retrace = np.zeros(pxsize)
            self.plotData = np.zeros(pxsize)[0]
            self.plotData_retrace = np.zeros(pxsize)[0]
            self.currLine = 0

            #Update graphs with empty data sets
            self.update_gph()
            
            #Prevent you from editing most parameters mid scan. 
            self.push_Scan.setEnabled(False)
            self.lineEdit_Angle.setEnabled(False)
            self.lineEdit_Xc.setEnabled(False)
            self.lineEdit_Yc.setEnabled(False)
            self.lineEdit_W.setEnabled(False)
            self.lineEdit_H.setEnabled(False)
            self.push_setView.setEnabled(False)
            self.lineEdit_Lines.setEnabled(False)
            self.lineEdit_Pixels.setEnabled(False)
            self.lineEdit_XTilt.setEnabled(False)
            self.lineEdit_YTilt.setEnabled(False)

            #Begin data gathering procedure
            self.scanning = True
            self.push_Scan.setText('Scanning')
            self.push_Scan.setEnabled(False)
            self.update_data()
        except Exception as inst:
            print "testUpdates: " + str(inst)
        
    @inlineCallbacks
    def update_data(self):
        try:
            #Create data vault file with appropriate parameters
            #Retrace index is 0 for trace, 1 for retrace
            yield self.dv.new("nSOT Scan Data " + self.fileName, ['Retrace Index','X Pos. Index','Y Pos. Index','X Pos. Voltage', 'Y Pos. Voltage'],['Z Pos. Voltage','SSAA DC Voltage'])
            print 'Created new DV file'
            params = (('X Center', self.currXc), ('Y Center', self.currYc), ('Width', self.currW), ('Height',self.currH), ('Angle',self.currAngle), ('Speed',self.linearSpeed), ('Pixels',self.pixels), ('Lines', self.lines))
            print params
            #Avi - This line was throwing an error - I'm not sure why - I commented it out to test the scanning
            #the version of data vault that is saved on this computer differs from that running on the mScope monitor 
            #computer in exactly the function that was throwing an error - the save() function in the ini python file
            #yield self.dv.add_parameters(params)
            #Marec - Yes, we should update that computer to the latest version of datavault
            print 'Added params'

            self.updateScanParameters()
            #First, lets check that all the points are within range
            #ADD THIS LATER
            
            #For now, HARD CODED THAT using DAC out 2 (or 1 when zero indexed) for X 
            #and DAC out 3 (2 zeros indexed) for Y. 

            if self.scanParameters['delta_x'] > 0 and self.scanning:
                print 'Moving by: ' + str(self.scanParameters['delta_x']) + ' in the x direction to starting position.'
                yield self.dac.ramp1(1, self.Atto_X_Voltage, self.scanParameters['x_start_voltage'], self.scanParameters['x_points'], self.scanParameters['delay_x'])
                #ramp1 returns ramp completed before the ramp is completed. Add a sleep statement to make 
                #make sure we don't continue too soon
                yield self.sleep(self.scanParameters['x_points']*self.scanParameters['delay_x'] / (1e6))
                
            if self.scanParameters['delta_y'] > 0 and self.scanning:
                print 'Moving by: ' + str(self.scanParameters['delta_y']) + ' in the y direction to starting position.'
                yield self.dac.ramp1(2, self.Atto_Y_Voltage, self.scanParameters['y_start_voltage'], self.scanParameters['y_points'], self.scanParameters['delay_y'])
                #ramp1 returns ramp completed before the ramp is completed. Add a sleep statement to make 
                #make sure we don't continue too soon
                yield self.sleep(self.scanParameters['y_points']*self.scanParameters['delay_y'] / (1e6))
            
            if self.scanMode == 'Constant Height' and self.scanning and self.Atto_Z_Voltage != 0:
                print 'Moving by: ' + str(self.Atto_Z_Voltage) + ' in the z direction to return to zero z offset.'
                #By default ramps output 0 from the current z voltage back to 0 with 1000 points at 1 ms delay 
                yield self.dac.ramp1(0, self.Atto_Z_Voltage, 0.0, 1000, 1000)
                #Eventually initialize this in communication with the approach software
                self.Atto_Z_Voltage = 0.0
            
            x_start_voltage = self.scanParameters['x_start_voltage']
            y_start_voltage = self.scanParameters['y_start_voltage']
            
            self.Atto_X_Voltage = x_start_voltage
            self.Atto_Y_Voltage = y_start_voltage
            
            #DAC messes up with ramp commands and doesn't get fully read. This clears the buffer
            #so that the first line of data is preserved correctly. 
            a = yield self.dac.read()
            while a != '':
                print a
                a = yield self.dac.read()
            
            for i in range(0,self.lines):
                print 'Starting sweep for line ' + str(i) + '.'
                if not self.scanning:
                    break

                #Get start and end positions for scan of a single line
                startx = self.Atto_X_Voltage
                starty = self.Atto_Y_Voltage
                stopx = self.Atto_X_Voltage + self.scanParameters['line_x']
                stopy = self.Atto_Y_Voltage + self.scanParameters['line_y']

                #Time for debugging
                tzero = time.clock()
                #Do buffer ramp
                if self.scanMode == 'Feedback':
                    newData = yield self.dac.buffer_ramp([1,2],[0,1],[startx, starty],[stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'])
                elif self.scanMode == 'Constant Height':
                    startz = self.Atto_Z_Voltage
                    stopz = self.Atto_Z_Voltage + self.scanParameters['line_y']*np.tan(self.y_tilt) + self.scanParameters['line_x']*np.tan(self.x_tilt)
                    newData = yield self.dac.buffer_ramp([0,1,2],[0,1],[startz,startx, starty],[stopz, stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'])
                    self.Atto_Z_Voltage = stopz
                    
                self.Atto_X_Voltage = stopx
                self.Atto_Y_Voltage = stopy

                #bin newData to appropriate number of pixels
                print 'Time taken for buffer ramp: ' + str(time.clock()-tzero)
                tzero = time.clock()
                #Add the binned Z data to the dataset
                self.data[0][i,:] = self.bin_data(newData[0], self.pixels, 'trace')
                #Add the binned magnetic field data to the dataset
                self.data[1][i,:] = self.bin_data(newData[1], self.pixels, 'trace')
                print 'Time taken to bin data: ' + str(time.clock()-tzero)
                tzero = time.clock()
                self.plotData[i,:] = processLineData(np.copy(self.data[self.channel][i,:]), self.dataProcessing)
                print 'Time taken to process the line data: ' + str(time.clock()-tzero)
                tzero = time.clock()
                
                #Reformat data and add to data vault
                x_voltage = np.linspace(startx, stopx, self.pixels)
                y_voltage = np.linspace(starty, stopy, self.pixels)
                formated_data = []
                for j in range(0, self.pixels):
                    #Putting in 0 for SSAA voltage (last entry) because not yet being used/read
                    formated_data.append((0, i, j, x_voltage[j], y_voltage[j], self.data[0][i,j], self.data[1][i,j]))
                yield self.dv.add(formated_data)
                print 'Time taken to add data to data vault: ' + str(time.clock()-tzero)

                #------------------------------------#
                
                if not self.scanning:
                    break
                    
                #Get retrace data
                startx = self.Atto_X_Voltage
                starty = self.Atto_Y_Voltage
                stopx = self.Atto_X_Voltage - self.scanParameters['line_x']
                stopy = self.Atto_Y_Voltage - self.scanParameters['line_y']

                if self.scanMode == 'Feedback':
                    newData = yield self.dac.buffer_ramp([1,2],[0,1],[startx, starty],[stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'])
                elif self.scanMode == 'Constant Height':
                    startz = self.Atto_Z_Voltage
                    stopz = self.Atto_Z_Voltage - self.scanParameters['line_y']*np.tan(self.y_tilt) - self.scanParameters['line_x']*np.tan(self.x_tilt)
                    newData = yield self.dac.buffer_ramp([0,1,2],[0,1],[startz,startx, starty],[stopz, stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'])
                    self.Atto_Z_Voltage = stopz
                    
                self.Atto_X_Voltage = stopx
                self.Atto_Y_Voltage = stopy

                #bin newData to appropriate number of pixels for Z data
                self.data_retrace[0][i,:] = self.bin_data(newData[0], self.pixels,'retrace')
                #bin newData to appropriate number of pixels for field data
                self.data_retrace[1][i,:] = self.bin_data(newData[1], self.pixels,'retrace')
                
                #Process data for plotting
                self.plotData_retrace[i,:] = processLineData(np.copy(self.data_retrace[self.channel][i,:]), self.dataProcessing)
                
                #Reformat data and add to data vault
                x_voltage = np.linspace(startx, stopx, self.pixels)
                y_voltage = np.linspace(starty, stopy, self.pixels)
                formated_data = []
                for j in range(0, self.pixels):
                    #Putting in 0 for SSAA voltage (last entry) because not yet being used/read
                    formated_data.append((1, i, j, x_voltage[::-1][j], y_voltage[::-1][j], self.data_retrace[0][i,j], self.data_retrace[1][i,j]))
                yield self.dv.add(formated_data)
                
                #------------------------------------#
                
                if not self.scanning:
                    break
                    
                #Move to position for next line
                startx = self.Atto_X_Voltage
                starty = self.Atto_Y_Voltage
                stopx = self.Atto_X_Voltage + self.scanParameters['pixel_x']
                stopy = self.Atto_Y_Voltage + self.scanParameters['pixel_y']

                tzero = time.clock()
                if self.scanMode == 'Feedback':
                    yield self.dac.buffer_ramp([1,2],[0],[startx, starty],[stopx, stopy], self.scanParameters['pixel_points'], self.scanParameters['pixel_delay'])
                elif self.scanMode == 'Constant Height':
                    startz = self.Atto_Z_Voltage
                    stopz = self.Atto_Z_Voltage - self.scanParameters['pixel_y']*np.tan(self.y_tilt) - self.scanParameters['pixel_x']*np.tan(self.x_tilt)
                    yield self.dac.buffer_ramp([0,1,2],[0],[startz,startx, starty],[stopz, stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'])
                    self.Atto_Z_Voltage = stopz
                    
                self.Atto_X_Voltage = stopx
                self.Atto_Y_Voltage = stopy
                #ramp to next y point
                print 'Time taken to move to next line: ' + str(time.clock()-tzero)
                tzero = time.clock()

                #update graph
                self.currLine = i
                self.update_gph()
                print 'Time taken to update graphs: ' + str(time.clock()-tzero)
            
            #Successfully finished the scan!
            self.scanning = False
            self.push_Scan.setText('Scan')
            self.push_Scan.setEnabled(True)
            
            self.push_Scan.setEnabled(True)
            self.lineEdit_Angle.setEnabled(True)
            self.lineEdit_Xc.setEnabled(True)
            self.lineEdit_Yc.setEnabled(True)
            self.lineEdit_W.setEnabled(True)
            self.lineEdit_H.setEnabled(True)
            self.push_setView.setEnabled(True)
            self.lineEdit_Lines.setEnabled(True)
            self.lineEdit_Pixels.setEnabled(True)
            self.lineEdit_XTilt.setEnabled(True)
            self.lineEdit_YTilt.setEnabled(True)
        except Exception as inst:
            print 'update_data: ' + str(inst)
                
    def update_gph(self):
        #Updates the trace, retrace, and mini plots with the plotData and plotData_retract images. 
        try:
            self.Plot2D.setImage(self.plotData, autoRange = False, autoLevels = False)
            self.Plot2D.imageItem.resetTransform()
            
            self.Plot2D_Retrace.setImage(self.plotData_retrace, autoRange = False, autoLevels = False)
            self.Plot2D_Retrace.imageItem.resetTransform()
            
            if self.scanCoordinates:
                angle = 0
                tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
                self.Plot2D.imageItem.setPos(-self.currW/2,-self.currH/2)
                self.Plot2D.imageItem.setTransform(tr)
                self.Plot2D_Retrace.imageItem.setPos(-self.currW/2,-self.currH/2)
                self.Plot2D_Retrace.imageItem.setTransform(tr)
            else: 
                angle = self.currAngle
                tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
                self.Plot2D.imageItem.setPos(self.curr_x,self.curr_y)
                self.Plot2D.imageItem.setTransform(tr)
                self.Plot2D_Retrace.imageItem.setPos(self.curr_x,self.curr_y)
                self.Plot2D_Retrace.imageItem.setTransform(tr)
            
            self.MiniPlot2D.setImage(self.plotData, autoRange = False, autoLevels = False)
            self.MiniPlot2D.imageItem.resetTransform()
            angle = self.currAngle
            tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
            self.MiniPlot2D.imageItem.setPos(self.curr_x,self.curr_y)
            self.MiniPlot2D.imageItem.setTransform(tr)

            #Update line traces
            pos = np.linspace(-self.currH/2, self.currH/2, self.pixels)
            self.traceLinePlot.clear()
            self.traceLinePlot.plot(pos, self.plotData[self.currLine,:])
            self.retraceLinePlot.clear()
            self.retraceLinePlot.plot(pos, self.plotData_retrace[self.currLine,:])

        except Exception as inst:
            print 'update_gph: ' + str(inst)
    
    def bin_data(self, data, num_points, trace):
        length = np.size(data)
        
        points = np.round(np.linspace(0,length-1,num_points)).astype(int)
        binned_data = np.take(data,points)
        if trace == 'retrace':
            length = len(binned_data)
            binned_data = binned_data[::-1]
        return binned_data
        
    def updateScanParameters(self):
        
        #-------------------------------------------------------------------------------------------------#
        '''
        Ramp to starting point calculations. 
        '''
        print 'Updating Scan Parameters'
        
        #Calculate the scan start voltage positions
        x_start_voltage = self.curr_x * self.x_volts_to_meters + self.x_volts_max/2
        y_start_voltage = self.curr_y * self.y_volts_to_meters + self.y_volts_max/2
        
        #Figure out how far we need to move from current position to get to starting position
        delta_x = np.absolute(self.Atto_X_Voltage - x_start_voltage)
        delta_y = np.absolute(self.Atto_Y_Voltage - y_start_voltage)
        
        #Make sure we're always taking the minimum step size with the dac, which is 300 microvolts,
        #such that the tip moves as smoothly as possible
        x_points = int(delta_x / (300e-6))
        y_points = int(delta_y / (300e-6))
        
        #next, choose the delay such that the speed is as chosen on the gui
        #300e-6 / xy_volts_to_meters yields the distance per step. 
        # dividing by linear speed gives time per step, ie the delay, in seconds
        #1e6 converts to microseconds
        delay_x = int(np.absolute(1e6 * (300e-6 / (self.x_volts_to_meters * self.linearSpeed))))
        delay_y = int(np.absolute(1e6 * (300e-6 / (self.y_volts_to_meters * self.linearSpeed))))
        
        #-------------------------------------------------------------------------------------------------#
        '''
        Single Line Scan Calculation
        '''
                 
        #Calculate the speed, number of points, delta_x/delta_y for scanning a line
        line_x = -self.currH * np.sin(np.pi*self.currAngle/180) * self.x_volts_to_meters
        line_y = self.currH * np.cos(np.pi*self.currAngle/180) * self.y_volts_to_meters
        
        line_points = int(np.maximum(np.absolute(line_x / (300e-6)), np.absolute(line_y / (300e-6))))
        line_delay = int(1e6 *self.lineTime / line_points)

        #-------------------------------------------------------------------------------------------------#
        '''
        Move to next line scan calculation
        '''
        #Calculate the speed, number of points, and delta_x/delta_y for moving to the next line
        pixel_x = self.currW * np.cos(np.pi*self.currAngle/180) * self.x_volts_to_meters / (self.lines - 1)
        pixel_y = self.currW * np.sin(np.pi*self.currAngle/180) * self.y_volts_to_meters / (self.lines - 1)
        
        pixel_points = int(np.maximum(np.absolute(pixel_x / (300e-6)), np.absolute(pixel_y / (300e-6))))
        pixel_delay = int(1e6 *self.currW / ((self.lines-1)*self.linearSpeed*pixel_points))

        self.scanParameters = {
            'x_start_voltage'            : x_start_voltage, #X position in volts where the scan starts
            'y_start_voltage'            : y_start_voltage, #Y position in volts where the scan starts
            'delta_x'                    : delta_x, #Absolute magnitude of volts needed to travel in X to get to the x starting point
            'delta_y'                    : delta_y, #Absolute magnitude of volts needed to travel in Y to get to the y starting point
            'x_points'                   : x_points, #Number of steps to be taken when ramping from current position to starting position to maximize use of spatial resolution
            'y_points'                   : y_points, #Number of steps to be taken when ramping from current position to starting position to maximize use of spatial resolution
            'delay_x'                    : delay_x, #delay in us between each point when ramping to starting point to achieve desired speed
            'delay_y'                    : delay_y, #delay in us between each point when ramping to starting point to achieve desired speed
            'line_x'                     : line_x, #volts that need to be moved in the x direction for the scan of a single line
            'line_y'                     : line_y, #volts that need to be moved in the y direction for the scan of a single line
            'line_points'                : line_points, #number of points that should be taken for minimum step resolution for a single line
            'line_delay'                 : line_delay, #delay between points for a single line to ensure proper speed
            'pixel_x'                    : pixel_x, #volts that need to be moved in the x direction to move from one line scan to the next
            'pixel_y'                    : pixel_y, #volts that need to be moved in the y direction to move from one line scan to the next
            'pixel_points'               : pixel_points, #number of points that should be taken for minimum step resolution for moving to next line
            'pixel_delay'                : pixel_delay, #delay between points for a single line to ensure proper speed
        }
        print 'Scan parameters updated to: '
        print self.scanParameters

#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""
           
    def lockInterface(self):
        self.push_Abort.setEnabled(False)
        self.push_Scan.setEnabled(False)
        self.push_DataLock.setEnabled(False)
        self.push_FrameLock.setEnabled(False)
        self.push_scanCoordinates.setEnabled(False)
        self.push_aspectLocked.setEnabled(False)
        self.push_SpeedLock.setEnabled(False)
        self.push_setView.setEnabled(False)
        self.push_apply2DFit.setEnabled(False)
        self.push_autoLevel.setEnabled(False)
        self.push_autoRange.setEnabled(False)

        self.lineEdit_FileName.setEnabled(False)
        self.lineEdit_Linear.setEnabled(False)
        self.lineEdit_Xc.setEnabled(False)
        self.lineEdit_Yc.setEnabled(False)
        self.lineEdit_W.setEnabled(False)
        self.lineEdit_H.setEnabled(False)
        self.lineEdit_Angle.setEnabled(False)
        self.lineEdit_Lines.setEnabled(False)
        self.lineEdit_Pixels.setEnabled(False)
        self.lineEdit_LineTime.setEnabled(False)
        self.lineEdit_FrameTime.setEnabled(False)
        self.lineEdit_ImageNum.setEnabled(False)
        self.lineEdit_XTilt.setEnabled(False)
        self.lineEdit_YTilt.setEnabled(False)

        self.comboBox_Processing.setEnabled(False)
        self.comboBox_PostProcessing.setEnabled(False)
        self.comboBox_Channel.setEnabled(False)
        self.comboBox_scanMode.setEnabled(False)

        self.checkBox.setEnabled(False)

    def unlockInterface(self):
        self.push_Abort.setEnabled(True)
        #Scan start gets enabled later when it's actually ready to start scanning
        #self.push_Scan.setEnabled(True)
        self.push_DataLock.setEnabled(True)
        self.push_FrameLock.setEnabled(True)
        self.push_scanCoordinates.setEnabled(True)
        self.push_aspectLocked.setEnabled(True)
        self.push_SpeedLock.setEnabled(True)
        self.push_setView.setEnabled(True)
        self.push_apply2DFit.setEnabled(True)
        self.push_autoLevel.setEnabled(True)
        self.push_autoRange.setEnabled(True)

        self.lineEdit_FileName.setEnabled(True)
        self.lineEdit_Linear.setEnabled(True)
        self.lineEdit_Xc.setEnabled(True)
        self.lineEdit_Yc.setEnabled(True)
        self.lineEdit_W.setEnabled(True)
        self.lineEdit_H.setEnabled(True)
        self.lineEdit_Angle.setEnabled(True)
        self.lineEdit_Lines.setEnabled(True)
        self.lineEdit_Pixels.setEnabled(True)
        self.lineEdit_LineTime.setEnabled(True)
        self.lineEdit_FrameTime.setEnabled(True)
        self.lineEdit_ImageNum.setEnabled(True)
        self.lineEdit_XTilt.setEnabled(True)
        self.lineEdit_YTilt.setEnabled(True)

        self.comboBox_Processing.setEnabled(True)
        self.comboBox_PostProcessing.setEnabled(True)
        self.comboBox_Channel.setEnabled(True)
        self.comboBox_scanMode.setEnabled(True)

        self.checkBox.setEnabled(True)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
        
        