"""
### BEGIN NODE INFO
[info]
name = LM-510 Liquid Cryogen Level Monitor Server
version = 1.0
description = LM-510 Liquid Cryogen Level Monitor Server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

#import stuff
from labrad.server import setting,Signal
from labrad.devices import DeviceServer,DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import labrad.units as units
from labrad.types import Value

BAUD = 9600 # assumed as default
TIMEOUT = Value(5,'s')

class serverInfo(object):
    def __init__(self):
        self.deviceName = 'Cryomagnetics LM-510'
        self.serverName = 'LM_510'

    def getDeviceName(self,comPort):
        return "%s (%s)"%(self.serverName,comPort)

class LM510Wrapper(DeviceWrapper):

    @inlineCallbacks
    def connect(self, server, port):
        """Connect to a device."""
        print 'connecting to "%s" on port "%s"...' % (server.name, port),
        self.server = server
        self.ctx = server.context()
        self.port = port
        p = self.packet()
        p.open(port)
        p.baudrate(BAUD)
        p.read() #clear out the read buffer
        p.timeout(TIMEOUT)
        print("Connected")
        yield p.send()

    def packet(self):
        """Create a packet in our private context."""
        return self.server.packet(context=self.ctx)

        #shutdown?
        #read?
        #write?
        #quary?

class LM510Server(DeviceServer):
    name = 'LM-510 Monitor'
    deviceName = 'Cryomagnetics LM-510'
    deviceWrapper = LM510Wrapper

    @inlineCallbacks
    def initServer(self):
        print 'loading config info...',
        self.reg = self.client.registry()
        yield self.loadConfigInfo()
        print 'done.'
        print self.serialLinks
        yield DeviceServer.initServer(self)

    @inlineCallbacks
    def loadConfigInfo(self):
        """Load configuration information from the registry."""
        reg = self.reg
        yield reg.cd(['', 'Servers', 'LM_510', 'Links'], True)
        dirs, keys = yield reg.dir()
        p = reg.packet()
        print " created packet"
        print "printing all the keys",keys
        for k in keys:
            print "k=",k
            p.get(k, key=k)

        ans = yield p.send()
        print "ans=",ans
        self.serialLinks = dict((k, ans[k]) for k in keys)

    @inlineCallbacks
    def findDevices(self):
        """Find available devices from list stored in the registry."""
        devs = []
        for name, (serServer, port) in self.serialLinks.items():
            if serServer not in self.client.servers:
                continue
            server = self.client[serServer]
            print server
            print port
            ports = yield server.list_serial_ports()
            print ports
            if port not in ports:
                continue
            devName = '%s (%s)' % (serServer, port)
            devs += [(devName, (server, port))]

       # devs += [(0,(3,4))]
        returnValue(devs)

    @setting(100)
    def connect(self,c,server,port):
        dev=self.selectedDevice(c)
        yield dev.connect(server,port)  #not certain

    @setting(201,mode="s")
    def boost(self,c,mode):
        """
        Availabe Mode: ON, OFF, SMART
        The BOOST command sets the operating mode for the boost portion of a sensor read cycle.
        BOOST OFF will eliminate the boost portion of the read cycle, BOOST ON enables the boost portion on every read cycle, and BOOST SMART enables a boost cycle if no readings have been taken in the previous 5 minutes.
        """
        dev=self.selectedDevice(c)
        yield dev.write("BOOST %s\r" %mode)
        rep=dev.readline()#echo from USB interface, one magic feature of this monitor!!!

    @setting(202) #do I need mode here
    def get_boost_mode(self,c):
        """
        Get operating mode for the boost portion of a sensor read cycle.
        BOOST OFF will eliminate the boost portion of the read cycle, BOOST ON enables the boost portion on every read cycle, and BOOST SMART enables a boost cycle if no readings have been taken in the previous 5 minutes.
        """
        dev=self.selectedDevice(c)
        yield dev.write("BOOST?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    #CHAN and CHAN? function is not useful since we only have one channel.

    @setting(203,mode="s")
    def control_mode(self,c,mode):
        """
        Availabe Mode: AUTO, OFF, MANUAL
        Set the control mode of the channel to the selected mode.
        """
        dev=self.selectedDevice(c)
        yield dev.write("CTRL %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(204) #do I need mode here
    def get_control_mode(self,c):
        """
        Returns the status of the Control Relay (i.e., refill status) if the Control Relay is not already active, or the time in minutes since CTRL started if the Control Relay is active.
        "Off" indicates that a Ctrl Timeout has not occurred.
        "Timeout" indicates that the Ctrl High limit was not reached before the Timeout time was exceeded, and that Control Relay is inhibited until the operator resets the Ctrl Timeout by selecting MENU on the LM-510 or issuing a *RST command via the computer interface.
        The Timeout can be inhibited by setting the value to zero in the Ctrl Menu for the channel.
        """
        dev=self.selectedDevice(c)
        yield dev.write("CTRL?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(205,mode="s")
    def error_mode(self,c,mode):
        """
        Availabe Mode: 0, 1
        Set the error responce mode of the channel to the selected mode.
        0 - diable error reporting
        1 - enable error reporting
        """
        dev=self.selectedDevice(c)
        yield dev.write("ERROR %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(206) #do I need mode here
    def get_error_mode(self,c):
        """
        Query the selected error reporting mode.
        0 - diable error reporting
        1 - enable error reporting
        """
        dev=self.selectedDevice(c)
        yield dev.write("ERROR?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(207,mode="s")
    def set_high_alarm_threshold(self,c,mode):
        """
        Availabe Range: 0.0 to Sensor Length
        Set the threshold for the high alarm in the present units for the selected channel.
        If the liquid level rises above the threshold the alarm will be activated.
        The alarm will be disabled if the threshold is set to 100.0.
        """
        dev=self.selectedDevice(c)
        yield dev.write("H-ALM %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(208) #do I need mode here
    def get_high_alarm_threshold(self,c):
        """
        Query the high alarm threshold in the present units for the selected channel.
        """
        dev=self.selectedDevice(c)
        yield dev.write("H-ALM?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(209,mode="s")
    def set_high_threshold_control(self,c,mode):
        """
        Availabe Range: 0.0 to Sensor Length
        Set the high threshold for CTRL functions such as automated LM-510 Operating Instruction Manual - Version 1.2 refill completion.
        The present units for the selected channel are implied.
        A CTRL (refill) cycle is started when a reading is taken that is below the LOW limit.
        A CTRL (refill) cycle is completed when a reading is taken that is above the HIGH limit, or when the Ctrl Timeout configured in the CTRL menu is exceeded.
        A sensor is sampled as in continuous mode during CTRL, but when the HIGH limit is reach the selected sample interval will be used for future readings.
        """
        dev=self.selectedDevice(c)
        yield dev.write("HIGH %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(210) #do I need mode here
    def get_high_threshold_control(self,c):
        """
        Query the high threshold for Control functions (automated refill completion) in the present units for the selected channel.
        """
        dev=self.selectedDevice(c)
        yield dev.write("HIGH?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(211,mode="s")
    def set_sample_interval(self,c,mode):
        """
        Availabe Range: 00:00:00 to 99:59:59
        Set the time between samples for the selected Liquid Helium Level Meter channel.
        Time is in hours, minutes, and seconds.
        """
        dev=self.selectedDevice(c)
        yield dev.write("INTVL %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(212) #do I need mode here
    def get_sample_interval(self,c):
        """
        Query the time between samples for the selected Liquid Helium Level Meter channel.
        Time is in hours, minutes, and seconds.
        """
        dev=self.selectedDevice(c)
        yield dev.write("INTVL?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(213,mode="s")
    def set_low_alarm_threshold(self,c,mode):
        """
        Availabe Range: 0.0 to Sensor Length
        Set the threshold for the low alarm in the present units for the selected channel.
        If the liquid level rises above the threshold the alarm will be activated.
        The alarm will be disabled if the threshold is set to 0.0.
        """
        dev=self.selectedDevice(c)
        yield dev.write("L-ALM %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(214) #do I need mode here
    def get_low_alarm_threshold(self,c):
        """
        Query the low alarm threshold in the present units for the selected channel.
        """
        dev=self.selectedDevice(c)
        yield dev.write("L-ALM?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(215) #do I need mode here
    def get_sensor_length(self,c):
        """
        Query the active sensor length in the present units for the selected channel.
        The length is returned in centimeters if percent is the present unit selection.
        """
        dev=self.selectedDevice(c)
        yield dev.write("L-ALM?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(216,mode="s")
    def local_control(self,c,mode):
        """
        Returns control the front panel keypad after remote control has been selected by the REMOTE or RWLOCK commands.
        """
        dev=self.selectedDevice(c)
        yield dev.write("LOCAL\r" )
        rep=dev.readline()#echo from USB interface

    @setting(217,mode="s")
    def set_low_threshold_control(self,c,mode):
        """
        Availabe Range: 0.0 to Sensor Length
        Set the low threshold for Control functions such as automated refill activation.
        The present units for the selected channel are implied.
        A CTRL (refill) cycle is started when a reading is taken that is below the LOW limit.
        The sensor will be sampled in Continuous mode until the HIGH limit is reached.
        A CTRL cycle is completed when a reading is taken that is above the HIGH limit, or when the Ctrl Timeout configured in the CTRL menu is exceeded.
        """
        dev=self.selectedDevice(c)
        yield dev.write("LOW %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(218) #do I need mode here
    def get_high_threshold_control(self,c):
        """
        Query the low threshold for Control functions (automated refill completion) in the present units for the selected channel.
        """
        dev=self.selectedDevice(c)
        yield dev.write("LOW?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(219)#do I need mode here
    def measure(self,c,mode):
        """
        starts a measurement on the selected channel.
        The DATA READY bit for the selected channel will be set in the status byte returned by the *STB? command when the measurement is complete.
        """
        dev=self.selectedDevice(c)
        yield dev.write("MEAS 1\r" )
        rep=dev.readline()#echo from USB interface

    @setting(220) #do I need mode here
    def get_measure(self,c):
        """
        Query latest reading in the present units for the selected channel.
        If a reading for the selected channel is in progress, the previous reading is returned.
        """
        dev=self.selectedDevice(c)
        yield dev.write("MEAS? 1\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(221,mode="s")
    def set_sample_mode(self,c,mode):
        """
        Availabe Mode: S(Sample/Hold) or C(Continious)
        Set the sample mode for the selected channel.
        In Sample/Hold mode the measurements are taken when a MEAS command is sent via the computer interface, the <Enter> button is pressed on the front panel, or when the delay between samples set by the INTVL command expires.
        The interval timer is reset on each measurement, regardless of source of the measurement request.
        In Continuous mode measurements are taken as frequently as possible.
        The channel will also operate as in continuous mode any time a CTRL (refill) cycle has been activated by the level dropping below the LOW threshold until the CTRL cycle is completed by the HIGH threshold being exceeded or a *RST command.
        """
        dev=self.selectedDevice(c)
        yield dev.write("MODE %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(222) #do I need mode here
    def get_mode(self,c):
        """
        Query the sample mode for the previously selected channel.
        The sample mode may have been set by a MODE command or the front panel menu.
        """
        dev=self.selectedDevice(c)
        yield dev.write("MODE?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(223)
    def remote_control(self,c,mode):
        """
        Takes control of the LM-510 via the remote interface.
        All LM-510 Operating Instruction Manual - Version 1.2 buttons on the front panel are disabled except the Local button.
        This command will be rejected if the menu system is being accessed via the front panel or if LOCAL has been selected via the Local button on the front panel.
        Pressing the Local button again when the menu is not selected will allow this command to be executed.
        This command is only necessary for RS-232 operation since the IEEE-488 RL1 option provides for bus level control of the Remote and Lock controls.
        """
        dev=self.selectedDevice(c)
        yield dev.write("REMOTE\r" )
        rep=dev.readline()#echo from USB interface

    #RWLOCK might be same as REMOTE

    @setting(224) #do I need mode here
    def status(self,c):
        """
        Query detailed instrument status as decimal values, and the status of local menu selection.
        When an operator selects the Menu, the instrument is taken out of operate mode, and <Menu Mode> is returned as 1.
        <Menu Mode> is returned as 0 when in operate mode.
        Channel detailed status is returned as a decimal number where each bit indicates a status condition of the channel.
        """
        dev=self.selectedDevice(c)
        yield dev.write("STAT?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(225) #do I need mode here
    def channel_type(self,c):
        """
        Query for the channel type of the designated channel.
        0 denotes a liquid helium level sensor and 1 denotes a liquid nitrogen level sensor.
        """
        dev=self.selectedDevice(c)
        yield dev.write("TYPE? 1\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(226,mode="s")
    def set_units(self,c,mode):
        """
        Availabe Units: CM, IN, PERCENT or %
        Set the units to be used for all input and display operations for the channel.
        Units may be set to centimeters, inches,or percentage of sensor length.
        """
        dev=self.selectedDevice(c)
        yield dev.write("UNITS %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(227) #do I need mode here
    def get_units(self,c):
        """
        Query for the channel type of the designated channel.
        0 denotes a liquid helium level sensor and 1 denotes a liquid nitrogen level sensor.
        """
        dev=self.selectedDevice(c)
        yield dev.write("TYPE? 1\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(228,mode="s")
    def clear_status(self,c,mode):
        """
        Operates per IEEE Std 488.2-1992 by clearing the Standard Event Status Register (ESR) and resetting the MAV bit in the Status Byte Register (STB).
        """
        dev=self.selectedDevice(c)
        yield dev.write("*CLS\r" )
        rep=dev.readline()#echo from USB interface

    @setting(229,mode="s")
    def enable_standard_event(self,c,mode):
        """
        Standard Event Status Enable Command
        Availabe Range: 0 to 255
        Operate per IEEE Std 488.2-1992 by setting the specified mask into the Standard Event Status Enable Register (ESE).
        """
        dev=self.selectedDevice(c)
        yield dev.write("*ESE %s\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(230) #do I need mode here
    def query_ESE(self,c):
        """
        Standard Event Status Enable Query
        Operates per IEEE Std 488.2-1992 by returning the mask set in the Standard Event Status Enable Register (ESE) by a prior *ESE command.
        """
        dev=self.selectedDevice(c)
        yield dev.write("*ESE?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(231) #do I need mode here
    def query_ESR(self,c):
        """
        Standard Event Status Register Query
        Operate per IEEE Std 488.2-1992 by returning the contents of the Standard Event Status Register and then clearing the register.
        """
        dev=self.selectedDevice(c)
        yield dev.write("*ESR?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(232) #do I need mode here
    def self_identification(self,c):
        """
        Query Idenification
        Operate per IEEE Std 488.2-1992 by returning the LM-510 manufacturer, model, serial number and firmware level.
        """
        dev=self.selectedDevice(c)
        yield dev.write("*IDN?\r")
        rep=dev.readline()#echo from USB interface
        ans=dev.readline()
        returnValue(ans)

    @setting(233,mode="s")
    def operation_complete(self,c,mode):
        """
        Operation Complete Command
        Operate per IEEE Std 488.2-1992 by placing the Operation Complete message in the Standard Event Status Register (ESR).
        The LM-510 processes each command as it is received and does not defer any commands for later processing.
        """
        dev=self.selectedDevice(c)
        yield dev.write("*OPC\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(234,mode="s")
    def reset(self,c,mode):
        """
        Operates per IEEE Std 488.2-1992 by returning the LM-510 to its power up configuration.
        This selects channel 1 as the default channel, terminates any control (refill) sequence in progress, and clears any Ctrl Timeouts that may have occurred.
        If the optional parameter <hw> is provided, the instrument will perform a hardware reset one second later instead of returning to power up configuration as required by the Standard.
        """
        dev=self.selectedDevice(c)
        yield dev.write("*RST\r" %mode)
        rep=dev.readline()#echo from USB interface

    @setting(9001,v='v')
    def do_nothing(self,c,v):
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

__server__ = LM510Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
