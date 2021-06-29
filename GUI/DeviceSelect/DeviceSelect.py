import sys
from PyQt5 import QtWidgets, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
from nSOTScannerFormat import printErrorInfo

path = sys.path[0] + r"\DeviceSelect"
DeviceSelectUI, QtBaseClass = uic.loadUiType(path + r"\DeviceSelect.ui")

class Window(QtWidgets.QMainWindow, DeviceSelectUI):
    newDeviceInfo = QtCore.pyqtSignal(dict)

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        #name of the file that stores the information about which configuration is the default configuration
        self.fileName = path + '\ConfigurationInfo.txt'

        self.moveDefault()

        self.localLabRADConnected = False
        self.remoteLabRADConnected = False

        #Creates a dictionary that organizes the GUI items into a similar structure as the deviceDictionary
        #for easy iteration and structure
        self.GUIDictionary = {
        'devices': {
                    'system' : {
                        'magnet supply':  self.comboBox_MagnetPowerSupply,
                        'specific supply':   self.comboBox_MagnetSupplyDevice,
                        'blink device':     self.comboBox_BlinkDevice,
                        'coarse positioner': self.comboBox_CoarsePositioner
                    },
                    'approach and TF' : {
                        'dc_box':   self.comboBox_Approach_DCBox,
                        'hf2li':    self.comboBox_Approach_HF2LI
                    },
                    'scan' : {
                        'dac_adc':  self.comboBox_Scan_DACADC
                    },
                    'nsot' : {
                        'dac_adc':  self.comboBox_nSOT_DACADC
                    },
                    'sample' : {
                        'dac_adc':  self.comboBox_Sample_DACADC,
                        'dc_box':   self.comboBox_Sample_DCBox
                    }
        },
        'channels':{
                    'system' : {
                        'blink channel':     self.comboBox_BlinkChannel,
                        'toellner dac voltage':     self.comboBox_ToeVolt,
                        'toellner dac current':  self.comboBox_ToeCurr
                    },
                    'approach and TF' : {
                        'pll input':    self.comboBox_Approach_PLLInput,
                        'pll output':   self.comboBox_Approach_PLLOutput,
                        'pid z out':    self.comboBox_Approach_PIDZOut,
                        'z monitor':    self.comboBox_Approach_ZMonitor,
                        'sum board toggle':    self.comboBox_Approach_SumBoard,
                    },
                    'scan' : {
                        'z out':        self.comboBox_Scan_ZOut,
                        'x out':        self.comboBox_Scan_XOut,
                        'y out':        self.comboBox_Scan_YOut,
                    },
                    'nsot' : {
                        'Bias Reference':    self.comboBox_nSOT_BiasRef,
                        'DC Readout':        self.comboBox_nSOT_DC,
                        'Noise Readout':     self.comboBox_nSOT_Noise,
                        'nSOT Bias':         self.comboBox_nSOT_Bias,
                        'nSOT Gate':         self.comboBox_nSOT_Gate,
                        'Gate Reference':    self.comboBox_nSOT_GateRef,
                    },
        }
        }

        #Set device dictionary to default empty state, and generally treat the module as if it were just disconnected
        self.disconnectLabRAD()

        self.push_setDefault.clicked.connect(self.setDefaultConfiguration)
        self.push_saveConfig.clicked.connect(self.saveConfigurationInfo)

        self.push_loadConfig.clicked.connect(self.loadNewConfigurationInfo)

        self.comboBox_Approach_DCBox.currentIndexChanged.connect(self.setApproachDCBox)
        self.comboBox_Approach_HF2LI.currentIndexChanged.connect(self.setApproachHF2LI)

        self.comboBox_Approach_PLLInput.currentIndexChanged.connect(self.setApproachPLLInput)
        self.comboBox_Approach_PLLOutput.currentIndexChanged.connect(self.setApproachPLLOutput)
        self.comboBox_Approach_PIDZOut.currentIndexChanged.connect(self.setApproachPIDZOut)
        self.comboBox_Approach_ZMonitor.currentIndexChanged.connect(self.setApproachZMonitor)
        self.comboBox_Approach_SumBoard.currentIndexChanged.connect(self.setApproachSumBoard)

        self.comboBox_Scan_DACADC.currentIndexChanged.connect(self.setScanDACADC)

        self.comboBox_Scan_ZOut.currentIndexChanged.connect(self.setScanZOut)
        self.comboBox_Scan_XOut.currentIndexChanged.connect(self.setScanXOut)
        self.comboBox_Scan_YOut.currentIndexChanged.connect(self.setScanYOut)

        self.comboBox_nSOT_DACADC.currentIndexChanged.connect(self.setNSOTDACADC)

        self.comboBox_nSOT_BiasRef.currentIndexChanged.connect(self.setNSOTBiasRef)
        self.comboBox_nSOT_Bias.currentIndexChanged.connect(self.setNSOTBias)
        self.comboBox_nSOT_DC.currentIndexChanged.connect(self.setNSOTDC)
        self.comboBox_nSOT_Noise.currentIndexChanged.connect(self.setNSOTNoise)
        self.comboBox_nSOT_GateRef.currentIndexChanged.connect(self.setNSOTGateRef)
        self.comboBox_nSOT_Gate.currentIndexChanged.connect(self.setNSOTGate)

        self.comboBox_MagnetPowerSupply.currentIndexChanged.connect(self.setMagnetPowerSupply)
        self.comboBox_MagnetSupplyDevice.currentIndexChanged.connect(self.setMagnetSupplyDevice)

        self.comboBox_Sample_DACADC.currentIndexChanged.connect(self.setSampleDACADC)
        self.comboBox_Sample_DCBox.currentIndexChanged.connect(self.setSampleDCBox)

        self.comboBox_BlinkDevice.currentIndexChanged.connect(self.setBlinkDevice)
        self.comboBox_BlinkChannel.currentIndexChanged.connect(self.setBlinkChannel)

        self.comboBox_CoarsePositioner.currentIndexChanged.connect(self.setCoarsePositioner)

    def moveDefault(self):
        self.move(550,10)

    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        pass

    def setConfigStatus(self, status):
        if status:
            sheet = '''#pushButton_configStatus{
                        background: rgb(0, 170, 0);
                        border-radius: 8px;
                        }'''
        else:
            sheet = '''#pushButton_configStatus{
                        background: rgb(161, 0, 0);
                        border-radius: 8px;
                        }'''
        self.pushButton_configStatus.setStyleSheet(sheet)

    def resetDeviceDictionary(self):
        self.deviceDictionary = {
        'servers': {
        #Gets autopopulated from the labrad connect server emitted
        },
        'devices': {
                    'system' : {
                        'magnet supply':  False,
                        'specific supply':   False,
                        'blink device':  False,
                        'coarse positioner': False,
                    },
                    'approach and TF' : {
                        'dc_box':   False,
                        'hf2li':    False
                    },
                    'scan' : {
                        'dac_adc':  False
                    },
                    'nsot' : {
                        'dac_adc':  False
                    },
                    'sample' : {
                        'dac_adc':  False,
                        'dc_box':   False,
                    }
        },
        'channels':{
                    'system' : {
                        'toellner dac voltage':  4,
                        'toellner dac current':  3,
                        'blink channel':  2,
                    },
                    'approach and TF' : {
                        'pll input':    1,
                        'pll output':   1,
                        'pid z out':    1,
                        'z monitor':    1,
                        'sum board toggle': 1,
                    },
                    'scan' : {
                        'z out':        1,
                        'x out':        2,
                        'y out':        3,
                    },
                    'nsot' : {
                        'DC Readout':        3,
                        'Noise Readout':     2,
                        'nSOT Bias':         4,
                        'Bias Reference':    4,
                        'nSOT Gate':         1,
                        'Gate Reference':    1,
                    }
        }
        }

    def setApproachDCBox(self):
        self.deviceDictionary['devices']['approach and TF']['dc_box'] = str(self.comboBox_Approach_DCBox.currentText())
        self.label_Approach_DCBox.setText(str(self.comboBox_Approach_DCBox.currentText()))
        self.setConfigStatus(False)

    def setApproachHF2LI(self):
        self.deviceDictionary['devices']['approach and TF']['hf2li'] = str(self.comboBox_Approach_HF2LI.currentText())
        self.label_Approach_HF1.setText(str(self.comboBox_Approach_HF2LI.currentText()))
        self.label_Approach_HF2.setText(str(self.comboBox_Approach_HF2LI.currentText()))
        self.label_Approach_HF3.setText(str(self.comboBox_Approach_HF2LI.currentText()))
        self.label_Approach_HF4.setText(str(self.comboBox_Approach_HF2LI.currentText()))
        self.setConfigStatus(False)

    def setApproachPLLInput(self):
        self.deviceDictionary['channels']['approach and TF']['pll input'] = int(self.comboBox_Approach_PLLInput.currentIndex())+1
        self.setConfigStatus(False)

    def setApproachPLLOutput(self):
        self.deviceDictionary['channels']['approach and TF']['pll output'] = int(self.comboBox_Approach_PLLOutput.currentIndex())+1
        self.setConfigStatus(False)

    def setApproachPIDZOut(self):
        self.deviceDictionary['channels']['approach and TF']['pid z out'] = int(self.comboBox_Approach_PIDZOut.currentIndex())+1
        self.setConfigStatus(False)

    def setApproachZMonitor(self):
        self.deviceDictionary['channels']['approach and TF']['z monitor'] = int(self.comboBox_Approach_ZMonitor.currentIndex())+1
        self.setConfigStatus(False)

    def setApproachSumBoard(self):
        self.deviceDictionary['channels']['approach and TF']['sum board toggle'] = int(self.comboBox_Approach_SumBoard.currentIndex())+1
        self.setConfigStatus(False)

    def setScanDACADC(self):
        self.deviceDictionary['devices']['scan']['dac_adc'] = str(self.comboBox_Scan_DACADC.currentText())
        self.label_Scan_Device1.setText(str(self.comboBox_Scan_DACADC.currentText()))
        self.label_Scan_Device2.setText(str(self.comboBox_Scan_DACADC.currentText()))
        self.label_Scan_Device3.setText(str(self.comboBox_Scan_DACADC.currentText()))
        self.setConfigStatus(False)

    def setScanZOut(self):
        self.deviceDictionary['channels']['scan']['z out'] = int(self.comboBox_Scan_ZOut.currentIndex())+1
        self.setConfigStatus(False)

    def setScanXOut(self):
        self.deviceDictionary['channels']['scan']['x out'] = int(self.comboBox_Scan_XOut.currentIndex())+1
        self.setConfigStatus(False)

    def setScanYOut(self):
        self.deviceDictionary['channels']['scan']['y out'] = int(self.comboBox_Scan_YOut.currentIndex())+1
        self.setConfigStatus(False)

    def setNSOTDACADC(self):
        self.deviceDictionary['devices']['nsot']['dac_adc'] = str(self.comboBox_nSOT_DACADC.currentText())

        self.label_nSOT_Device1.setText(str(self.comboBox_nSOT_DACADC.currentText()))
        self.label_nSOT_Device2.setText(str(self.comboBox_nSOT_DACADC.currentText()))
        self.label_nSOT_Device3.setText(str(self.comboBox_nSOT_DACADC.currentText()))
        self.label_nSOT_Device4.setText(str(self.comboBox_nSOT_DACADC.currentText()))
        self.label_nSOT_Device5.setText(str(self.comboBox_nSOT_DACADC.currentText()))
        self.label_nSOT_Device6.setText(str(self.comboBox_nSOT_DACADC.currentText()))
        self.setConfigStatus(False)

    def setNSOTBiasRef(self):
        self.deviceDictionary['channels']['nsot']['Bias Reference'] = int(self.comboBox_nSOT_BiasRef.currentIndex())+1
        self.setConfigStatus(False)

    def setNSOTBias(self):
        self.deviceDictionary['channels']['nsot']['nSOT Bias'] = int(self.comboBox_nSOT_Bias.currentIndex())+1
        self.setConfigStatus(False)

    def setNSOTDC(self):
        self.deviceDictionary['channels']['nsot']['DC Readout'] = int(self.comboBox_nSOT_DC.currentIndex())+1
        self.setConfigStatus(False)

    def setNSOTGateRef(self):
        self.deviceDictionary['channels']['nsot']['Gate Reference'] = int(self.comboBox_nSOT_GateRef.currentIndex())+1
        self.setConfigStatus(False)

    def setNSOTGate(self):
        self.deviceDictionary['channels']['nsot']['nSOT Gate'] = int(self.comboBox_nSOT_Gate.currentIndex())+1
        self.setConfigStatus(False)

    def setNSOTNoise(self):
        self.deviceDictionary['channels']['nsot']['Noise Readout'] = int(self.comboBox_nSOT_Noise.currentIndex())+1
        self.setConfigStatus(False)

    def setMagnetPowerSupply(self):
        self.deviceDictionary['devices']['system']['magnet supply'] = str(self.comboBox_MagnetPowerSupply.currentText())
        if str(self.comboBox_MagnetPowerSupply.currentText()).startswith('IPS') or str(self.comboBox_MagnetPowerSupply.currentText()).startswith('AMI'):
            self.label_ToeVolt.setVisible(False)
            self.label_ToeCurr.setVisible(False)
            self.label_ToeVoltDevice.setVisible(False)
            self.label_ToeCurrDevice.setVisible(False)
            self.comboBox_ToeVolt.setVisible(False)
            self.comboBox_ToeCurr.setVisible(False)
        elif str(self.comboBox_MagnetPowerSupply.currentText()).startswith('Toe'):
            self.label_ToeVolt.setVisible(True)
            self.label_ToeCurr.setVisible(True)
            self.label_ToeVoltDevice.setVisible(True)
            self.label_ToeCurrDevice.setVisible(True)
            self.comboBox_ToeVolt.setVisible(True)
            self.comboBox_ToeCurr.setVisible(True)
        self.setConfigStatus(False)

    def setMagnetSupplyDevice(self):
        self.deviceDictionary['devices']['system']['specific supply'] = str(self.comboBox_MagnetSupplyDevice.currentText())
        self.label_ToeVoltDevice.setText(str(self.comboBox_MagnetSupplyDevice.currentText()))
        self.label_ToeCurrDevice.setText(str(self.comboBox_MagnetSupplyDevice.currentText()))
        self.setConfigStatus(False)

    def setBlinkDevice(self):
        self.deviceDictionary['devices']['system']['blink device'] = str(self.comboBox_BlinkDevice.currentText())
        self.label_BlinkDevice.setText(str(self.comboBox_BlinkDevice.currentText()))
        self.setConfigStatus(False)

    def setBlinkChannel(self):
        self.deviceDictionary['channels']['system']['blink channel'] = int(self.comboBox_BlinkChannel.currentIndex()+1)
        self.setConfigStatus(False)

    def setCoarsePositioner(self):
        self.deviceDictionary['devices']['system']['coarse positioner'] = str(self.comboBox_CoarsePositioner.currentText())
        self.setConfigStatus(False)

    def setSampleDACADC(self):
        self.deviceDictionary['devices']['sample']['dac_adc'] = str(self.comboBox_Sample_DACADC.currentText())
        self.setConfigStatus(False)

    def setSampleDCBox(self):
        self.deviceDictionary['devices']['sample']['dc_box'] = str(self.comboBox_Sample_DCBox.currentText())
        self.setConfigStatus(False)

    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.deviceDictionary['servers']['local'] = dict

            if not not dict['dac_adc']:
                list = yield dict['dac_adc'].list_devices()

                #For this section, adding the items to the comboBoxes
                for device in list:
                    self.GUIDictionary['devices']['scan']['dac_adc'].addItem(device[1])
                    self.GUIDictionary['devices']['nsot']['dac_adc'].addItem(device[1])
                    self.GUIDictionary['devices']['sample']['dac_adc'].addItem(device[1])
                    self.GUIDictionary['devices']['system']['specific supply'].addItem(device[1])
                    self.GUIDictionary['devices']['system']['blink device'].addItem(device[1])

                if len(list) > 0:
                    self.GUIDictionary['devices']['system']['magnet supply'].addItem('Toellner Power Supply')

            if not not dict['dc_box']:
                list = yield dict['dc_box'].list_devices()
                for device in list:
                    self.GUIDictionary['devices']['approach and TF']['dc_box'].addItem(device[1])
                    self.GUIDictionary['devices']['sample']['dc_box'].addItem(device[1])
                    self.GUIDictionary['devices']['system']['blink device'].addItem(device[1])

            if not not dict['hf2li']:
                list = yield dict['hf2li'].list_devices()
                for device in list:
                    self.comboBox_Approach_HF2LI.addItem(device[1])

            if not not dict['anc350']:
                self.comboBox_CoarsePositioner.addItem('Attocube ANC350')

            if not not dict['ami_430']:
                list = yield dict['ami_430'].list_devices()
                for device in list:
                    self.comboBox_MagnetSupplyDevice.addItem(device[1])

                if len(list) > 0:
                    self.comboBox_MagnetPowerSupply.addItem('AMI 430 Power Supply')

            self.localLabRADConnected = True
            if self.localLabRADConnected and self.remoteLabRADConnected:
                self.loadDefaultConfigurationInfo()
        except:
            printErrorInfo()

    @inlineCallbacks
    def connectRemoteLabRAD(self, dict):
        try:
            self.deviceDictionary['servers']['remote'] = dict

            if not not dict['ips120']:
                list = yield dict['ips120'].list_devices()
                for device in list:
                    self.comboBox_MagnetSupplyDevice.addItem(device[1])

                if len(list) > 0:
                    self.deviceDictionary['devices']['system']['specific supply'] = str(list[0][1])
                    self.comboBox_MagnetPowerSupply.addItem('IPS 120 Power Supply')

            self.remoteLabRADConnected = True
            if self.localLabRADConnected and self.remoteLabRADConnected:
                self.loadDefaultConfigurationInfo()
        except:
            printErrorInfo()

    def disconnectLabRAD(self):
        #Reinitialize deviceDictionary to be empty
        self.resetDeviceDictionary()
        self.localLabRADConnected = False
        self.remoteLabRADConnected = False

        #Remove all devices from the GUI
        for section, dev_list in self.GUIDictionary['devices'].items():
            for dev, dev_name in dev_list.items():
                self.GUIDictionary['devices'][section][dev].clear()
                self.GUIDictionary['devices'][section][dev].addItem('None')

    def loadDefaultConfigurationInfo(self):
        f = open(self.fileName,'r')
        defaultConfig = f.read()
        self.configFileName = defaultConfig
        self.label_currentConfigFile.setText(self.configFileName)
        f.close()

        self.loadConfigurationInfo()

    def loadNewConfigurationInfo(self):
        file = str(QtWidgets.QFileDialog.getOpenFileName(self, directory = path, filter = "Text files (*.txt)"))
        self.configFileName = file.split('/')[-1]
        self.label_currentConfigFile.setText(self.configFileName)

        self.loadConfigurationInfo()

    def loadConfigurationInfo(self):
        f = open(path + '\\' + self.configFileName,'r')
        message = f.read()
        f.close()

        entries = message.splitlines()
        #First 5 lines encode the device information
        for entry in entries[0:5]:
            entry = entry.split(';')
            name = entry[0]
            entry.remove(entry[0])
            for item in entry:
                item = item.split(',')
                self.deviceDictionary['devices'][name][item[0]] = item[1]

        #Next 5 lines encode the channel information
        for entry in entries[6:11]:
            entry = entry.split(';')
            name = entry[0]
            entry.remove(entry[0])
            for item in entry:
                item = item.split(',')
                self.deviceDictionary['channels'][name][item[0]] = int(item[1])
                self.GUIDictionary['channels'][name][item[0]].setCurrentIndex(int(item[1])-1)

        self.checkLoadedConfiguration()

    def checkLoadedConfiguration(self):
        try:
            #keep track of which parts of the loaded config file were not found
            configNotFound = ''

            #Check all the devices in all the sections
            for section, dev_list in self.deviceDictionary['devices'].items():
                for dev, dev_name in dev_list.items():
                    ComboBox = self.GUIDictionary['devices'][section][dev]
                    AllItems = [str(ComboBox.itemText(i)) for i in range(ComboBox.count())]

                    if dev_name in AllItems:
                        ComboBox.setCurrentIndex(AllItems.index(dev_name))
                    elif dev_name == 'False':
                        pass
                    else:
                        if len(AllItems) > 0:
                            self.deviceDictionary['devices'][section][dev] = AllItems[0]
                        else:
                            self.deviceDictionary['devices'][section][dev] = False
                        configNotFound = configNotFound + str(dev_name) + ' was not found in the ' + str(section) + ' tab for the following device: ' + dev + '.\n'

            #If something wasn't found, throw error letting user know that the config wasn't valid
            if len(configNotFound) > 0:
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setIcon(QtWidgets.QMessageBox.Information)
                msgBox.setWindowTitle('Loaded Configuration Invalid')
                message = '''\r\n The loaded configuration file cannot be properly loaded with the servers and devices currently connected to the computer. The following
                                connections cannot be made: \n''' + configNotFound
                msgBox.setText(message)
                msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()

            self.sendDeviceInfo()

        except:
            printErrorInfo()

    @inlineCallbacks
    def sendDeviceInfo(self):
        try:
            #Select the proper devices for the system general devices
            if self.deviceDictionary['devices']['system']['magnet supply'] == 'IPS 120 Power Supply':
                yield self.deviceDictionary['servers']['remote']['ips120'].select_device(self.deviceDictionary['devices']['system']['specific supply'])
            elif self.deviceDictionary['devices']['system']['magnet supply'] == 'AMI 430 Power Supply':
                yield self.deviceDictionary['servers']['local']['ami_430'].select_device(self.deviceDictionary['devices']['system']['specific supply'])
            elif self.deviceDictionary['devices']['system']['magnet supply'] == 'Toellner Power Supply':
                yield self.deviceDictionary['servers']['local']['dac_adc'].select_device(self.deviceDictionary['devices']['system']['specific supply'])

            self.newDeviceInfo.emit(self.deviceDictionary)
            self.setConfigStatus(True)
        except:
            printErrorInfo()

    def setDefaultConfiguration(self):
        f = open(self.fileName,'w')
        f.write(self.configFileName)
        f.close()
        print('Devices: ', self.deviceDictionary['devices'])
        print('Channels: ', self.deviceDictionary['channels'])

    def saveConfigurationInfo(self):
        file = str(QtWidgets.QFileDialog.getSaveFileName(self, directory = path, filter = "Text files (*.txt)"))
        if len(file) >0:
            f = open(file,'w')
            message  = ''
            #For now, only adding devices into the configuration file
            for section, dev_list in self.deviceDictionary['devices'].items():
                message = message + section + ';'
                for dev, dev_name in dev_list.items():
                    message = message + str(dev) + ',' + str(dev_name) + ';'
                message = message[:-1] + '\n'

            message = message + '\n'

            for section, dev_list in self.deviceDictionary['channels'].items():
                message = message + section + ';'
                for dev, dev_name in dev_list.items():
                    message = message + str(dev) + ',' + str(dev_name) + ';'
                message = message[:-1] + '\n'

            f.write(message)
            f.close()

            self.configFileName = file.split('/')[-1]
            self.label_currentConfigFile.setText(self.configFileName)

    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous
    # delay that allows other labrad / pyqt methods to run
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
