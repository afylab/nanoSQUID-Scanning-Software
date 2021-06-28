import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from twisted.internet.defer import inlineCallbacks
from nSOTScannerFormat import printErrorInfo

path = sys.path[0] + r"\DataVaultBrowser"
Ui_dvExplorer, QtBaseClass = uic.loadUiType(path + r"\dvExplorer.ui")

class dataVaultExplorer(QtWidgets.QMainWindow, Ui_dvExplorer):
    accepted = QtCore.pyqtSignal()

    def __init__(self, dv, reactor, parent = None):
        QtWidgets.QDialog.__init__(self, parent)
        super(dataVaultExplorer, self).__init__(parent)
        self.setupUi(self)

        self.reactor = reactor
        self.dv = dv

        self.curDir = ''

        self.dirList.itemDoubleClicked.connect(lambda file: self.updateDirs(file))
        self.fileList.itemSelectionChanged.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(self.fileSelect)
        self.fileList.itemDoubleClicked.connect(lambda: self.selectDirFile())
        self.back.clicked.connect(lambda: self.backUp())
        self.home.clicked.connect(lambda: self.goHome())
        self.pushButton_dvexplorer_refresh.clicked.connect(lambda: self.popDirs())
        self.addDir.clicked.connect(lambda: self.makeDir())
        self.select.clicked.connect(lambda: self.selectDirFile())
        self.cancelSelect.clicked.connect(self.closeWindow)

        self.popDirs()

    @inlineCallbacks
    def popDirs(self):
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
            printErrorInfo()

    @inlineCallbacks
    def updateDirs(self, subdir):
        subdir = str(subdir.text())
        self.curDir = subdir
        yield self.dv.cd(subdir, False)
        yield self.popDirs()

    @inlineCallbacks
    def backUp(self):
        if self.curDir == '':
            pass
        else:
            self.currentFile.clear()
            direct = yield self.dv.cd()
            back = direct[0:-1]
            self.curDir = back[-1]
            yield self.dv.cd(back)
            yield self.popDirs()

    @inlineCallbacks
    def goHome(self):
        self.currentFile.clear()
        yield self.dv.cd('')
        self.curDir = ''
        self.popDirs()

    @inlineCallbacks
    def makeDir(self):
        direct, ok = QtWidgets.QInputDialog.getText(self, "Make directory", "Directory Name: " )
        if ok:
            yield self.dv.mkdir(str(direct))
            yield self.popDirs()

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
    def selectDirFile(self):
        self.directory = yield self.dv.cd()

        self.accepted.emit()

        #Reset all selected files and close
        selectedItem = self.fileList.selectedItems()
        for item in selectedItem:
            item.setSelected(False)
        self.close()

    def closeWindow(self):
        self.close()

if __name__ == "__main__":
	app = QtWidgets.QApplication([])
	from qtreactor import pyqt4reactor
	pyqt4reactor.install()
	from twisted.internet import reactor
	window = dataVaultExplorer(reactor)
	window.show()
	reactor.run()
