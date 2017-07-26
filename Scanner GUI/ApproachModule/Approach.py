import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np

path = sys.path[0] + r"\ApproachModule"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\Approach.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")
Ui_advancedApproachSettings, QtBaseClass = uic.loadUiType(path + r"\advancedApproachSettings.ui")
Ui_advancedFeedbackSettings, QtBaseClass = uic.loadUiType(path + r"\advancedFeedbackSettings.ui")
Ui_MeasurementSettings, QtBaseClass = uic.loadUiType(path + r"\MeasurementSettings.ui")

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.feedback = False
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()        

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        self.push_toggleFeedback.clicked.connect(self.toggleFeedback)
        #self.push_addPhase.enterEvent.connect(self.printTest)
        
        self.push_AdvancedApproach.clicked.connect(self.showAdvancedApproach)
        self.push_AdvancedFeedback.clicked.connect(self.showAdvancedFeedback)
        self.push_MeasurementSettings.clicked.connect(self.showMeasurementSettings)
        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None
        
    def moveDefault(self):    
        self.move(10,170)
        
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
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
        
    def showAdvancedApproach(self):
        advApp = advancedApproachSettings(self.reactor, 0, self)
        advApp.exec_()
        
    def showAdvancedFeedback(self):
        advFeed = advancedFeedbackSettings(self.reactor, 0, self)
        advFeed.exec_()
        
    def showMeasurementSettings(self):
        MeasSet = MeasurementSettings(self.reactor, 0, self)
        MeasSet.exec_()
        
    def setupAdditionalUi(self):
        self.fieldSlider.close()
        self.fieldSlider = MySlider(parent = self.centralwidget)
        self.fieldSlider.setGeometry(120,85,260,70)
        self.fieldSlider.setMinimum(0)
        self.fieldSlider.setMaximum(1000)
        self.fieldSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.fieldSlider.setTickPos([1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100,200,300,400,500,600,700,800,900,1000,2000])
        self.fieldSlider.setNumPos([1,10,100,1000])
        self.fieldSlider.lower()
        
        self.tempSlider.close()
        self.tempSlider = MySlider(parent = self.centralwidget)
        self.tempSlider.setGeometry(120,150,260,70)
        self.tempSlider.setMinimum(0)
        self.tempSlider.setMaximum(1000)
        self.tempSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.tempSlider.setTickPos([1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100,200,300,400,500,600,700,800,900,1000,2000])
        self.tempSlider.setNumPos([1,10,100,1000])
        self.tempSlider.lower()
        
        self.freqSlider.close()
        self.freqSlider = MySlider(parent = self.centralwidget)
        self.freqSlider.setGeometry(120,215,260,70)
        self.freqSlider.setMinimum(0)
        self.freqSlider.setMaximum(1000)
        self.freqSlider.setStyleSheet("QSlider::groove:horizontal {border: 1px solid #bbb;background: white;height: 10px;border-radius: 4px;}QSlider::sub-page:horizontal {background: qlineargradient(x1: 0, y1: 0,    x2: 0, y2: 1,    stop: 0 #66e, stop: 1 #bbf);background: qlineargradient(x1: 0, y1: 0.2, x2: 1, y2: 1,    stop: 0 #bbf, stop: 1 #55f);border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::add-page:horizontal {background: #fff;border: 1px solid #777;height: 10px;border-radius: 4px;}QSlider::handle:horizontal {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #eee, stop:1 #ccc);border: 1px solid #777;width: 13px;margin-top: -2px;margin-bottom: -2px;border-radius: 4px;}QSlider::handle:horizontal:hover {background: qlineargradient(x1:0, y1:0, x2:1, y2:1,    stop:0 #fff, stop:1 #ddd);border: 1px solid #444;border-radius: 4px;}QSlider::sub-page:horizontal:disabled {background: #bbb;border-color: #999;}QSlider::add-page:horizontal:disabled {background: #eee;border-color: #999;}QSlider::handle:horizontal:disabled {background: #eee;border: 1px solid #aaa;border-radius: 4px;}")
        self.freqSlider.setTickPos([1,2,3,4,5,6,7,8,9,10,20,30,40,50,60,70,80,90,100,200,300,400,500,600,700,800,900,1000,2000])
        self.freqSlider.setNumPos([1,10,100,1000])
        self.freqSlider.lower()
        
    def toggleFeedback(self):
        if self.feedback:
            self.push_toggleFeedback.setText('Off')
            self.push_toggleFeedback.setStyleSheet("#push_toggleFeedback{color: rgb(168,50,50);background-color:rgb(0,0,0);border: 2px solid rgb(168,50,50);border-radius: 5px}")
            self.feedback = False
        else:
            self.push_toggleFeedback.setText('On')
            self.push_toggleFeedback.setStyleSheet("#push_toggleFeedback{color: rgb(50,168,50);background-color:rgb(0,0,0);border: 2px solid rgb(50,168,50);border-radius: 5px}")
            self.feedback = True
    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous 
    # delay that allows other labrad / pyqt methods to run   
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
    def printTest(self):
        print 'Test!'
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
        
