'''
A set of objects for the various magnet controllers
'''
from twisted.internet.defer import inlineCallbacks
from Equipment.Equipment import EquipmentController
from nSOTScannerFormat import printErrorInfo
import numpy as np

class MagnetControl(EquipmentController):
    def __init__(self, widget, device_info, config):
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
        super().__init__(widget, device_info, config)

        self.max_field = self.config['max_field']

        # Status parameters
        self.Bz = 0.0 # The field from the magnet power supply output
        self.persist_Bz = 0.0 # The persistent field of the magnet
        self.setpoint_Bz = 0.0 # The field setpoint
        self.current = 0.0 # The current on the magnet power supply output
        self.persist_current = 0.0 # The persistent current of the magnet
        self.output_voltage = 0.0 # the output voltage when charging
        self.ramprate = 0 # T/min

        self.status = ''
        self.persist = False # If the supply is in persistent field mode
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
                self.server.select_device()
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

    @inlineCallbacks
    def readInitialValues(self):
        '''
        Read the starting configuration of a magnet power supply. Override for a specific supply.
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

    def setSetpoint(self, setpoint):
        '''
        Change the setpoint of the controller. Does not update to the actual power supply
        until goToSetpoint is called.
        '''
        if setpoint > self.max_field:
            self.setpoint_Bz = self.max_field
        elif setpoint < -1.0*self.max_field:
            self.setpoint_Bz = -1.0*self.max_field
        else:
            self.setpoint_Bz = setpoint
    #

    def setRampRate(self, ramprate):
        '''
        Change the setpoint of the power supply. Does not change the value in the magnet
        supply until goToSetpoint is called.
        '''
        self.ramprate = ramprate
    #

    @inlineCallbacks
    def goToSetpoint(self):
        '''
        Ramps to the setpoint. setSetpoint and setRampRate should be called first
        to configure this ramp.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #

    @inlineCallbacks
    def goToZero(self):
        '''
        Zero the current through the magnet.

        OVERRIDE for a specific magnet controller.
        '''
        pass
    #
#

class IPS120_MagnetController(MagnetControl):
    @inlineCallbacks
    def poll(self):
        '''
        Read out the current status. If it is persistent will read out the magnet
        field, current and voltage if not the output voltage
        '''

        status = yield self.server.examine()
        #The 9th (index 8) character of the status string encodes whether or not
        #the persistent switch is currently on
        if int(status[8]) == 0 or int(status[8]) == 2:
            self.status = "Persist"
            self.persist = True
        elif int(status[8]) == 1:
            self.status = "Charging"
        else:
            self.status = "Error"

        try:
            if self.persist: # Persistent field and current
                val = yield self.server.read_parameter(18)
                self.persist_Bz = float(val[1:])

                val = yield self.server.read_parameter(16)
                self.persist_current = float(val[1:])
            else:
                self.persist_Bz = 0
                self.persist_current = 0

            # The "Demand Field" during charging
            val = yield self.server.read_parameter(7)
            self.Bz = float(val[1:])

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
        setpoint = yield self.server.read_parameter(8)
        ramprate = yield self.server.read_parameter(9)
        self.setpoint_Bz = float(setpoint[1:])
        self.ramprate = float(ramprate[1:])
    #

    @inlineCallbacks
    def goToZero(self):
        '''
        Zero the current through the magnet.
        '''
        yield self.server.set_control(3) #Set IPS to remote communication (prevents user from using the front panel)
        yield self.server.set_activity(2)
        yield self.server.set_control(2) #Set IPS to local control (allows user to edit IPS from the front panel)
    #

    @inlineCallbacks
    def goToSetpoint(self):
        '''
        Ramps to the setpoint. setSetpoint and setRampRate should be called first
        to configure this ramp.
        '''
        yield self.server.set_control(3) #Set IPS to remote communication (prevents user from using the front panel)
        yield self.server.set_fieldsweep_rate(self.ramprate)
        yield self.server.set_targetfield(self.setpoint_Bz) #Set targetfield to desired field
        yield self.server.set_activity(1) #Set IPS mode to ramping instead of hold
        yield self.server.set_control(2) #Set IPS to local control (allows user to edit IPS from the front panel)
    #

    @inlineCallbacks
    def togglePersist(self):
        try:
            if self.persist:
                yield self.server.set_control(3)
                yield self.server.set_switchheater(1)
                yield self.server.set_control(2)
                self.persist = False
            else:
                yield self.server.set_control(3)
                yield self.server.set_switchheater(0)
                yield self.server.set_control(2)
                self.persist = True
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

class Toeller_Power_Supply(MagnetControl):
    def __init__(self, widget, device_info, config):
        super().__init__(widget, device_info, config)
        self.toeCurChan = config['toeCurChan']
        self.toeVoltsChan = config['toeVoltsChan']
        self.status = "Charging"
        self.persist = False

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

            self.Bz = self.current*self.IB_conv
        except Exception as inst:
            print(inst)
            printErrorInfo()
    #

    @inlineCallbacks
    def goToSetpoint(self):
        yield self.toeSweepField(self.Bz, self.setpoint_Bz, self.ramprate)
    #

    @inlineCallbacks
    def goToZero(self):
        yield self.toeSweepField(self.Bz, 0.0, self.ramprate)
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
            self.Bz = B_f
        except:
            printErrorInfo()
#

def Cryomag4G_Power_Supply(MagnetControl):
    pass
#
