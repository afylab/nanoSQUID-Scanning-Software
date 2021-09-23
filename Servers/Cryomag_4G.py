
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

import time

class Cryo4GWrapper(GPIBDeviceWrapper):
    @inlineCallbacks
    def initialize(self):
        '''
        Check if the supply is configured for dual channels by trying the CHAN command which
        only returns if there are two channels.
        
        Also sets the output units to Amps, DO NOT CHANGE THE UNITS AFTER THIS! It will cause headaches!
        '''

        try:
            ans = yield self.query("CHAN?")
            print("Dual Channel Mode")
            self.dual_channel = True
        except:
            print("Single Channel Mode")
            self.dual_channel = False
        
        ans = yield self.write("UNITS A;")

    @inlineCallbacks
    def get_chan(self):
        '''
        Get the active channel.
        '''
        if self.dual_channel:
            ans = yield self.query("CHAN?")
            returnValue(ans)
        else:
            returnValue(1)

    @inlineCallbacks
    def set_chan(self, chan):
        '''
        Set the active channel
        '''
        if chan == 1 or chan == 2:
            if self.dual_channel:
                ans = yield self.write("CHAN "+str(chan))
                returnValue(chan)
            else:
                returnValue('1')
        else:
            returnValue("INVALID CHANNEL (need 1 or 2)")

    @inlineCallbacks
    def get_units(self, chan):
        '''
        Get the output units (Amps or gauss). Units will often switch between field and current.

        Units on the 4G are weird, it can only communicate in kG or A remotly, but can display tesla
        on the front panel. If you set the units to tesla using the from panel you can't get connect
        units using remote commands. If you set units to tesla using the remote commands it will display
        Tesla but immediatly switch to gauss when using remote commands. It's best to just leave it
        in Guass and not touch it on the from panel.
        '''
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""
        ans = yield self.query(channel+"UNITS?")
        if ans == "T":
            print("Warning! Units of Tesla may cause communications problems.")
        returnValue(ans)

    @inlineCallbacks
    def get_output_current(self, chan):
        '''
        Get the power supply output current in units of Amps
        '''
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""
        # units = "UNITS A;" # Changing the units is slow!
        ans = yield self.query(channel+"IOUT?")
        if "A" in ans:
            ans = ans.replace("A","")
            ans = float(ans)
            returnValue(ans)
        else: # Changing the units can do weird things, see comment on get_units
            print("Warning! Remote communication units problem, wrong units for output current.")
            returnValue(ans)

    @inlineCallbacks
    def get_output_voltage(self, chan):
        '''
        Get the power supply output current in units of Amps
        '''
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""
        ans = yield self.query(channel+"VOUT?")
        if "V" in ans:
            ans = ans.replace("V","")
            ans = float(ans)
            returnValue(ans)
        else: # Changing the units can do weird things, see comment on get_units
            print("Warning! Remote communication units problem, wrong units for output current.")
            returnValue(ans)

    @inlineCallbacks
    def get_current(self, chan):
        '''
        Get the magnet current in units of Amps
        '''
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""
        #units = "UNITS A;" # Changing the units is slow!
        ans = yield self.query(channel+"IMAG?")
        if "A" in ans:
            ans = ans.replace("A","")
            ans = float(ans)
            returnValue(ans)
        else: # Changing the units can do weird things, see comment on get_units
            print("Warning! Remote communication units problem, wrong units for current.")
            returnValue(ans)

    # @inlineCallbacks
    # def get_field(self, chan):
    #     '''
    #     Get the magnet field in units of Tesla.
    # 
    #     If the persistent switch heater is ON the magnet current returned will be the same
    #     as the power supply output current. If the persistent switch heater is off, the
    #     magnet current will be the value of the power supply output current when the persistent
    #     switch heater was last turned off.
    #     '''
    #     if self.dual_channel:
    #         if chan == 1 or chan == 2:
    #             channel = "CHAN "+str(chan)+";"
    #         else:
    #             returnValue("INVALID CHANNEL (need 1 or 2)")
    #     else:
    #         channel = ""
    #     units = "UNITS G;" # For some reason it will not read out inits in tesla
    #     ans = yield self.query(channel+units+"IMAG?")
    #     if "kG" in ans:
    #         ans = ans.replace("kG","")
    #         ans = 0.1*float(ans)
    #         returnValue(ans)
    #     else: # Changing the units can do weird things, see comment on get_units
    #         print("Warning! Remote communication units problem, wrong units for field.")
    #         returnValue(ans)

    @inlineCallbacks
    def get_persist(self, chan):
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""
        ans = yield self.query(channel+"PSHTR?")
        if ans == '0':
            returnValue(True)
        else:
            returnValue(False)

    @inlineCallbacks
    def set_persist(self, chan, persist):
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""
        if persist:
            yield self.write(channel+"PSHTR OFF")
        else:
            yield self.write(channel+"PSHTR ON")
        returnValue(persist)

    @inlineCallbacks
    def sweep_current(self, chan, current, rate):
        '''
        Sweep to a given current (in A) at a given rate (in A/s)
        '''
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""

        #units = "UNITS A;" # Make sure everything is set and returned as current
        rate_set = "RATE 0 " + str(rate) + ";"

        # Get the current field to determine if you need to go up or down
        magnet_current = yield self.get_output_current(chan)
        if magnet_current > current: # Need to sweep down to the setpoint
            # Prevent an error thrown if LLIM is greater than ULIM
            ulim = yield self.query(channel+"ULIM?")
            ulim = float(ulim.replace("A",""))
            if ulim < current:
                if current < 0:
                    yield self.write(channel+"ULIM 0.0")
                else:
                    yield self.write(channel+"ULIM " + str(current+0.001))

            yield self.write(channel+"LLIM " + str(current))
            yield self.write(channel+rate_set+"SWEEP DOWN")

        else: # Need to sweep up to the setpoint
            # Prevent an error thrown if ULIM is lower than LLIM
            llim = yield self.query(channel+"LLIM?")
            llim = float(llim.replace("A",""))
            if llim > current:
                if current > 0:
                    yield self.write(channel+"LLIM 0.0")
                else:
                    yield self.write(channel+"LLIM " + str(current-0.001))

            yield self.write(channel+"ULIM " + str(current))
            yield self.write(channel+rate_set+"SWEEP UP")
        returnValue("SWEEPING")
    
    # @inlineCallbacks
    # def fast_sweep_current(self, chan, current, rate, overshoot):
    #     '''
    #     Fast mode of sweeping the current. Attempts to avoid a delay due to the 4G by initially
    #     setting the sweep to overshoot the setpoint, then when the sweep approaches the setpoint,
    #     setting it back to the intended setpoint.
    # 
    #     Using this function there is a risk of overshooting the setpoint by the overshoot amount.
    # 
    #     Sweep to a given current (in A) at a given rate (in A/s)
    #     '''
    #     if self.dual_channel:
    #         if chan == 1 or chan == 2:
    #             channel = "CHAN "+str(chan)+";"
    #         else:
    #             returnValue("INVALID CHANNEL (need 1 or 2)")
    #     else:
    #         channel = ""
    # 
    #     rate_set = "RATE 0 " + str(rate) + ";"
    # 
    #     # Get the current field to determine if you need to go up or down
    #     t0 = time.time()
    #     magnet_current = yield self.get_output_current(chan)
    #     t1 = time.time()
    #     print(t1-t0)
    # 
    # 
    #     if magnet_current > current: # Need to sweep down to the setpoint
    #         # Prevent an error thrown if LLIM is greater than ULIM
    #         ulim = yield self.query(channel+"ULIM?")
    #         ulim = float(ulim.replace("A",""))
    #         if ulim < current:
    #             if current < 0:
    #                 yield self.write(channel+"ULIM 0.0")
    #             else:
    #                 yield self.write(channel+"ULIM " + str(current+0.001))
    # 
    #         yield self.write(channel+"LLIM " + str(current))
    #         yield self.write(channel+rate_set+"SWEEP DOWN")
    # 
    #     else: # Need to sweep up to the setpoint
    #         # Prevent an error thrown if ULIM is lower than LLIM
    #         llim = yield self.query(channel+"LLIM?")
    #         llim = float(llim.replace("A",""))
    #         if llim > current:
    #             if current > 0:
    #                 yield self.write(channel+"LLIM 0.0")
    #             else:
    #                 yield self.write(channel+"LLIM " + str(current-0.001))
    # 
    #         yield self.write(channel+"ULIM " + str(current))
    #         yield self.write(channel+rate_set+"SWEEP UP")
    #     returnValue("SWEEPING")

    @inlineCallbacks
    def zero_output(self, chan):
        '''
        Brings the magnet output to zero. Equivalent to presseing the "Zero" button on the front panel.
        This may not zero out the persistent current if the magnet is in persistent mode.
        '''
        if self.dual_channel:
            if chan == 1 or chan == 2:
                channel = "CHAN "+str(chan)+";"
            else:
                returnValue("INVALID CHANNEL (need 1 or 2)")
        else:
            channel = ""
        yield self.write(channel+"SWEEP ZERO")
        returnValue("ZEROING MAGNET")


