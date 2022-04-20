import sys
from PyQt5 import QtGui, QtWidgets, QtCore, uic
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue
from nSOTScannerFormat import readNum, formatNum, printErrorInfo
from ScriptingModule import syntax
from Resources.customwidgets import LoopTimer
from traceback import format_exc

path = sys.path[0] + r"\ScriptingModule"
ScanControlWindowUI, QtBaseClass = uic.loadUiType(path + r"\Scripting.ui")

class Window(QtWidgets.QMainWindow, ScanControlWindowUI):

    def __init__(self, reactor, parent=None, *args, **kwargs):
        super(Window, self).__init__(parent)

        self.reactor = reactor

        self.ScanControl = args[0]
        self.Approach = args[1]
        self.nSOTChar = args[2]
        self.FieldControl = args[3]
        self.TempControl = args[4]
        self.SampleChar = args[5]
        self.nSOTBias = args[6]
        self.simulate = args[7]

        if "default_script_dir" in kwargs:
            self.default_script_dir = kwargs["default_script_dir"]
        else:
            self.default_script_dir = "C:\\Users"

        self.setupUi(self)
        self.setupAdditionalUi()

        self.moveDefault()

        self.push_run.clicked.connect(lambda *args : self.runScript(False, *args))
        self.push_abort.clicked.connect(self.abortScript)
        self.push_load.clicked.connect(self.loadFile)
        self.push_save.clicked.connect(self.saveFile)
        self.push_simulate.clicked.connect(lambda *args : self.runScript(True, *args))

        #Have Ctrl+S
        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+S"), self.codeEditor, self.saveFile, context=QtCore.Qt.WidgetShortcut)

        #Initialize all the labrad connections as none
        self.cxn = None
        self.cxnr = None

        self.runningScript = False
        
        self.looptimer = LoopTimer(self.label_timing)

        self.push_abort.setEnabled(False)

    def moveDefault(self):
        self.move(550,10)
        self.resize(700,510)

    @inlineCallbacks
    def connectLabRAD(self, equip):
        try:
            from labrad.wrappers import connectAsync
            if equip.cxn is not False:
                self.cxn = yield connectAsync(host='127.0.0.1', password='pass')

            if equip.cxnr is not False:
                self.cxnr = yield connectAsync(host=equip.remote_ip, password='pass')
            self.equip = equip
        except Exception as inst:
            printErrorInfo()

    def disconnectLabRAD(self):
        self.cxn = None
        self.cxnr = None

    def setupAdditionalUi(self):
        #Set up UI that isn't easily done from Qt Designer
        self.codeEditor.close()
        self.codeEditor = CodeEditor(self)
        self.verticalLayout.removeItem(self.horizontalLayout)
        self.verticalLayout.addWidget(self.codeEditor)
        self.verticalLayout.addItem(self.horizontalLayout)

    @inlineCallbacks
    def runScript(self, sim, *args):
        '''
        Runs a script in the Scripting module, if sim is True it will simulate the
        outputs without changing the hardware.
        '''
        #Define variables that can be used in the script.
        self.lockInterface()
        self.runningScript = True
        self.label_status.setText('Script is compiling')
        try:
            code_to_run = self.formatCode()
        except:
            printErrorInfo()

        try:
            self.current_line = 0
            exec(code_to_run, globals()) # Generates function f
            self.current_line = 1
            if sim:
                ScanControl, Approach, nSOTChar, FieldControl, TempControl, SampleChar, nSOTBias = self.simulate.get_virtual_modules()
                yield f(self, self.simulate.sleep, self.cxn, self.cxnr, ScanControl, Approach, nSOTChar, FieldControl, TempControl, SampleChar, nSOTBias)
                self.simulate.compile()
                self.simulate.showSim()
            else:
                yield f(self, self.sleep, self.cxn, self.cxnr, self.ScanControl, self.Approach, self.nSOTChar, self.FieldControl, self.TempControl, self.SampleChar, self.nSOTBias)
            self.runningScript = False
            self.label_status.setText('Script is in editing mode')
            self.unlockInterface()
            self.looptimer.reset()
        except ScriptAborted:
            self.runningScript = False
            self.label_status.setText('Script aborted on line ' + str(self.current_line))
            self.unlockInterface()
        except TabError:
            self.runningScript = False
            self.label_status.setText('TabError: check your whitespace')
            self.unlockInterface()
        except SyntaxError:
            '''Because by default many lines of code are added, if a syntax error is thrown it
            doesn't point to the offending line in the raw code. Try to rerun code without
            any modifications to get the true line where the syntax error is thrown'''
            try:
                exec(str(self.codeEditor.toPlainText()))
            except SyntaxError as inst:
                self.runningScript = False
                self.label_status.setText("Syntax error thrown on line " +  str(inst.lineno))
                from traceback import format_exc
                print(format_exc())
                self.unlockInterface()
        except Exception as inst:
            printErrorInfo()
            self.runningScript = False
            if self.current_line == 0:
                self.label_status.setText(str(inst) + ' error thrown while compiling')
            else:
                self.label_status.setText(str(inst) + ' thrown on line ' + str(self.current_line))
            self.unlockInterface()

    def abortScript(self):
        self.runningScript = False

    def formatCode(self):
        '''Format the code, inputting statements to be able to interrupt the script
        and updating which line of code is currently running. Note that whitespace
        in this section is critical to it running correctly.
        '''
        code_lines = str(self.codeEditor.toPlainText()).splitlines()
        code_to_run = "@inlineCallbacks\ndef f(self, sleep, cxn, cxnr, ScanControl, Approach, nSOTChar, FieldControl, TempControl, SampleChar, nSOTBias):\n "
        code_to_run = code_to_run + "yield sleep(0.1)\n "
        i = 1
        prev_line = 'None'
        prev_spaces = ''
        for line in code_lines:
            #detect number of space on next line
            spaces = self.detectSpaces(line)
            if len(line) == 0 and prev_spaces != '': # Handels blank lines in a loop, otherwise inserted linear would throw indentation errors.
                spaces = prev_spaces
            #inlineCallbacks header is special and needs to be right before the next line in the code,
            if '@inlineCallbacks' not in prev_line:
                #Add code that updates which line of code is being run
                code_to_run = code_to_run + spaces + "self.current_line = " + str(i) + "\n "
                #Eventually add line of code that throws signal to update status
                code_to_run = code_to_run + spaces + "self.label_status.setText(\'Script is running line " + str(i) + "\')\n "
                #Add code that throws error if not running the script
                code_to_run = code_to_run + spaces + "if not self.runningScript:\n" + spaces + "  raise ScriptAborted(" + str(i) + ")\n "
            code_to_run = code_to_run + line + "\n "
            prev_line = line
            prev_spaces = spaces
            i = i + 1
        code_to_run = code_to_run + "\n"
        return code_to_run

    def detectSpaces(self,line):
        '''Returns a string with all the whitespace at the beginning of the input line of code'''
        num = len(line) - len(line.lstrip())
        return line[0:num]

    def loadFile(self):
        file, file1 = QtWidgets.QFileDialog.getOpenFileName(self, directory=self.default_script_dir)
        if file:
            f = open(file,'r')
            message = f.read()
            self.codeEditor.setPlainText(message)
            f.close()

    def saveFile(self):
        file, file1 = QtWidgets.QFileDialog.getSaveFileName(self, directory=self.default_script_dir)
        if file:
            f = open(file,'w')
            message = self.codeEditor.toPlainText()
            f.write(message)
            f.close()

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d

