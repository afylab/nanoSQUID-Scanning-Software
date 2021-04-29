import sys
from PyQt4 import Qt, QtGui, QtCore, uic
import time 
import ctypes
myappid = 'YoungLab.nSOTScannerSoftware'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

path = sys.path[0]
sys.path.append(path + r'\Resources')
sys.path.append(path + r'\ScanControl')
sys.path.append(path + r'\LabRADConnect')
sys.path.append(path + r'\nSOTCharacterizer')    
sys.path.append(path + r'\DataVaultBrowser')
sys.path.append(path + r'\Plotters Control')
sys.path.append(path + r'\TFCharacterizer')
sys.path.append(path + r'\ApproachModule')
sys.path.append(path + r'\ApproachMonitor')
sys.path.append(path + r'\PositionCalibration')
sys.path.append(path + r'\Field Control')
sys.path.append(path + r'\ScriptingModule')
sys.path.append(path + r'\TemperatureControl')
sys.path.append(path + r'\QRreader')
sys.path.append(path + r'\SampleCharacterizer')
sys.path.append(path + r'\GoToSetpoint')
sys.path.append(path + r'\DeviceSelect')
sys.path.append(path + r'\CoarseAttocubeControl')

UI_path = path + r"\MainWindow.ui"
MainWindowUI, QtBaseClass = uic.loadUiType(UI_path)

#import all windows for gui
import ScanControl
import LabRADConnect
import nSOTCharacterizer
import PlottersControl
import TFCharacterizer
import Approach
import ApproachMonitor
import PositionCalibration
import FieldControl
import Scripting
import TemperatureControl
import QRreader
import gotoSetpoint
import DeviceSelect
import SampleCharacterizer
import CoarseAttocubeControl

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
        self.PlottersControl = PlottersControl.CommandingCenter(self.reactor, None)
        self.TFChar = TFCharacterizer.Window(self.reactor, None)
        self.Approach = Approach.Window(self.reactor, None)
        self.ApproachMonitor = ApproachMonitor.Window(self.reactor, None)
        self.PosCalibration = PositionCalibration.Window(self.reactor, None)
        self.FieldControl = FieldControl.Window(self.reactor, None)
        self.TempControl = TemperatureControl.Window(self.reactor,None)
        self.QRreader = QRreader.Window(self.reactor,None)
        self.GoToSetpoint = gotoSetpoint.Window(self.reactor, None)
        self.SampleCharacterizer = SampleCharacterizer.Window(self.reactor,None)
        self.AttocubeCoarseControl = CoarseAttocubeControl.Window(self.reactor,None)
        
        #This module should always be initialized last, and have the modules
        #That are desired to be scriptable be input
        self.Scripting = Scripting.Window(self.reactor, None, self.ScanControl, self.Approach, self.nSOTChar, self.FieldControl, self.TempControl,
                                          self.SampleCharacterizer, self.GoToSetpoint)
        
        #Connects all drop down menu button
        self.actionScan_Control.triggered.connect(self.openScanControlWindow)
        self.actionLabRAD_Connect.triggered.connect(self.openLabRADConnectWindow)
        self.actionnSOT_Characterizer.triggered.connect(self.opennSOTCharWindow)
        self.actionData_Plotter.triggered.connect(self.openDataPlotter)
        self.actionTF_Characterizer.triggered.connect(self.openTFCharWindow)
        self.actionApproach_Control.triggered.connect(self.openApproachWindow)
        self.actionApproach_Monitor.triggered.connect(self.openApproachMonitorWindow)
        self.actionAttocube_Position_Calibration.triggered.connect(self.openPosCalibrationWindow)
        self.actionMagnetic_Field_Control.triggered.connect(self.openFieldControlWindow)
        self.actionRun_Scripts.triggered.connect(self.openScriptingModule)
        self.actionTemperature_Control.triggered.connect(self.openTempControlWindow)
        self.actionQR_Reader.triggered.connect(self.openQRreaderWindow)
        self.actionNSOT_Setpoint.triggered.connect(self.openSetpointWindow)
        self.actionDevice_Select.triggered.connect(self.openDeviceSelectWindow)
        self.actionSample_Characterizer.triggered.connect(self.openSampleCharacterizerWindow)
        self.actionAttocube_Coarse_Position_Control.triggered.connect(self.openAttocubeCoarseControlWindow)

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

        self.nSOTChar.newToeField.connect(self.FieldControl.updateToeField)

        self.Approach.newPLLData.connect(self.ApproachMonitor.updatePLLPlots)
        self.Approach.newAux2Data.connect(self.ApproachMonitor.updateAux2Plot)
        self.Approach.newZData.connect(self.ApproachMonitor.updateZPlot)
        
        self.Approach.updateFeedbackStatus.connect(self.ScanControl.updateFeedbackStatus)
        self.Approach.updateConstantHeightStatus.connect(self.ScanControl.updateConstantHeightStatus)
        
        self.PosCalibration.newTemperatureCalibration.connect(self.setVoltageCalibration)
        
        self.ScanControl.updateScanningStatus.connect(self.Approach.updateScanningStatus)
        
        #Make sure default calibration is emitted 
        self.PosCalibration.emitCalibration()
        
        #Make sure default session flder is emitted
        self.LabRAD.newSessionFolder.emit(self.LabRAD.session_2)
        
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
        self.PlottersControl.showNormal()
        self.PlottersControl.moveDefault()
        self.PlottersControl.raise_()
            
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

    def openSampleCharacterizerWindow(self):
        self.SampleCharacterizer.showNormal()
        self.SampleCharacterizer.moveDefault()
        self.SampleCharacterizer.raise_()

    def openAttocubeCoarseControlWindow(self):
        self.AttocubeCoarseControl.showNormal()
        self.AttocubeCoarseControl.moveDefault()
        self.AttocubeCoarseControl.raise_()
        