class Cryomagnetics_4G_Server(GPIBManagedServer):
    name = 'cryo_4G_power_supply'
    deviceName = 'Cryomagnetics 4G'
    deviceIdentFunc = 'identify_device'
    deviceWrapper = Cryo4GWrapper

    @setting(100, channel='i', returns='?')
    def get_units(self,c, channel):
        '''
        Get the units of the given output channel.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_units(channel)
        returnValue(ans)

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
        Get the currently selected output channel. Dual Output mode will return 1 or 2,
        otherwise returns 1 always.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_chan()
        returnValue(ans)

    @setting(103, channel='i', returns='?')
    def set_channel(self,c, channel):
        '''
        Get the currently selected output channel. Dual Output mode only.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.set_chan(channel)
        returnValue(ans)

    @setting(104, channel='i', returns='?')
    def get_field(self, c, channel):
        '''
        Get the field of the magnet.

        If the persistent switch heater is ON the magnet current (or field) returned will
        be the same as the power supply output current. If the persistent switch
        heater is off, the magnet current will be the value of the power supply
        output current when the persistent switch heater was last turned off. The
        magnet current will be set to zero if the power supply detects a quench.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_field(channel)
        returnValue(ans)

    @setting(105, channel='i', returns='?')
    def get_current(self, c, channel):
        '''
        Get the current of the magnet.

        If the persistent switch heater is ON the magnet current (or field) returned will
        be the same as the power supply output current. If the persistent switch
        heater is off, the magnet current will be the value of the power supply
        output current when the persistent switch heater was last turned off. The
        magnet current will be set to zero if the power supply detects a quench.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_current(channel)
        returnValue(ans)

    @setting(106, channel='i', returns='?')
    def get_output_current(self, c, channel):
        '''
        Get the output of the power supply.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_output_current(channel)
        returnValue(ans)

    @setting(107, channel='i', returns='b')
    def get_persist(self, c, channel):
        '''
        Get the persistent mode. Returns True if the switch heater is off and the magnet is
        in persistent mode, returns False if the switch heater is on and the magnet is not
        in persistent mode.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_persist(channel)
        returnValue(ans)

    @setting(108, channel='i', persist='b', returns='?')
    def set_persist(self, c, channel, persist):
        '''
        Set the persistent mode. If persist is True will turn the heater off and go into persistent
        mode. If persist is False will turn the heater on.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.set_persist(channel, persist)
        returnValue(ans)

    @setting(109, channel='i', current='v', rate='v', returns='s')
    def sweep_magnet(self, c, channel, current, rate):
        '''
        Sweep the magnet current to the given current setpoint.

        Note about Maximum Rates:
            The 4G supply specifies multiple rates for different ranges of current to protect the magnet.
            The manufacturer of the magnet will give multiple rated ramp rates (e.g. 0-50A @0.2 A/s and
            50-60 A @ 0.1 A/s etc.). We want to be able to smoothly ramp the field for experiments so we
            set first range (range 0 on the controller) to the max field and then use the lowest rating
            specified by the manufacturer. This trades a small amount of time at low fields for a smooth
            ramp rate and safety. Most of the time we will not be operating near the maximum ramp rate.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.sweep_current(channel, current, rate)
        returnValue(ans)

    @setting(110, channel='i', returns='?')
    def zero_output(self, c, channel):
        '''
        Brings the magnet output to zero. Equivalent to pressing the "Zero" button on the front panel.
        This may not zero out the persistent current if the magnet is in persistent mode.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.zero_output(channel)
        returnValue(ans)

    @setting(111, returns='?')
    def get_output_voltage(self,c, channel):
        '''
        Get the output voltage of the currently selected channel.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.get_output_voltage(channel)
        returnValue(ans)
    
    # @setting(112, channel='i', current='v', rate='v', overshoot='v', returns='s')
    # def fast_sweep_magnet(self, c, channel, current, rate, overshoot):
    #     '''
    #     Sweep the magnet current to the given current setpoint in fast mode to avoid the PID 
    #     stabalization time.
    # 
    #     Note about Maximum Rates:
    #         The 4G supply specifies multiple rates for different ranges of current to protect the magnet.
    #         The manufacturer of the magnet will give multiple rated ramp rates (e.g. 0-50A @0.2 A/s and
    #         50-60 A @ 0.1 A/s etc.). We want to be able to smoothly ramp the field for experiments so we
    #         set first range (range 0 on the controller) to the max field and then use the lowest rating
    #         specified by the manufacturer. This trades a small amount of time at low fields for a smooth
    #         ramp rate and safety. Most of the time we will not be operating near the maximum ramp rate.
    #     '''
    #     dev=self.selectedDevice(c)
    #     ans = yield dev.fast_sweep_current(channel, current, rate, overshoot)
    #     returnValue(ans)

    @setting(998, returns='?')
    def manual_write(self,c, command):
        '''
        Get the output voltage of the currently selected channel.
        '''
        dev=self.selectedDevice(c)
        ans = yield dev.write(command)
        returnValue(command)

    @setting(999, returns='?')
    def manual_query(self,c, command):
        '''
        Get the output voltage of the currently selected channel.
        '''
        dev=self.selectedDevice(c)
        t0 = time.time()
        ans = yield dev.query(command)
        t1 = time.time()
        print(t1-t0)
        returnValue(ans)


__server__ = Cryomagnetics_4G_Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
