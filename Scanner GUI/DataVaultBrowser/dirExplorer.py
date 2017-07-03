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
import sys

path = sys.path[0] + r"\DataVaultBrowser"

Ui_dvExplorer, QtBaseClass = uic.loadUiType(path + r"\dvExplorer.ui")
Ui_EditDataInfo, QtBaseClass = uic.loadUiType(path + r"\editDatasetInfo.ui")


class editDataInfo(QtGui.QDialog, Ui_EditDataInfo):
    def __init__(self, dataset, dv, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(editDataInfo, self).__init__(parent)


        self.reactor = reactor
        self.setupUi(self)
        self.dv = dv
        self.dataSet = dataset

        self.ok.clicked.connect(self.updateComments)
        self.cancel.clicked.connect(self.exitEdit)

        self.name.setWordWrap(True)
        self.currentComs.setReadOnly(True)
        self.setupTags(reactor)

    @inlineCallbacks
    def setupTags(self, c):
        name = yield self.dv.get_name()
        params = yield self.dv.get_parameters()
        coms = yield self.dv.get_comments()
        self.name.setText(name)
        self.name.setStyleSheet("QLabel#name {color: rgb(131,131,131);}")
        self.parameters.setText(str(params))
        self.parameters.setStyleSheet("QLabel#parameters {color: rgb(131,131,131);}")
        if str(coms) == '[]':
            self.currentComs.setText("(None)")
        else:
            s = ""
            for i in coms:
                s += str(i[2]) + "\n\n" 
            self.currentComs.setText(str(s))

    @inlineCallbacks
    def updateComments(self, c):
        coms = str(self.comments.toPlainText())
        if coms == '':
            pass
        else:
            yield self.dv.add_comment(coms)
        self.close()
        
    def exitEdit(self):
        self.close()

class dataVaultExplorer(QtGui.QDialog, Ui_dvExplorer):
    def __init__(self, dv, reactor, parent = None):
        QtGui.QDialog.__init__(self, parent)
        super(dataVaultExplorer, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        self.dv = dv 

        self.currentDir.setReadOnly(True)
        self.currentFile.setReadOnly(True)

        self.dirList.itemDoubleClicked.connect(self.updateDirs)
        self.fileList.itemClicked.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(self.displayInfo)
        self.back.clicked.connect(self.backUp)
        self.home.clicked.connect(self.goHome)
        self.refresh.clicked.connect(self.popDirs)
        self.addDir.clicked.connect(self.makeDir)
        self.select.clicked.connect(self.selectDirFile)
        self.cancelSelect.clicked.connect(self.closeWindow)
        
        self.popDirs(reactor)

    @inlineCallbacks
    def popDirs(self, c):
        self.dirList.clear()
        self.fileList.clear()
        l = yield self.dv.dir()
        curDir = yield self.dv.cd()
        self.curDir = curDir[-1]
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

    @inlineCallbacks
    def displayInfo(self, c):
        dataSet = str(self.currentFile.text())
        yield self.dv.open(str(dataSet))
        self.editDataInfo = editDataInfo(dataSet, self.dv, c, self)
        self.editDataInfo.show()

    def fileSelect(self):
        file = self.fileList.currentItem()
        self.currentFile.setText(file.text())


    def dirFileVars(self):
        info =[self.file, self.directory, self.plotVars]
        return info

    @inlineCallbacks
    def selectDirFile(self, c):
        self.file =  str(self.currentFile.text())
        self.directory = yield self.dv.cd()
        try: 
            yield self.dv.open(self.file)
            self.plotVars = yield self.dv.variables()
        except: 
            self.plotVars = ''
        self.accept()

    def closeWindow(self):
        self.reject()
        self.close()

'''
#Print Error
try:
	yield 'something'
except Exception as inst:
	print type(inst)
	print inst.args
	print inst
'''