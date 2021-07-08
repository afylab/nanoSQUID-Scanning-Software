from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFrame

class ServerStatusWidget(QFrame):
    '''
    Need this stupid wrapper because Qt Designer does not inhert from QWidget so the references
    get convoluted. Call thisInstance.setGUIRef(self) from the class inheriting from QtDesigner and
    then this base can pass events to the mainWindow
    '''

    def __init__(self, parent, name):
        '''
        Call this when setting up the subclass (inherited from the Qt Designer code) in order to
        reference it from the main Window itself.
        '''
        super().__init__(parent)
        self.setGeometry(QtCore.QRect(0, 0, 225, 15))
        self.setStyleSheet("QLabel{\n"
            "color:rgb(168,168,168);\n"
            "qproperty-alignment: \'AlignVCenter | AlignRight\';\n"
            "}\n"
            "\n"
            "#centralwidget{\n"
            "background: black;\n"
            "}\n"
            "\n"
            "")
        self.name = name
        self.label = QtWidgets.QLabel(self)
        self.label.setGeometry(QtCore.QRect(0, 0, 80, 15))
        self.label.setText(name+":")

        self.push_indicator = QtWidgets.QPushButton(self)
        self.push_indicator.setGeometry(QtCore.QRect(85, 0, 15, 15))

        self.label_status = QtWidgets.QLabel(self)
        self.label_status.setGeometry(QtCore.QRect(115, 0, 110, 15))

        self.disconnected()
    #

    def connected(self, text=None):
        '''
        Inidcates that a server was connected successfully, will display
        text in the status label if given.
        '''
        self.push_indicator.setStyleSheet(
            "background: rgb(0, 170, 0);"
            "border-radius: 4px;")
        if text is not None:
            self.label_status.setText(text)
        else:
            self.label_status.setText("Connected")
    #

    def error(self, text=None):
        '''
        Inidcates that a server connection failed,
        will display text in the status label if given.
        '''
        self.push_indicator.setStyleSheet(
            "background: rgb(161, 0, 0);"
            "border-radius: 4px;")
        if text is not None:
            self.label_status.setText(text)
        else:
            self.label_status.setText("Connection Failed")
    #

    def disconnected(self, text=None):
        '''
        Inidcates that a server is not connected,
        will display text in the status label if given.
        '''
        self.push_indicator.setStyleSheet(
            "background: rgb(144, 140, 9);"
            "border-radius: 4px;")
        if text is not None:
            self.label_status.setText(text)
        else:
            self.label_status.setText("Not Connected")
    #
#
