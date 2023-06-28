import sys
from PyQt5 import QtCore, QtWidgets, uic
import ctypes
import os
import datetime
from twisted.internet.defer import Deferred, inlineCallbacks
myappid = 'YoungLab.nSOTScannerSoftware'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

path = sys.path[0]
sys.path.append(path + r'\Resources') # To makesure loadUiType can access it's resource files
MainWindowUI, QtBaseClass = uic.loadUiType(path + r"\MainWindow.ui")

#import all windows for GUI
from ScanControl import ScanControl
# from LabRADConnect import LabRADConnect
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
# from DeviceSelect import DeviceSelect
from SampleCharacterizer import SampleCharacterizer

from nSOTScannerFormat import printErrorInfo
from Equipment.Equipment import EquipmentHandler

class nanoSQUIDSystem(QtWidgets.QMainWindow, MainWindowUI):
    system_name = 'generic'
    default_script_dir = "C:\\Users"
    """ The following section initializes, or defines the initialization of the GUI and
    connecting to servers."""
    def __init__(self, reactor, parent = None, computer='', folderName=''):
        """ nSOT Scanner GUI """

        super(nanoSQUIDSystem, self).__init__(parent)
        self.reactor = reactor
        self.computer = computer
        self.sessionFolderName = folderName

        ''' Setup the GUI '''
        self.setupUi(self)
        self.setupAdditionalUi()
        self.setupWindows() # Setup the various Windows

        # Configure the equipment and session
        self.equip = EquipmentHandler(self.equipmentFrame, self.remoteFrame, self.computer, self.reactor, self.system_name)
        self.configureEquipment()
        self.configureSession()

        # Make sure the right number of magnets are displayed
        self.FieldControl.configureMagnetUi(self.equip)
        
        # Make sure the right number of thermometers are displayed
        self.TempControl.setupTemperatureUi(self.equip)

        self.moveDefault() #Move to default position

        self.push_ConnectHardware.clicked.connect(self.connectLabRADConnections)
        self.push_DisconnectHardware.clicked.connect(self.disconnectLabRADConnections)

        #Make sure default calibration is emitted
        self.PosCalibration.emitCalibration()


        # Connect buttons
        #self.push_Campaign.clicked.connect(self.chooseCampaign)

        #Make sure default session flder is emitted
        #self.LabRAD.newSessionFolder.emit(self.LabRAD.session_2)

        #Open by default the LabRAD Connect Module and Device Select
        #self.openWindow(self.LabRAD)

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
            printErrorInfo()
        window.raise_()

