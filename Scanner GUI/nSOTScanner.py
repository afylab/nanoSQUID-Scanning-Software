import sys
from PyQt4 import Qt, QtGui, QtCore, uic
import time 
import ctypes
myappid = 'YoungLab.nSOTScannerSoftware'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

path = sys.path[0]
sys.path.append(path+'\Resources')
sys.path.append(path+'\ScanControl')
sys.path.append(path+'\LabRADConnect')
sys.path.append(path+r'\nSOTCharacterizer')    
sys.path.append(path+'\DataVaultBrowser')
sys.path.append(path+'\Plotter')
sys.path.append(path+'\TFCharacterizer')
sys.path.append(path+'\ApproachModule')
sys.path.append(path+'\ApproachMonitor')
sys.path.append(path+'\JPEPositionControl')
sys.path.append(path+'\PositionCalibration')
sys.path.append(path+'\Field Control')
sys.path.append(path+'\ScriptingModule')
sys.path.append(path+'\TemperatureControl')
sys.path.append(path+'\QRreader')
sys.path.append(path+'\GoToSetpoint')
sys.path.append(path+'\DeviceSelect')

UI_path = path + r"\MainWindow.ui"
MainWindowUI, QtBaseClass = uic.loadUiType(UI_path)

#import all windows for gui
import ScanControl
import LabRADConnect
import nSOTCharacterizer
import plotter
import TFCharacterizer
import Approach
import ApproachMonitor
import JPEControl
import PositionCalibration
import FieldControl
import Scripting
import TemperatureControl
import QRreader
import gotoSetpoint
import DeviceSelect

import exceptions

