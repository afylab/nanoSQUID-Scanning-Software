# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ScanControlWindow.ui'
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
        MainWindow.resize(1000, 750)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(1000, 750))
        MainWindow.setMaximumSize(QtCore.QSize(1000, 750))
        self.centralwidget = QtGui.QWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.background = QtGui.QFrame(self.centralwidget)
        self.background.setGeometry(QtCore.QRect(0, 0, 1000, 750))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.background.sizePolicy().hasHeightForWidth())
        self.background.setSizePolicy(sizePolicy)
        self.background.setStyleSheet(_fromUtf8("#background{\n"
"background: black\n"
"}"))
        self.background.setFrameShape(QtGui.QFrame.StyledPanel)
        self.background.setFrameShadow(QtGui.QFrame.Sunken)
        self.background.setObjectName(_fromUtf8("background"))
        self.PlotArea = QtGui.QFrame(self.background)
        self.PlotArea.setGeometry(QtCore.QRect(240, 90, 750, 650))
        self.PlotArea.setStyleSheet(_fromUtf8("#PlotArea{\n"
"background:grey\n"
"}"))
        self.PlotArea.setFrameShape(QtGui.QFrame.StyledPanel)
        self.PlotArea.setFrameShadow(QtGui.QFrame.Raised)
        self.PlotArea.setObjectName(_fromUtf8("PlotArea"))
        self.label_Frame = QtGui.QLabel(self.background)
        self.label_Frame.setGeometry(QtCore.QRect(10, 90, 52, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_Frame.setFont(font)
        self.label_Frame.setStyleSheet(_fromUtf8("#label_Frame{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Frame.setObjectName(_fromUtf8("label_Frame"))
        self.line_2 = QtGui.QFrame(self.background)
        self.line_2.setGeometry(QtCore.QRect(235, 91, 3, 660))
        self.line_2.setStyleSheet(_fromUtf8("#line_2{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.line_2.setFrameShadow(QtGui.QFrame.Plain)
        self.line_2.setFrameShape(QtGui.QFrame.VLine)
        self.line_2.setObjectName(_fromUtf8("line_2"))
        self.label_Xc = QtGui.QLabel(self.background)
        self.label_Xc.setGeometry(QtCore.QRect(10, 150, 16, 20))
        self.label_Xc.setStyleSheet(_fromUtf8("#label_Xc{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Xc.setObjectName(_fromUtf8("label_Xc"))
        self.label_Yc = QtGui.QLabel(self.background)
        self.label_Yc.setGeometry(QtCore.QRect(10, 180, 16, 20))
        self.label_Yc.setStyleSheet(_fromUtf8("#label_Yc{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Yc.setObjectName(_fromUtf8("label_Yc"))
        self.label_H = QtGui.QLabel(self.background)
        self.label_H.setGeometry(QtCore.QRect(105, 150, 16, 20))
        self.label_H.setStyleSheet(_fromUtf8("#label_H{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_H.setObjectName(_fromUtf8("label_H"))
        self.label_W = QtGui.QLabel(self.background)
        self.label_W.setGeometry(QtCore.QRect(105, 180, 16, 20))
        self.label_W.setStyleSheet(_fromUtf8("#label_W{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_W.setObjectName(_fromUtf8("label_W"))
        self.label_Angle = QtGui.QLabel(self.background)
        self.label_Angle.setGeometry(QtCore.QRect(40, 210, 70, 20))
        self.label_Angle.setStyleSheet(_fromUtf8("#label_Angle{\n"
"color: rgb(168, 168, 168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_Angle.setObjectName(_fromUtf8("label_Angle"))
        self.lineEdit_Xc = QtGui.QLineEdit(self.background)
        self.lineEdit_Xc.setGeometry(QtCore.QRect(25, 150, 60, 20))
        self.lineEdit_Xc.setStyleSheet(_fromUtf8(""))
        self.lineEdit_Xc.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_Xc.setObjectName(_fromUtf8("lineEdit_Xc"))
        self.lineEdit_Yc = QtGui.QLineEdit(self.background)
        self.lineEdit_Yc.setGeometry(QtCore.QRect(25, 180, 60, 20))
        self.lineEdit_Yc.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_Yc.setObjectName(_fromUtf8("lineEdit_Yc"))
        self.lineEdit_W = QtGui.QLineEdit(self.background)
        self.lineEdit_W.setGeometry(QtCore.QRect(120, 180, 60, 20))
        self.lineEdit_W.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_W.setObjectName(_fromUtf8("lineEdit_W"))
        self.lineEdit_H = QtGui.QLineEdit(self.background)
        self.lineEdit_H.setGeometry(QtCore.QRect(120, 150, 60, 20))
        self.lineEdit_H.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_H.setObjectName(_fromUtf8("lineEdit_H"))
        self.label_Center = QtGui.QLabel(self.background)
        self.label_Center.setGeometry(QtCore.QRect(25, 120, 70, 20))
        self.label_Center.setStyleSheet(_fromUtf8("#label_Center{\n"
"color: rgb(168, 168, 168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_Center.setObjectName(_fromUtf8("label_Center"))
        self.label_Size = QtGui.QLabel(self.background)
        self.label_Size.setGeometry(QtCore.QRect(120, 120, 70, 20))
        self.label_Size.setStyleSheet(_fromUtf8("#label_Size{\n"
"color: rgb(168, 168, 168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_Size.setObjectName(_fromUtf8("label_Size"))
        self.lineEdit_Angle = QtGui.QLineEdit(self.background)
        self.lineEdit_Angle.setGeometry(QtCore.QRect(120, 210, 60, 20))
        self.lineEdit_Angle.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_Angle.setObjectName(_fromUtf8("lineEdit_Angle"))
        self.line_3 = QtGui.QFrame(self.background)
        self.line_3.setGeometry(QtCore.QRect(2, 240, 235, 3))
        self.line_3.setStyleSheet(_fromUtf8("#line_3{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_3.setFrameShadow(QtGui.QFrame.Plain)
        self.line_3.setFrameShape(QtGui.QFrame.HLine)
        self.line_3.setObjectName(_fromUtf8("line_3"))
        self.label_Speed = QtGui.QLabel(self.background)
        self.label_Speed.setGeometry(QtCore.QRect(10, 240, 52, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_Speed.setFont(font)
        self.label_Speed.setStyleSheet(_fromUtf8("#label_Speed{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Speed.setObjectName(_fromUtf8("label_Speed"))
        self.push_FrameLock = QtGui.QPushButton(self.background)
        self.push_FrameLock.setGeometry(QtCore.QRect(190, 164, 23, 23))
        self.push_FrameLock.setStyleSheet(_fromUtf8("#push_FrameLock{\n"
"image:url(:/nSOTScanner/lock.png);\n"
"background: black;\n"
"}\n"
""))
        self.push_FrameLock.setText(_fromUtf8(""))
        self.push_FrameLock.setObjectName(_fromUtf8("push_FrameLock"))
        self.line_4 = QtGui.QFrame(self.background)
        self.line_4.setGeometry(QtCore.QRect(182, 190, 20, 3))
        self.line_4.setStyleSheet(_fromUtf8("#line_4{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_4.setFrameShadow(QtGui.QFrame.Plain)
        self.line_4.setFrameShape(QtGui.QFrame.HLine)
        self.line_4.setObjectName(_fromUtf8("line_4"))
        self.line_5 = QtGui.QFrame(self.background)
        self.line_5.setGeometry(QtCore.QRect(182, 160, 20, 3))
        self.line_5.setStyleSheet(_fromUtf8("#line_5{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_5.setFrameShadow(QtGui.QFrame.Plain)
        self.line_5.setFrameShape(QtGui.QFrame.HLine)
        self.line_5.setObjectName(_fromUtf8("line_5"))
        self.line_6 = QtGui.QFrame(self.background)
        self.line_6.setGeometry(QtCore.QRect(200, 161, 3, 5))
        self.line_6.setStyleSheet(_fromUtf8("#line_6{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.line_6.setFrameShadow(QtGui.QFrame.Plain)
        self.line_6.setFrameShape(QtGui.QFrame.VLine)
        self.line_6.setObjectName(_fromUtf8("line_6"))
        self.line_7 = QtGui.QFrame(self.background)
        self.line_7.setGeometry(QtCore.QRect(200, 186, 3, 5))
        self.line_7.setStyleSheet(_fromUtf8("#line_7{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.line_7.setFrameShadow(QtGui.QFrame.Plain)
        self.line_7.setFrameShape(QtGui.QFrame.VLine)
        self.line_7.setObjectName(_fromUtf8("line_7"))
        self.label_Linear = QtGui.QLabel(self.background)
        self.label_Linear.setGeometry(QtCore.QRect(10, 280, 80, 20))
        self.label_Linear.setStyleSheet(_fromUtf8("#label_Linear{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Linear.setObjectName(_fromUtf8("label_Linear"))
        self.label_LineTime = QtGui.QLabel(self.background)
        self.label_LineTime.setGeometry(QtCore.QRect(10, 310, 80, 20))
        self.label_LineTime.setStyleSheet(_fromUtf8("#label_LineTime{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_LineTime.setObjectName(_fromUtf8("label_LineTime"))
        self.lineEdit_Linear = QtGui.QLineEdit(self.background)
        self.lineEdit_Linear.setGeometry(QtCore.QRect(100, 280, 60, 20))
        self.lineEdit_Linear.setStyleSheet(_fromUtf8(""))
        self.lineEdit_Linear.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_Linear.setObjectName(_fromUtf8("lineEdit_Linear"))
        self.lineEdit_LineTime = QtGui.QLineEdit(self.background)
        self.lineEdit_LineTime.setGeometry(QtCore.QRect(100, 310, 60, 20))
        self.lineEdit_LineTime.setStyleSheet(_fromUtf8(""))
        self.lineEdit_LineTime.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_LineTime.setObjectName(_fromUtf8("lineEdit_LineTime"))
        self.label_FrameTime = QtGui.QLabel(self.background)
        self.label_FrameTime.setGeometry(QtCore.QRect(10, 340, 80, 20))
        self.label_FrameTime.setStyleSheet(_fromUtf8("#label_FrameTime{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_FrameTime.setObjectName(_fromUtf8("label_FrameTime"))
        self.lineEdit_FrameTime = QtGui.QLineEdit(self.background)
        self.lineEdit_FrameTime.setGeometry(QtCore.QRect(100, 340, 60, 20))
        self.lineEdit_FrameTime.setStyleSheet(_fromUtf8("#lineEdit_FrameTime{\n"
"background: rgb(181, 181, 181);\n"
"border: grey;\n"
"}"))
        self.lineEdit_FrameTime.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_FrameTime.setReadOnly(True)
        self.lineEdit_FrameTime.setObjectName(_fromUtf8("lineEdit_FrameTime"))
        self.push_SpeedLock = QtGui.QPushButton(self.background)
        self.push_SpeedLock.setGeometry(QtCore.QRect(170, 309, 23, 23))
        self.push_SpeedLock.setStyleSheet(_fromUtf8("#push_SpeedLock{\n"
"image:url(:/nSOTScanner/lock.png);\n"
"background: black;\n"
"}\n"
""))
        self.push_SpeedLock.setText(_fromUtf8(""))
        self.push_SpeedLock.setObjectName(_fromUtf8("push_SpeedLock"))
        self.line_8 = QtGui.QFrame(self.background)
        self.line_8.setGeometry(QtCore.QRect(2, 370, 235, 3))
        self.line_8.setStyleSheet(_fromUtf8("#line_8{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_8.setFrameShadow(QtGui.QFrame.Plain)
        self.line_8.setFrameShape(QtGui.QFrame.HLine)
        self.line_8.setObjectName(_fromUtf8("line_8"))
        self.label_DAQ = QtGui.QLabel(self.background)
        self.label_DAQ.setGeometry(QtCore.QRect(10, 370, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_DAQ.setFont(font)
        self.label_DAQ.setStyleSheet(_fromUtf8("#label_DAQ{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_DAQ.setObjectName(_fromUtf8("label_DAQ"))
        self.label_Pixels = QtGui.QLabel(self.background)
        self.label_Pixels.setGeometry(QtCore.QRect(10, 410, 31, 20))
        self.label_Pixels.setStyleSheet(_fromUtf8("#label_Pixels{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Pixels.setObjectName(_fromUtf8("label_Pixels"))
        self.label_Lines = QtGui.QLabel(self.background)
        self.label_Lines.setGeometry(QtCore.QRect(10, 440, 31, 20))
        self.label_Lines.setStyleSheet(_fromUtf8("#label_Lines{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Lines.setObjectName(_fromUtf8("label_Lines"))
        self.lineEdit_Pixels = QtGui.QLineEdit(self.background)
        self.lineEdit_Pixels.setGeometry(QtCore.QRect(50, 410, 60, 20))
        self.lineEdit_Pixels.setStyleSheet(_fromUtf8(""))
        self.lineEdit_Pixels.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_Pixels.setObjectName(_fromUtf8("lineEdit_Pixels"))
        self.lineEdit_Lines = QtGui.QLineEdit(self.background)
        self.lineEdit_Lines.setGeometry(QtCore.QRect(50, 440, 60, 20))
        self.lineEdit_Lines.setStyleSheet(_fromUtf8(""))
        self.lineEdit_Lines.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_Lines.setObjectName(_fromUtf8("lineEdit_Lines"))
        self.push_DataLock = QtGui.QPushButton(self.background)
        self.push_DataLock.setGeometry(QtCore.QRect(120, 424, 23, 23))
        self.push_DataLock.setStyleSheet(_fromUtf8("#push_DataLock{\n"
"image:url(:/nSOTScanner/lock.png);\n"
"background: black;\n"
"}\n"
""))
        self.push_DataLock.setText(_fromUtf8(""))
        self.push_DataLock.setObjectName(_fromUtf8("push_DataLock"))
        self.line_9 = QtGui.QFrame(self.background)
        self.line_9.setGeometry(QtCore.QRect(112, 450, 20, 3))
        self.line_9.setStyleSheet(_fromUtf8("#line_9{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_9.setFrameShadow(QtGui.QFrame.Plain)
        self.line_9.setFrameShape(QtGui.QFrame.HLine)
        self.line_9.setObjectName(_fromUtf8("line_9"))
        self.line_10 = QtGui.QFrame(self.background)
        self.line_10.setGeometry(QtCore.QRect(112, 420, 20, 3))
        self.line_10.setStyleSheet(_fromUtf8("#line_10{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_10.setFrameShadow(QtGui.QFrame.Plain)
        self.line_10.setFrameShape(QtGui.QFrame.HLine)
        self.line_10.setObjectName(_fromUtf8("line_10"))
        self.line_11 = QtGui.QFrame(self.background)
        self.line_11.setGeometry(QtCore.QRect(130, 446, 3, 5))
        self.line_11.setStyleSheet(_fromUtf8("#line_11{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.line_11.setFrameShadow(QtGui.QFrame.Plain)
        self.line_11.setFrameShape(QtGui.QFrame.VLine)
        self.line_11.setObjectName(_fromUtf8("line_11"))
        self.line_12 = QtGui.QFrame(self.background)
        self.line_12.setGeometry(QtCore.QRect(130, 421, 3, 5))
        self.line_12.setStyleSheet(_fromUtf8("#line_12{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.line_12.setFrameShadow(QtGui.QFrame.Plain)
        self.line_12.setFrameShape(QtGui.QFrame.VLine)
        self.line_12.setObjectName(_fromUtf8("line_12"))
        self.line_13 = QtGui.QFrame(self.background)
        self.line_13.setGeometry(QtCore.QRect(2, 470, 235, 3))
        self.line_13.setStyleSheet(_fromUtf8("#line_13{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_13.setFrameShadow(QtGui.QFrame.Plain)
        self.line_13.setFrameShape(QtGui.QFrame.HLine)
        self.line_13.setObjectName(_fromUtf8("line_13"))
        self.label_Saving = QtGui.QLabel(self.background)
        self.label_Saving.setGeometry(QtCore.QRect(780, 0, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_Saving.setFont(font)
        self.label_Saving.setStyleSheet(_fromUtf8("#label_Saving{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Saving.setObjectName(_fromUtf8("label_Saving"))
        self.label_Basename = QtGui.QLabel(self.background)
        self.label_Basename.setGeometry(QtCore.QRect(780, 30, 61, 20))
        self.label_Basename.setStyleSheet(_fromUtf8("#label_Basename{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Basename.setObjectName(_fromUtf8("label_Basename"))
        self.label_ImageNum = QtGui.QLabel(self.background)
        self.label_ImageNum.setGeometry(QtCore.QRect(940, 30, 51, 20))
        self.label_ImageNum.setStyleSheet(_fromUtf8("#label_ImageNum{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_ImageNum.setObjectName(_fromUtf8("label_ImageNum"))
        self.lineEdit_Basename = QtGui.QLineEdit(self.background)
        self.lineEdit_Basename.setGeometry(QtCore.QRect(780, 60, 120, 20))
        self.lineEdit_Basename.setStyleSheet(_fromUtf8(""))
        self.lineEdit_Basename.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_Basename.setObjectName(_fromUtf8("lineEdit_Basename"))
        self.lineEdit_ImageNum = QtGui.QLineEdit(self.background)
        self.lineEdit_ImageNum.setGeometry(QtCore.QRect(940, 60, 40, 20))
        self.lineEdit_ImageNum.setStyleSheet(_fromUtf8("#lineEdit_ImageNum{\n"
"background: rgb(181, 181, 181);\n"
"border: grey;\n"
"}"))
        self.lineEdit_ImageNum.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.lineEdit_ImageNum.setReadOnly(True)
        self.lineEdit_ImageNum.setObjectName(_fromUtf8("lineEdit_ImageNum"))
        self.line_14 = QtGui.QFrame(self.background)
        self.line_14.setGeometry(QtCore.QRect(2, 90, 996, 3))
        self.line_14.setStyleSheet(_fromUtf8("#line_14{\n"
"color:rgb(168, 168, 168)\n"
"}"))
        self.line_14.setFrameShadow(QtGui.QFrame.Plain)
        self.line_14.setFrameShape(QtGui.QFrame.HLine)
        self.line_14.setObjectName(_fromUtf8("line_14"))
        self.label_Display = QtGui.QLabel(self.background)
        self.label_Display.setGeometry(QtCore.QRect(260, 0, 81, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_Display.setFont(font)
        self.label_Display.setStyleSheet(_fromUtf8("#label_Display{\n"
"color: rgb(168, 168, 168)\n"
"}"))
        self.label_Display.setObjectName(_fromUtf8("label_Display"))
        self.label_Channel = QtGui.QLabel(self.background)
        self.label_Channel.setGeometry(QtCore.QRect(270, 30, 51, 20))
        self.label_Channel.setStyleSheet(_fromUtf8("#label_Channel{\n"
"color: rgb(168, 168, 168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_Channel.setObjectName(_fromUtf8("label_Channel"))
        self.label_Processing = QtGui.QLabel(self.background)
        self.label_Processing.setGeometry(QtCore.QRect(360, 30, 111, 20))
        self.label_Processing.setStyleSheet(_fromUtf8("#label_Processing{\n"
"color: rgb(168, 168, 168);\n"
"qproperty-alignment: \'AlignVCenter | AlignCenter\';\n"
"}"))
        self.label_Processing.setObjectName(_fromUtf8("label_Processing"))
        self.comboBox_Channel = QtGui.QComboBox(self.background)
        self.comboBox_Channel.setGeometry(QtCore.QRect(270, 60, 51, 22))
        self.comboBox_Channel.setObjectName(_fromUtf8("comboBox_Channel"))
        self.comboBox_Channel.addItem(_fromUtf8(""))
        self.comboBox_Channel.addItem(_fromUtf8(""))
        self.comboBox_Processing = QtGui.QComboBox(self.background)
        self.comboBox_Processing.setGeometry(QtCore.QRect(360, 60, 111, 22))
        self.comboBox_Processing.setObjectName(_fromUtf8("comboBox_Processing"))
        self.comboBox_Processing.addItem(_fromUtf8(""))
        self.comboBox_Processing.addItem(_fromUtf8(""))
        self.comboBox_Processing.addItem(_fromUtf8(""))
        self.comboBox_Processing.addItem(_fromUtf8(""))
        self.comboBox_Processing.addItem(_fromUtf8(""))
        self.comboBox_Processing.addItem(_fromUtf8(""))
        self.MiniPlotArea = QtGui.QFrame(self.background)
        self.MiniPlotArea.setGeometry(QtCore.QRect(5, 500, 228, 228))
        self.MiniPlotArea.setStyleSheet(_fromUtf8("#MiniPlotArea{\n"
"background:grey\n"
"}"))
        self.MiniPlotArea.setFrameShape(QtGui.QFrame.StyledPanel)
        self.MiniPlotArea.setFrameShadow(QtGui.QFrame.Raised)
        self.MiniPlotArea.setObjectName(_fromUtf8("MiniPlotArea"))
        self.push_Test = QtGui.QPushButton(self.background)
        self.push_Test.setGeometry(QtCore.QRect(560, 40, 75, 23))
        self.push_Test.setObjectName(_fromUtf8("push_Test"))
        self.MiniPlotArea.raise_()
        self.push_FrameLock.raise_()
        self.PlotArea.raise_()
        self.label_Frame.raise_()
        self.label_Xc.raise_()
        self.label_Yc.raise_()
        self.label_H.raise_()
        self.label_W.raise_()
        self.label_Angle.raise_()
        self.lineEdit_Xc.raise_()
        self.lineEdit_Yc.raise_()
        self.lineEdit_W.raise_()
        self.lineEdit_H.raise_()
        self.label_Center.raise_()
        self.label_Size.raise_()
        self.lineEdit_Angle.raise_()
        self.line_2.raise_()
        self.line_3.raise_()
        self.label_Speed.raise_()
        self.line_4.raise_()
        self.line_5.raise_()
        self.line_6.raise_()
        self.line_7.raise_()
        self.label_Linear.raise_()
        self.label_LineTime.raise_()
        self.lineEdit_Linear.raise_()
        self.lineEdit_LineTime.raise_()
        self.label_FrameTime.raise_()
        self.lineEdit_FrameTime.raise_()
        self.push_SpeedLock.raise_()
        self.line_8.raise_()
        self.label_DAQ.raise_()
        self.label_Pixels.raise_()
        self.label_Lines.raise_()
        self.lineEdit_Pixels.raise_()
        self.lineEdit_Lines.raise_()
        self.push_DataLock.raise_()
        self.line_9.raise_()
        self.line_10.raise_()
        self.line_11.raise_()
        self.line_12.raise_()
        self.line_13.raise_()
        self.label_Saving.raise_()
        self.label_Basename.raise_()
        self.label_ImageNum.raise_()
        self.lineEdit_Basename.raise_()
        self.lineEdit_ImageNum.raise_()
        self.line_14.raise_()
        self.label_Display.raise_()
        self.label_Channel.raise_()
        self.label_Processing.raise_()
        self.comboBox_Channel.raise_()
        self.comboBox_Processing.raise_()
        self.push_Test.raise_()
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Scan Control", None))
        self.label_Frame.setText(_translate("MainWindow", "Frame", None))
        self.label_Xc.setText(_translate("MainWindow", "Xc", None))
        self.label_Yc.setText(_translate("MainWindow", "Yc", None))
        self.label_H.setText(_translate("MainWindow", "H", None))
        self.label_W.setText(_translate("MainWindow", "W", None))
        self.label_Angle.setText(_translate("MainWindow", "Angle (°)", None))
        self.lineEdit_Xc.setText(_translate("MainWindow", "0", None))
        self.lineEdit_Yc.setText(_translate("MainWindow", "0", None))
        self.lineEdit_W.setText(_translate("MainWindow", "5u", None))
        self.lineEdit_H.setText(_translate("MainWindow", "5u", None))
        self.label_Center.setText(_translate("MainWindow", "Center (m)", None))
        self.label_Size.setText(_translate("MainWindow", "Size (m)", None))
        self.lineEdit_Angle.setText(_translate("MainWindow", "0", None))
        self.label_Speed.setText(_translate("MainWindow", "Speed", None))
        self.label_Linear.setText(_translate("MainWindow", "Linear (m/s)", None))
        self.label_LineTime.setText(_translate("MainWindow", "Time/Line (s)", None))
        self.lineEdit_Linear.setText(_translate("MainWindow", "78.13u", None))
        self.lineEdit_LineTime.setText(_translate("MainWindow", "64m", None))
        self.label_FrameTime.setText(_translate("MainWindow", "Time/Frame (s)", None))
        self.lineEdit_FrameTime.setText(_translate("MainWindow", "16.38", None))
        self.label_DAQ.setText(_translate("MainWindow", "Data Acquisition", None))
        self.label_Pixels.setText(_translate("MainWindow", "Pixels", None))
        self.label_Lines.setText(_translate("MainWindow", "Lines", None))
        self.lineEdit_Pixels.setText(_translate("MainWindow", "256", None))
        self.lineEdit_Lines.setText(_translate("MainWindow", "256", None))
        self.label_Saving.setText(_translate("MainWindow", "Saving", None))
        self.label_Basename.setText(_translate("MainWindow", "Basename", None))
        self.label_ImageNum.setText(_translate("MainWindow", "Image #", None))
        self.lineEdit_Basename.setText(_translate("MainWindow", "unnamed", None))
        self.lineEdit_ImageNum.setText(_translate("MainWindow", "1", None))
        self.label_Display.setText(_translate("MainWindow", "Display", None))
        self.label_Channel.setText(_translate("MainWindow", "Channel", None))
        self.label_Processing.setText(_translate("MainWindow", "Processing", None))
        self.comboBox_Channel.setItemText(0, _translate("MainWindow", "Z(m)", None))
        self.comboBox_Channel.setItemText(1, _translate("MainWindow", "B(T)", None))
        self.comboBox_Processing.setItemText(0, _translate("MainWindow", "Raw", None))
        self.comboBox_Processing.setItemText(1, _translate("MainWindow", "Subtract Average", None))
        self.comboBox_Processing.setItemText(2, _translate("MainWindow", "Subtract Slope", None))
        self.comboBox_Processing.setItemText(3, _translate("MainWindow", "Subtract Linear Fit", None))
        self.comboBox_Processing.setItemText(4, _translate("MainWindow", "Subtract Parabolic Fit", None))
        self.comboBox_Processing.setItemText(5, _translate("MainWindow", "Differentiate", None))
        self.push_Test.setText(_translate("MainWindow", "Test", None))

import nSOTScannerResources_rc