#----------------------------------------------------------------------------------------------#
    """ Setup the specifics of the system. Overload these functions for specific systems. """

    def setupWindows(self):
        '''
        Setup all the Windows and put them in self.windows
        '''
        self.ScanControl = ScanControl.Window(self.reactor, None)
        # self.LabRAD = LabRADConnect.Window(self.reactor, None)
        # self.DeviceSelect = DeviceSelect.Window(self.reactor, None)
        self.nSOTChar = nSOTCharacterizer.Window(self.reactor, None)
        self.PlottingModule = PlottingModule.CommandCenter(self.reactor, None)
        self.TFChar = TFCharacterizer.Window(self.reactor, None)
        self.AttocubeCoarseControl = CoarseAttocubeControl.Window(self.reactor,None)
        self.Approach = Approach.Window(self.reactor, None, self.AttocubeCoarseControl.OutputEnabled)
        self.ApproachMonitor = ApproachMonitor.Window(self.reactor, None)
        self.PosCalibration = PositionCalibration.Window(self.reactor, None)
        self.FieldControl = FieldControl.Window(self.reactor, None)
        self.TempControl = TemperatureControl.Window(self.reactor,None)
        self.QRreader = QRreader.Window(self.reactor,None)
        self.GoToSetpoint = gotoSetpoint.Window(self.reactor, None, self.Approach)
        self.SampleCharacterizer = SampleCharacterizer.Window(self.reactor,None)
        

        # self.windows = [self.LabRAD, self.DeviceSelect, self.ScanControl, self.nSOTChar, self.PlottingModule, self.TFChar, self.Approach, self.ApproachMonitor,
        #     self.PosCalibration, self.FieldControl, self.TempControl, self.QRreader, self.GoToSetpoint, self.SampleCharacterizer, self.AttocubeCoarseControl]
        self.windows = [self.ScanControl, self.nSOTChar, self.PlottingModule, self.TFChar, self.Approach, self.ApproachMonitor,
            self.PosCalibration, self.FieldControl, self.TempControl, self.QRreader, self.GoToSetpoint, self.SampleCharacterizer, self.AttocubeCoarseControl]

        #This module should always be initialized last, and have the modules
        #That are desired to be scriptable be input
        self.Simulate = Simulation.ScriptSimulator(self.reactor, self, None)
        self.Scripting = Scripting.Window(self.reactor, None, self.ScanControl, self.Approach, self.nSOTChar, self.FieldControl, self.TempControl,
            self.SampleCharacterizer, self.GoToSetpoint, self.Simulate, self.AttocubeCoarseControl, default_script_dir=self.default_script_dir)

        self.windows.append(self.Scripting)
        self.windows.append(self.Simulate)

        #Connect signals between modules
        #When LabRAD Connect module emits all the local and remote labRAD connections, it goes to the device
        #select module. This module selects appropriate devices for things. That is then emitted and is distributed
        #among all the other modules
        # self.LabRAD.cxnLocal.connect(self.DeviceSelect.connectLabRAD)
        # self.LabRAD.cxnRemote.connect(self.DeviceSelect.connectRemoteLabRAD)
        # self.DeviceSelect.newDeviceInfo.connect(self.distributeDeviceInfo)
        # self.LabRAD.cxnDisconnected.connect(self.disconnectLabRADConnections)
        # self.LabRAD.newSessionFolder.connect(self.distributeSessionFolder)

        self.TFChar.workingPointSelected.connect(self.distributeWorkingPoint)
        #self.nSOTChar.newToeField.connect(self.FieldControl.updateToeField)
        self.Approach.newPLLData.connect(self.ApproachMonitor.updatePLLPlots)
        self.Approach.newAux2Data.connect(self.ApproachMonitor.updateAux2Plot)
        self.Approach.newZData.connect(self.ApproachMonitor.updateZPlot)
        self.AttocubeCoarseControl.newZCoarseData.connect(self.ApproachMonitor.updateZCoarsePlot)
        self.Approach.updateFeedbackStatus.connect(self.ScanControl.updateFeedbackStatus)
        self.Approach.updateConstantHeightStatus.connect(self.ScanControl.updateConstantHeightStatus)
        self.Approach.autowithdrawStatus.connect(self.ScanControl.autoWidthdrawAbort)
        self.PosCalibration.newTemperatureCalibration.connect(self.setVoltageCalibration)
        self.ScanControl.updateScanningStatus.connect(self.Approach.updateScanningStatus)

    def configureEquipment(self):
        '''
        Configure the specific equipment for the system by connecting things to the
        EquipmentHandler object, self.equip.
        '''
        self.equip.add_server("LabRAD", None, display_frame=self.genericFrame)
        self.equip.add_server("Data Vault", "data_vault", display_frame=self.genericFrame)
        self.equip.add_server("Serial Server", 'serial_server', display_frame=self.genericFrame)
        self.equip.add_server("GPIB Man.", "gpib_device_manager", display_frame=self.genericFrame)
        self.equip.add_server("GPIB Server", "gpib_bus", display_frame=self.genericFrame)

        '''
        Example of how to add remote connections
        '''
        # self.equip.configure_remote_host("REMOTEHOST", "computer_name_for_serial_server")
        # self.equip.add_remote_server("Remote LabRAD", None)
        # self.equip.add_remote_server("SR830", "sr_830", "0")
    #

    def configureSession(self):
        '''
        Configure the session information.
        '''
        #Saving images of all data taken info
        self.lineEdit_Session_2.setReadOnly(True)
        home = os.path.expanduser("~")
        screenshotdir = os.path.join(home, 'Young Lab Dropbox','Young Group', self.sessionFolderName,'Data','Software Screenshots')
        self.screenshots = os.path.join(screenshotdir, str(datetime.date.today()))
        self.lineEdit_Session_2.setText(self.screenshots)
        if not os.path.exists(self.screenshots):
            os.makedirs(self.screenshots)
        self.distributeSessionFolder(self.screenshots)

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to passing LabRAD connections."""

    @inlineCallbacks
    def connectLabRADConnections(self, c=None):
        yield self.equip.connect_all_servers()
        for window in self.windows:
            if hasattr(window, "connectLabRAD"):
                # print(window)
                window.connectLabRAD(self.equip)
    #

    @inlineCallbacks
    def disconnectLabRADConnections(self, c=None):
        for window in self.windows:
            if hasattr(window, "disconnectLabRAD"):
                window.disconnectLabRAD()
        yield self.sleep(0.25) # give the update loops a little time to complete
        yield self.equip.disconnect_servers()

    def distributeSessionFolder(self, folder):
        self.TFChar.setSessionFolder(folder)
        self.ScanControl.setSessionFolder(folder)
        self.nSOTChar.setSessionFolder(folder)
        self.SampleCharacterizer.setSessionFolder(folder)

#----------------------------------------------------------------------------------------------#
    """ The following section connects signals between various modules."""
    def distributeWorkingPoint(self,freq, phase, channel, amplitude):
        self.Approach.setWorkingPoint(freq, phase, channel, amplitude)

    def setVoltageCalibration(self,data):
        self.Approach.set_voltage_calibration(data)
        self.ScanControl.set_voltage_calibration(data)

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to basic interface functions"""

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

    #@inlineCallbacks
    def closeEvent(self, e):
        try:
            self.disconnectLabRADConnections()
            for window in self.windows:
                if hasattr(window, "close"):
                    window.close()
            #yield self.sleep(2)
            self.reactor.stop()
        except:
            printErrorInfo()

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def keyPressEvent(self, event):
        self.key_list.append(event.key())
        if len(self.key_list) > 10:
            self.key_list = self.key_list[-10:]
        if len(self.key_list) == 10:
            if self.key_list == [QtCore.Qt.Key_Up,QtCore.Qt.Key_Up,QtCore.Qt.Key_Down,QtCore.Qt.Key_Down,QtCore.Qt.Key_Left,QtCore.Qt.Key_Right,QtCore.Qt.Key_Left,QtCore.Qt.Key_Right,QtCore.Qt.Key_B,QtCore.Qt.Key_A]:
                self.flashSQUID()

    @inlineCallbacks
    def flashSQUID(self):
        style = '''QLabel{
                color:rgb(168,168,168);
                qproperty-alignment: 'AlignVCenter | AlignRight';
                }

                #centralwidget{
                background: url(:/nSOTScanner/Pictures/SQUID.png);
                }'''
        self.centralwidget.setStyleSheet(style)

        yield self.sleep(1)

        style = '''QLabel{
                color:rgb(168,168,168);
                qproperty-alignment: 'AlignVCenter | AlignRight';
                }

                #centralwidget{
                background: black;
                }'''
        self.centralwidget.setStyleSheet(style)

#----------------------------------------------------------------------------------------------#
""" The following runs the GUI"""
if __name__=="__main__":
    import qt5reactor
    app = QtWidgets.QApplication(sys.argv)
    qt5reactor.install()
    from twisted.internet import reactor
    window = nanoSQUIDSystem(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
