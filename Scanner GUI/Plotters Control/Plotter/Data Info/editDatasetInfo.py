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

path = sys.path[0] + r"\Plotters Control\Plotter\Data Info"
Ui_EditDataInfo, QtBaseClass = uic.loadUiType(path + r"\editDatasetInfo.ui")

class editDataInfo(QtGui.QMainWindow, Ui_EditDataInfo):
    def __init__(self, reactor, parent = None):
        super(editDataInfo, self).__init__(parent)

        self.reactor = reactor
        self.setupUi(self)
        
        self.parent = parent

        self.pushButton_ok.clicked.connect(self.updateComments)
        self.pushButton_Cancel.clicked.connect(self.exitEdit)

        self.lineEdit_Title.editingFinished.connect(self.UpdateTitle)

    def RefreshInfo(self, c = None):
        try:
            name = self.parent.file
            datatype = self.parent.DataType
            TraceFlag = self.parent.TraceFlag
            NumberofindexVariables = self.parent.NumberofindexVariables
            indVars = self.parent.indVars
            depVars = self.parent.depVars
            params = self.parent.Parameters
            coms = self.parent.comments
            title = self.parent.Title
            
            self.ClearAll()
            
            #Name
            self.label_DataSetName.setText(name)
            
            #DataType
            self.lineEdit_DataType.setText(datatype)
            
            #TraceInfo
            if TraceFlag != None:
                self.lineEdit_TraceInfo.setText('Contain Trace/Retrace')
            elif TraceFlag == None:
                self.lineEdit_TraceInfo.setText('No Trace/Retrace')

            #Number of Index
            if NumberofindexVariables != 0:
                self.lineEdit_Numberofindex.setText(str(NumberofindexVariables))
            else:
                self.lineEdit_Numberofindex.setText("No index")
                
            #Independent/Dependent Variables
            for i in indVars:
                self.listWidget_IndependentVariables.addItem(i)
            for i in depVars:
                self.listWidget_DependentVariables.addItem(i)
                
            #Parameters
            for key in sorted(params):
                item = key + " : " + str(params[key])
                self.listWidget_parameters.addItem(item)
                
            #Comments
            if str(coms) == '[]':
                self.textEdit_CurrentComments.setText("(None)")
            else:
                s = ""
                for i in coms:
                    s += str(i[2]) + "\n\n" 
                self.textEdit_CurrentComments.setText(str(s))

            #Title
            self.lineEdit_Title.setText(title)
                
            #PlotDetails
            #X,Ydimension
            x ,y = self.parent.Number_PlotData_X, self.parent.Number_PlotData_Y
            self.textEdit_XPoints.setText(str(x))
            self.textEdit_YPoints.setText(str(y))
            
            #Sweeping direction
            Sweepdirect = self.parent.SweepingDirection
            if Sweepdirect != '':
                self.textEdit_SweepingAxis.setText(Sweepdirect.capitalize() + " Axis")
            else:
                self.textEdit_SweepingAxis.setText("None")

        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
                
    def ClearAll(self):
        self.lineEdit_DataType.clear()
        self.lineEdit_TraceInfo.clear()
        self.lineEdit_Numberofindex.clear()
        self.listWidget_IndependentVariables.clear()
        self.textEdit_CurrentComments.clear()
        self.listWidget_DependentVariables.clear()
        self.listWidget_parameters.clear()
        self.lineEdit_Title.clear()

    @inlineCallbacks
    def updateComments(self, c):
        coms = str(self.textEdit_AddComments.toPlainText())
        if coms == '':
            pass
        else:
            dv = self.parent.dv
            yield dv.add_comment(coms)
        self.close()
    
    def UpdateTitle(self):
        self.parent.Title = self.lineEdit_Title.text()
        self.RefreshInfo()
        self.parent.RefreshInterface()
        self.parent.parent.RefreshPlotList()
        
    def exitEdit(self):
        self.close()