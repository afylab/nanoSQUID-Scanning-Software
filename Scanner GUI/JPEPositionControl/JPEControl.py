import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred

path = sys.path[0] + r"\JPEPositionControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\JPEControl.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    newJPESettings = QtCore.pyqtSignal(dict)
    updateJPEConnectStatus = QtCore.pyqtSignal(bool)
    
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()

        #initialize default values
        self.JPESettings = {
        'temp'                  : 293, #Experiment temperature
        'module_address'        : 1,   #Pretty sure this is always 1 unless we add more modules to the JPE controller
        'toggle_channel'        : 3,   #DC Box channel use to toggle the JPEs between connected and not. 1 indexed
        }
        #By default JPEs are disconnected when voltage is 0
        self.JPEConnected = False
        
        self.steps = 1000        #Number of step forward in z direction taken by JPEs after attocube fully extend and retract
        self.size = 100          #relative step size of jpe steps
        self.freq = 600          #Frequency of steps on JPE approach
        self.weight_for = [1.0, 1.0, 1.0]
        self.weight_back = [1.0, 1.0, 1.0]
        self.tip_height = 24 #Tip height from JPE stage in millimeters. 
        
        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize all the labrad connections as False
        self.cxn = False
        self.cpsc = False
        self.dcbox = False
        
        self.lineEdit_Temperature.editingFinished.connect(self.setTemperature)
        self.lineEdit_Tip_Height.editingFinished.connect(self.setJPE_Tip_Height)
        self.comboBox_JPE_Address.currentIndexChanged.connect(self.setJPE_Address)
        self.comboBox_JPE_Toggle.currentIndexChanged.connect(self.setJPE_Toggle_Channel)
        
        self.lineEdit_JPE_Approach_Steps.editingFinished.connect(self.setJPE_Approach_Steps)
        self.lineEdit_JPE_Approach_Size.editingFinished.connect(self.setJPE_Approach_Size)
        self.lineEdit_JPE_Approach_Freq.editingFinished.connect(self.setJPE_Approach_Freq)

        self.lineEdit_weight_for_A.editingFinished.connect(self.setForwardJPEWeightA)
        self.lineEdit_weight_for_B.editingFinished.connect(self.setForwardJPEWeightB)
        self.lineEdit_weight_for_C.editingFinished.connect(self.setForwardJPEWeightC)
        self.lineEdit_weight_back_A.editingFinished.connect(self.setBackwardJPEWeightA)
        self.lineEdit_weight_back_B.editingFinished.connect(self.setBackwardJPEWeightB)
        self.lineEdit_weight_back_C.editingFinished.connect(self.setBackwardJPEWeightC)
        
        self.push_JPEConnect.clicked.connect(self.toggleJPEConnection)
        
        self.push_movePosX.clicked.connect(self.movePosX)
        self.push_moveNegX.clicked.connect(self.moveNegX)
        self.push_movePosY.clicked.connect(self.movePosY)
        self.push_moveNegY.clicked.connect(self.moveNegY)
        self.push_movePosZ.clicked.connect(self.movePosZ)
        self.push_moveNegZ.clicked.connect(self.moveNegZ)

        self.lockInterface()
        
    def moveDefault(self):
        self.move(550,10)
        
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.cpsc = dict['servers']['local']['cpsc']
            
            #Create another connection for the connection to data vault to prevent 
            #problems of multiple windows trying to write the data vault at the same
            #time
            from labrad.wrappers import connectAsync
            self.cxn_jpe = yield connectAsync(host = '127.0.0.1', password = 'pass')
            
            self.dcbox = yield self.cxn_jpe.ad5764_dcbox
            self.dcbox.select_device(dict['devices']['approach and TF']['dc_box'])
            
            yield self.cpsc.set_height(self.tip_height+33.9)
            
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            self.serversConnected = True
            self.unlockInterface()

        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  

    def disconnectLabRAD(self):
        self.cpsc = False
        self.cxn = False
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.lockInterface()

    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        pass

    def setTemperature(self):
        val = readNum(str(self.lineEdit_Temperature.text()), self, False)
        if isinstance(val,float):
            self.JPESettings['temp'] = int(val)
            self.newJPESettings.emit(self.JPESettings)
        self.lineEdit_Temperature.setText(formatNum(self.JPESettings['temp']))
    
    @inlineCallbacks
    def setJPE_Tip_Height(self, c = None):
        val = readNum(str(self.lineEdit_Tip_Height.text()), self)
        if isinstance(val,float):
            self.tip_height = val
            yield self.cpsc.set_height(self.tip_height*1000+33.9)
        self.lineEdit_Tip_Height.setText(formatNum(self.tip_height))

    def setJPE_Address(self):
        self.JPESettings['module_address'] = self.comboBox_JPE_Address.currentIndex() + 1
        self.newJPESettings.emit(self.JPESettings)
        
    def setJPE_Approach_Steps(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Steps.text()), self, False)
        if isinstance(val,float):
            self.steps = val
        self.lineEdit_JPE_Approach_Steps.setText(formatNum(self.steps))
        
    def setJPE_Approach_Size(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Size.text()), self, False)
        if isinstance(val,float):
            self.size = int(val)
        self.lineEdit_JPE_Approach_Size.setText(formatNum(self.size))
        
    def setJPE_Approach_Freq(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Freq.text()), self, False)
        if isinstance(val,float):
            self.freq = int(val)
        self.lineEdit_JPE_Approach_Freq.setText(formatNum(self.freq))
        
    def setJPE_Toggle_Channel(self):
        self.JPESettings['toggle_channel'] = self.comboBox_JPE_Toggle.currentIndex()+1
        self.newJPESettings.emit(self.JPESettings)
        
    @inlineCallbacks
    def toggleJPEConnection(self, c = None):
        if not self.JPEConnected:
            yield self.dcbox.set_voltage(self.JPESettings['toggle_channel'] - 1, 10)
            style = '''#push_JPEConnect{
                    image: url(:/nSOTScanner/Pictures/Connected.png);
                    background: black;
                    }
                    '''
            self.push_JPEConnect.setStyleSheet(style)
            self.JPEConnected = True
        else: 
            yield self.dcbox.set_voltage(self.JPESettings['toggle_channel'] - 1, 0)
            style = '''#push_JPEConnect{
                    image: url(:/nSOTScanner/Pictures/Disconnected.png);
                    background: black;
                    }
                    '''
            self.push_JPEConnect.setStyleSheet(style)
            self.JPEConnected = False
        self.updateJPEConnectStatus.emit(self.JPEConnected)

    def updateJPEConnected(self, connected):
        self.JPEConnected = connected
        if connected:
            style = '''#push_JPEConnect{
                    image: url(:/nSOTScanner/Pictures/Connected.png);
                    background: black;
                    }
                    '''
            self.push_JPEConnect.setStyleSheet(style)
        else:
            style = '''#push_JPEConnect{
                    image: url(:/nSOTScanner/Pictures/Disconnected.png);
                    background: black;
                    }
                    '''
            self.push_JPEConnect.setStyleSheet(style)
            
    def throwWeightsWarning(self):
        msgBox = QtGui.QMessageBox(self)
        msgBox.setIcon(QtGui.QMessageBox.Information)
        msgBox.setWindowTitle('JPE Step Sizes Set Improperly')
        msgBox.setText("\r\n The relative step sizes for the JPEs are set improperly. The relative step size for one or more of the knobs is set to 0.")
        msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
        msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
        msgBox.exec_()
        
    @inlineCallbacks
    def movePosX(self, c = None):
        if not self.cpsc.checkweights():
            self.throwWeightsWarning()
        else:
            self.lockInterface()
            if self.checkBox_Torque.isChecked():
                yield self.cpsc.move_x(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, self.steps, 30)
            else: 
                yield self.cpsc.move_x(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, self.steps)
            self.unlockInterface()

    @inlineCallbacks
    def moveNegX(self, c = None):
        if not self.cpsc.checkweights():
            self.throwWeightsWarning()
        else:
            self.lockInterface()
            if self.checkBox_Torque.isChecked():
                yield self.cpsc.move_x(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, -self.steps, 30)
            else:
                yield self.cpsc.move_x(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, -self.steps)
            self.unlockInterface()

    @inlineCallbacks
    def movePosY(self, c = None):
        if not self.cpsc.checkweights():
            self.throwWeightsWarning()
        else:
            self.lockInterface()
            if self.checkBox_Torque.isChecked():
                yield self.cpsc.move_y(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, self.steps, 30)
            else:
                yield self.cpsc.move_y(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, self.steps)
            self.unlockInterface()

    @inlineCallbacks
    def moveNegY(self, c = None):
        if not self.cpsc.checkweights():
            self.throwWeightsWarning()
        else:
            self.lockInterface()
            if self.checkBox_Torque.isChecked():
                yield self.cpsc.move_y(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, -self.steps, 30)
            else:
                yield self.cpsc.move_y(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, -self.steps)
            self.unlockInterface()

    @inlineCallbacks
    def movePosZ(self, c = None):
        if not self.cpsc.checkweights():
            self.throwWeightsWarning()
        else:
            self.lockInterface()
            if self.checkBox_Torque.isChecked():
                yield self.cpsc.move_z(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, self.steps, 30)
            else:
                yield self.cpsc.move_z(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, self.steps)
            self.unlockInterface()

    @inlineCallbacks
    def moveNegZ(self, c = None):
        if not self.cpsc.checkweights():
            self.throwWeightsWarning()
        else:
            self.lockInterface()
            if self.checkBox_Torque.isChecked():
                yield self.cpsc.move_z(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, -self.steps, 30)
            else:
                yield self.cpsc.move_z(self.JPESettings['module_address'], self.JPESettings['temp'], self.freq, self.size, -self.steps)
            self.unlockInterface()

    def updateApproachStatus(self, status):
        if status:
            self.lockInterface()
        else:
            self.unlockInterface()
    
    @inlineCallbacks
    def setForwardJPEWeightA(self, c = None):
        val = readNum(str(self.lineEdit_weight_for_A.text()), self, False)
        if isinstance(val,float):
            if  val <= 0:
                val = 0
            self.weight_for[0] = val
            yield self.cpsc.setrelativestepsize(self.weight_for, self.weight_back)
        self.lineEdit_weight_for_A.setText(formatNum(self.weight_for[0]))
            
    @inlineCallbacks
    def setForwardJPEWeightB(self, c = None):
        val = readNum(str(self.lineEdit_weight_for_B.text()), self, False)
        if isinstance(val,float):
            if  val <= 0:
                val = 0
            self.weight_for[1] = val
            yield self.cpsc.setrelativestepsize(self.weight_for, self.weight_back)
        self.lineEdit_weight_for_B.setText(formatNum(self.weight_for[1]))
        
    @inlineCallbacks
    def setForwardJPEWeightC(self, c = None):
        val = readNum(str(self.lineEdit_weight_for_C.text()), self, False)
        if isinstance(val,float):
            if  val <= 0:
                val = 0
            self.weight_for[2] = val
            yield self.cpsc.setrelativestepsize(self.weight_for, self.weight_back)
        self.lineEdit_weight_for_C.setText(formatNum(self.weight_for[2]))
        
    @inlineCallbacks
    def setBackwardJPEWeightA(self, c = None):
        val = readNum(str(self.lineEdit_weight_back_A.text()), self, False)
        if isinstance(val,float):
            if  val <= 0:
                val = 0
            self.weight_back[0] = val
            yield self.cpsc.setrelativestepsize(self.weight_for, self.weight_back)
        self.lineEdit_weight_back_A.setText(formatNum(self.weight_back[0]))
            
    @inlineCallbacks
    def setBackwardJPEWeightB(self, c = None):
        val = readNum(str(self.lineEdit_weight_back_B.text()), self, False)
        if isinstance(val,float):
            if  val <= 0:
                val = 0
            self.weight_back[1] = val
            yield self.cpsc.setrelativestepsize(self.weight_for, self.weight_back)
        self.lineEdit_weight_back_B.setText(formatNum(self.weight_back[1]))
        
    @inlineCallbacks
    def setBackwardJPEWeightC(self, c = None):
        val = readNum(str(self.lineEdit_weight_back_C.text()), self, False)
        if isinstance(val,float):
            if  val <= 0:
                val = 0
            self.weight_back[2] = val
            yield self.cpsc.setrelativestepsize(self.weight_for, self.weight_back)
        self.lineEdit_weight_back_C.setText(formatNum(self.weight_back[2]))
        
    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()
            
    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous 
    # delay that allows other labrad / pyqt methods to run   
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""
           
    def lockInterface(self):
        self.lineEdit_Temperature.setEnabled(False)
        self.lineEdit_Tip_Height.setEnabled(False)
        self.lineEdit_JPE_Approach_Freq.setEnabled(False)
        self.lineEdit_JPE_Approach_Size.setEnabled(False)
        self.lineEdit_JPE_Approach_Steps.setEnabled(False)
        self.lineEdit_weight_for_A.setEnabled(False)
        self.lineEdit_weight_for_B.setEnabled(False)
        self.lineEdit_weight_for_C.setEnabled(False)
        self.lineEdit_weight_back_A.setEnabled(False)
        self.lineEdit_weight_back_B.setEnabled(False)
        self.lineEdit_weight_back_C.setEnabled(False)
        
        self.comboBox_JPE_Address.setEnabled(False)
        self.comboBox_JPE_Toggle.setEnabled(False)
        
        self.push_moveNegZ.setEnabled(False)
        self.push_movePosZ.setEnabled(False)
        self.push_moveNegY.setEnabled(False)
        self.push_movePosY.setEnabled(False)
        self.push_moveNegX.setEnabled(False)
        self.push_movePosX.setEnabled(False)
        
        self.push_JPEConnect.setEnabled(False)

        self.checkBox_Torque.setEnabled(False)
        
    def unlockInterface(self):
        self.lineEdit_Temperature.setEnabled(True)
        self.lineEdit_Tip_Height.setEnabled(True)
        self.lineEdit_JPE_Approach_Freq.setEnabled(True)
        self.lineEdit_JPE_Approach_Size.setEnabled(True)
        self.lineEdit_JPE_Approach_Steps.setEnabled(True)
        self.lineEdit_weight_for_A.setEnabled(True)
        self.lineEdit_weight_for_B.setEnabled(True)
        self.lineEdit_weight_for_C.setEnabled(True)
        self.lineEdit_weight_back_A.setEnabled(True)
        self.lineEdit_weight_back_B.setEnabled(True)
        self.lineEdit_weight_back_C.setEnabled(True)
        
        self.comboBox_JPE_Address.setEnabled(True)
        self.comboBox_JPE_Toggle.setEnabled(True)
        
        self.push_moveNegZ.setEnabled(True)
        self.push_movePosZ.setEnabled(True)
        self.push_moveNegY.setEnabled(True)
        self.push_movePosY.setEnabled(True)
        self.push_moveNegX.setEnabled(True)
        self.push_movePosX.setEnabled(True)
        
        self.push_JPEConnect.setEnabled(True)

        self.checkBox_Torque.setEnabled(True)
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)