class MainWindow(QtGui.QMainWindow, MainWindowUI):
    test = 0
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
        self.ScanControl = ScanControl.Window(self.reactor, None)
        self.LabRAD = LabRADConnect.Window(self.reactor, None)
        self.DeviceSelect = DeviceSelect.Window(self.reactor, None)
        self.nSOTChar = nSOTCharacterizer.Window(self.reactor, None)
        self.Plot = plotter.Plotter(self.reactor, None)
        self.TFChar = TFCharacterizer.Window(self.reactor, None)
        self.Approach = Approach.Window(self.reactor, None)
        self.ApproachMonitor = ApproachMonitor.Window(self.reactor, None)
        self.JPEControl = JPEControl.Window(self.reactor, None)
        self.PosCalibration = PositionCalibration.Window(self.reactor, None)
        self.FieldControl = FieldControl.Window(self.reactor, None)
        self.TempControl = TemperatureControl.Window(self.reactor,None)
        self.QRreader = QRreader.Window(self.reactor,None)
        self.GoToSetpoint = gotoSetpoint.Window(self.reactor, None)
        
        #This module should always be initialized last, and have the modules
        #That are desired to be scriptable be input
        self.Scripting = Scripting.Window(self.reactor, None, self.ScanControl, self.Approach, 
                                          self.JPEControl, self.nSOTChar, self.FieldControl, self.TempControl)
        
        #Connects all drop down menu button
        self.actionScan_Control.triggered.connect(self.openScanControlWindow)
        self.actionLabRAD_Connect.triggered.connect(self.openLabRADConnectWindow)
        self.actionnSOT_Characterizer.triggered.connect(self.opennSOTCharWindow)
        self.actionData_Plotter.triggered.connect(self.openDataPlotter)
        self.actionTF_Characterizer.triggered.connect(self.openTFCharWindow)
        self.actionApproach_Control.triggered.connect(self.openApproachWindow)
        self.actionApproach_Monitor.triggered.connect(self.openApproachMonitorWindow)
        self.actionJPE_Coarse_Position_Control.triggered.connect(self.openJPEControlWindow)
        self.actionAttocube_Position_Calibration.triggered.connect(self.openPosCalibrationWindow)
        self.actionMagnetic_Field_Control.triggered.connect(self.openFieldControlWindow)
        self.actionRun_Scripts.triggered.connect(self.openScriptingModule)
        self.actionTemperature_Control.triggered.connect(self.openTempControlWindow)
        self.actionQR_Reader.triggered.connect(self.openQRreaderWindow)
        self.actionNSOT_Setpoint.triggered.connect(self.openSetpointWindow)
        self.actionDevice_Select.triggered.connect(self.openDeviceSelectWindow)
        
        #Connectors all layout buttons
        self.push_Layout1.clicked.connect(self.setLayout1)
        
        self.push_Logo.clicked.connect(self.toggleLogo)
        self.isRedEyes = False
        
        #Connect signals between modules
        #When LabRAD Connect module emits all the local and remote labRAD connections, it goes to the device
        #select module. This module selects appropriate devices for things. That is then emitted and is distributed
        #among all the other modules
        self.LabRAD.cxnLocal.connect(self.DeviceSelect.connectLabRAD)
        self.LabRAD.cxnRemote.connect(self.DeviceSelect.connectRemoteLabRAD)
        self.DeviceSelect.newDeviceInfo.connect(self.distributeDeviceInfo)
        
        self.LabRAD.cxnDisconnected.connect(self.disconnectLabRADConnections)
        self.LabRAD.newSessionFolder.connect(self.distributeSessionFolder)
        
        self.TFChar.workingPointSelected.connect(self.distributeWorkingPoint)

        self.Approach.newPLLData.connect(self.ApproachMonitor.updatePLLPlots)
        self.Approach.newFdbkDCData.connect(self.ApproachMonitor.updateFdbkDCPlot)
        self.Approach.newFdbkACData.connect(self.ApproachMonitor.updateFdbkACPlot)
        self.Approach.newZData.connect(self.ApproachMonitor.updateZPlot)
        
        self.Approach.updateFeedbackStatus.connect(self.ScanControl.updateFeedbackStatus)
        self.Approach.updateConstantHeightStatus.connect(self.ScanControl.updateConstantHeightStatus)
        self.Approach.updateApproachStatus.connect(self.JPEControl.updateApproachStatus)
        self.Approach.updateJPEConnectStatus.connect(self.JPEControl.updateJPEConnected)
        
        self.PosCalibration.newTemperatureCalibration.connect(self.setVoltageCalibration)
        
        self.ScanControl.updateScanningStatus.connect(self.Approach.updateScanningStatus)

        self.JPEControl.newJPESettings.connect(self.Approach.updateJPESettings)
        self.JPEControl.updateJPEConnectStatus.connect(self.Approach.updateJPEConnected)
        
        self.nSOTChar.changedConnectionSettings.connect(self.GoToSetpoint.updateSetpointSettings)
        
        #Make sure default calibration is emitted 
        self.PosCalibration.emitCalibration()
        
        #Make sure default session flder is emitted
        self.LabRAD.newSessionFolder.emit(self.LabRAD.session_2)

        #Make sure default wiring connections and settings are emitted (eventually this will be a centralized window taking care of it)
        self.nSOTChar.changedConnectionSettings.emit(self.nSOTChar.settingsDict)
        
        #Open by default the LabRAD Connect Module and Device Select
        self.openLabRADConnectWindow()
        self.openDeviceSelectWindow()
        
        
    def setupAdditionalUi(self):
        """Some UI elements would not set properly from Qt Designer. These initializations are done here."""
        pass
        
    #----------------------------------------------------------------------------------------------#
            
    """ The following section connects actions related to default opening windows."""
    
    def moveDefault(self):
        self.move(10,10)
    
    def openScanControlWindow(self):
        self.ScanControl.showNormal()
        self.ScanControl.moveDefault()
        self.ScanControl.raise_()
        
    def openLabRADConnectWindow(self):
        self.LabRAD.showNormal()
        self.LabRAD.moveDefault()
        self.LabRAD.raise_()

    def opennSOTCharWindow(self):
        self.nSOTChar.showNormal()
        self.nSOTChar.moveDefault()
        self.nSOTChar.raise_()
            
    def openDataPlotter(self):
        self.Plot.showNormal()
        self.Plot.moveDefault()
        self.Plot.raise_()
            
    def openTFCharWindow(self):
        self.TFChar.showNormal()
        self.TFChar.moveDefault()
        self.TFChar.raise_()
    
    def openApproachWindow(self):
        self.Approach.showNormal()
        self.Approach.moveDefault()
        self.Approach.raise_()
            
    def openApproachMonitorWindow(self):
        self.ApproachMonitor.showNormal()
        self.ApproachMonitor.moveDefault()
        self.ApproachMonitor.raise_()
            
    def openJPEControlWindow(self):
        self.JPEControl.showNormal()
        self.JPEControl.moveDefault()
        self.JPEControl.raise_()

    def openPosCalibrationWindow(self):
        self.PosCalibration.showNormal()
        self.PosCalibration.moveDefault()
        self.PosCalibration.raise_()
            
    def openFieldControlWindow(self):
        self.FieldControl.showNormal()
        self.FieldControl.moveDefault()
        self.FieldControl.raise_()
            
    def openTempControlWindow(self):
        self.TempControl.showNormal()
        self.TempControl.moveDefault()
        self.TempControl.raise_()

    def openScriptingModule(self):
        self.Scripting.showNormal()
        self.Scripting.moveDefault()
        self.Scripting.raise_()
        
    def openQRreaderWindow(self):
        self.QRreader.showNormal()
        self.QRreader.moveDefault()
        self.QRreader.raise_()
        
    def openSetpointWindow(self):
        self.GoToSetpoint.showNormal()
        self.GoToSetpoint.moveDefault()
        self.GoToSetpoint.raise_()
        
    def openDeviceSelectWindow(self):
        self.DeviceSelect.showNormal()
        self.DeviceSelect.moveDefault()
        self.DeviceSelect.raise_()
        
