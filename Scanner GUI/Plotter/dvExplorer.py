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

dirExplorerGUI = r"C:\Python27\dataExplorer\dvExplorer.ui"
editDatasetInfoGUI = r"C:\Python27\dataExplorer\editDatasetInfo.ui"


Ui_MainWindow, QtBaseClass = uic.loadUiType(dirExplorerGUI)
Ui_EditDataInfo, QtBaseClass = uic.loadUiType(editDatasetInfoGUI)

class editDataInfo(QtGui.QDialog, Ui_EditDataInfo):
	def __init__(self, reactor, parent = None):
		super(editDataInfo, self).__init__(parent)

		self.reactor = reactor
		self.setupUi(self)
		self.window = window
		self.dv = self.window.dv
		self.dataSet = str(self.window.currentFile.text())
		self.ok.clicked.connect(self.updateComments)
		self.cancel.clicked.connect(self.exitEdit)
		self.name.setWordWrap(True)
		self.currentComs.setReadOnly(True)

		self.setupTags(self)

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



class dataVaultExplorer(QtGui.QDialog, Ui_MainWindow):
	def __init__(self, reactor, parent = None):
		super(dataVaultExplorer, self).__init__(parent)
		QtGui.QDialog.__init__(self)

		self.reactor = reactor
		self.setupUi(self)

		self.home.setIcon(QtGui.QIcon("homeIcon.png"))
		self.back.setIcon(QtGui.QIcon("backIcon.png"))
		self.currentDir.setReadOnly(True)
		self.currentFile.setReadOnly(True)
		self.curDir = ''

		self.connect()

		self.dirList.itemDoubleClicked.connect(self.updateDirs)
		self.fileList.itemClicked.connect(self.fileSelect)
		self.fileList.itemDoubleClicked.connect(self.displayInfo)
		self.back.clicked.connect(self.backUp)
		self.home.clicked.connect(self.goHome)
		self.addDir.clicked.connect(self.makeDir)
		self.select.clicked.connect(self.selectDirFile)
		self.cancelSelect.clicked.connect(self.closeWindow)



	@inlineCallbacks
	def connect(self):
		from labrad.wrappers import connectAsync
		try:
			self.cxn = yield connectAsync(name = 'name')
			self.dv = yield self.cxn.data_vault
		except:
			print 'Either no LabRad connection or DataVault connection.'
		self.popDirs()

	@inlineCallbacks
	def popDirs(self):
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


	@inlineCallbacks
	def updateDirs(self, subdir):
		subdir = str(subdir.text())
		self.curDir = subdir
		yield self.dv.cd(subdir, False)
		self.popDirs()

	@inlineCallbacks
	def backUp(self, c):
		if self.curDir == '':
			pass
		else:
			direct = yield self.dv.cd()
			back = direct[0:-1]
			self.curDir = back[-1]
			yield self.dv.cd(back)
			self.popDirs()

	@inlineCallbacks
	def goHome(self, c):
		yield self.dv.cd('')
		self.curDir = ''
		self.popDirs()

	@inlineCallbacks
	def makeDir(self, c):
		direct, ok = QtGui.QInputDialog.getText(self, "Make directory", "Directory Name: " )
		if ok:
			yield self.dv.mkdir(str(direct))
			self.popDirs()

	@inlineCallbacks
	def displayInfo(self, c):
		dataSet = str(self.currentFile.text())
		yield self.dv.open(str(dataSet))
		self.editDataInfo = editDataInfo(c)
		self.editDataInfo.show()

	def fileSelect(self):
		file = self.fileList.currentItem()
		self.currentFile.setText(file.text())

	def selectDirFile(self):
		file = self.currentFile.text()
		directory = self.currentDir.text()
		self.close()
	def closeWindow(self):
		self.close()

	def closeEvent(self, e):
		self.reactor.stop()
		print 'Reactor shut down.'

if __name__ == "__main__":
	app = QtGui.QApplication([])
	from qtreactor import pyqt4reactor
	pyqt4reactor.install()
	from twisted.internet import reactor
	window = dataVaultExplorer(reactor)
	window.show()
	reactor.run()



'''
#Print Error
try:
	yield 'something'
except Exception as inst:
	print type(inst)
	print inst.args
	print inst
'''