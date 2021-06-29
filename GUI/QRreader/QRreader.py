import sys
from PyQt5 import QtWidgets, uic
import numpy
import decimal #required for more digits
from nSOTScannerFormat import readNum, formatNum

path = sys.path[0]
QRreaderWindowUI, QtBaseClass = uic.loadUiType(path + r"\QRreader\QRreaderWindow.ui")

class Window(QtWidgets.QMainWindow, QRreaderWindowUI):
    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)
        self.setupAdditionalUi()

        #Connect all the pushbuttons in the grid
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

        #Connect lineEdits and pushBUtton to updating QR code grid center points
        self.lineEdit_Xpositioncenter.editingFinished.connect(self.UpdateCenterX)
        self.lineEdit_Ypositioncenter.editingFinished.connect(self.UpdateCenterY)
        self.pushButton_setGridCenter.clicked.connect(self.setGridCenter)

        #Initialize position tracking variables
        self.CenterX=83 #
        self.CenterY=83

        self.TotalX=166
        self.TotalY=166

        #
        self.QRpictureX = 200
        self.QRpictureY = 200

        #Se4t lineEdit to default center values
        self.lineEdit_Xpositioncenter.setText(str(self.CenterX))
        self.lineEdit_Ypositioncenter.setText(str(self.CenterY))

        #initialize a grid to keep track of which grid elements are selected and which are not
        self.fill=numpy.zeros((4,4))

        self.moveDefault()

    def moveDefault(self):
        self.move(550,10)

    def updatePosition(self):
        self.xposition = int(self.fill[0,0])*2**7+int(self.fill[0,1])*2**6+int(self.fill[0,2])*2**5+int(self.fill[0,3])*2**4+int(self.fill[1,0])*2**3+int(self.fill[1,1])*2**2+int(self.fill[1,2])*2**1+int(self.fill[1,3])*2**0
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

    def numtoint(self,num):
        #convert the distance in microns to the index of the QR code on the grid, knowing that they
        #code are separated by 30 microns
        val=int((num*10**6)/30.0)
        return val

    def inttonum(self,int):
        #convert the index of the QR code on the grid to a position knowing that the QR codes
        #are separated by 30 microns
        val=float(decimal.Decimal(int*30)/decimal.Decimal((10**6)))
        return val

    def setGridCenter(self):
        self.CenterX=int(self.fill[0,0])*2**7+int(self.fill[0,1])*2**6+int(self.fill[0,2])*2**5+int(self.fill[0,3])*2**4+int(self.fill[1,0])*2**3+int(self.fill[1,1])*2**2+int(self.fill[1,2])*2**1+int(self.fill[1,3])*2**0
        self.CenterY=int(self.fill[2,0])*2**7+int(self.fill[2,1])*2**6+int(self.fill[2,2])*2**5+int(self.fill[2,3])*2**4+int(self.fill[3,0])*2**3+int(self.fill[3,1])*2**2+int(self.fill[3,2])*2**1+int(self.fill[3,3])*2**0
        self.TotalX=2*self.CenterX
        self.TotalY=2*self.CenterY#read the configuration of QRCode
        self.lineEdit_Xpositioncenter.setText(str(self.CenterX))
        self.lineEdit_Ypositioncenter.setText(str(self.CenterY))
        self.updatePosition()
        self.UpdateTipTF()

    def UpdateCenterX(self):
        new_CenterX = readNum(self.lineEdit_Xpositioncenter.text())
        if isinstance(new_CenterX, float) and new_CenterX > 0 and new_CenterX < 129:
            self.CenterX=int(str(self.lineEdit_Xpositioncenter.text()))
            self.TotalX=2*self.CenterX
        self.lineEdit_Xpositioncenter.setText(str(self.CenterX))
        self.updatePosition()
        self.UpdateTipTF()

    def UpdateCenterY(self):
        new_CenterY = readNum(self.lineEdit_Ypositioncenter.text())
        if new_CenterY>0 and new_CenterY<129 and isinstance(new_CenterY, float):
            self.CenterY=int(str(self.lineEdit_Ypositioncenter.text()))
            self.TotalY=2*self.CenterY
        self.lineEdit_Ypositioncenter.setText(str(self.CenterY))
        self.updatePosition()
        self.UpdateTipTF()

    def setupAdditionalUi(self):
    #Set up UI that isn't easily done from Qt Designer
        pass

    def toggleqrcode(self, location, button):
        if self.fill[location] == False:
            self.fill[location] = True
            self.colorButton(button, True)
        else:
            self.fill[location] = False
            self.colorButton(button, False)
        self.updatePosition()
        self.UpdateTipTF()

    def UpdateTipTF(self):
        W=float(self.Frame_Minimap.width())#specific to picture
        H=self.Frame_Minimap.height()#specific to picture
        Length=float(H)*11/12#specific to picture
        x = readNum(str(self.lineEdit_Xposition.text()), self, True)
        y = readNum(str(self.lineEdit_Yposition.text()), self, True)
        self.Frame_TFTP.move(int(x/(self.TotalX*30)*(10**6)*Length+W/2-70),int(-y/(self.TotalY*30)*(10**6)*Length-60+Length/2))#formula is empirical
        self.Frame_TFTP.raise_()

if __name__=="__main__":
    import qt4reactor
    app = QtWidgets.QApplication(sys.argv)
    qt4reactor.install()
    from twisted.internet import reactor
    window = Window(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
