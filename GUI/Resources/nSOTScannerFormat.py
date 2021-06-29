import numpy as np
import itertools
import sys

'''Function that prints the error information in a standard way across the software with the relevant
information in a reasonable format'''

def printErrorInfo():
    type, inst, tb = sys.exc_info()
    print("Error: ", inst)
    print("Occured at line: ", tb.tb_lineno)
    print("In the file: ", tb.tb_frame.f_code.co_filename)

def saveDataToSessionFolder(window, folder, filename):
    try:
        app = QtWidgets.QApplication.instance()
        pixmap = QtGui.QScreen.grabWindow(app.primaryScreen(), window.winId())
        pixmap.save(folder + '\\' + filename + '.jpg','jpg')
    except:
        printErrorInfo()

#---------------------------------------------------------------------------------------------------------#
""" The following section describes how to read and write values to various lineEdits on the GUI."""

siDict = {'T': 12, 'G' : 9, 'M' : 6, 'k' : 3, '' : 0, 'm' : -3, 'u' : -6, 'n' : -9, 'p' : -12}

def get_key(val):
    for key, value in siDict.items(): #in python 3, switch to items.
         if val == value:
             return key
    return "key doesn't exist"

def formatNum(val, decimal_values = 2):
    if val != val:
        return 'nan'

    string = '%e'%val
    ind = string.index('e')
    num  = float(string[0:ind])
    exp = int(string[ind+1:])

    #Get power of 3 index
    si = exp-exp%3
    if si < -12:
        si = -12
    elif si > 12:
        si = 12

    num = num * 10**(exp - si)

    if num - int(num) == 0:
        num = int(num)
    else:
        num = round(num,decimal_values)

    string = str(num)+get_key(si)

    return string

#By default, accepts no parent and will not warn you for inputting a number without units.
#Adding a parent is needed to have error thrown in a reasonable place and avoid recursion errors
#associated with changing GUI element focus.
#For entries where the unit is critical (ie, scan range of 10 um instead of 10 m), it is suggested
#that the parent module is input and the warningFlag is set to True.
def readNum(string, parent = None, warningFlag = False):
    try:
        val = float(string)

        if not parent is None and warningFlag and val != 0:
            warning = UnitWarning(parent, val)
            parent.setFocus()
            if warning.exec_():
                pass
            else:
                return 'Rejected Input'
    except:
        try:
            exp = siDict[string[-1]]
            try:
                val = float(string[0:-1])*10**exp
            except:
                return 'Incorrect Format'
        except:
            return 'Empty Input'
    return val

#---------------------------------------------------------------------------------------------------------#
""" The following section creates a generic warning if a number is input without a unit."""

from PyQt5 import QtGui, QtWidgets, uic
import sys

path = sys.path[0] + r"\Resources"
Ui_UnitWarning, QtBaseClass = uic.loadUiType(path + r"\UnitWarningWindow.ui")

class UnitWarning(QtWidgets.QDialog, Ui_UnitWarning):
    def __init__(self, parent, val):
        super(UnitWarning, self).__init__(parent)
        self.window = parent
        self.setupUi(self)

        self.label.setText(self.label.text() + formatNum(val) + '.')

        self.push_yes.clicked.connect(self.acceptEntry)
        self.push_no.clicked.connect(self.rejectEntry)

    def acceptEntry(self):
        self.accept()

    def rejectEntry(self):
        self.reject()

    def closeEvent(self, e):
        self.reject()

#---------------------------------------------------------------------------------------------------------#
""" The following section has basic data processing methods."""

def processLineData(lineData, process):
    pixels = np.size(lineData)
    if process == 'Raw':
        return lineData
    elif process == 'Subtract Average':
        x = np.linspace(0,pixels-1,pixels)
        fit = np.polyfit(x, lineData, 0)
        residuals  = lineData - fit[0]
        return residuals
    elif process == 'Subtract Linear Fit':
        x = np.linspace(0,pixels-1,pixels)
        fit = np.polyfit(x, lineData, 1)
        residuals  = lineData - fit[0]*x - fit[1]
        return residuals
    elif process == 'Subtract Parabolic Fit':
        x = np.linspace(0,pixels-1,pixels)
        fit = np.polyfit(x, lineData, 2)
        residuals  = lineData - fit[0]*x**2 - fit[1]*x - fit[2]
        return residuals

def processImageData(image, process):
    shape = np.shape(image)

    width = int(shape[0])
    length = int(shape[1])

    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, length)
    X, Y = np.meshgrid(x, y, copy=False)

    X = X.flatten()
    Y = Y.flatten()

    if process == 'Raw':
        return image

    elif process == 'Subtract Image Average':
        avg = np.average(image)
        return image - avg

    elif process == 'Subtract Line Average':
        for i in range(0,length):
            image[:,i] = processLineData(image[:,i],'Subtract Average')
        return image

    elif process == 'Subtract Image Plane':
        A = np.array([X*0+1, X, Y]).T
        B = image.flatten('F')

        print("Print A: ", A)
        print("Print B: ", B)

        coeff, r, rank, s = np.linalg.lstsq(A, B)
        print("Print coeff: ", coeff)

        for i in range(length):
            for j in range(width):
                image[j][i] = image[j][i] - np.dot(coeff, [1, x[j], y[i]])
        return image

    elif process == 'Subtract Line Linear':
        for i in range(0,length):
            image[:,i] = processLineData(image[:,i],'Subtract Linear Fit')
        return image

    elif process == 'Subtract Image Quadratic':
        A = np.array([X*0+1, X, Y, X**2, Y**2, X*Y]).T
        B = image.flatten('F')

        coeff, r, rank, s = np.linalg.lstsq(A, B)

        for i in range(length):
            for j in range(width):
                image[j][i] = image[j][i] - np.dot(coeff, [1, x[j], y[i], x[j]**2, y[i]**2, x[j]*y[i]])

        return image

    elif process == 'Subtract Line Quadratic':
        for i in range(0,length):
            image[:,i] = processLineData(image[:,i],'Subtract Parabolic Fit')
        return image

