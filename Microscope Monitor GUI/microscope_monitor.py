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
import MySQLdb

db = MySQLdb.connect(host="192.185.4.111",
					 user="afy2003",
					  passwd="rwnVv3%MXns3j;X{",
					  db="afy2003_4KSQUID")

cur = db.cursor()

path = sys.path[0]
mScopeMonitorGUI = path + r"\microscopeMonitor.ui"
settingsGUI = path + r"\monitorSettings.ui"
rcxnGUI = path + r"\devRecxn.ui"
Ui_rcxn, QtBaseClass = uic.loadUiType(rcxnGUI)
Ui_mScopeMonitor, QtBaseClass = uic.loadUiType(mScopeMonitorGUI)
Ui_loggingSettings, QtBaseClass = uic.loadUiType(settingsGUI)

#Server managers
serSrvPath = 'start python "' + path + '\serial_server_v3.0.1.py"\n\r'
gpibSSrvPath = 'start python "' + path + '\gpib_server.py"\n\r'
gpibManPath = 'start python "' + path + '\gpib_device_manager.py"\n\r'



#Server paths
dvPath = 'start python  "' + path + '\data_vault.py"\n\r'
lm510Path = 'start python  "' + path + '\lm_510.py"\n\r'
lk350Path = 'start python "' + path + '\lakeshore_350.py"\n\r'
ips120Path = 'start python "' + path + '\ips_120_power_supply.py"\n\r'

