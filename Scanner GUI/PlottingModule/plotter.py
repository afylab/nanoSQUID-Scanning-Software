
import os
import sys
from PyQt4 import QtCore, QtGui, uic
from twisted.internet.defer import inlineCallbacks, returnValue
import numpy as np
import pyqtgraph as pg
import time
from math import sqrt, pi, atan2
import scipy.io as sio
from scipy import optimize

path = sys.path[0] + r"\PlottingModule\Plotter"
sys.path.append(sys.path[0] + r'\Resources')

from nSOTScannerFormat import readNum, formatNum, processImageData, deriv

ui_path = sys.path[0] + r"\PlottingModule\UI Files"
Ui_Plotter1D, QtBaseClass = uic.loadUiType(ui_path + r"\Plotter1D.ui")
Ui_Plotter2D, QtBaseClass = uic.loadUiType(ui_path + r"\Plotter2D.ui")
Ui_DataInfo, QtBaseClass = uic.loadUiType(ui_path + r"\DatasetInfo.ui")
Ui_DespikesSetting, QtBaseClass = uic.loadUiType(ui_path + r"\DespikeSettings.ui")
Ui_DerivSet, QtBaseClass = uic.loadUiType(ui_path + r"\DerivSettings.ui")
Ui_SensitivitySettings, QtBaseClass = uic.loadUiType(ui_path + r"\SensitivitySettings.ui")
Ui_FitTFSettings, QtBaseClass = uic.loadUiType(ui_path + r"\TuningForkFittingWindow.ui")

