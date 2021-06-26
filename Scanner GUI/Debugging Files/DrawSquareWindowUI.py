# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'DrawSquare.ui'
#
# Created by: PyQt5 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtWidgets.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.background = QtGui.QFrame(self.centralwidget)
        self.background.setGeometry(QtCore.QRect(0, 0, 651, 381))
        self.background.setStyleSheet(_fromUtf8("#background{\n"
"}"))
        self.background.setFrameShape(QtGui.QFrame.StyledPanel)
        self.background.setFrameShadow(QtGui.QFrame.Raised)
        self.background.setObjectName(_fromUtf8("background"))
        self.push_DrawSquare = QtGui.QPushButton(self.background)
        self.push_DrawSquare.setGeometry(QtCore.QRect(450, 240, 75, 23))
        self.push_DrawSquare.setObjectName(_fromUtf8("push_DrawSquare"))
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow", None))
        self.push_DrawSquare.setText(_translate("MainWindow", "Draw Square", None))

