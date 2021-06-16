from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import sys
from DataVaultBrowser import dirExplorer
import platform
import datetime
import os

path = sys.path[0] + r"\LabRADConnect"
LabRADConnectUI, QtBaseClass = uic.loadUiType(path + r"\LabRADConnect.ui")

class Window(QtGui.QMainWindow, LabRADConnectUI):
    cxnLocal = QtCore.pyqtSignal(dict)
    cxnRemote = QtCore.pyqtSignal(dict)
    cxnDisconnected = QtCore.pyqtSignal()
    newSessionFolder = QtCore.pyqtSignal(str)
    newDVFolder = QtCore.pyqtSignal()

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        #self.moveDefault()

        #Initialize variables for all possible server connections in a dictionary
        #Makes multiple connections for browsing data vault in every desired context
        self.emptyLocalDictionary = {
        'cxn'       : False,
        'dv'        : False,
        'ser_server': False,
        'dac_adc'   : False,
        'dc_box'    : False,
        'ami_430'   : False,
        'hf2li'     : False,
        'gpib_server': False,
        'gpib_manager': False,
        'anc350':       False
        }

        self.emptyRemoteDictionary = {
        'cxn'       : False,
        'dv'        : False,
        'gpib_server': False,
        'gpib_manager': False,
        'ser_server': False,
        'ips120'   : False,
        'ls350'     : False,
        'lm510'      : False
        }

        #Dictionary that holds all the local connections made
        self.connectionLocalDictionary = self.emptyLocalDictionary.copy()
        #Dictionary that holds all the remote connections made
        self.connectionRemoteDictionary = self.emptyRemoteDictionary.copy()

        #Dictionary that keeps track of whether or not the module has attempted to connect locally
        self.cxnAttemptLocalDictionary = self.emptyLocalDictionary.copy()
        #Dictionary that keeps track of whether or not the module has attempted to connect remotely
        self.cxnAttemptRemoteDictionary = self.emptyRemoteDictionary.copy()

        #Data vault session info
        self.lineEdit_Session.setReadOnly(True)
        self.session = ''
        self.lineEdit_Session.setText(self.session)

        #Saving images of all data taken info
        self.lineEdit_Session_2.setReadOnly(True)
        home = os.path.expanduser("~")
        #self.session_2 = home + '\\Data Sets\\ScanData\\' + str(datetime.date.today())
        self.session_2 = home + '\\Young Lab Dropbox\\NanoSQUID Battle Station\\Data\\Software Screenshots\\' + str(datetime.date.today())
        self.lineEdit_Session_2.setText(self.session_2)

        folderExists = os.path.exists(self.session_2)
        if not folderExists:
            os.makedirs(self.session_2)

        self.push_ConnectAll.clicked.connect(self.connectAllServers)
        self.push_ConnectLocal.clicked.connect(self.connectLocalServers)
        self.push_ConnectRemote.clicked.connect(self.connectRemoteServers)
        self.push_DisconnectAll.clicked.connect(self.disconnectLabRAD)

        self.key_list = []

        '''
        Eventually add ability to toggle individual connections.
        self.push_LabRAD.clicked.connect(self.connectLabRAD)
        self.push_DataVault.clicked.connect(self.connectDataVault)
        self.push_SerialServer.clicked.connect(self.connectSerialServer)
        self.push_DACADC.clicked.connect(self.connectDACADC)
        self.push_HF2LI.clicked.connect(self.connectHF2LI)
        '''

        self.push_Session.clicked.connect(self.chooseSession)
        self.push_Session_2.clicked.connect(self.chooseSession_2)

    def setupAdditionalUi(self):
        #Creates and array of stylesheets for the connect button
        base_sheet = """#push_ConnectAll{
                color: rgb(168,168,168);
                background: rgb(60, 60, 60);
                border-radius: 4px;
                }
                QPushButton:pressed#push_ConnectAll{
                color: rgb(168,168,168);
                background-color:rgb(100,100,100);
                border-radius: 4px
                }
                """
        self.sheets = []
        for i in range(0,40):
            new_background = 60 + i*3
            new_sheet = base_sheet.replace('60',str(new_background))
            self.sheets.append(new_sheet)
        for i in range(0,41):
            new_background = 180 - i*3
            new_sheet = base_sheet.replace('60',str(new_background))
            self.sheets.append(new_sheet)

    def moveDefault(self):
        self.move(10,170)

    def connectAllServers(self):
        #TODO: Lock buttons so prevent clicking during automatic connection
        self.connectLocalServers()
        self.connectRemoteServers()

        self.displayAllConnectingGraphics()
        #Unlock buttons once connection is done

    @inlineCallbacks
    def connectLocalServers(self, c = None):
        try:
            self.cxnAttemptLocalDictionary = self.emptyLocalDictionary.copy()

            #Do connecting graphics for one button at a time?
            #self.displayConnectingGraphics()

            #First create connection to labrad. Yielding this command ensures it will be completed before
            #starting following connections
            yield self.connectLabRAD()

            #First connect stand alone servers
            self.connectDataVault()
            self.connectHF2LI()
            self.connectANC350()

            #Then connect servers with dependencies on GPIB or Serial servers
            self.connectSerialDevices()
            self.connectGPIBDevices()

        except Exception as inst:
            print inst

    @inlineCallbacks
    def connectRemoteServers(self, c = None):
        try:
            self.cxnAttemptRemoteDictionary = self.emptyRemoteDictionary.copy()

            #Do connecting graphics for one button at a time?
            #self.displayConnectingGraphics()

            #First create connection to labrad. Yielding this command ensures it will be completed before
            #starting following connections
            yield self.connectRemoteLabRAD()

            #First connect stand alone servers
            self.connectRemoteDataVault()

            #Then connect servers with dependencies on GPIB or Serial servers
            self.connectRemoteSerialDevices()
            self.connectRemoteGPIBDevices()

        except Exception as inst:
            print inst

    @inlineCallbacks
    def displayAllConnectingGraphics(self, c = None):
        i = 0
        while not self.allConnectionsAttmpted():
            self.push_ConnectAll.setStyleSheet(self.sheets[i])
            yield self.sleep(0.025)
            i = (i+1)%81
            '''
            if i == 0:
                print self.cxnAttemptRemoteDictionary
                print self.cxnAttemptLocalDictionary
            '''
        self.push_ConnectAll.setStyleSheet(self.sheets[0])

    def allConnectionsAttmpted(self):
        allCxnAttempted = self.localConnectionsAttempted() * self.remoteConnectionsAttempted()
        return allCxnAttempted

    def localConnectionsAttempted(self):
        localCxnAttempted = True
        cxnAttempts = self.cxnAttemptLocalDictionary.values()
        for attempt in cxnAttempts:
            localCxnAttempted = localCxnAttempted * attempt
        return localCxnAttempted

    def remoteConnectionsAttempted(self):
        remoteCxnAttempted = True
        cxnAttempts = self.cxnAttemptRemoteDictionary.values()
        for attempt in cxnAttempts:
            remoteCxnAttempted = remoteCxnAttempted * attempt
        return remoteCxnAttempted

    def emitLocalConnectionDictionary(self):
        #Emits a connection dictionary only if all the connections were attempted
        if self.localConnectionsAttempted():
            self.cxnLocal.emit(self.connectionLocalDictionary)

    def emitRemoteConnectionDictionary(self):
        #Emits a connection dictionary only if all the connections were attempted
        if self.remoteConnectionsAttempted():
            self.cxnRemote.emit(self.connectionRemoteDictionary)

    @inlineCallbacks
    def disconnectLabRAD(self, c = None):
        try:
            yield self.connectionLocalDictionary['cxn'].anc350_server.disconnect()
            print 'Disconnected ANC350'
        except Exception as inst:
            print inst
            print 'Error disconnecting the ANC350 server.'

        try:
            yield self.connectionLocalDictionary['cxn'].disconnect()
            print 'Disconnected local'
            yield self.connectionRemoteDictionary['cxn'].disconnect()
            print 'Disconnected remote'
        except:
            print 'Error disconnecting the Labrad connection server.'

        self.connectionLocalDictionary = self.emptyLocalDictionary.copy()
        self.connectionRemoteDictionary = self.emptyRemoteDictionary.copy()

        self.lineEdit_Session.setText('')

        self.push_LabRAD.setStyleSheet("#push_LabRAD{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_LabRAD_status.setText('Not connected')
        self.push_DataVault.setStyleSheet("#push_DataVault{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_DataVault_status.setText('Not connected')
        self.push_SerialServer.setStyleSheet("#push_SerialServer{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_SerialServer_status.setText('Not connected')
        self.push_DACADC.setStyleSheet("#push_DACADC{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_DACADC_status.setText('Not connected')
        self.push_DCBox.setStyleSheet("#push_DCBox{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_DCBox_status.setText('Not connected')
        self.push_HF2LI.setStyleSheet("#push_HF2LI{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_HF2LI_status.setText('Not connected')
        self.push_GPIBServer.setStyleSheet("#push_GPIBServer{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_GPIBServer_status.setText('Not connected')
        self.push_GPIBMan.setStyleSheet("#push_GPIBMan{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_GPIBMan_status.setText('Not connected')

        self.push_remoteLabRAD.setStyleSheet("#push_remoteLabRAD{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_remoteLabRAD_status.setText('Not connected')
        self.push_remoteDataVault.setStyleSheet("#push_remoteDataVault{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_remoteDataVault_status.setText('Not connected')
        self.push_remoteSerialServer.setStyleSheet("#push_remoteSerialServer{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_remoteSerialServer_status.setText('Not connected')
        self.push_LM510.setStyleSheet("#push_LM510{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_LM510_status.setText('Not connected')
        self.push_remoteGPIBMan.setStyleSheet("#push_remoteGPIBMan{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_remoteGPIBMan_status.setText('Not connected')
        self.push_remoteGPIBServer.setStyleSheet("#push_remoteGPIBServer{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_remoteGPIBServer_status.setText('Not connected')
        self.push_IPS120.setStyleSheet("#push_IPS120{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_IPS120_status.setText('Not connected')
        self.push_LS350.setStyleSheet("#push_LS350{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_LS350_status.setText('Not connected')
        self.push_ANC350.setStyleSheet("#push_ANC350{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_ANC350_status.setText('Not connected')
        self.push_AMI430.setStyleSheet("#push_AMI430{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_AMI430_status.setText('Not connected')

        #self.cxnDisconnected.emit()

#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section has the methods for connecting independent local devices."""

    @inlineCallbacks
    def connectLabRAD(self, c = None):
        from labrad.wrappers import connectAsync
        try:
            #Connects to the manager on the local computer.
            cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.connectionLocalDictionary['cxn'] = cxn
            self.label_LabRAD_status.setText('Connected')
            self.push_LabRAD.setStyleSheet("#push_LabRAD{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
            self.label_LabRAD_status.setText('Connection Failed.')
            self.push_LabRAD.setStyleSheet("#push_LabRAD{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        self.cxnAttemptLocalDictionary['cxn'] = True
        self.emitLocalConnectionDictionary()

    @inlineCallbacks
    def connectDataVault(self, c = None):
        if self.connectionLocalDictionary['cxn'] is False:
            self.push_DataVault.setStyleSheet("#push_DataVault{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_DataVault_status.setText('Not connected')
        else:
            cxn = self.connectionLocalDictionary['cxn']
            try:
                dv = yield cxn.data_vault
                self.push_DataVault.setStyleSheet("#push_DataVault{" +
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_DataVault_status.setText('Connected')
                self.connectionLocalDictionary['dv'] = dv
                self.session = r'\.dataVault'
                self.lineEdit_Session.setText(self.session)
            except:
                self.push_DataVault.setStyleSheet("#push_DataVault{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DataVault_status.setText('Connection Failed')
        self.cxnAttemptLocalDictionary['dv'] = True
        self.emitLocalConnectionDictionary()

    @inlineCallbacks
    def connectHF2LI(self, c = None):
        if self.connectionLocalDictionary['cxn'] is False:
            self.push_HF2LI.setStyleSheet("#push_HF2LI{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_HF2LI_status.setText('Not connected')
        else:
            cxn = self.connectionLocalDictionary['cxn']
            try:
                hf = yield cxn.hf2li_server
                try:
                    yield hf.detect_devices()
                    yield hf.select_device()
                    self.push_HF2LI.setStyleSheet("#push_HF2LI{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_HF2LI_status.setText('Connected')
                    self.connectionLocalDictionary['hf2li'] = hf
                except:
                    self.push_HF2LI.setStyleSheet("#push_HF2LI{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_HF2LI_status.setText('No device detected')
            except:
                self.push_HF2LI.setStyleSheet("#push_HF2LI{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_HF2LI_status.setText('Connection Failed')
        self.cxnAttemptLocalDictionary['hf2li'] = True
        self.emitLocalConnectionDictionary()

    @inlineCallbacks
    def connectANC350(self, c = None):
        if self.connectionLocalDictionary['cxn'] is False:
            self.push_ANC350.setStyleSheet("#push_ANC350{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_ANC350_status.setText('Not connected')
        else:
            cxn = self.connectionLocalDictionary['cxn']
            try:
                anc = yield cxn.anc350_server
                num_devs = yield anc.discover()
                if num_devs > 0:
                    yield anc.connect()
                    self.push_ANC350.setStyleSheet("#push_ANC350{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_ANC350_status.setText('Connected')
                    self.connectionLocalDictionary['anc350'] = anc
                else:
                    self.push_ANC350.setStyleSheet("#push_ANC350{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_ANC350_status.setText('No device detected')
            except Exception: #as inst:
                self.push_ANC350.setStyleSheet("#push_ANC350{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_ANC350_status.setText('Connection Failed')
        self.cxnAttemptLocalDictionary['anc350'] = True
        self.emitLocalConnectionDictionary()

#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section has the methods for connecting independent remote devices."""
    @inlineCallbacks
    def connectRemoteLabRAD(self):
        from labrad.wrappers import connectAsync
        try:
            #Connects to the manager on the 4K system monitoring computer. Eventually add a way to
            #input the name of the connection
            cxn = yield connectAsync(host = '4KMonitor', password = 'pass')
            self.connectionRemoteDictionary['cxn'] = cxn
            self.label_remoteLabRAD_status.setText('Connected')
            self.push_remoteLabRAD.setStyleSheet("#push_remoteLabRAD{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except:
            self.label_remoteLabRAD_status.setText('Connection Failed.')
            self.push_remoteLabRAD.setStyleSheet("#push_remoteLabRAD{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        self.cxnAttemptRemoteDictionary['cxn'] = True
        self.emitRemoteConnectionDictionary()

    @inlineCallbacks
    def connectRemoteDataVault(self, c = None):
        if self.connectionRemoteDictionary['cxn'] is False:
            self.push_remoteDataVault.setStyleSheet("#push_remoteDataVault{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_remoteDataVault_status.setText('Not connected')
        else:
            cxn = self.connectionRemoteDictionary['cxn']
            try:
                dv = yield cxn.data_vault
                self.push_remoteDataVault.setStyleSheet("#push_remoteDataVault{" +
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_remoteDataVault_status.setText('Connected')
                self.connectionRemoteDictionary['dv'] = dv
            except:
                self.push_remoteDataVault.setStyleSheet("#push_remoteDataVault{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_remoteDataVault_status.setText('Connection Failed')
        self.cxnAttemptRemoteDictionary['dv'] = True
        self.emitRemoteConnectionDictionary()


#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section has the methods for connecting local Serial devices."""

    @inlineCallbacks
    def connectSerialDevices(self, c = None):
        yield self.connectSerialServer()
        self.connectDACADC()
        self.connectDCBox()
        self.connectAMI430()

    @inlineCallbacks
    def connectSerialServer(self, c = None):
        if self.connectionLocalDictionary['cxn'] is False:
            self.push_SerialServer.setStyleSheet("#push_SerialServer{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_SerialServer_status.setText('Not connected')
        else:
            cxn = self.connectionLocalDictionary['cxn']
            try:
                computerName = platform.node() # get computer name
                serialServerName = computerName.lower().replace(' ','_').replace('-','_') + '_serial_server'

                ser_server = yield cxn.servers[serialServerName]
                self.push_SerialServer.setStyleSheet("#push_SerialServer{" +
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_SerialServer_status.setText('Connected')
                self.connectionLocalDictionary['ser_server'] = ser_server
            except:
                self.push_SerialServer.setStyleSheet("#push_SerialServer{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_SerialServer_status.setText('Connection Failed')
        self.cxnAttemptLocalDictionary['ser_server'] = True
        self.emitLocalConnectionDictionary()

    @inlineCallbacks
    def connectDACADC(self, c = None):
        if self.connectionLocalDictionary['ser_server'] is False:
            self.push_DACADC.setStyleSheet("#push_DACADC{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_DACADC_status.setText('Not connected')
        else:
            cxn = self.connectionLocalDictionary['cxn']
            try:
                dac = yield cxn.dac_adc
                try:
                    yield dac.select_device()
                    self.push_DACADC.setStyleSheet("#push_DACADC{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_DACADC_status.setText('Connected')
                    self.connectionLocalDictionary['dac_adc'] = dac
                except:
                    self.push_DACADC.setStyleSheet("#push_DACADC{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_DACADC_status.setText('No device detected')
            except:
                self.push_DACADC.setStyleSheet("#push_DACADC{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DACADC_status.setText('Connection Failed')

        self.cxnAttemptLocalDictionary['dac_adc'] = True
        self.emitLocalConnectionDictionary()

    @inlineCallbacks
    def connectDCBox(self, c = None):
        if self.connectionLocalDictionary['ser_server'] is False:
            self.push_DCBox.setStyleSheet("#push_DCBox{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_DCBox_status.setText('Not connected')
        else:
            cxn = self.connectionLocalDictionary['cxn']
            try:
                ad = yield cxn.ad5764_dcbox
                try:
                    yield ad.select_device()
                    self.push_DCBox.setStyleSheet("#push_DCBox{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_DCBox_status.setText('Connected')
                    self.connectionLocalDictionary['dc_box'] = ad
                except:
                    self.push_DCBox.setStyleSheet("#push_DCBox{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_DCBox_status.setText('No device detected')
            except:
                self.push_DCBox.setStyleSheet("#push_DCBox{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DCBox_status.setText('Connection Failed')

        self.cxnAttemptLocalDictionary['dc_box'] = True
        self.emitLocalConnectionDictionary()

    @inlineCallbacks
    def connectAMI430(self, c = None):
        if self.connectionLocalDictionary['ser_server'] is False:
            self.push_AMI430.setStyleSheet("#push_AMI430{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_AMI430_status.setText('Not connected')
        else:
            cxn = self.connectionLocalDictionary['cxn']
            try:
                ami = yield cxn.ami_430
                try:
                    yield ami.select_device()
                    self.push_AMI430.setStyleSheet("#push_AMI430{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_AMI430_status.setText('Connected')
                    self.connectionLocalDictionary['ami_430'] = ami
                except:
                    self.push_AMI430.setStyleSheet("#push_AMI430{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_AMI430_status.setText('No device detected')
            except:
                self.push_AMI430.setStyleSheet("#push_AMI430{" +
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_AMI430_status.setText('Connection Failed')

        self.cxnAttemptLocalDictionary['ami_430'] = True
        self.emitLocalConnectionDictionary()

#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section has the methods for connecting remote Serial devices."""

    @inlineCallbacks
    def connectRemoteSerialDevices(self, c = None):
        yield self.connectRemoteSerialServer()
        self.connectRemoteLM510()

    @inlineCallbacks
    def connectRemoteSerialServer(self, c = None):
        try:
            if self.connectionRemoteDictionary['cxn'] is False:
                self.push_remoteSerialServer.setStyleSheet("#push_remoteSerialServer{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_remoteSerialServer_status.setText('Not connected')
            else:
                cxn = self.connectionRemoteDictionary['cxn']
                try:
                    ser_server = yield cxn.minint_o9n40pb_serial_server
                    self.push_remoteSerialServer.setStyleSheet("#push_remoteSerialServer{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_remoteSerialServer_status.setText('Connected')
                    self.connectionRemoteDictionary['ser_server'] = ser_server
                except:
                    self.push_remoteSerialServer.setStyleSheet("#push_remoteSerialServer{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_remoteSerialServer_status.setText('Connection Failed')
            self.cxnAttemptRemoteDictionary['ser_server'] = True
            self.emitRemoteConnectionDictionary()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def connectRemoteLM510(self, c = None):
        try:
            if self.connectionRemoteDictionary['ser_server'] is False:
                self.push_LM510.setStyleSheet("#push_LM510{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_LM510_status.setText('Not connected')
            else:
                cxn = self.connectionRemoteDictionary['cxn']
                try:
                    lm = yield cxn.lm_510
                except:
                    self.push_LM510.setStyleSheet("#push_LM510{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_LM510_status.setText('Connection Failed')
                try:
                    yield lm.select_device()
                    self.push_LM510.setStyleSheet("#push_LM510{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_LM510_status.setText('Connected')
                    self.connectionRemoteDictionary['lm510'] = lm
                except:
                    self.push_LM510.setStyleSheet("#push_LM510{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_LM510_status.setText('No device detected')
            self.cxnAttemptRemoteDictionary['lm510'] = True
            self.emitRemoteConnectionDictionary()
        except Exception as inst:
            print inst

#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section has the methods for connecting local GPIB devices."""

    @inlineCallbacks
    def connectGPIBDevices(self, c = None):
        yield self.connectGPIBServer()
        yield self.connectGPIBManager()
        #add gpib devices here

    @inlineCallbacks
    def connectGPIBServer(self, c = None):
        #TODO
        #Get local information to get GPIB bus server name
        try:
            if self.connectionLocalDictionary['cxn'] is False:
                self.push_GPIBServer.setStyleSheet("#push_GPIBServer{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_GPIBServer_status.setText('Not connected')
            else:
                cxn = self.connectionLocalDictionary['cxn']
                try:
                    gpib_server = yield cxn.nanosquid_ws_gpib_bus
                    self.push_GPIBServer.setStyleSheet("#push_GPIBServer{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_GPIBServer_status.setText('Connected')
                    self.connectionLocalDictionary['gpib_server'] = gpib_server
                except Exception as inst:
                    self.push_GPIBServer.setStyleSheet("#push_GPIBServer{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_GPIBServer_status.setText('Connection Failed')
            self.cxnAttemptLocalDictionary['gpib_server'] = True
            self.emitLocalConnectionDictionary()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def connectGPIBManager(self, c = None):
        try:
            if self.connectionLocalDictionary['cxn'] is False:
                self.push_GPIBMan.setStyleSheet("#push_GPIBMan{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_GPIBMan_status.setText('Not connected')
            else:
                cxn = self.connectionLocalDictionary['cxn']
                try:
                    gpib_man = yield cxn.gpib_device_manager
                    self.push_GPIBMan.setStyleSheet("#push_GPIBMan{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_GPIBMan_status.setText('Connected')
                    self.connectionLocalDictionary['gpib_manager'] = gpib_man
                except:
                    self.push_GPIBMan.setStyleSheet("#push_GPIBMan{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_GPIBMan_status.setText('Connection Failed')
            self.cxnAttemptLocalDictionary['gpib_manager'] = True
            self.emitLocalConnectionDictionary()
        except Exception as inst:
            print inst

#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section has the methods for connecting remote GPIB devices."""

    @inlineCallbacks
    def connectRemoteGPIBDevices(self, c = None):
        yield self.connectRemoteGPIBServer()
        yield self.connectRemoteGPIBManager()
        self.connectRemoteIPS120()
        self.connectRemoteLS350()

    @inlineCallbacks
    def connectRemoteGPIBServer(self, c = None):
        try:
            if self.connectionRemoteDictionary['cxn'] is False:
                self.push_remoteGPIBServer.setStyleSheet("#push_remoteGPIBServer{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_remoteGPIBServer_status.setText('Not connected')
            else:
                cxn = self.connectionRemoteDictionary['cxn']
                try:
                    gpib_server = yield cxn.minint_o9n40pb_gpib_bus
                    self.push_remoteGPIBServer.setStyleSheet("#push_remoteGPIBServer{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_remoteGPIBServer_status.setText('Connected')
                    self.connectionRemoteDictionary['gpib_server'] = gpib_server
                except Exception as inst:
                    self.push_remoteGPIBServer.setStyleSheet("#push_remoteGPIBServer{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_remoteGPIBServer_status.setText('Connection Failed')
            self.cxnAttemptRemoteDictionary['gpib_server'] = True
            self.emitRemoteConnectionDictionary()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def connectRemoteGPIBManager(self, c = None):
        try:
            if self.connectionRemoteDictionary['cxn'] is False:
                self.push_remoteGPIBMan.setStyleSheet("#push_remoteGPIBMan{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_remoteGPIBMan_status.setText('Not connected')
            else:
                cxn = self.connectionRemoteDictionary['cxn']
                try:
                    gpib_man = yield cxn.gpib_device_manager
                    self.push_remoteGPIBMan.setStyleSheet("#push_remoteGPIBMan{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_remoteGPIBMan_status.setText('Connected')
                    self.connectionRemoteDictionary['gpib_manager'] = gpib_man
                except:
                    self.push_remoteGPIBMan.setStyleSheet("#push_remoteGPIBMan{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_remoteGPIBMan_status.setText('Connection Failed')
            self.cxnAttemptRemoteDictionary['gpib_manager'] = True
            self.emitRemoteConnectionDictionary()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def connectRemoteIPS120(self):
        try:
            if self.connectionRemoteDictionary['gpib_server'] is False or self.connectionRemoteDictionary['gpib_manager'] is False:
                self.push_IPS120.setStyleSheet("#push_IPS120{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_IPS120_status.setText('Not connected')
            else:
                cxn = self.connectionRemoteDictionary['cxn']
                try:
                    ips = yield cxn.ips120_power_supply
                except:
                    self.push_IPS120.setStyleSheet("#push_IPS120{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_IPS120_status.setText('Connection Failed')
                try:
                    yield ips.select_device()

                    yield ips.set_control(3) #Set IPS to remote communication (prevents user from using the front panel)
                    yield ips.set_comm_protocol(6) #Set IPS communication protocol appropriately
                    yield ips.set_control(2) #Set IPS to local control (allows user to edit IPS from the front panel)

                    self.push_IPS120.setStyleSheet("#push_IPS120{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_IPS120_status.setText('Connected')
                    self.connectionRemoteDictionary['ips120'] = ips
                except:
                    self.push_IPS120.setStyleSheet("#push_IPS120{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_IPS120_status.setText('No device detected')
            self.cxnAttemptRemoteDictionary['ips120'] = True
            self.emitRemoteConnectionDictionary()
        except Exception as inst:
            print inst

    @inlineCallbacks
    def connectRemoteLS350(self, c = None):
        try:
            if self.connectionRemoteDictionary['gpib_server'] is False or self.connectionRemoteDictionary['gpib_manager'] is False:
                self.push_LS350.setStyleSheet("#push_LS350{" +
                "background: rgb(144, 140, 9);border-radius: 4px;}")
                self.label_LS350_status.setText('Not connected')
            else:
                cxn = self.connectionRemoteDictionary['cxn']
                try:
                    ls = yield cxn.lakeshore_350
                except:
                    self.push_LS350.setStyleSheet("#push_LS350{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_LS350_status.setText('Connection Failed')
                try:
                    yield ls.select_device()
                    self.push_LS350.setStyleSheet("#push_LS350{" +
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_LS350_status.setText('Connected')
                    self.connectionRemoteDictionary['ls350'] = ls
                except:
                    self.push_LS350.setStyleSheet("#push_LS350{" +
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_LS350_status.setText('No device detected')
            self.cxnAttemptRemoteDictionary['ls350'] = True
            self.emitRemoteConnectionDictionary()
        except Exception as inst:
            print inst
#--------------------------------------------------------------------------------------------------------------------------#

    """ The following section has the methods for choosing the datavault location."""

    @inlineCallbacks
    def chooseSession(self, c = None):
        try:
            if self.connectionLocalDictionary['dv'] is False:
                msgBox = QtGui.QMessageBox(self)
                msgBox.setIcon(QtGui.QMessageBox.Information)
                msgBox.setWindowTitle('Data Vault Connection Missing')
                msgBox.setText("\r\n Cannot choose data vault folder until connected to data vault.")
                msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()
            else:
                dv = self.connectionLocalDictionary['dv']
                dvExplorer = dirExplorer.dataVaultExplorer(dv, self.reactor, self)
                yield dvExplorer.popDirs()
                dvExplorer.show()
                dvExplorer.raise_()
                dvExplorer.accepted.connect(lambda: self.OpenDataVaultFolder(self.reactor, dv, dvExplorer.directory))

        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    @inlineCallbacks
    def OpenDataVaultFolder(self, c, datavault, directory):
        try:
            yield datavault.cd(directory)
            directory = directory[1:]
            session  = ''
            for i in directory:
                session = session + '\\' + i
            self.session = r'\.datavault' + session
            self.lineEdit_Session.setText(self.session)
            self.newDVFolder.emit()
        except Exception as inst:
            print 'Error:', inst, ' on line: ', sys.exc_traceback.tb_lineno

    def chooseSession_2(self):
        folder = str(QtGui.QFileDialog.getExistingDirectory(self, directory = 'C:\\Users\\cltschirhart\\Data Sets\\ScanData'))
        if folder:
            self.session_2 = folder
            self.lineEdit_Session_2.setText(self.session_2)
            self.newSessionFolder.emit(self.session_2)

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
