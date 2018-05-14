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
    
def readNum(string):
    try:
        val = float(string)
    except:
        try:
            exp = string[-1]
            if exp == 'm':
                exp = 1e-3
            if exp == 'u':
                exp = 1e-6
            if exp == 'n':
                exp = 1e-9
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
    
    width = int(shape[1])
    length = int(shape[0])
    
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
        B = image.flatten()

        coeff, r, rank, s = np.linalg.lstsq(A, B)

        for i in xrange(length):
            for j in xrange(width):
                image[i][j] = image[i][j] - np.dot(coeff, [1, x[j], y[i]])	
        return image
   
    elif process == 'Subtract Line Linear':
        for i in range(0,length):
            image[:,i] = processLineData(image[:,i],'Subtract Linear Fit')
        return image

    elif process == 'Subtract Image Quadratic':
        A = np.array([X*0+1, X, Y, X**2, Y**2, X*Y]).T
        B = image.flatten()

        coeff, r, rank, s = np.linalg.lstsq(A, B)

        for i in xrange(length):
            for j in xrange(width):
                image[i][j] = image[i][j] - np.dot(coeff, [1, x[j], y[i], x[j]**2, y[i]**2, x[j]*y[i]])	
        
        return image

    elif process == 'Subtract Line Quadratic':
        for i in range(0,length):
            image[:,i] = processLineData(image[:,i],'Subtract Parabolic Fit')
        return image