'''
Write a description here
'''
class Plotter(QtGui.QMainWindow, Ui_Plotter2D):
    plotInfoChanged = QtCore.pyqtSignal()
    plotClosed = QtCore.pyqtSignal(object)

    def __init__(self, file, directory, settings, number, parent = None):
        super(Plotter, self).__init__()

        self.number = number
        self.parent = parent

        self.plotSettings = settings #Get default plot settings from the command center

        self.data = None

        self.dataInfoDict = {
            'file': file, #Name of the dataset
            'directory': directory, #DV directory of dataset
            'title': 'Plotter ' + str(self.number), #Title of the plotter object
            'dataType': '', #Data type, right now either 1Dplot or 2Dplot
            'traceFlag': None, #None if data does not have trace / retrace data, 0 if plotting trace, 1 if plotting retrace
            'numIndexVars': 0, #Number of index variables
            'indVars': [], #List of independent variables
            'depVars': [], #List of dependent variables
            'parameters': {}, #Dictionary of dataset parameters
            'comments': [], #List of strings of comments
        }

        self.plotParamsDict = {
            'xMax': 0.0,
            'xMin': 0.0,
            'deltaX': 0.0,
            'xPoints': 0.0,
            'xscale': 0.0,
            'yMax': 0.0,
            'yMin': 0.0,
            'deltaY': 0.0,
            'yPoints': 0.0,
            'yscale': 0.0,
            'sweepDir': '',
        }

        self.despikeSettingsDict = {
            'adjacentPoints': 3,
            'numSigma':       5,
        }

        self.derivSettingsDict = {
            'fitOrder': 2,
            'adjPnts':  5,
            'edgePnts': 10,
        }

        self.sensSettingsDict = {
            'gain': 1000,
            'bandwidth': 65000,
        }

        self.fitTFSettingsDict = {
            'gain': 1000,
            'method': 'Nelder-Mead',
            'dc data': 1,
            'tf data x': 2,
            'tf data y': 3
        }

        self.initializePlotter()

        self.PlotData = None
        self.aspectLocked = False

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for loading and parsing the data"""

    @inlineCallbacks
    def initializePlotter(self):
        try:
            #Create a datavault connection, open the right dataset, and extract variable information
            dv = yield self.loadDataInfo(self.dataInfoDict['file'], self.dataInfoDict['directory'])

            #Once the data type is known from the variables, load the appropriate UI and show the window
            self.loadPlotterUI()
            self.show()
            self.moveDefault()

            #Set the title once loaded. This is done in two parts, because loadData is asynchronous and
            #the PlottingModule might request the plot title before the data is done loading.
            self.dataInfoDict['title']  = 'Plotter ' + str(self.number) + ": " + self.dataInfoDict['dataType']
            self.plotInfoChanged.emit()

            #Load the data from the datavault connection
            yield self.loadData(dv)

            if not self.data is None:
                self.refreshPlot()

            #Signal that the plot now has data, and the Command Center should refresh the plot list
            self.plotInfoChanged.emit()
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    @inlineCallbacks
    def loadDataInfo(self, file, directory):
        #Loads the specified data vault file from the specified directory
        print("Loading file: ", file, " from directory:  ", directory)
        try:
            #Create a new dv connection so that multiple plotters can load data simultaneously
            from labrad.wrappers import connectAsync
            cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')
            dv = yield cxn.data_vault

            #Go to the file directory and open the file. Note, this does not load data.
            #It only makes it so that the dv connection is now referreing to information about this dataset.
            yield dv.cd(directory)
            yield dv.open(file)

            variables = yield dv.variables() #Get variable information
            parameters = yield dv.get_parameters() #Get parameter information
            self.dataInfoDict['comments'] = yield dv.get_comments() #Get comments

            #Parse the variables into a useful form, identifying independent and dependent variables
            #The dataType
            self.dataInfoDict['indVars'], self.dataInfoDict['depVars'], self.dataInfoDict['dataType'], self.dataInfoDict['traceFlag'], self.dataInfoDict['numIndexVars'] = self.parseVariables(variables)

            if not self.dataInfoDict['traceFlag'] is None: #If we have trace and retrace data
                self.dataInfoDict['indVars'] = self.dataInfoDict['indVars'][1:] #Remove the trace / retrace index from the independent variables

            if parameters is None:
                self.dataInfoDict['parameters'] = {}
            else:
                self.dataInfoDict['parameters'] = dict(parameters) #Parameters comes in tuples ('key', 'value'). Cast to dictionary

            returnValue(dv)
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def parseVariables(self, variables):
        #Reformat the variable information.

        #Variables from dv Returns a tuple with first entry a list of independent
        #variables, and second entry a list of dependent variables. Variables within the lists
        #are tuples with first entry being the variable name (a string).

        #Create list of independent and dependent variable names
        indVars = []
        depVars = []
        for i in variables[0]:
            indVars.append(str(i[0]))

        for i in variables[1]:
            depVars.append(str(i[0]))
        variables = [indVars, depVars]

        #All data saved from the nanoSQUID scanning software has the same general format
        #for independent variables. Each experimental independent variable has two associated
        #independent variables in the dataset. The first is an index, letting you know the order
        #in which the points were taken, and the second is the actual value. For example, a voltage
        #sweep will have both "Voltage Index" and "Voltage". If measuring 101 points from 0 to 1V,
        #"Voltage index" will have 0, 1, ..., 101 and "Voltage" will have 0, 0.01, ..., 1
        #Counting the number of inpedent varaibles with "index" tells us how many dependent
        #variables there are, and what kind of plot to make (1D or 2D)
        numIndexVars = 0
        #Furthermore, data taken that sweeps in both directioon have "Trace" data and "Retrace" dataset
        #This is also important to plot the data correctly, and has a separately associated index.
        #The plotter assumes that the data does not have trace and retrace data if the dataset
        #has an inpendent variable indexing it. TraceFlag = 0 plots the trace, 1 plots retrace
        TraceFlag = None

        for var in indVars:
            if var == 'Trace Index' or var == 'Retrace Index':
                TraceFlag = 0 #by default set traceflag to trace. This also does not incremenet numebr of index variables
            elif "index" in var or "Index" in var:
                numIndexVars +=1

        if len(indVars)-numIndexVars == 1:
            DataType = "1DPlot"
        else:
            DataType = "2DPlot"

        return indVars, depVars, DataType, TraceFlag, numIndexVars

        self.editDataInfo.RefreshInfo() #This is called after a returns so it does nothing?

    @inlineCallbacks
    def loadData(self, dv):
        rawData = yield self.getData(dv) #Get the raw data
        try:
            if not self.dataInfoDict['traceFlag'] is None:
                self.data = self.splitTraceRetraceData(rawData)
            else:
                self.data = rawData

            if len(rawData) == 0:
                self.data = None
                self.updatePlotterStatus('Data Empty, check data integrity')
            elif np.isnan(rawData).any(): #Alert user if data is corrupted by NaNs
                rawData = self.removeNaN(rawData)
                self.updatePlotterStatus('NaN detected in data. Check data integrity')
        except Exception as inst:
            print('Following error was thrown: ', inst)
            print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    @inlineCallbacks
    def getData(self, dv):
        #Get all the data in datavault. This function only reads 1000 datapoints at a time.
        #Between readings of 1000 datapoints, the rest of the software updates
        #asynchronously and doesn't hang
        try:
            self.updatePlotterStatus("Loading data")

            i = 0 #Keep track of the number of lines read
            n = 0 #The number of periods to put after the string "Loading data" (see below)
            #Get the first 10000 points. This takes ~10 ms.
            #The fewer the points taken, the smoother the rest of the GUI runs, but the slower the data is loaded
            line = yield dv.get(10000)
            rawData = np.asarray(line) #Make the data into a numpy array

            while True:
                i += 1
                if i%4 == 0: #every 4th line read
                    n = (n+1)%4 #Add between 0 and 3 periods after loading data string
                    self.updatePlotterStatus("Loading data" + n*".")

                yield self.parent.sleep(0.001) #Wait for 1 ms to give rest of the software a chance to update
                line = yield dv.get(10000) #Get the next 10000 points. This takes ~10 ms
                if len(line) == 0: #If there are no more datapoint, break out of the loop
                    break
                else:
                    rawData = np.vstack((rawData, np.asarray(line))) #Otherwise, stack the data onto the np array

            self.updatePlotterStatus("Data loaded")

            returnValue(rawData)
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def removeNaN(self, data):
        try:
            raw = data
            listtodelete = []
            for i in range(len(raw[0])):
                for j in range(len(raw)):
                    if np.isnan(raw[j][i]):
                        listtodelete.append(j)
            raw = np.delete(raw, listtodelete, 0)# 0 for horizontal
            return raw

        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def splitTraceRetraceData(self, rawData):
        try:
            #If the data has trace and retrace data, split the data into trace and retrace datasets
            #Plotter assumes we have trace/retrace for only 2DPlot

            #Assume the first column (and entry in indVars) is the trace / retrace index
            #When it's 0, it corresponds to data taken on the trace. When 1, retrace
            self.traceData, self.retraceData = self.split(rawData, rawData[:,0] == 0) #Create two datasets for the trace and retrace data

            #Remove the trace / retrace data columns from the data
            self.traceData = np.delete(self.traceData, 0, 1)
            self.retraceData = np.delete(self.retraceData, 0, 1)

            return self.traceData

        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def split(self, arr, cond):
        return [arr[cond], arr[~cond]]

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for loading and populating the UI"""

    def loadPlotterUI(self):
        try:
            if self.dataInfoDict['dataType'] == '2DPlot':
                self.setupUi(self) #For now, this sets up the 2D UI. Eventually, have different UI for 1D plots
            elif self.dataInfoDict['dataType'] == '1DPlot':
                self.setupUi(self)
            else:
                self.updatePlotterStatus("Data type not recognized.")

            self.setupAdditionalUi() #Setup the aditional UI, creating 2D plots, 1D linecut plots, and linecut objects
            self.refreshInterface() #Set file name, window title, and enables relevant pushButtons
            self.populateAxesComboBoxes() #Populate the comboBoxes for choices of x and y variables

            self.connectUi()
            self.moveDefault()
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def setupAdditionalUi(self):
        self.setupPlots()
        self.setupLinecut()

    def connectUi(self):
        self.pushButton_refresh.clicked.connect(self.refreshPlot)
        self.pushButton_Info.clicked.connect(self.displayInfo)
        self.pushButton_lockratio.clicked.connect(self.toggleAspectRatio)

        self.trSelectMenu = QtGui.QMenu()
        showTrace = QtGui.QAction("Plot Trace", self)
        showRetrace = QtGui.QAction("Plot Retrace", self)
        self.trSelectMenu.addAction(showTrace)
        self.trSelectMenu.addAction(showRetrace)
        showTrace.triggered.connect(self.plotTrace)
        showRetrace.triggered.connect(self.plotRetrace)
        self.pushButton_trSelect.setMenu(self.trSelectMenu)

        #Define and connect the drop down menu for the data set subtraction button
        subtractMenu = QtGui.QMenu() #Create Qt menu object

        subOverallAvg = QtGui.QAction("Subtract average", self)
        subOverallAvg.triggered.connect(self.subtractOverallAvg)
        subtractMenu.addAction(subOverallAvg)

        subPlane = QtGui.QAction("Subtract plane", self)
        subPlane.triggered.connect(self.subtractPlane)
        subtractMenu.addAction(subPlane)

        subOverallQuad = QtGui.QAction("Subtract quadratic plane", self)
        subOverallQuad.triggered.connect(self.subtractOverallQuad)
        subtractMenu.addAction(subOverallQuad)

        subXAvg = QtGui.QAction("Subtract line average - X", self)
        subXAvg.triggered.connect(self.subtractXAvg)
        subtractMenu.addAction(subXAvg)

        subYAvg = QtGui.QAction("Subtract line average - Y", self)
        subYAvg.triggered.connect(self.subtractYAvg)
        subtractMenu.addAction(subYAvg)

        subXLinear = QtGui.QAction("Subtract line linear fit - X", self)
        subXLinear.triggered.connect(self.subtractXLinear)
        subtractMenu.addAction(subXLinear)

        subYLinear = QtGui.QAction("Subtract line linear fit - Y", self)
        subYLinear.triggered.connect(self.subtractYLinear)
        subtractMenu.addAction(subYLinear)

        subXQuad = QtGui.QAction("Subtract line quadratic fit - X", self)
        subXQuad.triggered.connect(self.subtractXQuad)
        subtractMenu.addAction(subXQuad)

        subYQuad = QtGui.QAction("Subtract line quadratic fit - Y", self)
        subYQuad.triggered.connect(self.subtractYQuad)
        subtractMenu.addAction(subYQuad)

        self.pushButton_subtract.setMenu(subtractMenu) #Set as the menu for the subtraction pushButton

        #Define and connect the drop down menu for saving data as mat files
        saveMenu = QtGui.QMenu()

        twoDSave = QtGui.QAction("Save 2D plot", self)
        twoDSave.triggered.connect(self.matPlot)
        saveMenu.addAction(twoDSave)

        oneDSaveh = QtGui.QAction("Save horizontal line cut", self)
        oneDSaveh.triggered.connect(self.matLinePloth)
        saveMenu.addAction(oneDSaveh)

        oneDSavev = QtGui.QAction("Save vertical line cut", self)
        oneDSavev.triggered.connect(self.matLinePlotv)
        saveMenu.addAction(oneDSavev)

        self.pushButton_savePlot.setMenu(saveMenu)

        #Define and connect the drop down menu for despiking data
        despikeMenu = QtGui.QMenu()

        despike = QtGui.QAction("Despike data", self)
        despike.triggered.connect(lambda: self.despikeData())
        despikeMenu.addAction(despike)

        despikeSetting = QtGui.QAction("Settings", self)
        despikeSetting.triggered.connect(self.openDespikeSettings)
        despikeMenu.addAction(despikeSetting)

        self.pushButton_despike.setMenu(despikeMenu)

        #Define and connect the drop down menu for taking gradients of the data
        derivMenu = QtGui.QMenu()

        gradX = QtGui.QAction(QtGui.QIcon("nablaXIcon.png"), "Compute x-gradient", self)
        gradX.triggered.connect(self.xDeriv)
        derivMenu.addAction(gradX)

        gradY = QtGui.QAction(QtGui.QIcon("nablaYIcon.png"), "Compute y-gradient", self)
        gradY.triggered.connect(self.yDeriv)
        derivMenu.addAction(gradY)

        derivSettings = QtGui.QAction("Settings", self)
        derivSettings.triggered.connect(self.openDerivSettings)
        derivMenu.addAction(derivSettings)

        self.pushButton_gradient.setMenu(derivMenu)

        #Connect button to make hystogram range symmetric
        self.pushButton_symHist.clicked.connect(self.symmetrizeHistogram)

        #Estimate the sensitivity of the SQUID at various points
        squidSensMenu = QtGui.QMenu()

        computeSens = QtGui.QAction("Compute sensitivity", self)
        computeSens.triggered.connect(self.computeSQUIDSensitivity)
        squidSensMenu.addAction(computeSens)

        sensOptimal = QtGui.QAction("Plot optimal parameters", self)
        sensOptimal.triggered.connect(self.plotOptimalSQUIDParameters)
        squidSensMenu.addAction(sensOptimal)

        sensSettings = QtGui.QAction("Settings", self)
        sensSettings.triggered.connect(self.openSensitivitySettings)
        squidSensMenu.addAction(sensSettings)

        self.pushButton_sensitivity.setMenu(squidSensMenu)

        #Fit the scan AC data to the TF data to extract the TF oscillation amplitude and direction
        tfFittingMenu = QtGui.QMenu()

        fitOscillation = QtGui.QAction("Extract TF Oscillation Info", self)
        fitOscillation.triggered.connect(self.extractTFOscillationInfo)
        tfFittingMenu.addAction(fitOscillation)

        fitTFSettings = QtGui.QAction("Settings", self)
        fitTFSettings.triggered.connect(self.openFitTFSettings)
        tfFittingMenu.addAction(fitTFSettings)

        self.pushButton_TFfitting.setMenu(tfFittingMenu)

    def setupPlots(self):
        #Create plot view for 2D plot
        self.mainPlotView = pg.PlotItem(name = "Plot")
        self.mainPlotView.showAxis('top', show = True)
        self.mainPlotView.showAxis('right', show = True)
        self.mainPlotView.setAspectLocked(lock = False, ratio = 1)
        self.mainPlotView.setAspectLocked(False)
        self.mainPlotView.invertY(False)
        self.mainPlotView.setXRange(-1.25, 1.25)
        self.mainPlotView.setYRange(-10, 10)

        #Create 2D plot
        self.mainPlot = pg.ImageView(view = self.mainPlotView)
        self.mainPlot.setGeometry(QtCore.QRect(0, 0, 750, 450))
        self.mainPlot.ui.menuBtn.hide()
        self.mainPlot.ui.histogram.item.gradient.loadPreset('bipolar')
        self.mainPlot.ui.roiBtn.hide()
        self.mainPlot.ui.menuBtn.hide()

        #Add main plot to the proper layout in the GUI
        self.layout_mainPlotArea.addWidget(self.mainPlot)

        self.XZPlot = pg.PlotWidget()
        self.setup1DPlot(self.XZPlot, self.layout_XZPlotArea)

        self.YZPlot = pg.PlotWidget()
        self.setup1DPlot(self.YZPlot, self.layout_YZPlotArea)

    def setup1DPlot(self, plot, layout):
        plot.setGeometry(QtCore.QRect(0, 0, 635, 200))
        plot.showAxis('right', show = True)
        plot.showAxis('top', show = True)
        layout.addWidget(plot)

    def setupLinecut(self):
        #Create both vertical and horizontal line objects
        self.vLine = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.hLine = pg.InfiniteLine(pos = 0, angle = 0,  movable = True)

        #Add them to the 2D plot
        self.mainPlotView.addItem(self.vLine, ignoreBounds = True)
        self.mainPlotView.addItem(self.hLine, ignoreBounds = True)

        #connect position change signals to the appropriate function
        self.vLine.sigPositionChangeFinished.connect(lambda: self.ChangeLineCutValue(self.vLine))
        self.hLine.sigPositionChangeFinished.connect(lambda: self.ChangeLineCutValue(self.hLine))

    def populateAxesComboBoxes(self):
        try:
            indVars = self.dataInfoDict['indVars']
            numIndexVars = self.dataInfoDict['numIndexVars']

            if self.dataInfoDict['dataType'] == "2DPlot":
                #If 2D plot, add independent variables to both x and y axis combo box
                #the independent variable list (and saved data) takes the form: index, index, value, value
                #So only add variables starting from the position in the list corresponding to the numbers
                #of independent variables
                for name in indVars[numIndexVars:]:
                    if self.plotSettings['scanPlot_realPosition']:
                        if name ==  'X Pos. Voltage':
                            name = 'X position'
                        elif name == 'Y Pos. Voltage':
                            name = 'Y position'

                    self.comboBox_xAxis.addItem(name)
                    self.comboBox_yAxis.addItem(name)

                self.comboBox_xAxis.setCurrentIndex(0) #Default
                self.comboBox_yAxis.setCurrentIndex(1) #Default

            elif self.dataInfoDict['dataType'] == "1DPlot":
                self.comboBox_xAxis.addItem(indVars[numIndexVars])
                self.comboBox_xAxis.setCurrentIndex(0)#Default

            depVars = self.dataInfoDict['depVars']
            for var in depVars:
                self.comboBox_zAxis.addItem(var)
                self.comboBox_zAxis.setCurrentIndex(0)#Default

        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def refreshInterface(self):
        self.label_FileName.setText(self.dataInfoDict['file'])
        self.setWindowTitle(self.dataInfoDict['title'])
        self.enableDataRelevantUIElements()

    def enableDataRelevantUIElements(self):
        dataExists = (not self.data is None) #Is there data?
        plotDataExists = (not self.PlotData is None) #Is there plot data?
        is2DData = ('2DPlot' == self.dataInfoDict['dataType']) #Is the data 2D?
        traceFlag = not self.dataInfoDict['traceFlag'] is None #Does the data have trace/retrace data

        enablePushButtonDict ={
            self.pushButton_refresh: dataExists,
            self.pushButton_trSelect: dataExists and traceFlag,
            self.pushButton_lockratio: plotDataExists and is2DData,
            self.pushButton_symHist: plotDataExists and is2DData,
            self.pushButton_savePlot: plotDataExists,
            self.pushButton_Info: dataExists,
            self.pushButton_subtract: plotDataExists and is2DData,
            self.pushButton_despike: plotDataExists and is2DData,
            self.pushButton_gradient: plotDataExists and is2DData,
            self.pushButton_sensitivity: plotDataExists and is2DData and 'nSOT vs. Bias Voltage and Field' in self.dataInfoDict['file'],
            self.pushButton_TFfitting: plotDataExists and is2DData and 'nSOT Scan Data' in self.dataInfoDict['file'],
        }

        for button in enablePushButtonDict:
            button.setEnabled(enablePushButtonDict[button])

    def displayInfo(self):
        #Create and display data info window
        dataInfo = dataInfoWindow(self.dataInfoDict, self.plotParamsDict, parent = self)
        dataInfo.exec_()

    def updatePlotterStatus(self, string):
        self.lineEdit_plotterStatus.setText("Status: " + string)

    def moveDefault(self):
        parentx, parenty = self.parent.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        parentwidth = self.parent.width()
        Offset = self.number * 50 + 10
        self.move(parentx + parentwidth + Offset, parenty)

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for plotting the loaded data"""

    def refreshPlot(self):
        try:
            self.clearLinecutPlots()
            self.setPlotAxesNames()
            self.setPlotParameters()
            self.formatPlotData()
            self.plotData()

            self.updatePlotterStatus('Plot Refreshed')
            self.refreshInterface()

        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def setPlotAxesNames(self):
        self.mainPlotView.setLabel('left', text=self.comboBox_yAxis.currentText())
        self.mainPlotView.setLabel('bottom', text=self.comboBox_xAxis.currentText())
        self.XZPlot.setLabel('left', self.comboBox_zAxis.currentText())
        self.XZPlot.setLabel('bottom', self.comboBox_xAxis.currentText())
        self.YZPlot.setLabel('left', self.comboBox_yAxis.currentText())
        self.YZPlot.setLabel('bottom',self.comboBox_zAxis.currentText())

    def setPlotParameters(self):
        #xIndex gives the column index of the data corresponding to the data indices.
        #xIndex + numIndexVars gives column index of the data with the data itself.
        xIndex = self.comboBox_xAxis.currentIndex()
        yIndex = self.comboBox_yAxis.currentIndex()
        numIndexVars = self.dataInfoDict['numIndexVars']

        try:
            self.plotParamsDict['xMax'] = np.amax(self.data[:, numIndexVars + xIndex])
            self.plotParamsDict['xMin'] = np.amin(self.data[:, numIndexVars + xIndex])
            #If the data has position data and the settings specify to do so, convert to microns
            if self.plotSettings['scanPlot_realPosition'] and ' position' in self.comboBox_xAxis.currentText():
                self.plotParamsDict['xMax'] = self.plotParamsDict['xMax'] * self.plotSettings['scanPlot_scalefactor'] + self.plotSettings['scanPlot_offset']
                self.plotParamsDict['xMin'] = self.plotParamsDict['xMin'] * self.plotSettings['scanPlot_scalefactor'] + self.plotSettings['scanPlot_offset']

            self.plotParamsDict['deltaX'] = self.plotParamsDict['xMax'] - self.plotParamsDict['xMin']
            self.plotParamsDict['xPoints'] = np.amax(self.data[:, xIndex]) + 1  #Find the number of points using the index column of the data
            self.plotParamsDict['xscale']  = (self.plotParamsDict['xMax']-self.plotParamsDict['xMin']) / (self.plotParamsDict['xPoints'] -1)

            if "2DPlot" in self.dataInfoDict['dataType']:
                self.plotParamsDict['yMax'] = np.amax(self.data[:, numIndexVars + yIndex])
                self.plotParamsDict['yMin'] = np.amin(self.data[:, numIndexVars + yIndex])
                #If the data has position data and the settings specify to do so, convert to microns
                if self.plotSettings['scanPlot_realPosition'] and ' position' in self.comboBox_yAxis.currentText(): #If checked, make it micron unit
                    self.plotParamsDict['yMax'] = self.plotParamsDict['yMax'] * self.plotSettings['scanPlot_scalefactor'] + self.plotSettings['scanPlot_offset']
                    self.plotParamsDict['yMin'] = self.plotParamsDict['yMin'] * self.plotSettings['scanPlot_scalefactor'] + self.plotSettings['scanPlot_offset']

                self.plotParamsDict['deltaY'] = self.plotParamsDict['yMax'] - self.plotParamsDict['yMin']
                self.plotParamsDict['yPoints'] = np.amax(self.data[:, yIndex]) + 1
                self.plotParamsDict['yscale'] = (self.plotParamsDict['yMax']-self.plotParamsDict['yMin']) / (self.plotParamsDict['yPoints'] - 1)
        except Exception as inst:
            print('Following error was thrown: ', inst)
            print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def formatPlotData(self):
        xIndex = self.comboBox_xAxis.currentIndex()
        yIndex = self.comboBox_yAxis.currentIndex()
        zIndex = self.comboBox_zAxis.currentIndex() + len(self.dataInfoDict['indVars'])

        try:
            if "2DPlot" == self.dataInfoDict['dataType']:
                self.PlotData = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])
                for i in self.data:
                    self.PlotData[int(i[xIndex]), int(i[yIndex])] = i[zIndex]

                self.plotParamsDict['xPoints'], self.plotParamsDict['yPoints'] = self.PlotData.shape

                self.determineSweepDirection()

            elif "1DPlot" == self.dataInfoDict['dataType']:
                self.PlotData = [[],[]] #0 for x, 1 for y
                for i in self.data:
                    self.PlotData[0].append(i[self.dataInfoDict['numIndexVars']])
                    self.PlotData[1].append(i[zIndex])

                self.plotParamsDict['xPoints'], self.plotParamsDict['yPoints'] = len(self.PlotData[0]), 0
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def determineSweepDirection(self):
        #In a 2D dataset, either x is held constant as y sweeps through a range of values or vice Average_SelectedArea
        #This function determines which axis is being swept (the "fast axis") and which is incremented afterwards ("slow axis")
        indVars = self.dataInfoDict['indVars']
        xAxis_Name = self.comboBox_xAxis.currentText()

        sweepingIndependentAxis = []
        for i in range(len(indVars)):
            if self.data[1][i] != self.data[0][i]:
                sweepingIndependentAxis.append(indVars[i])

        if xAxis_Name in sweepingIndependentAxis:
            self.plotParamsDict['sweepDir'] = "x"
        else:
            self.plotParamsDict['sweepDir'] = "y"

    def plotData(self):
        if "2DPlot" in self.dataInfoDict['dataType']:
            self.setAspectRatio()
            self.mainPlot.setImage(self.PlotData, autoRange = True , autoLevels = True, pos=[self.plotParamsDict['xMin'] - (self.plotParamsDict['xscale'] / 2), self.plotParamsDict['yMin'] - (self.plotParamsDict['yscale'] / 2)],scale=[self.plotParamsDict['xscale'], self.plotParamsDict['yscale']])

            self.ResetLineCutPlots()

        elif "1DPlot" in self.dataInfoDict['dataType']:
            self.LineCutXZYVals = self.PlotData[1]
            self.LineCutXZXVals = self.PlotData[0]
            self.XZPlot.plot(x = self.LineCutXZXVals, y = self.LineCutXZYVals, pen = 0.5)

    def plotTrace(self):
        self.data = self.traceData
        self.refreshPlot()
        self.updatePlotterStatus('Trace plotted')

    def plotRetrace(self):
        self.data = self.retraceData
        self.refreshPlot()
        self.updatePlotterStatus('Retrace plotted')

    def symmetrizeHistogram(self):
        level = self.mainPlot.ui.histogram.item.getLevels()
        high = max(abs(level[0]), abs(level[1]))
        self.mainPlot.ui.histogram.item.setLevels(-high, high)

    def toggleAspectRatio(self):
        self.aspectLocked = not self.aspectLocked
        self.setAspectRatio()

    def setAspectRatio(self):
        if self.aspectLocked == False:
            self.mainPlotView.setAspectLocked(False)
        else:
            self.mainPlotView.setAspectLocked(True, ratio = 1)

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for linecuts"""

    def ResetLineCutPlots(self):
        if self.PlotData is None:
            pass
        else:
            self.vLine.setValue(self.plotParamsDict['xMin'])
            self.hLine.setValue(self.plotParamsDict['yMin'])
            self.verticalposition=self.plotParamsDict['xMin']
            self.horizontalposition=self.plotParamsDict['yMin']
            self.clearLinecutPlots()

    def SetupLineCutverticalposition(self):
        try:
            val = readNum(str(self.lineEdit_vCutPos.text()))
            if isinstance(val, float):
                self.verticalposition=val
            self.ChangeLineCutValue("")
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def SetupLineCuthorizontalposition(self):
        try:
            val = readNum(str(self.lineEdit_hCutPos.text()))
            if isinstance(val, float):
                self.horizontalposition=val
            self.ChangeLineCutValue("")
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def ChangeLineCutValue(self, LineCut):
        try:
            if LineCut == self.vLine:
                self.verticalposition=LineCut.value()
            if LineCut == self.hLine:
                self.horizontalposition=LineCut.value()

            self.lineEdit_vCutPos.setText(formatNum(self.verticalposition))
            self.lineEdit_hCutPos.setText(formatNum(self.horizontalposition))
            self.MoveLineCut()
            self.updateLineCutPlot()
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def MoveLineCut(self):
        try:
            self.vLine.setValue(float(self.verticalposition))
            self.hLine.setValue(float(self.horizontalposition))
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def clearLinecutPlots(self):
        self.XZPlot.clear()
        self.YZPlot.clear()

    def updateLineCutPlot(self):
        try:
            self.clearLinecutPlots()
            xMin, xMax = self.plotParamsDict['xMin'] - self.plotParamsDict['xscale'] / 2, self.plotParamsDict['xMax'] + self.plotParamsDict['xscale'] / 2
            yMin, yMax = self.plotParamsDict['yMin'] - self.plotParamsDict['yscale'] / 2, self.plotParamsDict['yMax'] + self.plotParamsDict['yscale'] / 2

            if self.horizontalposition > yMax or self.horizontalposition < yMin:
                self.XZPlot.clear()
            else:
                yindex = int(round(abs((self.horizontalposition - self.plotParamsDict['yMin'])) / self.plotParamsDict['yscale']))
                self.LineCutXZXVals = np.linspace(self.plotParamsDict['xMin'], self.plotParamsDict['xMax'], num = self.plotParamsDict['xPoints'])
                self.LineCutXZYVals = self.PlotData[:,yindex]
                self.XZPlot.plot(x = self.LineCutXZXVals, y = self.LineCutXZYVals, pen = 0.5)

            if self.verticalposition > xMax or self.verticalposition < xMin:
                self.YZPlot.clear()
            else:
                xindex = int(round(abs((self.verticalposition - self.plotParamsDict['xMin'])) / self.plotParamsDict['xscale']))
                self.LineCutYZXVals = self.PlotData[xindex]
                self.LineCutYZYVals = np.linspace(self.plotParamsDict['yMin'], self.plotParamsDict['yMax'], num = self.plotParamsDict['yPoints'])
                self.YZPlot.plot(x = self.LineCutYZXVals, y = self.LineCutYZYVals, pen = 0.5)
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for subtracting backgrounds from 2D data"""

    def subtractOverallAvg(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Average')
        self.updatePlotterStatus("Subtracted Overall Average")
        self.plotData()

    def subtractPlane(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Plane')
        self.updatePlotterStatus("Subtracted Overall Plane Fit")
        self.plotData()

    def subtractOverallQuad(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Image Quadratic')
        self.updatePlotterStatus("Subtracted Overall Quadratic Fit")
        self.plotData()

    def subtractXAvg(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Average')
        self.updatePlotterStatus("Subtracted Line Average in X")
        self.plotData()

    def subtractYAvg(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Average').T
        self.updatePlotterStatus("Subtracted Line Average in Y")
        self.plotData()

    def subtractXLinear(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Linear')
        self.updatePlotterStatus("Subtracted Linear Fit in X")
        self.plotData()

    def subtractYLinear(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Linear').T
        self.updatePlotterStatus("Subtracted Linear Fit in Y")
        self.plotData()

    def subtractXQuad(self):
        self.PlotData = processImageData(self.PlotData, 'Subtract Line Quadratic')
        self.updatePlotterStatus("Subtracted Quadratic Fit in X")
        self.plotData()

    def subtractYQuad(self):
        self.PlotData = processImageData(self.PlotData.T, 'Subtract Line Quadratic').T
        self.updatePlotterStatus("Subtracted Quadratic Fit in Y")
        self.plotData()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for saving data as a matlab file"""

    def matPlot(self):
        if (not self.PlotData is None):
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            print(fold)
            if fold:
                self.genMatFile(fold)

    def genMatFile(self, fold):
        xVals = np.linspace(self.plotParamsDict['xMin'], self.plotParamsDict['xMax'], int(self.plotParamsDict['xPoints']))
        yVals = np.linspace(self.plotParamsDict['yMin'], self.plotParamsDict['yMax'], int(self.plotParamsDict['yPoints']))

        xInd = np.linspace(0, self.plotParamsDict['xPoints'] - 1, int(self.plotParamsDict['xPoints']))
        yInd = np.linspace(0, self.plotParamsDict['yPoints'] - 1, int(self.plotParamsDict['yPoints']))

        zX = np.ones([1,int(self.plotParamsDict['yPoints'])])
        zY = np.ones([1,int(self.plotParamsDict['xPoints'])])
        zXI = np.ones([1,int(self.plotParamsDict['yPoints'])])
        zYI = np.ones([1,int(self.plotParamsDict['xPoints'])])

        X, Y,  XI, YI = np.outer(xVals, zX), np.outer(zY, yVals), np.outer(xInd, zXI), np.outer(zYI, yInd)
        XX, YY, XXI, YYI, ZZ = X.flatten(), Y.flatten(), XI.flatten(), YI.flatten(), self.PlotData.flatten()
        matData = np.transpose(np.vstack((XXI, YYI, XX, YY, ZZ)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold ,{savename:matData})

    def matLinePloth(self):
        if (not self.PlotData is None):
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genLineMatFileh(fold)

    def genLineMatFileh(self, fold):
        XZyData = np.asarray(self.LineCutXZYVals)
        XZxData = np.asarray(self.LineCutXZXVals)

        xData, yData = XZxData, XZyData ###This part need to be modified

        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold, {savename:matData})
        matData = None

    def matLinePlotv(self):
        if (not self.PlotData is None):
            fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
            if fold:
                self.genLineMatFilev(fold)

    def genLineMatFilev(self, fold):
        YZyData = np.asarray(self.LineCutYZYVals)
        YZxData = np.asarray(self.LineCutYZXVals)

        xData, yData = YZxData, YZyData ###This part need to be modified

        matData = np.transpose(np.vstack((xData, yData)))
        savename = fold.split("/")[-1].split('.mat')[0]
        sio.savemat(fold, {savename:matData})
        matData = None

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for despiking"""

    @inlineCallbacks
    def despikeData(self):
        #Despike function
        #Algorithm loops through the 2D dataset along the direction of the sweep looking for individual
        #data points that are, due to noise or measurement errors, signficantly greater than their surrounding
        #values. The ith point is compared to the mean/stdev of the i-n to i+n ajacent points. If too large,
        #then the datapoint is set to the average.
        adjPnts = self.despikeSettingsDict['adjacentPoints']
        numSig = self.despikeSettingsDict['numSigma']
        xpnts = self.plotParamsDict['xPoints']
        ypnts = self.plotParamsDict['yPoints']
        sweepDir = self.plotParamsDict['sweepDir']

        status = "Start despiking algorithm with parameters: " + str(adjPnts) + ' , ' + str(numSig)
        self.updatePlotterStatus(status)

        number = 0 #Number of datapoints removed from algorithm
        #Loop through all the points in the 2D dataset
        t0 = time.clock() #Keep track of the time where the despiking algorithm started
        for i in range(xpnts):
            for j in range(ypnts):

                #First just check if the ith point is between the i-1 and i+1 point. If true, we can
                #avoid the more computationally expensive check of calculating mean / stdev
                data_i = self.PlotData[i][j] #ith point
                skipPoint = False
                if sweepDir == 'x' and i > 0 and i < (xpnts - 1):
                    data_im1 = self.PlotData[i-1][j] #i minus 1 along x axis
                    data_ip1 = self.PlotData[i+1][j] #i plus 1 along x axis
                    skipPoint = (data_im1 >= data_i >= data_ip1) or (data_im1 <= data_i <= data_ip1)
                elif sweepDir== 'y' and j < 0 and j > (ypnts - 1):
                    data_im1 = self.PlotData[i][j-1] #i minus 1 along y axis
                    data_ip1 = self.PlotData[i][j+1] #i plus 1 along y axis
                    skipPoint = (data_im1 >= data_i >= data_ip1) or (data_im1 <= data_i <= data_ip1)

                #Proceed if data is not within range of adjacent two points, calculate the means / stdev
                if not skipPoint:
                    avg, std = self.getAdjacentPointStatistics(i, j, adjPnts, xpnts, ypnts, sweepDir)
                     #If the point is above numSig* std above the mean of the adjacent points
                    if abs(self.PlotData[i][j] - avg) > numSig * std:
                        number += 1 #Increment the number of datapoints flattened
                        self.PlotData[i][j] = self.flattenPoint(i, j, xpnts, ypnts, sweepDir) #Linearly extrapolate a new value from nearest values

                #if more than 30ms have passed since the algorithm has been running
                #The shorter this time, the smoother the rest of the GUI runs, but the slower the algorithm runs.
                if time.clock() - t0 > 0.03:
                    #Update the plotter status
                    statusUpdate = "Despiking point: " + str(i) + " " + str(j) + "."
                    self.updatePlotterStatus(statusUpdate)

                    yield self.parent.sleep(0.001) #Wait 1ms to allow rest of the GUI to update
                    t0 = time.clock() #Reset the zero time

        self.plotData()
        statusUpdate = "Flattened " + str(number) + " datapoints."
        self.updatePlotterStatus(statusUpdate)

    def getAdjacentPointStatistics(self, x, y, adjPnts, xpnts, ypnts, sweepDir):
        #Find the mean and stdev of the data adjacent to the points in the data array indexed by (x,y)
        if sweepDir == 'x':
            if x >= adjPnts and xpnts - 1 - x >= adjPnts: #If adjacent points can be sampled symmetrically around x, do so
                data = [item[y] for item in self.PlotData][x - adjPnts:x + adjPnts +1] #This gives a list of 2*adjPnts + the original point
                data = data.tolist()
                del data[adjPnts] #Removes the (x,y) point from the list
            elif x < adjPnts: #If enough datapoints for indices < x don't exist for symmetric sampling
                data = [item[y] for item in self.PlotData][: 2*adjPnts + 1] #Grab the first 2*adjPnts + 1 pnts
                data = data.tolist()
                del data[x] #Remove the (x,y) point
            elif xpnts - 1 - x  < adjPnts: #If enough datapoints for indices > x don't exist for symmetric sampling
                data = [item[y] for item in self.PlotData][-(2*adjPnts + 1):] #Grab the last 2*adjPnts + 1 pnts
                data = data.tolist()
                del data[(x - xpnts - 1)] #Remove the (x,y) point
        elif sweepDir == 'y':
            #Do the same thing in the y direction
            if y >= adjPnts and ypnts - 1 - y >= adjPnts:
                data = self.PlotData[x][y - adjPnts : y + adjPnts + 1]
                data = data.tolist()
                del data[adjPnts]
            elif y < adjPnts:
                data = self.PlotData[x][: 2*adjPnts + 1]
                data = data.tolist()
                del data[y]
            elif ypnts - 1 - y < adjPnts:
                data = self.PlotData[x][-(2*adjPnts + 1):]
                data = data.tolist()
                del data[(y - ypnts - 1)]
        #Return the mean and std of the data
        return np.mean(data), np.std(data)

    def flattenPoint(self, x, y, xpnts, ypnts, sweepDir):
        #Do nearest neighbor linear extrapolation
        if sweepDir == 'x':
            if x == 0: #If it's the first point, extrapolate from 2nd and 3rd point
                value = 2*self.PlotData[x+1][y] - self.PlotData[x+2][y]
            elif x == xpnts - 1: #If it's the last point, extrapolate from the points before it
                value = 2*self.PlotData[x-1][y] - self.PlotData[x-2][y]
            else: #If points has adjacent points, take their average
                value = (self.PlotData[x-1][y] + self.PlotData[x+1][y]) / 2
        if sweepDir == 'y':
            #Do the same for the y direction
            if y == 0:
                value = 2*self.PlotData[x][y+1] - self.PlotData[x][y+2]
            elif y == ypnts- 1:
                value = 2*self.PlotData[x][y-1] - self.PlotData[x][y-2]
            else:
                value = (self.PlotData[x][y-1] + self.PlotData[x][y+1]) / 2
        return value

    def openDespikeSettings(self):
        '''
        Opens the despike settings window, giving it the settings dictionary.
        If changes are accepted, then the settings are updated with the new values.
        '''
        despikeSet = despikeSettingsWindow(self.despikeSettingsDict.copy(), parent = self)
        if despikeSet.exec_():
            self.despikeSettingsDict = despikeSet.getValues()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for taking derivatives of the data"""

    def xDeriv(self):
        xVals = np.linspace(self.plotParamsDict['xMin'], self.plotParamsDict['xMax'], self.plotParamsDict['xPoints'])
        delta = (self.plotParamsDict['xMax'] - self.plotParamsDict['xMin']) / (self.plotParamsDict['xPoints']-1)

        for i in range(0, self.PlotData.shape[1]):
            self.PlotData[:, i] = deriv(self.PlotData[:,i], xVals, self.derivSettingsDict['adjPnts'], delta, self.derivSettingsDict['fitOrder'], self.derivSettingsDict['edgePnts'])

        self.plotData() #Plot the derivative data
        self.updatePlotterStatus("Plotted gradient along x-axis.")

    def yDeriv(self):
        yVals = np.linspace(self.plotParamsDict['yMin'], self.plotParamsDict['yMax'], num = self.plotParamsDict['yPoints'])
        delta = (self.plotParamsDict['yMax'] - self.plotParamsDict['yMin']) / (self.plotParamsDict['yPoints']-1)

        for i in range(0, self.PlotData.shape[0]):
            self.PlotData[i, :] = deriv(self.PlotData[i,:], yVals, self.derivSettingsDict['adjPnts'], delta, self.derivSettingsDict['fitOrder'], self.derivSettingsDict['edgePnts'])

        self.plotData()
        self.updatePlotterStatus("Plotted gradient along y-axis.")

    def openDerivSettings(self):
        '''
        Opens the derivative settings window, giving it the settings dictionary.
        If changes are accepted, then the settings are updated with the new values.
        '''
        derivSet = derivSettingsWindow(self.derivSettingsDict.copy(), parent = self)
        if derivSet.exec_():
            self.derivSettingsDict = derivSet.getValues()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for SQUID sensitivity calculations"""

    def computeSQUIDSensitivity(self):
        #This function assumes the dataset is a standard dataset from the nSOT Characterizer modules
        #and has hardcoded which axes to use.
        #0 - magnetic field index , 1 - voltage bias index, 2 - field, 3 - field index, 4 - SSAA output, 5 - noise output

        #First, get the data of the SQUID response and the noise
        squidData = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])
        noiseData = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])
        for datum in self.data:
            squidData[int(datum[0]), int(datum[1])] = datum[4] #This should be the SSAA output
            noiseData[int(datum[0]), int(datum[1])] = datum[5] #This should be the noise box output

        #Take the x derivative to find the slope wrt to the field axis
        xVals = np.linspace(self.plotParamsDict['xMin'], self.plotParamsDict['xMax'], self.plotParamsDict['xPoints'])
        delta = (self.plotParamsDict['xMax'] - self.plotParamsDict['xMin']) / (self.plotParamsDict['xPoints']-1)
        for i in range(0, squidData.shape[1]):
            squidData[:, i] = deriv(squidData[:,i], xVals, self.derivSettingsDict['adjPnts'], delta, self.derivSettingsDict['fitOrder'], self.derivSettingsDict['edgePnts'])

        #Conversion of noise data from volts to volts / rtHz using the gain and bandwidth of the noise measurement box
        ratio = self.sensSettingsDict['gain'] * sqrt(self.sensSettingsDict['bandwidth'])
        self.PlotData = ratio * squidData / noiseData #Take the elementwise division of the x derivative to the noise

        self.plotData()
        self.updatePlotterStatus('Sensitivity plotted (rtHz/T)')

    def openSensitivitySettings(self):
        sensitivitySet = sensitivitySettingsWindow(self.sensSettingsDict.copy(), parent = self)
        if sensitivitySet.exec_():
            self.sensSettingsDict = sensitivitySet.getValues()

    def plotOptimalSQUIDParameters(self):
        #Function assumes that self.PlotData is the result from self.computeSQUIDSensitivity

        #These need to be oject variables, otherwise they will close randomly when python garbage collector gets to them
        self.OptimalSensitivity = Plot1D('Optimal Sensitivity', self)
        self.OptimalBias = Plot1D('Optimal Bias', self)

        fieldPnts = np.linspace(self.plotParamsDict['xMin'], self.plotParamsDict['xMax'], self.plotParamsDict['xPoints']).tolist()
        optSensitivity = []
        optBias = []

        for i in range(self.plotParamsDict['xPoints']):
            sensMax = np.amax(self.PlotData[i])
            sensMin = np.amin(self.PlotData[i])
            indexMax = np.argmax(self.PlotData[i])
            indexMin = np.argmin(self.PlotData[i])

            if abs(sensMax) < abs(sensMin):
                optSensitivity.append(abs(sensMin))
                optBias.append(indexMin * self.plotParamsDict['yscale'] + self.plotParamsDict['yMin'])
            elif abs(sensMax) >= abs(sensMin):
                optSensitivity.append(abs(sensMax))
                optBias.append(indexMax * self.plotParamsDict['yscale'] + self.plotParamsDict['yMin'])

        self.OptimalSensitivity.plotData(fieldPnts, optSensitivity)
        self.OptimalSensitivity.setLinecutMinPosition()
        self.OptimalSensitivity.moveDefault()
        self.OptimalSensitivity.raise_()
        self.OptimalSensitivity.show()

        self.OptimalBias.plotData(fieldPnts, optBias)
        self.OptimalBias.setLinecutMinPosition()
        self.OptimalBias.moveDefault()
        self.OptimalBias.raise_()
        self.OptimalBias.show()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for quickly extracting TF oscillation info"""

    def extractTFOscillationInfo(self):
        dc_index = self.fitTFSettingsDict['dc data'] + len(self.dataInfoDict['indVars'])
        tfx_index = self.fitTFSettingsDict['tf data x'] + len(self.dataInfoDict['indVars'])
        tfy_index = self.fitTFSettingsDict['tf data y'] + len(self.dataInfoDict['indVars'])

        #First, get the DC and TF scan data
        dc_data = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])
        self.tf_data_x = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])
        self.tf_data_y = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])

        for datum in self.data:
            dc_data[int(datum[0]), int(datum[1])] = datum[dc_index] #This should be the DC data
            self.tf_data_x[int(datum[0]), int(datum[1])] = datum[tfx_index] #This should be the TF data
            self.tf_data_y[int(datum[0]), int(datum[1])] = datum[tfy_index] #This should be the TF data

        #Take the x and y derivative of the DC data
        xVals = np.linspace(self.plotParamsDict['xMin'], self.plotParamsDict['xMax'], self.plotParamsDict['xPoints'])
        xdelta = (self.plotParamsDict['xMax'] - self.plotParamsDict['xMin']) / (self.plotParamsDict['xPoints']-1)
        self.x_deriv = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])

        yVals = np.linspace(self.plotParamsDict['yMin'], self.plotParamsDict['yMax'], self.plotParamsDict['yPoints'])
        ydelta = (self.plotParamsDict['yMax'] - self.plotParamsDict['yMin']) / (self.plotParamsDict['yPoints']-1)
        self.y_deriv = np.zeros([int(self.plotParamsDict['xPoints']), int(self.plotParamsDict['yPoints'])])

        for i in range(0, self.x_deriv.shape[1]):
            self.x_deriv[:, i] = deriv(dc_data[:, i], xVals, self.derivSettingsDict['adjPnts'], xdelta, self.derivSettingsDict['fitOrder'], self.derivSettingsDict['edgePnts'])

        for i in range(0, self.y_deriv.shape[0]):
            self.y_deriv[i, :] = deriv(dc_data[i, :], yVals, self.derivSettingsDict['adjPnts'], ydelta, self.derivSettingsDict['fitOrder'], self.derivSettingsDict['edgePnts'])

        #Flatten the datasets so that the fitting function runs properly
        self.tf_data_x.flatten()
        self.tf_data_y.flatten()
        self.x_deriv.flatten()
        self.y_deriv.flatten()

        #First perform a phase rotation on the TF X and Y data
        self.tf_data_x = self.tf_data_x - np.mean(self.tf_data_x) #Subtract the mean of the dataset to account for measurement offsets
        self.tf_data_y = self.tf_data_y - np.mean(self.tf_data_y) #Subtract the mean of the dataset to account for measurement offsets
        self.arctan = np.arctan2(self.tf_data_y, self.tf_data_x)

        p0 = np.mean(self.arctan) #Guess the mean angle as the initial fit
        fitTheta = optimize.minimize(self.thetaFunction, p0, method = self.fitTFSettingsDict['method'])

        theta = np.degrees(np.arctan(fitTheta.x))
        self.tf_data = np.sqrt(np.square(self.tf_data_x) + np.square(self.tf_data_y))*(np.cos(self.arctan - theta))

        fit = optimize.minimize(self.tfFittingFunction, [1.0, 1.0, 0], method = self.fitTFSettingsDict['method'])
        success = fit.success
        if success:
            fitparameter = fit.x
            amp = sqrt(fitparameter[0] ** 2 + fitparameter[1] ** 2) * 1e-6 / self.fitTFSettingsDict['gain']
            theta = 180.0 / pi * atan2(fitparameter[0], fitparameter[1])
            self.updatePlotterStatus('Amp = ' + formatNum(amp, 1) + 'm. Angle = ' + formatNum(theta, 1) + " degrees.")

            self.PlotData = fitparameter[0] * self.x_deriv + fitparameter[1] * self.y_deriv + fitparameter[2]
            self.plotData()
        else:
            self.updatePlotterStatus('Failure: ' + str(fit.message))

    def tfFittingFunction(self, weight):
        difference = self.tf_data - weight[0] * self.x_deriv - weight[1] * self.y_deriv - weight[2]
        square = np.sum(np.square(difference))
        return square

    def thetaFunction(self, para):
        return np.sum(np.square(np.sqrt(np.square(self.tf_data_x) + np.square(self.tf_data_y))*(np.sin(self.arctan - para))))

    def openFitTFSettings(self):
        '''
        Opens the fit TF settings window, giving it the settings dictionary.
        If changes are accepted, then the settings are updated with the new values.
        '''
        fitTFSettings = fitTFSettingsWindow(self.dataInfoDict.copy(), self.fitTFSettingsDict.copy(), parent = self)
        if fitTFSettings.exec_():
            self.fitTFSettingsDict = fitTFSettings.getValues()

    def closeEvent(self, e):
        self.plotClosed.emit(self)
        self.close()

