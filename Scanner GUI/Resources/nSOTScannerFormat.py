#---------------------------------------------------------------------------------------------------------#         
""" The following section describes how to read and write values to various lineEdits on the GUI."""

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
    return val