#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to passing LabRAD connections."""
    
    def distributeDeviceInfo(self,dic):
        #Call connectLabRAD functions for relevant modules
        self.PlottersControl.connectLabRAD(dic)
        self.nSOTChar.connectLabRAD(dic)
        self.ScanControl.connectLabRAD(dic)
        self.TFChar.connectLabRAD(dic)
        self.Approach.connectLabRAD(dic)
        self.Scripting.connectLabRAD(dic)
        self.GoToSetpoint.connectLabRAD(dic)
        self.FieldControl.connectLabRAD(dic)
        self.TempControl.connectLabRAD(dic)
        self.SampleCharacterizer.connectLabRAD(dic)
        self.AttocubeCoarseControl.connectLabRAD(dic)

    def disconnectLabRADConnections(self):
        self.DeviceSelect.disconnectLabRAD()
        self.PlottersControl.disconnectLabRAD()
        self.nSOTChar.disconnectLabRAD()
        self.ScanControl.disconnectLabRAD()
        self.TFChar.disconnectLabRAD()
        self.Approach.disconnectLabRAD()
        self.FieldControl.disconnectLabRAD()
        self.Scripting.disconnectLabRAD()
        self.TempControl.disconnectLabRAD()
        self.SampleCharacterizer.disconnectLabRAD()
        self.AttocubeCoarseControl.disconnectLabRAD()

    def distributeSessionFolder(self, folder):
        self.TFChar.setSessionFolder(folder)
        self.ScanControl.setSessionFolder(folder)
        self.nSOTChar.setSessionFolder(folder)
        self.SampleCharacterizer.setSessionFolder(folder)

    def updateDataVaultFolder(self):
        self.ScanControl.updateDataVaultDirectory()
        self.TFChar.updateDataVaultDirectory()
        self.nSOTChar.updateDataVaultDirectory()
        self.SampleCharacterizer.updateDataVaultDirectory()

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
        self.PlottersControl.hide()
        self.TFChar.hide()
        self.Approach.hide()
        self.ApproachMonitor.hide()
        self.PosCalibration.hide()
        self.GoToSetpoint.hide()
        self.QRreader.hide()
        self.TempControl.hide()
        self.SampleCharacterizer.hide()
        self.AttocubeCoarseControl.hide()
            
    def closeEvent(self, e):
        try:
            self.disconnectLabRADConnections()
            self.ScanControl.close()
            self.nSOTChar.close()
            self.PlottersControl.close()
            self.TFChar.close()
            self.Approach.close()
            self.ApproachMonitor.close()
            self.PosCalibration.close()
            self.Scripting.close()
            self.FieldControl.close()
            self.LabRAD.close()
            self.SampleCharacterizer.close()
            self.AttocubeCoarseControl.close()
            self.DeviceSelect.close()
            self.TempControl.close()
            self.QRreader.close()
            self.GoToSetpoint.close()
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