class Plot1D(QtGui.QMainWindow, Ui_Plotter1D):
    def __init__(self, name, parent = None ):
        super(Plot1D, self).__init__()
        self.setupUi(self)

        self.name = name

        self.label_name.setText(self.name)
        self.setWindowTitle(self.name)

        self.parent = parent

        self.XData = None
        self.YData = None

        self.unitsDict = {
            'Optimal Bias': 'V',
            'Optimal Sensitivity': '\u221a' + 'Hz' + '/T',
            'Optimal Noise': 'T/' + '\u221a' + 'Hz'
        }

        self.lineVisible = False
        self.lineEdit_LinecutPosition.editingFinished.connect(self.setLinecutPosition)

        self.pushButton_ShowLinecut.clicked.connect(self.toggleLinecut)
        self.pushButton_SaveMatlab.clicked.connect(self.saveDataMatlab)

        if self.name == 'Optimal Sensitivity':
            self.pushButton_Switch.clicked.connect(self.switchData)
        else:
            self.pushButton_Switch.hide()

        self.lineObject = pg.InfiniteLine(pos = 0, angle = 90, movable = True)
        self.lineObject.sigPositionChangeFinished.connect(self.updateLinecutValue)

        self.plot1D = pg.PlotWidget()
        self.setupPlot()

    def switchData(self):
        self.YData = 1.0 / np.asarray(self.YData)

        if self.name == 'Optimal Sensitivity':
            self.name = 'Optimal Noise'
        elif self.name == 'Optimal Noise':
            self.name = 'Optimal Sensitivity'

        self.label_name.setText(self.name)
        self.setWindowTitle(self.name)

        self.refreshPlot()

    def setLinecutMinPosition(self):
        self.position = np.amin(self.XData)
        self.lineObject.setValue(self.position)
        self.lineEdit_LinecutPosition.setText(formatNum(self.position))

    def updateLinecutValue(self):
        self.position = self.lineObject.value()
        self.lineEdit_LinecutPosition.setText(formatNum(self.position))

        index = int(round((self.position - self.xmin) / self.xscale))
        if index < 0:
            index = 0
        elif index > len(self.YData) - 1:
            index = len(self.YData) - 1

        self.lineEdit_LinecutValue.setText(formatNum(self.YData[index]))

    def setLinecutPosition(self):
        try:
            val = readNum(str(self.lineEdit_LinecutPosition.text()))
            if isinstance(val, float):
                self.position = val
            self.lineObject.setValue(float(self.position))
            self.updateLinecutValue()
        except Exception as inst:
                print('Following error was thrown: ', inst)
                print('Error thrown on line: ', sys.exc_traceback.tb_lineno)

    def setupPlot(self):
        self.plot1D.setGeometry(QtCore.QRect(0, 0, 635, 200))
        self.plot1D.showAxis('right', show = True)
        self.plot1D.showAxis('top', show = True)
        self.layout_mainPlot.addWidget(self.plot1D)
        self.setPlotLabels()

    def setPlotLabels(self):
        self.plot1D.setLabel('bottom', 'Magnetic Field', units = 'T')
        self.plot1D.setLabel('left', self.name, units = self.unitsDict[self.name])

    def plotData(self, dataX, dataY):
        self.XData = dataX
        self.YData = dataY
        self.xmin = np.amin(self.XData)
        self.xscale = self.XData[1] - self.XData[0]

        if self.name == 'Optimal Bias':
            color = 'r'
        elif self.name == 'Optimal Sensitivity' or self.name == 'Optimal Noise':
            color = 'b'
        else:
            color = 'g'

        self.plot1D.plot(x = dataX, y = dataY, pen = color)

    def toggleLinecut(self):
        self.lineVisible = not self.lineVisible
        if self.lineVisible:
            self.plot1D.addItem(self.lineObject)
        elif not self.lineVisible:
            self.plot1D.removeItem(self.lineObject)

    def refreshPlot(self):
        self.plot1D.clear()
        self.plotData(self.XData, self.YData)
        self.setPlotLabels()
        self.updateLinecutValue()

    def saveDataMatlab(self):
        fold = str(QtGui.QFileDialog.getSaveFileName(self, directory = os.getcwd(), filter = "MATLAB Data (*.mat)"))
        if fold:
            XData = np.asarray(self.XData)
            YData = np.asarray(self.YData)

            matData = np.transpose(np.vstack((XData, YData)))
            savename = fold.split("/")[-1].split('.mat')[0]
            sio.savemat(fold,{savename:matData})
            matData = None

    def moveDefault(self):
        parentx, parenty = self.parent.mapToGlobal(QtCore.QPoint(0,0)).x(), self.parent.mapToGlobal(QtCore.QPoint(0,0)).y()
        parentwidth = self.parent.width()
        Offset = 400
        if self.name == 'Optimal Sensitivity':
            self.move(parentx + parentwidth/2, parenty)
        elif self.name == 'Optimal Bias':
            self.move(parentx + parentwidth/2, parenty + Offset)

