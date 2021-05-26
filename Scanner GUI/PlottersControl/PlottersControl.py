#Worked by Marec, Avi and Raymond
import sys
from PyQt4 import QtCore, QtGui, uic
from twisted.internet.defer import inlineCallbacks
import numpy as np
import os

path = sys.path[0] + r"\PlottersControl"
sys.path.append(sys.path[0] + r'\DataVaultBrowser')
sys.path.append(path + r'\Plotter')
sys.path.append(path + r'\Process List')
sys.path.append(path + r'\Multiplier Window')
sys.path.append(path + r'\Plotters Control Setting')
sys.path.append(path + r'\TuningForkFitting')


import plotter
import ProcessWindow
import MultiplierSettings
import dirExplorer
import PlottersControlSetting
import TuningForkFitting

Ui_CommandCenter, QtBaseClass = uic.loadUiType(path + r"\PlottersControl.ui")

'''
General Property of a Plotter include:
number
Data
PlotData
TraceFlag
DataType
NumberofindexVariables
file = None
directory = None
PlotParameters
file
Parameters
comments
Number_PlotData_X, Number_PlotData_Y
SweepingDirection = ''
'''
class CommandingCenter(QtGui.QMainWindow, Ui_CommandCenter):
    keyPressed = QtCore.pyqtSignal(QtCore.QEvent)

    def __init__(self, reactor, parent = None):
        super(CommandingCenter, self).__init__(parent)
        self.dv = False
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        self.PlotterList = [] #PlotterList contains the all the Plotters
        self.ProcessList = ProcessWindow.ProcessWindow(self.reactor, self)

        #Color Code  [0]for Text, [1] for Background
        self.Color_NoData = [QtGui.QColor(131, 131, 131), QtGui.QColor(0, 0, 0)]
        self.Color_ContainData = [QtGui.QColor(0, 0, 0), QtGui.QColor(100, 100, 100)]
        self.Color_ContainPlotData = [QtGui.QColor(0, 0, 0), QtGui.QColor(155, 155, 155)]

        self.subtractMenu = QtGui.QMenu()
        subOverallAvg = QtGui.QAction( "Subtract overall average", self)
        subOverallAvg.triggered.connect(self.subtractOverallAvg)
        self.subtractMenu.addAction(subOverallAvg)
        subPlane = QtGui.QAction( "Subtract planar fit", self)
        subPlane.triggered.connect(self.subtractPlane)
        self.subtractMenu.addAction(subPlane)
        subOverallQuad = QtGui.QAction( "Subtract overall quadratic fit", self)
        subOverallQuad.triggered.connect(self.subtractOverallQuad)
        self.subtractMenu.addAction(subOverallQuad)
        subSelectedAreaAvg = QtGui.QAction( "Subtract selected area average", self)
        subSelectedAreaAvg.triggered.connect(self.subtractSelectedArea)
        self.subtractMenu.addAction(subSelectedAreaAvg)
        subXAvg = QtGui.QAction( "Subtract X average", self)
        subXAvg.triggered.connect(self.subtractXAvg)
        self.subtractMenu.addAction(subXAvg)
        subYAvg = QtGui.QAction( "Subtract Y average", self)
        subYAvg.triggered.connect(self.subtractYAvg)
        self.subtractMenu.addAction(subYAvg)
        subXLinear = QtGui.QAction( "Subtract X linear fit", self)
        subXLinear.triggered.connect(self.subtractXLinear)
        self.subtractMenu.addAction(subXLinear)
        subYLinear = QtGui.QAction( "Subtract Y linear fit", self)
        subYLinear.triggered.connect(self.subtractYLinear)
        self.subtractMenu.addAction(subYLinear)
        subXQuad = QtGui.QAction( "Subtract X quadratic fit", self)
        subXQuad.triggered.connect(self.subtractXQuad)
        self.subtractMenu.addAction(subXQuad)
        subYQuad = QtGui.QAction( "Subtract Y quadratic fit", self)
        subYQuad.triggered.connect(self.subtractYQuad)
        self.subtractMenu.addAction(subYQuad)
        self.pushButton_SubtractOveralAverage.setMenu(self.subtractMenu)

        # Fine Tuning related functions
        self.FineTuneMenu = QtGui.QMenu()
        FineTuneNo1 = QtGui.QAction( "Fine Tune No.1", self)
        FineTuneNo1.triggered.connect(lambda: self.FineTune(self.listWidget_Plots.selectedItems()))
        self.FineTuneMenu.addAction(FineTuneNo1)
        SelectedAreaStandardDeviation = QtGui.QAction( "Selected Area Standard Deviation", self)
        SelectedAreaStandardDeviation.triggered.connect(lambda: self.SelectedAreaStandardDeviation(self.listWidget_Plots.selectedItems()))
        self.FineTuneMenu.addAction(SelectedAreaStandardDeviation)
        self.pushButton_FineTune.setMenu(self.FineTuneMenu)

        # self.listWidget_Plots.itemDoubleClicked.connect(self.EditPlotterName)
        self.pushButton_Subtract.clicked.connect(lambda: self.Process('Subtract'))
        self.pushButton_Addition.clicked.connect(lambda: self.Process('Addition'))
        self.pushButton_Product.clicked.connect(lambda: self.Process('Product'))
        self.pushButton_Division.clicked.connect(lambda: self.Process('Division'))
        self.pushButton_SetArea.clicked.connect(self.SetSelectedArea)
        self.SelectedArea_Flag = False
        self.pushButton_AddPlotter.clicked.connect(self.BrowseDataVault)
        self.pushButton_RefreshPlotters.clicked.connect(self.RefreshPlotters)
        self.pushButton_Setting.clicked.connect(self.OpenSetting)

        #####Multiply
        self.multiplier = 1.0
        self.MultiplyWindow = MultiplierSettings.MultiplierWindow(self.reactor, self)
        self.pushButton_MultiplySelected.clicked.connect(self.MultiplySelected)

        self.SettingWindow = PlottersControlSetting.SettingWindow(self.reactor, self, self.pushButton_Setting)

        self.SaveAllMatlabMenu = QtGui.QMenu()
        SaveAll2D = QtGui.QAction( "Save 2D Plot", self)
        SaveAll2D.triggered.connect(lambda: self.SaveAllPlot('2D'))
        self.SaveAllMatlabMenu.addAction(SaveAll2D)
        SaveAllhorizontal = QtGui.QAction( "Save horizontal Plot", self)
        SaveAllhorizontal.triggered.connect(lambda: self.SaveAllPlot('horizontal'))
        self.SaveAllMatlabMenu.addAction(SaveAllhorizontal)
        SaveAllVertical = QtGui.QAction( "Save vertical Plot", self)
        SaveAllVertical.triggered.connect(lambda: self.SaveAllPlot('vertical'))
        self.SaveAllMatlabMenu.addAction(SaveAllhorizontal)
        self.pushButton_savePlot.setMenu(self.SaveAllMatlabMenu)

        self.pushButton_ACfitting.clicked.connect(self.OpenTuningForkFittingWindow)
        self.TuningForkFittingWindow = TuningForkFitting.ACFittingWindow(self.reactor, self, self.pushButton_ACfitting)

        self.keyPressed.connect(self.PressingKey)

        self.RefreshInterface()

    def RefreshInterface(self):
        self.RefreshPlotList()
        self.DetermineEnableConditions()
        for button in self.ButtonsCondition:
            self.ProcessButton(button)

    def ProcessButton(self, button):
        button.setEnabled(self.ButtonsCondition[button])

    def DetermineEnableConditions(self):
        self.ButtonsCondition={
            self.pushButton_AddPlotter: (not self.dv == False) and (not self.dv is None),
            self.pushButton_RefreshPlotters: (not self.dv == False) and (not self.dv is None),
            self.pushButton_SetArea: (self.PlotterList != []),
            self.pushButton_SubtractOveralAverage: self.PlotterList != [],
            self.pushButton_savePlot: self.PlotterList != [],
            self.pushButton_MultiplySelected: self.PlotterList != [],
            self.pushButton_FineTune: self.PlotterList != [],
            self.pushButton_ACfitting: self.PlotterList != []
        }

