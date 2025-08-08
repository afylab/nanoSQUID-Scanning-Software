'''
A set of objects for the various magnet controllers
'''
from twisted.internet.defer import inlineCallbacks, Deferred
from Equipment.Equipment import EquipmentController
from nSOTScannerFormat import printErrorInfo
import numpy as np

class MagnetControl(EquipmentController):
    def __init__(self, widget, device_info, config, reactor):
        '''
        A generic base class for a magnet controller, features a variety of functions that
        are meant to be overwritten for a specific controller. The arugments will generally
        be defined in an inheriting subclass.

        Args:
            widget : The widget to display the status of the server.
            device_info (dict) : information to connect to the proper hardware.
            config (dict) : A dictionary of configurations settings, passed from equipment handler
            dimensions (int) : The number of dimensions of controllable field. 1 is assumed a simple
                Z-axis magnet, 2 is a X-Z vector magnet and 3 is an X-Y-Z vector magnet.
        '''
        super().__init__(widget, device_info, config, reactor)

        self.max_field = self.config['max_field']
        self.max_ramp = self.config["max_ramp"]

        # Status parameters
        self.B = 0.0 # The field from the magnet power supply output
        self.persist_B = 0.0 # The persistent field of the magnet
        self.setpoint_B = 0.0 # The field setpoint
        self.current = 0.0 # The current on the magnet power supply output
        self.persist_current = 0.0 # The persistent current of the magnet
        self.output_voltage = 0.0 # the output voltage when charging
        self.ramprate = 0 # T/min
        self.sweeping = False
        self.abort_wait = False

        self.status = ''
        self.persist = False # If the supply is in persistent field mode
        self.autopersist = True # Automatically go into persistent mode when done ramping/scanning.
    #

    def connect(self, server):
        '''
        Connect to the device for the given server by calling select_device
        with the given selection info (if present). Override for more complex
        startup procedures.
        '''
        self.server = server
        try:
            if hasattr(self.server, 'select_device'):
                if self.device_info is None:
                    server.select_device()
                else:
                    server.select_device(self.device_info)
            self.widget.connected(self.device_info)
        except Exception as inst:
            print("Error connecting labrad servers")
            print(str(inst))
            printErrorInfo()
            self.widget.error()

        try:
            self.readInitialValues() # Load in any information that needs to be there
        except Exception as inst:
            print("Error reading magnet initial parameters")
            print(str(inst))
            printErrorInfo()
            self.widget.error()
    #

    def setSetpoint(self, setpoint):
        '''
        Change the setpoint of the controller. Does not update to the actual power supply
        until goToSetpoint is called.
        '''
        if setpoint > self.max_field:
            self.setpoint_B = self.max_field
        elif setpoint < -1.0*self.max_field:
            self.setpoint_B = -1.0*self.max_field
        else:
            self.setpoint_B = setpoint
    #

    def checkFieldRange(self, field):
        '''
        Checks that the given field is withinin the max/min field for the magnet.
        If the field is outside the range will return the maximum or minimum, if
        the field is within the range will resturn the field.

        For compatability with older parts of software
        '''
        if field > self.max_field:
            field = self.max_field
        elif field < -1.0*self.max_field:
            field = -1.0*self.max_field
        return field

    def setRampRate(self, ramprate):
        '''
        Change the field ramp rate (in T/min) of the power supply. Does not change the value in the magnet
        supply until goToSetpoint is called. If the ramprate is greater than the maximum possible ramprate
        then the rate will be set to the maximum.
        '''
        if ramprate > self.max_ramp:
            self.ramprate = self.max_ramp
        else:
            self.ramprate = ramprate
    #

    @inlineCallbacks
    def autoPersistMagnet(self):
        '''
        Called at the end of ramping the magnet, if self.autopersist is true will persist the field then ramp
        down the supply.

        Made to work the same for any magnet supply.
        '''
        if not self.autopersist:
            print("Warning. Autopersist not enabled.")
            return
        yield self.poll()
        if self.persist:
            if self.B != self.persist_B:
                print("Autopersist: ramping supply to last setpoint")
                self.setSetpoint(self.persist_B)
                self.setRampRate(self.max_ramp)
                yield self.goToSetpoint()
                yield self.sleep_still_poll(30)
            print("Autopersist:, toggling persistent switch")
            yield self.togglePersist() # Turn switch on, enter charging mode
            print("Autopersist: Done, ready to sweep magnet")
        else:
            if self.sweeping: # Were sweeping, don't do anything
                print("Warning, system is sweeping, autopersist failed.")
                return
            print("Autopersist: persisting magnet")
            yield self.sleep_still_poll(30)
            yield self.togglePersist() # Turn switch off, enter persistent mode
            yield self.sleep_still_poll(5)
            if self.B != 0:
                print("Autopersist: ramping down magnet supply")
                self.setRampRate(self.max_ramp)
                yield self.goToZero()
    #

    @inlineCallbacks
    def resetPersistMagnet(self):
        '''
        If the magnet is persistent, reset it's field by ramping to the setpoint, toggling the field,
        then ramping down.

        Made to work the same for any magnet supply.
        '''
        yield self.poll()
        yield self.sleep(2)
        if self.persist and self.autopersist:
            print("Resetting persistent magnet.")
            yield self.startSweeping() # Will ramp up the supply then un-persist the magnet
            yield self.sleep_still_poll(30)
            yield self.doneSweeping() # Will autopersist the magnet
        else:
            print("Cannot reset field unless it is persistent and autopersist is on.")
    #
    @inlineCallbacks
    def startSweeping(self):
        '''
        Prepares the controller for something to perform a sweep for any reason.
        This only affects behavior if in autopersist mode. Otherwise you need to
        take care of it manually.
        '''
        if self.autopersist: # Does nothing if not in autopersist mode
            self.sweeping = True
            print("Preparing for a magnetic field sweep.")
            yield self.autoPersistMagnet()
    #
    @inlineCallbacks
    def doneSweeping(self):
        '''
        Tells the controller that whatever was sweeping is done. Will call autoPersistMagent if in
        autopersist mode.
        '''
        if self.autopersist: # Does nothing if not in autopersist mode
            self.sweeping = False
            print("Done sweeping the magnetic field.")
            yield self.autoPersistMagnet()
        else: # In case autopersist is turned off during a sweep
            self.sweeping = False
            yield self.queryPersist()
    #

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = Deferred()
        self.reactor.callLater(secs,d.callback,'Sleeping')
        return d
    #

    @inlineCallbacks
    def sleep_still_poll(self, secs):
        '''
        Sleep the magnet but still poll so that the interface updates.
        LESS PRECISE because polling takes a little time and will round to an
        integer number of seconds if secs>1
        '''
        s = int(secs)
        if s == 0:
            yield self.sleep(secs)
            yield self.poll()
        else:
            for i in range(s):
                yield self.sleep(1)
                yield self.poll()
    #

    '''
    --------------------------------------
    BELOW FUNCTIONS SPECIFIC TO A GIVEN MAGNET POWER SUPPLY, OVERRIDE TO ADD FUNCTIONALITY
    --------------------------------------
    '''

    @inlineCallbacks
    def readInitialValues(self):
        '''
        Read the starting configuration of a magnet power supply.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #

    @inlineCallbacks
    def poll(self):
        '''
        Read out the current values from the equipment: field, current and voltage. Will update the output
        values if self.persist is False and the magnet values if self.persist is True.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #

    @inlineCallbacks
    def goToSetpoint(self, wait=True):
        '''
        Ramps to the setpoint. setSetpoint and setRampRate should be called first
        to configure this ramp.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #

    @inlineCallbacks
    def goToZero(self, wait=True):
        '''
        Zero the current through the magnet.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #

    @inlineCallbacks
    def queryPersist(self):
        '''
        Read from the supply is the persistent switch heater is on.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #

    @inlineCallbacks
    def togglePersist(self):
        '''
        Switches into or out of persistent mode.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #

