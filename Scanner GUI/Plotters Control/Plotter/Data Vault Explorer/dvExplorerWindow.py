import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import threading
import copy

path = sys.path[0] + r"\Plotters Control\Plotter\Data Vault Explorer"
Ui_dvExplorer, QtBaseClass = uic.loadUiType(path + r"\dvExplorerWindow.ui")

class dataVaultExplorer(QtGui.QDialog, Ui_dvExplorer):
    def __init__(self, dv, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(dataVaultExplorer, self).__init__(parent)
        self.setupUi(self)

        self.reactor = reactor
        self.dv = dv 

        self.currentDir.setReadOnly(True)
        self.currentFile.setReadOnly(True)
        self.curDir = ''

        self.dirList.itemDoubleClicked.connect(self.updateDirs)
        self.fileList.itemClicked.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(self.selectDirFile)
        self.back.clicked.connect(self.backUp)
        self.home.clicked.connect(self.goHome)
        self.pushButton_dvexplorer_refresh.clicked.connect(self.popDirs)
        self.addDir.clicked.connect(self.makeDir)
        self.select.clicked.connect(self.selectDirFile)
        self.cancelSelect.clicked.connect(self.closeWindow)

    @inlineCallbacks
    def popDirs(self, c = None):
        try:
            self.dirList.clear()
            self.fileList.clear()

            l = yield self.dv.dir()

            for i in l[0]:
                self.dirList.addItem(i)
            for i in l[1]:
                self.fileList.addItem(i)

            if self.curDir == '':
                self.currentDir.setText('Root')
                self.dirName.setText('Root')
                self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")
            else:
                self.currentDir.setText(self.curDir)
                self.dirName.setText(self.curDir)
                self.dirName.setStyleSheet("QLabel#dirName {color: rgb(131,131,131);}")
        except Exception as inst:
            print inst

    @inlineCallbacks
    def updateDirs(self, subdir):
        subdir = str(subdir.text())
        self.curDir = subdir
        yield self.dv.cd(subdir, False)
        self.popDirs(self.reactor)

    @inlineCallbacks
    def backUp(self, c):
        if self.curDir == '':
            pass
        else:
            self.currentFile.clear()
            direct = yield self.dv.cd()
            back = direct[0:-1]
            self.curDir = back[-1]
            yield self.dv.cd(back)
            self.popDirs(self.reactor)

    @inlineCallbacks
    def goHome(self, c):
        self.currentFile.clear()
        yield self.dv.cd('')
        self.curDir = ''
        self.popDirs(self.reactor)

    @inlineCallbacks
    def makeDir(self, c):
        direct, ok = QtGui.QInputDialog.getText(self, "Make directory", "Directory Name: " )
        if ok:
            yield self.dv.mkdir(str(direct))
            self.popDirs(self.reactor)

    def fileSelect(self):
        file = self.fileList.currentItem()
        print file
        self.currentFile.setText(file.text())

    def dataSetInfo(self):
        info =[self.file, self.directory, self.variables, self.parameters, self.comments]
        return info

    @inlineCallbacks
    def selectDirFile(self, c):
        self.file = str(self.currentFile.text())
        self.directory = yield self.dv.cd()
        try:
            yield self.dv.open(self.file)
        except Exception as inst:
            print 'Following error was thrown: ', inst
            print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

        variables = yield self.dv.variables()
        self.indVars = []
        self.depVars = []
        for i in variables[0]:
            self.indVars.append(str(i[0]))
        for i in variables[1]:
            self.depVars.append(str(i[0]))
        self.variables = [self.indVars, self.depVars]
        self.parameters = yield self.dv.get_parameters()
        self.comments = yield self.dv.get_comments()
        
        self.accept()

    def closeWindow(self):
        self.reject()

if __name__ == "__main__":
	app = QtGui.QApplication([])
	from qtreactor import pyqt4reactor
	pyqt4reactor.install()
	from twisted.internet import reactor
	window = dataVaultExplorer(reactor)
	window.show()
	reactor.run()