#----------------------------------------------------------------------------------------------#
    """ The following section has generally useful functions."""

    def lockInterface(self):
        self.push_run.setEnabled(False)
        self.push_save.setEnabled(False)
        self.push_load.setEnabled(False)
        self.push_abort.setEnabled(True)

    def unlockInterface(self):
        self.push_run.setEnabled(True)
        self.push_save.setEnabled(True)
        self.push_load.setEnabled(True)
        self.push_abort.setEnabled(False)

class LineNumberArea(QtWidgets.QWidget):

    def __init__(self, editor):
        super(QtWidgets.QWidget, self).__init__(editor)
        self.myeditor = editor

    def sizeHint(self):
        return QtCore.QSize(self.myeditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.myeditor.lineNumberAreaPaintEvent(event)


class CodeEditor(QtWidgets.QPlainTextEdit):
    def __init__(self, parent = None):
        super(QtWidgets.QPlainTextEdit, self).__init__(parent)

        self.lineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        # # This is PyQt4 syntax
        # self.connect(self, QtCore.SIGNAL('blockCountChanged(int)'), self.updateLineNumberAreaWidth)
        # self.connect(self, QtCore.SIGNAL('updateRequest(QRect,int)'), self.updateLineNumberArea)
        # self.connect(self, QtCore.SIGNAL('cursorPositionChanged()'), self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)

        self.setTabStopWidth(20)
        
        # For syntax highlighting
        self.highlight = syntax.PythonHighlighter(self.document())
        
        opts = self.document().defaultTextOption()
        opts.setFlags(opts.flags() | QtGui.QTextOption.ShowTabsAndSpaces)
        self.document().setDefaultTextOption(opts)
        tab_format = QtGui.QTextCharFormat()
        tab_format.setBackground(QtGui.QColor("lightgray"))

    def lineNumberAreaWidth(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):

        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(),
                       rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)


    def resizeEvent(self, event):
        super(QtWidgets.QPlainTextEdit, self).resizeEvent(event)

        cr = self.contentsRect();
        self.lineNumberArea.setGeometry(QtCore.QRect(cr.left(), cr.top(),
                    self.lineNumberAreaWidth(), cr.height()))


    def lineNumberAreaPaintEvent(self, event):
        mypainter = QtGui.QPainter(self.lineNumberArea)

        mypainter.fillRect(event.rect(), QtCore.Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Just to make sure I use the right font
        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                mypainter.setPen(QtCore.Qt.black)
                mypainter.drawText(0, top, self.lineNumberArea.width(), height,
                 QtCore.Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []

        if not self.isReadOnly():
            selection = QtWidgets.QTextEdit.ExtraSelection()

            #TODO Edit color
            lineColor = QtGui.QColor(QtCore.Qt.yellow).lighter(160)

            selection.format.setBackground(lineColor)
            selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

class ScriptAborted(Exception):
     def __init__(self, value):
         self.value = value
     def __str__(self):
         return repr(self.value)