class IPS120_MagnetController(MagnetControl):
    @inlineCallbacks
    def poll(self):
        '''
        Read out the current status. If it is persistent will read out the magnet
        field, current and voltage if not the output voltage
        '''

        yield self.queryPersist()

        try:
            if self.persist: # Persistent field and current
                val = yield self.server.read_parameter(18)
                self.persist_B = float(val[1:])

                val = yield self.server.read_parameter(16)
                self.persist_current = float(val[1:])
            else:
                self.persist_B = 0
                self.persist_current = 0

            # The "Demand Field" during charging
            val = yield self.server.read_parameter(7)
            self.B = float(val[1:])

            # The demand "Output" current
            val = yield self.server.read_parameter(0)
            self.current = float(val[1:])

            # The charging voltage
            val = yield self.server.read_parameter(1)
            self.output_voltage = float(val[1:])
        except Exception as inst:
            print(inst)
            printErrorInfo()
    #

    @inlineCallbacks
    def readInitialValues(self):
        '''
        Read the starting configuration of a magnet power supply. Override for a specific supply.
        '''
        yield self.server.set_comm_protocol(4) # Turn it into high-resolution mode
        setpoint = yield self.server.read_parameter(8)
        ramprate = yield self.server.read_parameter(9)
        self.setpoint_B = float(setpoint[1:])
        self.ramprate = float(ramprate[1:])

        yield self.queryPersist()
    #

    @inlineCallbacks
    def queryPersist(self):
        '''
        Read from the supply is the persistent switch heater is on.
        '''
        status = yield self.server.examine()
        #The 9th (index 8) character of the status string encodes whether or not
        #the persistent switch is currently on
        if int(status[8]) == 0 or int(status[8]) == 2:
            self.status = "Persist"
            self.persist = True
        elif int(status[8]) == 1:
            self.status = "Charging"
            self.persist = False
        else:
            self.status = "Error"
            self.persist = False
    #

    @inlineCallbacks
    def goToZero(self, wait=True):
        '''
        Zero the output of the magnet supply.

        Args:
            wait (bool) : Will wait for the controller to reach the setpoint.
        '''
        yield self.server.set_control(3) #Set IPS to remote communication (prevents user from using the front panel)
        yield self.server.set_activity(2)
        yield self.server.set_control(2) #Set IPS to local control (allows user to edit IPS from the front panel)

        if wait:
            #Only finish running the gotoZero function once the field is zero
            while True:
                yield self.poll()
                if self.B <= 0.00001 and self.B >= -0.00001:
                    break
                elif self.abort_wait:
                    self.abort_wait = False
                    break
                yield self.sleep(0.25)
            yield self.sleep(0.25)
    #

    @inlineCallbacks
    def goToSetpoint(self, wait=True):
        '''
        Ramps the supply to the setpoint. setSetpoint and setRampRate should be called first
        to configure this ramp.

        Args:
            wait (bool) : Will wait for the controller to reach the setpoint
        '''
        yield self.server.set_control(3) #Set IPS to remote communication (prevents user from using the front panel)
        yield self.server.set_fieldsweep_rate(self.ramprate)
        yield self.server.set_targetfield(self.setpoint_B) #Set targetfield to desired field
        yield self.server.set_activity(1) #Set IPS mode to ramping instead of hold
        yield self.server.set_control(2) #Set IPS to local control (allows user to edit IPS from the front panel)

        if wait:
            #Only finish running the gotoField function when the field is reached
            while True:
                yield self.poll()
                if self.B <= self.setpoint_B+0.00001 and self.B >= self.setpoint_B-0.00001:
                    break
                elif self.abort_wait:
                    self.abort_wait = False
                    break
                yield self.sleep(0.25)
            yield self.sleep(0.25)
    #

    @inlineCallbacks
    def togglePersist(self):
        try:
            yield self.queryPersist()
            if self.persist:
                yield self.server.set_control(3)
                yield self.server.set_switchheater(1)
                yield self.server.set_control(2)
                self.persist = False
                yield self.sleep_still_poll(15)
            else:
                yield self.server.set_control(3)
                yield self.server.set_switchheater(0)
                yield self.server.set_control(2)
                self.persist = True
                yield self.sleep_still_poll(15)
        except:
            printErrorInfo()

    @inlineCallbacks
    def hold(self):
        '''
        Set the ISP to hold mode
        '''
        yield self.server.set_control(3)
        yield self.server.set_activity(0)
        yield self.server.set_control(2)
    #

    @inlineCallbacks
    def clamp(self):
        '''
        Set the ISP to clamp mode
        '''
        yield self.server.set_control(3)
        yield self.server.set_activity(4)
        yield self.server.set_control(2)
    #
