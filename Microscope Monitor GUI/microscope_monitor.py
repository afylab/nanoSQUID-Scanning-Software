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


path = sys.path[0]
mScopeMonitorGUI = path + "\microscopeMonitor.ui"
Ui_mScopeMonitor, QtBaseClass = uic.loadUiType(mScopeMonitorGUI)

class microscopeMonitor(QtGui.QMainWindow, Ui_mScopeMonitor):
	def __init__(self, reactor, parent = None):
		super(microscopeMonitor, self).__init__(parent)
		
		self.reactor = reactor
		self.setupUi(self)
		self.setupPlots()

		#Monitor flag, True while monitoring is in progress
		self.monitoring = True
		#The total time the monitor has been active
		self.monitor_time = 0
		#Frequency with which the monitor samples the temperature, magnetic field, and helium level in samples/second
		self.monitorFreq = float(self.updateFreq.value())
		#Number of hours of temperature/field/level data displayed on the monitor plots
		self.plot_hours = 24.0
		#Number of points to keep on the plots
		self.numPts = int(self.plot_hours * (3600 / self.monitorFreq))
		#Number of data points used to compute the average boil-off rate
		self.boilOffPts = int(60 * self.boilAvg.value() * self.monitorFreq)
		#Threshold helium level in cm
		self.levelThresh = 5

		#self.updateFreq.valueChanged.connect(self.changeFreq)
		
		self.connectLabRAD(self.reactor)

		
	@inlineCallbacks
	def connectLabRAD(self, c):
		from labrad.wrappers import connectAsync

		try:
			self.cxn = yield connectAsync(name = 'mScopeMonitor')
			print 'LabRAD initialization complete.'
			self.dv = yield self.cxn.data_vault
			print 'Data Vault connection complete.'
			try:
				yield self.dv.cd('4K nSOT Microscope Monitor')
			except:
				yield self.dv.mkdir('4K nSOT Microscope Monitor')
				yield self.dv.cd('4K nSOT Microscope Monitor')
			print 'Navigated to microscope monitor logging folder.'
			yield self.connectDevices(self.reactor)
		except:
			print 'LabRAD connection failed.'
		

	@inlineCallbacks
	def connectDevices(self, c):
		try:
			#self.ips = yield self.cxn.ips120_power_supply

			self.lk = yield self.cxn.lakeshore_350
			self.lm = yield self.cxn.lm_510
			self.sleep(0.25)
			
			#yield self.ips.select_device()
			yield self.lk.select_device()
			yield self.lm.select_device()
			yield self.lm.remote()
			self.serverCxn.setStyleSheet("#serverCxn{" + 
			"background: rgb(0, 170, 0);border-radius: 4px;}")
			yield self.monitor(self.reactor)
			self.monitor_time = time.time()
		except:
			self.serverCxn.setStyleSheet("#serverCxn{" + 
			"background: rgb(161, 0, 0);border-radius: 4px;}")
		
	
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
	def monitor(self, c):
		year, month, day = time.localtime()[0], time.localtime()[1], time.localtime()[2]
		daily_log = 'Log ' + str(month) + '-' + str(day) + '-' + str(year) 
		#Creates a new Data Vault file each day
		yield self.dv.new(daily_log, ['time index', 'Time'], ['Temperature', 'Magnetic Field', 'Helium Level'])
		#Time spent monitoring today
		self.daily_monitor_time = time.time()
		#Time used to maintain a constant sampling rate
		start = time.time()
		i = 0
		while self.monitoring == True and time.localtime()[2] == day:
			self.monitorFreq = float(self.updateFreq.value())

			temp = yield self.lk.read_temp('D')
			temp = float(temp.replace("+", ""))

			#field = yield self.ips.read_parameter(7)
			level = yield self.lm.measure()
			field =  0
			now = time.time()
			dataTime = np.round((now - self.monitor_time)/3600, decimals = 4)
			logTime = np.round((now - self.daily_monitor_time)/3600, decimals = 4)
			print [temp, field, level], dataTime
			yield self.dv.add(i, logTime, float(temp), float(field), float(level))
			print 'updating'
			self.updatePlots([temp, float(field), float(level)], dataTime)
			
			yield self.sleep((start - time.time()) % self.monitorFreq)
			start = time.time()
			i+=1
		#Restarts the loop at the end of the day and updates the sampling rate
		yield self.monitor(self.reactor)
	
	def updatePlots(self, data, dataTime):

		new_temp = data[0]
		new_field = data[1]
		new_level = data[2]
		new_time = dataTime


		if self.timePts[-1] - self.timePts[0] < self.plot_hours:
			self.tempPts = np.concatenate((self.tempPts, [new_temp]), axis = 0)
			self.fieldPts = np.concatenate((self.fieldPts, [new_field]), axis = 0)
			self.levelPts = np.concatenate((self.levelPts, [new_level]), axis = 0)
			self.timePts = np.concatenate((self.timePts, [new_time]), axis = 0)
		else:
			self.tempPts = np.delete(self.tempPts, 0)
			self.fieldPts = np.delete(self.fieldPts, 0)
			self.levelPts = np.delete(self.levelPts,  0)
			self.timePts = np.delete(self.timePts, 0)
			
			self.tempPts = np.concatenate((self.tempPts, [new_temp]), axis = 0)
			self.fieldPts = np.concatenate((self.fieldPts, [new_field]), axis = 0)
			self.levelPts = np.concatenate((self.levelPts, [new_level]), axis = 0)
			self.timePts = np.concatenate((self.timePts, [new_time]), axis = 0)
		
		self.tempPlot.clear()
		self.tempPlot.plot(x = self.timePts - self.timePts[0], y = self.tempPts, pen = 0.5)
		
		self.fieldPlot.clear()
		self.fieldPlot.plot(x = self.timePts - self.timePts[0], y = self.fieldPts, pen = 0.5)
		
		self.levelPlot.clear()
		self.levelPlot.plot(x = self.timePts - self.timePts[0], y = self.levelPts, pen = 0.5)
		
		self.tempValue.display(new_temp)
		self.fieldValue.display(new_field)
		self.levelValue.display(new_level)

		#Takes the last number of helium level data points and computes the average boil-off rate in cm/hr
		avgTime = self.boilAvg.value() / 60
		tBack = np.absolute(self.tempPts - avgTime)
		argBack = np.argmin(tBack)
		levelChange = np.absolute(self.levelPts[argBack] - self.levelPts[-1])
		
		avgBoilOff = float(levelChange / avgTime)
		self.boilRate.display(np.round(avgBoilOff, decimals = 1))

		#Finds the time until the helium level reaches the specified threshold assuming the boil-off rate found above
		avgBoilOff = avgBoilOff * 3600
		refillSecs = float((self.levelPts[-1] - self.levelThresh) / avgBoilOff)
		refillHours = int(refillSecs/3600)
		refillMins = int((refillSecs - 3600*refillHours) / 60)

		dispTime = str(refillHours) + ':' + str(refillMins)
		self.refillTime.display(dispTime)



		
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
	window.show()
	reactor.run()