class dataInfoWindow(QtGui.QDialog, Ui_DataInfo):
    def __init__(self, dataInfo, plotParams, parent = None):
        super(dataInfoWindow, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)

        self.dataInfo = dataInfo
        self.plotParams = plotParams

        self.label_DataSetName.setText(self.dataInfo['file']) #Name
        self.lineEdit_Title.setText(self.dataInfo['title']) #Title
        self.lineEdit_DataType.setText(self.dataInfo['dataType']) #DataType

        #Populate trace info
        if self.dataInfo['traceFlag'] is None:
            self.lineEdit_TraceInfo.setText('No')
        else:
            self.lineEdit_TraceInfo.setText('Yes')

        #Populate number of index (independent) variables
        if self.dataInfo['numIndexVars'] > 0:
            self.lineEdit_Numberofindex.setText(str(self.dataInfo['numIndexVars'] ))
        else:
            self.lineEdit_Numberofindex.setText("No index")

        #Populate independent/dependent variables
        for i in self.dataInfo['indVars']:
            self.listWidget_IndependentVariables.addItem(i)

        for i in self.dataInfo['depVars']:
            self.listWidget_DependentVariables.addItem(i)

        #Populate parameters
        params = self.dataInfo['parameters']
        for key in params:
            item = key + " : " + str(params[key])
            self.listWidget_parameters.addItem(item)

        #Format and populate comments UI
        comments = self.dataInfo['comments']
        if str(comments) == '[]':
            s = "None"
        else:
            s = ""
            for com in comments:
                s += str(com[2]) + "\n\n"

        self.textEdit_CurrentComments.setText(s)

        #PlotDetails
        #X,Y dimension
        self.lineEdit_XPoints.setText(str(self.plotParams['xPoints']))
        self.lineEdit_YPoints.setText(str(self.plotParams['yPoints']))

        #Sweeping direction
        if self.plotParams['sweepDir'] != '':
            self.lineEdit_SweepingAxis.setText(self.plotParams['sweepDir'] + "-axis")
        else:
            self.lineEdit_SweepingAxis.setText("none")

