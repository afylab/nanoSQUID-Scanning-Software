import sys
from PyQt5 import QtWidgets, uic
import numpy
from nSOTScannerFormat import readNum, formatNum

path = sys.path[0]
QRreaderWindowUI, QtBaseClass = uic.loadUiType(path + r"\QRreader\QRreaderWindow.ui")

class Window(QtWidgets.QMainWindow, QRreaderWindowUI):
    def __init__(self, reactor, parent = None):
        super(Window, self).__init__(parent)
        self.reactor = reactor
        self.setupUi(self)

        #Connect all the pushbuttons in the grid
        self.pushButton_qrcode00.clicked.connect(lambda: self.toggleqrcode((0,0), self.pushButton_qrcode00))
        self.pushButton_qrcode01.clicked.connect(lambda: self.toggleqrcode((0,1), self.pushButton_qrcode01))
        self.pushButton_qrcode02.clicked.connect(lambda: self.toggleqrcode((0,2), self.pushButton_qrcode02))
        self.pushButton_qrcode03.clicked.connect(lambda: self.toggleqrcode((0,3), self.pushButton_qrcode03))
        self.pushButton_qrcode10.clicked.connect(lambda: self.toggleqrcode((1,0), self.pushButton_qrcode10))
        self.pushButton_qrcode11.clicked.connect(lambda: self.toggleqrcode((1,1), self.pushButton_qrcode11))
        self.pushButton_qrcode12.clicked.connect(lambda: self.toggleqrcode((1,2), self.pushButton_qrcode12))
        self.pushButton_qrcode13.clicked.connect(lambda: self.toggleqrcode((1,3), self.pushButton_qrcode13))
        self.pushButton_qrcode20.clicked.connect(lambda: self.toggleqrcode((2,0), self.pushButton_qrcode20))
        self.pushButton_qrcode21.clicked.connect(lambda: self.toggleqrcode((2,1), self.pushButton_qrcode21))
        self.pushButton_qrcode22.clicked.connect(lambda: self.toggleqrcode((2,2), self.pushButton_qrcode22))
        self.pushButton_qrcode23.clicked.connect(lambda: self.toggleqrcode((2,3), self.pushButton_qrcode23))
        self.pushButton_qrcode30.clicked.connect(lambda: self.toggleqrcode((3,0), self.pushButton_qrcode30))
        self.pushButton_qrcode31.clicked.connect(lambda: self.toggleqrcode((3,1), self.pushButton_qrcode31))
        self.pushButton_qrcode32.clicked.connect(lambda: self.toggleqrcode((3,2), self.pushButton_qrcode32))
        self.pushButton_qrcode33.clicked.connect(lambda: self.toggleqrcode((3,3), self.pushButton_qrcode33))

        #Connect lineEdits and pushButton to updating QR code grid center points
        self.lineEdit_gridCenterX.editingFinished.connect(self.updateCenterX)
        self.lineEdit_gridCenterY.editingFinished.connect(self.updateCenterY)
        self.pushButton_setGridCenter.clicked.connect(self.setGridCenter)

        #Define the (i,j) center coordinate of the QR code grid and the picture
        self.gridCenter = [83, 83]

        #Set lineEdits to default values
        self.lineEdit_gridCenterX.setText(formatNum(self.gridCenter[0]))
        self.lineEdit_gridCenterY.setText(formatNum(self.gridCenter[1]))

        #initialize a grid to keep track of which grid elements are selected and which are not.
        #By default, none are selected
        self.fill = numpy.zeros((4,4))

        #Update the position
        self.updatePosition()

        self.moveDefault()

    def moveDefault(self):
        self.move(550,10)

    def toggleqrcode(self, location, button):
        if self.fill[location] == False:
            self.fill[location] = True
            self.colorButton(button, True)
        else:
            self.fill[location] = False
            self.colorButton(button, False)
        self.updatePosition()

    def updatePosition(self):
        #First find the x and y position indices from the currently selected QR code pattern
        xPosIndex = int(self.fill[0,0])*2**7+int(self.fill[0,1])*2**6+int(self.fill[0,2])*2**5+int(self.fill[0,3])*2**4+int(self.fill[1,0])*2**3+int(self.fill[1,1])*2**2+int(self.fill[1,2])*2**1+int(self.fill[1,3])*2**0
        yPosIndex = int(self.fill[2,0])*2**7+int(self.fill[2,1])*2**6+int(self.fill[2,2])*2**5+int(self.fill[2,3])*2**4+int(self.fill[3,0])*2**3+int(self.fill[3,1])*2**2+int(self.fill[3,2])*2**1+int(self.fill[3,3])*2**0

        #Convert the indices to microns (knowing that they are separated by 30 um and 0,0 is at the center)
        self.lineEdit_Xposition.setText(formatNum(30e-6*(xPosIndex - self.gridCenter[0])))
        self.lineEdit_Yposition.setText(formatNum(30e-6*(yPosIndex - self.gridCenter[1])))

        #Get the current dimensions of the real picture
        W, H = self.Frame_Minimap.width(), self.Frame_Minimap.height()

        #Determine where the TF should go in the picture pixel coordinates. These formulas were determined
        #empirically to look good enough
        TF_pos_x = int( ((xPosIndex-self.gridCenter[0])/(2*self.gridCenter[0]))*H*11/12 + W/2 - 70)
        TF_pos_y = int( (-(yPosIndex-self.gridCenter[1])/(2*self.gridCenter[1]))*H*11/12 + H*11/24 - 60)
        self.Frame_TFTP.move(TF_pos_x,TF_pos_y)#formula is empirical

    def colorButton(self, button, fill):
        fillstatus ="background-color: red;color:black"
        notfillstatus = "background-color: rgb(230,230,230);color:grey"
        if fill:
            button.setStyleSheet(fillstatus)
        else:
            button.setStyleSheet(notfillstatus)

    def setGridCenter(self):
        centerX = int(self.fill[0,0])*2**7+int(self.fill[0,1])*2**6+int(self.fill[0,2])*2**5+int(self.fill[0,3])*2**4+int(self.fill[1,0])*2**3+int(self.fill[1,1])*2**2+int(self.fill[1,2])*2**1+int(self.fill[1,3])*2**0
        centerY = int(self.fill[2,0])*2**7+int(self.fill[2,1])*2**6+int(self.fill[2,2])*2**5+int(self.fill[2,3])*2**4+int(self.fill[3,0])*2**3+int(self.fill[3,1])*2**2+int(self.fill[3,2])*2**1+int(self.fill[3,3])*2**0

        #Only update the center if it's not 0,0
        if centerX > 0 and centerY > 0:
            self.gridCenter = (centerX, centerY)
            self.lineEdit_gridCenterX.setText(formatNum(self.gridCenter[0], 0))
            self.lineEdit_gridCenterY.setText(formatNum(self.gridCenter[1], 0))
            self.updatePosition()

    def updateCenterX(self):
        new_CenterX = readNum(self.lineEdit_gridCenterX.text())
        if isinstance(new_CenterX, float) and new_CenterX > 0 and new_CenterX < 129:
            self.gridCenter[0] = int(new_CenterX)
        self.lineEdit_gridCenterX.setText(formatNum(self.gridCenter[0], 0))
        self.updatePosition()

    def updateCenterY(self):
        new_CenterY = readNum(self.lineEdit_gridCenterY.text())
        if new_CenterY>0 and new_CenterY<129 and isinstance(new_CenterY, float):
            self.gridCenter[1] = int(new_CenterY)
        self.lineEdit_gridCenterY.setText(formatNum(self.gridCenter[1], 0))
        self.updatePosition()

if __name__=="__main__":
    import qt4reactor
    app = QtWidgets.QApplication(sys.argv)
    qt4reactor.install()
    from twisted.internet import reactor
    window = Window(reactor)
    window.show()
    reactor.runReturn()
    sys.exit(app.exec_())