class advancedApproachSettings(QtGui.QDialog, Ui_advancedApproachSettings):
    def __init__(self,reactor, values, parent = None):
        super(advancedApproachSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.pushButton.clicked.connect(self.acceptNewValues)
      
    def acceptNewValues(self):
        self.accept()
        
    def getValues(self):
        return "stuff"
        
class advancedFeedbackSettings(QtGui.QDialog, Ui_advancedFeedbackSettings):
    def __init__(self,reactor, values,parent = None):
        super(advancedFeedbackSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.pushButton.clicked.connect(self.acceptNewValues)
      
    def acceptNewValues(self):
        self.accept()
        
    def getValues(self):
        return "stuff"
        
class MeasurementSettings(QtGui.QDialog, Ui_MeasurementSettings):
    def __init__(self,reactor, values,parent = None):
        super(MeasurementSettings, self).__init__(parent)
        self.setupUi(self)
        
        self.pushButton.clicked.connect(self.acceptNewValues)
      
    def acceptNewValues(self):
        self.accept()
        
    def getValues(self):
        return "stuff"
        
class MySlider(QtGui.QSlider):
    #Shitty programming. Only looks good for horizontal sliders with length 400 and thickness 70. 
    def __init__(self, parent=None): 
        self.tickPos = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.numPos = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        super(MySlider, self).__init__(QtCore.Qt.Horizontal, parent)
 
    def paintEvent(self, event):
        """Paint log scale ticks"""
        super(MySlider, self).paintEvent(event)
        qp = QtGui.QPainter(self)
        pen = QtGui.QPen()
        pen.setWidth(1)
        pen.setColor(QtGui.QColor(168,168,168))
 
        qp.setPen(pen)
        font = QtGui.QFont('Times', 10)
        font_y_offset = font.pointSize()/2
        qp.setFont(font)
        size = self.size()
        contents = self.contentsRect()
        width = contents.width()
        height = contents.height()
        y = contents.y()
        max = np.log10(self.tickPos[-1])
        lower_padding = 8
        upper_padding = 16
        for val in self.tickPos:
            log_val = np.log10(val)
            x_val = round( log_val* (width-upper_padding) / max) + lower_padding
            if val in self.numPos:
                pen.setColor(QtGui.QColor(95,107,166))
                pen.setWidth(2)
                qp.setPen(pen)
                qp.drawLine(x_val , y + 45,  x_val, y+50)
                pen.setColor(QtGui.QColor(168,168,168))
                pen.setWidth(1)
                qp.setPen(pen)
                text = '{0:2}'.format(val)
                x_offset = float(len(text)*font.pointSize()/(3))
                qp.drawText(x_val - x_offset, y + 58 + font_y_offset,text)
            else:
                qp.drawLine(x_val , y + 45,  x_val, y+50)
    
    def setTickPos(self, ticks):
        self.tickPos = ticks
        
    def setNumPos(self, nums):
        self.numPos = nums
            

    