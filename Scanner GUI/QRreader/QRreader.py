import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import time 
from array import array
import pyqtgraph as pg
import numpy
import decimal #required for more digits
from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView
import threading
from scipy.signal import detrend


path = sys.path[0] 
sys.path.append(path+'\Resources')
QRreaderWindowUI, QtBaseClass = uic.loadUiType(path + r"\QRreader\QRreaderWindow.ui")

class Window(QtGui.QMainWindow, QRreaderWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.pushButton_qrcode00.clicked.connect(lambda: self.toggleqrcode((0,0),self.pushButton_qrcode00))
        self.pushButton_qrcode01.clicked.connect(lambda: self.toggleqrcode((0,1),self.pushButton_qrcode01))
        self.pushButton_qrcode02.clicked.connect(lambda: self.toggleqrcode((0,2),self.pushButton_qrcode02))
        self.pushButton_qrcode03.clicked.connect(lambda: self.toggleqrcode((0,3),self.pushButton_qrcode03))
        self.pushButton_qrcode10.clicked.connect(lambda: self.toggleqrcode((1,0),self.pushButton_qrcode10))
        self.pushButton_qrcode11.clicked.connect(lambda: self.toggleqrcode((1,1),self.pushButton_qrcode11))
        self.pushButton_qrcode12.clicked.connect(lambda: self.toggleqrcode((1,2),self.pushButton_qrcode12))
        self.pushButton_qrcode13.clicked.connect(lambda: self.toggleqrcode((1,3),self.pushButton_qrcode13))
        self.pushButton_qrcode20.clicked.connect(lambda: self.toggleqrcode((2,0),self.pushButton_qrcode20))
        self.pushButton_qrcode21.clicked.connect(lambda: self.toggleqrcode((2,1),self.pushButton_qrcode21))
        self.pushButton_qrcode22.clicked.connect(lambda: self.toggleqrcode((2,2),self.pushButton_qrcode22))
        self.pushButton_qrcode23.clicked.connect(lambda: self.toggleqrcode((2,3),self.pushButton_qrcode23))
        self.pushButton_qrcode30.clicked.connect(lambda: self.toggleqrcode((3,0),self.pushButton_qrcode30))
        self.pushButton_qrcode31.clicked.connect(lambda: self.toggleqrcode((3,1),self.pushButton_qrcode31))
        self.pushButton_qrcode32.clicked.connect(lambda: self.toggleqrcode((3,2),self.pushButton_qrcode32))
        self.pushButton_qrcode33.clicked.connect(lambda: self.toggleqrcode((3,3),self.pushButton_qrcode33))
        
        self.lineEdit_Xpositioncenter.editingFinished.connect(self.UpdateCenterX)
        self.lineEdit_Ypositioncenter.editingFinished.connect(self.UpdateCenterY)
        
        self.CenterX=83
        self.CenterY=83
        self.TotalX=166
        self.TotalY=166
        self.QRpictureX=200
        self.QRpictureY=200
        self.lineEdit_Xpositioncenter.setText(str(self.CenterX))
        self.lineEdit_Ypositioncenter.setText(str(self.CenterY))

        
        self.fill=numpy.zeros((4,4))
        
        #self.pushButton_Gotobutton.clicked.connect(self.GoTo)    #Obsolete
        self.pushButton_SetupCenter.clicked.connect(self.SetupCenter)

        self.moveDefault()

        #Connect show servers list pop up
        
        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None

    def moveDefault(self):
        self.move(550,10)

        
        
    def Updateposition(self):
        self.xposition=int(self.fill[0,0])*2**7+int(self.fill[0,1])*2**6+int(self.fill[0,2])*2**5+int(self.fill[0,3])*2**4+int(self.fill[1,0])*2**3+int(self.fill[1,1])*2**2+int(self.fill[1,2])*2**1+int(self.fill[1,3])*2**0
        #This convert the QR code to the integer it correspond to
        valx=formatNum(self.inttonum(self.xposition)-float(decimal.Decimal(self.CenterX*30)/decimal.Decimal(10**6)))
        self.lineEdit_Xposition.setText(valx)
        self.yposition=int(self.fill[2,0])*2**7+int(self.fill[2,1])*2**6+int(self.fill[2,2])*2**5+int(self.fill[2,3])*2**4+int(self.fill[3,0])*2**3+int(self.fill[3,1])*2**2+int(self.fill[3,2])*2**1+int(self.fill[3,3])*2**0
        valy=formatNum(self.inttonum(self.yposition)-float(decimal.Decimal(self.CenterY*30)/decimal.Decimal(10**6)))
        self.lineEdit_Yposition.setText(valy)

    def colorButton(self, button, fill):
        fillstatus ="background-color: red;color:black"
        notfillstatus = "background-color: rgb(230,230,230);color:grey"
        if fill:
            button.setStyleSheet(fillstatus)
        else:
            button.setStyleSheet(notfillstatus)
            # This just change the color of the button

    def colorAllButton(self):
        for i in range(0,4):
            for j in range (0,4):
                Status=self.fill[i,j]
                self.colorButton(eval("self.pushButton_qrcode"+str(i)+str(j)),Status)
                #this change the color of all the button

    def numtoint(self,num):
        val=int((num*10**6)/30.0)
        return val
        #convert the distance to the actual number

    def inttonum(self,int):
        val=float(decimal.Decimal(int*30)/decimal.Decimal((10**6)))
        return val
        #convert the number to the actual distance
        
    def GoTo(self):
        if self.lineEdit_Xposition.text()=="SQUID":
            print("yes")
            self.ASQUID()
        else:  
            valx=readNum(str(self.lineEdit_Xposition.text()),self)
            valy=readNum(str(self.lineEdit_Yposition.text()),self)#read the position from entered value
            x = self.numtoint(valx)
            y = self.numtoint(valy)
            xbinaryarray=list('{0:08b}'.format(x))
            ybinaryarray=list('{0:08b}'.format(y))
            for i in range(0, 2):
                for j in range(0,4):
                    self.fill[i,j]=xbinaryarray[i*4+j]
            for i in range(2, 4):
                for j in range(0,4):
                    self.fill[i,j]=ybinaryarray[(i-2)*4+j]
            self.Updateposition()
            self.colorAllButton()
            self.UpdateTipTF()

    def SetupCenter(self):
        self.CenterX=int(self.fill[0,0])*2**7+int(self.fill[0,1])*2**6+int(self.fill[0,2])*2**5+int(self.fill[0,3])*2**4+int(self.fill[1,0])*2**3+int(self.fill[1,1])*2**2+int(self.fill[1,2])*2**1+int(self.fill[1,3])*2**0
        self.CenterY=int(self.fill[2,0])*2**7+int(self.fill[2,1])*2**6+int(self.fill[2,2])*2**5+int(self.fill[2,3])*2**4+int(self.fill[3,0])*2**3+int(self.fill[3,1])*2**2+int(self.fill[3,2])*2**1+int(self.fill[3,3])*2**0
        self.TotalX=2*self.CenterX
        self.TotalY=2*self.CenterY#read the configuration of QRCode
        self.lineEdit_Xpositioncenter.setText(str(self.CenterX))
        self.lineEdit_Ypositioncenter.setText(str(self.CenterY))
        self.Updateposition()
        self.UpdateTipTF()
        
    def UpdateCenterX(self):
        new_CenterX=readNum(self.lineEdit_Xpositioncenter.text(),self,False)
        if new_CenterX>0 and new_CenterX<129 and isinstance(new_CenterX, float):
            self.CenterX=int(str(self.lineEdit_Xpositioncenter.text()))
            self.TotalX=2*self.CenterX
        self.lineEdit_Xpositioncenter.setText(str(self.CenterX))
        self.Updateposition()
        self.UpdateTipTF()


        
    def UpdateCenterY(self):
        new_CenterY=readNum(self.lineEdit_Ypositioncenter.text(),self,False)
        if new_CenterY>0 and new_CenterY<129 and isinstance(new_CenterY, float):
            self.CenterY=int(str(self.lineEdit_Ypositioncenter.text()))
            self.TotalY=2*self.CenterY
        self.lineEdit_Ypositioncenter.setText(str(self.CenterY))
        self.Updateposition()
        self.UpdateTipTF()


    def setupAdditionalUi(self):
    #Set up UI that isn't easily done from Qt Designer
        pass
            
    # Below function is not necessary, but is often useful. Yielding it will provide an asynchronous 
    # delay that allows other labrad / pyqt methods to run   
    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
        
    def toggleqrcode(self, location, button):
        if self.fill[location] == False:
            self.fill[location] = True
            self.colorButton(button, True)
        else:
            self.fill[location] = False
            self.colorButton(button, False)
        self.Updateposition()
        x = readNum((self.lineEdit_Xposition.text()),self)
        y = readNum((self.lineEdit_Yposition.text()),self)
        self.UpdateTipTF()

    def UpdateTipTF(self):
        W=float(self.Frame_Minimap.width())#specific to picture
        H=self.Frame_Minimap.height()#specific to picture
        Length=float(H)*11/12#specific to picture
        x = readNum(str(self.lineEdit_Xposition.text()),self)
        y = readNum(str(self.lineEdit_Yposition.text()),self)
        self.Frame_TFTP.move(int(x/(self.TotalX*30)*(10**6)*Length+W/2-70),int(-y/(self.TotalY*30)*(10**6)*Length-60+Length/2))#formula is empirical
        self.Frame_TFTP.raise_()

    def ASQUID(self):
        print("hey")
        style = '''
                {
                image:url(:/nSOTScanner/Pictures/SQUIDRotated.png);
                background:black;
                }
                '''
        defaultstyle=self.centralwidget.styleSheet()
        self.centralwidget.setStyleSheet(style)

        yield self.sleep(1)
        self.centralwidget.setStyleSheet(defaultstyle)
        
        
        
        
            
#----------------------------------------------------------------------------------------------#         
    """ The following section has generally useful functions."""
           
    def lockInterface(self):
        pass
        
    def unlockInterface(self):
        pass

if __name__=="__main__":
    import qt4reactor
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install()
    from twisted.internet import reactor
    window = Window(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