class despikeSettingsWindow(QtGui.QDialog, Ui_DespikesSetting):
    def __init__(self, settings, parent = None):
        super(despikeSettingsWindow, self).__init__(parent)
        self.setupUi(self)

        self.settings = settings

        self.lineEdit_AdjacentPoints.setText(formatNum(self.settings['adjacentPoints']))
        self.lineEdit_NumberofSigma.setText(formatNum(self.settings['numSigma']))

        self.lineEdit_AdjacentPoints.editingFinished.connect(lambda: self.updateParameter('adjacentPoints', self.lineEdit_AdjacentPoints))
        self.lineEdit_NumberofSigma.editingFinished.connect(lambda: self.updateParameter('numSigma', self.lineEdit_NumberofSigma))

    def updateParameter(self, key, lineEdit):
        val = readNum(str(lineEdit.text()))
        if isinstance(val, float):
                self.settings[key] = val
        lineEdit.setText(formatNum(self.settings[key], 6))

    def closeEvent(self, e):
        self.accept()

    def getValues(self):
        return self.settings

class derivSettingsWindow(QtGui.QDialog, Ui_DerivSet):
    def __init__(self, settings, parent = None):
        super(derivSettingsWindow, self).__init__(parent)

        self.setupUi(self)
        self.settings = settings

        self.lineEdit_numSymPoints.setText(formatNum(self.settings['adjPnts']))
        self.lineEdit_numEdgePoints.setText(formatNum(self.settings['edgePnts']))
        self.lineEdit_polyOrder.setText(formatNum(self.settings['fitOrder']))

        self.lineEdit_numSymPoints.editingFinished.connect(lambda: self.updateParameter('adjPnts', self.lineEdit_numSymPoints))
        self.lineEdit_numEdgePoints.editingFinished.connect(lambda: self.updateParameter('edgePnts', self.lineEdit_numEdgePoints))
        self.lineEdit_polyOrder.editingFinished.connect(lambda: self.updateParameter('fitOrder', self.lineEdit_polyOrder))

        self.pushButton_ok.clicked.connect(self.accept)
        self.pushButton_cancel.clicked.connect(self.close)

    def updateParameter(self, key, lineEdit):
        val = readNum(str(lineEdit.text()))
        if isinstance(val, float):
                self.settings[key] = val
        lineEdit.setText(formatNum(self.settings[key], 6))

    def getValues(self):
        return self.settings

