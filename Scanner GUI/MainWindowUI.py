# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MainWindow.ui'
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
        MainWindow.setEnabled(True)
        MainWindow.resize(500, 110)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(500, 110))
        MainWindow.setMaximumSize(QtCore.QSize(500, 110))
        self.centralwidget = QtGui.QWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.MainWindowBackground = QtGui.QFrame(self.centralwidget)
        self.MainWindowBackground.setGeometry(QtCore.QRect(0, 0, 500, 150))
        self.MainWindowBackground.setStyleSheet(_fromUtf8("#MainWindowBackground{\n"
"background: black\n"
"}"))
        self.MainWindowBackground.setFrameShape(QtGui.QFrame.StyledPanel)
        self.MainWindowBackground.setFrameShadow(QtGui.QFrame.Raised)
        self.MainWindowBackground.setObjectName(_fromUtf8("MainWindowBackground"))
        self.push_Layout5 = QtGui.QPushButton(self.MainWindowBackground)
        self.push_Layout5.setGeometry(QtCore.QRect(460, 30, 23, 23))
        self.push_Layout5.setObjectName(_fromUtf8("push_Layout5"))
        self.push_Layout3 = QtGui.QPushButton(self.MainWindowBackground)
        self.push_Layout3.setGeometry(QtCore.QRect(400, 30, 23, 23))
        self.push_Layout3.setObjectName(_fromUtf8("push_Layout3"))
        self.push_Layout2 = QtGui.QPushButton(self.MainWindowBackground)
        self.push_Layout2.setGeometry(QtCore.QRect(370, 30, 23, 23))
        self.push_Layout2.setObjectName(_fromUtf8("push_Layout2"))
        self.label_Layout = QtGui.QLabel(self.MainWindowBackground)
        self.label_Layout.setGeometry(QtCore.QRect(280, 30, 47, 23))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_Layout.setFont(font)
        self.label_Layout.setStyleSheet(_fromUtf8("#label_Layout{\n"
"color: rgb(168, 168, 168);\n"
"font: 10pt \"MS Shell Dlg 2\";\n"
"qproperty-alignment: \'AlignVCenter | AlignRight\';\n"
"qproperty-wordWrap: true;\n"
"}"))
        self.label_Layout.setObjectName(_fromUtf8("label_Layout"))
        self.push_Layout1 = QtGui.QPushButton(self.MainWindowBackground)
        self.push_Layout1.setGeometry(QtCore.QRect(340, 30, 23, 23))
        self.push_Layout1.setToolTip(_fromUtf8(""))
        self.push_Layout1.setStatusTip(_fromUtf8(""))
        self.push_Layout1.setWhatsThis(_fromUtf8(""))
        self.push_Layout1.setAccessibleName(_fromUtf8(""))
        self.push_Layout1.setAccessibleDescription(_fromUtf8(""))
        self.push_Layout1.setObjectName(_fromUtf8("push_Layout1"))
        self.push_Layout4 = QtGui.QPushButton(self.MainWindowBackground)
        self.push_Layout4.setGeometry(QtCore.QRect(430, 30, 23, 23))
        self.push_Layout4.setObjectName(_fromUtf8("push_Layout4"))
        self.push_Logo = QtGui.QPushButton(self.MainWindowBackground)
        self.push_Logo.setGeometry(QtCore.QRect(0, -15, 241, 120))
        self.push_Logo.setStyleSheet(_fromUtf8("#push_Logo{\n"
"image:url(:/nSOTScanner/SQUIDRotated2.png);\n"
"background: black;\n"
"}"))
        self.push_Logo.setObjectName(_fromUtf8("push_Logo"))
        self.push_Logo.raise_()
        self.push_Layout5.raise_()
        self.push_Layout3.raise_()
        self.push_Layout2.raise_()
        self.label_Layout.raise_()
        self.push_Layout1.raise_()
        self.push_Layout4.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 500, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        self.menuSystem = QtGui.QMenu(self.menubar)
        self.menuSystem.setObjectName(_fromUtf8("menuSystem"))
        self.menuGraphs = QtGui.QMenu(self.menubar)
        self.menuGraphs.setObjectName(_fromUtf8("menuGraphs"))
        self.menuModules = QtGui.QMenu(self.menubar)
        self.menuModules.setObjectName(_fromUtf8("menuModules"))
        self.menuUser_Channels = QtGui.QMenu(self.menubar)
        self.menuUser_Channels.setObjectName(_fromUtf8("menuUser_Channels"))
        self.menuExeriments = QtGui.QMenu(self.menubar)
        self.menuExeriments.setObjectName(_fromUtf8("menuExeriments"))
        self.menuHelp = QtGui.QMenu(self.menubar)
        self.menuHelp.setObjectName(_fromUtf8("menuHelp"))
        MainWindow.setMenuBar(self.menubar)
        self.actionScan_Control = QtGui.QAction(MainWindow)
        self.actionScan_Control.setObjectName(_fromUtf8("actionScan_Control"))
        self.actionLine_View = QtGui.QAction(MainWindow)
        self.actionLine_View.setObjectName(_fromUtf8("actionLine_View"))
        self.actionApproach_Control = QtGui.QAction(MainWindow)
        self.actionApproach_Control.setObjectName(_fromUtf8("actionApproach_Control"))
        self.actionTest_Draw_Square = QtGui.QAction(MainWindow)
        self.actionTest_Draw_Square.setObjectName(_fromUtf8("actionTest_Draw_Square"))
        self.actionLabRAD_Connect = QtGui.QAction(MainWindow)
        self.actionLabRAD_Connect.setObjectName(_fromUtf8("actionLabRAD_Connect"))
        self.menuModules.addAction(self.actionApproach_Control)
        self.menuModules.addAction(self.actionLabRAD_Connect)
        self.menuModules.addAction(self.actionLine_View)
        self.menuModules.addAction(self.actionScan_Control)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSystem.menuAction())
        self.menubar.addAction(self.menuGraphs.menuAction())
        self.menubar.addAction(self.menuModules.menuAction())
        self.menubar.addAction(self.menuUser_Channels.menuAction())
        self.menubar.addAction(self.menuExeriments.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "nSOT Scanner", None))
        self.push_Layout5.setText(_translate("MainWindow", "5", None))
        self.push_Layout3.setText(_translate("MainWindow", "3", None))
        self.push_Layout2.setText(_translate("MainWindow", "2", None))
        self.label_Layout.setText(_translate("MainWindow", "Layout: ", None))
        self.push_Layout1.setText(_translate("MainWindow", "1", None))
        self.push_Layout4.setText(_translate("MainWindow", "4", None))
        self.push_Logo.setText(_translate("MainWindow", "PushButton", None))
        self.menuFile.setTitle(_translate("MainWindow", "File", None))
        self.menuSystem.setTitle(_translate("MainWindow", "System", None))
        self.menuGraphs.setTitle(_translate("MainWindow", "Graphs", None))
        self.menuModules.setTitle(_translate("MainWindow", "Modules", None))
        self.menuUser_Channels.setTitle(_translate("MainWindow", "User Channels", None))
        self.menuExeriments.setTitle(_translate("MainWindow", "Exeriments", None))
        self.menuHelp.setTitle(_translate("MainWindow", "Help", None))
        self.actionScan_Control.setText(_translate("MainWindow", "Scan Control", None))
        self.actionLine_View.setText(_translate("MainWindow", "Line View", None))
        self.actionApproach_Control.setText(_translate("MainWindow", "Approach Control", None))
        self.actionTest_Draw_Square.setText(_translate("MainWindow", "Test Draw Square", None))
        self.actionLabRAD_Connect.setText(_translate("MainWindow", "LabRAD Connect", None))

import nSOTScannerResources_rc
