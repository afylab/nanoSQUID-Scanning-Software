import sys
from PyQt5 import QtWidgets, uic
from twisted.internet.defer import inlineCallbacks, Deferred
from nSOTScannerFormat import readNum, formatNum, printErrorInfo
from PyQt5.QtCore import QTimer
path = sys.path[0] + r"\CoarseAttocubeControl"
sys.path.append(path + r'\Status')
sys.path.append(path + r'\Debug Panel')

CoarseAttocubeControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\CoarseAttocubeControl.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

import Status
import DebugPy

class Window(QtWidgets.QMainWindow, CoarseAttocubeControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.pushButton_CapacitorAxis1.clicked.connect(lambda: self.RefreshCapacitance(0, self.label_CapacitanceAxis1))
        self.pushButton_CapacitorAxis2.clicked.connect(lambda: self.RefreshCapacitance(1, self.label_CapacitanceAxis2))
        self.pushButton_CapacitorAxis3.clicked.connect(lambda: self.RefreshCapacitance(2, self.label_CapacitanceAxis3))

        self.checkBox_targetGND_Axis1.stateChanged.connect(lambda: self.toggleTargetGround(0))
        self.checkBox_targetGND_Axis2.stateChanged.connect(lambda: self.toggleTargetGround(1))
        self.checkBox_targetGND_Axis3.stateChanged.connect(lambda: self.toggleTargetGround(2))

        self.checkBox_OutputEnabled_Axis1.stateChanged.connect(lambda: self.toggleOutput(0))
        self.checkBox_OutputEnabled_Axis2.stateChanged.connect(lambda: self.toggleOutput(1))
        self.checkBox_OutputEnabled_Axis3.stateChanged.connect(lambda: self.toggleOutput(2))

        self.lineEdit_AutoPositionRelative_Axis1.editingFinished.connect(lambda: self.UpdateAutomaticPositioningRelativePosition(0))
        self.lineEdit_AutoPositionAbsolute_Axis1.editingFinished.connect(lambda: self.UpdateAutomaticPositioningAbsolutePosition(0))
        self.lineEdit_AutoPositionRelative_Axis2.editingFinished.connect(lambda: self.UpdateAutomaticPositioningRelativePosition(1))
        self.lineEdit_AutoPositionAbsolute_Axis2.editingFinished.connect(lambda: self.UpdateAutomaticPositioningAbsolutePosition(1))
        self.lineEdit_AutoPositionRelative_Axis3.editingFinished.connect(lambda: self.UpdateAutomaticPositioningRelativePosition(2))
        self.lineEdit_AutoPositionAbsolute_Axis3.editingFinished.connect(lambda: self.UpdateAutomaticPositioningAbsolutePosition(2))

        self.lineEdit_Amplitude_Axis1.editingFinished.connect(lambda: self.UpdateAmplitude(0))
        self.lineEdit_Amplitude_Axis2.editingFinished.connect(lambda: self.UpdateAmplitude(1))
        self.lineEdit_Amplitude_Axis3.editingFinished.connect(lambda: self.UpdateAmplitude(2))

        self.lineEdit_Frequency_Axis1.editingFinished.connect(lambda: self.UpdateFrequency(0))
        self.lineEdit_Frequency_Axis2.editingFinished.connect(lambda: self.UpdateFrequency(1))
        self.lineEdit_Frequency_Axis3.editingFinished.connect(lambda: self.UpdateFrequency(2))

        self.lineEdit_TargetRange_Axis1.editingFinished.connect(lambda: self.UpdateTargetRange(0))
        self.lineEdit_TargetRange_Axis2.editingFinished.connect(lambda: self.UpdateTargetRange(1))
        self.lineEdit_TargetRange_Axis3.editingFinished.connect(lambda: self.UpdateTargetRange(2))

        self.pushButton_Status_Axis1.clicked.connect(lambda: self.ResetStatus(0))
        self.pushButton_Status_Axis2.clicked.connect(lambda: self.ResetStatus(1))
        self.pushButton_Status_Axis3.clicked.connect(lambda: self.ResetStatus(2))

        self.pushButton_AutomaticMoveRelative_Axis1.clicked.connect(lambda: self.MovingRelative(0))
        self.pushButton_AutomaticMoveAbsolute_Axis1.clicked.connect(lambda: self.MovingAbsolute(0))
        self.pushButton_AutomaticMoveRelative_Axis2.clicked.connect(lambda: self.MovingRelative(1))
        self.pushButton_AutomaticMoveAbsolute_Axis2.clicked.connect(lambda: self.MovingAbsolute(1))
        self.pushButton_AutomaticMoveRelative_Axis3.clicked.connect(lambda: self.MovingRelative(2))
        self.pushButton_AutomaticMoveAbsolute_Axis3.clicked.connect(lambda: self.MovingAbsolute(2))


        self.ManualPushButtonsPlus = [self.pushButton_ManualStepPlus_Axis1, self.pushButton_ManualStepPlus_Axis2, self.pushButton_ManualStepPlus_Axis3]
        self.ManualPushButtonsMinus = [self.pushButton_ManualStepMinus_Axis1, self.pushButton_ManualStepMinus_Axis2, self.pushButton_ManualStepMinus_Axis3]
        self.pushButton_ManualStepMinus_Axis1.clicked.connect(lambda: self.StartSingleStep(0, 1))
        self.pushButton_ManualStepPlus_Axis1.clicked.connect(lambda: self.StartSingleStep(0, 0))
        self.pushButton_ManualStepMinus_Axis2.clicked.connect(lambda: self.StartSingleStep(1, 1))
        self.pushButton_ManualStepPlus_Axis2.clicked.connect(lambda: self.StartSingleStep(1, 0))
        self.pushButton_ManualStepMinus_Axis3.clicked.connect(lambda: self.StartSingleStep(2, 1))
        self.pushButton_ManualStepPlus_Axis3.clicked.connect(lambda: self.StartSingleStep(2, 0))

        # self.timer = [QTimer() for i in range(6)]
        # self.pushButton_ManualStepMinus_Axis1.pressed.connect(lambda: self.manualstep_on_press(0))
        # self.pushButton_ManualStepPlus_Axis1.pressed.connect(lambda: self.manualstep_on_press(1))
        # self.pushButton_ManualStepMinus_Axis2.pressed.connect(lambda: self.manualstep_on_press(2))
        # self.pushButton_ManualStepPlus_Axis2.pressed.connect(lambda: self.manualstep_on_press(3))
        # self.pushButton_ManualStepMinus_Axis3.pressed.connect(lambda: self.manualstep_on_press(4))
        # self.pushButton_ManualStepPlus_Axis3.pressed.connect(lambda: self.manualstep_on_press(5))
        #
        # self.pushButton_ManualStepMinus_Axis1.released.connect(lambda: self.manualstep_on_release(0))
        # self.pushButton_ManualStepPlus_Axis1.released.connect(lambda: self.manualstep_on_release(1))
        # self.pushButton_ManualStepMinus_Axis2.released.connect(lambda: self.manualstep_on_release(2))
        # self.pushButton_ManualStepPlus_Axis2.released.connect(lambda: self.manualstep_on_release(3))
        # self.pushButton_ManualStepMinus_Axis3.released.connect(lambda: self.manualstep_on_release(4))
        # self.pushButton_ManualStepPlus_Axis3.released.connect(lambda: self.manualstep_on_release(5))

        # self.timer[0].timeout.connect(lambda: self.manualstep_on_hold(0,1))
        # self.timer[1].timeout.connect(lambda: self.manualstep_on_hold(0,0))
        # self.timer[2].timeout.connect(lambda: self.manualstep_on_hold(1,1))
        # self.timer[3].timeout.connect(lambda: self.manualstep_on_hold(1,0))
        # self.timer[4].timeout.connect(lambda: self.manualstep_on_hold(2,1))
        # self.timer[5].timeout.connect(lambda: self.manualstep_on_hold(2,0))

        self.IconPath = {
            'Still': ':/nSOTScanner/Pictures/ManStill.png',
            'Moving Negative': ':/nSOTScanner/Pictures/ManRunningLeft.png',
            'Moving Positive': ':/nSOTScanner/Pictures/ManRunningRight.png',
            'MoveBlockedLeft': ':/nSOTScanner/Pictures/ManRunningLeftBlocked.png',
            'MoveBlockedRight': ':/nSOTScanner/Pictures/ManRunningRightBlocked.png',
            'TargetReached': ':/nSOTScanner/Pictures/ManReachGoal.png',
            'Error': ':/nSOTScanner/Pictures/ManError.png'
        }

        self.Status = ['', '', '']
        self.Direction =['Positive', 'Positive', 'Positive']
        self.lineEdit_Relative = [self.lineEdit_AutoPositionRelative_Axis1, self.lineEdit_AutoPositionRelative_Axis2, self.lineEdit_AutoPositionRelative_Axis3]
        self.lineEdit_Absolute = [self.lineEdit_AutoPositionAbsolute_Axis1, self.lineEdit_AutoPositionAbsolute_Axis2, self.lineEdit_AutoPositionAbsolute_Axis3]
        self.lineEdit_Amplitude = [self.lineEdit_Amplitude_Axis1, self.lineEdit_Amplitude_Axis2, self.lineEdit_Amplitude_Axis3]
        self.lineEdit_Frequency = [self.lineEdit_Frequency_Axis1, self.lineEdit_Frequency_Axis2, self.lineEdit_Frequency_Axis3]
        self.lineEdit_TargetRange = [self.lineEdit_TargetRange_Axis1, self.lineEdit_TargetRange_Axis2, self.lineEdit_TargetRange_Axis3]
        self.pushButton_Relative = [self.pushButton_AutomaticMoveRelative_Axis1, self.pushButton_AutomaticMoveRelative_Axis2, self.pushButton_AutomaticMoveRelative_Axis3]
        self.pushButton_Absolute = [self.pushButton_AutomaticMoveAbsolute_Axis1, self.pushButton_AutomaticMoveAbsolute_Axis2, self.pushButton_AutomaticMoveAbsolute_Axis3]
        self.pushButton_Status = [self.pushButton_Status_Axis1, self.pushButton_Status_Axis2, self.pushButton_Status_Axis3]
        self.pushButton_SingleStepPlus = [self.pushButton_ManualStepPlus_Axis1, self.pushButton_ManualStepPlus_Axis2, self.pushButton_ManualStepPlus_Axis3]
        self.pushButton_SingleStepMinus = [self.pushButton_ManualStepMinus_Axis1, self.pushButton_ManualStepMinus_Axis2, self.pushButton_ManualStepMinus_Axis3]
        self.checkBox_OutputEnabled = [self.checkBox_OutputEnabled_Axis1, self.checkBox_OutputEnabled_Axis2, self.checkBox_OutputEnabled_Axis3]

        self.lcddisplay = [self.lcdNumber_Axis1, self.lcdNumber_Axis2, self.lcdNumber_Axis3]
        self.CurrentPosition = [0.0, 0.0, 0.0]
        self.RelativePosition = [0.0, 0.0, 0.0]
        self.AbsolutePosition = [0.0, 0.0, 0.0]
        self.manual_Amplitude = [30.0, 30.0, 40.0]
        self.manual_Frequency = [30, 30, 30]
        self.TargetRange = [500*10**-9, 500*10**-9, 1000*10**-9]
        self.TargetGround = [True, True, True]
        self.OutputEnabled = [True, True, True]

        for i in range(3):
            self.ManualPushButtonsPlus[i].setAutoRepeatInterval(1000/self.manual_Frequency[i])
            self.ManualPushButtonsMinus[i].setAutoRepeatInterval(1000/self.manual_Frequency[i])

        self.StatusWindow = Status.StatusWindow(self.reactor)
        self.pushButton_StatusMonitor.clicked.connect(self.OpenStatusWindow)
        self.DebugWindow = DebugPy.DebugWindow(self.reactor, self)
        self.pushButton_Debug.clicked.connect(self.OpenDebugWindow)

    def manualstep_on_press(self, i):
        if i ==0 or i==1:
            self.timer[i].start(1/self.manual_Frequency[0]*1000)
        elif i==2 or i==3:
            self.timer[i].start(1/self.manual_Frequency[1]*1000)
        elif i==4 or i==5:
            self.timer[i].start(1/self.manual_Frequency[2]*1000)

    def manualstep_on_hold(self, i, j):
        self.StartSingleStep(i, j)

    def manualstep_on_release(self, i):
        self.timer[i].stop()

    @inlineCallbacks
    def connectLabRAD(self, equip):
        try:
            # self.anc350 = dict['servers']['local']['anc350']
            '''
            FUTURE:
            A lot of this could be abstracted into the controller object, not directly
            from the labRAD server.
            '''
            if "ANC350" in equip.servers:
                self.anc350 = equip.servers['ANC350'][0]
            else:
                print("'ANC350' not found, LabRAD connection to Appraoch Module Failed.")
                return
            self.anc_err_count = 0


            self.pushButton_Servers.setStyleSheet("#pushButton_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            self.serversConnected = True

            if self.anc350 != None:
                yield self.loadParameters()
                self.MonitorStatus()
            else:
                raise Exception
        except:
            self.pushButton_Servers.setStyleSheet("#pushButton_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            printErrorInfo()

    @inlineCallbacks
    def loadParameters(self):
        try:
            for i in range(3):
                #Load parameters in the GUI that can be read
                amp = yield self.anc350.get_amplitude(i)
                freq = yield self.anc350.get_frequency(i)
                self.lineEdit_Amplitude[i].setText(formatNum(amp))
                self.lineEdit_Frequency[i].setText(formatNum(freq))
                statusarray = yield self.anc350.get_axis_status(i)
                if statusarray[1] == 1:
                    self.OutputEnabled[i] = True

                else:
                    self.OutputEnabled[i] = False
                self.checkBox_OutputEnabled[i].setChecked(self.OutputEnabled[i])

                #Attocube doesn't provide the capability to read the following values from their hardware, so set these
                #to our chosen default values
                yield self.UpdateAutomaticPositioningRelativePosition(i)
                yield self.UpdateAutomaticPositioningAbsolutePosition(i)
                yield self.UpdateAmplitude(i)
                yield self.UpdateFrequency(i)
                yield self.UpdateTargetRange(i)
                yield self.anc350.set_target_ground(i, self.TargetGround[i])
        except:
            print("Error reading Course Positioner Settings. Warning that they may be set to default values on the GUI.")

    def disconnectLabRAD(self):
        self.serversConnected = False
        self.anc350 = False

        self.pushButton_Servers.setStyleSheet("#pushButton_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")

    @inlineCallbacks
    def MonitorStatus(self):
        while self.serversConnected:
            try:
                yield self.RefreshAttocubeStatus()
                yield self.sleep(0.1)
            except:
                yield self.sleep(0.1)
            if self.anc_err_count > 10:
                print("===========================")
                print("CoursePositionerControl: More than 10 errors, stopped monitoring course positioners.")
                print("===========================")
                break

    @inlineCallbacks
    def RefreshAttocubeStatus(self):
        try:
            for i in range(3):
                if not self.serversConnected:
                    return
                self.CurrentPosition[i] = yield self.anc350.get_position(i)
                self.lcddisplay[i].display(round(self.CurrentPosition[i]*10**6, 4) )
                statusarray = yield self.anc350.get_axis_status(i)# [0]connected, [1]enabled, [2]moving, [3]target, [4]eotFwd, [5]eotBwd , [6]error
                self.StatusWindow.ChangeStatus(i, statusarray)
                #Determine Status
                if statusarray[6] == 1:
                    self.Status[i] = 'Error'
                elif statusarray[4] == 1:
                    self.Status[i] = 'MoveBlockedRight'
                    self.SetIndicatorStill(i)
                elif statusarray[5] == 1:
                    self.Status[i] = 'MoveBlockedLeft'
                    self.SetIndicatorStill(i)
                elif statusarray[2] == 1:
                    self.SetIndicatorMoving(i)
                    if self.Direction[i] == 'Positive':
                        self.Status[i] = 'Moving Positive'
                    elif self.Direction[i] == 'Negative':
                        self.Status[i] = 'Moving Negative'
                    elif statusarray[3] == 1: #No need to throw an error if target reached.
                        self.Direction[i] == 'Positive'
                        self.Status[i] = 'Moving Positive'
                    else:
                        self.Direction[i] == 'Positive'
                        self.Status[i] = 'Moving Positive'
                elif statusarray[2] == 0:
                    self.Status[i] = 'Still'
                    self.Direction[i] = 'Still'
                    self.SetIndicatorStill(i)
                else:
                    self.Status[i] = 'Still'
                    self.SetIndicatorStill(i)
                    print('Status unclear')

                if statusarray[3] == 1 :#and self.Status[i] != 'TargetReached'
                    self.Status[i] = 'TargetReached'

                #Change the Pushbutton
                stylesheet = '#pushButton_Status_Axis' + str(i+1) + '{\nimage:url(' + self.IconPath[self.Status[i]] + ');\nbackground: black;\nborder: 0px solid rgb(95,107,166);\n}\n'
                self.pushButton_Status[i].setStyleSheet(stylesheet)
        except Exception as inst:
            self.anc_err_count += 1
            #printErrorInfo()

    def SetIndicatorMoving(self, AxisNo):
        self.pushButton_Relative[AxisNo].setText('Moving')
        self.pushButton_Absolute[AxisNo].setText('Moving')
        self.DisableSingleStep(AxisNo)

    def SetIndicatorStill(self, AxisNo):
        self.pushButton_Relative[AxisNo].setText('Move Relative')
        self.pushButton_Absolute[AxisNo].setText('Move Absolute')
        self.EnableSingleStep(AxisNo)

    @inlineCallbacks
    def RefreshCapacitance(self, AxisNo, label):
        try:
            Capacitance = yield self.anc350.measure_capacitance(AxisNo)
            label.setText(formatNum(Capacitance))
        except:
            printErrorInfo()

    @inlineCallbacks
    def MovingRelative(self, AxisNo):
        try:
            if self.pushButton_Relative[AxisNo].text() == 'Move Relative':
                yield self.anc350.set_target_position(AxisNo, self.RelativePosition[AxisNo])
                yield self.anc350.start_auto_move(AxisNo, True, True)
                if self.RelativePosition[AxisNo] > 0:
                    self.Direction[AxisNo] = 'Positive'
                else:
                    self.Direction[AxisNo] = 'Negative'
            elif self.pushButton_Relative[AxisNo].text() == 'Moving':
                yield self.anc350.start_auto_move(AxisNo, False, True) #Only stop auto move but not disble the aixs
        except:
            printErrorInfo()

    @inlineCallbacks
    def MovingAbsolute(self, AxisNo):
        if self.pushButton_Absolute[AxisNo].text() == 'Move Absolute':
            yield self.anc350.set_target_position(AxisNo, self.AbsolutePosition[AxisNo])
            yield self.anc350.start_auto_move(AxisNo, True, False)
            if self.AbsolutePosition[AxisNo] > self.CurrentPosition[AxisNo]:
                self.Direction[AxisNo] = 'Positive'
            else:
                self.Direction[AxisNo] = 'Negative'
        elif self.pushButton_Absolute[AxisNo].text() == 'Moving':
            yield self.anc350.start_auto_move(AxisNo, False, False)

    @inlineCallbacks
    def StartSingleStep(self, AxisNo, direction): #forward is 0, backward is 1
        try:
            if direction == 0:
                flag = False
            else:
                flag = True
            yield self.anc350.start_single_step(AxisNo, flag)
            #yield self.sleep(0.1)
        except:
            printErrorInfo()

    def UpdateAutomaticPositioningRelativePosition(self, AxisNo):
        val = readNum(str(self.lineEdit_Relative[AxisNo].text()), self, True)
        if isinstance(val,float):
            if val >= -5.0 * 10**-3 and val <= 5.0 * 10**-3:
                self.RelativePosition[AxisNo] = val
            elif val < -5.0 * 10**-3:
                self.RelativePosition[AxisNo] = -5.0 * 10**-3
            elif val > 5.0 * 10**-3:
                self.RelativePosition[AxisNo] = 5.0 * 10**-3
        self.lineEdit_Relative[AxisNo].setText(formatNum(self.RelativePosition[AxisNo], 6))

    def UpdateAutomaticPositioningAbsolutePosition(self, AxisNo):
        val = readNum(str(self.lineEdit_Absolute[AxisNo].text()), self, True)
        if isinstance(val,float):
            if val >= -5.0 * 10**-3 and val <= 5.0 * 10**-3:
                self.AbsolutePosition[AxisNo] = val
            elif val < -5.0 * 10**-3:
                self.AbsolutePosition[AxisNo] = -5.0 * 10**-3
            elif val > 5.0 * 10**-3:
                self.AbsolutePosition[AxisNo] = 5.0 * 10**-3
        self.lineEdit_Absolute[AxisNo].setText(formatNum(self.AbsolutePosition[AxisNo],6))

    @inlineCallbacks
    def UpdateAmplitude(self, AxisNo):
        try:
            val = readNum(str(self.lineEdit_Amplitude[AxisNo].text()))
            if isinstance(val, float):
                if val >= 0 and val <= 60:
                    self.manual_Amplitude[AxisNo] = val
                elif val < 0:
                    self.manual_Amplitude[AxisNo] = 0
                elif val > 60:
                    self.manual_Amplitude[AxisNo] = 60
            self.lineEdit_Amplitude[AxisNo].setText(formatNum(self.manual_Amplitude[AxisNo],6))
            if hasattr(self, 'anc350'):
                yield self.anc350.set_amplitude(AxisNo, self.manual_Amplitude[AxisNo])
        except:
            print("Error reading Course Positioner Amplitude. Warning that they may be set to default values on the GUI.")
            #printErrorInfo()

    @inlineCallbacks
    def UpdateFrequency(self, AxisNo):
        try:
            val = readNum(str(self.lineEdit_Frequency[AxisNo].text()))
            if isinstance(val, float):
                if val >= 1 and val <= 2000:
                    self.manual_Frequency[AxisNo]= int(val)
                elif val < 1:
                    self.manual_Frequency[AxisNo] = 1
                elif val > 2000:
                    self.manual_Frequency[AxisNo] = 2000
            self.lineEdit_Frequency[AxisNo].setText(formatNum(self.manual_Frequency[AxisNo],6))
            self.ManualPushButtonsPlus[AxisNo].setAutoRepeatInterval(1000/self.manual_Frequency[AxisNo])
            self.ManualPushButtonsMinus[AxisNo].setAutoRepeatInterval(1000/self.manual_Frequency[AxisNo])
            if hasattr(self, 'anc350'):
                yield self.anc350.set_frequency(AxisNo, self.manual_Frequency[AxisNo])
        except:
            print("Error reading Course Positioner Frequency. Warning that they may be set to default values on the GUI.")
            #printErrorInfo()

    @inlineCallbacks
    def UpdateTargetRange(self, AxisNo):
        try:
            val = readNum(str(self.lineEdit_TargetRange[AxisNo].text()), self, True)
            if isinstance(val, float):
                if val >= 1*10**-9 and val <= 10**-3:
                    self.TargetRange[AxisNo]= val
                elif val < 1*10**-9:
                    self.TargetRange[AxisNo] = 1*10**-9
                elif val > 10**-3:
                    self.TargetRange[AxisNo] = 10**-3
            self.lineEdit_TargetRange[AxisNo].setText(formatNum(self.TargetRange[AxisNo],6))
            if hasattr(self, 'anc350'):
                yield self.anc350.set_target_range(AxisNo, self.TargetRange[AxisNo])
        except:
            print("Error reading Course Positioner Range. Warning that they may be set to default values on the GUI.")
            #printErrorInfo()

    @inlineCallbacks
    def toggleTargetGround(self, AxisNo):
        if self.TargetGround[AxisNo]:
            self.TargetGround[AxisNo] = False
            yield self.anc350.set_target_ground(AxisNo, False)
        else:
            self.TargetGround[AxisNo] = True
            yield self.anc350.set_target_ground(AxisNo, True)

    @inlineCallbacks
    def toggleOutput(self, AxisNo):
        output_on = self.checkBox_OutputEnabled[AxisNo].isChecked()
        if output_on:
            self.OutputEnabled[AxisNo] = True
            yield self.anc350.set_axis_output(AxisNo, True, False)
        else:
            self.OutputEnabled[AxisNo] = False
            yield self.anc350.set_axis_output(AxisNo, False, False)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

    def ResetStatus(self, AxisNo):
        self.Status[AxisNo] = ''

    def OpenStatusWindow(self):
        self.StatusWindow.moveDefault()
        self.StatusWindow.raise_()
        self.StatusWindow.show()

    def OpenDebugWindow(self):
        self.DebugWindow.moveDefault()
        self.DebugWindow.raise_()
        self.DebugWindow.show()

    def EnableSingleStep(self, AxisNo):
        self.pushButton_SingleStepPlus[AxisNo].setEnabled(True)
        self.pushButton_SingleStepMinus[AxisNo].setEnabled(True)

    def DisableSingleStep(self, AxisNo):
        self.pushButton_SingleStepPlus[AxisNo].setEnabled(False)
        self.pushButton_SingleStepMinus[AxisNo].setEnabled(False)

    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()

    def moveDefault(self):
        self.move(550,10)

    def closeEvent(self, c):
        self.close()

class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)

        #pushButton_Status_Axis1{\nimage:url(:/nSOTScanner/Pictures/ManStill.png);\nbackground: black;\nborder: 0px solid rgb(95,107,166);\n}\n