#

'''
An alternate version of the IPS controller that works on setting the current setpoint.
'''
class IPS120_MagnetController_ALT(IPS120_MagnetController):
    def __init__(self, widget, device_info, config, reactor):
        self.gauss_to_amps = config['gauss_to_amps']
        super().__init__(widget, device_info, config, reactor)
    #
    
    @inlineCallbacks
    def poll(self):
        '''
        Read out the current status. If it is persistent will read out the magnet
        field, current and voltage if not the output voltage
        '''

        yield self.queryPersist()

        try:
            if self.persist: # Persistent field and current
                # val = yield self.server.read_parameter(18)
                # self.persist_B = float(val[1:])

                val = yield self.server.read_parameter(16)
                self.persist_current = float(val[1:])
                # Back convert the current to get field
                self.persist_B = self.persist_current*self.gauss_to_amps*1e-4
            else:
                self.persist_B = 0
                self.persist_current = 0

            # The "Demand Field" during charging
            # val = yield self.server.read_parameter(7)
            # self.B = float(val[1:])

            # The demand "Output" current
            val = yield self.server.read_parameter(0)
            self.current = float(val[1:])
            # Back convert the current to get field
            self.B = self.current*self.gauss_to_amps*1e-4

            # The charging voltage
            val = yield self.server.read_parameter(1)
            self.output_voltage = float(val[1:])
        except Exception as inst:
            print(inst)
            printErrorInfo()
    #
    
    @inlineCallbacks
    def readInitialValues(self):
        '''
        Read the starting configuration of a magnet power supply. Override for a specific supply.
        '''
        yield self.server.set_comm_protocol(4) # Turn it into high-resolution mode
        setpoint = yield self.server.read_parameter(8)
        ramprate = yield self.server.read_parameter(9)
        self.setpoint_B = float(setpoint[1:])
        self.ramprate = float(ramprate[1:])

        yield self.queryPersist()
    #
    @inlineCallbacks
    def goToSetpoint(self, wait=True):
        '''
        Ramps the supply to the setpoint. setSetpoint and setRampRate should be called first
        to configure this ramp.

        Args:
            wait (bool) : Will wait for the controller to reach the setpoint
        '''
        yield self.server.set_control(3) #Set IPS to remote communication (prevents user from using the front panel)
        
        # Use the target current instead of the target field
        #yield self.server.set_fieldsweep_rate(self.ramprate)
        #yield self.server.set_targetfield(self.setpoint_B) #Set targetfield to desired field
        current = self.setpoint_B*1e4/self.gauss_to_amps
        ramprate = self.ramprate*1e4/self.gauss_to_amps
        yield self.server.set_currentsweep_rate(ramprate)
        yield self.server.set_targetcurrent(current)
        yield self.server.set_activity(1) #Set IPS mode to ramping instead of hold
        yield self.server.set_control(2) #Set IPS to local control (allows user to edit IPS from the front panel)

        if wait:
            #Only finish running the gotoField function when the field is reached
            while True:
                yield self.poll()
                if self.B <= self.setpoint_B+0.00001 and self.B >= self.setpoint_B-0.00001:
                    break
                elif self.abort_wait:
                    self.abort_wait = False
                    break
                yield self.sleep(0.25)
            yield self.sleep(0.25)
    #
