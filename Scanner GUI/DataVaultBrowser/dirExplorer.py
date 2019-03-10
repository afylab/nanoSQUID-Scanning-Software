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

path = sys.path[0] + r"\DataVaultBrowser"
Ui_dvExplorer, QtBaseClass = uic.loadUiType(path + r"\dvExplorer.ui")

class dataVaultExplorer(QtGui.QMainWindow, Ui_dvExplorer):
    accepted = QtCore.pyqtSignal()

    def __init__(self, dv, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(dataVaultExplorer, self).__init__(parent)
        self.setupUi(self)

        self.reactor = reactor
        self.dv = dv 

        self.curDir = ''

        self.dirList.itemDoubleClicked.connect(self.updateDirs)
        self.fileList.itemSelectionChanged.connect(self.fileSelect)
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
        selectedItem = self.fileList.selectedItems()
        self.file = [str(item.text()) for item in selectedItem]
        if len(self.file) == 1:
            self.currentFile.setText(self.file[0])
        elif len(self.file) == 0:
            self.currentFile.setText('')
        else:
            self.currentFile.setText('Selected ' + str(len(self.file)) +' files')

    @inlineCallbacks
    def selectDirFile(self, c):
        self.directory = yield self.dv.cd()
        
        self.accepted.emit()

        #Reset all selected files and close
        selectedItem = self.fileList.selectedItems()
        for item in selectedItem:
            self.fileList.setItemSelected(item, False)
        self.close()

    def closeWindow(self):
        self.close()

if __name__ == "__main__":
	app = QtGui.QApplication([])
	from qtreactor import pyqt4reactor
	pyqt4reactor.install()
	from twisted.internet import reactor
	window = dataVaultExplorer(reactor)
	window.show()
	reactor.run()


