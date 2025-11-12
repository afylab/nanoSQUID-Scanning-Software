
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
name = IPS 120_10 Superconducting Magnet Power Supply
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
from labrad.devices import DeviceServer, DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import labrad.units as units
from labrad.types import Value

TIMEOUT = Value(5,'s')
BAUD    = 9600

class IPS120Wrapper(DeviceWrapper):
    @inlineCallbacks
    def connect(self, server, port):
        """Connect to a device."""
        print('connecting to "%s" on port "%s"...' % (server.name, port), end=' ')
        self.server = server
        self.ctx = server.context()
        self.port = port
        p = self.packet()
        p.open(port)
        print('opened on port "%s"' %self.port)
        p.baudrate(BAUD)
        # p.parity(PARITY)
        # p.stopbits(STOP_BITS)
        # p.bytesize(BYTESIZE)
        p.read()  # clear out the read buffer
        p.timeout(TIMEOUT)
        print(" CONNECTED ")
        yield p.send()

    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)

    def shutdown(self):
        """Disconnect from the serial port when we shut down."""
        return self.packet().close().send()

    @inlineCallbacks
    def write(self, code):
        """Write a data value to the temperature controller."""
        yield self.packet().write(code).send()

    @inlineCallbacks
    def read(self):
        p=self.packet()
        p.read_line()
        ans=yield p.send()
        returnValue(ans.read_line)

    @inlineCallbacks
    def query(self, code):
        """ Write, then read. """
        p = self.packet()
        p.write_line(code)
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)

    @inlineCallbacks
    def set_control(self,mode):
        ans = yield self.query("C%i"%mode)
        returnValue(ans)

    @inlineCallbacks
    def set_comm_protocol(self,comm):
        yield self.write("Q%i"%comm)

    @inlineCallbacks
    def read_parameter(self,parameter):
        ans = yield self.query("R%i"%parameter)
        returnValue(ans)

    @inlineCallbacks
    def unlock(self,key):
        ans = yield self.query("U%i"%key)
        returnValue(ans)

    @inlineCallbacks
    def version(self):
        ans = yield self.query("V")
        returnValue(ans)

    @inlineCallbacks
    def wait(self,time):
        ans = yield self.query("W%i"%time)
        returnValue(ans)

    @inlineCallbacks
    def status(self):
        ans = yield self.query("X")
        returnValue(ans)

    @inlineCallbacks
    def set_activity(self,activity):
        ans = yield self.query("A%i"%activity)
        returnValue(ans)

    @inlineCallbacks
    def set_panelDisplay(self,parameter):
        ans = yield self.query("F%i"%parameter)
        returnValue(ans)

    @inlineCallbacks
    def set_switchHeater(self,mode):
        ans = yield self.query("H%i"%mode)
        returnValue(ans)

    @inlineCallbacks
    def set_targetCurrent(self,current):
        ans = yield self.query("I"+str(current))
        returnValue(ans)

    @inlineCallbacks
    def set_targetField(self,field):
        ans = yield self.query("J"+'{:f}'.format(field))
        returnValue(ans)

    @inlineCallbacks
    def set_mode(self,mode):
        ans = yield self.query("M%i"%mode)
        returnValue(ans)

    @inlineCallbacks
    def set_polarity(self,polarity):
        ans = yield self.query("P%i"%polarity)
        returnValue(ans)

    @inlineCallbacks
    def set_currentSweep_rate(self,rate):
        ans = yield self.query("S"+str(rate))
        returnValue(ans)

    @inlineCallbacks
    def set_fieldSweep_rate(self,rate):
        ans = yield self.query("T"+str(rate))
        returnValue(ans)

    @inlineCallbacks
    def load_ram(self,nKbytes):
        ans = yield self.query("Y%i"%nKbytes)
        returnValue(ans)

    @inlineCallbacks
    def dump_ram(self,nKbytes):
        ans = yield self.query("Z%i"%nKbytes)
        returnValue(ans)

    @inlineCallbacks
    def examine(self):
        ans = yield self.query('X')
        returnValue(ans)

    @inlineCallbacks
    def clearbuffer(self):
        ans = yield self.read()
        resp = ans
        while ans != '':
            ans = yield self.read()
            resp = resp + ans
        returnValue(resp)

