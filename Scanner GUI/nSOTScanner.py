import sys
from PyQt4 import QtGui, uic
import ctypes
myappid = 'YoungLab.nSOTScannerSoftware'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

path = sys.path[0]
sys.path.append(path + r'\Resources') # To makesure loadUiType can access it's resource files
MainWindowUI, QtBaseClass = uic.loadUiType(path + r"\MainWindow.ui")

#import all windows for gui
from ScanControl import ScanControl
from LabRADConnect import LabRADConnect
from nSOTCharacterizer import nSOTCharacterizer
from PlottingModule import PlottingModule
from TFCharacterizer import TFCharacterizer
from Approach import Approach, ApproachMonitor
from CoarseAttocubeControl import CoarseAttocubeControl
from PositionCalibration import PositionCalibration
from FieldControl import FieldControl
from ScriptingModule import Scripting, Simulation
from TemperatureControl import TemperatureControl
from QRreader import QRreader
from GoToSetpoint import gotoSetpoint
from DeviceSelect import DeviceSelect
from SampleCharacterizer import SampleCharacterizer

from Equipment.Equipment import EquipmentHandler


class nanoSQUIDSystem(QtGui.QMainWindow, MainWindowUI):
    test = 0
    """ The following section initializes, or defines the initialization of the GUI and
    connecting to servers."""
    def __init__(self, reactor, parent=None):
        """ nSOT Scanner GUI """

        super(nanoSQUIDSystem, self).__init__(parent)
        self.reactor = reactor

        ''' Setup the GUI '''
        self.setupUi(self)
        self.setupWindows() # Setup the various Windows
        self.setupAdditionalUi()
        self.moveDefault() #Move to default position

        self.equip = EquipmentHandler()
        self.configureEquipment()

        #Make sure default calibration is emitted
        self.PosCalibration.emitCalibration()

        #Make sure default session flder is emitted
        self.LabRAD.newSessionFolder.emit(self.LabRAD.session_2)

        #Open by default the LabRAD Connect Module and Device Select
        self.openWindow(self.LabRAD)
        #self.openWindow(self.DeviceSelect)
        #self.openWindow(self.Simulate)

    def setupAdditionalUi(self):
        """Some UI elements would not set properly from Qt Designer. These initializations are done here."""
        #Connects all drop down menu button
        self.actionScan_Control.triggered.connect(lambda : self.openWindow(self.ScanControl))
        self.actionLabRAD_Connect.triggered.connect(lambda : self.openWindow(self.LabRAD))
        self.actionnSOT_Characterizer.triggered.connect(lambda : self.openWindow(self.nSOTChar))
        self.actionData_Plotter.triggered.connect(lambda : self.openWindow(self.PlottingModule))
        self.actionTF_Characterizer.triggered.connect(lambda : self.openWindow(self.TFChar))
        self.actionApproach_Control.triggered.connect(lambda : self.openWindow(self.Approach))
        self.actionApproach_Monitor.triggered.connect(lambda : self.openWindow(self.ApproachMonitor))
        self.actionAttocube_Position_Calibration.triggered.connect(lambda : self.openWindow(self.PosCalibration))
        self.actionMagnetic_Field_Control.triggered.connect(lambda : self.openWindow(self.FieldControl))
        self.actionRun_Scripts.triggered.connect(lambda : self.openWindow(self.Scripting))
        self.actionTemperature_Control.triggered.connect(lambda : self.openWindow(self.TempControl))
        self.actionQR_Reader.triggered.connect(lambda : self.openWindow(self.QRreader))
        self.actionNSOT_Setpoint.triggered.connect(lambda : self.openWindow(self.GoToSetpoint))
        self.actionDevice_Select.triggered.connect(lambda : self.openWindow(self.DeviceSelect))
        self.actionSample_Characterizer.triggered.connect(lambda : self.openWindow(self.SampleCharacterizer))
        self.actionAttocube_Coarse_Position_Control.triggered.connect(lambda : self.openWindow(self.AttocubeCoarseControl))

        #Connectors all layout buttons
        self.push_Layout1.clicked.connect(self.setLayout1)

        self.push_Logo.clicked.connect(self.toggleLogo)
        self.isRedEyes = False

    #----------------------------------------------------------------------------------------------#

    """ The following section connects actions related to default opening windows."""

    def moveDefault(self):
        self.move(10,10)

    def openWindow(self, window):
        window.showNormal()
        try:
            window.moveDefault()
        except:
            pass
        window.raise_()

#----------------------------------------------------------------------------------------------#
    """ Setup the specifics of the system. Overload these functions for specific systems. """

    def setupWindows(self):
        '''
        Setup all the Windows and put them in self.windows
        '''
        self.ScanControl = ScanControl.Window(self.reactor, None)
        self.LabRAD = LabRADConnect.Window(self.reactor, None)
        self.DeviceSelect = DeviceSelect.Window(self.reactor, None)
        self.nSOTChar = nSOTCharacterizer.Window(self.reactor, None)
        self.PlottingModule = PlottingModule.CommandCenter(self.reactor, None)
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

        self.windows = [self.LabRAD, self.DeviceSelect, self.ScanControl, self.nSOTChar, self.PlottingModule, self.TFChar, self.Approach, self.ApproachMonitor,
            self.PosCalibration, self.FieldControl, self.TempControl, self.QRreader, self.GoToSetpoint, self.SampleCharacterizer, self.AttocubeCoarseControl]

        #This module should always be initialized last, and have the modules
        #That are desired to be scriptable be input
        self.Simulate = Simulation.ScriptSimulator(self.reactor, self, None)
        self.Scripting = Scripting.Window(self.reactor, None, self.ScanControl, self.Approach, self.nSOTChar, self.FieldControl, self.TempControl,
            self.SampleCharacterizer, self.GoToSetpoint, self.Simulate)

        self.windows.append(self.Scripting)
        self.windows.append(self.Simulate)

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

    def configureEquipment(self):
        '''
        Configure the specific equipment for the system by connecting things to the
        EquipmentHandler object, self.equip.
        '''
        pass
    #

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to passing LabRAD connections."""

    def distributeDeviceInfo(self, dic):
        #Call connectLabRAD functions for relevant modules.
        #Note that self.windows[0] corresponds to the LabRADConnect and DeviceSelect module
        #LabRAD connections are not sent to them module to prevent recursion errors
        for window in self.windows[2:]:
            if hasattr(window, "connectLabRAD"):
                window.connectLabRAD(dic)

    def disconnectLabRADConnections(self):
        for window in self.windows:
            if hasattr(window, "disconnectLabRAD"):
                window.disconnectLabRAD()

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
        self.openWindow(self.ScanControl)
        self.openWindow(self.Approach)

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
        for window in self.windows:
            if hasattr(window, "hide"):
                window.hide()

    def closeEvent(self, e):
        try:
            self.disconnectLabRADConnections()
            for window in self.windows:
                if hasattr(window, "close"):
                    window.close()
        except Exception as inst:
            print inst

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""

if __name__=="__main__":
    import qt4reactor
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install()
    from twisted.internet import reactor
    window = nanoSQUIDSystem(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
