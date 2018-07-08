from __future__ import division
import sys
import twisted
from PyQt4 import QtCore, QtGui, QtTest, uic
from twisted.internet.defer import inlineCallbacks, Deferred
import numpy as np
import pyqtgraph as pg
import exceptions
import time
import datetime as dt
import subprocess
from subprocess import *



path = sys.path[0]
mScopeMonitorGUI = path + "\microscopeMonitor.ui"
settingsGUI = path + "\monitorSettings.ui"
Ui_mScopeMonitor, QtBaseClass = uic.loadUiType(mScopeMonitorGUI)
Ui_loggingSettings, QtBaseClass = uic.loadUiType(settingsGUI)



class microscopeMonitor(QtGui.QMainWindow, Ui_mScopeMonitor):
	def __init__(self, reactor, parent = None):
		super(microscopeMonitor, self).__init__(parent)
		
		self.reactor = reactor
		self.windowSize = 1
		self.setupUi(self)
		self.setupPlots()
		self.editSettings.clicked.connect(self.edit)
		self.stopMon.clicked.connect(self.pause)
		self.connect(QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.CTRL+ QtCore.Qt.Key_Z), self), QtCore.SIGNAL('activated()'),self.normal)

		#Monitor flag, True while monitoring is in progress
		self.monitoring = True
		#The total time the monitor has been active
		self.monitor_time = 0
		#Frequency with which the monitor samples the temperature and magnetic field in samples/second
		self.monitorFreq = 1
		#Frequency with which the monitor samples the helium level in samples/second
		self.levelFreq = 60
		#Number of hours of temperature/field/level data displayed on the monitor plots
		self.plot_hours = 12.0
		#Number of points to keep on the plots
		self.numPts = int(self.plot_hours * (3600 / self.monitorFreq))
		self.boilAvg = 30
		#Number of data points used to compute the average boil-off rate
		self.boilOffPts = int(60 * float(self.boilAvg * self.monitorFreq))
		#Threshold helium level in cm
		self.levelThresh = 0
		#Level monitor reading in percent that corresponds to the bottom of the belly.
		self.bellyLevel = 30
		#Inputs from the magnet and sample thermometers
		self.magTempInput = str('A')
		self.sampleTempInput = str('B')

		#Keeps trck of most important connections
		self.labCxns = {"labRAD" : False , "datavault" : False , "devServers" : False}
		#Registers which devices are plugged in
		self.devCxns = {"levelMon" : False, "tempCont" : False, "magPower": False}
		
		self.connectLabRAD()


		
	@inlineCallbacks
	def connectLabRAD(self, c = None):
		#subprocess.Popen('labrad', shell = True)
		dvPath = 'start python "' + path + '\data_vault.py"\n\r'
		self.p = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE, shell = True)
		self.pid =  self.p.pid
		self.p.stdin.write(dvPath)
		time.sleep(5)	
		from labrad.wrappers import connectAsync

		try:
			self.cxn = yield connectAsync(host = '127.0.0.1', password = 'pass')
			self.labCxns["labRAD"] = True
			print 'LabRAD initialization complete.'

			yield self.connectDv(self.reactor)
		except:
			print 'LabRAD connection failed.'

	@inlineCallbacks
	def connectDv(self, c):	
		print 'Starting dv cxn'
		#p = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE)
		#dvPath = 'start python "' + path + '\data_vault.py"\n\r'
		#p.stdin.write(dvPath)
		#subprocess.Popen(dvPath, shell = True)
		print 'sleeping'
		yield self.sleep(1)
		print 'done sleeping'
		i = 0
		try:
			print 'trying dv'
			self.dv = yield self.cxn.data_vault
			self.labCxns["datavault"] == True
		except Exception as inst:
			print type(inst)
			print inst.args
			print inst
			print i 
			i += 1
			time.sleep(1)
		print 'tesing dv'
		self.testDv(self.reactor)


	@inlineCallbacks
	def testDv(self, c):
		yield self.dv.new("Trace Test", ['Trace Index', 'B Field Index','Bias Voltage Index','B Field','Bias Voltage'],['DC SSAA Output','Noise', 'dI/dV'])
	
		xvals = np.linspace(0, 10, 100)
		yvals = np.linspace(-1, 1, 100)


		for i in range(0,10):
			for j in range(0, 10):
				a = (0,i,j, xvals[i], yvals[j], np.sin(yvals[j]), np.exp(yvals[j]), 0)
				b = (1,i,j, xvals[i], yvals[j], np.cos(yvals[j]), np.exp(-yvals[j]), 0)
				yield self.dv.add(a)
				yield self.dv.add(b)
			print i
		print 'done, closing dv'
		x = self.pid
		Popen("TASKKILL /F /PID {pid} /T".format(pid=x))

		



		

	@inlineCallbacks
	def connectDevices(self, c = None):
		try:
			self.lk = yield self.cxn.lakeshore_331
			print 'got lk'
			self.lm = yield self.cxn.lm_510
			print 'got lm'
			self.ips = yield self.cxn.ips120_power_supply
			print 'got ips'
			self.labCxns["devServes"] = True
			self.sleep(0.25)
		except:
			print "Device servers not running"

		try:			
			yield self.ips.select_device()
			self.devCxns["magPower"] = True
			print 'selected ips'
		except:
			pass
		try:
			yield self.lk.select_device()
			self.devCxns["tempCont"] = True
			print 'selected lk'
		except:
			pass
		try:
			yield self.lm.select_device()
			self.devCxns["levelMon"] = True
			yield self.lm.remote()
			print 'selected lm'
		except:
			pass
		if not False in self.devCxns.values():
			self.serverCxn.setStyleSheet("#serverCxn{" + 
			"background: rgb(0, 170, 0);border-radius: 4px;}")
		else:
			self.serverCxn.setStyleSheet("#serverCxn{" + 
			"background: rgb(161, 0, 0);border-radius: 4px;}")
		if self.labCxns["devServes"] == True:
			self.monitor_time = time.time()
			yield self.monitor()
		else:
			"Cannot start monitoring"


		
	
	def setupPlots(self):
		self.tempPts = np.array([])
		self.fieldPts = np.array([])
		self.levelPts = np.array([])
		self.timePts = np.array([])
		
		self.tempPlot = pg.PlotWidget(parent = self.temperaturePlot)
		self.tempPlot.setGeometry(QtCore.QRect(0, 0, 400, 250))
		self.tempPlot.setLabel('left', 'Temperature', units = 'K')
		self.tempPlot.setLabel('bottom', 'Time', units = 'hr')
		self.tempPlot.showAxis('right', show = True)
		self.tempPlot.showAxis('top', show = True)
		
		self.fieldPlot = pg.PlotWidget(parent = self.magFieldPlot)
		self.fieldPlot.setGeometry(QtCore.QRect(0, 0, 400, 250))
		self.fieldPlot.setLabel('left', 'Magnetic Field', units = 'T')
		self.fieldPlot.setLabel('bottom', 'Time', units = 'hr')
		self.fieldPlot.showAxis('right', show = True)
		self.fieldPlot.showAxis('top', show = True)
		
		self.levelPlot = pg.PlotWidget(parent = self.heLevelPlot)
		self.levelPlot.setGeometry(QtCore.QRect(0, 0, 400, 250))
		self.levelPlot.setLabel('left', 'Helium Level', units = 'cm')
		self.levelPlot.setLabel('bottom', 'Time', units = 'hr')
		self.levelPlot.showAxis('right', show = True)
		self.levelPlot.showAxis('top', show = True)


	@inlineCallbacks
	def monitor(self, c = None):
		year, month, day = time.localtime()[0], time.localtime()[1], time.localtime()[2]
		daily_log = 'Log ' + str(month) + '-' + str(day) + '-' + str(year) 
		#Creates a new Data Vault file each day
		yield self.dv.new(daily_log, ['time index', 'Time'], ['Magnet Temperature', 'Sample Temperature', 'Magnetic Field', 'Helium Level'])
		#Time spent monitoring today
		self.daily_monitor_time = time.time()
		#Time used to maintain a constant sampling rate
		start = time.time()
		refTimes = [time.time(), time.time()]
		yield self.lm.set_units("PERCENT")
		i = 0
		while time.localtime()[2] == day:

			if self.monitoring == True:
				now = time.time()
				#checks if it's time to read the temperature and field and does so as needed
				if ((now - refTimes[0]) > self.monitorFreq)or i == 0:

					try:
						temp = yield self.lk.read_temp(self.magTempInput)
						temp = float(temp.replace("+", ""))
						sampTemp = yield self.lk.read_temp(self.sampleTempInput)
						sampTemp = float(sampTemp.replace("+", ""))
						self.devCxns["tempCont"] = True
					except:
						sampTemp = 0
						temp = 0
						self.devCxns["tempCont"] = False
					try:
						field =  yield self.ips.read_parameter(7)
						field = field.replace("'", "")
						field = field.replace("R", "")
						field = field.replace("+", "")
						field = float(field.replace("-", ""))
						self.devCxns["magPower"] = True
					except:
						field = 0
						self.devCxns["magPower"] = False

					refTimes[0] = time.time()
				else:
					pass

				#checks to see if it's time to read the level and does so if needed
				if ((now - refTimes[1]) > self.levelFreq) or i == 0:

					try:
						level = yield self.lm.measure()
						self.devCxns["levelMon"] = True
					except:
						level = 0
						self.devCxns["levelMon"] = False

					refTimes[1] = time.time()
				else:
					pass

				dataTime = np.round((now - self.monitor_time)/3600, decimals = 4)
				logTime = np.round((now - self.daily_monitor_time)/3600, decimals = 4)
				yield self.dv.add(i, logTime, float(temp), float(sampTemp), float(field), float(level))
				print temp, sampTemp, field, level, dataTime
				self.updatePlots([temp, float(field), float(level)], dataTime, sampTemp)
				#checks to see which values are updated more frequently and sleeps accordingly
				smallFreq = np.amin([self.monitorFreq, self.levelFreq])

				yield self.sleep((start - time.time()) % smallFreq)
				if not False in self.devCxns.values():
					self.serverCxn.setStyleSheet("#serverCxn{" + 
					"background: rgb(0, 170, 0);border-radius: 4px;}")
				else:
					self.serverCxn.setStyleSheet("#serverCxn{" + 
					"background: rgb(161, 0, 0);border-radius: 4px;}")
				start = time.time()

			elif self.monitoring == False:
				pass
			i += 1
		#Restarts the loop at the end of the day
		yield self.monitor(self.reactor)
	
	def updatePlots(self, data, dataTime, sampTemp):
		new_temp = data[0]
		new_field = data[1]
		new_level = 100 * (data[2] - self.bellyLevel) / (100 - self.bellyLevel)
		new_time = dataTime
		sampleTemperature = float(sampTemp)

		if len(self.timePts) == 0 or self.timePts[-1] - self.timePts[0] < self.plot_hours:

			self.tempPts = np.concatenate((self.tempPts, [new_temp]), axis = 0)
			self.fieldPts = np.concatenate((self.fieldPts, [new_field]), axis = 0)
			self.levelPts = np.concatenate((self.levelPts, [new_level]), axis = 0)
			self.timePts = np.concatenate((self.timePts, [new_time]), axis = 0)

		else:
			plotPoints = int(self.plot_hours * 3600 / self.monitorFreq)
			while len(self.timePts) > plotPoints:
				self.tempPts = np.delete(self.tempPts, 0)
				self.fieldPts = np.delete(self.fieldPts, 0)
				self.levelPts = np.delete(self.levelPts,  0)
				self.timePts = np.delete(self.timePts, 0)
			
			self.tempPts = np.concatenate((self.tempPts, [new_temp]), axis = 0)
			self.fieldPts = np.concatenate((self.fieldPts, [new_field]), axis = 0)
			self.levelPts = np.concatenate((self.levelPts, [new_level]), axis = 0)
			self.timePts = np.concatenate((self.timePts, [new_time]), axis = 0)

		if self.devCxns["tempCont"] == True:
			self.tempPlot.clear()
			self.tempPlot.plot(x = self.timePts - self.timePts[0], y = self.tempPts, pen = 0.5)
			self.tempValue.display(new_temp)
			self.sampleTemp.display(sampleTemperature)
		else:
			self.tempValue.setDigitCount(5)
			self.tempValue.display("-----")
			self.sampleTemp.setDigitCount(5)
			self.sampleTemp.display("-----")

		if self.devCxns["magPower"] == True:
			self.fieldPlot.clear()
			self.fieldPlot.plot(x = self.timePts - self.timePts[0], y = self.fieldPts, pen = 0.5)
			self.fieldValue.display(new_field)
		else:
			self.fieldValue.setDigitCount(5)
			self.fieldValue.display("-----")
		
		if self.devCxns["levelMon"] == True:
			self.levelPlot.clear()
			self.levelPlot.plot(x = self.timePts - self.timePts[0], y = self.levelPts, pen = 0.5)
			self.levelValue.display(new_level)
		else:
			self.levelValue.setDigitCount(5)
			self.levelValue.display("-----")
		
		



		#Takes the last number of helium level data points and computes the average boil-off rate in %/hr
		if self.devCxns["levelMon"] == True:
			avgTime = self.boilAvg / 60
			backTime = self.timePts[-1] - avgTime
			tBack = np.absolute(self.timePts - backTime)
			argBack = np.argmin(tBack)
			levelChange = self.levelPts[argBack] - self.levelPts[-1]
			
			avgBoilOff = float(levelChange / avgTime)
			self.boilRate.display(np.round(avgBoilOff, decimals = 2))


			#Finds the time until the helium level reaches the specified threshold assuming the boil-off rate found above
			avgBoilOff = float(avgBoilOff / 3600)
			if avgBoilOff != 0 and avgBoilOff>0 and len(self.timePts)>2:
				refillSecs = float((self.levelPts[-1] - self.levelThresh) / avgBoilOff)
				refillDays = int(refillSecs/86400)
				refillHours = int((refillSecs - 86400*refillDays) / 3600)
				refillMins = int((refillSecs - 3600*refillHours - 86400*refillDays) / 60)

				dispMins = str(refillMins)
				dispDays = str(refillDays)
				dispHours = str(refillHours)

				if refillDays != 0 and refillDays < 99:
					dispTime = dispDays + 'd ' + dispHours + 'hr'


				elif refillDays == 0:
					dispTime = dispHours + 'hr ' + dispMins + 'min'
				else:
					dispTime = "--:--"
				self.refillTime.setDigitCount(len(dispTime))
				self.refillTime.display(dispTime)
			else:
				dispTime = "--:--"
				self.refillTime.setDigitCount(len(dispTime))
				self.refillTime.display(dispTime)
		else:
			pass

	def edit(self):
		self.editMonitor = monitorSettings(self)
		self.editMonitor.show()
	def normal(self):
		if self.windowSize ==1:
			window.showNormal()
			self.windowSize = 0
		elif self.windowSize == 0:
			window.showFullScreen()
			self.windowSize = 1
	def pause(self):
		if self.monitoring == True:
			self.monitoring = False
			self.stopMon.setText("Start")
		elif self.monitoring == False:
			self.monitoring = True
			self.stopMon.setText("Stop")

		
	def sleep(self,secs):
		d = Deferred()
		self.reactor.callLater(secs,d.callback,'Sleeping')
		return d

		
	def closeEvent(self, e):
		self.reactor.stop()
		print 'Reactor shut down.'


if __name__ == "__main__":
	app = QtGui.QApplication([])
	from qtreactor import pyqt4reactor
	pyqt4reactor.install()
	from twisted.internet import reactor
	window = microscopeMonitor(reactor)
	window.showFullScreen()
	reactor.run()
