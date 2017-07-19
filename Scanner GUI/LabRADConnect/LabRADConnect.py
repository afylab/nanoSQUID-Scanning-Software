from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import twisted
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import sys
import dirExplorer

path = sys.path[0] + r"\LabRADConnect"
LabRADConnectUI, QtBaseClass = uic.loadUiType(path + r"\LabRADConnect.ui")

class Window(QtGui.QMainWindow, LabRADConnectUI):
    cxnSuccessful = QtCore.pyqtSignal(dict)
    cxnDisconnected = QtCore.pyqtSignal(dict)
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.moveDefault()
        
        #Initialize variables for all possible server connections in a dictionary
        #Makes multiple connections for browsing data vault in every desired context
        self.emptyDictionary = {
        'cxn'       : None,
        'dv'        : None,
        'ser_server': None,
        'dac_adc'   : None,       
        'hf2li'     : None
        }
        self.connectionDictionary = self.emptyDictionary
        
        self.lineEdit_Session.setReadOnly(True)
        self.session = ''
        self.lineEdit_Session.setText(self.session)
        
        self.push_ConnectAll.clicked.connect(self.connectAllServers)
        self.push_DisconnectAll.clicked.connect(self.disconnectLabRAD)
        self.push_LabRAD.clicked.connect(self.connectLabRAD)
        self.push_DataVault.clicked.connect(self.connectDataVault)
        self.push_SerialServer.clicked.connect(self.connectSerialServer)
        self.push_DACADC.clicked.connect(self.connectDACADC)
        self.push_HF2LI.clicked.connect(self.connectHF2LI)
        
        self.push_Session.clicked.connect(self.chooseSession)
    
    def setupAdditionalUi(self):
        pass
        
    def moveDefault(self):    
        self.move(10,170)
        
    @inlineCallbacks
    def connectAllServers(self, c = None):
        #Lock buttons so prevent clicking during automatic connection
        
        
        #First create connection to labrad and give time for connection to be made
        yield self.connectLabRAD()
        yield self.sleep(0.5)

        #Then create connection to Data Vault and Serial Server (and eventually GPIB server if needed)
        yield self.connectDataVault()
        yield self.connectSerialServer()

        #Give time for serial server connection to be made, before connecting to serial devices
        yield self.sleep(0.5)

        yield self.connectDACADC()
        
        yield self.connectHF2LI()
        
        self.cxnSuccessful.emit(self.connectionDictionary) 
        
        #Unlock buttons once connection is done
        
        
    @inlineCallbacks
    def disconnectLabRAD(self, c = None):
        try: 
            yield self.cxn.disconnect()
        except:
            pass

        self.connectionDictionary = self.emptyDictionary
        
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
        self.push_HF2LI.setStyleSheet("#push_HF2LI{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.label_HF2LI_status.setText('Not connected')
        
        
        self.cxnDisconnected.emit(self.connectionDictionary)   

    @inlineCallbacks
    def connectLabRAD(self, c = None):
        from labrad.wrappers import connectAsync
        try:
            cxn = yield connectAsync(name = 'nSOT Scanner Labrad Connection')
            self.connectionDictionary['cxn'] = cxn
            self.label_LabRAD_status.setText('Connected')
            self.push_LabRAD.setStyleSheet("#push_LabRAD{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except: 
            self.label_LabRAD_status.setText('Connection Failed.')
            self.push_LabRAD.setStyleSheet("#push_LabRAD{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        
    @inlineCallbacks
    def connectDataVault(self, c = None):
        if self.connectionDictionary['cxn'] is None:
            self.push_DataVault.setStyleSheet("#push_DataVault{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_DataVault_status.setText('Not connected')
        else: 
            cxn = self.connectionDictionary['cxn']
            try:
                dv = yield cxn.data_vault
                self.push_DataVault.setStyleSheet("#push_DataVault{" + 
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_DataVault_status.setText('Connected')
                self.connectionDictionary['dv'] = dv
                self.session = r'\.dataVault'
                self.lineEdit_Session.setText(self.session)
            except:
                self.push_DataVault.setStyleSheet("#push_DataVault{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DataVault_status.setText('Connection Failed')
              
    @inlineCallbacks
    def connectSerialServer(self, c = None):
        if self.connectionDictionary['cxn'] is None:
            self.push_SerialServer.setStyleSheet("#push_SerialServer{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_SerialServer_status.setText('Not connected')
        else: 
            try:
                ser_server = yield self.cxn.marec_pc_serial_server
                print self.ser_server
                self.push_SerialServer.setStyleSheet("#push_SerialServer{" + 
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_SerialServer_status.setText('Connected')
                self.connectionDictionary['ser_server'] = ser_server
            except:
                self.push_SerialServer.setStyleSheet("#push_SerialServer{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_SerialServer_status.setText('Connection Failed')
        
    @inlineCallbacks
    def connectDACADC(self, c = None):
        if self.connectionDictionary['ser_server'] is None:
            self.push_DACADC.setStyleSheet("#push_DACADC{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_DACADC_status.setText('Not connected')
        else: 
            try:
                self.dac = yield self.cxn.dac_adc
            except:
                self.push_DACADC.setStyleSheet("#push_DACADC{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DACADC_status.setText('Connection Failed')
            try: 
                yield self.dac.select_device()
                self.push_DACADC.setStyleSheet("#push_DACADC{" + 
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_DACADC_status.setText('Connected')
                self.connectionDictionary['dac_adc'] = dac
            except:
                self.push_DACADC.setStyleSheet("#push_DACADC{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DACADC_status.setText('No device detected')
           
    @inlineCallbacks
    def connectHF2LI(self, c = None):
    
        if self.connectionDictionary['cxn'] is None:
            self.push_HF2LI.setStyleSheet("#push_HF2LI{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_HF2LI_status.setText('Not connected')
        else: 
            cxn = self.connectionDictionary['cxn']
            try:
                hf = yield cxn.hf2li_server
                try: 
                    yield hf.detect_devices()
                    yield hf.select_device()
                    self.push_HF2LI.setStyleSheet("#push_HF2LI{" + 
                    "background: rgb(0,170,0);border-radius: 4px;}")
                    self.label_HF2LI_status.setText('Connected')
                    self.connectionDictionary['hf2li'] = hf
                except:
                    self.push_HF2LI.setStyleSheet("#push_HF2LI{" + 
                    "background: rgb(161,0,0);border-radius: 4px;}")
                    self.label_HF2LI_status.setText('No device detected') 
            except:
                self.push_HF2LI.setStyleSheet("#push_HF2LI{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_HF2LI_status.setText('Connection Failed')


           
    @inlineCallbacks
    def chooseSession(self, c = None):
        if self.connectionDictionary['dv'] is None:
            msgBox = QtGui.QMessageBox(self)
            msgBox.setIcon(QtGui.QMessageBox.Information)
            msgBox.setWindowTitle('Data Vault Connection Missing')
            msgBox.setText("\r\n Cannot choose session location until connected to data vault.")
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
            msgBox.exec_()
        else: 
            dv = self.connectionDictionary['dv']
            dvExplorer = dirExplorer.dataVaultExplorer(dv, self.reactor, self)
            if dvExplorer.exec_():
                fileName, directory, variables = dvExplorer.dirFileVars()
                try:
                    yield dv.cd(directory)
                    directory = directory[1:]
                    session  = ''
                    for i in directory:
                        session = session + '\\' + i
                    self.session = r'\.datavault' + session
                    self.lineEdit_Session.setText(self.session)
                except Exception as inst:
                    print type(inst)
                    print inst.args
                    print inst
                    
                
    def closeEvent(self, e):
        pass
        
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
    
        
        
        
        
        
        
        