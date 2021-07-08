'''
A set of objects for the various magnet controllers
'''
from twisted import inlineCallbacks
from Equipment import EquipmentController

class MagnetControl(EquipmentController):
    def __init__(self, labrad_server, config, dimensions):
        '''
        A generic base class for a magnet controller, features a variety of functions that
        are meant to be overwritten for a specific controller. The arugments will generally
        be defined in an inheriting subclass.

        Args:
            labrad_server : The labrad server to use, if None will need to be initialized
                via the labradConnect function before anything can be done.
            config (dict) : A dictionary of configurations settings to pass
            dimensions (int) : The number of dimensions of controllable field. 1 is assumed a simple
                Z-axis manget, 2 is a X-Z vector magnet and 3 is an X-Y-Z vector magnet.
        '''
        self.server = labrad_server
        self.current_to_field = config['current_to_field']
        self.ramprate = config['ramprate']
        self.dimensions = dimensions

        # Status parameters
        self.Bx = 0.0
        self.By = 0.0
        self.Bz = 0.0
        self.setpoint_Bx = 0.0
        self.setpoint_By = 0.0
        self.setpoint_Bz = 0.0

        # Do we need to have seperate values for the different dimensions?
        self.current = 0.0
        self.voltage = 0.0


        self.persist = True

        self.poll()
    #

    @inlineCallbacks
    def poll(self):
        '''
        Read out the values from the equipment: field, current and voltage. Updates internal
        parameters. OVERRIDE for a specific magnet controller.
        '''
        pass
    #

    def setpoint(self, setpoint):
        '''
        Change the setpoint.

        Args:
            setpoint (float or tuple) : If it is a float it's assumed to be the Z-axis field
        '''

    @inlineCallbacks
    def goToSetpoint(self):
        '''
        Ramps to the setpoint. In a vector magnet always goes one dimension at a time in the order: Z-X-Y
        '''
        self.ramp(self.setpoint_Bz, dimension='z')
        if self.dimensions >= 2:
            self.ramp(self.setpoint_Bx, dimensions='x')
        if self.dimensions >= 3:
            self.ramp(self.setpoint_Bz, dimensions='z')
    #

    @inlineCallbacks
    def ramp(self, value, dimension='z'):
        '''
        Ramp the output to a given field.
        '''
        pass
    #

#
