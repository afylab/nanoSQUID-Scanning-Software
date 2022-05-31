import sys
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QRect
from twisted.internet.defer import inlineCallbacks, Deferred
from nSOTScannerFormat import readNum, formatNum, printErrorInfo

path = sys.path[0] + r"\FieldControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\FieldControl-multiple.ui")
MagnetWidget, QtBaseClass = uic.loadUiType(path + r"\magnet-widget.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

class Window(QtWidgets.QMainWindow, ScanControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.moveDefault()

    def configureMagnetUi(self, equip):
        n = 1
        if 'Magnet Z' in equip.servers:
            self.Z = MagnetUI(self.reactor, 'Magnet Z', self.magnet_frame)
            self.Z.move(0, (n-1)*200)

        if 'Magnet X' in equip.servers:
            self.X = MagnetUI(self.reactor, 'Magnet X', self.magnet_frame)
            self.X.magnet_label.setText('X')
            n += 1
            self.X.move(0, (n-1)*200)

        if 'Magnet Y' in equip.servers:
            self.Y = MagnetUI(self.reactor, 'Magnet Y', self.magnet_frame)
            self.Y.magnet_label.setText('Y')
            n += 1
            self.Y.move(0, (n-1)*200)
        self.setGeometry(QRect(0, 0, 690, n*200+25))

    def moveDefault(self):
        self.move(550,10)

    #@inlineCallbacks
    def connectLabRAD(self, equip):
        if hasattr(self, "Z"):
            self.Z.connectLabRAD(equip)
        if hasattr(self, "X"):
            self.X.connectLabRAD(equip)
        if hasattr(self, "Y"):
            self.Y.connectLabRAD(equip)

    #@inlineCallbacks
    def disconnectLabRAD(self):
        if hasattr(self, "Z"):
            self.Z.disconnectLabRAD()
        if hasattr(self, "X"):
            self.X.disconnectLabRAD()
        if hasattr(self, "Y"):
            self.Y.disconnectLabRAD()

class MagnetUI(QtWidgets.QWidget, MagnetWidget):
    def __init__(self, reactor, magnetref, parent=None):
        super(MagnetUI, self).__init__(parent)
        self.magnetref = magnetref

        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        self.push_GotoSet.clicked.connect(lambda: self.goToSetpoint())
        self.push_GotoZero.clicked.connect(lambda: self.gotoZero())

        self.lineEdit_setpoint.editingFinished.connect(self.setSetpoint)
        self.lineEdit_ramprate.editingFinished.connect(self.setRamprate)

        self.autopersist_checkBox.clicked.connect(self.toggleAutoPersist)
        self.push_magReset.clicked.connect(lambda: self.resetMagnet())

        self.controller = False

        self.currField = 0
        self.currCurrent = 0
        self.persistField = 0
        self.persistCurrent = 0
        self.currVoltage = 0
        self.setpoint = 0
        self.ramprate = 0

        self.setting_value = False
        #By default, the switch is off, which corresponds to being in persist mode
        self.persist = True

        self.push_hold.hide()
        self.push_clamp.hide()
        self.lockInterface()

    @inlineCallbacks
    def connectLabRAD(self, equip):
        if self.magnetref in equip.servers:
            svr, ln, device_info, cnt, config = equip.servers[self.magnetref]
            if svr:
                self.controller = cnt
            else:
                print(str(self.magnetref)+" not found, LabRAD connection to FieldControl Failed.")
                return
        else:
            print(str(self.magnetref)+" not found, LabRAD connection to FieldControl Failed.")
            return

        if hasattr(self.controller, "clamp"):
            self.push_clamp.clicked.connect(lambda: self.controller.clamp())
            self.push_clamp.show()

        if hasattr(self.controller, "hold"):
            self.push_hold.clicked.connect(lambda: self.controller.hold())
            self.push_hold.show()

        if hasattr(self.controller, "togglePersist"):
            self.push_persistSwitch.clicked.connect(lambda: self.togglePersist())

        try:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            yield self.loadInitialValues()
            self.unlockInterface()
            self.monitor = True #modified temporarily
            yield self.monitorField() # Loops to monitor field
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")

    def disconnectLabRAD(self):
        self.monitor = False
        # Since updaitng is slow turn the controller to false after it exits loop
        #self.controller = False
        self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")
        self.lockInterface()

    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()

    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        pass

    @inlineCallbacks
    def monitorField(self):
        try:
            while self.monitor:
                if not self.setting_value and not self.controller.sweeping:
                    yield self.controller.poll()
                self.currField = self.controller.B
                self.currCurrent = self.controller.current
                self.persistField = self.controller.persist_B
                self.persistCurrent = self.controller.persist_current
                self.currVoltage = self.controller.output_voltage
                self.updateSwitchStatus()
                try:
                    self.label_persist_fieldval.setText(formatNum(self.persistField,3))
                    self.label_persist_currentval.setText(formatNum(self.persistCurrent,3))
                    self.label_fieldval.setText(formatNum(self.currField,3))
                    self.label_currentval.setText(formatNum(self.currCurrent,3))
                    self.label_outputvoltage.setText(formatNum(self.currVoltage,3))
                except:
                    printErrorInfo()
                yield self.sleep(0.5)

            if not self.monitor:
                self.controller = False
        except:
            if self.monitor: # Sometimes there are issues setting things to None when disconnecting labRAD, don't worry about those
                printErrorInfo()

    @inlineCallbacks
    def loadInitialValues(self):
        try:
            yield self.controller.readInitialValues()
            yield self.controller.poll()
            self.updateSwitchStatus()

            self.lineEdit_setpoint.setText(formatNum(self.controller.setpoint_B))
            self.lineEdit_ramprate.setText(formatNum(self.controller.ramprate))
        except Exception as inst:
            print(inst)
            printErrorInfo()

    def updateSwitchStatus(self):
        if self.controller.persist:
            style = '''#push_persistSwitch{
                        background: rgb(0, 170, 0);
                        border-radius: 10px;
                        }'''
            self.push_persistSwitch.setStyleSheet(style)
            self.label_switchStatus.setText('Persistent')
        else:
            if self.controller.sweeping:
                style = '''#push_persistSwitch{
                            background: rgb(0, 0, 152);
                            border-radius: 10px;
                            }'''
                self.push_persistSwitch.setStyleSheet(style)
                self.label_switchStatus.setText('Sweeping')
            elif self.controller.status == "Charging":
                style = '''#push_persistSwitch{
                            background: rgb(0, 0, 152);
                            border-radius: 10px;
                            }'''
                self.push_persistSwitch.setStyleSheet(style)
                self.label_switchStatus.setText('Charging')
            else:
                style = '''#push_persistSwitch{
                            background: rgb(161, 0, 0);
                            border-radius: 10px;
                            }'''
                self.push_persistSwitch.setStyleSheet(style)
                self.label_switchStatus.setText('Error')

    def setSetpoint(self, val = None):
        if str(self.lineEdit_setpoint.text()).lower() == 'abort':
            return
        if val is None:
            val = readNum(str(self.lineEdit_setpoint.text()))
        if isinstance(val,float):
            self.controller.setSetpoint(val)
            self.setpoint = self.controller.setpoint_B
        self.lineEdit_setpoint.setText(formatNum(self.setpoint, 4))

    def setRamprate(self, val=None):
        if val is None:
            val = readNum(str(self.lineEdit_ramprate.text()))
        if isinstance(val,float):
            self.ramprate = val
            self.setting_value = True
            self.controller.setRampRate(self.ramprate)
            self.setting_value = False
        self.lineEdit_ramprate.setText(formatNum(self.ramprate))


    @inlineCallbacks
    def goToSetpoint(self):
        try:
            if self.controller.sweeping and self.controller.autopersist:
                print("Error cannot goToSetpoint: Magnet is already sweeping")
                return
            if str(self.lineEdit_setpoint.text()).lower() == 'abort': # Hack to prevent softlocking
                print("Breaking out of sweep loop and going into manual mode. Magnet may still keep sweeping but you can now enter commands.")
                self.autopersist_checkBox.setChecked(False)
                self.controller.autopersist = False
                self.controller.abort_wait = True
                return
            self.setSetpoint()
            self.setRamprate()
            print("")
            print("Setting magnet to", self.setpoint, "T at", self.ramprate, "T/min")
            self.setting_value = True
            if self.controller.autopersist:
                yield self.controller.startSweeping()
                self.setSetpoint()
                self.setRamprate()
                yield self.controller.goToSetpoint(wait=True)
                yield self.controller.doneSweeping()
                print("Done Sweeping to Setpoint")
            else:
                yield self.controller.goToSetpoint(wait=False)
            self.setting_value = False
            self.updateSwitchStatus()
        except:
            printErrorInfo()
    #

    @inlineCallbacks
    def gotoZero(self):
        try:
            if self.controller.sweeping:
                print("Warning: Magnet is already sweeping. Zeroing may cause issues for other processes.")
            print("Zeroing the magnet supply.")
            self.setting_value = True
            if self.controller.autopersist:
                yield self.controller.startSweeping()
                self.setRamprate()
                yield self.controller.goToZero(wait=True)
                yield self.controller.doneSweeping()
                print("Done Zeroing the magnet.")
            else:
                self.setRamprate()
                yield self.controller.goToZero(wait=False)
            self.setting_value = False
            self.updateSwitchStatus()
        except:
            printErrorInfo()
    #

    @inlineCallbacks
    def togglePersist(self, state=None):
        '''
        If state is none, just toggle. If True or false will turn persistent mode on or off (On means heater is off).
        '''
        try:
            if not self.setting_value:
                self.setting_value = True
                if isinstance(state, bool):
                    if state and not self.controller.persist:
                        yield self.controller.togglePersist()
                    elif not state and self.controller.persist:
                        yield self.controller.togglePersist()
                else:
                    yield self.controller.togglePersist()
                self.setting_value = False
                self.updateSwitchStatus()
        except:
            printErrorInfo()

    def toggleAutoPersist(self, state=None):
        '''
        If state is none, just toggle. If True or false will turn autopersist on or off.
        '''
        try:
            self.setting_value = True
            if isinstance(state, bool):
                if state and not self.controller.autopersist:
                    self.autopersist_checkBox.setChecked(True)
                    self.controller.autopersist = True
                elif not state and self.controller.autopersist:
                    self.autopersist_checkBox.setChecked(False)
                    self.controller.autopersist = False
            else:
                autopersist = self.autopersist_checkBox.isChecked()
                self.controller.autopersist = autopersist
            self.setting_value = False
        except:
            printErrorInfo()
    #

    @inlineCallbacks
    def resetMagnet(self):
        try:
            self.setting_value = True
            yield self.controller.resetPersistMagnet()
            self.setting_value = False
        except:
            printErrorInfo()
    #

    @inlineCallbacks
    def hold(self):
        self.setting_value = True
        yield self.controller.hold()
        self.setting_value = False
    #

    @inlineCallbacks
    def clamp(self):
        self.setting_value = True
        yield self.controller.clamp()
        self.setting_value = False
    #

    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous
    # delay that allows other labrad / pyqt methods to run
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""

    @inlineCallbacks
    def setField(self, B):
        #Sets the magnetic field through the currently selected magnet power supply.
        #The function stops running only when the field has been reached

        # if self.magDevice == 'Toellner 8851':
        #     yield self.toeSweepField(self.currField, B, self.ramprate)
        #
        # elif self.magDevice == 'IPS 120-10':
        #     #Got to the desired field on the IPS power supply.
        #     yield self.goToSetpointIPS(B) #Set the setpoint and update the IPS mode to sweep to field

        yield self.setSetpoint(B)
        yield self.controller.goToSetpoint(wait=True)

        # Waiting has been moved into the controller
        # #Only finish running the gotoField function when the field is reached
        # while True:
        #     yield self.controller.poll()
        #     if self.controller.B <= B+0.00001 and self.controller.B >= B-0.00001:
        #         break
        #     yield self.sleep(0.25)
        # yield self.sleep(0.25)

    def readField(self):
        '''
        Returns either the output or the persistent field, depending on the mode.
        '''
        return self.controller.B

    def readPersistField(self):
        '''
        Equivalent to readField in persitent mode, returns a warning if not in persistent mode.
        '''
        if self.controller.persist:
            return self.controller.B
        else:
            return "Field not persistent"
    #

    @inlineCallbacks
    def setPersist(self, on):
        '''
        Set the persistence mode of the magnet.

        Args:
            on (bool) : True of persistent, False for not persistent.
        '''
        self.setting_value = True
        if on and not self.controller.persist: #Persists the magnet at field
            yield self.controller.togglePersist()
            yield self.sleep(0.25)
        elif not on and self.controller.persist: #Heats the switch to enable charging
            yield self.controller.togglePersist()
            yield self.sleep(0.25)
        yield self.updateSwitchStatus()
        self.setting_value = False

        # self.setting_value = True
        # yield self.ips.set_control(3)
        # if on == True: #Persists the magnet at field
        #     yield self.ips.set_switchheater(2)
        # elif on == False: #Heats the switch to enable charging
        #     yield self.ips.set_switchheater(1)
        # yield self.sleep(0.25)
        # yield self.updateSwitchStatus()
        # yield self.ips.set_control(2)
        # self.setting_value = False

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def lockInterface(self):
        self.push_GotoZero.setEnabled(False)
        self.push_GotoSet.setEnabled(False)
        self.push_hold.setEnabled(False)
        self.push_clamp.setEnabled(False)
        self.push_persistSwitch.setEnabled(False)
        self.lineEdit_setpoint.setEnabled(False)
        self.lineEdit_ramprate.setEnabled(False)

    def unlockInterface(self):
        self.push_GotoZero.setEnabled(True)
        self.push_GotoSet.setEnabled(True)
        self.push_hold.setEnabled(True)
        self.push_clamp.setEnabled(True)
        self.push_persistSwitch.setEnabled(True)
        self.lineEdit_setpoint.setEnabled(True)
        self.lineEdit_ramprate.setEnabled(True)
    #
#

class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)
