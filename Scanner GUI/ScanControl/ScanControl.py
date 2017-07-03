import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks
import twisted
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading

path = sys.path[0] + r"\ScanControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\ScanControlWindow.ui")

'''
THINGS TO DO:
Make sure no scan more than maximum area
Fix linewidth to be constant number of pixels instead of bullshit variable stuff it does now
'''

class MultiLine(pg.QtGui.QGraphicsPathItem):
    def __init__(self, x, y):
        """x and y are 2D arrays of shape (Nplots, Nsamples)"""
        connect = np.ones(x.shape, dtype=bool)
        connect[:,-1] = 0 # don't draw the segment between each trace
        self.path = pg.arrayToQPath(x.flatten(), y.flatten(), connect.flatten())
        pg.QtGui.QGraphicsPathItem.__init__(self, self.path)
        self.setPen(pg.mkPen('w'))
    def shape(self): # override because QGraphicsPathItem.shape is too expensive.
        return pg.QtGui.QGraphicsItem.shape(self)
    def boundingRect(self):
        return self.path.boundingRect()

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.moveDefault()
        
        self.setupScanningArea()
        
        self.FrameLocked = True
        self.LinearSpeedLocked = False
        self.DataLocked = True
        
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
        self.push_Test.clicked.connect(self.testUpdates)
        self.lineEdit_Xc.editingFinished.connect(self.updateXc)
        self.lineEdit_Yc.editingFinished.connect(self.updateYc)
        self.lineEdit_H.editingFinished.connect(self.updateH)
        self.lineEdit_W.editingFinished.connect(self.updateW)
        self.lineEdit_Angle.editingFinished.connect(self.updateAngle)
        self.lineEdit_Pixels.editingFinished.connect(self.updatePixels)
        self.lineEdit_Lines.editingFinished.connect(self.updateLines)
        self.lineEdit_LineTime.editingFinished.connect(self.updateLineTime)
        self.lineEdit_Linear.editingFinished.connect(self.updateLinearSpeed)
        
        #Connect click and drag of scan frame area for both the main and the miniplot
        self.view.newCenterSig.connect(self.updateCenter)
        self.view.newAngleSig.connect(self.updateAngle)
        self.view.newSizeSig.connect(self.updateSize)
        self.view.scanAdjustmentDone.connect(self.finishScanAdjustment)
        self.view2.newCenterSig.connect(self.updateCenter)
        self.view2.newAngleSig.connect(self.updateAngle)
        self.view2.newSizeSig.connect(self.updateSize)
        self.view2.scanAdjustmentDone.connect(self.finishScanAdjustment)
        
    def moveDefault(self):    
        self.move(550,10)
            
    def testUpdates(self):
        self.pxsize = (2000,2000)
        self.extent = [-1e-5,1e-5,-1e-5,1e-5]
        self.dy = np.random.rand(self.pxsize[0],self.pxsize[1])
        self.dx = np.empty((2000,2000))
        self.dx[:] = np.arange(2000)[np.newaxis,:]
        self.DX = MultiLine(self.dx, self.dy)
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.update_gph)
        timer.start(2000)
        
    def update_gph(self):
        now = pg.ptime.time()
        print "Data creation time: %0.2f sec" % (pg.ptime.time()-now)
        x0, x1 = (self.extent[0], self.extent[1])
        y0, y1 = (self.extent[2], self.extent[3])
        xscale, yscale = 1.0*(x1-x0) / self.dx.shape[0], 1.0 * (y1-y0) / self.dx.shape[1]
        print "Scale time: %0.2f sec" % (pg.ptime.time()-now)
        self.Plot2D.setImage(self.DX, autoRange = False, autoLevels = True, pos=[x0, y0],scale=[xscale, yscale])
        print "Set image: %0.2f sec" % (pg.ptime.time()-now)
        #self.Plot2DThreaded.updatePlot(self.dx,self.extent)
        self.Plot2D.show()
        print "Show: %0.2f sec" % (pg.ptime.time()-now)
        
    def setupAdditionalUi(self):
        #Set up main plot
        self.view = plotEnvironment(name="Magnetic Field")
        self.view.setLabel('left',text='Y position',units = 'm')
        self.view.setLabel('right',text='Y position',units = 'm')
        self.view.setLabel('top',text='X position',units = 'm')
        self.view.setLabel('bottom',text='X position',units = 'm')
        self.Plot2D = pg.ImageView(parent = self.background, view = self.view)
        self.view.invertY(False)
        self.Plot2D.setGeometry(QtCore.QRect(240, 90, 750, 650))
        self.Plot2D.ui.roiBtn.hide()
        self.Plot2D.ui.menuBtn.hide()
        self.Plot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        self.Plot2D.lower()
        self.PlotArea.lower()
        
        self.pxsize = (256,256)
        self.extent = [-1e-5,1e-5,-1e-5,1e-5]
        self.dx = np.zeros(self.pxsize)
        x0, x1 = (self.extent[0], self.extent[1])
        y0, y1 = (self.extent[2], self.extent[3])
        xscale, yscale = 1.0*(x1-x0) / self.dx.shape[0], 1.0 * (y1-y0) / self.dx.shape[1]
        self.Plot2D.setImage(self.dx, pos=[x0, y0],scale=[xscale, yscale])
        #self.Plot2DThreaded = PlotThread(self.Plot2D,self.dx,self.extent,self)
        self.Plot2D.show()
        
        #Set up mini plot for maximum scan range
        self.view2 = plotEnvironment(name='Full Scan Range')
        self.view2.setLabel('left',text='Y position',units = 'm')
        self.view2.setLabel('right',text='Y position',units = 'm')
        self.view2.setLabel('top',text='X position',units = 'm')
        self.view2.setLabel('bottom',text='X position',units = 'm')
        self.MiniPlot2D = pg.ImageView(parent = self.background, view = self.view2)
        self.view2.invertY(False)
        self.MiniPlot2D.setGeometry(QtCore.QRect(5, 500, 228, 228))
        self.MiniPlot2D.ui.roiBtn.hide()
        self.MiniPlot2D.ui.menuBtn.hide()
        self.MiniPlot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        self.MiniPlot2D.ui.histogram.hide()
        self.view2.setMouseEnabled(False,False)
        self.MiniPlot2D.lower()
        self.MiniPlotArea.lower()
        
        x0, x1 = (-15e-6, 15e-6)
        y0, y1 = (-15e-6, 15e-6)
        dx = np.zeros((100,100))
        xscale, yscale = 1.0*(x1-x0) / dx.shape[0], 1.0 * (y1-y0) / dx.shape[1]
        self.MiniPlot2D.setImage(dx, autoRange = False, pos=[x0, y0],scale=[xscale, yscale])
        self.view2.setAspectLocked(False)
        self.view2.setXRange(-15e-6,15e-6,0)
        self.view2.setYRange(-15e-6,15e-6,0)
        self.view2.hideButtons()
        self.view2.setMenuEnabled(False)
        self.MiniPlot2D.show()

    def setupScanningArea(self):
        self.Xc = 0
        self.Yc = 0
        self.H = 5e-6
        self.W = 5e-6
        self.Angle = 0
        
        self.FrameAspectRatio = 1.0
        #Because once data rotates, don't want to deal with plotting rotated data. 
        self.currAngle = 0
        
        self.updatePoints()
            
        pen = QtGui.QPen(QtGui.QColor(200, 0, 0), 2.5e-7, QtCore.Qt.SolidLine) 
        
        self.line1 = QtGui.QGraphicsLineItem(self.topLeft[0], self.topLeft[1], self.topRight[0], self.topRight[1])
        self.line2 = QtGui.QGraphicsLineItem(self.topLeft[0], self.topLeft[1], self.bottomLeft[0], self.bottomLeft[1])
        self.line3 = QtGui.QGraphicsLineItem(self.topRight[0], self.topRight[1], self.bottomRight[0], self.bottomRight[1])
        self.line4 = QtGui.QGraphicsLineItem(self.bottomLeft[0], self.bottomRight[1], self.bottomRight[0], self.bottomRight[1])
        
        self.line1.setPen(pen)
        self.line2.setPen(pen)
        self.line3.setPen(pen)
        self.line4.setPen(pen)
        
        self.view.addItem(self.line1)
        self.view.addItem(self.line2)
        self.view.addItem(self.line3)
        self.view.addItem(self.line4)
        
        #Miniplot
        self.miniLine1 = QtGui.QGraphicsLineItem(self.topLeft[0], self.topLeft[1], self.topRight[0], self.topRight[1])
        self.miniLine2 = QtGui.QGraphicsLineItem(self.topLeft[0], self.topLeft[1], self.bottomLeft[0], self.bottomLeft[1])
        self.miniLine3 = QtGui.QGraphicsLineItem(self.topRight[0], self.topRight[1], self.bottomRight[0], self.bottomRight[1])
        self.miniLine4 = QtGui.QGraphicsLineItem(self.bottomLeft[0], self.bottomRight[1], self.bottomRight[0], self.bottomRight[1])
        
        pen = QtGui.QPen(QtGui.QColor(200, 0, 0), 5e-7, QtCore.Qt.SolidLine) 
        
        self.miniLine1.setPen(pen)
        self.miniLine2.setPen(pen)
        self.miniLine3.setPen(pen)
        self.miniLine4.setPen(pen)
        
        self.view2.addItem(self.miniLine1)
        self.view2.addItem(self.miniLine2)
        self.view2.addItem(self.miniLine3)
        self.view2.addItem(self.miniLine4)
        
    #----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to buttons on the Scan Control window."""
        
    def toggleFrameLock(self):
        if self.FrameLocked == True:
            self.push_FrameLock.setStyleSheet("#push_FrameLock{"+
            "image:url(:/nSOTScanner/Pictures/unlock.png);background: black;}")
            self.FrameLocked = False
        else:
            self.push_FrameLock.setStyleSheet("#push_FrameLock{"+
            "image:url(:/nSOTScanner/Pictures/lock.png);background: black;}")
            self.FrameLocked = True
            
    def toggleSpeedLock(self):
        if self.LinearSpeedLocked == False:
            self.push_SpeedLock.move(170,279)
            self.LinearSpeedLocked = True
        else:
            self.push_SpeedLock.move(170,309)
            self.LinearSpeedLocked = False
            
    def toggleDataLock(self):
        if self.DataLocked == True:
            self.push_DataLock.setStyleSheet("#push_DataLock{"+
            "image:url(:/nSOTScanner/Pictures/unlock.png);background: black;}")
            self.DataLocked = False
        else:
            self.push_DataLock.setStyleSheet("#push_DataLock{"+
            "image:url(:/nSOTScanner/Pictures/lock.png);background: black;}")
            self.DataLocked = True
    #----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to drawing the scanning square."""
    def updatePoints(self):
        #needs to include angle calculation
        dispAngle = self.Angle - self.currAngle
        sin = np.sin(dispAngle * np.pi/180)
        cos = np.cos(dispAngle * np.pi/180)
        self.topLeft = (self.Xc - self.W * cos /2 + self.H * sin / 2, self.Yc + self.H* cos /2 + self.W * sin / 2)
        self.topRight = (self.Xc + self.W * cos /2 + self.H * sin / 2, self.Yc + self.H* cos /2 - self.W * sin / 2)
        self.bottomLeft = (self.Xc - self.W* cos /2 - self.H * sin / 2, self.Yc - self.H* cos /2 + self.W * sin / 2)
        self.bottomRight = (self.Xc + self.W* cos /2 - self.H * sin / 2, self.Yc - self.H* cos /2 - self.W * sin / 2)
        
    def updateSquare(self): 
        self.updatePen()
        
        self.line1.setLine(self.topLeft[0], self.topLeft[1], self.topRight[0], self.topRight[1])
        self.line2.setLine(self.topLeft[0], self.topLeft[1], self.bottomLeft[0], self.bottomLeft[1])
        self.line3.setLine(self.topRight[0], self.topRight[1], self.bottomRight[0], self.bottomRight[1])
        self.line4.setLine(self.bottomLeft[0], self.bottomLeft[1], self.bottomRight[0], self.bottomRight[1])
        
        self.miniLine1.setLine(self.topLeft[0], self.topLeft[1], self.topRight[0], self.topRight[1])
        self.miniLine2.setLine(self.topLeft[0], self.topLeft[1], self.bottomLeft[0], self.bottomLeft[1])
        self.miniLine3.setLine(self.topRight[0], self.topRight[1], self.bottomRight[0], self.bottomRight[1])
        self.miniLine4.setLine(self.bottomLeft[0], self.bottomLeft[1], self.bottomRight[0], self.bottomRight[1])
        
    def updatePen(self):
        width = np.amin([np.abs(self.H),np.abs(self.W)])/25
        pen = QtGui.QPen(QtGui.QColor(200, 0, 0), width, QtCore.Qt.SolidLine) 
        self.line1.setPen(pen)
        self.line2.setPen(pen)
        self.line3.setPen(pen)
        self.line4.setPen(pen)
        
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
        
    def updateXc(self):
        new_Xc = str(self.lineEdit_Xc.text())
        val = self.readNum(new_Xc)
        if isinstance(val,float):
            self.Xc = val
            self.updatePoints()
            self.updateSquare()
        self.lineEdit_Xc.setText(self.formatNum(self.Xc))
            
    def updateYc(self):
        new_Yc = str(self.lineEdit_Yc.text())
        val = self.readNum(new_Yc)
        if isinstance(val,float):
            self.Yc = val
            self.updatePoints()
            self.updateSquare()
        self.lineEdit_Yc.setText(self.formatNum(self.Yc))
        
    def updateCenter(self,center):
        self.Xc = center.x()
        self.Yc = center.y()
        self.updatePoints()
        self.updateSquare()
        self.lineEdit_Xc.setText(self.formatNum(self.Xc))
        self.lineEdit_Yc.setText(self.formatNum(self.Yc))
    
    def updateH(self, diff = None):
        if diff is None:
            new_H = str(self.lineEdit_H.text())
            val = self.readNum(new_H)
        else: 
            val = self.H + diff
        if isinstance(val,float):
            if val != 0:
                self.H = val
                if self.FrameLocked:
                    self.W = val /self.FrameAspectRatio
                    self.lineEdit_W.setText(self.formatNum(np.abs(self.W)))
                    if self.LinearSpeedLocked:
                        self.lineTime = np.abs(self.W) / self.linearSpeed
                        self.lineEdit_LineTime.setText(self.formatNum(self.lineTime))
                        self.FrameTime = self.lines * self.lineTime
                        self.lineEdit_FrameTime.setText(self.formatNum(self.FrameTime))
                    else: 
                        self.linearSpeed = np.abs(self.W) / self.lineTime
                        self.lineEdit_Linear.setText(self.formatNum(self.linearSpeed))
                else:
                    self.FrameAspectRatio = np.abs(self.H)/np.abs(self.W)
                self.updatePoints()
                self.updateSquare()
        self.lineEdit_H.setText(self.formatNum(np.abs(self.H)))
        
    def updateW(self, diff = None):
        if diff is None:
            new_W = str(self.lineEdit_W.text())
            val = self.readNum(new_W)
        else: 
            val = self.W + diff
        if isinstance(val,float):
            if val != 0:
                self.W = val
                if self.FrameLocked:
                    self.H = val * self.FrameAspectRatio
                    self.lineEdit_H.setText(self.formatNum(np.abs(self.H)))
                else:
                    self.FrameAspectRatio = np.abs(self.H) / np.abs(self.W)
                if self.LinearSpeedLocked:
                    self.lineTime = np.abs(self.W) / self.linearSpeed
                    self.lineEdit_LineTime.setText(self.formatNum(self.lineTime))
                    self.FrameTime = self.lines * self.lineTime
                    self.lineEdit_FrameTime.setText(self.formatNum(self.FrameTime))
                else: 
                    self.linearSpeed = np.abs(self.W) / self.lineTime
                    self.lineEdit_Linear.setText(self.formatNum(self.linearSpeed))
                self.updatePoints()
                self.updateSquare()
        self.lineEdit_W.setText(self.formatNum(np.abs(self.W)))
        
    def updateSize(self,diff,direction):
        dir_angle = (180*np.arctan2(direction.y(),direction.x())/np.pi)
        diff_angle = (dir_angle + self.Angle)%360
        if diff_angle <= 2 or diff_angle >= 358 or 178 <= diff_angle <= 182:
            self.updateW(2*diff)
        elif 88 <= diff_angle <= 92 or 268 <= diff_angle <= 272:
            self.updateH(2*diff)
            
    def updateAngle(self, angle = None):
        if angle is None:
            new_Angle = str(self.lineEdit_Angle.text())
            val = self.readNum(new_Angle)
        else:
            val = self.Angle - angle
        if isinstance(val,float):
            self.Angle = val%360
            self.updatePoints()
            self.updateSquare()
        self.lineEdit_Angle.setText(self.formatNum(self.Angle))
        
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
        
    def finishScanAdjustment(self):
        self.W = np.abs(self.W)
        self.H = np.abs(self.H)
        
