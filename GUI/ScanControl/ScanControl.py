import sys
from PyQt5 import QtGui, QtWidgets, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
import numpy as np
import pyqtgraph as pg
import time
from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView, printErrorInfo, saveDataToSessionFolder

path = sys.path[0] + r"\ScanControl"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\ScanControlWindow.ui")
Ui_ServerList, QtBaseClass = uic.loadUiType(path + r"\requiredServers.ui")



'''
TODO:
Check whether or not scanning works with different x and y calibration
make tilt compatible with stepwise constant height approach - should be done
'''

class Window(QtWidgets.QMainWindow, ScanControlWindowUI):
    updateScanningStatus = QtCore.pyqtSignal(bool)

    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)

        self.aspectLocked = True
        self.FrameLocked = True
        self.DataLocked = True
        self.scanSmooth = True
        self.scanCoordinates = False
        self.dataProcessing = 'Raw'
        self.dataPostProcessing = 'Raw'

        self.reactor = reactor
        self.setupUi(self)

        #initialize scanning area and plotted data information
        #Lower left corner of the square (assuming unrotated)
        self.x = -15e-6
        self.y = -15e-6
        #Center of the square
        self.Xc = 0.0
        self.Yc = 0.0
        #Height and width of scanning square
        self.H = 30e-6
        self.W = 30e-6
        #Aspect ratio defined as H/W
        self.SquareAspectRatio = 1.0
        #Angle of scanning square in degrees
        self.angle = 0.0

        #Keep track of plotted data location / angle so that we can also plot it in scan coordinates
        self.currAngle = 0.0
        self.currXc = 0.0
        self.currYc = 0.0
        self.currH = 3e-5
        self.currW = 3e-5
        self.curr_x = -1.5e-5
        self.curr_y = -1.5e-5
        self.currLine = -1

        #Number of pixels taken in each direction, and the ratio of pixels to lines
        self.pixels = 256
        self.lines = 256
        self.PixelsAspectRatio = 1.0

        #Measurement information
        self.linearSpeed = 2e-6
        self.delayTime = 1e-2
        self.lineTime = 15

        #Initial attocube position in volts as controlled by the scanning DAC ADC
        self.Atto_X_Voltage = 0.0
        self.Atto_Y_Voltage = 0.0
        self.Atto_Z_Voltage = 0.0
        # print("init", self.Atto_Z_Voltage)

        #When moving in constant height mode, all movement will happen on a plane defined by tilts in the x and y
        #direction, as well as the point on the plane where we approached for constant height. In meters.
        #As above, this is only the fraction contributed by the scanning DAC. The Zurich also provides motion
        #in the z direction
        self.z_center = 0
        self.x_center = 0
        self.y_center = 0

        #Tilt in x and y direction in radians
        self.x_tilt = 0
        self.y_tilt = 0

        #Position to manually move to if push_Set is pushed. In meters
        self.Xset = 0
        self.Yset = 0

        #Flag to indicate whether or not we're scanning
        self.scanning = False

        #Name of the file to be saved
        self.fileName = 'unnamed'

        #Initialize the Scan Mode
        self.scanMode = 'Constant Height'
        self.FeedbackReady = False
        self.ConstantHeightReady = False

        #0 corresponds to no blinking, 1 before trace, 2 before trace and retrace
        self.blinkMode = 0

        #Channel 0 corresponds to height, and 1 to input 1, and 2 to input 2
        self.channel = 0

        inputDict  = {
        'Name'              : 'Input', #Name of the input
        'Conversion'        : 1,       #Conversion from volts to the units specified. Shoudl be units = volts / conversion_factor
        'Units'             : 'V',     #Units of the input
        'ADC Channel'       : 1        #ADC Channel 1 indexed
        }

        #Array of 8 dictionaires containing the information for each input
        self.inputs = [inputDict.copy(),inputDict.copy(),inputDict.copy(),inputDict.copy(),inputDict.copy(),inputDict.copy(),inputDict.copy(),inputDict.copy()]
        #Initialize dictionaries to appropriate defaults
        self.inputs[0]['Name'] = 'Z'
        self.inputs[0]['ADC Channel'] = 1
        self.inputs[0]['Units'] = 'm'
        for i in range(1,8):
            self.inputs[i]['Name'] = 'Input ' + str(i+1)
            self.inputs[i]['ADC Channel'] = i+1

        #The outputs are kept in a dictionary. Values are determined by the device select module and loaded in the connectLabRAD function
        self.outputs = {
                'z out'               : 1,         # 1 indexed DAC output that goes to constant gain on Z
                'x out'               : 2,         # 1 indexed DAC output that goes to X
                'y out'               : 3,         # 1 indexed DAC output that goes to Y
                'blink out'           : 4,         # 1 indexed DC Box output that goes to blinking
        }

        #Random number that is not real data. This lets us know when plotting which values are real data, and which can just be ignored.
        #Should be a float with magnitude less than 1, as otherwise seems to cause problems with imageView
        #A negative value is chosen because, more often than not, the data will be positive. This minimizes the risk of removing a real
        #data point from the plot.
        self.randomFill = -0.987654321

        #Specify the voltage step size for smooth scans.
        self.voltageStepSize = 300e-6

        #Set up rest of UI (must be done after initializing default values)
        self.setupAdditionalUi()
        self.setupScanningArea()
        self.moveDefault()

        #Connect the buttons to the appropriate methods
        self.push_FrameLock.clicked.connect(self.toggleFrameLock)
        self.push_DataLock.clicked.connect(self.toggleDataLock)
        self.push_autoRange.clicked.connect(self.autoRangeImageViews)
        self.push_autoLevel.clicked.connect(self.autoLevelImageViews)
        self.push_aspectLocked.clicked.connect(self.toggleAspect)
        self.push_scanCoordinates.clicked.connect(self.toggleCoordinates)
        self.push_apply2DFit.clicked.connect(self.apply2DFit)
        self.push_setView.clicked.connect(self.setView)
        self.push_Scan.clicked.connect(lambda: self.startScan())
        self.push_Abort.clicked.connect(lambda: self.abortScan())
        self.push_ZeroXY.clicked.connect(lambda: self.zeroXYPosition())
        self.push_Set.clicked.connect(lambda: self.setPosition(self.Xset, self.Yset))
        self.push_ZeroZ.clicked.connect(lambda: self.zeroZOffset())
        self.push_toggleSmooth.clicked.connect(self.toggleSmoothScan)
        self.push_ResetScan.clicked.connect(self.resetScan)

        self.pushButton_RemoveInput.clicked.connect(lambda: self.removeInput(0))
        self.pushButton_RemoveInput2.clicked.connect(lambda: self.removeInput(1))
        self.pushButton_RemoveInput3.clicked.connect(lambda: self.removeInput(2))
        self.pushButton_RemoveInput4.clicked.connect(lambda: self.removeInput(3))
        self.pushButton_RemoveInput5.clicked.connect(lambda: self.removeInput(4))
        self.pushButton_RemoveInput6.clicked.connect(lambda: self.removeInput(5))
        self.pushButton_RemoveInput7.clicked.connect(lambda: self.removeInput(6))
        self.pushButton_RemoveInput8.clicked.connect(lambda: self.removeInput(7))

        self.pushButton_addInput.clicked.connect(self.addInput)

        #Connect lineEdits
        self.lineEdit_Xc.editingFinished.connect(self.updateXc)
        self.lineEdit_Yc.editingFinished.connect(self.updateYc)
        self.lineEdit_H.editingFinished.connect(self.updateH)
        self.lineEdit_W.editingFinished.connect(self.updateW)
        self.lineEdit_Angle.editingFinished.connect(self.updateAngle)
        self.lineEdit_Pixels.editingFinished.connect(self.updatePixels)
        self.lineEdit_Lines.editingFinished.connect(self.updateLines)
        self.lineEdit_Linear.editingFinished.connect(self.updateLinearSpeed)
        self.lineEdit_FileName.editingFinished.connect(self.updateFileName)
        self.lineEdit_XTilt.editingFinished.connect(self.updateXTilt)
        self.lineEdit_YTilt.editingFinished.connect(self.updateYTilt)
        self.lineEdit_Xset.editingFinished.connect(self.updateXset)
        self.lineEdit_Yset.editingFinished.connect(self.updateYset)

        self.checkBox.toggled.connect(self.toggleROIVisibility)

        self.comboBox_Processing.activated[str].connect(self.selectProcessing)
        self.comboBox_PostProcessing.activated[str].connect(self.selectPostProcessing)
        self.comboBox_scanMode.activated[str].connect(self.updateScanMode)
        self.comboBox_Channel.currentIndexChanged.connect(self.selectChannel)
        self.comboBox_blinkMode.currentIndexChanged.connect(self.setBlinkMode)

        self.comboBox_Input1.currentIndexChanged.connect(lambda: self.setInputChannel(0,self.comboBox_Input1))
        self.comboBox_Input2.currentIndexChanged.connect(lambda: self.setInputChannel(1,self.comboBox_Input2))
        self.comboBox_Input3.currentIndexChanged.connect(lambda: self.setInputChannel(2,self.comboBox_Input3))
        self.comboBox_Input4.currentIndexChanged.connect(lambda: self.setInputChannel(3,self.comboBox_Input4))
        self.comboBox_Input5.currentIndexChanged.connect(lambda: self.setInputChannel(4,self.comboBox_Input5))
        self.comboBox_Input6.currentIndexChanged.connect(lambda: self.setInputChannel(5,self.comboBox_Input6))
        self.comboBox_Input7.currentIndexChanged.connect(lambda: self.setInputChannel(6,self.comboBox_Input7))
        self.comboBox_Input8.currentIndexChanged.connect(lambda: self.setInputChannel(7,self.comboBox_Input8))

        self.lineEdit_Input1Name.editingFinished.connect(lambda: self.setInputName(0, self.lineEdit_Input1Name))
        self.lineEdit_Input2Name.editingFinished.connect(lambda: self.setInputName(1, self.lineEdit_Input2Name))
        self.lineEdit_Input3Name.editingFinished.connect(lambda: self.setInputName(2, self.lineEdit_Input3Name))
        self.lineEdit_Input4Name.editingFinished.connect(lambda: self.setInputName(3, self.lineEdit_Input4Name))
        self.lineEdit_Input5Name.editingFinished.connect(lambda: self.setInputName(4, self.lineEdit_Input5Name))
        self.lineEdit_Input6Name.editingFinished.connect(lambda: self.setInputName(5, self.lineEdit_Input6Name))
        self.lineEdit_Input7Name.editingFinished.connect(lambda: self.setInputName(6, self.lineEdit_Input7Name))
        self.lineEdit_Input8Name.editingFinished.connect(lambda: self.setInputName(7, self.lineEdit_Input8Name))

        self.lineEdit_Input1Conversion.editingFinished.connect(lambda: self.setInputConversion(0, self.lineEdit_Input1Conversion))
        self.lineEdit_Input2Conversion.editingFinished.connect(lambda: self.setInputConversion(1, self.lineEdit_Input2Conversion))
        self.lineEdit_Input3Conversion.editingFinished.connect(lambda: self.setInputConversion(2, self.lineEdit_Input3Conversion))
        self.lineEdit_Input4Conversion.editingFinished.connect(lambda: self.setInputConversion(3, self.lineEdit_Input4Conversion))
        self.lineEdit_Input5Conversion.editingFinished.connect(lambda: self.setInputConversion(4, self.lineEdit_Input5Conversion))
        self.lineEdit_Input6Conversion.editingFinished.connect(lambda: self.setInputConversion(5, self.lineEdit_Input6Conversion))
        self.lineEdit_Input7Conversion.editingFinished.connect(lambda: self.setInputConversion(6, self.lineEdit_Input7Conversion))
        self.lineEdit_Input8Conversion.editingFinished.connect(lambda: self.setInputConversion(7, self.lineEdit_Input8Conversion))

        self.lineEdit_Input1Unit.editingFinished.connect(lambda: self.setInputUnit(0, self.lineEdit_Input1Unit))
        self.lineEdit_Input2Unit.editingFinished.connect(lambda: self.setInputUnit(1, self.lineEdit_Input2Unit))
        self.lineEdit_Input3Unit.editingFinished.connect(lambda: self.setInputUnit(2, self.lineEdit_Input3Unit))
        self.lineEdit_Input4Unit.editingFinished.connect(lambda: self.setInputUnit(3, self.lineEdit_Input4Unit))
        self.lineEdit_Input5Unit.editingFinished.connect(lambda: self.setInputUnit(4, self.lineEdit_Input5Unit))
        self.lineEdit_Input6Unit.editingFinished.connect(lambda: self.setInputUnit(5, self.lineEdit_Input6Unit))
        self.lineEdit_Input7Unit.editingFinished.connect(lambda: self.setInputUnit(6, self.lineEdit_Input7Unit))
        self.lineEdit_Input8Unit.editingFinished.connect(lambda: self.setInputUnit(7, self.lineEdit_Input8Unit))

        #ROI in trace plot
        self.ROI.sigRegionChanged.connect(self.updateROI)
        self.ROI.sigRegionChangeFinished.connect(self.moveROIs)
        #ROI in mini plot
        self.ROI2.sigRegionChanged.connect(self.updateROI2)
        self.ROI2.sigRegionChangeFinished.connect(self.moveROIs)
        #ROI in retrace plot
        self.ROI3.sigRegionChanged.connect(self.updateROI3)
        self.ROI3.sigRegionChangeFinished.connect(self.moveROIs)

        #Connect show servers list pop up
        self.push_Servers.clicked.connect(self.showServersList)

        #Initialize all the labrad connections as false and lock the interface
        self.disconnectLabRAD()

    def moveDefault(self):
        self.move(10,170)
        self.resize(0,0)

    @inlineCallbacks
    def connectLabRAD(self, equip):
        try:
            self.cxn = equip.cxn
            self.gen_dv = equip.dv

            #Create another connection for the connection to data vault to prevent
            #problems of multiple windows trying to write the data vault at the same
            #time
            from labrad.wrappers import connectAsync
            self.cxn_scan = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.cxn_blink = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = self.cxn_scan.data_vault
            curr_folder = yield self.gen_dv.cd()
            yield self.dv.cd(curr_folder)

            if "Scan DAC" in equip.servers:
                svr, ln, device_info, cnt, config = equip.servers["Scan DAC"]

                #Similarly uses that extra connection so that we can talk to the scan dac at the same time as other dacs
                self.dac = yield self.cxn_scan.dac_adc
                yield self.dac.select_device(device_info)

                self.outputs['z out'] = config['z out']
                self.outputs['x out'] = config['x out']
                self.outputs['y out'] = config['y out']
            else:
                print("'Scan DAC' not found, LabRAD connection to Scan Control Failed.")
                return

            if "Blink Device" in equip.servers:
                svr, labrad_name, device_info, cnt, config = equip.servers["Blink Device"]

                #Create a connection to the proper device for blinking
                if device_info.startswith('ad5764_dcbox'):
                    self.blink_server = yield self.cxn_blink.ad5764_dcbox
                    yield self.blink_server.select_device(device_info)
                elif device_info.startswith('DA'):
                    self.blink_server = yield self.cxn_blink.dac_adc
                    yield self.blink_server.select_device(device_info)

                self.outputs['blink out'] = config['blink channel']
            else:
                print("'DC Box' not found, LabRAD connection to Scan Control Failed.")
                return
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(0, 170, 0);border-radius: 4px;}")

            yield self.loadCurrentState()

            self.unlockInterface()
        except Exception: # as inst:
            self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(161, 0, 0);border-radius: 4px;}")
            printErrorInfo()

    def disconnectLabRAD(self):
        self.cxn = False
        self.cxn_dv = False
        self.dac = False
        self.gen_dv = False
        self.dv = False
        self.blink_server = False

        self.lockInterface()

        self.push_Servers.setStyleSheet("#push_Servers{" +
            "background: rgb(144, 140, 9);border-radius: 4px;}")

    @inlineCallbacks
    def loadCurrentState(self):
        try:
            self.Atto_X_Voltage = yield self.dac.read_dac_voltage(self.outputs['x out']-1)
            self.Atto_Y_Voltage = yield self.dac.read_dac_voltage(self.outputs['y out']-1)
            self.Atto_Z_Voltage = yield self.dac.read_dac_voltage(self.outputs['z out']-1)
            # print("loadCurrentState", self.Atto_Z_Voltage)

            self.updatePosition()
        except:
            printErrorInfo()

    def updateDataVaultDirectory(self):
        curr_folder = yield self.gen_dv.cd()
        yield self.dv.cd(curr_folder)

    def showServersList(self):
        serList = serversList(self.reactor, self)
        serList.exec_()

    def setupAdditionalUi(self):
        #Initial read only configuration of line edits
        self.lineEdit_LineTime.setReadOnly(True)
        self.lineEdit_Linear.setReadOnly(False)

        self.comboBox_blinkMode.view().setMinimumWidth(130)

        #Have drop down view be wider than the real view to see all the entries
        self.comboBox_PostProcessing.view().setMinimumWidth(130)

        #Set up main plot
        self.view = pg.PlotItem(title="Trace")
        self.view.setLabel('left',text='Y position',units = 'm')
        self.view.setLabel('right',text='Y position',units = 'm')
        self.view.setLabel('top',text='X position',units = 'm')
        self.view.setLabel('bottom',text='X position',units = 'm')
        self.Plot2D = ScanImageView(parent = self.centralwidget, view = self.view, randFill = self.randomFill)
        self.view.invertY(False)
        self.view.setAspectLocked(self.aspectLocked)
        self.Plot2D.ui.roiBtn.hide()
        self.Plot2D.ui.menuBtn.hide()
        self.Plot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        self.Plot2D.lower()
        self.PlotArea.close()
        self.horizontalLayout.addWidget(self.Plot2D)

        #Set up retrace plot
        self.view3 = pg.PlotItem(title="Retrace")
        self.view3.setLabel('left',text='Y position',units = 'm')
        self.view3.setLabel('right',text='Y position',units = 'm')
        self.view3.setLabel('top',text='X position',units = 'm')
        self.view3.setLabel('bottom',text='X position',units = 'm')
        self.Plot2D_Retrace = ScanImageView(parent = self.centralwidget, view = self.view3, randFill = self.randomFill)
        self.view3.invertY(False)
        self.view3.setAspectLocked(self.aspectLocked)
        self.Plot2D_Retrace.ui.roiBtn.hide()
        self.Plot2D_Retrace.ui.menuBtn.hide()
        self.Plot2D_Retrace.ui.histogram.item.gradient.loadPreset('bipolar')
        self.Plot2D_Retrace.lower()
        self.PlotArea_2.close()
        self.horizontalLayout.addWidget(self.Plot2D_Retrace)

        #Set up mini plot for maximum scan range
        self.view2 = pg.PlotItem(title = "Full Scan Range")
        self.view2.setLabel('left',text='Y position',units = 'm')
        self.view2.setLabel('right',text='Y position',units = 'm')
        self.view2.setLabel('top',text='X position',units = 'm')
        self.view2.setLabel('bottom',text='X position',units = 'm')
        self.view2.enableAutoRange(self.view2.getViewBox().XYAxes, enable = False)
        self.MiniPlot2D = ScanImageView(parent = self.centralwidget, view = self.view2, randFill = self.randomFill)
        self.view2.invertY(False)
        self.MiniPlot2D.ui.roiBtn.hide()
        self.MiniPlot2D.ui.menuBtn.hide()
        self.MiniPlot2D.ui.histogram.item.gradient.loadPreset('bipolar')
        self.MiniPlot2D.ui.histogram.hide()
        self.view2.setMouseEnabled(False,False)
        self.MiniPlot2D.lower()
        self.MiniPlotArea.close()
        self.MiniPlot2D.setMinimumSize(265,265)

        self.frame_12.layout().addWidget(self.MiniPlot2D)

        #15.2 to avoid pixel overlapping with axes, hiding them
        self.view2.setXRange(-15.2e-6,15e-6,0)
        self.view2.setYRange(-15e-6,15.2e-6,0)
        self.view2.hideButtons()
        self.view2.setMenuEnabled(False)

        #Determine plot scales
        self.xscale, self.yscale = self.currW / self.lines, self.currH / self.pixels

        #Create default dataset for initial plots. lines x pixels x 3, since by default start with 3 inputs
        pxsize = (3, self.pixels, self.lines)
        #data and data_retrace contain only the raw data
        self.data = np.full(pxsize, self.randomFill)
        self.data_retrace = np.full(pxsize, self.randomFill)
        #plotData and plotData_retrace contain processed data for graphing
        self.plotData = np.full(pxsize, self.randomFill)[0]
        self.plotData_retrace = np.full(pxsize, self.randomFill)[0]

        #By default, automatically range and level the histogram when data is being updated
        self.autoLevels = True
        self.autoHistogramRange = True
        #If you manually change the range of the histograms, then stop the histogram from auto updating
        #Maybe eventially separate range from autolevels. For now changing range manually stops both
        #and changing levels manually stops neither.
        self.Plot2D.ui.histogram.vb.sigRangeChangedManually.connect(self.disableAutoHistogram)
        self.Plot2D_Retrace.ui.histogram.vb.sigRangeChangedManually.connect(self.disableAutoHistogram)

        #Connect plot histogram to the other two plots so that changing one changes the other
        self.sigHistogramRangeChangedEmitted = False
        self.Plot2D_Retrace.ui.histogram.sigLevelsChanged.connect(self.updateHistogramLevels)
        self.Plot2D_Retrace.ui.histogram.gradient.sigGradientChangeFinished.connect(self.updateTraceHistogramLookup)
        self.Plot2D_Retrace.ui.histogram.vb.sigRangeChanged.connect(self.retraceHistogramRangeChanged)

        self.Plot2D.ui.histogram.sigLevelsChanged.connect(self.updateHistogramLevels)
        self.Plot2D.ui.histogram.gradient.sigGradientChangeFinished.connect(self.updateRetraceHistogramLookup)
        self.Plot2D.ui.histogram.vb.sigRangeChanged.connect(self.traceHistogramRangeChanged)

        #Connect the trace and retrace plots view ranges
        self.sigRangeChangedEmitted = False
        self.view.sigRangeChanged.connect(self.traceRangeChanged)
        self.view3.sigRangeChanged.connect(self.retraceRangeChanged)

        #Set up UI that isn't easily done from Qt Designer
        self.traceLinePlot = pg.PlotWidget(parent = self)
        self.traceLinePlot.setLabel('left', 'Z', units = 'm')
        self.traceLinePlot.setLabel('bottom', 'Position', units = 'm')
        self.traceLinePlot.showAxis('right', show = True)
        self.traceLinePlot.showAxis('top', show = True)
        self.PlotArea_3.hide()

        horizontalSpacer = QtWidgets.QSpacerItem(130, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.horizontalLayout_3.addWidget(self.traceLinePlot)
        self.horizontalLayout_3.addItem(horizontalSpacer)

        self.retraceLinePlot = pg.PlotWidget(parent = self)
        self.retraceLinePlot.setLabel('left', 'Z', units = 'm')
        self.retraceLinePlot.setLabel('bottom', 'Position', units = 'm')
        self.retraceLinePlot.showAxis('right', show = True)
        self.retraceLinePlot.showAxis('top', show = True)
        self.PlotArea_4.hide()

        self.horizontalLayout_3.addWidget(self.retraceLinePlot)
        self.horizontalLayout_3.addItem(horizontalSpacer)

        #Below is array formatted GUIs. Each grid frame contains the GUI associated with an input. gridFrame 1 has the GUI associated with input 1, etc...
        self.inputFrames = [self.gridFrame, self.gridFrame_2, self.gridFrame_3, self.gridFrame_4, self.gridFrame_5, self.gridFrame_6, self.gridFrame_7, self.gridFrame_8]
        #Below is an arrray keeping track of whether or not an input is "active", meaning visible on the top right of the scan control window.
        self.inputActive = [True, True, True, True, True, True, True, True]
        #An array to keep track of the order of the inputs at the top right of the scan window. All the inputs in this array are "active", meaning they will be measured in a scan.
        self.inputActiveOrder = [1, 2, 3, 4, 5, 6, 7, 8]
        #Start with the first three inputs by default
        self.removeInput(3)
        self.removeInput(4)
        self.removeInput(5)
        self.removeInput(6)
        self.removeInput(7)
        self.inputScanOrder = [1,2,3]

    def setupScanningArea(self):
        #ROI and ROI3 and the trace, and retrace ROIs
        #ROI2 is the minimap ROI
        self.ROI = pg.RectROI((self.x,self.y),(self.W,self.H), movable = True)
        self.ROI2 = pg.RectROI((self.x,self.y),(self.W,self.H), movable = True)
        self.ROI3 = pg.RectROI((self.x,self.y),(self.W,self.H), movable = True)

        self.view.addItem(self.ROI)
        self.view2.addItem(self.ROI2)
        self.view3.addItem(self.ROI3)

        #Remove default handles and add desired handles.
        self.ROI.removeHandle(self.ROI.indexOfHandle(self.ROI.getHandles()[0]))
        self.ROI.addRotateHandle((0,0),(0.5,0.5), name = 'Rotate')
        self.ROI.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)

        self.ROI2.removeHandle(self.ROI2.indexOfHandle(self.ROI2.getHandles()[0]))

        self.ROI3.removeHandle(self.ROI3.indexOfHandle(self.ROI3.getHandles()[0]))
        self.ROI3.addRotateHandle((0,0),(0.5,0.5), name = 'Rotate')
        self.ROI3.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)

    def updateHistogramLevels(self, hist):
        mn, mx = hist.getLevels()
        self.MiniPlot2D.ui.histogram.setLevels(mn, mx)
        self.Plot2D.ui.histogram.setLevels(mn, mx)
        self.Plot2D_Retrace.ui.histogram.setLevels(mn, mx)
        #self.autoLevels = False

    def gradientsEqual(self, grad1, grad2):
        if grad1['mode'] != grad2['mode']:
            return False
        if self.sortTicks(grad1['ticks']) == self.sortTicks(grad2['ticks']):
            return True
        else:
            return False

    def sortTicks(self,ticklist):
        length = len(ticklist)
        for index in range(0,length):
            currentvalue = ticklist[index]
            position = index
            while position>0 and ticklist[position-1][0]>currentvalue[0]:
                ticklist[position] = ticklist[position-1]
                position = position-1
            ticklist[position] = currentvalue
        return ticklist

    def updateTraceHistogramLookup(self,grad):
        new_gradient = grad.saveState()
        old_gradient = self.Plot2D.ui.histogram.gradient.saveState()
        if not self.gradientsEqual(new_gradient, old_gradient):
            self.Plot2D.ui.histogram.gradient.restoreState(new_gradient)
            self.MiniPlot2D.ui.histogram.gradient.restoreState(new_gradient)

    def updateRetraceHistogramLookup(self,grad):
        new_gradient = grad.saveState()
        old_gradient = self.Plot2D_Retrace.ui.histogram.gradient.saveState()
        if not self.gradientsEqual(new_gradient,old_gradient):
            self.Plot2D_Retrace.ui.histogram.gradient.restoreState(new_gradient)
            self.MiniPlot2D.ui.histogram.gradient.restoreState(new_gradient)

    def traceHistogramRangeChanged(self, input):
        #This format was done because setRange emits a range as changed signal, so you need to toggle this boolean to cut
        #a possible infinite recursion
        if not self.sigHistogramRangeChangedEmitted:
            range = input.viewRange()
            self.sigHistogramRangeChangedEmitted= True
            self.Plot2D_Retrace.ui.histogram.vb.setRange(xRange = range[0], yRange = range[1], padding =  0, update = False)
        else:
            self.sigHistogramRangeChangedEmitted= False

    def retraceHistogramRangeChanged(self, input):
        if not self.sigHistogramRangeChangedEmitted:
            range = input.viewRange()
            self.sigHistogramRangeChangedEmitted= True
            self.Plot2D.ui.histogram.vb.setRange(xRange = range[0], yRange = range[1], padding =  0, update = False)
        else:
            self.sigHistogramRangeChangedEmitted= False

    def set_voltage_calibration(self, calibration):
        self.x_volts_to_meters = float(calibration[1])
        self.y_volts_to_meters = float(calibration[2])
        self.z_volts_to_meters = float(calibration[3])
        self.x_meters_max = float(calibration[4])
        self.y_meters_max = float(calibration[5])
        self.z_meters_max = float(calibration[6])
        self.x_volts_max = float(calibration[7])
        self.y_volts_max = float(calibration[8])
        self.z_volts_max = float(calibration[9])

        self.view2.setXRange(-self.x_meters_max/2 - 2.0e-7,self.x_meters_max/2,0)
        self.view2.setYRange(-self.y_meters_max/2,self.y_meters_max/2 + 2.0e-7,0)

        self.lineEdit_Input1Conversion.setText(formatNum(self.z_volts_to_meters))
        self.inputs[0]['Conversion'] = self.z_volts_to_meters

        self.updatePosition()
        self.updateFrameTime()