class reconnectDev(QtGui.QDialog, Ui_rcxn):
	def __init__(self, reactor, devCxns, sqlCxn, parent = None):
		super(reconnectDev, self).__init__(parent)

		self.setupUi(self)
		self.reactor = reactor
		self.window = parent
		
		self.devCxns = devCxns
		self.sqlCxn = sqlCxn
		
		self.initCxnStatus()
		
		self.rcxnIPS.clicked.connect(self.reconIPS)
		self.rcxnLS.clicked.connect(self.reconLS)
		self.rcxnLM.clicked.connect(self.reconLM)
		self.rcxnSQL.clicked.connect(self.reconSQL)
		
		print self.devCxns
		
	@inlineCallbacks
	def initCxnStatus(self, c = None):
		yield self.window.sleep(0.1)
		if self.devCxns["lm_510"] == True:
			self.rcxnLM.setText("Connected")
			self.setButtonStyle(self.rcxnLM, 'rcxnLM', 'green')
			self.rcxnLM.setEnabled(False)
		else:
			self.rcxnLM.setText("Reconnect")
			self.setButtonStyle(self.rcxnLM, 'rcxnLM', 'red')
			self.rcxnLM.setEnabled(True)

		if self.devCxns["ips_120"] == True:
			self.rcxnIPS.setText("Connected")
			self.setButtonStyle(self.rcxnIPS, 'rcxnIPS', 'green')
			self.rcxnIPS.setEnabled(False)
		else:
			self.rcxnIPS.setText("Reconnect")
			self.setButtonStyle(self.rcxnIPS, 'rcxnIPS', 'red')
			self.rcxnIPS.setEnabled(True)
			
		if self.devCxns["lk_350"] == True:
			self.rcxnLS.setText("Connected")
			self.setButtonStyle(self.rcxnLS, 'rcxnLS', 'green')
			self.rcxnLS.setEnabled(False)
		else:
			self.rcxnLS.setText("Reconnect")
			self.setButtonStyle(self.rcxnLS, 'rcxnLS', 'red')
			self.rcxnLS.setEnabled(True)
			
		if self.sqlCxn == True:
			self.rcxnSQL.setText("Connected")
			self.setButtonStyle(self.rcxnSQL, 'rcxnSQL', 'green')
			self.rcxnSQL.setEnabled(False)
		else:
			self.rcxnSQL.setText("Reconnect")
			self.setButtonStyle(self.rcxnSQL, 'rcxnSQL', 'red')
			self.rcxnSQL.setEnabled(True)		
			
			
	@inlineCallbacks
	def reconIPS(self, c=None):
		print 'trying to recon IPS'
		self.rcxnIPS.setEnabled(False)
		yield self.window.GPIB_SRV.refresh_devices()
		yield self.window.sleep(0.5)
		print 'recon GPIB server'
		try:
			yield self.window.ips.select_device()
			yield self.window.ips.set_control(3)
			self.window.devCxns['ips_120'] = True
			self.devCxns['ips_120'] = True
			print 'got ips again'
		except:
			print 'no ips'
		print 'tried to recon IPS'
		yield self.initCxnStatus()
	@inlineCallbacks
	def reconLS(self, c = None):
		self.rcxnLS.setEnabled(False)
		yield self.window.GPIB_SRV.refresh_devices()
		yield self.window.sleep(0.5)
		try:
			yield self.window.lk.select_device()
			yield self.window.lk.idn()
			self.window.devCxns['lk_350'] = True
			self.devCxns['lk_350'] = True
		except:
			pass
		print 'tried to recon LS'
		yield self.initCxnStatus()
	@inlineCallbacks
	def reconLM(self, c=None):
		self.rcxnLM.setEnabled(False)
		yield self.window.startServer('lm_510', 'end')
		yield self.window.sleep(1)
		yield self.window.startServer('lm_510', 'cxn')
		yield self.window.sleep(5)
		try:
			yield self.window.lm.select_device()
			yield self.window.lm.remote()
			self.window.devCxns['lm_510'] = True
			self.devCxns['lm_510'] = True
			print 'lm recon success'
		except:
			print 'lm recon failed'
		print 'tried to recon LM'
		yield self.initCxnStatus()
	@inlineCallbacks
	def reconSQL(self, c = None):
		self.rcxnSQL.setEnabled(False)
		global db
		global cur
		try:
			db = MySQLdb.connect(host="192.185.4.111",
								 user="afy2003",
								  passwd="rwnVv3%MXns3j;X{",
								  db="afy2003_4KSQUID")

			cur = db.cursor()
			self.window.sqlCxn = True
			self.sqlCxn = True
		except:
			print 'Cannot connect to database...'
		yield self.initCxnStatus()
		
	def setButtonStyle(self, button, name, color):
		reg = "QPushButton#" + name
		press = "QPushButton:pressed#" + name
		if color == 'green':
			regStr = reg + "{color: rgb(0,250,0);background-color:rgb(0,0,0);border: 2px solid rgb(0,250,0);border-radius: 5px}"
			pressStr = press + "{color: rgb(0,0,0); background-color:rgb(0,250,0);border: 2px solid rgb(0,250,0);border-radius: 5px}" 
			style = regStr + " " + pressStr
			button.setStyleSheet(style)

		elif color == 'red':
			regStr = reg + "{color: rgb(250,0,0);background-color:rgb(0,0,0);border: 2px solid rgb(250,0,0);border-radius: 5px}"
			pressStr = press + "{color: rgb(0,0,0); background-color:rgb(250,0,0);border: 2px solid rgb(250,0,0);border-radius: 5px}" 
			style = regStr + " " + pressStr
			button.setStyleSheet(style)
		else:
			pass

