#Written by Marec, Avi and Raymond
import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from twisted.internet.defer import inlineCallbacks, Deferred
from nSOTScannerFormat import readNum, formatNum, printErrorInfo

path = sys.path[0] + r"\PlottingModule"
sys.path.append(sys.path[0] + r'\DataVaultBrowser')

ui_path = sys.path[0] + r"\PlottingModule\UI Files"
Ui_CommandCenter, QtBaseClass = uic.loadUiType(ui_path + r"\PlottingModule.ui")
Ui_SettingsWindow, QtBaseClass = uic.loadUiType(ui_path + r"\PlottingModuleSettings.ui")

from . import plotter
import dirExplorer

'''
General structure of the plotting modules
The main window, called the command center, has a UI for opening datasets.
Each dataset is opened into its own window and object, called a Plotter.
All the Plotter objects are kept in a list and displayed in the command center GUI.
'''

class CommandCenter(QtWidgets.QMainWindow, Ui_CommandCenter):
    def __init__(self, reactor, parent = None):
        super(CommandCenter, self).__init__(parent)
        self.reactor = reactor
        self.parent = parent
        self.setupUi(self)

        #Dictionary of default plotting settings
        self.defaultSettings = {
            'scanPlot_realPosition': True, #If true, when 2D scan data is plotted, the piezo voltages are converted to displacements in um
            'scanPlot_scalefactor': 5.36, #Conversion from volts to um. 1V = 5.36 um
            'scanPlot_offset': 0, #Include an offset when converting to position. Formula is x (meters) = V (volts) * scalefactor (um / V) + offset (um)
        }

        #Initialize list that dynamically updates with all the Plotter objects
        self.plotterList = []

        #Connect button to open new plot
        self.pushButton_newPlotter.clicked.connect(lambda: self.openDataVaultFiles()) #Connect button to open a new dataset

        #Connect button to open setting window
        self.pushButton_settings.clicked.connect(self.openSettingsWindow)

        #Initialize module without a labRAD connection and with a locked interface
        self.disconnectLabRAD()