class IPS120Server(DeviceServer):
    name = 'ips120_power_supply'
    deviceName = 'IPS120-10  Version 3.07  (c) OXFORD 1996'
    deviceWrapper = IPS120Wrapper

    @inlineCallbacks
    def initServer(self):
        print('loading config info...', end=' ')
        self.reg = self.client.registry()
        yield self.loadConfigInfo()
        print('done.')
        print(self.serialLinks)
        yield DeviceServer.initServer(self)

    @inlineCallbacks
    def loadConfigInfo(self):
        """Load configuration information from the registry."""
        reg = self.reg
        yield reg.cd(['', 'Servers', 'ips120_power_supply', 'Links'], True)
        dirs, keys = yield reg.dir()
        p = reg.packet()
        print(" created packet")
        print("printing all the keys",keys)
        for k in keys:
            print("k=",k)
            p.get(k, key=k)

        ans = yield p.send()
        print("ans=",ans)
        self.serialLinks = dict((k, ans[k]) for k in keys)


    @inlineCallbacks
    def findDevices(self):
        """Find available devices from list stored in the registry."""
        devs = []
        for name, (serServer, port) in list(self.serialLinks.items()):
            if serServer not in self.client.servers:
                continue
            server = self.client[serServer]
            print(server)
            print(port)
            ports = yield server.list_serial_ports()
            print(ports)
            if port not in ports:
                continue
            devName = '%s - %s' % (serServer, port)
            devs += [(devName, (server, port))]

       # devs += [(0,(3,4))]
        returnValue(devs)

    @setting(100)
    def connect(self,c,server,port):
        dev=self.selectedDevice(c)
        yield dev.connect(server,port)

    @setting(101, mode='i',returns='s')
    def set_control(self,c,mode):
        dev=self.selectedDevice(c)
        ans = yield dev.set_control(mode)
        returnValue(ans)

    @setting(102, comm='i')
    def set_comm_protocol(self,c,comm):
        dev=self.selectedDevice(c)
        yield dev.set_comm_protocol(comm)

    @setting(103, parameter='i', returns='s')
    def read_parameter(self,c,parameter):
        dev=self.selectedDevice(c)
        ans = yield dev.read_parameter(parameter)
        returnValue(ans)

    @setting(104, key='i', returns='s')
    def unlock(self,c,key):
        dev=self.selectedDevice(c)
        ans = yield dev.unlock(key)
        returnValue(ans)

    @setting(105, returns='s')
    def version(self,c):
        dev=self.selectedDevice(c)
        ans = yield dev.version()
        returnValue(ans)

    @setting(106, time='i', returns='s')
    def wait(self,c,time):
        dev=self.selectedDevice(c)
        ans = yield dev.wait(time)
        returnValue(ans)

    @setting(107, returns='s')
    def status(self,c):
        dev=self.selectedDevice(c)
        ans = yield dev.status()
        returnValue(ans)

    @setting(108, activity='i', returns='s')
    def set_activity(self,c,activity):
        dev=self.selectedDevice(c)
        ans = yield dev.set_activity(activity)
        returnValue(ans)

    @setting(109, parameter='i', returns='s')
    def set_panelDisplay(self,c,parameter):
        dev=self.selectedDevice(c)
        ans = yield dev.set_panelDisplay(parameter)
        returnValue(ans)

    @setting(110, mode='i', returns='s')
    def set_switchHeater(self,c,mode):
        dev=self.selectedDevice(c)
        ans = yield dev.set_switchHeater(mode)
        returnValue(ans)

    @setting(111, current='v', returns='s')
    def set_targetCurrent(self,c,current):
        dev=self.selectedDevice(c)
        ans = yield dev.set_targetCurrent(current)
        returnValue(ans)

    @setting(112, field='v', returns='s')
    def set_targetField(self,c,field):
        dev=self.selectedDevice(c)
        ans = yield dev.set_targetField(field)
        returnValue(ans)

    @setting(113, mode='i', returns='s')
    def set_mode(self,c,mode):
        dev=self.selectedDevice(c)
        ans = yield dev.set_mode(mode)
        returnValue(ans)

    @setting(114, polarity='i', returns='s')
    def set_polarity(self,c,polarity):
        dev=self.selectedDevice(c)
        ans = yield dev.set_polarity(polarity)
        returnValue(ans)

    @setting(115, rate='v', returns='s')
    def set_currentSweep_rate(self,c,rate):
        dev=self.selectedDevice(c)
        ans = yield dev.set_currentSweep_rate(rate)
        returnValue(ans)

    @setting(116, rate='v', returns='s')
    def set_fieldSweep_rate(self,c,rate):
        dev=self.selectedDevice(c)
        ans = yield dev.set_fieldSweep_rate(rate)
        returnValue(ans)

    @setting(117, nKbytes='i', returns='s')
    def load_ram(self,c,nKbytes):
        dev=self.selectedDevice(c)
        ans = yield dev.load_ram(nKbytes)
        returnValue(ans)

    @setting(118, nKbytes='i', returns='s')
    def dump_ram(self,c,nKbytes):
        dev=self.selectedDevice(c)
        ans = yield dev.dump_ram(nKbytes)
        returnValue(ans)

    @setting(119, returns='s')
    def examine(self, c):
        '''Returns information about the magnet in the format: XmnAnCnHnMmnPmn
        View ips120 manual for details.'''
        dev = self.selectedDevice(c)
        ans = yield dev.examine()
        returnValue(ans)

    @setting(120, returns='s')
    def clear_buffer(self, c):
        '''clear buffer'''
        dev = self.selectedDevice(c)
        ans = yield dev.clearbuffer()
        returnValue(ans)

    @setting(9001,v='v')
    def do_nothing(self, c, v):
        pass

    @setting(9002)
    def read(self,c):
        dev=self.selectedDevice(c)
        ret=yield dev.read()
        returnValue(ret)

    @setting(9003)
    def write(self,c,phrase):
        dev=self.selectedDevice(c)
        yield dev.write(phrase)
    @setting(9004)
    def query(self,c,phrase):
        dev=self.selectedDevice(c)
        yield dev.write(phrase)
        ret = yield dev.read()
        returnValue(ret)

__server__ = IPS120Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
