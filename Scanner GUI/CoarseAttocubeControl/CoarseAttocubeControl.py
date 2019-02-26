import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np

path = sys.path[0] + r"\CoarseAttocubeControl"
sys.path.append(path + r'\Status')

CoarseAttocubeControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\CoarseAttocubeControl.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")

import Status

sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, CoarseAttocubeControlWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
    
        self.reactor = reactor
        self.setupUi(self)

        self.pushButton_Servers.clicked.connect(self.showServersList)

        self.pushButton_CapacitorAxis1.clicked.connect(lambda: self.RefreshCapacitance(0, self.label_CapacitanceAxis1))
        self.pushButton_CapacitorAxis2.clicked.connect(lambda: self.RefreshCapacitance(1, self.label_CapacitanceAxis2))
        self.pushButton_CapacitorAxis3.clicked.connect(lambda: self.RefreshCapacitance(2, self.label_CapacitanceAxis3))

        self.pushButton_Compensation_Axis1.clicked.connect(lambda: self.ChangeCompensation(0))
        self.pushButton_Compensation_Axis2.clicked.connect(lambda: self.ChangeCompensation(1))
        self.pushButton_Compensation_Axis3.clicked.connect(lambda: self.ChangeCompensation(2))

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

        self.pushButton_ManualStepMinus_Axis1.clicked.connect(lambda: self.StartSingleStep(0, 1))
        self.pushButton_ManualStepPlus_Axis1.clicked.connect(lambda: self.StartSingleStep(0, 0))
        self.pushButton_ManualStepMinus_Axis2.clicked.connect(lambda: self.StartSingleStep(1, 1))
        self.pushButton_ManualStepPlus_Axis2.clicked.connect(lambda: self.StartSingleStep(1, 0))
        self.pushButton_ManualStepMinus_Axis3.clicked.connect(lambda: self.StartSingleStep(2, 1))
        self.pushButton_ManualStepPlus_Axis3.clicked.connect(lambda: self.StartSingleStep(2, 0))

        self.IconPath = {
            'Still': ':/nSOTScanner/Pictures/ManStill.png',
            'Moving Negative': ':/nSOTScanner/Pictures/ManRunningLeft.png',
            'Moving Positive': ':/nSOTScanner/Pictures/ManRunningRight.png',
            'MoveBlockedLeft': ':/nSOTScanner/Pictures/ManRunningLeftBlocked.png',
            'MoveBlockedRight': ':/nSOTScanner/Pictures/ManRunningRightBlocked.png',
            'TargetReached': ':/nSOTScanner/Pictures/ManReachGoal.png',
            'Error': ':/nSOTScanner/Pictures/ManError.png',
            'Compensation': ':/nSOTScanner/Pictures/ManReachingForward.png',
            'NoCompensation': ':/nSOTScanner/Pictures/MannotReachingForward.png'
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
        self.pushButton_Compensation = [self.pushButton_Compensation_Axis1, self.pushButton_Compensation_Axis2, self.pushButton_Compensation_Axis3]
        self.pushButton_SingleStepPlus = [self.pushButton_ManualStepPlus_Axis1, self.pushButton_ManualStepPlus_Axis2, self.pushButton_ManualStepPlus_Axis3]
        self.pushButton_SingleStepMinus = [self.pushButton_ManualStepMinus_Axis1, self.pushButton_ManualStepMinus_Axis2, self.pushButton_ManualStepMinus_Axis3]        
        self.lcddisplay = [self.lcdNumber_Axis1, self.lcdNumber_Axis2, self.lcdNumber_Axis3]
        self.CurrentPosition = [0.0, 0.0, 0.0]
        self.RelativePosition = [0.0, 0.0, 0.0]
        self.AbsolutePosition = [0.0, 0.0, 0.0]
        self.manual_Amplitude = [30.0, 30.0, 40.0]
        self.manual_Frequency = [1000, 1000, 1000]
        self.TargetRange = [500*10**-9, 500*10**-9, 1000*10**-9]
        self.Compensation = [False, False, False]
        
        self.StatusWindow = Status.StatusWindow(self.reactor)
        self.pushButton_StatusMonitor.clicked.connect(self.OpenStatusWindow)


    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.anc350 = dict['servers']['local']['anc350']
            
            self.pushButton_Servers.setStyleSheet("#pushButton_Servers{" + 
            "background: rgb(0, 170, 0);border-radius: 4px;}")
            self.serversConnected = True

            for i in range(3):
                yield self.UpdateAutomaticPositioningRelativePosition(i)
                yield self.UpdateAutomaticPositioningAbsolutePosition(i)
                yield self.UpdateAmplitude(i)
                yield self.UpdateFrequency(i)
                yield self.UpdateTargetRange(i)
                # yield self.anc350.set_axis_output(i, True, False)#Set default status to be no DC level

            self.MonitoringStatus()
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno            
            self.pushButton_Servers.setStyleSheet("#pushButton_Servers{" + 
            "background: rgb(161, 0, 0);border-radius: 4px;}")  

    def disconnectLabRAD(self):
        self.cxn = False
        self.anc350 = False

        self.serversConnected = False

        self.pushButton_Servers.setStyleSheet("#pushButton_Servers{" + 
            "background: rgb(144, 140, 9);border-radius: 4px;}")
            
    @inlineCallbacks
    def MonitoringStatus(self):
        while self.serversConnected:
            try:
                yield self.RefreshAttocubeStatus()
                yield self.sleep(0.1)
            except Exception as inst:
                print 'Monitor error: ', inst, sys.exc_traceback.tb_lineno
                yield self.sleep(0.1)

    @inlineCallbacks
    def RefreshAttocubeStatus(self):
        try:
            for i in range(3):
                self.CurrentPosition[i] = yield self.anc350.get_position(i)
                self.lcddisplay[i].display('{0:<09}'.format(self.CurrentPosition[i]*10**6))
                statusarray = yield self.anc350.get_axis_status(i)# [0]connected, [1]enabled, [2]moving, [3]target, [4]eotFwd, [5]eotBwd , [6]error
                self.StatusWindow.ChangeStatus(i, statusarray)
                #Determine Status
                if statusarray[6] == 1:
                    self.Status[i] = 'Error'
                elif statusarray[4] == 1:
                    self.Status[i] = 'MoveBlockedRight'
                elif statusarray[5] == 1:
                    self.Status[i] = 'MoveBlockedLeft'
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
                        if i == 0:
                            print 'Do not know the direction so Positive and target not reached', self.Direction[i]
                        self.Direction[i] == 'Positive'
                        self.Status[i] = 'Moving Positive'
                elif statusarray[2] == 0:
                    if i == 0:
                        print 'not moving'

                    self.Status[i] = 'Still'
                    self.Direction[i] = 'Still'
                    self.SetIndicatorStill(i)
                else:
                    self.Status[i] = 'Still'
                    self.SetIndicatorStill(i)
                    print 'Status unclear'
                    
                if statusarray[3] == 1 :#and self.Status[i] != 'TargetReached'
                    if i == 0:
                        print 'prevent'
                    self.Status[i] = 'TargetReached'
                    if self.Compensation[i] == False: #When first detect target reached, disable dc level if compensation is false
                        self.anc350.set_axis_output(i, False, True)
                
                #Change the Pushbutton
                stylesheet = '#pushButton_Status_Axis' + str(i+1) + '{\nimage:url(' + self.IconPath[self.Status[i]] + ');\nbackground: black;\nborder: 0px solid rgb(95,107,166);\n}\n'
                self.pushButton_Status[i].setStyleSheet(stylesheet)
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno

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
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno

    @inlineCallbacks
    def MovingRelative(self, AxisNo):
        try:
            if self.Direction[AxisNo] == 'Still':
                print 'start relative'
                yield self.anc350.set_axis_output(AxisNo, True, True) #Enable Axis when moving
                yield self.anc350.set_target_position(AxisNo, self.RelativePosition[AxisNo])
                yield self.anc350.start_auto_move(AxisNo, True, True)
                if self.RelativePosition[AxisNo] > 0:
                    self.Direction[AxisNo] = 'Positive'
                else:
                    self.Direction[AxisNo] = 'Negative'
            elif self.Direction[AxisNo] == 'Positive' or self.Direction[AxisNo] == 'Negative':
                print 'stop relative'
                yield self.anc350.start_auto_move(AxisNo, False, True) #Only stop auto move but not disble the aixs
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
    @inlineCallbacks
    def MovingAbsolute(self, AxisNo):
        if self.Direction[AxisNo] == 'Still':
            yield self.anc350.set_axis_output(AxisNo, True, True) #Enable Axis when moving
            yield self.anc350.set_target_position(AxisNo, self.AbsolutePosition[AxisNo])
            yield self.anc350.start_auto_move(AxisNo, True, False)
            if self.AbsolutePosition[AxisNo] > self.CurrentPosition[AxisNo]:
                self.Direction[AxisNo] = 'Positive'
            else:
                self.Direction[AxisNo] = 'Negative'
        elif self.Direction[AxisNo] == 'Positive' or self.Direction[AxisNo] == 'Negative':
            yield self.anc350.start_auto_move(AxisNo, False, False)

    @inlineCallbacks
    def StartSingleStep(self, Axis, direction): #forward is 0, backward is 1
        try:
            if direction == 0:
                flag = True
            else:
                flag = False
            yield self.anc350.start_single_step(Axis, flag)
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno

    def ChangeCompensation(self, AxisNo):
        if self.Compensation[AxisNo]:
            self.Compensation[AxisNo] = False
            stylesheet = '#pushButton_Compensation_Axis' + str(AxisNo+1) + '{\nimage:url(' + self.IconPath['NoCompensation'] + ');\nbackground: black;\nborder: 0px solid rgb(95,107,166);\n}\n'
            self.pushButton_Compensation[AxisNo].setStyleSheet(stylesheet)
        else:
            self.Compensation[AxisNo] = True
            stylesheet = '#pushButton_Compensation_Axis' + str(AxisNo+1) + '{\nimage:url(' + self.IconPath['Compensation'] + ');\nbackground: black;\nborder: 0px solid rgb(95,107,166);\n}\n'
            self.pushButton_Compensation[AxisNo].setStyleSheet(stylesheet)

    def UpdateAutomaticPositioningRelativePosition(self, AxisNo):
        dummystr=str(self.lineEdit_Relative[AxisNo].text())
        dummyval=readNum(dummystr, self)
        if isinstance(dummyval,float):
            if dummyval >= -5.0 * 10**-3 and dummyval <= 5.0 * 10**-3:
                self.RelativePosition[AxisNo] = dummyval
            elif dummyval < -5.0 * 10**-3:
                self.RelativePosition[AxisNo] = -5.0 * 10**-3
            elif dummyval > 5.0 * 10**-3:
                self.RelativePosition[AxisNo] = 5.0 * 10**-3
        self.lineEdit_Relative[AxisNo].setText(formatNum(self.RelativePosition[AxisNo],6))

    def UpdateAutomaticPositioningAbsolutePosition(self, AxisNo):
        dummystr=str(self.lineEdit_Absolute[AxisNo].text())
        dummyval=readNum(dummystr, self)
        if isinstance(dummyval,float):
            if dummyval >= -5.0 * 10**-3 and dummyval <= 5.0 * 10**-3:
                self.AbsolutePosition[AxisNo]=dummyval
            elif dummyval < -5.0 * 10**-3:
                self.AbsolutePosition[AxisNo] = -5.0 * 10**-3
            elif dummyval > 5.0 * 10**-3:
                self.AbsolutePosition[AxisNo] = 5.0 * 10**-3
        self.lineEdit_Absolute[AxisNo].setText(formatNum(self.AbsolutePosition[AxisNo],6))

    @inlineCallbacks
    def UpdateAmplitude(self, AxisNo):
        try:
            dummystr=str(self.lineEdit_Amplitude[AxisNo].text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float):
                if dummyval >= 0 and dummyval <= 60:
                    self.manual_Amplitude[AxisNo] = dummyval
                elif dummyval < 0:
                    self.manual_Amplitude[AxisNo] = 0
                elif dummyval > 60:
                    self.manual_Amplitude[AxisNo] = 60
            self.lineEdit_Amplitude[AxisNo].setText(formatNum(self.manual_Amplitude[AxisNo],6))
            if hasattr(self, 'anc350'):
                yield self.anc350.set_amplitude(AxisNo, self.manual_Amplitude[AxisNo])
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
    @inlineCallbacks
    def UpdateFrequency(self, AxisNo):
        try:    
            dummystr=str(self.lineEdit_Frequency[AxisNo].text())
            dummyval=readNum(dummystr, self , False)
            if isinstance(dummyval,float):
                if dummyval >= 1 and dummyval <= 2000:
                    self.manual_Frequency[AxisNo]= int(dummyval)
                elif dummyval < 1:
                    self.manual_Frequency[AxisNo] = 1
                elif dummyval > 2000:
                    self.manual_Frequency[AxisNo] = 2000
            self.lineEdit_Frequency[AxisNo].setText(formatNum(self.manual_Frequency[AxisNo],6))
            if hasattr(self, 'anc350'):
                yield self.anc350.set_frequency(AxisNo, self.manual_Frequency[AxisNo])
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
    @inlineCallbacks
    def UpdateTargetRange(self, AxisNo):
        try:    
            dummystr=str(self.lineEdit_TargetRange[AxisNo].text())
            dummyval=readNum(dummystr, self)
            if isinstance(dummyval,float):
                if dummyval >= 1*10**-9 and dummyval <= 10**-3:
                    self.TargetRange[AxisNo]= dummyval
                elif dummyval < 1*10**-9:
                    self.TargetRange[AxisNo] = 1*10**-9
                elif dummyval > 10**-3:
                    self.TargetRange[AxisNo] = 10**-3
            self.lineEdit_TargetRange[AxisNo].setText(formatNum(self.TargetRange[AxisNo],6))
            if hasattr(self, 'anc350'):
                yield self.anc350.set_target_range(AxisNo, self.TargetRange[AxisNo])
        except Exception as inst:
            print inst, sys.exc_traceback.tb_lineno
            
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

class serversList(QtGui.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos)

        #pushButton_Status_Axis1{\nimage:url(:/nSOTScanner/Pictures/ManStill.png);\nbackground: black;\nborder: 0px solid rgb(95,107,166);\n}\n