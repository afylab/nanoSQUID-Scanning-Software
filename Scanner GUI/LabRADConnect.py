from PyQt4 import QtGui, QtCore
from twisted.internet.defer import inlineCallbacks, Deferred
import twisted
import numpy as np
import pyqtgraph as pg
import exceptions
import time

import LabRADConnectUI

class Window(QtGui.QMainWindow, LabRADConnectUI.Ui_MainWindow):
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.moveDefault()
        
        #Initialize variables for all possible server connections
        self.cxn = None
        self.dv = None
        self.ser_server = None
        self.dac = None
        
        self.push_ConnectAll.clicked.connect(self.connectAllServers)
        self.push_DisconnectAll.clicked.connect(self.disconnectLabRAD)
        self.push_LabRAD.clicked.connect(self.connectLabRAD)
        self.push_DataVault.clicked.connect(self.connectDataVault)
        self.push_SerialServer.clicked.connect(self.connectSerialServer)
        self.push_DACADC.clicked.connect(self.connectDACADC)
        
    @inlineCallbacks
    def connectAllServers(self, c = None):
        #First create connection to labrad and give time for connection to be made
        self.connectLabRAD()
        yield self.sleep(1)
        #Then create connection to Data Vault and Serial Server (and eventually GPIB server if needed)
        self.connectDataVault()
        self.connectSerialServer()
        #Give time for serial server connection to be made, before connecting to serial devices
        yield self.sleep(1)
        self.connectDACADC()
        
        
    @inlineCallbacks
    def disconnectLabRAD(self, c = None):
        try: 
            yield self.cxn.disconnect()
            self.cxn = None
            self.dv = None
            self.ss = None
            self.dac = None
        except:
            pass
        
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
        
    @inlineCallbacks
    def connectLabRAD(self):
        from labrad.wrappers import connectAsync
        try:
            self.cxn = yield connectAsync(name = 'nSOT Scanner Labrad Connection')
            self.label_LabRAD_status.setText('Connected')
            self.push_LabRAD.setStyleSheet("#push_LabRAD{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
        except: 
            self.label_LabRAD_status.setText('Connection Failed.')
            self.push_LabRAD.setStyleSheet("#push_LabRAD{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        
    @inlineCallbacks
    def connectDataVault(self):
        if self.cxn is None:
            self.push_DataVault.setStyleSheet("#push_DataVault{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_DataVault_status.setText('Not connected')
        else: 
            try:
                self.dv = yield self.cxn.data_vault
                self.push_DataVault.setStyleSheet("#push_DataVault{" + 
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_DataVault_status.setText('Connected')
                #Eventually add listening for signals here
            except:
                self.push_DataVault.setStyleSheet("#push_DataVault{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DataVault_status.setText('Connection Failed')
              
    @inlineCallbacks
    def connectSerialServer(self):
        if self.cxn is None:
            self.push_SerialServer.setStyleSheet("#push_SerialServer{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            self.label_SerialServer_status.setText('Not connected')
        else: 
            try:
                self.ser_server = yield self.cxn.marec_pc_serial_server
                print self.ser_server
                self.push_SerialServer.setStyleSheet("#push_SerialServer{" + 
                "background: rgb(0,170,0);border-radius: 4px;}")
                self.label_SerialServer_status.setText('Connected')
            except:
                self.push_SerialServer.setStyleSheet("#push_SerialServer{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_SerialServer_status.setText('Connection Failed')
        
    @inlineCallbacks
    def connectDACADC(self):
        if self.ser_server is None:
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
            except:
                self.push_DACADC.setStyleSheet("#push_DACADC{" + 
                "background: rgb(161,0,0);border-radius: 4px;}")
                self.label_DACADC_status.setText('No device detected')
                
    def setupAdditionalUi(self):
        pass
        
    def moveDefault(self):    
        self.move(10,170)
     
    def closeEvent(self, e):
        self.disconnectLabRAD()
        
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
    
        
        
        
        
        
        
        