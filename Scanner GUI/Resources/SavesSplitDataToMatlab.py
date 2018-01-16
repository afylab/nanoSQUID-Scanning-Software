#import csv
import scipy.io as sio
import labrad
import numpy as np

cxn = labrad.connect()
dv = cxn.data_vault

directory = ''
file_number = '00153'
file_header = 'nSOT Scan Data'
file_name = 'unnamed'
folder_name = 'C:\Users\cltschirhart\Data Sets\SSAA Windings\\C4'
file = file_number + ' - ' + file_header + ' ' + file_name

dv.cd(directory)
dv.open(file)
Data = dv.get()
print 'Got data.'

Data = np.asarray(Data)
trace = Data[Data[:,0] == 0]
retrace = Data[Data[:,0] == 1]

savename = folder_name + '\\d' +file_number

print 'All data converted. Saving .mat file'
sio.savemat(savename + 'trace.mat',{'d'+file_number + 'trace':trace})
sio.savemat(savename + 'retrace.mat',{'d'+file_number + 'retrace':retrace})