#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to passing LabRAD connections."""
    
    def distributeDeviceInfo(self,dict):
        #Call connectLabRAD functions for relevant modules
        self.Plot.connectLabRAD(dict)
        self.nSOTChar.connectLabRAD(dict)
        self.ScanControl.connectLabRAD(dict)
        self.TFChar.connectLabRAD(dict)
        self.Approach.connectLabRAD(dict)
        self.JPEControl.connectLabRAD(dict)
        self.Scripting.connectLabRAD(dict)
        self.GoToSetpoint.connectLabRAD(dict)

        
    def disconnectLabRADConnections(self):
        self.DeviceSelect.disconnectLabRAD()
        self.Plot.disconnectLabRAD()
        self.nSOTChar.disconnectLabRAD()
        self.ScanControl.disconnectLabRAD()
        self.TFChar.disconnectLabRAD()
        self.Approach.disconnectLabRAD()
        self.JPEControl.disconnectLabRAD()
        self.FieldControl.disconnectLabRAD()
        self.Scripting.disconnectLabRAD()
        self.TempControl.disconnectLabRAD()
        
    def distributeSessionFolder(self, folder):
        self.TFChar.setSessionFolder(folder)
        self.ScanControl.setSessionFolder(folder)
        self.nSOTChar.setSessionFolder(folder)
        
    def updateDataVaultFolder(self):
        self.ScanControl.updateDataVaultDirectory()
        self.TFChar.updateDataVaultDirectory()
        self.nSOTChar.updateDataVaultDirectory()

#----------------------------------------------------------------------------------------------#
            
    """ The following section connects signals between various modules."""
    def distributeWorkingPoint(self,freq, phase, channel, amplitude):
        self.Approach.setWorkingPoint(freq, phase, channel, amplitude)
        
    def setVoltageCalibration(self,data):
        self.Approach.set_voltage_calibration(data)
        self.ScanControl.set_voltage_calibration(data)

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
            self.push_Logo.setToolTip('A SQUID has been hidden in every module (no exceptions). Can you find them all?')
            self.isRedEyes = True
        else:
            self.push_Logo.setStyleSheet("#push_Logo{"+
            "image:url(:/nSOTScanner/Pictures/SQUIDRotated2.png);background: black;}")
            self.push_Logo.setToolTip('')
            self.isRedEyes = False
            
    def hideAllWindows(self):
        self.ScanControl.hide()
        self.LabRAD.hide()
        self.nSOTChar.hide()
        self.Plot.hide()
        self.TFChar.hide()
        self.Approach.hide()
        self.ApproachMonitor.hide()
        self.JPEControl.hide()
        self.PosCalibration.hide()
        self.GoToSetpoint.hide()
        self.QRreader.hide()
        self.TempControl.hide()
        
            
    def closeEvent(self, e):
        try:
            self.disconnectLabRADConnections()
            self.ScanControl.close()
            self.nSOTChar.close()
            self.Plot.close()
            self.TFChar.close()
            self.Approach.close()
            self.ApproachMonitor.close()
            self.JPEControl.close()
            self.PosCalibration.close()
            self.Scripting.close()
            self.FieldControl.close()
            self.LabRAD.close()
        except Exception as inst:
            print inst
    
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