#####Labrad Related Function
    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.cxn = dict['servers']['local']['cxn']
            self.gen_dv = dict['servers']['local']['dv']

            from labrad.wrappers import connectAsync
            self.cxn_pc = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn_pc.data_vault
            self.RefreshInterface()
        except:
            pass

    def disconnectLabRAD(self):
        self.cxn = False
        self.cxn_dv = False
        self.gen_dv = False
        self.dv = False
        self.RefreshInterface()

#####Labrad Related Function

#####Save Matlab file Related Function
    def SaveAllPlot(self, PlotType):
        fold = str(QtGui.QFileDialog.getExistingDirectory(self, directory = os.getcwd()))
        self.Feedback('Save All ' + PlotType + 'Data at ' + fold)
        for plotter in self.PlotterList:
            FolderAndName = fold + '/D' + plotter.file[0:5]
            if PlotType == '2D':
                plotter.genMatFile(FolderAndName)
            elif PlotType == 'horizontal':
                plotter.genLineMatFileh(FolderAndName)
            elif PlotType == 'vertical':
                plotter.genLineMatFilev(FolderAndName)

#####Save Matlab file Related Function

    def ClearListWidget(self):
        self.listWidget_Plots.clear()
        self.ProcessList.ClearListWidget()

    def RefreshPlotList(self):
        try:
            self.ClearListWidget()
            for plotter in self.PlotterList:
                item = QtGui.QListWidgetItem()
                number = plotter.number
                self.renderItem(item, number)
                self.listWidget_Plots.addItem(item)

            self.ProcessList.RefreshPlotList()
        except Exception as inst:
            print "Error: ", inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def renderItem(self, ListWidgetItem , number): #Based on the plotter.number, dress the Item property
        try:
            plotter = self.GrabPlotterFromNumber(number)
            index = self.PlotterList.index(plotter)
            Text = self.PlotterList[index].Title
            ListWidgetItem.setText(Text)

            if isinstance(plotter.Data, np.ndarray): #Check if it contains data
                ListWidgetItem.setTextColor(self.Color_ContainData[0])
                ListWidgetItem.setBackgroundColor(self.Color_ContainData[1])
            else:
                ListWidgetItem.setTextColor(self.Color_NoData[0])
                ListWidgetItem.setBackgroundColor(self.Color_NoData[1])
                ListWidgetItem.setToolTip('No Data Loaded')

            if isinstance(plotter.PlotData, np.ndarray) or isinstance(plotter.PlotData, list):#Check if it contains PlotData
                ListWidgetItem.setTextColor(self.Color_ContainPlotData[0])
                ListWidgetItem.setBackgroundColor(self.Color_ContainPlotData[1])
                x, y = str(plotter.Number_PlotData_X), str(plotter.Number_PlotData_Y)
                ListWidgetItem.setToolTip('X: ' + x + '; ' + 'Y: ' + y)

        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def GrabPlotterFromNumber(self, number): #return the plotter based on the plotter.number given
        for plotter in self.PlotterList:
            if number == plotter.number:
                return plotter

    def MaximizePlotter(self, item):
        index = self.listWidget_Plots.indexFromItem(item).row()
        self.PlotterList[index].showMaximized()

    def Process(self, Process, c = None):
        if self.ProcessList.label_Operation.text() == Process: #If the operation changed, kill the current list
            pass
        else:
            self.ProcessList.ClearListWidget()
            self.ProcessList.PlotsListA, self.ProcessList.PlotsListB = [], []

        self.ProcessList.raise_()
        self.ProcessList.moveDefault()
        self.ProcessList.show()
        self.ProcessList.label_Operation.setText(Process)

    def transferPlotData(self, plotter, PlotData, comments, filename, title, PlotParameters, indVars, depVars):
        plotter.PlotData = PlotData
        plotter.comments = ['faketime','fakeuser',comments]
        plotter.file = filename
        plotter.DataType = "2DPlot Reconstitute"
        plotter.Title = title
        plotter.PlotParameters = PlotParameters
        plotter.indVars = indVars
        plotter.depVars = depVars

    @inlineCallbacks
    def BrowseDataVault(self, c = None):
        try:
            self.dvExplorer = dirExplorer.dataVaultExplorer(self.dv, self.reactor)
            yield self.dvExplorer.popDirs()
            self.dvExplorer.show()
            self.dvExplorer.accepted.connect(lambda: self.OpenData(self.reactor, self.dvExplorer.file, self.dvExplorer.directory))
        except Exception as inst:
            print "Error: ", inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    @inlineCallbacks
    def OpenData(self, c, filelist, directory):
        for file in filelist:
            self.AddPlotter()
            yield self.PlotterList[-1].loadData(file, directory)

    def AddPlotter(self):
        try:
            ii= -1 #0 is MainPlot, so the number start with
            while True:
                ii +=1
                if ii not in [item.number for item in self.PlotterList]: #info[0] is label of plot
                    break
            self.PlotterList.append(plotter.Plotter(self.reactor, self.dv, ii, self))
            self.PlotterList[-1].moveDefault()
            self.PlotterList[-1].show()
            self.RefreshInterface()

        except Exception as inst:
            print "Error: ",inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def RemovePlotsListAItem(self, item):
        index = self.listWidget_PlotsListA.indexFromItem(item).row()
        self.PlotsListA.pop(index)
        self.RefreshInterface()

    def RemovePlotsListBItem(self, item):
        index = self.listWidget_PlotsListB.indexFromItem(item).row()
        self.PlotsListB.pop(index)
        self.RefreshInterface()

    def SetSelectedArea(self):
        if self.SelectedArea_Flag == False:
            self.plotter_AreaSelected = self.PlotterList[-1]
            self.Feedback('Selected Area change in ' + self.plotter_AreaSelected.Title + ' is globally applied')
            self.plotter_AreaSelected.AreaSelected.sigRegionChangeFinished.connect(lambda: self.ApplySelectedArea(self.plotter_AreaSelected))
            self.plotter_AreaSelected.raise_()
            self.SelectedArea_Flag = True
        else:
            self.Feedback('Selected Area change in ' + self.plotter_AreaSelected.Title + ' is disconnected from other plotters')
            self.plotter_AreaSelected.AreaSelected.sigRegionChangeFinished.disconnect()
            self.SelectedArea_Flag = False

    def ApplySelectedArea(self, plotterchanged,):
        AreaSelectedParameters = plotterchanged.AreaSelectedParameters
        pos = plotterchanged.AreaSelected.pos()
        size = plotterchanged.AreaSelected.size()
        for plotter in self.PlotterList:
            if plotter != plotterchanged:
                plotter.AreaSelectedParameters = AreaSelectedParameters
                plotter.AreaSelected.setSize(size)
                plotter.AreaSelected.setPos(pos)

