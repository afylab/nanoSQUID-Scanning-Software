import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks
import twisted
import numpy as np
import pyqtgraph as pg

path = sys.path[0]
sys.path.append(path+'\Resources')
sys.path.append(path+'\ScanControl')
sys.path.append(path+'\LabRADConnect')
sys.path.append(path+r'\nSOTCharacterizer')    
sys.path.append(path+'\DataVaultBrowser')
sys.path.append(path+'\Plotter')
sys.path.append(path+'\TFCharacterizer')
sys.path.append(path+'\ApproachModule')
sys.path.append(path+'\PLLMonitor')
sys.path.append(path+'\JPEPositionControl')

UI_path = path + r"\MainWindow.ui"
MainWindowUI, QtBaseClass = uic.loadUiType(UI_path)

#import all windows for gui
import ScanControl
import LabRADConnect
import nSOTCharacterizer
import plotter
import TFCharacterizer
import Approach
import PLLMonitor
import JPEControl

import exceptions

class MainWindow(QtGui.QMainWindow, MainWindowUI):
            
    """ The following section initializes, or defines the initialization of the GUI and 
    connecting to servers."""
    def __init__(self, reactor, parent=None):
        """ nSOT Scanner GUI """
        
        super(MainWindow, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        
        #Move to default position
        self.moveDefault()
        
        #Intialize all widgets. 
        self.SC = ScanControl.Window(self.reactor, None)
        self.LabRAD = LabRADConnect.Window(self.reactor, None)
        self.nSOTChar = nSOTCharacterizer.Window(self.reactor, None)
        self.Plot = plotter.Plotter(self.reactor, None)
        self.TFChar = TFCharacterizer.Window(self.reactor, None)
        self.Approach = Approach.Window(self.reactor, None)
        self.PLLMonitor = PLLMonitor.Window(self.reactor, None)
        self.JPEControl = JPEControl.Window(self.reactor, None)
        
        #Connects all drop down menu button
        self.actionScan_Control.triggered.connect(self.openScanControlWindow)
        self.actionLabRAD_Connect.triggered.connect(self.openLabRADConnectWindow)
        self.actionnSOT_Characterizer.triggered.connect(self.opennSOTCharWindow)
        self.actionData_Plotter.triggered.connect(self.openDataPlotter)
        self.actionTF_Characterizer.triggered.connect(self.openTFCharWindow)
        self.actionApproach_Control.triggered.connect(self.openApproachWindow)
        self.actionPLL_Monitor.triggered.connect(self.openPLLMonitorWindow)
        self.actionJPE_Coarse_Position_Control.triggered.connect(self.openJPEControlWindow)

        #Connectors all layout buttons
        self.push_Layout1.clicked.connect(self.setLayout1)
        
        self.push_Logo.clicked.connect(self.toggleLogo)
        self.isRedEyes = False
        
        #Connect 
        self.LabRAD.cxnSuccessful.connect(self.distributeLabRADConnections)
        self.LabRAD.cxnDisconnected.connect(self.disconnectLabRADConnections)
        
        self.TFChar.workingPointSelected.connect(self.distributeWorkingPoint)

        self.Approach.newPLLData.connect(self.updatePLLMonitor)
        
        #Open by default the LabRAD Connect Module
        self.openLabRADConnectWindow()
        
    def setupAdditionalUi(self):
        """Some UI elements would not set properly from Qt Designer. These initializations are done here."""
        self.push_Layout1.setToolTip('Loads and repositions Scan Control and' +
        'Main Window. Closes the rest.')
        
    #----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to default opening windows."""
    
    def moveDefault(self):
        self.move(10,10)
    
    def openScanControlWindow(self):
        self.SC.moveDefault()
        self.SC.raise_()
        if self.SC.isVisible() == False:
            self.SC.show()
            
    def openLabRADConnectWindow(self):
        self.LabRAD.moveDefault()
        self.LabRAD.raise_()
        if self.LabRAD.isVisible() == False:
            self.LabRAD.show()
            
    def opennSOTCharWindow(self):
        self.nSOTChar.moveDefault()
        self.nSOTChar.raise_()
        if self.nSOTChar.isVisible() == False:
            self.nSOTChar.show()
            
    def openDataPlotter(self):
        self.Plot.moveDefault()
        self.Plot.raise_()
        if self.Plot.isVisible() == False:
            self.Plot.show()
            
    def openTFCharWindow(self):
        self.TFChar.moveDefault()
        self.TFChar.raise_()
        if self.TFChar.isVisible() == False:
            self.TFChar.show()
    
    def openApproachWindow(self):
        self.Approach.moveDefault()
        self.Approach.raise_()
        if self.Approach.isVisible() == False:
            self.Approach.show()

    def openPLLMonitorWindow(self):
        self.PLLMonitor.moveDefault()
        self.PLLMonitor.raise_()
        if self.PLLMonitor.isVisible() == False:
            self.PLLMonitor.show()
            
    def openJPEControlWindow(self):
        self.JPEControl.moveDefault()
        self.JPEControl.raise_()
        if self.JPEControl.isVisible() == False:
            self.JPEControl.show()
#----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to passing LabRAD connections."""
    
    def distributeLabRADConnections(self,dict):
        self.Plot.connectLabRAD(dict)
        self.nSOTChar.connectLabRAD(dict)
        self.SC.connectLabRAD(dict)
        self.TFChar.connectLabRAD(dict)
        self.Approach.connectLabRAD(dict)
        self.JPEControl.connectLabRAD(dict)
        
    def disconnectLabRADConnections(self,dict):
        self.Plot.disconnectLabRAD()
        self.nSOTChar.disconnectLabRAD()
        self.SC.disconnectLabRAD()
        self.TFChar.disconnectLabRAD()
        self.Approach.disconnectLabRAD()
        self.JPEControl.disconnectLabRAD()

#----------------------------------------------------------------------------------------------#
            
    """ The following section connects signals between various modules."""

    def distributeWorkingPoint(self,freq, phase, channel, amplitude):
        self.Approach.setWorkingPoint(freq, phase, channel, amplitude)

    def updatePLLMonitor(self, deltaF, phaseError):
        self.PLLMonitor.updatePlots(deltaF, phaseError)
        
#----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to setting the default layouts."""
        
    def setLayout1(self):
        self.moveDefault()
        self.hideAllWindows()
        self.openScanControlWindow()
        self.openApproachWindow()
        
    def toggleLogo(self):
        if self.isRedEyes == False:
            self.push_Logo.setStyleSheet("#push_Logo{"+
            "image:url(:/nSOTScanner/Pictures/SQUIDRotated.png);background: black;}")
            self.isRedEyes = True
        else:
            self.push_Logo.setStyleSheet("#push_Logo{"+
            "image:url(:/nSOTScanner/Pictures/SQUIDRotated2.png);background: black;}")
            self.isRedEyes = False
            
    def hideAllWindows(self):
        self.SC.hide()
        self.LabRAD.hide()
        self.nSOTChar.hide()
        self.Plot.hide()
        self.TFChar.hide()
        self.Approach.hide()
        self.PLLMonitor.hide()
        self.JPEControl.hide()
            
    def closeEvent(self, e):
        self.SC.close()
        self.nSOTChar.close()
        self.Plot.close()
        self.TFChar.close()
        self.Approach.close()
        self.LabRAD.disconnectLabRAD()
        self.LabRAD.close()
        self.PLLMonitor.close()
        self.JPEControl.close()
        
#----------------------------------------------------------------------------------------------#     
""" The following runs the GUI"""

if __name__=="__main__":
    import qt4reactor
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install()
    from twisted.internet import reactor
    window = MainWindow(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())

