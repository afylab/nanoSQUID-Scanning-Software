
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
name = 4G Superconducting Magnet Power Supply
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

from labrad.server import setting
from labrad.gpib import GPIBManagedServer, GPIBDeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import labrad.units as units
from labrad.types import Value

class Cryo4GWrapper(GPIBDeviceWrapper):
    @inlineCallbacks
    def initialize(self):
        '''
        Check if the supply is configured for dual channels by trying the CHAN command which
        only returns if there are two channels.
        '''
        self.configured = False
        self.gauss_to_amps = 0
        self.maxrate = 0

        try:
            ans = yield self.query("CHAN?")
            print("Dual Channel Mode")
            self.dual_channel = True
        except:
            print("Single Channel Mode")
            self.dual_channel = False

    def configure_magnet(self, gauss_to_amps, maxrate):
        '''
        Configuration required in order to change the field (except zeroing the magnet).

        Units:
        gauss_to_amps in G/A
        maxrate in T/min
        '''
        self.gauss_to_amps = float(gauss_to_amps)

        # The magnet needs rate in A/s, need to convert
        self.maxrate = maxrate*166.667/self.gauss_to_amps
        self.configured = True

    @inlineCallbacks
    def get_chan(self):
        if self.dual_channel:
            ans = yield self.query("CHAN?")
            returnValue(ans)
        else:
            returnValue(1)

    @inlineCallbacks
    def set_chan(self, chan):
        if chan == 1 or chan == 2:
            if self.dual_channel:
                ans = yield self.write("CHAN "+str(chan))
                returnValue(chan)
            else:
                returnValue(1)
        else:
            returnValue("INVALID CHANNEL")

    @inlineCallbacks
    def get_units(self):
        '''
        Get the output units (Amps or gauss). Units will often switch between field and current.

        Units on the 4G are weird, it can only communicate in kG or A remotly, but can display tesla
        on the fron panel. If you set the units to tesla using the from panel you can't get connect
        units using remote commands. If you set units to tesla using the remote commands it will display
        Tesla but immediatly switch to gauss when using remote commands. It's best to just leave it
        in Guass and not touch it on the from panel.
        '''
        ans = yield self.query("UNITS?")
        if ans == "T":
            print("Warning! Units of Tesla may cause communications problems.")
        returnValue(ans)

    @inlineCallbacks
    def get_ouput_current(self):
        '''
        Get the power supply output current in units of Amps
        '''
        yield self.write("UNITS A")
        ans = yield self.query("IOUT?")
        if "A" in ans:
            ans = ans.replace("A","")
            ans = float(ans)
            returnValue(ans)
        else: # Changing the units can do weird things, see comment on get_units
            print("Warning! Remote communication units problem, wrong units for output current.")
            returnValue(ans)

    @inlineCallbacks
    def get_current(self):
        '''
        Get the magnet current in units of Amps
        '''
        yield self.write("UNITS A")
        ans = yield self.query("IMAG?")
        if "A" in ans:
            ans = ans.replace("A","")
            ans = float(ans)
            returnValue(ans)
        else: # Changing the units can do weird things, see comment on get_units
            print("Warning! Remote communication units problem, wrong units for current.")
            returnValue(ans)

    @inlineCallbacks
    def get_field(self):
        '''
        Get the magnet field in units of Tesla.

        If the persistent switch heater is ON the magnet current returned will be the same
        as the power supply output current. If the persistent switch heater is off, the
        magnet current will be the value of the power supply output current when the persistent
        switch heater was last turned off.
        '''
        yield self.write("UNITS G") # For some reason it will not read out inits in tesla
        ans = yield self.query("IMAG?")
        if "kG" in ans:
            ans = ans.replace("kG","")
            ans = 0.1*float(ans)
            returnValue(ans)
        else: # Changing the units can do weird things, see comment on get_units
            print("Warning! Remote communication units problem, wrong units for field.")
            returnValue(ans)

    @inlineCallbacks
    def sweep_to_field(self, field, rate):
        '''
        Sweep to a given field (in Telsa) at a given rate (Tela/Minute). Requires the device be
        configured (using configure_magnet).
        '''
        if not self.configured:
            print("Attempting to change the field before calling configure_magnet")
            returnValue("MAGNET NOT CONFIGURED")

        rate = rate*166.667/self.gauss_to_amps
        if rate > self.maxrate:
            print("Attempting to change the field before calling configure_magnet")
            returnValue("RATE EXCEEDS MAXIMUM SWEEP RATE")

        current = field*10000/self.gauss_to_amps

        # Get the current field to determine if you need to go up or down
        magnet_current = yield self.get_field()

        yield self.write("UNITS A") # Make sure everything is set and returned as current
        yield self.write("RATE 0 " + str(rate))

        if magnet_current > current: # Need to sweep down to the setpoint
            # Prevent an error thrown if LLIM is greater than ULIM
            ulim = yield self.query("ULIM?")
            ulim = float(ulim.replace("A",""))
            if ulim < current:
                if current < 0:
                    yield self.write("ULIM 0.0")
                else:
                    yield self.write("ULIM " + str(current+0.001))

            yield self.write("LLIM " + str(current))
            yield self.write("SWEEP DOWN")

        else: # Need to sweep up to the setpoint
            # Prevent an error thrown if ULIM is lower than LLIM
            llim = yield self.query("LLIM?")
            llim = float(llim.replace("A",""))
            if llim > current:
                if current > 0:
                    yield self.write("LLIM 0.0")
                else:
                    yield self.write("LLIM " + str(current-0.001))

            yield self.write("ULIM " + str(current))
            yield self.write("SWEEP UP")


        #yield self.write("IMAG "+str(10*field)) # Convert to kG
        returnValue("SWEEPING")

    @inlineCallbacks
    def zero_output(self):
        '''
        Brings the magnet output to zero. Equivalent to presseing the "Zero" button on the front panel.
        This may not zero out the persistent current if the magnet is in persistent mode.
        '''
        yield self.write("SWEEP ZERO")

    @inlineCallbacks
    def manual_query(self, comm):
        ans = yield self.query(comm)
        returnValue(ans)

    @inlineCallbacks
    def manual_write(self, comm):
        yield self.write(comm)