#----------------------------------------------------------------------------------------------#
    """ The following section connects actions related to buttons on the Scan Control window."""

    def toggleFrameLock(self):
        if self.FrameLocked == True:
            self.push_FrameLock.setStyleSheet("#push_FrameLock{"+
            "image:url(:/nSOTScanner/Pictures/unlock.png);background: black;}")
            self.FrameLocked = False
            self.ROI.removeHandle(1)
            self.ROI.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = False)
            self.ROI3.removeHandle(1)
            self.ROI3.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = False)
        else:
            self.push_FrameLock.setStyleSheet("#push_FrameLock{"+
            "image:url(:/nSOTScanner/Pictures/lock.png);background: black;}")
            self.FrameLocked = True
            self.ROI.removeHandle(1)
            self.ROI.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)
            self.ROI3.removeHandle(1)
            self.ROI3.addScaleHandle((1,1), (.5,.5), name = 'Scale', lockAspect = True)

    def toggleDataLock(self):
        if self.DataLocked == True:
            self.push_DataLock.setStyleSheet("#push_DataLock{"+
            "image:url(:/nSOTScanner/Pictures/unlock.png);background: black;}")
            self.DataLocked = False
        else:
            self.push_DataLock.setStyleSheet("#push_DataLock{"+
            "image:url(:/nSOTScanner/Pictures/lock.png);background: black;}")
            self.DataLocked = True

    def toggleSmoothScan(self):
        if self.scanSmooth == True:
            self.push_toggleSmooth.setStyleSheet("#push_toggleSmooth{"+
            "image:url(:/nSOTScanner/Pictures/stepScan.png);background: black;}")
            self.label_Linear.setText('Delay (s)')
            self.lineEdit_Linear.setText(formatNum(self.delayTime))
            self.lineTime = self.pixels * self.delayTime
            self.scanSmooth = False
        else:
            self.push_toggleSmooth.setStyleSheet("#push_toggleSmooth{"+
            "image:url(:/nSOTScanner/Pictures/smoothScan.png);background: black;}")
            self.label_Linear.setText('Linear (m/s)')
            self.lineEdit_Linear.setText(formatNum(self.linearSpeed))
            self.lineTime = self.W / self.linearSpeed
            self.scanSmooth = True
        self.lineEdit_LineTime.setText(formatNum(self.lineTime))
        self.updateFrameTime()

    def resetScan(self):
        #Set scan values to those of the previous scan
        self.angle = self.currAngle
        self.Xc = self.currXc
        self.Yc = self.currYc
        self.W = self.currW
        self.H = self.currH
        self.x = self.curr_x
        self.y = self.curr_y

        self.updateGUI()
        self.moveROIs()

    def autoRangeImageViews(self):
        self.Plot2D.autoRange()
        self.Plot2D_Retrace.autoRange()

    def autoLevelImageViews(self):
        self.Plot2D_Retrace.autoLevels()
        self.Plot2D_Retrace.ui.histogram.vb.autoRange()
        self.autoLevels = True
        self.autoHistogramRange = True

    def disableAutoHistogram(self):
        self.autoLevels = False
        self.autoHistogramRange = False

    def toggleAspect(self):
        if self.aspectLocked:
            self.aspectLocked = False
            self.view.setAspectLocked(False)
            self.view3.setAspectLocked(False)
            self.push_aspectLocked.setText(str('Lock Aspect'))
        else:
            self.aspectLocked = True
            self.view.setAspectLocked(True, ratio = 1)
            self.view3.setAspectLocked(True, ratio = 1)
            self.push_aspectLocked.setText(str('Unlock Aspect'))

    def toggleCoordinates(self):
        if self.scanCoordinates:
            self.scanCoordinates = False
            self.update_gph()
            self.moveROI()
            self.moveROI3()
            self.push_scanCoordinates.setText('View Scan Coord.')
        else:
            self.scanCoordinates = True
            self.update_gph()
            self.moveROI()
            self.moveROI3()
            self.push_scanCoordinates.setText('View Atto Coord.')

    def selectProcessing(self, string):
        self.dataProcessing = string
        self.refreshPlotData()

    def selectPostProcessing(self, string):
        self.dataPostProcessing = string

    def selectChannel(self):
        self.channel = self.comboBox_Channel.currentIndex()
        self.traceLinePlot.setLabel('left', self.inputs[self.inputActiveOrder[self.channel]-1]['Name'], units = self.inputs[self.inputActiveOrder[self.channel]-1]['Units'])
        self.retraceLinePlot.setLabel('left', self.inputs[self.inputActiveOrder[self.channel]-1]['Name'], units = self.inputs[self.inputActiveOrder[self.channel]-1]['Units'])
        self.refreshPlotData()

    def setBlinkMode(self):
        self.blinkMode = self.comboBox_blinkMode.currentIndex()
        self.updateFrameTime()

    def refreshPlotData(self):
        if self.dataProcessing == 'Raw':
            self.plotData = np.copy(self.data[self.channel])
            self.plotData_retrace = np.copy(self.data_retrace[self.channel])
        elif self.dataProcessing == 'Subtract Average':
            self.plotData = processImageData(np.copy(self.data[self.channel]), 'Subtract Line Average')
            self.plotData_retrace = processImageData(np.copy(self.data_retrace[self.channel]), 'Subtract Line Average')
        elif self.dataProcessing == 'Subtract Linear Fit':
            self.plotData = processImageData(np.copy(self.data[self.channel]), 'Subtract Line Linear')
            self.plotData_retrace = processImageData(np.copy(self.data_retrace[self.channel]), 'Subtract Line Linear')
        elif self.dataProcessing == 'Subtract Parabolic Fit':
            self.plotData = processImageData(np.copy(self.data[self.channel]), 'Subtract Line Quadratic')
            self.plotData_retrace = processImageData(np.copy(self.data_retrace[self.channel]), 'Subtract Line Quadratic')
        self.update_gph()

    def apply2DFit(self):
        if self.dataPostProcessing == 'Raw':
            self.plotData = np.copy(self.data[self.channel])
            self.plotData_retrace = np.copy(self.data_retrace[self.channel])
        else:
            self.plotData = processImageData(np.copy(self.plotData), self.dataPostProcessing)
            self.plotData_retrace = processImageData(np.copy(self.plotData_retrace), self.dataPostProcessing)
        self.update_gph()

    #----------------------------------------------------------------------------------------------#

    """ The following section connects actions related to drawing the scanning square and updating
        the plots."""

    def updateROI(self,input):
        #Use rules for updating GUI for when the first ROI is changed
        self.updateScanArea(input)
        self.updateGUI()
        #Then move the second ROI to match
        self.moveROI2()
        self.moveROI3()

    def updateROI2(self,input):
        #Use rules for updating GUI for when the second ROI is changed
        self.updateScanArea2(input)
        self.updateGUI()
        #Then move the first ROI to match
        self.moveROI()
        self.moveROI3()

    def updateROI3(self,input):
        #Use rules for updating GUI for when the second ROI is changed
        self.updateScanArea(input)
        self.updateGUI()
        #Then move the first ROI to match
        self.moveROI()
        self.moveROI2()

    def updateScanArea(self, input):
        size = input.size()
        W = size.x()
        H = size.y()

        if self.scanCoordinates:
            inputAngle = input.angle()
            angle = inputAngle + self.currAngle
            pos = input.pos()
            posx = -self.W*np.cos(inputAngle*np.pi/180)/2 + self.H*np.sin(inputAngle*np.pi/180)/2
            posy = -self.H*np.cos(inputAngle*np.pi/180)/2 - self.W*np.sin(inputAngle*np.pi/180)/2
            Xc = (pos.x() - posx) * np.cos(self.currAngle*np.pi/180) - (pos.y() - posy) * np.sin(self.currAngle*np.pi/180) + self.currXc
            Yc = (pos.y() - posy) * np.cos(self.currAngle*np.pi/180) + (pos.x() - posx) * np.sin(self.currAngle*np.pi/180) + self.currYc
            x = self.Xc - self.W*np.cos(self.angle*np.pi/180)/2 + self.H*np.sin(self.angle*np.pi/180)/2
            y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
        else:
            angle = input.angle()
            pos = input.pos()
            x = pos.x()
            y = pos.y()
            Xc = self.x - self.H*np.sin(self.angle*np.pi/180)/2 + self.W*np.cos(self.angle*np.pi/180)/2
            Yc = self.y + self.H*np.cos(self.angle*np.pi/180)/2 + self.W*np.sin(self.angle*np.pi/180)/2

        if self.isInRange(x, y, W, H, angle):
            self.x = x
            self.y = y
            self.Xc = Xc
            self.Yc = Yc
            self.W = W
            self.H = H
            self.SquareAspectRatio = self.H / self.W
            self.angle = angle

    def updateScanArea2(self, input):
        size = input.size()
        W = size.x()
        H = size.y()

        angle = input.angle()
        pos = input.pos()
        x = pos.x()
        y = pos.y()
        Xc = self.x - self.H*np.sin(self.angle*np.pi/180)/2 + self.W*np.cos(self.angle*np.pi/180)/2
        Yc = self.y + self.H*np.cos(self.angle*np.pi/180)/2 + self.W*np.sin(self.angle*np.pi/180)/2

        if self.isInRange(x, y, W, H, angle):
            self.x = x
            self.y = y
            self.Xc = Xc
            self.Yc = Yc
            self.W = W
            self.H = H
            self.SquareAspectRatio = self.H / self.W
            self.angle = angle

    def moveROI(self):
        self.ROI.setSize([self.W, self.H], update = False, finish = False)
        if self.scanCoordinates:
            angle = self.angle-self.currAngle
            self.ROI.setAngle(angle, update = False, finish = False)
            x = (self.Xc - self.currXc)*np.cos(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.sin(self.currAngle*np.pi/180) + self.H*np.sin(angle*np.pi/180)/2 - self.W*np.cos(angle*np.pi/180)/2
            y = -(self.Xc - self.currXc)*np.sin(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.cos(self.currAngle*np.pi/180) - self.H*np.cos(angle*np.pi/180)/2 - self.W*np.sin(angle*np.pi/180)/2
            self.ROI.setPos([x, y], update = False, finish = False)
        else:
            self.ROI.setAngle(self.angle, update = False, finish = False)
            self.ROI.setPos([self.x, self.y], update = False, finish = False)
        self.updateHandles(self.ROI)

    def moveROI2(self):
        self.ROI2.setPos([self.x, self.y], update = False, finish = False)
        self.ROI2.setSize([self.W, self.H], update = False, finish = False)
        self.ROI2.setAngle(self.angle, update = False, finish = False)
        self.updateHandles(self.ROI2)

    def moveROI3(self):
        self.ROI3.setSize([self.W, self.H], update = False, finish = False)
        if self.scanCoordinates:
            angle = self.angle-self.currAngle
            self.ROI3.setAngle(angle, update = False, finish = False)
            x = (self.Xc - self.currXc)*np.cos(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.sin(self.currAngle*np.pi/180) + self.H*np.sin(angle*np.pi/180)/2 - self.W*np.cos(angle*np.pi/180)/2
            y = -(self.Xc - self.currXc)*np.sin(self.currAngle*np.pi/180) + (self.Yc - self.currYc)*np.cos(self.currAngle*np.pi/180) - self.H*np.cos(angle*np.pi/180)/2 - self.W*np.sin(angle*np.pi/180)/2
            self.ROI3.setPos([x, y], update = False, finish = False)
        else:
            self.ROI3.setAngle(self.angle, update = False, finish = False)
            self.ROI3.setPos([self.x, self.y], update = False, finish = False)
        self.updateHandles(self.ROI3)

    def updateHandles(self, ROI):
        for h in ROI.handles:
            if h['item'] in ROI.childItems():
                h['item'].setPos(h['pos'] * ROI.state['size'])
            ROI.update()

    def toggleROIVisibility(self):
        if self.checkBox.isChecked():
            self.view.addItem(self.ROI)
            self.view3.addItem(self.ROI3)
        else:
            self.view.removeItem(self.ROI)
            self.view3.removeItem(self.ROI3)

    def traceRangeChanged(self, input):
        #Presumably this was done because setRange emits a range as changed signal, so you need to toggle this boolean to cut
        #a possible infinite recursion
        if not self.sigRangeChangedEmitted:
            range = input.viewRange()
            self.sigRangeChangedEmitted = True
            self.view3.setRange(xRange = range[0], yRange = range[1], padding =  0, update = False)
        else:
            self.sigRangeChangedEmitted = False

    def retraceRangeChanged(self, input):
        if not self.sigRangeChangedEmitted:
            range = input.viewRange()
            self.sigRangeChangedEmitted = True
            self.view.setRange(xRange = range[0], yRange = range[1], padding =  0, update = False)
        else:
            self.sigRangeChangedEmitted = False

    def setView(self):
        '''
        Sets the scan range to be everything that is currently in view.
        '''
        x_range, y_range = self.view.viewRange()
        if self.scanCoordinates:
            #Set the appropriate information
            angle = self.currAngle
            W = x_range[1] - x_range[0]
            H = y_range[1] - y_range[0]
            posx = -self.W/2
            posy = -self.H/2
            Xc = (x_range[0] - posx) * np.cos(angle*np.pi/180) - (y_range[0] - posy) * np.sin(angle*np.pi/180) + self.currXc
            Yc = (y_range[0] - posy) * np.cos(angle*np.pi/180) + (x_range[0] - posx) * np.sin(angle*np.pi/180) + self.currYc
            x = Xc - np.cos(angle*np.pi/180)/2 + H*np.sin(angle*np.pi/180)/2
            y = Yc - np.cos(angle*np.pi/180)/2 - W*np.sin(angle*np.pi/180)/2

            if self.isInRange(x, y, W, H, angle):
                self.x = x
                self.Xc = Xc
                self.y = y
                self.Yc = Yc
                self.W = W
                self.H = H
                self.SquareAspectRatio = self.H / self.W
                self.angle = angle

                #update all the lines
                self.updateLineEdits()
                #Update ROIs
                self.moveROIs()

        else:
            #Set the appropriate information
            angle = 0
            W = x_range[1] - x_range[0]
            H = y_range[1] - y_range[0]
            Xc = (x_range[1] + x_range[0])/2
            Yc = (y_range[1] + y_range[0])/2
            x = x_range[0]
            y = y_range[0]

            if self.isInRange(x, y, W, H, angle):
                self.x = x
                self.Xc = Xc
                self.y = y
                self.Yc = Yc
                self.W = W
                self.H = H
                self.SquareAspectRatio = self.H / self.W
                self.angle = angle

                #update all the lines
                self.updateLineEdits()
                #Update ROIs
                self.moveROIs()

    def updateGUI(self):
        '''
        Updates the text elements of the GUI once =the scan range have been changed.
        '''
        self.lineEdit_W.setText(formatNum(self.W))
        self.lineEdit_H.setText(formatNum(self.H))
        self.lineEdit_Xc.setText(formatNum(self.Xc))
        self.lineEdit_Yc.setText(formatNum(self.Yc))
        self.lineEdit_Angle.setText(formatNum(self.angle))
        if self.scanSmooth:
                self.lineTime = self.W / self.linearSpeed
                self.lineEdit_LineTime.setText(formatNum(self.lineTime))

    def moveROIs(self):
        self.moveROI()
        self.moveROI2()
        self.moveROI3()

#----------------------------------------------------------------------------------------------#

    """ The following section connects actions related to updating scan parameters from
        the line edits."""

    def updateXc(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_Xc.text()), self, True)
        if isinstance(val,float):
            Xc = val
            x = Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
            if self.isInRange(x, self.y, self.W, self.H, self.angle):
                self.Xc = Xc
                self.x = x
                self.moveROIs()
        self.lineEdit_Xc.setText(formatNum(self.Xc))

    def updateYc(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_Yc.text()), self, True)
        if isinstance(val,float):
            Yc = val
            y = Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2
            if self.isInRange(self.x, y, self.W, self.H, self.angle):
                self.Yc = Yc
                self.y = y
                self.moveROIs()
        self.lineEdit_Yc.setText(formatNum(self.Yc))

    def updateAngle(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_Angle.text()))
        if isinstance(val,float):
            angle = val
            x = self.Xc + self.H*np.sin(angle*np.pi/180)/2 - self.W*np.cos(angle*np.pi/180)/2
            y = self.Yc - self.H*np.cos(angle*np.pi/180)/2 - self.W*np.sin(angle*np.pi/180)/2
            if self.isInRange(x, y, self.W, self.H, angle):
                self.x = x
                self.y = y
                self.angle = angle
                self.moveROIs()
        self.lineEdit_Angle.setText(formatNum(self.angle))

    def updateH(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_H.text()), self, True)
        if isinstance(val,float):
            H = val
            if self.FrameLocked:
                W = H / self.SquareAspectRatio
            else:
                W = self.W

            x = self.Xc + H*np.sin(self.angle*np.pi/180)/2 - W*np.cos(self.angle*np.pi/180)/2
            y = self.Yc - H*np.cos(self.angle*np.pi/180)/2 - W*np.sin(self.angle*np.pi/180)/2

            if self.isInRange(x, y, W, H, self.angle):
                self.H = H
                self.W = W
                self.SquareAspectRatio = self.H / self.W
                self.x = x
                self.y = y
                self.moveROIs()

        self.updateGUI()

    def updateW(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_W.text()), self, True)
        if isinstance(val,float):
            W = val
            if self.FrameLocked:
                H = W * self.SquareAspectRatio
            else:
                H = self.H

            x = self.Xc + H*np.sin(self.angle*np.pi/180)/2 - W*np.cos(self.angle*np.pi/180)/2
            y = self.Yc - H*np.cos(self.angle*np.pi/180)/2 - W*np.sin(self.angle*np.pi/180)/2

            if self.isInRange(x, y, W, H, self.angle):
                self.H = H
                self.W = W
                self.SquareAspectRatio = self.H / self.W
                self.x = x
                self.y = y
                self.moveROIs()

        self.updateGUI()

    def updatePixels(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_Pixels.text()))
        if isinstance(val,float) and int(val) > 0:
            self.pixels = int(val)
            if self.DataLocked:
                self.lines = int(val/self.PixelsAspectRatio)
                self.lineEdit_Lines.setText(formatNum(self.lines))
            else:
                self.PixelsAspectRatio = float(self.pixels)/float(self.lines)
            if not self.scanSmooth:
                self.lineTime = self.pixels*self.delayTime
                self.lineEdit_LineTime.setText(formatNum(self.lineTime))
            self.updateFrameTime()
        self.lineEdit_Pixels.setText(formatNum(self.pixels))

    def updateLines(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_Lines.text()))
        if isinstance(val,float) and int(val) > 0:
            self.lines = int(val)
            if self.DataLocked:
                self.pixels = int(val*self.PixelsAspectRatio)
                self.lineEdit_Pixels.setText(formatNum(self.pixels))
                if not self.scanSmooth:
                    self.lineTime = self.pixels*self.delayTime
                    self.lineEdit_LineTime.setText(formatNum(self.lineTime))
            else:
                self.PixelsAspectRatio = float(self.pixels)/float(self.lines)
            self.updateFrameTime()
        self.lineEdit_Lines.setText(formatNum(self.lines))

    def updateLinearSpeed(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_Linear.text()), self, True)
        if isinstance(val,float) and val > 0:
            if self.scanSmooth:
                self.linearSpeed = val
                self.lineTime = self.W/self.linearSpeed
            else:
                self.delayTime = val
                self.lineTime = self.pixels * self.delayTime
            self.lineEdit_LineTime.setText(formatNum(self.lineTime))
        if self.scanSmooth:
            self.lineEdit_Linear.setText(formatNum(self.linearSpeed))
        else:
            self.lineEdit_Linear.setText(formatNum(self.delayTime))
        self.updateScanParameters()
        self.updateFrameTime()

    def updateFileName(self):
        self.fileName = str(self.lineEdit_FileName.text())

    def updateXTilt(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_XTilt.text()))
        if isinstance(val,float):
            self.x_tilt = val*np.pi / 180
            self.updateScanPlaneCenter()
        self.lineEdit_XTilt.setText(formatNum(self.x_tilt*180 / np.pi))

    def updateYTilt(self, val = None):
        if val is None:
            val = readNum(str(self.lineEdit_YTilt.text()))
        if isinstance(val,float):
            self.y_tilt = val*np.pi / 180
            self.updateScanPlaneCenter()
        self.lineEdit_YTilt.setText(formatNum(self.y_tilt*180 / np.pi))

    def updateScanMode(self, string):
        if string == 'Constant Height':
            self.scanMode = 'Constant Height'
            self.lineEdit_XTilt.setEnabled(True)
            self.lineEdit_YTilt.setEnabled(True)
            if self.ConstantHeightReady:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
            else:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)
        elif string == 'Feedback':
            self.scanMode = 'Feedback'
            self.lineEdit_XTilt.setEnabled(False)
            self.lineEdit_YTilt.setEnabled(False)
            if self.FeedbackReady:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
            else:
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)
        self.updateFrameTime()

    def updateFeedbackStatus(self, status):
        if status:
            self.FeedbackReady = True
            if self.scanMode == 'Feedback':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
        else:
            self.FeedbackReady = False
            if self.scanMode == 'Feedback':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)

    @inlineCallbacks
    def updateConstantHeightStatus(self, status):
        '''
        The attocube X and Y voltages are only controlled by the scan module, so unless the software
        crashes they won't have changed. However, the Approach module can sometimes change the Z voltage
        from the scanning dac adc. Therefore, before updating the center of the plane always read the
        output voltage on the Z channel to make sure there's no mismatch.
        '''
        self.Atto_Z_Voltage = yield self.dac.read_dac_voltage(self.outputs['z out']-1)
        # print("updateConstantHeightStatus", self.Atto_Z_Voltage)
        self.updateScanPlaneCenter()

        if status:
            self.ConstantHeightReady = True
            if self.scanMode == 'Constant Height':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(0, 170, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(True)
        else:
            self.ConstantHeightReady = False
            if self.scanMode == 'Constant Height':
                self.push_scanModeSet.setStyleSheet("""#push_scanModeSet{
                background: rgb(161, 0, 0);
                border-radius: 5px;
                }""")
                self.push_Scan.setEnabled(False)

    def updateScanPlaneCenter(self):
        '''
        Sets the current x, y, z position to be the center of the scan plane.
        '''
        self.z_center = (self.Atto_Z_Voltage) / self.z_volts_to_meters
        self.x_center = self.Atto_X_Voltage / self.x_volts_to_meters - self.x_meters_max/2
        self.y_center = self.Atto_Y_Voltage / self.y_volts_to_meters - self.y_meters_max/2


    def getPlaneVoltages(self, x,y):
        '''
        When in constant height mode, we always want to be moving on a plane. This function takes in the desired X and Y coordinates
        in meters and returns the X, Y, Z voltages that need to be traveled to.
        '''
        z = self.z_center - np.tan(self.x_tilt)*(x-self.x_center) - np.tan(self.y_tilt)*(y-self.y_center)

        #Below is how it used to be done. Reference to make sure new version also does this properly
        #startz = self.Atto_Z_Voltage + self.Atto_Z_Voltage_Offset
        #stopz = startz - self.scanParameters['line_y']*np.tan(self.y_tilt)*self.z_volts_to_meters/self.y_volts_to_meters - self.scanParameters['line_x']*np.tan(self.x_tilt)*self.z_volts_to_meters/self.x_volts_to_meters

        z_volts = z * self.z_volts_to_meters
        x_volts = (x + self.x_meters_max/2) * self.x_volts_to_meters
        y_volts = (y + self.y_meters_max/2) * self.y_volts_to_meters

        return np.array([z_volts,x_volts,y_volts])

    def updateXset(self):
        val = readNum(self.lineEdit_Xset.text())
        if isinstance(val,float):
            Xset = val
            Vset = Xset * self.x_volts_to_meters + self.x_volts_max/2
            if  0 <= Vset <= self.x_volts_max:
                self.Xset = Xset
        self.lineEdit_Xset.setText(formatNum(self.Xset))

    def updateYset(self):
        val = readNum(self.lineEdit_Yset.text())
        if isinstance(val,float):
            Yset = val
            Vset = Yset * self.y_volts_to_meters + self.y_volts_max/2
            if  0 <= Vset <= self.y_volts_max:
                self.Yset = Yset
        self.lineEdit_Yset.setText(formatNum(self.Yset))

    def updatePosition(self):
        xpos = (self.Atto_X_Voltage - self.x_volts_max/2) / self.x_volts_to_meters
        ypos = (self.Atto_Y_Voltage - self.y_volts_max/2) / self.y_volts_to_meters

        self.lineEdit_Xcurr.setText(formatNum(xpos))
        self.lineEdit_Ycurr.setText(formatNum(ypos))

    def updateFrameTime(self):
        try:
            #These speeds are calculated using the manually set delay values
            lineContribution = 2*self.lines * self.lineTime
            if self.scanSmooth and self.lines > 1:
                pixelContribution = self.H / (self.linearSpeed)
            else:
                pixelContribution = 0

            #Next we consider the unavoidable delays not accounted for in speed calcualtions.
            line_x = self.W * np.cos(np.pi*self.angle/180) * self.x_volts_to_meters
            line_y = self.W * np.sin(np.pi*self.angle/180) * self.y_volts_to_meters

            line_points = int(np.maximum(np.absolute(line_x / (self.voltageStepSize)), np.absolute(line_y / (self.voltageStepSize))))

            line_ADC = self.pixels
            if self.scanSmooth:
                line_DAC = np.maximum(line_points, self.pixels)
            else:
                line_DAC = self.pixels

            if self.lines > 1:
                pixel_x = -self.H * np.sin(np.pi*self.angle/180) * self.x_volts_to_meters / (self.lines - 1)
                pixel_y = self.H * np.cos(np.pi*self.angle/180) * self.y_volts_to_meters / (self.lines - 1)
            else:
                pixel_x = 0
                pixel_y = 0

            pixel_points = int(np.maximum(np.absolute(pixel_x / (self.voltageStepSize)), np.absolute(pixel_y / (self.voltageStepSize))))
            if pixel_points == 0:
                pixel_points = 1

            #Pixel_ADC should be 0, but causes a bug in the code. So currently set to 1
            pixel_ADC = 1
            if self.scanSmooth:
                pixel_DAC = pixel_points
            else:
                pixel_DAC = 1

            #Assumed conversion time of 465 us for ADC (determined experimentally, much larger than it should be but hey). Multiplied by the number of channels read
            #on a line scan, and only 1 on the pixel scan (that ends up thrown out).
            #Previous value assumes buffered differential input to 16 bit ADC. Unbuffered / non differential ADC was 425 us. Discrepency might just be from experimental method.
            num = len(self.inputActiveOrder)
            conversionContribution = 0.000465*(2*line_ADC*num*self.lines + pixel_ADC*(self.lines-1))

            #Assumed setting time of 71.4 us for the DAC when scanning with 2 DAC outputs, and 69.5 us when scanning with 3 DAC outputs.
            #(determined experimentally, much larger than it should be). Multiplied by either 2 or 3 depending on if scanning
            #in feedback (z is not buffer ramped) or constant height (z is controlled)
            #Previous value assumes a 20 bit DAC. For a 16 bit DAC, the value is 48 us. Also experimentally determined.
            if self.scanMode == 'Constant Height':
                settlingContribution = 0.0000695*(2*line_DAC*3*self.lines + 3*pixel_DAC*(self.lines-1))
            else:
                settlingContribution = 0.0000714*(2*line_DAC*2*self.lines + 2*pixel_DAC*(self.lines-1))

            #Assume 0.02 seconds taken for each buffer ramp call
            #3 communications per line, trace, retrace, and pixel step.
            communicationContribution = 3 * self.lines * 0.02

            #Each blink takes ~ 0.6 seconds
            blinkContribution = 0.6 * self.blinkMode * self.lines

            #Graphing contribution. Takes about 15 ms to update the graph. This happens once per line
            graphContribution = 0.015*self.lines

            self.FrameTime = lineContribution + pixelContribution + blinkContribution + communicationContribution + conversionContribution + settlingContribution+graphContribution
            self.lineEdit_FrameTime.setText(formatNum(self.FrameTime))
        except AttributeError:
            pass
#-----------------------------------------------------------------------------------------#
    '''The following section deals with managing inputs'''

    def removeInput(self, input):
        self.scrollAreaWidgetContents.layout().removeWidget(self.inputFrames[input])
        self.inputFrames[input].setParent(None)
        self.inputActive[input] = False
        self.inputActiveOrder.remove(input+1)
        self.updateFrameTime()

    def addInput(self):
        try:
            num = self.inputActive.index(False)
            self.scrollAreaWidgetContents.layout().insertWidget(self.scrollAreaWidgetContents.layout().count()-2, self.inputFrames[num])
            self.inputActive[num] = True
            self.inputActiveOrder.append(num+1)
            self.updateFrameTime()
        except ValueError:
            pass

    def setInputChannel(self, index, comboBox):
        self.inputs[index]['ADC Channel'] = comboBox.currentIndex()+1

    def setInputName(self, ind, lineEdit):
        self.inputs[ind]['Name'] = str(lineEdit.text())
        try:
            #If the edited
            pos = self.inputScanOrder.index(ind+1)
            self.comboBox_Channel.setItemText(pos, lineEdit.text())
        except ValueError:
            pass

    def setInputConversion(self, index, lineEdit):
        val = readNum(lineEdit.text())
        if isinstance(val,float):
            self.inputs[index]['Conversion'] = val
        lineEdit.setText(formatNum(self.inputs[index]['Conversion']))

    def setInputUnit(self, index, lineEdit):
        self.inputs[index]['Units'] = str(lineEdit.text())

#----------------------------------------------------------------------------------------------#
    """ The following section has scanning functions and live graph updating."""

    @inlineCallbacks
    def blink(self):
        yield self.blink_server.set_voltage(self.outputs['blink out']-1, 5)  #The -1 is necessary to get from the 1-indexed front panel numbers to the 0-indexed firmware
        yield self.sleep(0.25)
        yield self.blink_server.set_voltage(self.outputs['blink out']-1, 0)  #The -1 is necessary to get from the 1-indexed front panel numbers to the 0-indexed firmware
        yield self.sleep(0.25)

    @inlineCallbacks
    def abortScan(self):
        self.scanning = False
        print('Attempting to stop ramp')
        self.dac.stop_ramp()
        yield self.sleep(0.1)
        self.updateScanningStatus.emit(False)

    @inlineCallbacks
    def setPosition(self, x, y):
        try:
            if not self.scanning:
                self.push_ZeroXY.setEnabled(False)
                self.push_Set.setEnabled(False)
            #Buffer ramp is being used here to ramp 1 and 2, or 0,1,2 at the same time
            #Read values are not being used for anything (but are being read to avoid
            #bugs related to having 0 read values)
            startz, startx, starty = self.Atto_Z_Voltage, self.Atto_X_Voltage, self.Atto_Y_Voltage
            stopz, stopx, stopy = self.getPlaneVoltages(x, y)

            #Takes the number of points required for this to be a smooth (300 uV step size)
            points = int(np.maximum(np.absolute((stopx-startx) / (self.voltageStepSize)), np.absolute((stopy-starty) / (self.voltageStepSize))))
            #Make sure minimum of 2 point to avoid errors
            if points < 2:
                points = 2

            #Find time to travel from current position to zero position at specified linear speed
            delta_x_pos = (startx - stopx)/self.x_volts_to_meters
            delta_y_pos = (starty - stopy)/self.y_volts_to_meters
            time = np.sqrt(delta_x_pos**2 + delta_y_pos**2) / self.linearSpeed

            #Get delay in microseconds to ensure going at the module specified line speed
            delay = int(1e6 * time / points)

            #Only change the z value when moving around if we're in constant height mode
            if self.scanMode == 'Constant Height' and self.ConstantHeightReady:
                out_list = [self.outputs['z out']-1, self.outputs['x out']-1,self.outputs['y out']-1]
                yield self.dac.buffer_ramp_dis(out_list,[0],[startz,startx, starty],[stopz, stopx, stopy], points, delay,2)
                self.Atto_Z_Voltage = stopz
                # print("setPosition", self.Atto_Z_Voltage)
            else:
                out_list = [self.outputs['x out']-1,self.outputs['y out']-1]
                yield self.dac.buffer_ramp_dis(out_list,[0],[startx, starty],[stopx, stopy], points, delay,2)

            self.Atto_X_Voltage = stopx
            self.Atto_Y_Voltage = stopy

            self.updatePosition()

            if not self.scanning:
                self.push_ZeroXY.setEnabled(True)
                self.push_Set.setEnabled(True)
        except:
            printErrorInfo()


    @inlineCallbacks
    def zeroXYPosition(self):
        msgBox = QtWidgets.QMessageBox(self)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setWindowTitle('Confirm Zero Fine Positioner')
        msgBox.setText("Zero X,Y fine positioners.")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
        retValue = msgBox.exec_()
        if retValue != QtWidgets.QMessageBox.Ok:
            return
        yield self.setPosition(-self.x_meters_max / 2, -self.y_meters_max / 2)

    @inlineCallbacks
    def zeroZOffset(self):
        msgBox = QtWidgets.QMessageBox(self)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setWindowTitle('Confirm Zero Fine Positioner')
        msgBox.setText("Zero Z fine positioner.")
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok  | QtWidgets.QMessageBox.Cancel)
        msgBox.setStyleSheet("background-color:black; color:rgb(168,168,168)")
        retValue = msgBox.exec_()
        if retValue != QtWidgets.QMessageBox.Ok:
            return

        #So that, no matter what, after a scan back at 0 height relative to the Offset point. FIX THIS SOON
        print('Moving by: ' + str(self.Atto_Z_Voltage) + 'V in the z direction to return to zero z offset.')
        #By default ramps output 0 from the current z voltage back to 0 with 1000 points at 1 ms delay
        yield self.dac.ramp1(self.outputs['z out']-1, self.Atto_Z_Voltage, 0.0, 1000, 1000)
        self.Atto_Z_Voltage = 0.0
        # print("zeroOffset", self.Atto_Z_Voltage)
        print('Z voltage from the scan module has been zeroed')

        #DAC messes up with ramp commands and doesn't get fully read. This clears the buffer
        #so that the first line of data is preserved correctly. occurs because of the same
        #timeout problem
        a = yield self.dac.read()
        while a != '':
            a = yield self.dac.read()

        #Call this the new center of the plane
        yield self.updateScanPlaneCenter()

    @inlineCallbacks
    def startScan(self):
        try:
            print('Starting Scan Protocol')
            #Save the values of the current scan as separate variables so that they are not editted by moving around scan windows mid-scan
            self.currAngle = self.angle
            self.currXc = self.Xc
            self.currYc = self.Yc
            self.currW = self.W
            self.currH = self.H
            self.curr_x = self.x
            self.curr_y = self.y

            #Save a separate list of the order in which the data is saved for this scan data. Syntax on right creates a copy
            self.inputScanOrder = list(self.inputActiveOrder)

            #Determine plot scales
            self.xscale, self.yscale = self.currW / self.pixels, self.currH / self.lines

            #If we are viewing the data in the coordinate system of the scan, then update ROIs so that they are accurately reflected by the new coordinate system
            if self.scanCoordinates:
                self.moveROI()
                self.moveROI3()

            #Initialize empty data sets to the appropriate size for whatever data is being taken
            num_datasets = len(self.inputScanOrder)
            pxsize = (num_datasets, self.pixels, self.lines)

            #Make the initial dataset of null values, that has size num_datasets by pixels by lines
            self.data = np.full(pxsize, self.randomFill)
            self.data_retrace = np.full(pxsize, self.randomFill)

            #The plot data is 1 by pixel by lines (since we only plot one dataset at a time). Initially by default this is defined to be the 1st (0th) channel
            self.plotData = np.full(pxsize, self.randomFill)[0]
            self.plotData_retrace = np.full(pxsize, self.randomFill)[0]

            #Repopulate the Channel drop down menu with the appropriate number, name, and order of inputs being viewed
            #Also, define list of input channels for the scan ramps (in_list) as well as a list of input name (in_name_list)
            self.comboBox_Channel.clear()
            in_list = []
            in_name_list = []
            for a in self.inputScanOrder:
                self.comboBox_Channel.addItem(self.inputs[a-1]['Name'])
                in_name_list.append(self.inputs[a-1]['Name'])
                in_list.append(self.inputs[a-1]['ADC Channel']-1)

            #Define list of outputs for the scan ramps. If scanning in feedback, z voltage is not ramped by the dac. If constant height, it is.
            if self.scanMode == 'Feedback':
                out_list = [self.outputs['x out']-1,self.outputs['y out']-1]
            elif self.scanMode == 'Constant Height':
                out_list = [self.outputs['z out']-1, self.outputs['x out']-1,self.outputs['y out']-1]

            #Set the current scan line to -1, because we have not yet started scanning
            self.currLine = -1

            #Update graphs with empty data sets
            self.update_gph()

            #Prevent you from editing parameters mid scan that would break things
            self.scanInterfaceEnabled(False)

            #Begin data gathering procedure
            self.scanning = True
            self.updateScanningStatus.emit(True)
            self.push_Scan.setText('Scanning')
            self.push_Scan.setEnabled(False)

            #Create data vault file with appropriate parameters
            #Retrace index is 0 for trace, 1 for retrace
            file_info = yield self.dv.new("nSOT Scan Data " + self.fileName, ['Retrace Index','X Pos. Index','Y Pos. Index','X Pos. Voltage', 'Y Pos. Voltage'],in_name_list)
            self.dvFileName = file_info[1]
            self.lineEdit_ImageNum.setText(file_info[1].split(" - ")[1]) # second string is unique identifier
            session  = ''
            for folder in file_info[0][1:]:
                session = session + '\\' + folder
            self.lineEdit_ImageDir.setText(r'\.datavault' + session)
            print('Created new DV file')

            params = (('X Center', self.currXc), ('Y Center', self.currYc), ('Width', self.currW),
                     ('Height',self.currH), ('Angle',self.currAngle), ('Speed',self.linearSpeed), ('Blink', self.blinkMode),
                     ('Pixels',self.pixels), ('Lines', self.lines))

            num = 1
            for a in self.inputScanOrder:
                params += (('Input ' + str(num) + ' Name', self.inputs[a-1]['Name']), ('Input ' + str(num) + ' Units', self.inputs[a-1]['Units']) , ('Input ' + str(num) + ' Conversion', self.inputs[a-1]['Conversion']))
                num += 1

            yield self.dv.add_parameters(params)

            self.updateScanParameters()

            #Move to the bottom left corner of the scan range
            yield self.setPosition(self.curr_x, self.curr_y)

            #Start the scan timer
            self.startScanTimer()
            #Empty array of the scan data
            trace_data = []
            retrace_data = []
            for i in range(0,self.lines):
                print('Starting sweep for line ' + str(i) + '.')

                if not self.scanning:
                    break

                #Get start and end positions for scan of a single line
                startx, starty, startz = self.Atto_X_Voltage, self.Atto_Y_Voltage, self.Atto_Z_Voltage
                stopx, stopy, stopz = self.Atto_X_Voltage + self.scanParameters['line_x'], self.Atto_Y_Voltage + self.scanParameters['line_y'], self.Atto_Z_Voltage + self.scanParameters['line_z']

                #Blink prior to trace if desired
                if self.blinkMode == 1 or self.blinkMode == 2:
                    yield self.blink()

                if not self.scanning:
                    break

                #Measure time for debugging
                tzero = time.time()
                #Do buffer ramp. If in feedback mode,
                if self.scanMode == 'Feedback':
                    print("X and Y outputs: ", out_list)
                    print("Input in use in order: ", in_list)
                    if self.scanSmooth:
                        newData = yield self.dac.buffer_ramp_dis(out_list,in_list,[startx, starty],[stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'], self.pixels)
                    else:
                        newData = yield self.dac.buffer_ramp(out_list,in_list,[startx, starty],[stopx, stopy], self.pixels, self.delayTime*1e6)

                elif self.scanMode == 'Constant Height':
                    print("Z, X and Y outputs: ", out_list)
                    print("Input in use in order: ", in_list)
                    if self.scanSmooth:
                        newData = yield self.dac.buffer_ramp_dis(out_list, in_list, [startz, startx, starty], [stopz, stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'], self.pixels)
                    else:
                        newData = yield self.dac.buffer_ramp(out_list,in_list,[startz, startx, starty],[stopz, stopx, stopy], self.pixels, self.delayTime*1e6)
                    self.Atto_Z_Voltage = stopz

                self.Atto_X_Voltage = stopx
                self.Atto_Y_Voltage = stopy
                self.updatePosition()

                #bin newData to appropriate number of pixels
                print('Time taken for trace buffer ramp: ' + str(time.time()-tzero))
                tzero = time.time()
                #Add the binned Z data to the dataset. Note that right now, newData is the same length as self.pixels,
                #and the binning does nothing except flip the order of the data for retraces. The function is kept to
                #allow future modifications for multiple types of binning
                for k in range(0,num_datasets):
                    self.data[k][:,i] = self.bin_data(newData[k]/self.inputs[self.inputScanOrder[k]-1]['Conversion'], self.pixels, 'trace')

                print('Time taken to bin data: ' + str(time.time()-tzero))
                tzero = time.time()
                self.plotData[:,i] = processLineData(np.copy(self.data[self.channel][:,i]), self.dataProcessing)
                print('Time taken to process the line data: ' + str(time.time()-tzero))
                tzero = time.time()

                #Reformat data and add to data vault
                x_voltage = np.linspace(startx, stopx, self.pixels)
                y_voltage = np.linspace(starty, stopy, self.pixels)
                formatted_data = []
                for j in range(0, self.pixels):
                    data_point = (0, j, i, x_voltage[j], y_voltage[j])
                    for k in range(0,num_datasets):
                        data_point += (self.data[k][j,i],)
                    formatted_data.append(data_point)
                    trace_data.append(data_point)
                yield self.dv.add(formatted_data)
                print('Time taken to add data to data vault: ' + str(time.time()-tzero))

                #------------------------------------#

                if not self.scanning:
                    break

                #Get retrace start and stop voltage
                startx, starty, startz = self.Atto_X_Voltage, self.Atto_Y_Voltage, self.Atto_Z_Voltage
                stopx, stopy, stopz = self.Atto_X_Voltage - self.scanParameters['line_x'], self.Atto_Y_Voltage - self.scanParameters['line_y'], self.Atto_Z_Voltage - self.scanParameters['line_z']

                #Blink before retrace if desired
                if self.blinkMode == 2:
                    yield self.blink()

                if not self.scanning:
                    break

                tzero = time.time()
                if self.scanMode == 'Feedback':
                    print("X and Y outputs: ", out_list)
                    print("Input in use in order: ", in_list)
                    if self.scanSmooth:
                        newData = yield self.dac.buffer_ramp_dis(out_list,in_list,[startx, starty],[stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'], self.pixels)
                    else:
                        newData = yield self.dac.buffer_ramp(out_list,in_list,[startx, starty],[stopx, stopy], self.pixels, self.delayTime*1e6)
                elif self.scanMode == 'Constant Height':
                    print("Z, X and Y outputs: ", out_list)
                    print("Input in use in order: ", in_list)
                    if self.scanSmooth:
                        newData = yield self.dac.buffer_ramp_dis(out_list,in_list,[startz,startx, starty],[stopz, stopx, stopy], self.scanParameters['line_points'], self.scanParameters['line_delay'], self.pixels)
                    else:
                        newData = yield self.dac.buffer_ramp(out_list,in_list,[startz, startx, starty],[stopz, stopx, stopy], self.pixels, self.delayTime*1e6)
                    self.Atto_Z_Voltage = stopz

                self.Atto_X_Voltage = stopx
                self.Atto_Y_Voltage = stopy
                self.updatePosition()

                print('Time taken for retrace buffer ramp: ' + str(time.time()-tzero))
                tzero = time.time()

                #Add the binned Z data to the dataset. Note that right now, newData is the same length as self.pixels,
                #and the binning does nothing except flip the order of the data for retraces. The function is kept to
                #allow future modifications for multiple types of binning
                for k in range(0,num_datasets):
                    self.data_retrace[k][:,i] = self.bin_data(newData[k]/self.inputs[self.inputScanOrder[k]-1]['Conversion'], self.pixels, 'retrace')

                #Process data for plotting
                self.plotData_retrace[:,i] = processLineData(np.copy(self.data_retrace[self.channel][:,i]), self.dataProcessing)

                #Reformat data and add to data vault
                x_voltage = np.linspace(startx, stopx, self.pixels)
                y_voltage = np.linspace(starty, stopy, self.pixels)
                formatted_data = []
                for j in range(0, self.pixels):
                    data_point = (1, j, i, x_voltage[::-1][j], y_voltage[::-1][j])
                    for k in range(0,num_datasets):
                        data_point += (self.data_retrace[k][j,i],)
                    formatted_data.append(data_point)
                    retrace_data.append(data_point)
                yield self.dv.add(formatted_data)

                #------------------------------------#

                #update graph
                self.currLine = i
                self.update_gph()

                if not self.scanning:
                    break

                #if we are not on the last line
                if i < self.lines - 1:
                    print('Bout to move to the next line')
                    #Move to position for next line
                    startx, starty, startz = self.Atto_X_Voltage, self.Atto_Y_Voltage, self.Atto_Z_Voltage
                    stopx, stopy, stopz = self.Atto_X_Voltage + self.scanParameters['pixel_x'], self.Atto_Y_Voltage + self.scanParameters['pixel_y'], self.Atto_Z_Voltage + self.scanParameters['pixel_z']

                    #Buffer ramp is being used here to ramp 1 and 2, or 0,1,2 at the same time
                    #Read values are not being used for anything (but are being read to avoid
                    #bugs related to having 0 read values)
                    tzero = time.time()
                    if self.scanMode == 'Feedback':
                        print("X and Y outputs: ", out_list)
                        yield self.dac.buffer_ramp_dis(out_list,[0],[startx, starty],[stopx, stopy], self.scanParameters['pixel_points'], self.scanParameters['pixel_delay'],2)
                    elif self.scanMode == 'Constant Height':
                        yield self.dac.buffer_ramp_dis(out_list,[0],[startz,startx, starty],[stopz, stopx, stopy], self.scanParameters['pixel_points'], self.scanParameters['pixel_delay'],2)
                        self.Atto_Z_Voltage = stopz

                    self.Atto_X_Voltage = stopx
                    self.Atto_Y_Voltage = stopy
                    self.updatePosition()
                    #ramp to next y point
                    print('Time taken to move to next line: ' + str(time.time()-tzero))
                    tzero = time.time()

        except:
            printErrorInfo()

        #Successfully or not finished the scan!
        self.scanning = False
        self.updateScanningStatus.emit(False)

        self.push_Scan.setText('Scan')
        self.push_Scan.setEnabled(True)

        self.push_Scan.setEnabled(True)
        self.lineEdit_Angle.setEnabled(True)
        self.lineEdit_Xc.setEnabled(True)
        self.lineEdit_Yc.setEnabled(True)
        self.lineEdit_W.setEnabled(True)
        self.lineEdit_H.setEnabled(True)
        self.push_setView.setEnabled(True)
        self.lineEdit_Lines.setEnabled(True)
        self.lineEdit_Pixels.setEnabled(True)
        self.lineEdit_XTilt.setEnabled(True)
        self.lineEdit_YTilt.setEnabled(True)

        self.push_ZeroXY.setEnabled(True)
        self.push_ZeroZ.setEnabled(True)
        self.push_Set.setEnabled(True)

        #Wait until all plots are appropriately updated before saving screenshot
        yield self.sleep(0.25)
        saveDataToSessionFolder(self, self.sessionFolder, self.dvFileName)

        #yield [trace_data, retrace_data]
        returnValue([trace_data, retrace_data])

    def update_gph(self):
        #Updates the trace, retrace, and mini plots with the plotData and plotData_retract images.
        try:
            self.Plot2D.setImage(self.plotData, autoRange = False, autoLevels = self.autoLevels, autoHistogramRange = self.autoHistogramRange)
            self.Plot2D.imageItem.resetTransform()

            self.Plot2D_Retrace.setImage(self.plotData_retrace, autoRange = False, autoLevels = self.autoLevels, autoHistogramRange = self.autoHistogramRange)
            self.Plot2D_Retrace.imageItem.resetTransform()

            if self.scanCoordinates:
                angle = 0
                tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
                self.Plot2D.imageItem.setPos(-self.currW/2,-self.currH/2)
                self.Plot2D.imageItem.setTransform(tr)
                self.Plot2D_Retrace.imageItem.setPos(-self.currW/2,-self.currH/2)
                self.Plot2D_Retrace.imageItem.setTransform(tr)
            else:
                angle = self.currAngle
                tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
                self.Plot2D.imageItem.setPos(self.curr_x,self.curr_y)
                self.Plot2D.imageItem.setTransform(tr)
                self.Plot2D_Retrace.imageItem.setPos(self.curr_x,self.curr_y)
                self.Plot2D_Retrace.imageItem.setTransform(tr)

            self.MiniPlot2D.setImage(self.plotData, autoRange = False, autoLevels = self.autoLevels, autoHistogramRange = self.autoHistogramRange)
            self.MiniPlot2D.imageItem.resetTransform()
            angle = self.currAngle
            tr = QtGui.QTransform(self.xscale * np.cos(angle * np.pi/180),self.xscale * np.sin(angle * np.pi/180),0,-self.yscale * np.sin(angle * np.pi/180),self.yscale * np.cos(angle * np.pi/180),0,0,0,1)
            self.MiniPlot2D.imageItem.setPos(self.curr_x,self.curr_y)
            self.MiniPlot2D.imageItem.setTransform(tr)

            #Update line traces
            self.traceLinePlot.clear()
            self.retraceLinePlot.clear()
            if self.currLine >= 0:
                pos = np.linspace(-self.currH/2, self.currH/2, self.pixels)
                self.traceLinePlot.plot(pos, self.plotData[:,self.currLine])
                self.retraceLinePlot.plot(pos, self.plotData_retrace[:,self.currLine])

        except:
            printErrorInfo()


    def scanInterfaceEnabled(self, status):
        self.push_Scan.setEnabled(status)
        self.lineEdit_Angle.setEnabled(status)
        self.lineEdit_Xc.setEnabled(status)
        self.lineEdit_Yc.setEnabled(status)
        self.lineEdit_W.setEnabled(status)
        self.lineEdit_H.setEnabled(status)
        self.push_setView.setEnabled(status)
        self.lineEdit_Lines.setEnabled(status)
        self.lineEdit_Pixels.setEnabled(status)
        self.lineEdit_XTilt.setEnabled(status)
        self.lineEdit_YTilt.setEnabled(status)

        self.push_ZeroXY.setEnabled(status)
        self.push_ZeroZ.setEnabled(status)
        self.push_Set.setEnabled(status)

    '''
    Function that in the future can be implemented to bin data in different ways.
    Right now, it simply takes a line of M data points and takes N number of points
    equally spaced in that dataset. Also allows to reverse the order of the data
    taken with a retrace, so that it's stored in the same order as a trace.
    '''
    def bin_data(self, data, num_points, trace):
        length = np.size(data)

        points = np.round(np.linspace(0,length-1,num_points)).astype(int)
        binned_data = np.take(data,points)
        if trace == 'retrace':
            binned_data = binned_data[::-1]
        return binned_data

    def updateScanParameters(self):
        #-------------------------------------------------------------------------------------------------#
        '''
        Single Line Scan Calculation
        '''

        #Calculate the number of points, delta_x/delta_y/delta_z for scanning a line
        dx = self.currW * np.cos(np.pi*self.currAngle/180)
        dy = self.currW * np.sin(np.pi*self.currAngle/180)
        line_z, line_x, line_y = self.getPlaneVoltages(dx, dy) - self.getPlaneVoltages(0,0)

        line_points = int(np.maximum(np.absolute(line_x / (self.voltageStepSize)), np.absolute(line_y / (self.voltageStepSize))))
        #If the scan range is so small that the number of steps to take with high resolution is
        #less than the desired number of pixels to have in the scan, set the number of points to
        #be the deisred number of pixels. This means that, in reality, several points will be taken
        #at the same position. But w/e dude
        if line_points < self.pixels:
            line_points = self.pixels
        line_delay = int(1e6 *self.lineTime / line_points)

        #-------------------------------------------------------------------------------------------------#
        '''
        Move to next line scan calculation
        '''
        #Calculate the speed, number of points, and delta_x/delta_y for moving to the next line
        #If only doing 1 line, then don't move pixels at all!
        if self.lines > 1:
            dx = -self.currH * np.sin(np.pi*self.currAngle/180)/ (self.lines - 1)
            dy = self.currH * np.cos(np.pi*self.currAngle/180)/ (self.lines - 1)
        else:
            dx = 0
            dy = 0

        pixel_z, pixel_x, pixel_y = self.getPlaneVoltages(dx, dy) - self.getPlaneVoltages(0,0)

        pixel_points = int(np.maximum(np.absolute(pixel_x / (self.voltageStepSize)), np.absolute(pixel_y / (self.voltageStepSize))))
        if pixel_points == 0:
            pixel_points = 1
        if self.lines >1:
            pixel_delay = int(1e6 *self.currH / ((self.lines-1)*self.linearSpeed*pixel_points))
        else:
            pixel_delay = 1e3

        self.scanParameters = {
            'line_x'                     : line_x, #volts that need to be moved in the x direction for the scan of a single line
            'line_y'                     : line_y, #volts that need to be moved in the y direction for the scan of a single line
            'line_z'                     : line_z, #volts that need to be moved in the z direction for the scan of a single line
            'line_points'                : line_points, #number of points that should be taken for minimum step resolution for a single line
            'line_delay'                 : line_delay, #delay between points for a single line to ensure proper speed
            'pixel_x'                    : pixel_x, #volts that need to be moved in the x direction to move from one line scan to the next
            'pixel_y'                    : pixel_y, #volts that need to be moved in the y direction to move from one line scan to the next
            'pixel_z'                    : pixel_z, #volts that need to be moved in the y direction to move from one line scan to the next
            'pixel_points'               : pixel_points, #number of points that should be taken for minimum step resolution for moving to next line
            'pixel_delay'                : pixel_delay, #delay between points for a single line to ensure proper speed
        }

        print('Scan parameters updated to: ')
        print(self.scanParameters)

    def isInRange(self, x, y, w, h, theta):
        '''
        Function checks if the specified position is within the scan range of the attocubes.
        Input should be in units of meters and dergees.
        x - lower left corner of scan square X coordinate
        y - lower left corner of scan square Y coordinate
        w - width of the scan
        h - height of the scan square
        theta - angle of the scans square
        Returns true if yes, false if no.
        '''
        x_extents = []
        y_extents = []

        #Bottom left point
        x_extents.append(x * self.x_volts_to_meters + self.x_volts_max/2)
        y_extents.append(y * self.y_volts_to_meters + self.y_volts_max/2)

        #Bottom right point
        x_extents.append(x_extents[0] + self.x_volts_to_meters * w * np.cos(theta*np.pi/180))
        y_extents.append(y_extents[0] + self.y_volts_to_meters * w * np.sin(theta*np.pi/180))

        x_extents.append(x_extents[0] + self.x_volts_to_meters * w * np.cos(theta*np.pi/180) - self.x_volts_to_meters * h * np.sin(theta*np.pi/180))
        y_extents.append(y_extents[0] + self.y_volts_to_meters * w * np.sin(theta*np.pi/180) + self.y_volts_to_meters * h * np.cos(theta*np.pi/180))

        x_extents.append(x_extents[0] - self.x_volts_to_meters * h * np.sin(theta*np.pi/180))
        y_extents.append(y_extents[0] + self.y_volts_to_meters * h * np.cos(theta*np.pi/180))

        if all(0 <= x <= self.x_volts_max for x in x_extents) and all(0 <= y <= self.y_volts_max for y in y_extents):
            return True
        else:
            return False

    @inlineCallbacks
    def startScanTimer(self):
        t_zero = time.time()
        while self.scanning:
            t = time.time() - t_zero
            self.lineEdit_TimeElapsed.setText(formatNum(t))
            yield self.sleep(0.25)

    def setSessionFolder(self, folder):
        self.sessionFolder = folder

#----------------------------------------------------------------------------------------------#
    """ The following section has functions intended for use when running scripts from the scripting module."""

    def setSpeed(self, speed):
        if not self.scanSmooth:
            self.toggleSmoothScan()
        self.updateLinearSpeed(speed)

    def setDelay(self, delay):
        if self.scanSmooth:
            self.toggleSmoothScan()
        self.updateLinearSpeed(delay)

    def setPixels(self, pixels):
        self.updatePixels(pixels)

    def setLines(self, lines):
        self.updateLines(lines)

    def lockDataAspect(self):
        if self.DataLocked == False:
            self.toggleDataLock()

    def unlockDataAspect(self):
        if self.DataLocked == True:
            self.toggleDataLock()

    def setTilt(self, xtilt, ytilt):
        self.updateXTilt(xtilt)
        self.updateYTilt(ytilt)

    def lockScanAspect(self):
        if self.FrameLocked == False:
            self.toggleFrameLock()

    def unlockScanAspect(self):
        if self.FrameLocked == True:
            self.toggleFrameLock()

    def setXc(self, x):
        self.updateXc(x)

    def setYc(self, y):
        self.updateYc(y)

    def setH(self, H):
        self.updateH(H)

    def setW(self, W):
        self.updateW(W)

    def setAngle(self, theta):
        self.updateAngle(theta)

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def lockInterface(self):
        self.push_Abort.setEnabled(False)
        self.push_Scan.setEnabled(False)
        self.push_DataLock.setEnabled(False)
        self.push_FrameLock.setEnabled(False)
        self.push_scanCoordinates.setEnabled(False)
        self.push_aspectLocked.setEnabled(False)
        self.push_setView.setEnabled(False)
        self.push_apply2DFit.setEnabled(False)
        self.push_autoLevel.setEnabled(False)
        self.push_autoRange.setEnabled(False)
        self.push_ZeroXY.setEnabled(False)
        self.push_ZeroZ.setEnabled(False)
        self.push_Set.setEnabled(False)

        self.lineEdit_FileName.setEnabled(False)
        self.lineEdit_Linear.setEnabled(False)
        self.lineEdit_Xc.setEnabled(False)
        self.lineEdit_Yc.setEnabled(False)
        self.lineEdit_W.setEnabled(False)
        self.lineEdit_H.setEnabled(False)
        self.lineEdit_Angle.setEnabled(False)
        self.lineEdit_Lines.setEnabled(False)
        self.lineEdit_Pixels.setEnabled(False)
        self.lineEdit_LineTime.setEnabled(False)
        self.lineEdit_FrameTime.setEnabled(False)
        self.lineEdit_ImageNum.setEnabled(False)
        self.lineEdit_XTilt.setEnabled(False)
        self.lineEdit_YTilt.setEnabled(False)

        self.comboBox_Processing.setEnabled(False)
        self.comboBox_PostProcessing.setEnabled(False)
        self.comboBox_Channel.setEnabled(False)
        self.comboBox_scanMode.setEnabled(False)
        self.comboBox_blinkMode.setEnabled(False)

        self.comboBox_Input1.setEnabled(False)
        self.comboBox_Input2.setEnabled(False)

        self.lineEdit_Input1Name.setEnabled(False)
        self.lineEdit_Input2Name.setEnabled(False)

        self.lineEdit_Input1Conversion.setEnabled(False)
        self.lineEdit_Input2Conversion.setEnabled(False)

        self.lineEdit_Input1Unit.setEnabled(False)
        self.lineEdit_Input2Unit.setEnabled(False)

        self.checkBox.setEnabled(False)

    def unlockInterface(self):
        self.push_Abort.setEnabled(True)
        #Scan start gets enabled later when it's actually ready to start scanning
        #self.push_Scan.setEnabled(True)
        self.push_DataLock.setEnabled(True)
        self.push_FrameLock.setEnabled(True)
        self.push_scanCoordinates.setEnabled(True)
        self.push_aspectLocked.setEnabled(True)
        self.push_setView.setEnabled(True)
        self.push_apply2DFit.setEnabled(True)
        self.push_autoLevel.setEnabled(True)
        self.push_autoRange.setEnabled(True)
        self.push_ZeroXY.setEnabled(True)
        self.push_ZeroZ.setEnabled(True)
        self.push_Set.setEnabled(True)

        self.lineEdit_FileName.setEnabled(True)
        self.lineEdit_Linear.setEnabled(True)
        self.lineEdit_Xc.setEnabled(True)
        self.lineEdit_Yc.setEnabled(True)
        self.lineEdit_W.setEnabled(True)
        self.lineEdit_H.setEnabled(True)
        self.lineEdit_Angle.setEnabled(True)
        self.lineEdit_Lines.setEnabled(True)
        self.lineEdit_Pixels.setEnabled(True)
        self.lineEdit_LineTime.setEnabled(True)
        self.lineEdit_FrameTime.setEnabled(True)
        self.lineEdit_ImageNum.setEnabled(True)
        self.lineEdit_XTilt.setEnabled(True)
        self.lineEdit_YTilt.setEnabled(True)

        self.comboBox_Processing.setEnabled(True)
        self.comboBox_PostProcessing.setEnabled(True)
        self.comboBox_Channel.setEnabled(True)
        self.comboBox_scanMode.setEnabled(True)
        self.comboBox_blinkMode.setEnabled(True)

        self.comboBox_Input1.setEnabled(True)
        self.comboBox_Input2.setEnabled(True)

        self.lineEdit_Input1Name.setEnabled(True)
        self.lineEdit_Input2Name.setEnabled(True)

        self.lineEdit_Input1Conversion.setEnabled(True)
        self.lineEdit_Input2Conversion.setEnabled(True)

        self.lineEdit_Input1Unit.setEnabled(True)
        self.lineEdit_Input2Unit.setEnabled(True)

        self.checkBox.setEnabled(True)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class serversList(QtWidgets.QDialog, Ui_ServerList):
    def __init__(self, reactor, parent = None):
        super(serversList, self).__init__(parent)
        self.setupUi(self)
        pos = parent.pos()
        self.move(pos + QtCore.QPoint(5,5))