class monitorSettings(QtGui.QDialog, Ui_loggingSettings):
	def __init__(self, parent = None):
		super(monitorSettings, self).__init__(parent)

		self.setupUi(self)
		self.window = parent
		self.setSampleRate.setValue(self.window.monitorFreq)
		self.setLevelRate.setValue(self.window.levelFreq)
		self.setBoilAvg.setValue(self.window.boilAvg)
		self.plotDisp.setValue(self.window.plot_hours)
		self.magTempIn.setText(self.window.magTempInput)
		self.sampleTempIn.setText(self.window.sampleTempInput)
		self.ok.clicked.connect(self.ok_)
		self.closeWin.clicked.connect(self.cancel_)

	def ok_(self):
		self.window.plot_hours = float(self.plotDisp.value())
		if float(self.setSampleRate.value()) >= 1:
			self.window.monitorFreq = float(self.setSampleRate.value())
		else:
			self.window.monitorFreq = 1
			self.setSampleRate.setValue(1)
		if float(self.setLevelRate.value()) >= 1:
			self.window.levelFreq = float(self.setLevelRate.value())
		else:
			self.window.levelFreq = 1
			self.setLevelRate.setValue(1)
		self.window.boilAvg = float(self.setBoilAvg.value())
		self.window.magTempInput = str(self.magTempIn.text())
		self.window.sampleTempInput = str(self.sampleTempIn.text())
		self.window.boilAvgValue.setText(str(self.setBoilAvg.value()))
		self.window.boilAvgValue.setStyleSheet("QLabel#boilAvgValue {font-size: 16pt; color: rgb(168,168,168);}")
		self.close()
	def cancel_(self):
		self.close()
	def closeEvent(self, e):
		self.close()




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
		self.boilAvg = 1.5
		#Parameters to indicate when and how often to update the boil off rate
		self.updateAvgBoilOffTime = 0
		self.updateAvgBoilOffSecs = 30
		#Parameter to indicate when and how often to update the boil off rate
		self.updateRefillTime = 0
		self.updateRefillSecs = 30
		#Number of data points used to compute the average boil-off rate
		self.boilOffPts = int(3600 * float(self.boilAvg * self.monitorFreq))
		#Threshold helium level in cm
		self.levelThresh = 0
		#Level monitor reading in percent that corresponds to the bottom of the belly.
		self.bellyLevel = 30
		#Inputs from the magnet and sample thermometers
		self.magTempInput = str('B')
		self.sampleTempInput = str('D5')

		#Keeps trck of most important connections
		self.labCxns = {"labRAD" : False , "datavault" : False , 'devServers' : {"lm_510" : False, "lk_350" : False, "ips_120" : False}}
		#Registers which devices are plugged in
		self.devCxns = {"lm_510" : False, "lk_350" : False, "ips_120": False}
		#Registers whether the logged data is being uploaded to the group website
		self.sqlCxn = False
		
		self.startMgr()
		
		#self.startServers()
		
		#self.connectLabRAD()

	def startMgr(self):	
		self.dvPrc = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE, shell = True)
		self.dvPrc.stdin.write(dvPath)
		print "opened data vault"
		time.sleep(1)
		
		self.serSrv = Popen( ["cmd.exe"], stdin = PIPE, stdout = PIPE, shell = True)
		self.serSrv.stdin.write(serSrvPath)
		print "opened serial server"
		time.sleep(1)
		
		self.gpibSrv = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE, shell = True)
		self.gpibSrv.stdin.write(gpibSSrvPath)
		print "opened gpib server"
		time.sleep(1)
		
		self.gpibMan = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE, shell = True)
		self.gpibMan.stdin.write(gpibManPath)
		print "opened gpib manager"
		time.sleep(5)
		
		
		for server in self.devCxns.keys():
			self.startServer(server, "cxn")
			time.sleep(1)
			
		self.connectLabRAD(self.reactor)
		

	def startServer(self, server, action):
	
		if server == 'lm_510':
			if action == "cxn":
				self.lm510Prc = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE, shell = True)
				self.lm510Prc.stdin.write(lm510Path)
				print "opened lm_510"
			elif action == "end":
				try:
					x = self.lm510Prc.pid
					Popen("TASKKILL /F /PID {pid} /T".format(pid=x))
					print "closed lm_510 server"
				except:
					print "Cannot close lm_510 process"

			
		elif server == 'lk_350':
			if action == "cxn":
				self.lk350Prc = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE, shell = True)
				self.lk350Prc.stdin.write(lk350Path)
				print "opened lk_350"
			elif action == "end":
				try:
					x = self.lk350Prc.pid
					Popen("TASKKILL /F /PID {pid} /T".format(pid=x))
					print "closed lk_350 server"
				except:
					print "Cannot close lk_350 process"

			
		elif server == 'ips_120':
			if action == "cxn":
				self.ips120 = Popen( ["cmd.exe"], stdin = PIPE, stdout =PIPE, shell = True)
				self.ips120.stdin.write(ips120Path)
				print "opened ips_120"
			elif action == "end":
				try:
					x = self.ips120.pid
					Popen("TASKKILL /F /PID {pid} /T".format(pid=x))
					print "closed ips_120 server"
				except:
					print "Cannot close ips_120 process"
		
	@inlineCallbacks
	def connectLabRAD(self, c = None):
		from labrad.wrappers import connectAsync

		try:
			self.cxn = yield connectAsync(name = 'mScopeMonitor')
			self.labCxns["labRAD"] = True
			print 'LabRAD initialization complete.'
		except:
			print 'LabRAD connection failed.'

		try:
			self.dv = yield self.cxn.data_vault
			self.labCxns["datavault"] = True
			print 'Data Vault connection complete.'
		except:
			print "Data Vault connection failed"

		try:
			yield self.dv.cd('4K nSOT Microscope Monitor')
		except:
			yield self.dv.mkdir('4K nSOT Microscope Monitor')
			yield self.dv.cd('4K nSOT Microscope Monitor')
		print 'Navigated to microscope monitor logging folder.'

		#If LabRAD and Data Vault are connected, connects device servers and selects devices
		if self.labCxns["labRAD"] == True and self.labCxns["datavault"] == True:
			yield self.sleep(1)
			print "Starting device connections"
			self.GPIB_SRV = self.cxn.minint_o9n40pb_gpib_bus
			for dev in self.devCxns.keys():
				yield self.connectDevice(dev)
				yield self.sleep(0.5)

		else:
			print "Cannot start monitoring"
		
		#Sets serve indicator green if all devices are selected 
		if not False in self.devCxns.values():
			print "green"
			self.serverCxn.setStyleSheet("#serverCxn{" + 
			"background: rgb(0, 170, 0);border-radius: 4px;}")
		else:
			self.serverCxn.setStyleSheet("#serverCxn{" + 
			"background: rgb(161, 0, 0);border-radius: 4px;}")
		print 'here'
		#Starts monitoring as long as all servers are started
		if True in self.labCxns["devServers"].values():
			print "Starting monitor"
			self.monitor_time = time.time()
			yield self.monitor()
		else:
			"Cannot start monitoring"
		

	@inlineCallbacks
	def connectDevice(self, dev, c = None):
		if dev == "lk_350":
			try:
				self.lk = yield self.cxn.lakeshore_350
				self.labCxns['devServers']['lk_350'] = True
				print 'got lk'
			except:
				print 'lm_350 server unavailable'
			try:
				yield self.lk.select_device()
				self.devCxns["lk_350"] = True
				print "selected lk"
			except:
				print "lk_350 selection failed"
		
		elif dev == 'lm_510':
			try:
				self.lm = yield self.cxn.lm_510
				self.labCxns['devServers']['lm_510'] = True
				print 'got lm'
			except:
				print 'lm server unavailable'
			try:
				yield self.lm.select_device()
				yield self.sleep(0.5)
				yield self.lm.remote()
				self.devCxns["lm_510"] = True
				print 'selected lm'
			except:
				print 'lm_510 selection failed'
				
		elif dev == 'ips_120':
			try:
				self.ips = yield self.cxn.ips120_power_supply
				self.labCxns['devServers']['ips_120'] = True
				print 'got ips'
			except:
				print 'ips server unavailable'
			try:
				yield self.ips.select_device()
				yield self.sleep(1.0)
				yield self.ips.set_control(3)
				self.devCxns["ips_120"] = True
				print 'selected ips'
			except:
				print 'ips_120 selection failed'


	@inlineCallbacks
	def reconnectDevices(self, c = None):
		for dev in self.devCxns.keys():
			if self.devCxns[dev] == False:
				yield self.startServer(dev, "end")
				yield self.sleep(1)
				yield self.startServer(dev, "cxn")
				yield self.sleep(1)
				yield self.connectDevice(dev)
				
	@inlineCallbacks
	def upadte_database(data, c = None):
		try:
			date = str(data[0][1]) + '/' + str(data[0][2]) + '/' + str(data[0][0])
			time = data[0][3]*3600 + data[0][4]*60 + data[0][5]
			magnet_temp = data[1]
			sample_temp = data[2]
			level = data[3]
			field = data[4]

			yield cur.execute("""INSERT INTO 4KSQUID
							VALUES ({},{},{},{},{},{})""".format(date, time, magnet_temp, sample_temp, level, field))
			yield db.commit()

		except:
			yield self.sleep(60)
			print "RECONNECTING...."
			try:
				db = yield MySQLdb.connect(host="192.185.4.111",
						 user="afy2003",
						  passwd="E4rmsrV+tw3r",
						  db="afy2003_BF")

				cur = yield db.cursor()
			except:
				print "RECONNECTION FAILED.. trying again in 60s"
					
				
	
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
		try:
			yield self.lm.set_units("PERCENT")
		except:
			self.devCxns["lm_510"] = False
		i = 0
		while time.localtime()[2] == day:

			if self.monitoring == True:
				self.checkHour = time.localtime()[4]
				now = time.time()
				#checks if it's time to read the temperature and field and does so as needed
				if ((now - refTimes[0]) > self.monitorFreq)or i == 0:

					try:
						temp = yield self.lk.read_temp(self.magTempInput)
						temp = float(temp.replace("+", ""))
						sampTemp = yield self.lk.read_temp(self.sampleTempInput)
						sampTemp = float(sampTemp.replace("+", ""))
						self.devCxns["lk_350"] = True
					except:
						sampTemp = 0
						temp = 0
						self.devCxns["lk_350"] = False
					try:
						yield self.ips.set_control(3)
						field =  yield self.ips.read_parameter(7)
						yield self.ips.set_control(2)
						field = field.replace("'", "")
						field = field.replace("R", "")
						field = float(field)
						self.devCxns["ips_120"] = True
					except:
						field = 0
						self.devCxns["ips_120"] = False

					refTimes[0] = time.time()
				else:
					pass

				#checks to see if it's time to read the level and does so if needed
				if ((now - refTimes[1]) > self.levelFreq) or i == 0:

					try:
						level = yield self.lm.measure()
						self.devCxns["lm_510"] = True
					except:
						level = 0
						self.devCxns["lm_510"] = False

					refTimes[1] = time.time()
				else:
					pass

				dataTime = np.round((now - self.monitor_time)/3600, decimals = 4)
				logTime = np.round((now - self.daily_monitor_time)/3600, decimals = 4)
				yield self.dv.add(i, logTime, float(temp), float(sampTemp), float(field), float(level))
				#print temp, sampTemp, field, level, dataTime
				data = [time.localtime(), temp, sampTemp, float(level), float(field)]
				try:
					self.updatePlots([sampTemp, float(field), float(level), temp], dataTime)
				except:
					print dt.datetime.now().strftime("%m-%d %H:%M"), ': Error encountered in plot update'
				#yield self.update_database(data, self.reactor)
				try:
					ddate = dt.datetime.now().strftime("%Y-%m-%d")
					dtime = dt.datetime.now().strftime("%X")
					dcurr = int((dt.datetime.strptime(ddate+','+dtime, "%Y-%m-%d,%X")- dt.datetime(1970,1,1)).total_seconds())+ 3600*7
					yield cur.execute("""INSERT INTO nSOT_4K_CRYO
									VALUES ({},{},{},{},{})""".format(dcurr, float(level), float(field), float(sampTemp), float(temp)))
					yield db.commit()
					self.sqlCxn = True
					#print 'added to db'
				except:
					print dt.datetime.now().strftime("%m-%d %H:%M"), ': Database connection lost... Logging data is not being upload to the group website'
					self.sqlCxn = False
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
				#print start

			elif self.monitoring == False:
				pass
			i += 1
		#Restarts the loop at the end of the day
		yield self.monitor(self.reactor)
	
	def updatePlots(self, data, dataTime):
		new_sampTemp = data[0]
		new_field = data[1]
		new_level = 100 * (data[2] - self.bellyLevel) / (100 - self.bellyLevel)
		new_time = dataTime
		magnetTemperature = data[3]

		if len(self.timePts) == 0 or self.timePts[-1] - self.timePts[0] < self.plot_hours:

			self.tempPts = np.concatenate((self.tempPts, [new_sampTemp]), axis = 0)
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
			
			self.tempPts = np.concatenate((self.tempPts, [new_sampTemp]), axis = 0)
			self.fieldPts = np.concatenate((self.fieldPts, [new_field]), axis = 0)
			self.levelPts = np.concatenate((self.levelPts, [new_level]), axis = 0)
			self.timePts = np.concatenate((self.timePts, [new_time]), axis = 0)

		if self.devCxns["lk_350"] == True:
			self.tempPlot.clear()
			self.tempPlot.plot(x = self.timePts - self.timePts[0], y = self.tempPts, pen = 0.5)
			self.tempValue.display(new_sampTemp)
			self.magnetTemp.display(magnetTemperature)
		else:
			self.tempValue.setDigitCount(5)
			self.tempValue.display("-----")
			self.sampleTemp.setDigitCount(5)
			self.sampleTemp.display("-----")

		if self.devCxns["ips_120"] == True:
			self.fieldPlot.clear()
			self.fieldPlot.plot(x = self.timePts - self.timePts[0], y = self.fieldPts, pen = 0.5)
			new_field = np.round(float(new_field), decimals = 4)
			self.fieldValue.setDigitCount(len(str(new_field)))
			self.fieldValue.display(new_field)

		else:
			self.fieldValue.setDigitCount(5)
			self.fieldValue.display("-----")
		
		if self.devCxns["lm_510"] == True:
			self.levelPlot.clear()
			self.levelPlot.plot(x = self.timePts - self.timePts[0], y = np.round(self.levelPts, decimals = 3), pen = 0.5)
			self.levelValue.display(new_level)
		else:
			self.levelValue.setDigitCount(5)
			self.levelValue.display("-----")
		
		



		#Takes the last number of helium level data points and computes the average boil-off rate in %/hr
		if self.devCxns["lm_510"] == True and len(self.levelPts) > 2:
			avgTime = self.boilAvg
			backTime = self.timePts[-1] - avgTime
			tBack = np.absolute(self.timePts - backTime)
			argBack = np.argmin(tBack)
			#levelChange = self.levelPts[argBack] - self.levelPts[-1]
			
			boilFit = np.polyfit(self.timePts[argBack::], self.levelPts[argBack::], 1)
			intcpt, avgBoilOff = boilFit[1], -boilFit[0]
			
			#avgBoilOff = float(levelChange / avgTime)
			if (time.time() - self.updateAvgBoilOffTime) > self.updateAvgBoilOffSecs:
				self.boilRate.display(np.round(avgBoilOff, decimals = 2))
				self.updateAvgBoilOffTime = time.time()
			#intcpt = self.levelPts[-1]  +  (avgBoilOff * self.timePts[-1])
			avgLine = np.round(-avgBoilOff * self.timePts[argBack::] + intcpt, decimals = 3)
			self.levelPlot.plot(x = self.timePts[argBack::] - self.timePts[0], y = avgLine, pen = pg.mkPen(color = (255, 0, 0)))


			#Finds the time until the helium level reaches the specified threshold assuming the boil-off rate found above
			avgBoilOff = float(avgBoilOff / 3600)
			if avgBoilOff != 0 and avgBoilOff>0 and len(self.timePts)>2 and (self.levelPts[-1] > self.levelThresh):
				refillSecs = float((self.levelPts[-1] - self.levelThresh) / avgBoilOff)
				refillDays = int(refillSecs/86400)
				refillHours = np.round(((refillSecs - 86400*refillDays) / 3600), decimals = 2)

				dispDays = str(refillDays)
				dispHours = str(refillHours)

				if refillDays != 0 and refillDays < 99:
					dispTime = dispDays + 'D ' + dispHours + 'hr'


				elif refillDays == 0 and refillHours != 0:
					dispTime = dispHours + 'hr'

				else:
					dispTime = "--:--"
					
				if (time.time() - self.updateRefillTime) > self.updateRefillSecs:
					self.refillTime.setDigitCount(len(dispTime))
					self.refillTime.display(dispTime)
					self.updateRefillSecs = time.time()

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
		self.rCxn = reconnectDev(self.reactor, self.devCxns, self.sqlCxn, self)
		self.rCxn.show()

		
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