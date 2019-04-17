#---------------------------------------------------------------------------------------------------------#         
""" The following section describes how to read and write values to various lineEdits on the GUI."""

import numpy as np
from itertools import product

def formatNum(val, decimal_values = 2):
    if val != val:
        return 'nan'
        
    string = '%e'%val
    ind = string.index('e')
    num  = float(string[0:ind])
    exp = int(string[ind+1:])
    if exp < -6:
        diff = exp + 9
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'n'
    elif exp < -3:
        diff = exp + 6
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'u'
    elif exp < 0:
        diff = exp + 3
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'m'
    elif exp < 3:
        if val - int(val) == 0:
            val = int(val)
        else: 
            val = round(val,decimal_values)
        string = str(val)
    elif exp < 6:
        diff = exp - 3
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'k'
    elif exp < 9:
        diff = exp - 6
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'M'
    elif exp < 12:
        diff = exp - 9
        num = num * 10**diff
        if num - int(num) == 0:
            num = int(num)
        else: 
            num = round(num,decimal_values)
        string = str(num)+'G'
    return string
    
#By default, accepts no parent and will warn you for inputting a number without units. 
#Adding a parent is needed to have error thrown in a reasonable place and avoid recursion errors. 
#For entries that are expected to be of order unity the warningFlag can be set to False. 
def readNum(string, parent, warningFlag = True):
    try:
        val = float(string)
        
        if warningFlag and val != 0:
            warning = UnitWarning(parent, val)
            parent.setFocus()
            if warning.exec_():
                pass
            else:
                return 'Rejected Input'
    except:
        try:
            exp = string[-1]
            if exp == 'm':
                exp = 1e-3
            if exp == 'u':
                exp = 1e-6
            if exp == 'n':
                exp = 1e-9
            if exp == 'p':
                exp = 1e-12
            if exp == 'k':
                exp = 1e3
            if exp == 'M':
                exp = 1e6
            if exp == 'G':
                exp = 1e9
            try:
                val = float(string[0:-1])*exp
            except: 
                return 'Incorrect Format'
        except:
            return 'Empty Input'
    return val
        
#---------------------------------------------------------------------------------------------------------#         
""" The following section creates a generic warning if a numebr is input without a unit."""
        
from PyQt4 import QtGui, QtCore, uic
import sys

path = sys.path[0] + r"\Resources"
Ui_UnitWarning, QtBaseClass = uic.loadUiType(path + r"\UnitWarningWindow.ui")
        
class UnitWarning(QtGui.QDialog, Ui_UnitWarning):
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
        
        print "Print A: ", A
        print "Print B: ", B

        coeff, r, rank, s = np.linalg.lstsq(A, B)
        print "Print coeff: ", coeff
        
        for i in xrange(length):
            for j in xrange(width):
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

        for i in xrange(length):
            for j in xrange(width):
                image[j][i] = image[j][i] - np.dot(coeff, [1, x[j], y[i], x[j]**2, y[i]**2, x[j]*y[i]])    
        
        return image

    elif process == 'Subtract Line Quadratic':
        for i in range(0,length):
            image[:,i] = processLineData(image[:,i],'Subtract Parabolic Fit')
        return image
        
#---------------------------------------------------------------------------------------------------------#         
""" The following section creates a better image plotted, based off of pyqt's ImageView, to allow plotting of partial images."""
    
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
        