class Cryomagnetics_4G_Server(GPIBManagedServer):
    name = 'cryo_4G_power_supply'
    deviceName = 'Cryomagnetics 4G'
    deviceIdentFunc = 'identify_device'
    deviceWrapper = Cryo4GWrapper

    @setting(100, gauss_to_amps='v', maxrate='v', returns='?')
    def configure_magnet(self,c, gauss_to_amps, maxrate):
        '''
        Enters the configuration parameters for the selected magnet. These are required in order to
        change the field (aside from zeroing the output).

        Args:
            gauss_to_amps : The field to current conversion in units of G/A
            maxrate : The maximum sweep rate for the field in Tesla/min (usually less than 1 T/min).
                We use the lowest rate specified by the manufactuer, see note below.

        Note about Max Rate:
        The 4G supply specifies multiple rates for different ranges of current to protect the magnet.
        The manufacturer of the magnet will give multiple rated ramp rates (e.g. 0-50A @0.2 A/s and
        50-60 A @ 0.1 A/s etc.). We want to be able to smoothly ramp the field for experiments so we
        set first range (range 0 on the controller) to the max field and then use the lowest rating
        specified by the manufacturer. This trades a small amount of time at low fields for a smooth
        ramp rate and safety. Most of the time we will not be operating near the maximum ramp rate.
        '''
        dev=self.selectedDevice(c)
        yield dev.configure_magnet(gauss_to_amps, maxrate)

    @setting(101, returns='?')
    def get_mode(self,c):
        '''
        Get the operating mode
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.query("MODE?")
        returnValue(ans)

    @setting(102, returns='?')
    def get_channel(self,c):
        '''
        Get the current output channel. Dual Ouput mode will return 1 or 2,
        otherwise returns 1 always.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_chan()
        returnValue(ans)

    @setting(103, channel='i', returns='?')
    def set_channel(self,c, channel):
        '''
        Get the current output channel. Dual Ouput mode only. Returns the selected channel.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.set_chan(channel)
        returnValue(ans)

    @setting(104, returns='?')
    def get_field(self, c):
        '''
        Get the field of the magnet.

        If the persistent switch heater is ON the magnet current (or field) returned will
        be the same as the power supply output current. If the persistent switch
        heater is off, the magnet current will be the value of the power supply
        output current when the persistent switch heater was last turned off. The
        magnet current will be set to zero if the power supply detects a quench.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_field()
        returnValue(ans)

    @setting(105, returns='?')
    def get_current(self, c):
        '''
        Get the current of the magnet.

        If the persistent switch heater is ON the magnet current (or field) returned will
        be the same as the power supply output current. If the persistent switch
        heater is off, the magnet current will be the value of the power supply
        output current when the persistent switch heater was last turned off. The
        magnet current will be set to zero if the power supply detects a quench.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_current()
        returnValue(ans)

    @setting(106, returns='?')
    def get_output_current(self, c):
        '''
        Get the output of the power supply.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_ouput_current()
        returnValue(ans)

    @setting(107, returns='?')
    def get_persist(self, c):
        '''
        Get the persistent mode. Returns True if the switch heater is off and the magnet is
        in persistent mode, returns False if the switch heater is on and the magnet is not
        in persistent mode.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.query("PSHTR?")
        if ans == '0':
            returnValue(True)
        else:
            returnValue(False)

    @setting(108, persist='b', returns='?')
    def set_persist(self, c, persist):
        '''
        Set the persistent mode. If persist is True will turn the heater off and go into persistent
        mode. If persist is False will turn the heater on.
        '''
        dev=self.selectedDevice(c)
        if persist:
            yield dev.write("PSHTR OFF")
        else:
            yield dev.write("PSHTR ON")
        returnValue(persist)

    @setting(109, field='v', rate='v', returns='s')
    def sweep_to_field(self, c, field, rate):
        '''
        Sweep to a given field (in Telsa) at a given rate (Tela/Minute). Requires the device be
        configured (using configure_magnet).
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.sweep_to_field(field, rate)
        returnValue(ans)

    @setting(110, returns='?')
    def zero_output(self, c, current):
        '''
        Brings the magnet output to zero. Equivalent to pressing the "Zero" button on the front panel.
        This may not zero out the persistent current if the magnet is in persistent mode.
        '''
        dev=self.selectedDevice(c)
        yield dev.zero_output()

    @setting(200, comm='s', returns='?')
    def manual_query(self, c, comm):
        '''
        Manually query the controller
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.manual_query(comm)
        returnValue(ans)

    @setting(201, comm='s', returns='?')
    def manual_write(self, c, comm):
        '''
        Manually write a command to the controller
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.manual_write(comm)
        returnValue(ans)


__server__ = Cryomagnetics_4G_Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
