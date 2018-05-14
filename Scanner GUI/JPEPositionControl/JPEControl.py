import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred

path = sys.path[0] + r"\JPEPositionControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\JPEControl.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, ScanControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()        

        #initialize default values
        self.temperature = 293   #Experiment temperature
        self.tip_height = 24e-3 #Tip height from sample stage in meters. 
        self.module_address = 1  #Pretty sure this is always 1 unless we add more modules to the JPE controller
        self.steps = 1000        #Number of step forward in z direction taken by JPEs after attocube fully extend and retract
        self.size = 100          #relative step size of jpe steps
        self.freq = 600          #Frequency of steps on JPE approach

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        
        #Initialize all the labrad connections as none
        self.cxn = None
        self.cpsc = None

        self.lineEdit_Temperature.editingFinished.connect(self.setTemperature)
        self.lineEdit_Tip_Height.editingFinished.connect(self.setJPE_Tip_Height)
        self.comboBox_JPE_Address.currentIndexChanged.connect(self.setJPE_Address)
        
        self.lineEdit_JPE_Approach_Steps.editingFinished.connect(self.setJPE_Approach_Steps)
        self.lineEdit_JPE_Approach_Size.editingFinished.connect(self.setJPE_Approach_Size)
        self.lineEdit_JPE_Approach_Freq.editingFinished.connect(self.setJPE_Approach_Freq)

        self.push_movePosX.clicked.connect(self.movePosX)
        self.push_moveNegX.clicked.connect(self.moveNegX)
        self.push_movePosY.clicked.connect(self.movePosY)
        self.push_moveNegY.clicked.connect(self.moveNegY)
        self.push_movePosZ.clicked.connect(self.movePosZ)
        self.push_moveNegZ.clicked.connect(self.moveNegZ)

        self.lockInterface()
        
    def moveDefault(self):    
        self.move(550,10)
        
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['cxn']
            self.cpsc = dict['cpsc']
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  
        if not self.cxn:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        elif not self.cpsc:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")
        else:
            self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            self.serversConnected = True
            self.unlockInterface()

    def disconnectLabRAD(self):
        self.dv = None
        self.cxn = None
        self.push_Servers.setStyleSheet("#push_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.lockInterface()

    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        pass

    def setTemperature(self):
        val = readNum(str(self.lineEdit_Temperature.text()))
        if isinstance(val,float):
            self.temperature = int(val)
        self.lineEdit_Temperature.setText(formatNum(self.temperature))
    
    def setJPE_Tip_Height(self, c = None):
        val = readNum(str(self.lineEdit_Tip_Height.text()))
        if isinstance(val,float):
            self.tip_height = val
        self.lineEdit_Tip_Height.setText(formatNum(self.tip_height))

    def setJPE_Address(self):
        self.module_address = self.comboBox_JPE_Address.currentIndex() + 1
    
    def setJPE_Approach_Steps(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Steps.text()))
        if isinstance(val,float):
            self.steps = val
        self.lineEdit_JPE_Approach_Steps.setText(formatNum(self.steps))
        
    def setJPE_Approach_Size(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Size.text()))
        if isinstance(val,float):
            self.size = int(val)
        self.lineEdit_JPE_Approach_Size.setText(formatNum(self.size))
        
    def setJPE_Approach_Freq(self):
        val = readNum(str(self.lineEdit_JPE_Approach_Freq.text()))
        if isinstance(val,float):
            self.freq = int(val)
        self.lineEdit_JPE_Approach_Freq.setText(formatNum(self.freq))

    @inlineCallbacks
    def movePosX(self, c = None):
        self.lockInterface()
        yield self.cpsc.set_height(self.tip_height+33.9)
        if self.checkBox_Torque.isChecked():
            yield self.cpsc.move_x(self.module_address, self.temperature, self.freq, self.size, self.steps, 30)
        else: 
            yield self.cpsc.move_x(self.module_address, self.temperature, self.freq, self.size, self.steps)
        self.unlockInterface()

    @inlineCallbacks
    def moveNegX(self, c = None):
        self.lockInterface()
        yield self.cpsc.set_height(self.tip_height+33.9)
        if self.checkBox_Torque.isChecked():
            yield self.cpsc.move_x(self.module_address, self.temperature, self.freq, self.size, -self.steps, 30)
        else:
            yield self.cpsc.move_x(self.module_address, self.temperature, self.freq, self.size, -self.steps)
        self.unlockInterface()

    @inlineCallbacks
    def movePosY(self, c = None):
        self.lockInterface()
        yield self.cpsc.set_height(self.tip_height+33.9)
        if self.checkBox_Torque.isChecked():
            yield self.cpsc.move_y(self.module_address, self.temperature, self.freq, self.size, self.steps, 30)
        else:
            yield self.cpsc.move_y(self.module_address, self.temperature, self.freq, self.size, self.steps)
        self.unlockInterface()

    @inlineCallbacks
    def moveNegY(self, c = None):
        self.lockInterface()
        yield self.cpsc.set_height(self.tip_height+33.9)
        if self.checkBox_Torque.isChecked():
            yield self.cpsc.move_y(self.module_address, self.temperature, self.freq, self.size, -self.steps, 30)
        else:
            yield self.cpsc.move_y(self.module_address, self.temperature, self.freq, self.size, -self.steps)
        self.unlockInterface()

    @inlineCallbacks
    def movePosZ(self, c = None):
        self.lockInterface()
        yield self.cpsc.set_height(self.tip_height+33.9)
        if self.checkBox_Torque.isChecked():
            yield self.cpsc.move_z(self.module_address, self.temperature, self.freq, self.size, self.steps, 30)
        else:
            yield self.cpsc.move_z(self.module_address, self.temperature, self.freq, self.size, self.steps)
        self.unlockInterface()

    @inlineCallbacks
    def moveNegZ(self, c = None):
        self.lockInterface()
        yield self.cpsc.set_height(self.tip_height+33.9)
        if self.checkBox_Torque.isChecked():
            yield self.cpsc.move_z(self.module_address, self.temperature, self.freq, self.size, -self.steps, 30)
        else:
            yield self.cpsc.move_z(self.module_address, self.temperature, self.freq, self.size, -self.steps)
        self.unlockInterface()

    def updateApproachStatus(self, status):
        if status:
            self.lockInterface()
        else:
            self.unlockInterface()
        
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
        self.comboBox_JPE_Address.setEnabled(False)

        self.push_moveNegZ.setEnabled(False)
        self.push_movePosZ.setEnabled(False)
        self.push_moveNegY.setEnabled(False)
        self.push_movePosY.setEnabled(False)
        self.push_moveNegX.setEnabled(False)
        self.push_movePosX.setEnabled(False)

        self.checkBox_Torque.setEnabled(False)
        
    def unlockInterface(self):
        self.lineEdit_Temperature.setEnabled(True)
        self.lineEdit_Tip_Height.setEnabled(True)
        self.lineEdit_JPE_Approach_Freq.setEnabled(True)
        self.lineEdit_JPE_Approach_Size.setEnabled(True)
        self.lineEdit_JPE_Approach_Steps.setEnabled(True)
        self.comboBox_JPE_Address.setEnabled(True)

        self.push_moveNegZ.setEnabled(True)
        self.push_movePosZ.setEnabled(True)
        self.push_moveNegY.setEnabled(True)
        self.push_movePosY.setEnabled(True)
        self.push_moveNegX.setEnabled(True)
        self.push_movePosX.setEnabled(True)

        self.checkBox_Torque.setEnabled(True)
        
class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)