class plotEnvironment(pg.PlotItem):

    newCenterSig = QtCore.pyqtSignal(QtCore.QPointF)
    newAngleSig = QtCore.pyqtSignal(float)
    newSizeSig = QtCore.pyqtSignal(float,QtCore.QPointF)
    scanAdjustmentDone = QtCore.pyqtSignal()
    
    def __init__(self,name = None):
        super(plotEnvironment,self).__init__(title = name) 
        
    def dot(self,p1,p2):
        dot = p1.x()*p2.x() + p1.y()*p2.y()
        return dot
        
    def mouseDragEvent(self, ev):
        if ev.button() == QtCore.Qt.LeftButton or ev.button() == QtCore.Qt.RightButton:        
            #item[1] is ImageView, this maps pos to graph coordinates
            items = self.items
            
            if ev.isStart():
                # If first event since drag was started, then check if the click was on a line
                pos = ev.buttonDownPos()
                scaledPos = items[1].mapFromScene(pos)
                self.selectedLine = None
                self.lines = []
                
                for item in items:
                    # Items with type 6 are lines. 
                    if item.type() == 6:
                        self.lines.append(item)
                
                self.linePoints = []
                
                for line in self.lines:
                    if line.contains(scaledPos):
                        #If clicked on one of the lines, take note
                        self.selectedLine = line
                    self.linePoints.append(line.line())
                
                #If no lines were clicked, then ignore this event. 
                if self.selectedLine is None:
                    ev.ignore()
                    return 
                
                #Find center of the square
                self.center = QtCore.QPointF(0,0)
                for points in self.linePoints:
                    p1 = points.p1()
                    p2 = points.p2()
                    self.center = self.center + p1 + p2
                self.center = self.center / 8
                
                #Find unit vector pointing from line to center of square
                lineCoordinates = self.selectedLine.line()
                p1 = lineCoordinates.p1()
                p2 = lineCoordinates.p2()
                p_mid = (p1+p2)/2
                direction = p_mid - self.center
                self.direction = direction / np.sqrt((direction.x()**2 + direction.y()**2))
                
                #Set reference point and angle
                self.size_diff = 0
                self.dragPoint = scaledPos
                vector = scaledPos - self.center
                self.ref_angle = np.arctan2(vector.y(), vector.x()) 
                
            elif ev.isFinish():
                self.selectedLine = None
                self.scanAdjustmentDone.emit()
                return
            else:
                if self.selectedLine is None:
                    ev.ignore()
                    return
            
            pos = ev.pos()
            scaledPos = items[1].mapFromScene(pos)  
            
            self.dragOffset = scaledPos - self.dragPoint
            
            modifiers = QtGui.QApplication.keyboardModifiers() 
            if ev.button() == QtCore.Qt.LeftButton and modifiers != QtCore.Qt.ControlModifier: 
                new_center = self.center + self.dragOffset
                self.newCenterSig.emit(new_center)
            elif ev.button() == QtCore.Qt.RightButton:
                vector = scaledPos - self.center
                angle = np.arctan2(vector.y(), vector.x())
                new_angle = 180*(angle - self.ref_angle)/np.pi
                self.ref_angle = angle
                self.newAngleSig.emit(new_angle)
            elif ev.button() == QtCore.Qt.LeftButton and modifiers == QtCore.Qt.ControlModifier:  
                diff = self.dot(self.dragOffset,self.direction)
                self.newSizeSig.emit(diff - self.size_diff,self.direction)
                self.size_diff = diff
            ev.accept()
        else:
            ev.ignore()
            return

        
class PlotThread(QtCore.QThread):
    def __init__(self,ImageView, data, extent, parent = None):
        super(PlotThread,self).__init__(parent = parent)
        self.ImageView = ImageView
        self.stopMutex = threading.Lock()
        self.updateMutex = threading.Lock()
        #initialize to true so that runs the first time
        self.data = data
        self.updatePlot(data,extent)
        self._stop = False
        
    def run(self):
        while True:
            with self.updateMutex:
                if self.update:
                    self.ImageView.setImage(self.data, pos=[self.x0, self.y0],scale=[self.xscale, self.yscale])
                    self.ImageView.show()
                    self.update = False
            with self.stopMutex:
                if self._stop:
                    break
            time.sleep(0.05)
            
    def updatePlot(self,data,extent):
        with self.updateMutex:
            self.x0, x1 = (extent[0], extent[1])
            self.y0, y1 = (extent[2], extent[3])
            self.xscale, self.yscale = 1.0*(x1-self.x0) / self.data.shape[0], 1.0 * (y1-self.y0) / self.data.shape[1]
            self.update = True
            
    def stop(self):
        with self.stopMutex:
            self._stop = True
        
        
        
        