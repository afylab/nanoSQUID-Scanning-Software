# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'LabRADConnect.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(500, 250)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.background = QtGui.QFrame(self.centralwidget)
        self.background.setGeometry(QtCore.QRect(0, 0, 500, 250))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.background.sizePolicy().hasHeightForWidth())
        self.background.setSizePolicy(sizePolicy)
        self.background.setMinimumSize(QtCore.QSize(500, 250))
        self.background.setMaximumSize(QtCore.QSize(500, 250))
        self.background.setStyleSheet(_fromUtf8("#background{\n"
"background: black;\n"
"}"))
        self.background.setFrameShape(QtGui.QFrame.StyledPanel)
        self.background.setFrameShadow(QtGui.QFrame.Raised)
        self.background.setObjectName(_fromUtf8("background"))
        self.label_Session = QtGui.QLabel(self.background)
        self.label_Session.setGeometry(QtCore.QRect(0, 210, 100, 20))
        self.label_Session.setStyleSheet(_fromUtf8("#label_Session{\n"
"color: rgb(168, 168, 168);\n"
"font: 10pt \"MS Shell Dlg 2\";\n"
"qproperty-alignment: \'AlignVCenter | AlignRight\';\n"
"qproperty-wordWrap: true;\n"
"}"))
        self.label_Session.setObjectName(_fromUtf8("label_Session"))
        self.lineEdit_Session = QtGui.QLineEdit(self.background)
        self.lineEdit_Session.setGeometry(QtCore.QRect(110, 210, 311, 20))
        self.lineEdit_Session.setObjectName(_fromUtf8("lineEdit_Session"))
        self.push_Session = QtGui.QPushButton(self.background)
        self.push_Session.setGeometry(QtCore.QRect(430, 202, 36, 36))
        self.push_Session.setStyleSheet(_fromUtf8("#push_Session{\n"
"image:url(:/nSOTScanner/SessionSelect.png);\n"
"background: black;\n"
"}"))
        self.push_Session.setText(_fromUtf8(""))
        self.push_Session.setObjectName(_fromUtf8("push_Session"))
        self.label_LabRAD = QtGui.QLabel(self.background)
        self.label_LabRAD.setGeometry(QtCore.QRect(0, 50, 80, 15))
        self.label_LabRAD.setStyleSheet(_fromUtf8("#label_LabRAD{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignRight\';\n"
"}"))
        self.label_LabRAD.setObjectName(_fromUtf8("label_LabRAD"))
        self.label_DataVault = QtGui.QLabel(self.background)
        self.label_DataVault.setGeometry(QtCore.QRect(0, 70, 80, 15))
        self.label_DataVault.setStyleSheet(_fromUtf8("#label_DataVault{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignRight\';\n"
"}"))
        self.label_DataVault.setObjectName(_fromUtf8("label_DataVault"))
        self.label_SerialServer = QtGui.QLabel(self.background)
        self.label_SerialServer.setGeometry(QtCore.QRect(0, 90, 80, 15))
        self.label_SerialServer.setStyleSheet(_fromUtf8("#label_SerialServer{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignRight\';\n"
"}"))
        self.label_SerialServer.setObjectName(_fromUtf8("label_SerialServer"))
        self.label_DACADC = QtGui.QLabel(self.background)
        self.label_DACADC.setGeometry(QtCore.QRect(0, 110, 80, 15))
        self.label_DACADC.setStyleSheet(_fromUtf8("#label_DACADC{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignRight\';\n"
"}"))
        self.label_DACADC.setObjectName(_fromUtf8("label_DACADC"))
        self.label_LabRAD_status = QtGui.QLabel(self.background)
        self.label_LabRAD_status.setGeometry(QtCore.QRect(110, 50, 121, 15))
        self.label_LabRAD_status.setStyleSheet(_fromUtf8("#label_LabRAD_status{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_LabRAD_status.setObjectName(_fromUtf8("label_LabRAD_status"))
        self.label_DataVault_status = QtGui.QLabel(self.background)
        self.label_DataVault_status.setGeometry(QtCore.QRect(110, 70, 121, 15))
        self.label_DataVault_status.setStyleSheet(_fromUtf8("#label_DataVault_status{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_DataVault_status.setObjectName(_fromUtf8("label_DataVault_status"))
        self.push_LabRAD = QtGui.QPushButton(self.background)
        self.push_LabRAD.setGeometry(QtCore.QRect(90, 50, 15, 15))
        self.push_LabRAD.setStyleSheet(_fromUtf8("#push_LabRAD{\n"
"background:rgb(144, 140, 9);\n"
"border-radius: 4px;\n"
"}"))
        self.push_LabRAD.setText(_fromUtf8(""))
        self.push_LabRAD.setObjectName(_fromUtf8("push_LabRAD"))
        self.label_SerialServer_status = QtGui.QLabel(self.background)
        self.label_SerialServer_status.setGeometry(QtCore.QRect(110, 90, 121, 15))
        self.label_SerialServer_status.setStyleSheet(_fromUtf8("#label_SerialServer_status{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_SerialServer_status.setObjectName(_fromUtf8("label_SerialServer_status"))
        self.label_DACADC_status = QtGui.QLabel(self.background)
        self.label_DACADC_status.setGeometry(QtCore.QRect(110, 110, 121, 15))
        self.label_DACADC_status.setStyleSheet(_fromUtf8("#label_DACADC_status{\n"
"color:rgb(168,168,168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_DACADC_status.setObjectName(_fromUtf8("label_DACADC_status"))
        self.push_DataVault = QtGui.QPushButton(self.background)
        self.push_DataVault.setGeometry(QtCore.QRect(90, 70, 15, 15))
        self.push_DataVault.setStyleSheet(_fromUtf8("#push_DataVault{\n"
"background: rgb(144, 140, 9);\n"
" border-radius: 4px;\n"
"}"))
        self.push_DataVault.setText(_fromUtf8(""))
        self.push_DataVault.setObjectName(_fromUtf8("push_DataVault"))
        self.push_SerialServer = QtGui.QPushButton(self.background)
        self.push_SerialServer.setGeometry(QtCore.QRect(90, 90, 15, 15))
        self.push_SerialServer.setStyleSheet(_fromUtf8("#push_SerialServer{\n"
"background: rgb(144, 140, 9);\n"
" border-radius: 4px;\n"
"}"))
        self.push_SerialServer.setText(_fromUtf8(""))
        self.push_SerialServer.setObjectName(_fromUtf8("push_SerialServer"))
        self.push_DACADC = QtGui.QPushButton(self.background)
        self.push_DACADC.setGeometry(QtCore.QRect(90, 110, 15, 15))
        self.push_DACADC.setStyleSheet(_fromUtf8("#push_DACADC{\n"
"background: rgb(144, 140, 9);\n"
" border-radius: 4px;\n"
"}"))
        self.push_DACADC.setText(_fromUtf8(""))
        self.push_DACADC.setObjectName(_fromUtf8("push_DACADC"))
        self.push_ConnectAll = QtGui.QPushButton(self.background)
        self.push_ConnectAll.setGeometry(QtCore.QRect(80, 15, 121, 23))
        self.push_ConnectAll.setStyleSheet(_fromUtf8("#push_ConnectAll{\n"
"color: rgb(168,168,168);\n"
"background: rgb(60, 60, 60);\n"
"border-radius: 4px;\n"
"}"))
        self.push_ConnectAll.setObjectName(_fromUtf8("push_ConnectAll"))
        self.push_DisconnectAll = QtGui.QPushButton(self.background)
        self.push_DisconnectAll.setGeometry(QtCore.QRect(280, 15, 121, 23))
        self.push_DisconnectAll.setStyleSheet(_fromUtf8("#push_DisconnectAll{\n"
"color: rgb(168,168,168);\n"
"background: rgb(60, 60, 60);\n"
"border-radius: 4px;\n"
"}"))
        self.push_DisconnectAll.setObjectName(_fromUtf8("push_DisconnectAll"))
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "LabRAD Connect", None))
        self.label_Session.setText(_translate("MainWindow", "Session Folder:", None))
        self.label_LabRAD.setText(_translate("MainWindow", "LabRAD:", None))
        self.label_DataVault.setText(_translate("MainWindow", "Data Vault:", None))
        self.label_SerialServer.setText(_translate("MainWindow", "Serial Server:", None))
        self.label_DACADC.setText(_translate("MainWindow", "DAC ADC:", None))
        self.label_LabRAD_status.setText(_translate("MainWindow", "Not connected", None))
        self.label_DataVault_status.setText(_translate("MainWindow", "Not connected", None))
        self.label_SerialServer_status.setText(_translate("MainWindow", "Not connected", None))
        self.label_DACADC_status.setText(_translate("MainWindow", "Not connected", None))
        self.push_ConnectAll.setText(_translate("MainWindow", "Connect All Servers", None))
        self.push_DisconnectAll.setText(_translate("MainWindow", "Disconnect All Servers", None))

import nSOTScannerResources_rc
