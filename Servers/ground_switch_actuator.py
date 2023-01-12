# General info about the serial server (section 1.1 on lab wiki)

"""
 ### BEGIN NODE INFO
[info]

name = Ground Switch Actuator
version = 1.0
description = This is server actuates a grounding switch to float/ground a signal.

[startup]
cmdline = %PYTHON% %FILE%
timeout = 10 ms

[shutdown]
message = 987654321
timeout = 10 ms
 ### END NODE INFO
"""

# Key import functions for serial server (section 1.2 on lab wiki)

from labrad.server import setting, Signal
from labrad.devices import DeviceServer, DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import labrad.units as units
from labrad.types import Value

# Define timeout and BAUD RATE (section 1.3 on lab wiki)
TIMEOUT = Value(50, 'ms')
BAUD = 115200  # change if not 9600


class GSAWrapper(DeviceWrapper):

    @inlineCallbacks
    def connect(self, server, port):
        """Connect to a device."""
        print('connecting to "%s" on port "%s"...' % (server.name, port), end=' ')
        self.server = server
        self.ctx = server.context()
        self.port = port
        p = self.packet()
        p.open(port)
        p.baudrate(BAUD)
        p.read()  # clear out the read buffer
        p.timeout(TIMEOUT)
        print("Connected")
        yield p.send()

    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)

    @inlineCallbacks
    def write(self, code):
        """Write a data value to the heat switch."""
        yield self.packet().write(code).send()

    @inlineCallbacks
    def read(self):
        p = self.packet()
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)

    @inlineCallbacks
    def query(self, code):
        """ Write, then read. """
        p = self.packet()
        p.write_line(code)
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)


class GroundSwitchActuator(DeviceServer):
    deviceName = 'grounding_circuit'
    name = 'ground_switch_actuator'
    deviceWrapper = GSAWrapper

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
        yield reg.cd(['', 'Servers', 'GroundSwitch', 'Links'], True)
        dirs, keys = yield reg.dir()
        p = reg.packet()
        for k in keys:
            p.get(k, key=k)
        ans = yield p.send()
        self.serialLinks = dict((k, ans[k]) for k in keys)

    @inlineCallbacks
    def findDevices(self):
        """Find available devices from list stored in the registry."""
        devs = []
        for name, (serServer, port) in self.serialLinks.items():
            if serServer not in self.client.servers:
                continue
            server = self.client[serServer]
            ports = yield server.list_serial_ports()
            if port not in ports:
                continue
            devName = '%s - %s' % (serServer, port)
            devs += [(devName, (server, port))]
        returnValue(devs)


    @setting(10, returns = 's')
    def start(self,c):
        '''Starts switch up and returns the state the switch is starting in.'''
        dev=self.selectedDevice(c)
        yield dev.write("startup")
        ans1 = yield dev.read()
        return ans1

    @setting(11, returns = 's')
    def ground(self,c):
        '''Switch actuates to ground.'''
        dev=self.selectedDevice(c)
        yield dev.write("ground")
        ans = yield dev.read()
        return ans

    @setting(12, returns = 's')
    def float(self,c):
        '''Switch actuates to float.'''
        dev=self.selectedDevice(c)
        yield dev.write("float")
        ans = yield dev.read()
        return ans

    @setting(13, returns = 'b')
    def is_grounded(self,c):
        '''Checks to see if the signal is grounded or not. 1 = the device is in the grounded state. 0 = the device is not in the grounded state.'''
        dev=self.selectedDevice(c)
        yield dev.write("is_grounded")
        ans = yield dev.read()
        print("---"+ans+'---') # For Debugging
        if ans == '1':
            return True
        elif ans == '0':
            return False
        else: # Try again, there is sometimes something in the serial buffer
            yield dev.write("is_grounded")
            ans = yield dev.read()
            print("+++"+ans+'+++') # For Debugging
            if ans == '1':
                return True
            elif ans == '0':
                return False
            else:
                raise Exception('is_grounded not responding to GND query')

__server__ = GroundSwitchActuator()

if __name__ == '__main__':
    from labrad import util

    util.runServer(__server__)