#TuningFork
    def OpenTuningForkFittingWindow(self):
        self.TuningForkFittingWindow.raise_()
        self.TuningForkFittingWindow.show()

#####Refresh Plotters Function
    def RefreshPlotters(self):
        for plotter in self.PlotterList:
            plotter.refreshPlot()
        self.Feedback('Refresh Finished.')

#####Subtract Related Function
    def subtractOverallAvg(self):
        for plotter in self.PlotterList:
            plotter.subtractOverallAvg()

    def subtractPlane(self):
        for plotter in self.PlotterList:
            plotter.subtractPlane()

    def subtractOverallQuad(self):
        for plotter in self.PlotterList:
            plotter.subtractOverallQuad()

    def subtractXAvg(self):
        for plotter in self.PlotterList:
            plotter.subtractXAvg()

    def subtractYAvg(self):
        for plotter in self.PlotterList:
            plotter.subtractYAvg()

    def subtractXLinear(self):
        for plotter in self.PlotterList:
            plotter.subtractXLinear()

    def subtractYLinear(self):
        for plotter in self.PlotterList:
            plotter.subtractYLinear()

    def subtractXQuad(self):
        for plotter in self.PlotterList:
            plotter.subtractXQuad()

    def subtractYQuad(self):
        for plotter in self.PlotterList:
            plotter.subtractYLinear()

    def subtractSelectedArea(self):
        for plotter in self.PlotterList:
            plotter.subtractOverallConstant(plotter.Average_SelectedArea)
