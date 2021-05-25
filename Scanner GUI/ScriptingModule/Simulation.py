import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred #, returnValue

path = sys.path[0] + r"\ScriptingModule"
SimulatorWindowUI, QtBaseClass = uic.loadUiType(path + r"\ScriptSimulator.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way.
sys.path.append(sys.path[0]+'\Resources')

class VirtualModule():
    '''
    A virtual modules to take inputs from a script. Will inherit to make a clone
    of a specific module, will have all documented scripting functions (from Marec's)
    thesis, but most of these will be dummy functions. We really just want functions
    that affect the outputs, which will be displayed.
    '''
    eventList = [] # This is a shared varaible, need to specify it when inheriting.

    def addEvent(self, name, *args, **kwargs):
        '''
        For the scripting functions that don't affect the output, still records them
        '''
        self.eventList.append([name, args, kwargs])
        return None
    #
#

class Virtual_nSOTBias(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setBias = lambda *args, **kwargs : self.addEvent('setBias', *args, **kwargs)
        self.readBias = lambda *args, **kwargs : self.addEvent('readBias', *args, **kwargs)
        self.setFeedback = lambda *args, **kwargs : self.addEvent('setFeedback', *args, **kwargs)
        self.readFeedback = lambda *args, **kwargs : self.addEvent('readFeedback', *args, **kwargs)
        self.blink = lambda *args, **kwargs : self.addEvent('blink', *args, **kwargs)
        self.setGate = lambda *args, **kwargs : self.addEvent('setGate', *args, **kwargs)
        self.readGate = lambda *args, **kwargs : self.addEvent('readGate', *args, **kwargs)
#

class Virtual_nSOTChar(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setMinVoltage = lambda *args, **kwargs : self.addEvent('setMinVoltage', *args, **kwargs)
        self.setMaxVoltage = lambda *args, **kwargs : self.addEvent('setMaxVoltage', *args, **kwargs)
        self.setVoltagePoints = lambda *args, **kwargs : self.addEvent('setVoltagePoints', *args, **kwargs)
        self.setMinField = lambda *args, **kwargs : self.addEvent('setMinField', *args, **kwargs)
        self.setMaxField = lambda *args, **kwargs : self.addEvent('setMaxField', *args, **kwargs)
        self.setFieldPoints = lambda *args, **kwargs : self.addEvent('setFieldPoints', *args, **kwargs)
        self.readFeedbackVoltage = lambda *args, **kwargs : self.addEvent('readFeedbackVoltage', *args, **kwargs)
        self.setSweepMode = lambda *args, **kwargs : self.addEvent('setSweepMode', *args, **kwargs)
        self.startSweep = lambda *args, **kwargs : self.addEvent('startSweep', *args, **kwargs)
#

class Virtual_SampleChar(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setFourTermMinVoltage = lambda *args, **kwargs : self.addEvent('setFourTermMinVoltage', *args, **kwargs)
        self.setFourTermMaxVoltage = lambda *args, **kwargs : self.addEvent('setFourTermMaxVoltage', *args, **kwargs)
        self.setFourTermVoltagePoints = lambda *args, **kwargs : self.addEvent('setFourTermVoltagePoints', *args, **kwargs)
        self.setFourTermVoltageStepSize = lambda *args, **kwargs : self.addEvent('setFourTermVoltageStepSize', *args, **kwargs)
        self.setFourTermDelay = lambda *args, **kwargs : self.addEvent('setFourTermDelay', *args, **kwargs)
        self.setFourTermOutput = lambda *args, **kwargs : self.addEvent('setFourTermOutput', *args, **kwargs)
        self.setFourTermVoltageInput = lambda *args, **kwargs : self.addEvent('setFourTermVoltageInput', *args, **kwargs)
        self.setFourTermCurrentInput = lambda *args, **kwargs : self.addEvent('setFourTermCurrentInput', *args, **kwargs)
        self.FourTerminalSweep = lambda *args, **kwargs : self.addEvent('FourTerminalSweep', *args, **kwargs)
        self.rampOutputVoltage = lambda *args, **kwargs : self.addEvent('rampOutputVoltage', *args, **kwargs)
#

class Virtual_TempControl(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.readTherm1 = lambda *args, **kwargs : self.addEvent('readTherm1', *args, **kwargs)
        self.readTherm2 = lambda *args, **kwargs : self.addEvent('readTherm2', *args, **kwargs)
        self.readTherm3 = lambda *args, **kwargs : self.addEvent('readTherm3', *args, **kwargs)
        self.setFeedbackThermometer = lambda *args, **kwargs : self.addEvent('setFeedbackThermometer', *args, **kwargs)
        self.setHeaterMode = lambda *args, **kwargs : self.addEvent('setHeaterMode', *args, **kwargs)
        self.setHeaterOutput = lambda *args, **kwargs : self.addEvent('setHeaterOutput', *args, **kwargs)
        self.setHeaterRange = lambda *args, **kwargs : self.addEvent('setHeaterRange', *args, **kwargs)
        self.setHeaterPID = lambda *args, **kwargs : self.addEvent('setHeaterPID', *args, **kwargs)
        self.setHeaterSetpoint = lambda *args, **kwargs : self.addEvent('setHeaterSetpoint', *args, **kwargs)
        self.setHeaterPercentage = lambda *args, **kwargs : self.addEvent('setHeaterPercentage', *args, **kwargs)
        self.setHeaterOn = lambda *args, **kwargs : self.addEvent('setHeaterOn', *args, **kwargs)
        self.setHeaterOff = lambda *args, **kwargs : self.addEvent('setHeaterOff', *args, **kwargs)
#

class Virtual_FieldControl(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setSetpoint = lambda *args, **kwargs : self.addEvent('setSetpoint', *args, **kwargs)
        self.setField = lambda *args, **kwargs : self.addEvent('setField', *args, **kwargs)
        self.readField = lambda *args, **kwargs : self.addEvent('readField', *args, **kwargs)
        self.readPersistField = lambda *args, **kwargs : self.addEvent('readPersistField', *args, **kwargs)
        self.hold = lambda *args, **kwargs : self.addEvent('hold', *args, **kwargs)
        self.clamp = lambda *args, **kwargs : self.addEvent('clamp', *args, **kwargs)
        self.setPersist = lambda *args, **kwargs : self.addEvent('setPersist', *args, **kwargs)
#

class Virtual_Approach(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setPLLThreshold = lambda *args, **kwargs : self.addEvent('setPLLThreshold', *args, **kwargs)
        self.withdraw = lambda *args, **kwargs : self.addEvent('withdraw', *args, **kwargs)
        self.setHeight = lambda *args, **kwargs : self.addEvent('setHeight', *args, **kwargs)
        self.approachConstHeight = lambda *args, **kwargs : self.addEvent('approachConstHeight', *args, **kwargs)
        self.getContactPosition = lambda *args, **kwargs : self.addEvent('getContactPosition', *args, **kwargs)
        self.setFrustratedFeedback = lambda *args, **kwargs : self.addEvent('setFrustratedFeedback', *args, **kwargs)
#

class Virtual_ScanControl(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setPosition = lambda *args, **kwargs : self.addEvent('setPosition', *args, **kwargs)
        self.startScan = lambda *args, **kwargs : self.addEvent('startScan', *args, **kwargs)
        self.setSpeed = lambda *args, **kwargs : self.addEvent('setSpeed', *args, **kwargs)
        self.setDelay = lambda *args, **kwargs : self.addEvent('setDelay', *args, **kwargs)
        self.setPixels = lambda *args, **kwargs : self.addEvent('setPixels', *args, **kwargs)
        self.lockDataAspect = lambda *args, **kwargs : self.addEvent('lockDataAspect', *args, **kwargs)
        self.unlockDataAspect = lambda *args, **kwargs : self.addEvent('unlockDataAspect', *args, **kwargs)
        self.setTilt = lambda *args, **kwargs : self.addEvent('setTilt', *args, **kwargs)
        self.setXc = lambda *args, **kwargs : self.addEvent('setXc', *args, **kwargs)
        self.setYc = lambda *args, **kwargs : self.addEvent('setYc', *args, **kwargs)
        self.setH = lambda *args, **kwargs : self.addEvent('setH', *args, **kwargs)
        self.setW = lambda *args, **kwargs : self.addEvent('setW', *args, **kwargs)
        self.setAngle = lambda *args, **kwargs : self.addEvent('setAngle', *args, **kwargs)
        self.lockScanAspect = lambda *args, **kwargs : self.addEvent('lockScanAspect', *args, **kwargs)
        self.unlockScanAspect = lambda *args, **kwargs : self.addEvent('unlockScanAspect', *args, **kwargs)
    #


class ScriptSimulator(QtGui.QMainWindow, SimulatorWindowUI):
    '''
    A window to display the potential experimental outputs of a given script to
    evaluate it prior to running the script.
    '''
    def __init__(self, reactor, parent=None, *args):
        super(ScriptSimulator, self).__init__(parent)

        self.reactor = reactor

        self.setupUi(self)

        # instantiate all the virtual modules
        self.scanControl = Virtual_ScanControl()
        self.Approach = Virtual_Approach()
        self.nSOTChar = Virtual_nSOTChar()
        self.FieldControl = Virtual_FieldControl()
        self.TempControl = Virtual_TempControl()
        self.SampleChar = Virtual_SampleChar()
        self.nSOTBias = Virtual_nSOTBias()
    #

    def get_virtual_modules(self):
        '''
        Return all the virtual modules
        '''
        return self.scanControl, self.Approach, self.nSOTChar, self.FieldControl, self.TempControl, self.SampleChar, self.nSOTBias,
    #

    def sleep(self, secs):
        '''
        Takes the place of the sleep command without actually sleeping the program.
        '''
        print("sleeping " + str(secs))
    #

    def compile(self):
        '''
        Takes all the data from the virtual modules
        '''
        print(VirtualModule.eventList)
    #

    def showSim(self):
        '''
        Display the simulation module
        '''

        self.showNormal()
        self.moveDefault()
        self.raise_()

    def moveDefault(self):
        self.move(10,170)
    #


#