#

class Toeller_Power_Supply(MagnetControl):
    def __init__(self, widget, device_info, config, reactor):
        super().__init__(widget, device_info, config, reactor)
        self.toeCurChan = config['toeCurChan']
        self.toeVoltsChan = config['toeVoltsChan']
        self.status = "Charging"
        self.persist = False
        self.autopersist = False

        #Toellner voltage set point / DAC voltage out conversion [V_Toellner / V_DAC]
        self.VV_conv = 3.20
        #Toellner current set point / DAC voltage out conversion [I_Toellner / V_DAC]
        self.IV_conv = 1.0

        #Field / Current ratio on the dipper magnet (0.132 [Tesla / Amp])
        self.IB_conv = 0.132

    @inlineCallbacks
    def poll(self):
        '''
        Read out the current values. Toeller does not have a persistent mode
        so it is always considered "charging"
        '''
        try:
            val = yield self.server.read_dac_voltage(self.toeCurChan)
            self.current = float(val*self.IV_conv)

            val = yield self.server.read_dac_voltage(self.toeVoltsChan)
            self.output_voltage = float(val*self.VV_conv)

            self.B = self.current*self.IB_conv
        except Exception as inst:
            print(inst)
            printErrorInfo()
    #

    @inlineCallbacks
    def goToSetpoint(self):
        yield self.toeSweepField(self.B, self.setpoint_B, self.ramprate)
    #

    @inlineCallbacks
    def goToZero(self):
        yield self.toeSweepField(self.B, 0.0, self.ramprate)
    #
    
    @inlineCallbacks
    def readInitialValues(self):
        '''
        Just a DAC-ADC
        '''
        yield self.poll()
    #
    
    @inlineCallbacks
    def queryPersist(self):
        '''
        Read from the supply is the persistent switch heater is on.

        OVERRIDE for a specific magnet controller.
        '''
        yield self.sleep(0)
        return False
    #

    @inlineCallbacks
    def togglePersist(self):
        '''
        Switches into or out of persistent mode.

        OVERRIDE for a specific magnet controller.
        '''
        yield self.sleep(0)
    #


    @inlineCallbacks
    def toeSweepField(self, B_i, B_f, B_speed):
        try:
            #Starting and ending field values in Tesla, use positive field values for now
            B_range = np.absolute(B_f - B_i)

            #Delay between DAC steps in microseconds
            magnet_delay = 1000
            #Converts between microseconds and minutes [us / minute]
            t_conv = 6e07

            #Sets the appropriate DAC buffer ramp parameters
            sweep_steps = int((t_conv * B_range) / (B_speed * magnet_delay))  + 1
            v_start = B_i / (self.IB_conv * self.IV_conv)
            v_end = B_f / (self.IB_conv * self.IV_conv)

            #Sets an appropraite voltage set point to ensure that the Toellner power supply stays in constant current mode
            # assuming a parasitic resistance of R_p between the power supply and magnet
            R_p = 1
            V_setpoint =  (R_p * B_f) / (self.VV_conv * self.IB_conv)
            V_initial = (R_p * B_i) / (self.VV_conv * self.IB_conv)
            if V_setpoint*self.VV_conv > 5.0:
                V_setpoint = 5.0/self.VV_conv
            else:
                pass
            if V_initial*self.VV_conv > 5.0:
                V_initial = 5.0/self.VV_conv
            else:
                pass

            #Sweeps field from B_i to B_f
            print('Sweeping field from ' + str(B_i) + ' to ' + str(B_f)+'.')
            yield self.server.buffer_ramp([self.toeCurChan, self.toeVoltsChan],[0],[v_start, V_initial],[v_end, V_setpoint], sweep_steps, magnet_delay)

            self.output_voltage = V_setpoint
            self.current = B_f/self.IB_conv
            self.B = B_f
        except:
            printErrorInfo()
