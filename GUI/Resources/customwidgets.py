from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFrame
from time import time

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

class LoopTimer():
    '''
    For timing loops, designed to be robust so that it does not every hold up a
    script if it fails.
    
    This works with the generic code:
    LoopTimerInstance.start(N)
    for i in range(N):
        # YOUR CODE
        message = LoopTimerInstance.next()
    
    or for while loops where the end is not defined.
    LoopTimerInstance.start()
    while condition:
        # YOUR CODE
        message = LoopTimerInstance.next()
    
    This version will display to a label that you pass to it on instantiation.
    '''
    def __init__(self, displayLabel):
        self.printErr = True
        self.sumDT = 0
        self.numIter = 0
        self.label = displayLabel
        
    
    def start_loop_timer(self, total=None):
        '''
        Start timing a loop, call right before the loop starts.
        
        Optional parameter total is the number of iterations in the loop, pass it
        the number of iterations as an integer or if iterating over a list pass it
        the list and it will determine the number of iternations.
        '''
        try:
            self.t0 = time()
            self.tlast = 0
            self.printErr = True
            self.sumDT = 0
            self.numIter = 0
            if isinstance(total, int) or isinstance(total, float):
                self.N = int(total)
            elif isinstance(total, list):
                self.N = len(total)
            elif isinstance(total, np.ndarray):
                self.N = total.size
            else:
                self.N = 0
        except Exception as e:
            if self.printErr:
                self.printErr = False
                print("Loop Timer Error")
                print(format_exc())
        
    
    def next(self):
        '''
        Counts the end of an iteration. Call at the end of a loop, right before it resets.
        If it runs into an error, it will only print an error message once to avoid flooding
        the terminal with error messages.
        '''
        try:
            if not hasattr(self,'t0'):
                self.label.setText("Loop Timer not instantiated. Starting the timer now.")
                self.start_loop_timer()
                return
        
            tnow = time() - self.t0
            deltat = tnow - self.tlast
            self.tlast = tnow
            self.sumDT += deltat
            self.numIter += 1
            avg = self.sumDT / self.numIter
            msg = " Time: " + str(round(deltat,1)) + "s Average: " + str(round(avg,1)) + "s"
            if self.N != 0:
                msg = str(self.numIter) + "/" + str(self.N) + msg + " " + str(round(100*self.numIter/self.N,1)) + "% Complete"
            else:
                msg = str(self.numIter) + "/" + msg
            self.label.setText(msg)
        except Exception as e:
            if self.printErr:
                self.printErr = False
                print("Loop Timer Error")
                print(format_exc())
    
    def reset(self):
        self.printErr = True
        if hasattr(self,'t0'):
            ttotal = time() - self.t0
            msg = "Done. Total Time: " + str(round(ttotal,1)) + " "
            self.label.setText(msg)
            delattr(self, 't0')