class sensitivitySettingsWindow(QtGui.QDialog, Ui_SensitivitySettings):
    def __init__(self, sensSettingsDict, parent = None):
        super(sensitivitySettingsWindow, self).__init__(parent)

        self.settings = sensSettingsDict
        self.setupUi(self)

        self.lineEdit_gain.setText(formatNum(self.settings['gain']))
        self.lineEdit_bandwidth.setText(formatNum(self.settings['bandwidth']))

        self.lineEdit_gain.editingFinished.connect(lambda: self.updateParameter('gain', self.lineEdit_gain))
        self.lineEdit_bandwidth.editingFinished.connect(lambda: self.updateParameter('bandwidth', self.lineEdit_bandwidth))

        self.pushButton_ok.clicked.connect(self.accept)
        self.pushButton_cancel.clicked.connect(self.close)

    def updateParameter(self, key, lineEdit):
        val = readNum(str(lineEdit.text()))
        if isinstance(val, float):
                self.settings[key] = val
        lineEdit.setText(formatNum(self.settings[key], 6))

    def getValues(self):
        return self.settings

class fitTFSettingsWindow(QtGui.QDialog, Ui_FitTFSettings):
    def __init__(self, datainfo, settings, parent):
        super(fitTFSettingsWindow, self).__init__(parent)

        self.settings = settings
        self.dataInfo = datainfo

        self.setupUi(self)

        for i in self.dataInfo['depVars']:
            self.comboBox_dcData.addItem(i)
            self.comboBox_acDataX.addItem(i)
            self.comboBox_acDataY.addItem(i)

        self.comboBox_dcData.setCurrentIndex(self.settings['dc data'])
        self.comboBox_acDataX.setCurrentIndex(self.settings['tf data x'])
        self.comboBox_acDataY.setCurrentIndex(self.settings['tf data y'])
        self.comboBox_Method.setCurrentIndex(self.comboBox_Method.findText(self.settings['method']))

        self.comboBox_dcData.currentIndexChanged.connect(self.setDCDataIndex)
        self.comboBox_acDataX.currentIndexChanged.connect(self.setTFXDataIndex)
        self.comboBox_acDataY.currentIndexChanged.connect(self.setTFYDataIndex)
        self.comboBox_Method.currentIndexChanged.connect(self.setFittingMethod)

        self.lineEdit_Gain.setText(formatNum(self.settings['gain']))
        self.lineEdit_Gain.editingFinished.connect(self.setGain)

        self.pushButton_Ok.clicked.connect(self.accept)

    def setDCDataIndex(self):
        self.settings['dc data'] = self.comboBox_dcData.currentIndex()

    def setTFXDataIndex(self):
        self.settings['tf data x'] = self.comboBox_acDataX.currentIndex()

    def setTFYDataIndex(self):
        self.settings['tf data y'] = self.comboBox_acDataY.currentIndex()

    def setFittingMethod(self):
        self.settings['method'] = str(self.comboBox_Method.currentText())

    def setGain(self):
        val = readNum(str(self.lineEdit_Gain.text()))
        if isinstance(val, float):
                self.settings['gain'] = val
        self.lineEdit_Gain.setText(formatNum(self.settings['gain'], 6))

    def getValues(self):
        return self.settings

if __name__ == "__main__":
    app = QtGui.QApplication([])
    from qtreactor import pyqt4reactor
    pyqt4reactor.install()
    from twisted.internet import reactor
    window = Plotter(reactor)
    window.show()
    reactor.run()
