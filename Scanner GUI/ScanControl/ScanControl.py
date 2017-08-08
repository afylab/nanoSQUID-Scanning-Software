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

'''
THINGS TO DO:
Make sure no scan more than maximum area
Fix linewidth to be constant number of pixels instead of bullshit variable stuff it does now
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
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.setupScanningArea()
        self.moveDefault()
        
        self.pixels = 256
        self.lines = 256
        self.PixelsAspectRatio = 1.0
        
        self.FrameTime = 16.38
        self.linearSpeed = 78.13e-6
        self.lineTime = 64e-3
        
        #Connect the buttons to the appropriate methods
        self.push_FrameLock.clicked.connect(self.toggleFrameLock)
        self.push_SpeedLock.clicked.connect(self.toggleSpeedLock)
        self.push_DataLock.clicked.connect(self.toggleDataLock)
        self.push_autoRange.clicked.connect(self.autoRange)
        self.push_autoLevel.clicked.connect(self.autoLevel)
        self.push_aspectLocked.clicked.connect(self.toggleAspect)
        self.push_scanCoordinates.clicked.connect(self.toggleCoordinates)
        self.push_Test.clicked.connect(self.testUpdates)
        
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
                
        self.checkBox.toggled.connect(self.toggleROIVisibility)
                
        self.comboBox_Processing.activated[str].connect(self.selectProcessing)
        
        self.ROI.sigRegionChanged.connect(self.updateROI)
        self.ROI2.sigRegionChanged.connect(self.updateROI2)
        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None
        self.dac = None
        self.hf = None
        self.ips = None
        
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
        
    def setupAdditionalUi(self):
        #Initial read only configuration of line edits
        self.lineEdit_Linear.setReadOnly(False)
        self.lineEdit_LineTime.setReadOnly(True)
        
        #Set up main plot
        self.view = pg.PlotItem(title="Magnetic Field")
        self.view.setLabel('left',text='Y position',units = 'm')
        self.view.setLabel('right',text='Y position',units = 'm')
        self.view.setLabel('top',text='X position',units = 'm')
        self.view.setLabel('bottom',text='X position',units = 'm')
        self.Plot2D = pg.ImageView(parent = self.centralwidget, view = self.view)
        self.view.invertY(False)
        self.Plot2D.setGeometry(QtCore.QRect(240, 90, 750, 650))
        self.view.setAspectLocked(self.aspectLocked)
        self.Plot2D.ui.roiBtn.hide()
        self.Plot2D.ui.menuBtn.hide()
        self.Plot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        self.Plot2D.lower()
        self.PlotArea.close()
        
        #Set up mini plot for maximum scan range
        self.view2 = pg.PlotItem(title='Full Scan Range')
        self.view2.setLabel('left',text='Y position',units = 'm')
        self.view2.setLabel('right',text='Y position',units = 'm')
        self.view2.setLabel('top',text='X position',units = 'm')
        self.view2.setLabel('bottom',text='X position',units = 'm')
        self.view2.enableAutoRange(self.view2.getViewBox().XYAxes, enable = False)
        self.MiniPlot2D = pg.ImageView(parent = self.centralwidget, view = self.view2)
        self.view2.invertY(False)
        self.MiniPlot2D.setGeometry(QtCore.QRect(5, 500, 228, 228))
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
        
        #Create default dataset for initial plots
        self.pxsize = (256,256)
        extent = [-1e-5,1e-5,-1e-5,1e-5]
        self.data = np.zeros(self.pxsize)
        self.x0, x1 = (extent[0], extent[1])
        self.y0, y1 = (extent[2], extent[3])
        self.xscale, self.yscale = 1.0*(x1-self.x0) / self.data.shape[0], 1.0*(y1-self.y0) / self.data.shape[1]
        
        #Load default image
        self.Plot2D.setImage(self.data, autoRange = False, autoLevels = False, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.Plot2D.show()
        self.MiniPlot2D.setImage(self.data, autoRange = False, autoLevels = False, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
        self.MiniPlot2D.show()
        
        #Connect large plot histogram changes to the mini plot
        self.Plot2D.ui.histogram.sigLevelsChanged.connect(self.updateMiniHistogramLevels)
        self.Plot2D.ui.histogram.sigLookupTableChanged.connect(self.updateMiniHistogramLookup)
        
    def setupScanningArea(self):
        self.x = -2.5e-6
        self.y = -2.5e-6
        self.Xc = 0
        self.Yc = 0
        self.H = 5e-6
        self.W = 5e-6
        self.angle = 0
        
        # Keep track of plotted data location / angle so that we can also plot it in scan coordinates
        self.currAngle = 0
        self.currXc = 0
        self.currYc = 0
        self.currH = 2e-5
        self.currW = 2e-5
        
        #Testing stuff
        self.ROI = pg.RectROI((-2.5e-6,-2.5e-6),(5e-6,5e-6), movable = True)
        self.ROI2 = pg.RectROI((-2.5e-6,-2.5e-6),(5e-6,5e-6), movable = True)
        
        self.view.addItem(self.ROI)
        self.view2.addItem(self.ROI2)
        
        #Remove default handles and add desired handles. 
        self.ROI.removeHandle(self.ROI.indexOfHandle(self.ROI.getHandles()[0]))
        self.ROI.addRotateHandle((0,0),(0.5,0.5), name = 'Rotate')
        self.ROI.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
        
        self.ROI2.removeHandle(self.ROI2.indexOfHandle(self.ROI2.getHandles()[0]))
        self.ROI2.addRotateHandle((0,0),(0.5,0.5), name = 'Rotate')
        self.ROI2.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
        
    def updateMiniHistogramLevels(self, hist):
        mn, mx = hist.getLevels()
        self.MiniPlot2D.ui.histogram.setLevels(mn, mx)
        
    def updateMiniHistogramLookup(self,hist):
        self.MiniPlot2D.ui.histogram.imageItem().setLookupTable(hist.getLookupTable)
        
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
            self.push_SpeedLock.move(170,279)
            self.LinearSpeedLocked = True
            self.lineEdit_Linear.setReadOnly(True)
            self.lineEdit_LineTime.setReadOnly(False)
        else:
            self.push_SpeedLock.move(170,309)
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
        
    def autoLevel(self):    
        self.Plot2D.autoLevels()
    
    def toggleAspect(self):
        if self.aspectLocked:
            self.aspectLocked = False
            self.view.setAspectLocked(False)
        else:
            self.aspectLocked = True
            self.view.setAspectLocked(True, ratio = 1)
            
    def toggleCoordinates(self):
        if self.scanCoordinates:
            self.scanCoordinates = False
            self.update_gph()
            self.moveROI()
            self.push_scanCoordinates.setText('Scan Coordinates')
        else:
            self.scanCoordinates = True
            self.update_gph()
            self.moveROI()
            self.push_scanCoordinates.setText('Absolute Coordinates')
            
    def selectProcessing(self, str):
        self.dataProcessing = str
            
    #----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to drawing the scanning square."""
        
    def formatNum(self,val):
        string = '%e'%val
        num  = float(string[0:-4])
        exp = int(string[-3:])
        if exp < -6:
            diff = exp + 9
            num = num * 10**diff
            if num - int(num) == 0:
                num = int(num)
            else: 
                num = round(num,2)
            string = str(num)+'n'
        elif exp < -3:
            diff = exp + 6
            num = num * 10**diff
            if num - int(num) == 0:
                num = int(num)
            else: 
                num = round(num,2)
            string = str(num)+'u'
        elif exp < 0:
            diff = exp + 3
            num = num * 10**diff
            if num - int(num) == 0:
                num = int(num)
            else: 
                num = round(num,2)
            string = str(num)+'m'
        elif exp >= 0:
            if val - int(val) == 0:
                val = int(val)
            else: 
                val = round(val,2)
            string = str(val)
        return string
        
    def readNum(self,string):
        try:
            val = float(string)
        except:
            exp = string[-1]
            if exp == 'm':
                exp = 1e-3
            if exp == 'u':
                exp = 1e-6
            if exp == 'n':
                exp = 1e-9
            try:
                val = float(string[0:-1])*exp
            except: 
                return 'Incorrect Format'
        return val
                    
    def updateROI(self,input):
        #Use rules for updating GUI for when the first ROI is changed
        self.updateScanArea(input)
        self.updateGUI()
        #Then move the second ROI to match
        self.moveROI2()
        
    def updateROI2(self,input):
        #Use rules for updating GUI for when the second ROI is changed
        self.updateScanArea2(input)
        self.updateGUI()
        #Then move the first ROI to match
        self.moveROI()  
        
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
        self.lineEdit_Xc.setText(self.formatNum(self.Xc))
        self.lineEdit_Yc.setText(self.formatNum(self.Yc))
        
        self.lineEdit_Angle.setText(self.formatNum(self.angle))
        
        self.lineEdit_H.setText(self.formatNum(self.H))
        self.lineEdit_W.setText(self.formatNum(self.W))
        
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
        
    def updateHandles(self, ROI):
        for h in ROI.handles:
            if h['item'] in ROI.childItems():
                p = h['pos']
                h['item'].setPos(h['pos'] * ROI.state['size'])     
            ROI.update()
            
    def toggleROIVisibility(self):
        if self.checkBox.isChecked():
            self.view.addItem(self.ROI)
        else:
            self.view.removeItem(self.ROI)
#----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to updating scan parameters from
        the line edits."""  
        
    def updateXc(self):
        new_Xc = str(self.lineEdit_Xc.text())
        val = self.readNum(new_Xc)
        if isinstance(val,float):
            self.Xc = val
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.moveROI()
            self.moveROI2()
        self.lineEdit_Xc.setText(self.formatNum(self.Xc))
        
    def updateYc(self):
        new_Yc = str(self.lineEdit_Yc.text())
        val = self.readNum(new_Yc)
        if isinstance(val,float):
            self.Yc = val
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROI()
            self.moveROI2()
        self.lineEdit_Yc.setText(self.formatNum(self.Yc))
        
    def updateAngle(self):
        new_Angle = str(self.lineEdit_Angle.text())
        val = self.readNum(new_Angle)
        if isinstance(val,float):
            self.angle = val
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROI()
            self.moveROI2()
        self.lineEdit_Angle.setText(self.formatNum(self.angle))
        
    def updateH(self):
        new_H = str(self.lineEdit_H.text())
        val = self.readNum(new_H)
        if isinstance(val,float):
            self.H = val
            if self.FrameLocked:
                self.W = self.H
                self.lineEdit_W.setText(self.formatNum(self.W))
                self.updateSpeed()
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROI()
            self.moveROI2()
        self.lineEdit_H.setText(self.formatNum(self.H))
            
    def updateW(self):
        new_W = str(self.lineEdit_W.text())
        val = self.readNum(new_W)
        if isinstance(val,float):
            self.W = val
            if self.FrameLocked:
                self.H = self.W
                self.lineEdit_H.setText(self.formatNum(self.H))
            self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            self.moveROI()
            self.moveROI2()
            self.updateSpeed()
        self.lineEdit_W.setText(self.formatNum(self.W))
        
    def updateSpeed(self):
        if self.LinearSpeedLocked:
            self.lineTime = self.W / self.linearSpeed
            self.lineEdit_LineTime.setText(self.formatNum(self.lineTime))
            self.FrameTime = self.lines * self.lineTime
            self.lineEdit_FrameTime.setText(self.formatNum(self.FrameTime))
        else: 
            self.linearSpeed = self.W / self.lineTime
            self.lineEdit_Linear.setText(self.formatNum(self.linearSpeed))
        
    def updatePixels(self):
        new_Pixels = str(self.lineEdit_Pixels.text())
        val = self.readNum(new_Pixels)
        if isinstance(val,float):
            self.pixels = int(val)
            if self.DataLocked:
                self.lines = int(val/self.PixelsAspectRatio)
                self.lineEdit_Lines.setText(self.formatNum(self.lines))
                self.FrameTime = self.lines * self.lineTime
                self.lineEdit_FrameTime.setText(self.formatNum(self.FrameTime))
            else:
                self.PixelsAspectRatio = float(self.pixels)/float(self.lines)
        self.lineEdit_Pixels.setText(self.formatNum(self.pixels))
        
    def updateLines(self):
        new_Lines = str(self.lineEdit_Lines.text())
        val = self.readNum(new_Lines)
        if isinstance(val,float):
            self.lines = int(val)
            if self.DataLocked:
                self.pixels = int(val*self.PixelsAspectRatio)
                self.lineEdit_Pixels.setText(self.formatNum(self.pixels))
            else:
                self.PixelsAspectRatio = float(self.pixels)/float(self.lines)
            self.FrameTime = self.lines * self.lineTime
            self.lineEdit_FrameTime.setText(self.formatNum(self.FrameTime))
        self.lineEdit_Lines.setText(self.formatNum(self.lines))
        
    def updateLinearSpeed(self):
        new_LinearSpeed = str(self.lineEdit_Linear.text())
        val = self.readNum(new_LinearSpeed)
        if isinstance(val,float):
            self.linearSpeed = val
            self.lineTime = self.W/self.linearSpeed
            self.lineEdit_LineTime.setText(self.formatNum(self.lineTime))
            self.FrameTime = self.lineTime * self.lines
            self.lineEdit_FrameTime.setText(self.formatNum(self.FrameTime))
        self.lineEdit_Linear.setText(self.formatNum(self.linearSpeed))
        
    def updateLineTime(self):
        new_LineTime = str(self.lineEdit_LineTime.text())
        val = self.readNum(new_LineTime)
        if isinstance(val,float):
            self.lineTime = val
            self.linearSpeed = self.W/self.lineTime
            self.lineEdit_Linear.setText(self.formatNum(self.linearSpeed))
            self.FrameTime = self.lineTime * self.lines
            self.lineEdit_FrameTime.setText(self.formatNum(self.FrameTime))
        self.lineEdit_LineTime.setText(self.formatNum(self.lineTime))
        
#----------------------------------------------------------------------------------------------#      
    """ The following section has test functions."""  
        
    def testUpdates(self):
        self.currAngle = self.angle
        self.currXc = self.Xc
        self.currYc = self.Yc
        self.currW = self.W
        self.currH = self.H
        
        if self.scanCoordinates:
            self.moveROI()
        self.update_data()

        #timer = QtCore.QTimer(self)
        #timer.timeout.connect(self.update_gph)
        #timer.start(2000)
        
    @inlineCallbacks
    def update_data(self):
        self.pxsize = (self.lines,self.pixels)
        extent = [self.x,self.x+self.W,self.y,self.y+self.H]
        self.data = np.zeros(self.pxsize)
        self.x0, x1 = (extent[0], extent[1])
        self.y0, y1 = (extent[2], extent[3])
        self.xscale, self.yscale = self.W / self.lines, self.H / self.pixels
        self.update_gph()
        for i in range(0,self.lines):
            yield self.sleep(self.lineTime)
            newData = np.random.rand(self.pixels) + 3 + 2*np.linspace(0,1,self.pixels) + 5*np.linspace(0,1,self.pixels)**2
            newProcessedData = self.processData(newData)
            self.data[:,i] = newProcessedData
            self.update_gph()
                
    def update_gph(self):
        self.Plot2D.setImage(self.data, autoRange = False, autoLevels = False)
        self.Plot2D.imageItem.resetTransform()
        if self.scanCoordinates:
            angle = 0
            tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
            #self.Plot2D.imageItem.setPos(-self.W/2+self.Xc,-self.H/2+self.Yc)
            self.Plot2D.imageItem.setPos(-self.currW/2,-self.currH/2)
            self.Plot2D.imageItem.setTransform(tr)
        else: 
            angle = self.currAngle
            tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
            self.Plot2D.imageItem.setPos(self.x0,self.y0)
            self.Plot2D.imageItem.setTransform(tr)
        
        self.MiniPlot2D.setImage(self.data, autoRange = False, autoLevels = False)
        self.MiniPlot2D.imageItem.resetTransform()
        angle = self.currAngle
        tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
        self.MiniPlot2D.imageItem.setPos(self.x0,self.y0)
        self.MiniPlot2D.imageItem.setTransform(tr)
        
    def processData(self, lineData):
        if self.dataProcessing == 'Raw':
            return lineData 
        elif self.dataProcessing == 'Subtract Average':
            x = np.linspace(0,self.pixels-1,self.pixels)
            fit = np.polyfit(x, lineData, 0)
            residuals  = lineData - fit[0]
            return residuals
        elif self.dataProcessing == 'Subtract Linear Fit':
            x = np.linspace(0,self.pixels-1,self.pixels)
            fit = np.polyfit(x, lineData, 1)
            residuals  = lineData - fit[0]*x - fit[1]
            return residuals
        elif self.dataProcessing == 'Subtract Parabolic Fit':
            x = np.linspace(0,self.pixels-1,self.pixels)
            fit = np.polyfit(x, lineData, 2)
            residuals  = lineData - fit[0]*x**2 - fit[1]*x - fit[2]
            return residuals
            
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
        
        