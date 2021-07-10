import sys
from PyQt5 import QtWidgets, uic
from twisted.internet.defer import inlineCallbacks, Deferred
# import numpy as np
from nSOTScannerFormat import readNum, formatNum, printErrorInfo

path = sys.path[0] + r"\FieldControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\FieldControl.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

class Window(QtWidgets.QMainWindow, ScanControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)
        self.push_GotoSet.clicked.connect(lambda: self.goToSetpoint())
        self.push_GotoZero.clicked.connect(lambda: self.gotoZero())

        self.lineEdit_setpoint.editingFinished.connect(self.setSetpoint)
        self.lineEdit_ramprate.editingFinished.connect(self.setRamprate)

        self.controller = False

        self.currField = 0
        self.currCurrent = 0
        self.currVoltage = 0

        self.setting_value = False
        #By default, the switch is off, which corresponds to being in persist mode
        self.persist = True

        self.push_hold.hide()
        self.push_clamp.hide()
        self.lockInterface()

    def moveDefault(self):
        self.move(550,10)

    @inlineCallbacks
    def connectLabRAD(self, equip):
        if 'Magnet Supply' in equip.servers:
            svr, ln, device_info, cnt, config = equip.servers['Magnet Supply']
            self.controller = cnt
        else:
            print("'Magnet Supply' not found, LabRAD connection to FieldControl Failed.")
            return

        try:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            yield self.loadInitialValues()
            self.unlockInterface()
            self.monitor = True #modified temporarily
            yield self.monitorField()
        except:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")

        if hasattr(self.controller, "clamp"):
            self.push_clamp.clicked.connect(lambda: self.clamp())

        if hasattr(self.controller, "hold"):
            self.push_hold.clicked.connect(lambda: self.hold())

        # if hasattr(self.controller, "togglePersist"):
        #     self.push_persistSwitch.clicked.connect(lambda: self.togglePersist())

    def disconnectLabRAD(self):
        self.monitor = False
        self.controller = False
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
                if not self.setting_value:
                    yield self.controller.poll()
                    self.currField = self.controller.Bz
                    self.currCurrent = self.controller.current
                    self.currVoltage = self.controller.output_voltage
                    self.updateSwitchStatus()
                try:
                    self.label_fieldval.setText(formatNum(self.currField,3))
                    self.label_currentval.setText(formatNum(self.currCurrent,3))
                    self.label_outputvoltage.setText(formatNum(self.currVoltage,3))
                except:
                    printErrorInfo()
                yield self.sleep(0.5)
        except:
            printErrorInfo()

    @inlineCallbacks
    def loadInitialValues(self):
        try:
            yield self.controller.loadInitialValues()
            yield self.controller.poll()
            self.updateSwitchStatus()

            self.label_setpoint.setText(formatNum(self.controller.setpoint_Bz))
            self.label_ramprate.setText(formatNum(self.ramprate))
            self.lineEdit_setpoint.setText(formatNum(self.controller.setpoint_Bz))
            self.lineEdit_ramprate.setText(formatNum(self.ramprate))
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
            if self.controller.status == "Charging":
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

    @inlineCallbacks
    def setSetpoint(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_setpoint.text()))
        if isinstance(val,float):
            yield self.controller.setSetpoint(val)
            self.setpoint = self.controller.setpoint_Bz
        self.lineEdit_setpoint.setText(formatNum(self.setpoint, 4))

    @inlineCallbacks
    def setRamprate(self):
        val = readNum(str(self.lineEdit_ramprate.text()))
        if isinstance(val,float):
            self.ramprate = val
            self.setting_value = True
            yield self.controller.setRampRate(self.ramprate)
            self.setting_value = False
        self.lineEdit_ramprate.setText(formatNum(self.ramprate))


    @inlineCallbacks
    def goToSetpoint(self):
        try:
            self.setting_value = True
            yield self.controller.goToSetpoint()
            self.setting_value = False
            # if self.magDevice == 'IPS 120-10':
            #     yield self.goToSetpointIPS()
            # else:
            #     yield self.toeSweepField(self.currField, self.setpoint, self.ramprate)
        except:
            printErrorInfo()
    #

    @inlineCallbacks
    def gotoZero(self):
        try:
            self.setting_value = True
            yield self.controller.goToZero()
            self.setting_value = False
            # if self.magDevice == 'IPS 120-10':
            #     yield self.gotoZeroIPS()
            # else:
            #     yield self.toeSweepField(self.currField, 0, self.ramprate)
        except:
            printErrorInfo()
    #

    @inlineCallbacks
    def togglePersist(self):
        try:
            self.setting_value = True
            yield self.controller.togglePersist()
            self.setting_value = False
            self.updateSwitchStatus()
        except:
            printErrorInfo()

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

    # @inlineCallbacks
    # def toeSweepField(self, B_i, B_f, B_speed):
    #     try:
    #         #Toellner voltage set point / DAC voltage out conversion [V_Toellner / V_DAC]
    #         VV_conv = 3.20
    #         #Toellner current set point / DAC voltage out conversion [I_Toellner / V_DAC]
    #         IV_conv = 1.0
    #
    #         #Field / Current ratio on the dipper magnet (0.132 [Tesla / Amp])
    #         IB_conv = 0.132
    #
    #         #Starting and ending field values in Tesla, use positive field values for now
    #         B_range = np.absolute(B_f - B_i)
    #
    #         #Delay between DAC steps in microseconds
    #         magnet_delay = 1000
    #         #Converts between microseconds and minutes [us / minute]
    #         t_conv = 6e07
    #
    #         #Sets the appropriate DAC buffer ramp parameters
    #         sweep_steps = int((t_conv * B_range) / (B_speed * magnet_delay))  + 1
    #         v_start = B_i / (IB_conv * IV_conv)
    #         v_end = B_f / (IB_conv * IV_conv)
    #
    #         #Sets an appropraite voltage set point to ensure that the Toellner power supply stays in constant current mode
    #         # assuming a parasitic resistance of R_p between the power supply and magnet
    #         R_p = 1
    #         V_setpoint =  (R_p * B_f) / (VV_conv * IB_conv)
    #         V_initial = (R_p * B_i) / (VV_conv * IB_conv)
    #         if V_setpoint*VV_conv > 5.0:
    #             V_setpoint = 5.0/VV_conv
    #         else:
    #             pass
    #         if V_initial*VV_conv > 5.0:
    #             V_initial = 5.0/VV_conv
    #         else:
    #             pass
    #
    #         #Sweeps field from B_i to B_f
    #         print('Sweeping field from ' + str(B_i) + ' to ' + str(B_f)+'.')
    #         yield self.dac_toe.buffer_ramp([self.toeCurChan, self.toeVoltsChan],[0],[v_start, V_initial],[v_end, V_setpoint], sweep_steps, magnet_delay)
    #
    #         self.currVoltage = V_setpoint
    #         self.currCurrent = B_f/IB_conv
    #         self.currField = B_f
    #     except:
    #         printErrorInfo()

    # def updateToeField(self, field, curr, volt):
    #     self.currField = field
    #     self.currVoltage = volt
    #     self.currCurrent = curr

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
        yield self.controller.goToSetpoint()

        #Only finish running the gotoField function when the field is reached
        while True:
            yield self.controller.poll()
            if self.controller.Bz <= B+0.00001 and self.controller.Bz >= B-0.00001:
                break
            yield self.sleep(0.25)
        yield self.sleep(0.25)

    def readField(self):
        '''
        Returns either the output or the persistent field, depending on the mode.
        '''
        return self.controller.Bz

    def readPersistField(self):
        '''
        Equivalent to readField in persitent mode, returns a warning if not in persistent mode.
        '''
        if self.controller.persist:
            return self.controller.Bz
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