#----------------------------------------------------------------------------------------------#
    """ The following section has standard server connection and GUI functions"""

    @inlineCallbacks
    def connectLabRAD(self, dict):
        try:
            self.gen_cxn = dict['servers']['local']['cxn']
            self.gen_dv = dict['servers']['local']['dv']

            from labrad.wrappers import connectAsync
            self.cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')
            self.dv = yield self.cxn.data_vault

            self.dvBrowser = dirExplorer.dataVaultExplorer(self.dv, self.reactor)
            self.dvBrowser.accepted.connect(lambda: self.openFilesInPlotter(self.dvBrowser.file, self.dvBrowser.directory))

            self.unlockInterface()
        except:
            pass

    def disconnectLabRAD(self):
        self.gen_cxn = False
        self.cxn = False
        self.gen_dv = False
        self.dv = False
        self.lockInterface()

    def moveDefault(self):
        self.move(10,170)

    def lockInterface(self):
        self.pushButton_newPlotter.setEnabled(False)
        self.pushButton_settings.setEnabled(False)

    def unlockInterface(self):
        self.pushButton_newPlotter.setEnabled(True)
        self.pushButton_settings.setEnabled(True)

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for updating the Plotter module UI"""

    def refreshPlotList(self):
        try:
            self.listWidget_Plots.clear()

            for plot in self.plotterList:
                item = QtWidgets.QListWidgetItem()
                self.formatListWidgetItem(item, plot)
                self.listWidget_Plots.addItem(item)

        except Exception as inst:
            printErrorInfo()

    def formatListWidgetItem(self, ListWidgetItem, plotter):
        try:
            Text = plotter.dataInfoDict['title']
            ListWidgetItem.setText(Text)

            #Define colors for various GUI elements
            Color_NoData = [QtGui.QColor(131, 131, 131), QtGui.QColor(0, 0, 0)]
            Color_ContainData = [QtGui.QColor(0, 0, 0), QtGui.QColor(100, 100, 100)]

            #Check if the plotter has data. It may not if the datavault file opened did not contain
            #any data
            if not plotter.data is None: #If yes, set the text color appropriately
                ListWidgetItem.setForeground(Color_ContainData[0])
                ListWidgetItem.setBackground(Color_ContainData[1])
            else: #If no, set text to a different color and set tooltip indicating to the user that there's no data
                ListWidgetItem.setForeground(Color_NoData[0])
                ListWidgetItem.setBackground(Color_NoData[1])
                ListWidgetItem.setToolTip('No Data Loaded')
        except Exception as inst:
            printErrorInfo()

    def removePlot(self, plotter):
        self.plotterList.remove(plotter) #Remove the plotter from the plotterlist
        self.refreshPlotList() #refresh the plotlist

    def keyPressEvent(self, event):
        #When the backspace or delete key is pressed, close the selected Plotters
        if event.key() == QtCore.Qt.Key_Delete or event.key() == QtCore.Qt.Key_Backspace:
            itemlist = self.listWidget_Plots.selectedItems() #List of selected items in listWidget
            if not itemlist is None:
                index = [] #Create list of indices of the list items
                for item in itemlist:
                    index.append(self.listWidget_Plots.indexFromItem(item).row())
                index.sort(reverse = True) #Close the plotters in reverse order so that their indices don't change as plots are removed
                for ind in index:
                    self.plotterList[ind].close()

            self.refreshPlotList()

#----------------------------------------------------------------------------------------------#
    """ The following section has functions for opening datasets"""

    def openDataVaultFiles(self):
        try:
            #First open a data vault browser to allow the user to select the files
            self.dvBrowser.popDirs()
            self.dvBrowser.show()
        except Exception as inst:
            printErrorInfo()

    def openFilesInPlotter(self, filelist, directory):
        for file in filelist:
            try:
                #Plotters are indexed by a number. Whenever creating a new plotter, give it the
                #lowest available number starting from 0
                plt_num = 0
                while True:
                    if plt_num not in [item.number for item in self.plotterList]:
                        break
                    plt_num +=1

                #Create a new plotter for the provided file passing along the default settings
                new_plotter = plotter.Plotter(file, directory, self.defaultSettings, plt_num, self)

                new_plotter.plotInfoChanged.connect(self.refreshPlotList) #When the information (namely, the title) of the plot is changed, refresh the plot list
                new_plotter.plotClosed.connect(self.removePlot) #If the plotter is closed, remove it from the plotters list

                self.plotterList.append(new_plotter) #Add plotter to the list

                self.refreshPlotList() #Refresh the plot list UI

            except Exception as inst:
                printErrorInfo()

#----------------------------------------------------------------------------------------------#
    """ The following section has the functions for opening the settings window"""

    def openSettingsWindow(self):
        '''
        Opens the plotter settings window, giving it the defaultSettings dictionary.
        If changes are accepted, then the general settings dictionary is updated with the
        new values.
        '''
        defSet = settingsWindow(self.defaultSettings.copy(), parent = self)
        if defSet.exec_():
            self.defaultSettings = defSet.getValues()

    def sleep(self, secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

class settingsWindow(QtWidgets.QDialog, Ui_SettingsWindow):
    def __init__(self, settings, parent = None):
        super(settingsWindow, self).__init__(parent)

        self.setupUi(self)

        self.plotSettings = settings

        #Load the current values into the setting window UI
        self.lineEdit_ScaleFactor.setText(formatNum(self.plotSettings['scanPlot_scalefactor'], 6))
        self.lineEdit_Offset.setText(formatNum(self.plotSettings['scanPlot_offset'], 6))
        self.checkBox_realUnit.setChecked(self.plotSettings['scanPlot_realPosition'])

        #Connect UI elements for updating the settings
        self.lineEdit_ScaleFactor.editingFinished.connect(lambda: self.updateParameter('scanPlot_scalefactor', self.lineEdit_ScaleFactor))
        self.lineEdit_Offset.editingFinished.connect(lambda: self.updateParameter('scanPlot_offset', self.lineEdit_Offset))
        self.checkBox_realUnit.stateChanged.connect(self.updateCheckBox)

        #Accept the changes if the accept button is clicked
        self.pushButton_accept.clicked.connect(self.accept)

    def updateParameter(self, key, lineEdit):
        val = readNum(str(lineEdit.text()))
        if isinstance(val, float):
                self.plotSettings[key] = val
        lineEdit.setText(formatNum(self.plotSettings[key], 6))

    def updateCheckBox(self):
        self.plotSettings['scanPlot_realPosition'] = self.checkBox_realUnit.isChecked()

    def getValues(self):
        return self.plotSettings
