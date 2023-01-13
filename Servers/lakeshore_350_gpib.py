 # Copyright []
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
### BEGIN NODE INFO
[info]
name = lakeshore_350
version = 1.0
description =
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import platform
global serial_server_name
serial_server_name = platform.node() + '_serial_server'

from labrad.server import setting
from labrad.gpib import GPIBManagedServer, GPIBDeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import labrad.units as units
from labrad.types import Value

TIMEOUT = Value(5,'s')
BAUD    = 57600
PARITY = 'O'
STOP_BITS = 1
BYTESIZE= 7


class Lakeshore350Wrapper(GPIBDeviceWrapper):
	@inlineCallbacks
	def read_temp(self, input):
		ans = yield self.query("KRDG?%s" %input)
		returnValue(ans)
	@inlineCallbacks
	def mode_read(self):
		ans = yield self.query("MODE?")
		returnValue(ans)
	@inlineCallbacks
	def mode_set(self, mode):
		yield self.write("MODE%i" %mode)
	@inlineCallbacks
	def reset(self):
		yield self.write("*RST")
	@inlineCallbacks
	def idn(self):
		ans = yield self.query("*IDN?")
		returnValue(ans)
	@inlineCallbacks
	def heater_pct(self, output):
		ans = yield self.query("HTR?%s" %output)
		returnValue(ans)
	@inlineCallbacks
	def heater_set(self, output, heater_resistance, max_current, max_user_current, current_pwr):
		yield self.write("HTRSET%s,%s,%s,%s,%s," %(output, heater_resistance, max_current, max_user_current, current_pwr))
	@inlineCallbacks
	def heater_read(self, output):
		ans = yield self.query("HTRSET?%i" %output)
		returnValue(ans)
	@inlineCallbacks
	def out_mode_set(self, output, mode, input, powerup_enable):
		yield self.write("OUTMODE%i,%i,%i,%i" %(output, mode, input, powerup_enable))
	@inlineCallbacks
	def out_mode_read(self, output):
		ans = yield self.query("OUTMODE?%i" %output)
		returnValue(ans)
	@inlineCallbacks
	def PID_set(self, output, prop, integ, deriv):
		yield self.write("PID%i,%f,%f,%f" %(output, prop, integ, deriv))
	@inlineCallbacks
	def PID_read(self, output):
		ans = yield self.query("PID?%i" %output)
		returnValue(ans)
	@inlineCallbacks
	def ramp_set(self, output, stat, rate):
		yield self.write("RAMP%i,%i,%f" %(output, stat, rate))
	@inlineCallbacks
	def ramp_read(self, output):
		ans = yield self.query("RAMP?%i" %output)
		returnValue(ans)
	@inlineCallbacks
	def ramp_stat(self, output):
		ans = yield self.query("RAMPST?%i" %output)
		returnValue(ans)
	@inlineCallbacks
	def range_set(self, output, range):
		yield self.write("RANGE%i,%i" %(output, range))
	@inlineCallbacks
	def range_read(self, output):
		ans = yield self.query("RANGE?%i" %output)
		returnValue(ans)
	@inlineCallbacks
	def setpoint(self, output, setp):
		yield self.write('SETP%i,%f'%(output, setp))
	@inlineCallbacks
	def setpoint_read(self, output):
		ans = yield self.query("SETP?%i" %output)
		returnValue(ans)
	@inlineCallbacks
	def jtemp(self):
		ans = yield self.query("TEMP?")
		returnValue(ans)
	@inlineCallbacks
	def autotune(self, output, mode):
		yield self.write("ATUNE%i,%i" %(output, mode))
	@inlineCallbacks
	def name_set(self, input, chname):
		yield self.write('INNAME '+str(input) +',"'+ str(chname)+'"')
	@inlineCallbacks
	def name_read(self, input):
		ans = yield self.query("INNAME?%s" %input)
		returnValue(ans)