#####Subtract Related Function

    def MultiplySelected(self):
        self.MultiplyWindow.moveDefault()
        self.MultiplyWindow.show()

    def MultiplySelectedPlotData(self, multiplier):
        itemlist = self.listWidget_Plots.selectedItems ()
        PlotterList = []
        for item in itemlist:
            PlotterList.append(self.PlotterList[self.listWidget_Plots.indexFromItem(item).row()])
        for plotter in self.PlotterList:
            plotter.MultiplyPlotData(multiplier)
        self.Feedback('Multiply ' + str(len(PlotterList)) + ' plotters by ' + str(multiplier))

    def FineTune(self, plotteritems):
        try:
            if len(plotteritems) !=2 :
                self.Feedback('Please make sure to select two plotters.')
            else:
                indexlist = []
                plotterlist = []
                for item in plotteritems:
                    indexlist.append(self.listWidget_Plots.indexFromItem(item).row())
                    plotterlist.append(self.PlotterList[self.listWidget_Plots.indexFromItem(item).row()])
                SelectedAreaData = [self.PlotterList[indexlist[0]].SelectedAreaData, self.PlotterList[indexlist[1]].SelectedAreaData]
                print self.CalculateAverage(np.absolute(SelectedAreaData[0]-SelectedAreaData[1]))
                histA = self.HistogramOfData(plotterlist[0].PlotData, self.SettingWindow.Setting_Parameter['NumberHistogramBin'])
                histB = self.HistogramOfData(plotterlist[1].PlotData, self.SettingWindow.Setting_Parameter['NumberHistogramBin'])
                hist = self.HistogramOfData(plotterlist[0].PlotData - plotterlist[1].PlotData, self.SettingWindow.Setting_Parameter['NumberHistogramBin'])
                print 'A',histA
                print 'B',histB
                print 'A-B',hist
        except Exception as inst:
            print "Error: ", inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno

    def SelectedAreaStandardDeviation(self, plotteritems):
        try:
            if len(plotteritems) <= 1 :
                self.Feedback('Please select plotters.')
            else:
                indexlist = []
                for item in plotteritems:
                    indexlist.append(self.listWidget_Plots.indexFromItem(item).row())
                DataRef = self.PlotterList[indexlist[0]].SelectedAreaData
                for index in indexlist[1:]:
                    plotter = self.PlotterList[index]
                    SelectedAreaData = plotter.SelectedAreaData
                    multiplier, offset = np.polyfit(SelectedAreaData.flatten(), DataRef.flatten(), 1)
                    plotter.MultiplyPlotData(multiplier)
                    plotter.subtractOverallConstant(-offset)
                self.Feedback('Fine Tuning finished')

        except Exception as inst:
            print "Error: ", inst
            print "Occured at line: ", sys.exc_traceback.tb_lineno
            print SelectedAreaData, len(SelectedAreaData[0]), len(SelectedAreaData[1])

    def CalculateAverage(self, data):
        average = np.mean(data)
        return average

    def HistogramOfData(self, data, number):
        try:
            datamin, datamax = np.amin(data), np.amax(data) #generate the bin for histogram, symmtric around zero
            print datamin,datamax
            interval = (datamax - datamin) / number
            binlist = np.linspace(datamin, datamax, number - 1)
            sortedbinlist = sorted(binlist, key=abs)
            print sortedbinlist
            offset = (sortedbinlist[0] + sortedbinlist[1]) / 2
            print offset
            binlistmin, binlistmax = datamin + offset, datamax + offset
            if offset > 0:
                binlistmin -= 2 * offset
            elif offset < 0:
                binlistmax += 2 * offset
            binlist = np.linspace(binlistmin, binlistmax, number)
            histogram = np.histogram(data, binlist, density = True)
            return histogram
        except Exception as inst:
                print 'Following error was thrown: ', inst
                print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

    def OpenSetting(self):
        self.SettingWindow.show()
        self.SettingWindow.raise_()

    def keyPressEvent(self, event):
        super(CommandingCenter, self).keyPressEvent(event)
        self.keyPressed.emit(event)

    def PressingKey(self, event):
        if event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace:
            itemlist = self.listWidget_Plots.selectedItems ()
            if not itemlist is None:
                index = []
                for item in itemlist:
                    index.append(self.listWidget_Plots.indexFromItem(item).row())
                index.sort(reverse = True)
                for value in index:
                    self.DeletePlotter(value)
        elif event.key() == 83: #Ctrl + S
            itemlist = self.listWidget_Plots.selectedItems ()
            if not itemlist is None:
                for item in itemlist:
                    index = self.listWidget_Plots.indexFromItem(item).row()
                    self.PlotterList[index].raise_()

    def DeletePlotter(self, index):
        self.PlotterList[index].close()

    def CopyPlotter(self, plotter):
        pass

    def Feedback(self, str):
        self.label_Feedback.setText(str)

    def moveDefault(self):
        self.move(10,170)
