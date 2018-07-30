import sys
from PyQt4 import QtGui, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import time 
from array import array
import numpy
from nSOTScannerFormat import readNum, formatNum, processLineData, processImageData, ScanImageView


path = sys.path[0] 
sys.path.append(path+'\Resources')
QRreaderWindowUI, QtBaseClass = uic.loadUiType(path + r"\QRreader\QRreaderWindow.ui")

class Window(QtGui.QMainWindow, QRreaderWindowUI):
    def __init__(self, reactor, parent=None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        self.PushBotton_qrcode00.clicked.connect(lambda: self.toggleqrcode((0,0),self.PushBotton_qrcode00))
        self.PushBotton_qrcode01.clicked.connect(lambda: self.toggleqrcode((0,1),self.PushBotton_qrcode01))
        self.PushBotton_qrcode02.clicked.connect(lambda: self.toggleqrcode((0,2),self.PushBotton_qrcode02))
        self.PushBotton_qrcode03.clicked.connect(lambda: self.toggleqrcode((0,3),self.PushBotton_qrcode03))
        self.PushBotton_qrcode10.clicked.connect(lambda: self.toggleqrcode((1,0),self.PushBotton_qrcode10))
        self.PushBotton_qrcode11.clicked.connect(lambda: self.toggleqrcode((1,1),self.PushBotton_qrcode11))
        self.PushBotton_qrcode12.clicked.connect(lambda: self.toggleqrcode((1,2),self.PushBotton_qrcode12))
        self.PushBotton_qrcode13.clicked.connect(lambda: self.toggleqrcode((1,3),self.PushBotton_qrcode13))
        self.PushBotton_qrcode20.clicked.connect(lambda: self.toggleqrcode((2,0),self.PushBotton_qrcode20))
        self.PushBotton_qrcode21.clicked.connect(lambda: self.toggleqrcode((2,1),self.PushBotton_qrcode21))
        self.PushBotton_qrcode22.clicked.connect(lambda: self.toggleqrcode((2,2),self.PushBotton_qrcode22))
        self.PushBotton_qrcode23.clicked.connect(lambda: self.toggleqrcode((2,3),self.PushBotton_qrcode23))
        self.PushBotton_qrcode30.clicked.connect(lambda: self.toggleqrcode((3,0),self.PushBotton_qrcode30))
        self.PushBotton_qrcode31.clicked.connect(lambda: self.toggleqrcode((3,1),self.PushBotton_qrcode31))
        self.PushBotton_qrcode32.clicked.connect(lambda: self.toggleqrcode((3,2),self.PushBotton_qrcode32))
        self.PushBotton_qrcode33.clicked.connect(lambda: self.toggleqrcode((3,3),self.PushBotton_qrcode33))
        
        self.fill=numpy.zeros((4,4))
        
        self.PushBotton_Gotobutton.clicked.connect(self.GoTo)

        self.moveDefault()

        #Connect show servers list pop up
        
        #Initialize all the labrad connections as none
        self.cxn = None
        self.dv = None

    def moveDefault(self):
        self.move(550,10)
        
    def Updateposition(self):
        self.xposition=int(self.fill[0,0])*2**7+int(self.fill[0,1])*2**6+int(self.fill[0,2])*2**5+int(self.fill[0,3])*2**4+int(self.fill[1,0])*2**3+int(self.fill[1,1])*2**2+int(self.fill[1,2])*2**1+int(self.fill[1,3])*2**0
        valx=formatNum(self.inttonum(self.xposition))
        self.LineEdit_Xposition.setText(valx)
        self.yposition=int(self.fill[2,0])*2**7+int(self.fill[2,1])*2**6+int(self.fill[2,2])*2**5+int(self.fill[2,3])*2**4+int(self.fill[3,0])*2**3+int(self.fill[3,1])*2**2+int(self.fill[3,2])*2**1+int(self.fill[3,3])*2**0
        valy=formatNum(self.inttonum(self.yposition))
        self.LineEdit_Yposition.setText(valy)

    def colorButton(self, button, fill):
        fillstatus ="background-color: red;color:black"
        notfillstatus = "background-color: rgb(230,230,230);color:grey"
        if fill:
            button.setStyleSheet(fillstatus)
        else:
            button.setStyleSheet(notfillstatus)

    def colorAllButton(self):
        for i in range(0,4):
            for j in range (0,4):
                Status=self.fill[i,j]
                self.colorButton(eval("self.PushBotton_qrcode"+str(i)+str(j)),Status)
            
#    def Updatedistancetocenter(self):
#        x = readNum(str(self.LineEdit_Xposition.text()),self)
#        y = readNum(str(self.LineEdit_Yposition.text()),self)
#        self.LineEdit_Xposition.setText(formatNum(x-127.5*30/(10**6)))
#        self.LineEdit_Yposition.setText(formatNum(y-127.5*30/(10**6)))

    def numtoint(self,num):
        val=int((num*10**6)/30.0+127.5)
        return val

    def inttonum(self,int):
        val=float((int*30-127.5*30)/(10**6))
        return val
        
        
    def GoTo(self):
        if self.LineEdit_Xposition.text()=="SQUID":
            print("yes")
            self.ASQUID()
        else:  
            valx=readNum(str(self.LineEdit_Xposition.text()),self)
            valy=readNum(str(self.LineEdit_Yposition.text()),self)
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
        x = readNum((self.LineEdit_Xposition.text()),self)
        y = readNum((self.LineEdit_Yposition.text()),self)
        self.UpdateTipTF()

    def UpdateTipTF(self):
        W=float(self.Frame_Minimap.width())
        H=self.Frame_Minimap.height()
        Length=float(H)*11/12
        x = readNum(str(self.LineEdit_Xposition.text()),self)
        y = readNum(str(self.LineEdit_Yposition.text()),self)
        self.Frame_TFTP.move(int(x/(256*30)*(10**6)*Length+W/2-70),int(-y/(256*30)*(10**6)*Length-60+Length/2))
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