class Lakeshore350Server(GPIBManagedServer):
	name = 'lakeshore_350'
	deviceName = 'LSCI MODEL350'
	deviceIdentFunc = 'identify_device'
	deviceWrapper = Lakeshore350Wrapper

	@setting(9988, server='s', address='s')
	def identify_device(self, c, server, address):
		print('identifying:', server, address)
		try:
			s = self.client[server]
			p = s.packet()
			p.address(address)
			p.write_termination('\r')
			p.read_termination('\r')
			p.write('V')
			p.read()
			p.write('V')
			p.read()
			ans = yield p.send()
			resp = ans.read[1]
			print('got ident response:', resp)
			if resp == 'LSCI,MODEL350,LSA14JG/#######,1.4':
				returnValue(self.deviceName)

		except Exception as e:
			print('failed:', e)
			raise


	@setting(101, returns='?')
	def idn(self, c):
		"""
		Identifies the device, response should be 'LSCI,MODEL350,LSA14JG/#######,1.4'.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.idn()
		returnValue(ans)
	@setting(102)
	def reset(self, c):
		"""
		Resets the control parameters to power-up settings.
		"""
		dev=self.selectedDevice(c)
		yield dev.reset()
	@setting(103, input ='s', returns='s')
	def read_temp(self, c, input):
		"""
		Reads the temperature at an input in degrees Kelvin. Input channels are labeled by letters 'A' - 'D'.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.read_temp(input)
		returnValue(ans)
	@setting(104, returns='s')
	def mode_read(self, c):
		"""
		Returns the device mode 0 = Local, 1 = Remote, 2 = Remote with Local Lockout.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.mode_read()
		returnValue(ans)
	@setting(105, mode = 'i')
	def mode_set(self, c, mode):
		"""
		Sets the device mode 0 = Local, 1 = Remote, 2 = Remote with Local Lockout.
		"""
		dev=self.selectedDevice(c)
		yield dev.mode_set(mode)
	@setting(106, output = 'i', returns='s')
	def heater_pct(self, c, output):
		"""
		Returns the heater output in percent for a specified output.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.heater_pct(output)
		returnValue(ans)
	@setting(107, output = 'i', heater_resistance = 'i', max_current = 'i', max_user_current = 'v[]', current_pwr ='i')
	def heater_set(self, c, output, heater_resistance, max_current, max_user_current, current_pwr):
		"""
		Modifies the heater settings for a specified output. The user should input the desired output, heater resistance
		(input 1 = 25Ohm, 2 = 50Ohm), maximum current output (0 = user specified [channel 1 only], 1 =0.707A, 2 = 1A, 3 = 1.14A,
		4 = 2A), maximum current output if user specified current maximum is in effect (channel 1 only), and whether the heater
		heater output displays current or power (1 = current, 2 = power).
		"""
		dev=self.selectedDevice(c)
		yield dev.heater_set(output, heater_resistance, max_current, max_user_current, current_pwr)
	@setting(108, output = 'i', returns='s')
	def heater_read(self, c, output):
		"""
		Reads the heater output setting for a specified output (the meaning of the returned list is documented in heater_set).
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.heater_read(output)
		returnValue(ans)
	@setting(109, output = 'i', mode = 'i', input = 'i', powerup_enable = 'i')
	def out_mode_set(self, c, output, mode, input, powerup_enable):
		"""
		Sets the output mode for a specified channel. User inputs which output to configure, the desired control mode (0 = Off,
		1 = PID Control, 2 = Zone, 3 = Open Loop, 4 = Monitor Out, 5 = Warmup Supply), which input to use for the control (1 = A,
		2 = B, 3 = C, 4 = D), and whether the output stays on or shuts off after a power cycle (0 = shuts off, 1 = remians on).
		"""
		dev=self.selectedDevice(c)
		yield dev.out_mode_set(output, mode, input, powerup_enable)
	@setting(110, output = 'i', returns='s')
	def out_mode_read(self, c, output):
		"""
		Reads the output mode settings for a specified output (the meaning of the returned list is documented in out_mode_set).
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.out_mode_read(output)
		returnValue(ans)
	@setting(111, output = 'i', prop = 'v[]', integ = 'v[]', deriv = 'v[]')
	def PID_set(self, c, output, prop, integ, deriv):
		"""
		Set the PID parameters for a specified output. 0.1 < P < 1000, 0.1 < I < 1000, 0 < D < 200.
		"""
		dev=self.selectedDevice(c)
		yield dev.PID_set(output, prop, integ, deriv)
	@setting(112, output = 'i', returns='s')
	def PID_read(self, c, output):
		"""
		Reads the PID parameters for a specified output.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.PID_read(output)
		returnValue(ans)
	@setting(113, output = 'i', stat = 'i', rate = 'v[]')
	def ramp_set(self, c, output, stat, rate):
		"""
		Set the ramp parameters for a specified output. Input the target output, whether you would like the ramping to be on = 1 or off = 0
		as well as the ramp rate in units of Kelvin/minute between 0.001 and 100K/min (rateof 0 turns ramping off).
		"""
		dev=self.selectedDevice(c)
		yield dev.PID_set(output, stat, rate)
	@setting(114, output = 'i', returns='s')
	def ramp_read(self, c, output):
		"""
		Reads the ramp parameters for a specified output.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.ramp_read(output)
		returnValue(ans)
	@setting(115, output = 'i', returns='i')
	def ramp_stat(self, c, output):
		"""
		Reads the ramp status for a specified output. Returns 0 if there is no ramp in progress and 1 if the output is ramping.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.ramp_stat(output)
		returnValue(ans)
	@setting(116, output = 'i', range = 'i')
	def range_set(self, c, output, range):
		"""
		Sets the range for a specified output. Outputs 1 and 2 have 5 available ranges, and outputs 3 and 4 are either 0 = off or 1 = on.
		"""
		dev=self.selectedDevice(c)
		yield dev.range_set(output, range)

	@setting(117, output = 'i', returns='i')
	def range_read(self, c, output):
		"""
		Reads the range for a specified output. Refer to the documentation for range_set for a description of the return value.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.range_read(output)
		returnValue(int(ans))

	@setting(118, output = 'i', setp = 'v[]')
	def setpoint(self, c, output, setp):
		"""
		Sets the temperature setpoint for a specified output.
		"""
		dev=self.selectedDevice(c)
		yield dev.setpoint(output, setp)
	@setting(119, output = 'i', returns='s')
	def setpoint_read(self, c, output):
		"""
		Reads the temperature setpoint for a specified output.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.setpoint_read(output)
		returnValue(ans)
	@setting(120, returns='s')
	def jtemp(self, c):
		"""
		Reads the temperature of the room-temperature ceramic block used in the device's thermocouple, in degrees Kelvin, in case you're curious.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.jtemp()
		returnValue(ans)
	@setting(121, output = 'i', mode = 'i')
	def autotune(self, c, output, mode):
		"""
		Autotunes the PID parameters for a specified output. The user also inputs a mode: 0 = tunes only P, 1 = tunes P and I, 2 = tunes P, I, and D.
		"""
		dev=self.selectedDevice(c)
		yield dev.autotune(output, mode)
	@setting(122, input = 's', chname = '?')
	def name_set(self, c, input, chname):
		"""
		Set the name of an input.
		"""
		dev=self.selectedDevice(c)
		yield dev.name_set(input, chname)
	@setting(123, input = 's')
	def name_read(self, c, input):
		"""
		Reads the name of an input.
		"""
		dev=self.selectedDevice(c)
		ans = yield dev.name_read(input)
		returnValue(ans)

	@setting(124, phrase = 's')
	def write(self,c,phrase):
		dev=self.selectedDevice(c)
		yield dev.write(phrase)


__server__ = Lakeshore350Server()

if __name__ == '__main__':
	from labrad import util
	util.runServer(__server__)
