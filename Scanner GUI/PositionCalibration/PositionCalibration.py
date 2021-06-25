import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred

path = sys.path[0] + r"\PositionCalibration"
CalibrationUI, QtBaseClass = uic.loadUiType(path + r"\Calibration.ui")
Ui_getCalibrationName, QtBaseClass = uic.loadUiType(path + r"\getCalibrationName.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way. 
sys.path.append(sys.path[0]+'\Resources')
from nSOTScannerFormat import readNum, formatNum

class Window(QtGui.QMainWindow, CalibrationUI):
    newTemperatureCalibration = QtCore.pyqtSignal(list)

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()
        self.fileName = path + '\CalibrationData.txt'
        self.moveDefault()

        self.loadCalibrationInfo()

        self.comboBox.activated[str].connect(self.selectCalibration)

        self.push_remove.clicked.connect(self.removeCalibration)
        self.push_set.clicked.connect(self.saveSetCalibration)
        
        #Connect all line edits
        self.lineEdit_XCon.editingFinished.connect(self.set_XCon)
        self.lineEdit_YCon.editingFinished.connect(self.set_YCon)
        self.lineEdit_ZCon.editingFinished.connect(self.set_ZCon)

        self.lineEdit_XMax.editingFinished.connect(self.set_XMax)
        self.lineEdit_YMax.editingFinished.connect(self.set_YMax)
        self.lineEdit_ZMax.editingFinished.connect(self.set_ZMax)

        self.push_select.clicked.connect(self.emitCalibration)

    def setupAdditionalUi(self):
        pass

    def moveDefault(self):
        self.move(550,10)

    def emitCalibration(self):
        self.newTemperatureCalibration.emit(self.tempData)

    def setLineEditsReadOnly(self, state):
        self.lineEdit_XCon.setReadOnly(state)
        self.lineEdit_YCon.setReadOnly(state)
        self.lineEdit_ZCon.setReadOnly(state)

        self.lineEdit_XMax.setReadOnly(state)
        self.lineEdit_YMax.setReadOnly(state)
        self.lineEdit_ZMax.setReadOnly(state)

        self.lineEdit_XMaxVolts.setReadOnly(True)
        self.lineEdit_YMaxVolts.setReadOnly(True)
        self.lineEdit_ZMaxVolts.setReadOnly(True)

        if state:
            self.lineEdit_XCon.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_YCon.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_ZCon.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_XMax.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_YMax.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_ZMax.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_XMaxVolts.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_YMaxVolts.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_ZMaxVolts.setStyleSheet("background: rgb(181, 181, 181);")
        else:
            self.lineEdit_XCon.setStyleSheet("")
            self.lineEdit_YCon.setStyleSheet("")
            self.lineEdit_ZCon.setStyleSheet("")
            self.lineEdit_XMax.setStyleSheet("")
            self.lineEdit_YMax.setStyleSheet("")
            self.lineEdit_ZMax.setStyleSheet("")
            self.lineEdit_XMaxVolts.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_YMaxVolts.setStyleSheet("background: rgb(181, 181, 181);")
            self.lineEdit_ZMaxVolts.setStyleSheet("background: rgb(181, 181, 181);")

    def loadCalibrationInfo(self):
        f = open(self.fileName,'r')
        message = f.read()
        f.close()

        entries = message.splitlines()
        calibrationData = [a.split(',') for a in entries]
        keys = [cal[0] for cal in calibrationData]
        data = [cal[1:] for cal in calibrationData]
        self.calibrationDictionary = dict(list(zip(keys, data)))

        insert_index = 0
        for key, data in self.calibrationDictionary.items():
            if float(data[0]) == 1.0:
                self.comboBox.insertItem(insert_index, key + ' (Default)')
                insert_index = 1
                self.comboBox.setCurrentIndex(0)
                self.setLineEditsReadOnly(True)

                self.loadSelectedCalibration(key)
            else: 
                self.comboBox.insertItem(insert_index, key)

    def selectCalibration(self,string):
        if string == 'Add New Calibration':
            self.setLineEditsReadOnly(False)

            self.tempData = [0, None, None, None, None, None, None, None, None, None]

            self.lineEdit_XCon.setText('')
            self.lineEdit_YCon.setText('')
            self.lineEdit_ZCon.setText('')

            self.lineEdit_XMax.setText('')
            self.lineEdit_YMax.setText('')
            self.lineEdit_ZMax.setText('')

            self.lineEdit_XMaxVolts.setText('')
            self.lineEdit_YMaxVolts.setText('')
            self.lineEdit_ZMaxVolts.setText('')

            self.push_remove.setEnabled(False)
            self.push_select.setEnabled(False)
            self.push_set.setText('Save Calibr.')
        elif string[-9:] == '(Default)':
            self.setLineEditsReadOnly(True)
            self.loadSelectedCalibration(string[:-10])
            self.push_remove.setEnabled(False)
            self.push_select.setEnabled(True)
            self.push_set.setText('Set Default')
        else:
            self.setLineEditsReadOnly(True)
            self.loadSelectedCalibration(string)
            self.push_remove.setEnabled(True)
            self.push_select.setEnabled(True)
            self.push_set.setText('Set Default')

    def loadSelectedCalibration(self, key):
        data = self.calibrationDictionary[str(key)]

        self.tempData = data

        self.lineEdit_XCon.setText(formatNum(float(data[1]),3))
        self.lineEdit_YCon.setText(formatNum(float(data[2]),3))
        self.lineEdit_ZCon.setText(formatNum(float(data[3]),3))

        self.lineEdit_XMax.setText(formatNum(float(data[4]),3))
        self.lineEdit_YMax.setText(formatNum(float(data[5]),3))
        self.lineEdit_ZMax.setText(formatNum(float(data[6]),3))

        self.lineEdit_XMaxVolts.setText(formatNum(float(data[7]),3))
        self.lineEdit_YMaxVolts.setText(formatNum(float(data[8]),3))
        self.lineEdit_ZMaxVolts.setText(formatNum(float(data[9]),3))

    def saveSetCalibration(self):
        name = self.comboBox.currentText()
        index = self.comboBox.currentIndex()

        if name == 'Add New Calibration':
            if None in self.tempData:
                msgBox = QtGui.QMessageBox(self)
                msgBox.setIcon(QtGui.QMessageBox.Information)
                msgBox.setWindowTitle('Define All Values Error')
                msgBox.setText("\r\n Make sure that all the values are properly defined")
                msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
                msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
                msgBox.exec_()
            else:
                getName = getCalibrationName(self.reactor, self.calibrationDictionary, self)
                if getName.exec_():
                    new_name = str(getName.getName())
                    self.tempData = [str(datum) for datum in self.tempData]
                    self.calibrationDictionary[new_name] = self.tempData
                    self.comboBox.insertItem(index, new_name)
                    self.comboBox.setCurrentIndex(index)
                    self.selectCalibration(new_name)
                    self.writeCalibrationInfo()
        elif name[-9:] == '(Default)':
            pass
        else:
            for key, data in self.calibrationDictionary.items():
                if float(data[0]) == 1.0:
                    data[0] = '0.0'
                    self.calibrationDictionary[key] = data
                    old_index = self.comboBox.findText(key + ' (Default)')
                    self.comboBox.removeItem(old_index)
                    self.comboBox.insertItem(old_index, key)
                    #Find this key and remove the default string
                if key == name:
                    data[0] = '1.0'
                    self.calibrationDictionary[key] = data
                    self.comboBox.removeItem(index)
                    self.comboBox.insertItem(index, key + ' (Default)')
            self.comboBox.setCurrentIndex(index)
            self.writeCalibrationInfo()

    def removeCalibration(self):
        name = str(self.comboBox.currentText())
        del self.calibrationDictionary[name]
        index = self.comboBox.currentIndex()
        self.comboBox.removeItem(index)
        new_name = str(self.comboBox.currentText())
        self.selectCalibration(new_name)
        self.writeCalibrationInfo()

    def writeCalibrationInfo(self):
        f = open(self.fileName,'w')
        message  = ''
        for key, data in self.calibrationDictionary.items():
            message = message + key + ','
            for item in data:
                message = message + str(item) + ','
            message = message[:-1] + '\n'
        message = message[:-1]
        f.write(message)
        f.close()

    def set_XCon(self):
        val = readNum(str(self.lineEdit_XCon.text()), self)
        if isinstance(val,float):
            self.tempData[1] = val
            if self.tempData[1] is not None and self.tempData[4] is not None:
                self.tempData[7] = float(self.tempData[1])*float(self.tempData[4])
                self.set_XMaxVolts()
        if self.tempData[1] is None:
            self.lineEdit_XCon.setText('')
        else: 
            self.lineEdit_XCon.setText(formatNum(self.tempData[1]))

    def set_YCon(self):
        val = readNum(str(self.lineEdit_YCon.text()), self)
        if isinstance(val,float):
            self.tempData[2] = val
            if self.tempData[2] is not None and self.tempData[5] is not None:
                self.tempData[8] = float(self.tempData[2])*float(self.tempData[5])
                self.set_YMaxVolts()
        if self.tempData[2] is None:
            self.lineEdit_YCon.setText('')
        else: 
            self.lineEdit_YCon.setText(formatNum(self.tempData[2]))

    def set_ZCon(self):
        val = readNum(str(self.lineEdit_ZCon.text()), self)
        if isinstance(val,float):
            self.tempData[3] = val
            if self.tempData[3] is not None and self.tempData[6] is not None:
                self.tempData[9] = float(self.tempData[3])*float(self.tempData[6])
                self.set_ZMaxVolts()
        if self.tempData[3] is None:
            self.lineEdit_ZCon.setText('')
        else: 
            self.lineEdit_ZCon.setText(formatNum(self.tempData[3]))

    def set_XMax(self):
        val = readNum(str(self.lineEdit_XMax.text()), self)
        if isinstance(val,float):
            self.tempData[4] = val
            if self.tempData[1] is not None and self.tempData[4] is not None:
                self.tempData[7] = float(self.tempData[1])*float(self.tempData[4])
                self.set_XMaxVolts()
        if self.tempData[4] is None:
            self.lineEdit_XMax.setText('')
        else: 
            self.lineEdit_XMax.setText(formatNum(self.tempData[4]))

    def set_YMax(self):
        val = readNum(str(self.lineEdit_YMax.text()), self)
        if isinstance(val,float):
            self.tempData[5] = val
            if self.tempData[2] is not None and self.tempData[5] is not None:
                self.tempData[8] = float(self.tempData[2])*float(self.tempData[5])
                self.set_YMaxVolts()
        if self.tempData[5] is None:
            self.lineEdit_YMax.setText('')
        else: 
            self.lineEdit_YMax.setText(formatNum(self.tempData[5]))

    def set_ZMax(self):
        val = readNum(str(self.lineEdit_ZMax.text()), self)
        if isinstance(val,float):
            self.tempData[6] = val
            if self.tempData[3] is not None and self.tempData[6] is not None:
                self.tempData[9] = float(self.tempData[3])*float(self.tempData[6])
                self.set_ZMaxVolts()
        if self.tempData[6] is None:
            self.lineEdit_ZMax.setText('')
        else: 
            self.lineEdit_ZMax.setText(formatNum(self.tempData[6]))

    def set_XMaxVolts(self):
        #val = readNum(str(self.lineEdit_XMaxVolts.text()))
        #if isinstance(val,float):
        #    self.tempData[7] = val
        if self.tempData[7] is None:
            self.lineEdit_XMaxVolts.setText('')
        else: 
            self.lineEdit_XMaxVolts.setText(formatNum(self.tempData[7]))

    def set_YMaxVolts(self):
        #val = readNum(str(self.lineEdit_YMaxVolts.text()))
        #if isinstance(val,float):
        #    self.tempData[8] = val
        if self.tempData[8] is None:
            self.lineEdit_YMaxVolts.setText('')
        else: 
            self.lineEdit_YMaxVolts.setText(formatNum(self.tempData[8]))

    def set_ZMaxVolts(self):
        #val = readNum(str(self.lineEdit_ZMaxVolts.text()))
        #if isinstance(val,float):
        #    self.tempData[9] = val
        if self.tempData[9] is None:
            self.lineEdit_ZMaxVolts.setText('')
        else: 
            self.lineEdit_ZMaxVolts.setText(formatNum(self.tempData[9]))

    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous 
    # delay that allows other labrad / pyqt methods to run   
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class getCalibrationName(QtGui.QDialog, Ui_getCalibrationName):
    def __init__(self,reactor, calibrationDictionary, parent = None):
        super(getCalibrationName, self).__init__(parent)
        self.setupUi(self)
        
        self.pushButton.clicked.connect(self.acceptNewValues)
        self.calibrationDictionary = calibrationDictionary
        self.lineEdit.editingFinished.connect(self.checkUniqueName)

    def checkUniqueName(self):
        name = str(self.lineEdit.text())
        for key in self.calibrationDictionary:
            if name == key or name == 'Add New Calibration':
                self.lineEdit.setText('')

    def acceptNewValues(self):
        if len(self.lineEdit.text())> 10:
            self.accept()
        else:
            msgBox = QtGui.QMessageBox(self)
            msgBox.setIcon(QtGui.QMessageBox.Information)
            msgBox.setWindowTitle('Define Name Error')
            msgBox.setText("\r\n Make sure that the name is defined and is at least 10 characters long.")
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
            msgBox.exec_()

    def getName(self):
        return self.lineEdit.text()