#

class Cryomag4G_Power_Supply(MagnetControl):
    def __init__(self, widget, device_info, config, reactor):
        self.channel = config['channel']
        self.gauss_to_amps = config['gauss_to_amps']

        super().__init__(widget, device_info, config, reactor)

    @inlineCallbacks
    def readInitialValues(self):
        '''
        Read the starting configuration of a magnet power supply.
        '''
        yield self.poll()
    #

    @inlineCallbacks
    def poll(self, outputonly=False):
        '''
        Read out the current values from the equipment: field, current and voltage. Will update the output
        values if self.persist is False and the magnet values if self.persist is True.
        '''
        if self.server is None or isinstance(self.server, bool):
            return

        try:
            # Only poll the output, for performance tests or fast sweeping mode
            if outputonly:
                val = yield self.server.get_output_current(self.channel)
                self.current = float(val)
                self.B = self.current*self.gauss_to_amps*1e-4
                return

            yield self.queryPersist()

            if self.persist:
                if self.server is not None: # Sometimes these functions are slow to update and close out on disconnect
                    curr = yield self.server.get_current(self.channel)
                    self.persist_current = float(curr)
                    self.persist_B = self.persist_current*self.gauss_to_amps*1e-4
            else:
                self.persist_B = 0
                self.persist_current = 0

            # The Ouput current and voltage
            if self.server is not None:
                val = yield self.server.get_output_current(self.channel)
                self.current = float(val)
                self.B = self.current*self.gauss_to_amps*1e-4
            if self.server is not None:
                val = yield self.server.get_output_voltage(self.channel)
                self.output_voltage = float(val)
        except Exception as inst:
            print(str(inst))
            printErrorInfo()
            self.status = "Error"
    #

    @inlineCallbacks
    def goToSetpoint(self, wait=True, wait_tolerance=0.00002):
        '''
        Ramps to the setpoint. setSetpoint and setRampRate should be called first
        to configure this ramp.

        Args:
            wait (bool) : Will wait for the controller to reach the setpoint.
            wait_tolerance (float) : If waiting, the tolerance of the field around the setpoint.
        '''

        # The Cryomag 4G has weired unit issues for field, so we set the current
        # Convert the setpoint (in T) and ramp rate (in T/min) to A and A/s
        current = self.setpoint_B*1e4/self.gauss_to_amps
        ramprate = self.ramprate*166.666667/self.gauss_to_amps
        yield self.server.sweep_magnet(self.channel, current, ramprate)
        if wait:
            #Only finish running the goToSetpoint function when the field is reached
            while True:
                yield self.poll()
                if self.B <= self.setpoint_B+wait_tolerance and self.B >= self.setpoint_B-wait_tolerance:
                    break
                elif self.abort_wait:
                    self.abort_wait = False
                    break
                yield self.sleep(0.25)
            yield self.sleep(0.1)
    #

    # @inlineCallbacks
    # def fastToSetpoint(self, overshoot=0.015, ramprate=0.2, cutback=0.030, wait=False, wait_tolerance=0.0002):
    #     '''
    #     Ramps to the setpoint in a manner to make the ramping faster by avoiding the
    #     PID stabalization. First it sets the server to sweep to a value that slightly overshoots the setpoint,
    #     then when approaching the setpoint switching to the original setpoint.
    #
    #     OVERRIDES the default ramprate, since the overshoot algorithm is very sensitive to ramprate.
    #
    #     setSetpoint and setRampRate should be called first to configure this ramp.
    #
    #     Args:
    #         overshoot (float) : The theoretical overshoot used to fool the 4G PID loop. Using this mode
    #             there is a risk of overshooting the setpoint by this amount.
    #         ramprate (float): The sweep rate of the magnetic field, overrides the normal ramprate set
    #             by the user.
    #         cutback (float) : How close (in units of A) the power supply gets to the setpoint before
    #             turning off the overshooting. If this is too small it will result in overshooting due
    #             to latency, and if it is too large it will result in undershooting.
    #         wait (bool) : Will wait for the controller to reach the setpoint.
    #         wait_tolerance (float) : If waiting, the tolerance of the field around the setpoint.
    #     '''
    #
    #     # to prevent potential overshooting don't use near the maximum field, just
    #     # do a normal goToSetpoint
    #     if np.abs(self.setpoint_B) + overshoot >= self.max_field:
    #         yield self.goToSetpoint(wait=wait)
    #
    #     try:
    #         # The Cryomag 4G has weired unit issues for field, so we set the current
    #         # Convert the setpoint (in T) and ramp rate (in T/min) to A and A/s
    #         current = self.setpoint_B*1e4/self.gauss_to_amps
    #
    #         if self.setpoint_B > self.B:
    #             Iover = (self.setpoint_B+overshoot)*1e4/self.gauss_to_amps
    #         else:
    #             Iover = (self.setpoint_B-overshoot)*1e4/self.gauss_to_amps
    #
    #         ramprate = ramprate*166.666667/self.gauss_to_amps # Convert ramprate to correct units
    #
    #         if wait: # Only finish running the goToSetpoint function when the field is reached
    #             yield self.server.fast_sweep_magnet(self.channel, current, ramprate, Iover, cutback)
    #             while True:
    #                 yield self.poll(outputonly=True)
    #                 if self.B <= self.setpoint_B+wait_tolerance and self.B >= self.setpoint_B-wait_tolerance:
    #                     break
    #                 elif self.abort_wait:
    #                     self.abort_wait = False
    #                     break
    #                 yield self.sleep(0.25)
    #             yield self.sleep(0.1)
    #         else: # don't wait for it to finish, just send the command.
    #             self.server.fast_sweep_magnet(self.channel, current, ramprate, Iover, cutback)
    #     except:
    #         from traceback import format_exc
    #         print("Error encounter in fastToSetpoint")
    #         print(format_exc())
    # #

    @inlineCallbacks
    def togglePersist(self):
        try:
            self.persist = yield self.server.get_persist(self.channel)
            if self.persist:
                yield self.server.set_persist(self.channel, False)
                yield self.sleep_still_poll(25)
                self.persist = yield self.server.get_persist(self.channel)
                if self.persist:
                    print("Warning: persistent switch didn't toggle. Probably output doesn't match persistent field.")
            else:
                yield self.server.set_persist(self.channel, True)
                yield self.sleep_still_poll(25)
                self.persist =  yield self.server.get_persist(self.channel)
                if not self.persist:
                    print("Warning: persistent switch didn't toggle. Probably output doesn't match persistent field.")
        except:
            printErrorInfo()

    @inlineCallbacks
    def queryPersist(self):
        '''
        Read from the supply is the persistent switch heater is on.
        '''
        self.persist = yield self.server.get_persist(self.channel)
        if self.persist:
            self.status = "Persist"
        else:
            self.status = "Charging"
    #

    @inlineCallbacks
    def goToZero(self, wait=True):
        '''
        Zero the current through the magnet.

        Args:
            wait (bool) : Will wait for the controller to reach zero.
        '''
        yield self.server.zero_output(self.channel)
        if wait:
            #Only finish running the gotoZero function once the field is zero
            while True:
                yield self.poll()
                if self.B <= 0.00001 and self.B >= -0.00001:
                    break
                elif self.abort_wait:
                    self.abort_wait = False
                    break
                yield self.sleep(0.25)
            yield self.sleep(1)
    #
#