#---------------------------------------------------------------------------------------------------------#
""" The following section has the function for performing a numerical derivative of a 1D dataset using a
    lanczos algorithm"""

def deriv(Data, x, NumberOfSide, delta, order = 1, EdgeNumber = 10):
	NumberOfSide = int(NumberOfSide)
	EdgeNumber = int(EdgeNumber)
	order = int(order)
	denom = NumberOfSide * (NumberOfSide + 1) * (2*NumberOfSide + 1)#denominator for the weight
	k = np.arange(1, 2*(NumberOfSide + 1))
	lanc = (3  * k) / (denom * delta)#weight
	df0 = []
	df1 = []
	df = [sum(lanc[j-1]*(Data[i+j] - Data[i-j]) for j in range(1, NumberOfSide + 1)) for i in range(NumberOfSide, len(Data) - NumberOfSide)]
	first_dats = Data[0: EdgeNumber]
	last_dats = Data[len(Data) - EdgeNumber: len(Data)]
	first_fit = np.polyfit(x[0: EdgeNumber], first_dats, order)
	last_fit = np.polyfit(x[len(Data) - EdgeNumber: len(Data)], last_dats, order)
	for i in range(0, NumberOfSide):
		deriv = 0
		for j in range(order):
			deriv += first_fit[j] * x[i] ** (order - j - 1 ) * (order - j)
		df0.append(deriv)
	for i in range(len(Data) - NumberOfSide, len(Data)):
		deriv = 0
		for j in range(order):
			deriv += last_fit[j] * x[i] ** (order - j - 1 ) * (order - j)
		df1.append(deriv)

	return list(itertools.chain(df0, df, df1))

#---------------------------------------------------------------------------------------------------------#
""" The following section creates a better image plotter, based off of pyqt's ImageView, to allow plotting of partial images."""

import pyqtgraph as pg

class ScanImageView(pg.ImageView):
    '''
    Extension of pyqtgraph's ImageView. This allows you to plot only part of a dataset. This works by specifying a "random filling" number which,
    if found during plotting, is ignored from both the plotting and the histogram.
    '''
    def __init__(self, parent=None, name="ImageView", view=None, imageItem=None, randFill = 0.0, *args):
        pg.ImageView.__init__(self, parent, name, view, imageItem, *args)
        #Rand fill is the number that gets thrown out of the dataset
        self.randFill = randFill

    def setImage(self, img, autoRange = False, autoLevels = False, levels=None, axes=None, xvals=None, pos=None, scale=None, transform=None, autoHistogramRange=True):
        r0 = np.where(np.all(img == self.randFill, axis = 0))[0]
        c0 = np.where(np.all(img == self.randFill, axis = 1))[0]
        tmp = np.delete(np.delete(img, r0, axis = 1), c0, axis = 0)
        #If nothing is left, don't plot anything
        if np.size(tmp) != 0:
            pg.ImageView.setImage(self, tmp, autoRange, autoLevels, levels, axes, xvals, pos, scale, transform, False)
        else:
            #Clear plot if nothing is being plotted
            pg.ImageView.clear(self)
            self.ui.histogram.plot.clear()

        #Autoscales histogram x axis, making sure we can always see the peaks of the histogram
        self.ui.histogram.vb.enableAutoRange(axis = pg.ViewBox.XAxis, enable = True)

        if autoHistogramRange:
            self.ui.histogram.vb.autoRange()

    def setRandFill(self, val):
        self.randFill = val

    def autoRange(self):
        #Redefine this function because in the pyqtgraph version, for some unknown reason, it also calls getProcessedImage, which causes bugs when nothing
        #is being plotted.
        self.view.enableAutoRange()

    #Eventually also add the following from Avi's code so that if we're plotting point by point (instead of line by line) the histogram doesn't get populated
    '''
    def updateHist(self, autoLevel=False, autoRange=False):
        histTmp = self.tmp - self.randFill
        w = np.absolute(np.divide(histTmp, histTmp, out = np.zeros_like(histTmp), where = histTmp != 0))
        step = (int(np.ceil(w.shape[0] / 200)),
                    int(np.ceil(w.shape[1] / 200)))
        if np.isscalar(step):
            step = (step, step)
        stepW = w[::step[0], ::step[1]]
        stepW = stepW[np.isfinite(stepW)]
        h = self.mainImage.getHistogram(weights = stepW)
        if h[0] is None:
            return
        self.mainPlot.ui.histogram.plot.setData(*h)
        if autoLevel:
            mn = h[0][0]
            mx = h[0][-1]
            self.mainPlot.ui.histogram.region.setRegion([mn, mx])
    '''
