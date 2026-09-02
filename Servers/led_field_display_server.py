'''
I am making this code modeled on the Young Lab Wiki page for "Servers" as well as the lm_510.py 
file on the GUI for nanoSQUID Scanning Software
'''



"""
### BEGIN NODE INFO

[info]
name = led_field_display
version = 1.0
description = LED Field Display Server - drives the ESP32-S3 HUB75 status panel

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
serial_server_name = (platform.node() + '_serial_server').replace('-','_').lower()

from labrad.server import setting, Signal
from labrad.devices import DeviceServer, DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import labrad.units as units
from labrad.types import Value
from twisted.internet import reactor
from twisted.internet.task import deferLater


#Where in the LabRAD registry the port lives. Same layout lm_510 uses: one key per panel
#under Links, whose value is a (serial server name, com port) pair. See loadConfigInfo.
REGISTRY_PATH = ['', 'Servers', 'led_field_display', 'Links']

TIMEOUT = Value(5,'s')
BAUD = 115200 
BYTESIZE = 8
STOPBITS = 1
PARITY = None

'''
This code is for the LED Field Display about the 3HE system. IT is a 63 x 32 field display controlled by an ESP32 RGB
microcontroller.
'''

#list of codes that correspond to what is being sent to the microcontroller
STATE_CODES = {
        'Idle'                      : 'b0',
        'Idle - Withdrawn'          : 'b1',
        'Idle - Aborted'            : 'b2',
        'approaching'               : 'b3',
        'Surface Contacted'         : 'b4',
        'moving_to_constant_height' : 'b5',
        'at_constant_height'        : 'b6',
        'extension_failed'          : 'b7',
        'Withdrawing'               : 'b8',
        'Collecting Threshold Data' : 'b9',
        'Retracting Attocubes'      : 'b10',
        'Scanning'                  : 'b11',
        'Idle - Scan Ended'         : 'b12',
        }

#states who we need the constant_height parameter for.
HEIGHT_STATES = ('moving_to_constant_height', 'at_constant_height')

#Colors that just fill the screen with eitehr red or green.
FILL_COLORS = ('red', 'green')

#Seconds to wait after the port is opened for the microcontroller to accept/do its first commmand
SETTLE_TIME = 2.0

#The state the panel is parked on whenever a client goes away or the server stops. The
#panel holds whatever it was last told until something tells it otherwise, so without this
#a closed GUI leaves an approach that finished hours ago sitting up on the wall.
IDLE_STATE = 'Idle'


class serverInfo(object):
    '''
    declaring the device and server name, this is from lm_510.py
    '''
    def __init__(self):
        self.deviceName = 'ESP32 LED Field Display'
        self.serverName = 'led_field_display'

    def getDeviceName(self,comPort):
        return "%s (%s)"%(self.serverName,comPort)


class LEDFieldDisplayWrapper(DeviceWrapper):

    @inlineCallbacks
    def connect(self, server, port):
        '''
        This is run once (not by me, automaatically). it asks the serial monitor to open the port and set it up
        and thrwos away anythign sitting in the incoming buffer.
        '''
        print('connecting to "%s" on port "%s"...' % (server.name, port), end=' ')

        self.server = server            
        self.ctx = server.context()     
        self.port = port                
        p = self.packet()
        p.open(port)
        p.baudrate(BAUD)
        p.bytesize(BYTESIZE)
        p.stopbits(STOPBITS)
        p.read()
        p.timeout(TIMEOUT)
        yield p.send()

        #Gives the panel a little "settle time" before taking the first command - 
        yield deferLater(reactor, SETTLE_TIME, lambda: None)
        print("Connected")

    @inlineCallbacks
    def shutdown(self):
        '''
        sets the panel to IDLE mode and then shuts down.
        '''
        try:
            yield self.write(STATE_CODES[IDLE_STATE] + '\n')
        except Exception:
            #Panel already unplugged, or the serial server went away first. Nothing to
            #park, so just close up.
            print("Could not set the LED field display to Idle before closing the port.")

        try:
            '''shuts down'''
            yield self.packet().close().send()
        except Exception:
            #We are shutting down either way, so a failed close must not take the rest
            #of the shutdown sequence down with it.
            pass

    def packet(self):
        '''
        Create a packet in our private context
        '''
        return self.server.packet(context=self.ctx)

    @inlineCallbacks
    def read(self):
        '''
        Asks the serial server for one line of whatever the panel has sent back
        to us. 
        '''
        p = self.packet()
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)

    @inlineCallbacks
    def write(self, code):
        '''
        Sends one line of cod toward the panel.
        '''
        yield self.packet().write(code).send()

    @inlineCallbacks
    def query(self, code):
        '''
        Write, then read
        '''
        p = self.packet()
        p.write_line(code)
        p.read_line()
        ans = yield p.send()
        returnValue(ans.read_line)


class LEDFieldDisplayServer(DeviceServer):
    '''
    This is the server itself
    '''
    deviceName = 'ESP32 LED Field Display'
    name = 'led_field_display'
    deviceWrapper = LEDFieldDisplayWrapper

    @inlineCallbacks
    def initServer(self):
        '''
        Runs once, automatically, the moment this server starts up. Reads which serial
        server and port to use out of the registry, then lets DeviceServer go find the
        panel.
        '''
        print('loading config info...', end=' ')
        self.reg = self.client.registry()
        yield self.loadConfigInfo()
        print('done.')
        print(self.serialLinks)
        yield DeviceServer.initServer(self)

    @inlineCallbacks
    def loadConfigInfo(self):
        '''
        load configuration info from registry
        '''
        reg = self.reg
        yield reg.cd(REGISTRY_PATH, True)
        dirs, keys = yield reg.dir()

        if not keys:
            self.serialLinks = {}
            print()
            print('No panels listed in the registry. Add a key under')
            print('    %s' % (' > '.join(REGISTRY_PATH[1:]),))
            print('whose value is a (serial server, port) pair, for example')
            print("    led_panel = ('%s', 'COM4')" % (serial_server_name,))
            print('then call Refresh Devices. (That server name is a guess from this')
            print("machine's hostname - use whatever your serial server actually calls itself.)")
            return

        p = reg.packet()
        for k in keys:
            p.get(k, key=k)
        ans = yield p.send()
        self.serialLinks = dict((k, ans[k]) for k in keys)

    @inlineCallbacks
    def findDevices(self):
        '''
        Determines whether the panel is reachable. Finds available devices from list stored in registry
        '''
        yield self.loadConfigInfo()

        devs = []
        for name, (serServer, port) in list(self.serialLinks.items()):
            if serServer not in self.client.servers:
                # means the serial server is not in servers
                print('serial server "%s" is not running' % (serServer,))
                continue
            server = self.client[serServer]
            ports = yield server.list_serial_ports()
            if port not in ports:
                #the port named in the registry is not attainable.
                print('port "%s" not found. Ports on this machine: %s' % (port, ports))
                continue
            devName = '%s - %s' % (serServer, port)
            devs += [(devName, (server, port))]
        returnValue(devs)

    def expireContext(self, c):
        '''
        Runs when something disconnects.
        '''
        dev = None

        if 'device' in c:
            try:
                dev = self.devices[c['device']]
            except KeyError:
                pass

        DeviceServer.expireContext(self, c)

        if dev is None:
            return


        d = dev.write(STATE_CODES[IDLE_STATE] + '\n')
        d.addErrback(lambda reason: None)

    @setting(100)
    def connect(self, c, server, port):
        '''
        connects dev to server and port.
        '''
        dev = self.selectedDevice(c)
        yield dev.connect(server, port)

    @setting(2, 'Select Device',
                key=[': Select first device',
                     's: Select device by name',
                     'w: Select device by ID'],
                returns=['s: Name of the selected device'])
    def select_device(self, c, key=0):
        '''
        select_device command for the current context
        '''
        dev = self.selectDevice(c, key=key)
        return dev.name

    @setting(101, state='s', returns='s')
    def set_state(self, c, state):
        '''
        This function is the one refd in approach.py - it actually writes the byte to serial.
        '''
        dev = self.selectedDevice(c)
        code = STATE_CODES.get(state)

        if code is None:
            raise ValueError("Unknown LED field display state: %r" % (state,))

        yield dev.write(code + '\n')
        returnValue(code)

    @setting(102, state='s', height='v[]', returns='s')
    def set_state_with_height(self, c, state, height):
        '''
        Same as set_state, just adds a height for b5, b6
        '''
        dev = self.selectedDevice(c)
        code = STATE_CODES.get(state)

        if code is None:
            raise ValueError("Unknown LED field display state: %r" % (state,))

        message = code

        if state in HEIGHT_STATES:
            message = '%s, %d' % (code, int(round(height * 1e9)))

        yield dev.write(message + '\n')
        returnValue(message)

    @setting(103, color='s', returns='s')
    def fill(self, c, color):
        '''
        fills the panel with red or green (kinda just a test)
        '''
        dev = self.selectedDevice(c)
        color = color.lower()

        if color not in FILL_COLORS:
            raise ValueError("Unknown fill colour: %r (expected red or green)" % (color,))

        yield dev.write(color + '\n')
        returnValue(color)

    @setting(104, returns='*s')
    def list_states(self, c):
        '''
        Hands back every state name we can use (i.e. idle, idle-aborted, etc)
        '''
        return sorted(STATE_CODES.keys())

    @setting(105, returns='*s')
    def list_height_states(self, c):
        '''
        Hands back every state name that involves heights (really just b5, b6)
        '''
        return list(HEIGHT_STATES)

    @setting(106, state='s', returns='s')
    def get_code(self, c, state):
        '''
        tells you which "byte" i.e. b0,b1,b2,b3 that "state" refers to.
        '''
        code = STATE_CODES.get(state)

        if code is None:
            raise ValueError("Unknown LED field display state: %r" % (state,))

        return code

    '''
    Troubleshooting settings
    '''

    @setting(9001, v='v')
    def do_nothing(self, c, v):
        '''
        Accepts a value and does nothing with it. Confirms the server is up and answering
        without touching the panel.
        '''
        pass

    @setting(9002, returns='s')
    def read(self, c):
        '''
       Listens for whatever is coming back from the panel (largely things like "unknown cmd", etc)
        '''
        dev = self.selectedDevice(c)
        ret = yield dev.read()
        returnValue(ret)

    @setting(9003, phrase='s')
    def write(self, c, phrase):
        '''
        Sends whatever text you give it to the serial (this time, instead of being just code it could be anything)
        note that you have to add newline \n after each message
        '''
        dev = self.selectedDevice(c)
        yield dev.write(phrase)

    @setting(9004, phrase='s', returns='s')
    def query(self, c, phrase):
        '''
       Sends raw text to the device and waits for a return message. make sure to add \n
        '''
        dev = self.selectedDevice(c)
        yield dev.write(phrase)
        ret = yield dev.read()
        returnValue(ret)


__server__ = LEDFieldDisplayServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
