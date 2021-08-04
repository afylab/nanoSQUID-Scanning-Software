import sys
from PyQt5 import QtGui, QtWidgets, QtCore, uic
import numpy as np
import pyqtgraph as pg

path = sys.path[0] + r"\ScriptingModule"
SimulatorWindowUI, QtBaseClass = uic.loadUiType(path + r"\ScriptSimulator.ui")

#Not required, but strongly recommended functions used to format numbers in a particular way.
sys.path.append(sys.path[0]+'\Resources')

class VirtualModule():
    '''
    A virtual modules to take inputs from a script. Will inherit to make a clone
    of a specific module, will have all documented scripting functions (from Marec's)
    thesis, but most of these will be dummy functions. We really just want functions
    that affect the outputs, which will be displayed.
    '''
    eventList = [] # This is a shared varaible, need to specify it when inheriting.

    def addEvent(self, name, *args, **kwargs):
        '''
        For the scripting functions that don't affect the output, still records them
        '''
        self.eventList.append([name, args, kwargs])
        return None
    #

    def set_real_reference(self, module):
        '''
        Sets a reference to the real module that the virtual module simulates
        '''
        self.real = module
    #

    def get_initial_state(self):
        '''
        Get the inital state of things from the interface, i.e. with all the user inputs.
        Override to get particulars for a given module.
        '''
        pass
    #

    def get_stating_outputs(self):
        '''
        Return a dictionary containing the starting values of the outputs if they exist. If they do
        not exist return None
        '''
        return None
    #
#

class Virtual_nSOTBias(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setBias = lambda *args, **kwargs : self.addEvent('setBias', *args, **kwargs)
        self.readBias = lambda *args, **kwargs : self.addEvent('readBias', *args, **kwargs)
        self.setFeedback = lambda *args, **kwargs : self.addEvent('setFeedback', *args, **kwargs)
        self.readFeedback = lambda *args, **kwargs : self.addEvent('readFeedback', *args, **kwargs)
        self.blink = lambda *args, **kwargs : self.addEvent('blink', *args, **kwargs)
        self.setGate = lambda *args, **kwargs : self.addEvent('setGate', *args, **kwargs)
        self.readGate = lambda *args, **kwargs : self.addEvent('readGate', *args, **kwargs)
#

class Virtual_nSOTChar(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setMinVoltage = lambda *args, **kwargs : self.addEvent('setMinVoltage', *args, **kwargs)
        self.setMaxVoltage = lambda *args, **kwargs : self.addEvent('setMaxVoltage', *args, **kwargs)
        self.setVoltagePoints = lambda *args, **kwargs : self.addEvent('setVoltagePoints', *args, **kwargs)
        self.setMinField = lambda *args, **kwargs : self.addEvent('setMinField', *args, **kwargs)
        self.setMaxField = lambda *args, **kwargs : self.addEvent('setMaxField', *args, **kwargs)
        self.setFieldPoints = lambda *args, **kwargs : self.addEvent('setFieldPoints', *args, **kwargs)
        self.readFeedbackVoltage = lambda *args, **kwargs : self.addEvent('readFeedbackVoltage', *args, **kwargs)
        self.setSweepMode = lambda *args, **kwargs : self.addEvent('setSweepMode', *args, **kwargs)
        self.startSweep = lambda *args, **kwargs : self.addEvent('startSweep', *args, **kwargs)
#

class Virtual_TempControl(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.readTherm1 = lambda *args, **kwargs : self.addEvent('readTherm1', *args, **kwargs)
        self.readTherm2 = lambda *args, **kwargs : self.addEvent('readTherm2', *args, **kwargs)
        self.readTherm3 = lambda *args, **kwargs : self.addEvent('readTherm3', *args, **kwargs)
        self.setFeedbackThermometer = lambda *args, **kwargs : self.addEvent('setFeedbackThermometer', *args, **kwargs)
        self.setHeaterMode = lambda *args, **kwargs : self.addEvent('setHeaterMode', *args, **kwargs)
        self.setHeaterOutput = lambda *args, **kwargs : self.addEvent('setHeaterOutput', *args, **kwargs)
        self.setHeaterRange = lambda *args, **kwargs : self.addEvent('setHeaterRange', *args, **kwargs)
        self.setHeaterPID = lambda *args, **kwargs : self.addEvent('setHeaterPID', *args, **kwargs)
        self.setHeaterSetpoint = lambda *args, **kwargs : self.addEvent('setHeaterSetpoint', *args, **kwargs)
        self.setHeaterPercentage = lambda *args, **kwargs : self.addEvent('setHeaterPercentage', *args, **kwargs)
        self.setHeaterOn = lambda *args, **kwargs : self.addEvent('setHeaterOn', *args, **kwargs)
        self.setHeaterOff = lambda *args, **kwargs : self.addEvent('setHeaterOff', *args, **kwargs)
#

class Virtual_SampleChar(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setFourTermMinVoltage = lambda *args, **kwargs : self.addEvent('setFourTermMinVoltage', *args, **kwargs)
        self.setFourTermMaxVoltage = lambda *args, **kwargs : self.addEvent('setFourTermMaxVoltage', *args, **kwargs)
        self.setFourTermVoltagePoints = lambda *args, **kwargs : self.addEvent('setFourTermVoltagePoints', *args, **kwargs)
        self.setFourTermVoltageStepSize = lambda *args, **kwargs : self.addEvent('setFourTermVoltageStepSize', *args, **kwargs)
        self.setFourTermDelay = lambda *args, **kwargs : self.addEvent('setFourTermDelay', *args, **kwargs)
        self.setFourTermOutput = lambda *args, **kwargs : self.addEvent('setFourTermOutput', *args, **kwargs)
        self.setFourTermVoltageInput = lambda *args, **kwargs : self.addEvent('setFourTermVoltageInput', *args, **kwargs)
        self.setFourTermCurrentInput = lambda *args, **kwargs : self.addEvent('setFourTermCurrentInput', *args, **kwargs)
        self.FourTerminalSweep = lambda *args, **kwargs : self.addEvent('FourTerminalSweep', *args, **kwargs)
        self.rampOutputVoltage = lambda *args, **kwargs : self.addEvent('rampOutputVoltage', *args, **kwargs)

    def get_initial_state(self):
        self.sweepParameters = self.real.sweepParameters.copy()
        # self.FourTerminal_ChannelInput = self.real.FourTerminal_ChannelInput
        # self.FourTerminal_ChannelOutput = self.real.FourTerminal_ChannelOutput
        # self.FourTerminal_Output1 = self.real.FourTerminal_Output1
        # self.FourTerminal_Input1 = self.real.FourTerminal_Input1
        # self.FourTerminal_Input2 = self.real.FourTerminal_Input2
        # self.currentDAC_Output = self.real.currentDAC_Output
        # self.setpointDAC_Output = self.real.setpointDAC_Output
    #

    def get_starting_outputs(self):
        '''
        Return a dictionary containing the starting values of the outputs if they exist. If they do
        not exist return None
        '''
        ret = dict()
        for i in range(4):
            ret['DAC'+str(i+1)] = self.real.DAC_output[i]
        return ret
    #

    def _Update_Parameters(self, value, key, range=None):
        if isinstance(value,float) or isinstance(value,int):
            if range == None:
                self.sweepParameters[key] = value
            elif value >= range[0] and value <= range[1]:
                self.sweepParameters[key] = value
    #

    def _setFourTermMinVoltage(self, vmin):
        self._Update_Parameters(vmin, 'FourTerminal_MinVoltage', [-10.0, 10.0])
    #

    def _setFourTermMaxVoltage(self, vmax):
        self._Update_Parameters(vmax, 'FourTerminal_MaxVoltage', [-10.0, 10.0])
    #

    def _setFourTermVoltagePoints(self, points):
        self.sweepParameters['FourTerminal_VoltageSteps_Status'] = "Numberofsteps"
        self.sweepParameters['FourTerminal_VoltageSteps'] = int(round(points))
    #

    def _setFourTermVoltageStepSize(self, vstep):
        self.sweepParameters['FourTerminal_VoltageSteps_Status'] = "StepSize"
        Max, Min, SS = self.sweepParameters['FourTerminal_MaxVoltage'], self.sweepParameters['FourTerminal_MinVoltage'], float(vstep)
        self.sweepParameters['FourTerminal_VoltageSteps']=int((Max-Min)/float(SS)+1)

    def _setFourTermDelay(self, delay):
        self._Update_Parameters(delay, 'FourTerminal_Delay')
    #

    def _setFourTermOutput(self, output):
        self.FourTerminal_Output1 = output-1
    #

    def _setFourTermVoltageInput(self, inp):
        self.FourTerminal_Input1 = inp-1
    #

    def _setFourTermCurrentInput(self, inp):
        self.FourTerminal_Input2 = inp-1
    #

    def _FourTerminalSweep(self):
        self.FourTerminal_ChannelOutput=[self.FourTerminal_Output1]
        self.FourTerminal_ChannelInput=[self.FourTerminal_Input1]

        dt, points = self._Ramp1(self.FourTerminal_ChannelOutput[0],self.currentDAC_Output[self.FourTerminal_ChannelOutput[0]],self.sweepParameters['FourTerminal_MinVoltage'],10000,100)    #ramp to initial value

        ix = "DAC"+str(self.FourTerminal_ChannelOutput[0]+1)
        points[ix].append(self.sweepParameters['FourTerminal_MaxVoltage'])
        dt.append(self.sweepParameters['FourTerminal_VoltageSteps']*self.sweepParameters['FourTerminal_Delay'])

        dt_2, points_2 = self._Ramp1(self.FourTerminal_ChannelOutput[0],self.sweepParameters['FourTerminal_MaxVoltage'],0.0,10000,100)
        dt.append(dt_2[0])
        points[ix].append(points_2[ix][0])

        return dt, points
    #

    def _rampOutputVoltage(self, channel, vfinal, points, delay):
        #Convert delay from seconds to microseconds.
        channel = channel-1
        return self._Ramp1(channel,self.currentDAC_Output[channel],vfinal,points,int(delay*1e6))
    #

    def _Ramp1(self, SweepPort, Startingpoint, Endpoint, Numberofsteps, Delay):
        time = Numberofsteps*Delay*1e-6
        ret = dict()
        ret["DAC"+str(SweepPort+1)] = [Endpoint]
        return [time], ret
    #
#

'''
MAGNET CONTROL NEEDS TO BE GENERALIZED TO WORK ON ALL SYSTEMS,
THIS IS NOT FINISHED BUT WILL NEED TO BE RE-WRITTEN
'''
class Virtual_FieldControl(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setSetpoint = lambda *args, **kwargs : self.addEvent('setSetpoint', *args, **kwargs)
        self.setField = lambda *args, **kwargs : self.addEvent('setField', *args, **kwargs)
        self.readField = lambda *args, **kwargs : self.addEvent('readField', *args, **kwargs)
        self.readPersistField = lambda *args, **kwargs : self.addEvent('readPersistField', *args, **kwargs)
        self.hold = lambda *args, **kwargs : self.addEvent('hold', *args, **kwargs)
        self.clamp = lambda *args, **kwargs : self.addEvent('clamp', *args, **kwargs)
        self.setPersist = lambda *args, **kwargs : self.addEvent('setPersist', *args, **kwargs)

    # def get_initial_state(self):
    #     self.currField = self.real.currField
    #     self.ramprate = self.real.ramprate
    #     self.setpoint = self.real.setpoint
    # #
    #
    # def get_stating_outputs(self):
    #     return {'B':[self.currField]}
    # #

    def _setField(self, B):
        points = {'B':[B]}
        dt = [np.abs(self.currField - B)/self.ramprate]
        self.currField = B
        return dt, points

    def _setSetpoint(self, B):
        self.setpoint = B
    #

    def _setRamprate(self, rate):
        self.ramprate = rate

    def _hold(self):
        pass
    #

    def _setPersist(self, on):
        pass
    #
#

class Virtual_Approach(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self, ScanControl):
        self.setPLLThreshold = lambda *args, **kwargs : self.addEvent('setPLLThreshold', *args, **kwargs)
        self.withdraw = lambda *args, **kwargs : self.addEvent('withdraw', *args, **kwargs)
        self.setHeight = lambda *args, **kwargs : self.addEvent('setHeight', *args, **kwargs)
        self.approachConstHeight = lambda *args, **kwargs : self.addEvent('approachConstHeight', *args, **kwargs)
        self.getContactPosition = lambda *args, **kwargs : self.addEvent('getContactPosition', *args, **kwargs)
        self.setFrustratedFeedback = lambda *args, **kwargs : self.addEvent('setFrustratedFeedback', *args, **kwargs)

        self.ScanControl = ScanControl # The virtual ScanControl, which also affects the Z output
    #

    def get_initial_state(self):
        self.generalSettings = self.real.generalSettings.copy()
        self.PIDApproachSettings = self.real.PIDApproachSettings.copy()
        self.curr_z = self.real.Atto_Z_Voltage/self.real.z_volts_to_meters
    #

    def syncScanControl(self):
        self.curr_x = self.ScanControl.curr_z

    def get_stating_outputs(self):
        return {'Z':[self.curr_z]}
    #

    def _setHeight(self, height):
        if isinstance(height,float):
            if height < 0:
                height = 0
            elif height > self.generalSettings['total_retract_dist']:
                height = self.generalSettings['total_retract_dist']
            self.PIDApproachSettings['height'] = height
    #

    def _withdraw(self, dist):
        self.syncScanControl()
        stopz = self.curr_z + dist
        if stopz > self.generalSettings['total_retract_dist']:
            stopz = self.generalSettings['total_retract_dist']
        dt = (stopz - self.curr_z)/self.generalSettings['pid_retract_speed']
        self.curr_z = stopz
        self.ScanControl._setHeight(stopz)

        points = {'Z':[self.curr_z]}
        return [dt], points
    #

    def _approachConstHeight(self):
        '''
        Simulates an approach, since this is what calibrates the height it can never quite
        know how long this is going to take, but make the best guess by assuming the surface is at Z=0
        in whatever the current coordinates are and the retraction length.
        '''
        self.syncScanControl()
        startz = self.curr_z
        touchdownz = 0.0 # First assume it goes to zero
        finalz = self.PIDApproachSettings['height']
        self.curr_z = finalz
        self.ScanControl._setHeight(finalz)
        points = {'Z':[touchdownz, finalz]}
        dt = [(startz-touchdownz)/self.PIDApproachSettings['step_speed'], (finalz-touchdownz)/self.generalSettings['pid_retract_speed']]
        return dt, points
#

class Virtual_ScanControl(VirtualModule):
    eventList = VirtualModule.eventList # to make it shared across all virtual modules
    def __init__(self):
        self.setPosition = lambda *args, **kwargs : self.addEvent('setPosition', *args, **kwargs)
        self.startScan = lambda *args, **kwargs : self.addEvent('startScan', *args, **kwargs)
        self.setSpeed = lambda *args, **kwargs : self.addEvent('setSpeed', *args, **kwargs)
        self.setDelay = lambda *args, **kwargs : self.addEvent('setDelay', *args, **kwargs)
        self.setPixels = lambda *args, **kwargs : self.addEvent('setPixels', *args, **kwargs)
        self.setLines = lambda *args, **kwargs : self.addEvent('setLines', *args, **kwargs)
        self.lockDataAspect = lambda *args, **kwargs : self.addEvent('lockDataAspect', *args, **kwargs)
        self.unlockDataAspect = lambda *args, **kwargs : self.addEvent('unlockDataAspect', *args, **kwargs)
        self.setTilt = lambda *args, **kwargs : self.addEvent('setTilt', *args, **kwargs)
        self.setXc = lambda *args, **kwargs : self.addEvent('setXc', *args, **kwargs)
        self.setYc = lambda *args, **kwargs : self.addEvent('setYc', *args, **kwargs)
        self.setH = lambda *args, **kwargs : self.addEvent('setH', *args, **kwargs)
        self.setW = lambda *args, **kwargs : self.addEvent('setW', *args, **kwargs)
        self.setAngle = lambda *args, **kwargs : self.addEvent('setAngle', *args, **kwargs)
        self.lockScanAspect = lambda *args, **kwargs : self.addEvent('lockScanAspect', *args, **kwargs)
        self.unlockScanAspect = lambda *args, **kwargs : self.addEvent('unlockScanAspect', *args, **kwargs)
    #

    def get_initial_state(self):
        '''
        Get the state of things from the interface.
        '''
        self.x = self.real.x
        self.y = self.real.y
        self.Xc = self.real.Xc
        self.Yc = self.real.Yc
        self.W = self.real.W
        self.H = self.real.H
        self.angle = self.real.angle
        self.x_tilt = self.real.x_tilt
        self.y_tilt = self.real.y_tilt
        self.x_center = self.real.x_center
        self.y_center = self.real.y_center
        self.z_center = self.real.z_center

        self.curr_x = self.real.Atto_X_Voltage/self.real.x_volts_to_meters
        self.curr_y = self.real.Atto_Y_Voltage/self.real.y_volts_to_meters
        self.curr_z = self.real.Atto_Z_Voltage/self.real.z_volts_to_meters

        self.lines = self.real.lines
        self.pixels = self.real.pixels
        self.linearSpeed = self.real.linearSpeed
        self.lineTime = self.real.lineTime
        self.delayTime = self.real.delayTime
        self.scanSmooth = self.real.scanSmooth
        self.voltageStepSize = self.real.voltageStepSize
    #

    def get_stating_outputs(self):
        '''
        Return a dictionary containing the starting values of the outputs if they exist. If they do
        not exist return None
        '''
        ret = dict()
        ret['X'] = self.real.curr_x
        ret['Y'] = self.real.curr_y
        return ret
    #

    def _setXc(self, Xc):
        self.Xc = Xc
        self.x = Xc + self.H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2

    def _setYc(self, Yc):
        self.Yc = Yc
        self.y = Yc - self.H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2

    def _setH(self, H):
        self.H = H
        self.x = self.Xc + H*np.sin(self.angle*np.pi/180)/2 - self.W*np.cos(self.angle*np.pi/180)/2
        self.y = self.Yc - H*np.cos(self.angle*np.pi/180)/2 - self.W*np.sin(self.angle*np.pi/180)/2

    def _setW(self, W):
        self.W = W
        self.x = self.Xc + self.H*np.sin(self.angle*np.pi/180)/2 - W*np.cos(self.angle*np.pi/180)/2
        self.y = self.Yc - self.H*np.cos(self.angle*np.pi/180)/2 - W*np.sin(self.angle*np.pi/180)/2

    def _setAngle(self, theta):
        self.angle = theta
        self.x = self.Xc + self.H*np.sin(theta*np.pi/180)/2 - self.W*np.cos(theta*np.pi/180)/2
        self.y = self.Yc - self.H*np.cos(theta*np.pi/180)/2 - self.W*np.sin(theta*np.pi/180)/2

    def _setTilt(self, xtilt, ytilt):
        self.x_tilt = xtilt*np.pi / 180
        self.y_tilt = ytilt*np.pi / 180

    def _setLines(self, lines):
        self.lines = int(lines)
        self.lineTime = self.pixels*self.delayTime

    def _setSpeed(self, speed):
        self.scanSmooth = True
        self.linearSpeed = speed
        self.lineTime = self.W/self.linearSpeed

    def _setDelay(self, delay):
        self.scanSmooth = False
        self.delayTime = delay
        self.lineTime = self.pixels * self.delayTime

    def _setPixels(self, pixels):
        self.pixels = int(pixels)
        self.lineTime = self.pixels * self.delayTime

    def _setHeight(self, height):
        self.curr_z = height
        self.z_center = self.curr_z

    def _getPlaneCoordinates(self, x,y):
        '''
        When in constant height mode, we always want to be moving on a plane. This function returns
        the Z value in constant height mode at X, Y. Based on how the Scan Control getPlaneVoltages
        function.
        '''
        z = self.z_center - np.tan(self.x_tilt)*(x-self.x_center) - np.tan(self.y_tilt)*(y-self.y_center)
        return np.array([z, x, y])
    #

    def _updateScanPlaneCenter(self):
        '''
        Sets the current x, y, z position to be the center of the scan plane.
        '''
        self.z_center = (self.real.Atto_Z_Voltage) / self.real.z_volts_to_meters
        self.x_center = self.real.Atto_X_Voltage / self.real.x_volts_to_meters - self.real.x_meters_max/2
        self.y_center = self.real.Atto_Y_Voltage / self.real.y_volts_to_meters - self.real.y_meters_max/2

    def _updateScanParameters(self):
        '''
        Replicates the update scan parameters function from the ScanControl module,
        generates the scan parameters that will be used to make a 2D scan.
        '''
        #-------------------------------------------------------------------------------------------------#
        '''
        Single Line Scan Calculation
        '''

        #Calculate the number of points, delta_x/delta_y/delta_z for scanning a line
        dx = self.W * np.cos(np.pi*self.angle/180)
        dy = self.W * np.sin(np.pi*self.angle/180)
        line_z, line_x, line_y = self._getPlaneCoordinates(dx, dy) - self._getPlaneCoordinates(0,0)

        line_points = int(np.maximum(np.absolute(line_x*self.real.x_volts_to_meters / (self.voltageStepSize)), np.absolute(line_y*self.real.y_volts_to_meters / (self.voltageStepSize))))
        #If the scan range is so small that the number of steps to take with high resolution is
        #less than the desired number of pixels to have in the scan, set the number of points to
        #be the deisred number of pixels. This means that, in reality, several points will be taken
        #at the same position. But w/e dude
        if line_points < self.pixels:
            line_points = self.pixels
        line_delay = int(1e6 *self.lineTime / line_points)

        #-------------------------------------------------------------------------------------------------#
        '''
        Move to next line scan calculation
        '''
        #Calculate the speed, number of points, and delta_x/delta_y for moving to the next line
        #If only doing 1 line, then don't move pixels at all!
        if self.lines > 1:
            dx = -self.H * np.sin(np.pi*self.angle/180)/ (self.lines - 1)
            dy = self.H * np.cos(np.pi*self.angle/180)/ (self.lines - 1)
        else:
            dx = 0
            dy = 0

        pixel_z, pixel_x, pixel_y = self._getPlaneCoordinates(dx, dy) - self._getPlaneCoordinates(0,0)

        pixel_points = int(np.maximum(np.absolute(pixel_x*self.real.x_volts_to_meters / (self.voltageStepSize)), np.absolute(pixel_y*self.real.y_volts_to_meters / (self.voltageStepSize))))
        if pixel_points == 0:
            pixel_points = 1
        if self.lines >1:
            pixel_delay = int(1e6 *self.H / ((self.lines-1)*self.linearSpeed*pixel_points))
        else:
            pixel_delay = 1e3

        self.scanParameters = {
            'line_x'                     : line_x, #volts that need to be moved in the x direction for the scan of a single line
            'line_y'                     : line_y, #volts that need to be moved in the y direction for the scan of a single line
            'line_z'                     : line_z, #volts that need to be moved in the z direction for the scan of a single line
            'line_points'                : line_points, #number of points that should be taken for minimum step resolution for a single line
            'line_delay'                 : line_delay, #delay between points for a single line to ensure proper speed
            'pixel_x'                    : pixel_x, #volts that need to be moved in the x direction to move from one line scan to the next
            'pixel_y'                    : pixel_y, #volts that need to be moved in the y direction to move from one line scan to the next
            'pixel_z'                    : pixel_z, #volts that need to be moved in the y direction to move from one line scan to the next
            'pixel_points'               : pixel_points, #number of points that should be taken for minimum step resolution for moving to next line
            'pixel_delay'                : pixel_delay, #delay between points for a single line to ensure proper speed
        }

    def _setPosition(self, x, y):
        points = dict()
        z, x, y = self._getPlaneCoordinates(x,y)
        points['X'] = [x]
        points['Y'] = [y]
        points['Z'] = [z]
        delta_x_pos = (self.curr_x - x)
        delta_y_pos = (self.curr_y - y)
        time = np.sqrt(delta_x_pos**2 + delta_y_pos**2) / self.linearSpeed

        self.curr_x = x
        self.curr_y = y
        self.curr_z = z
        return [time], points
    #

    def _startScan(self):
        time, points = self._setPosition(self.x, self.y) # Move to the starting point
        startx, starty, startz = points['X'][-1], points['Y'][-1], points['Z'][-1]

        self._updateScanParameters()

        for i in range(0, self.lines):
            stopx, stopy, stopz = startx + self.scanParameters['line_x'], starty + self.scanParameters['line_y'], startz + self.scanParameters['line_z']
            # Trace
            points['X'].append(stopx)
            points['Y'].append(stopy)
            points['Z'].append(stopz)
            if self.scanSmooth:
                time.append(self.scanParameters['line_points']*self.scanParameters['line_delay']/1.0e6)
            else:
                time.append([self.pixels*self.delayTime])

            # Retrace
            points['X'].append(startx)
            points['Y'].append(starty)
            points['Z'].append(startz)
            if self.scanSmooth:
                time.append(self.scanParameters['line_points']*self.scanParameters['line_delay']/1.0e6)
            else:
                time.append([self.pixels*self.delayTime])

            # Move to next line
            if i < self.lines - 1:
                stopx, stopy, stopz = startx + self.scanParameters['pixel_x'], starty + self.scanParameters['pixel_y'], startz + self.scanParameters['pixel_z']
                points['X'].append(stopx)
                points['Y'].append(stopy)
                points['Z'].append(stopz)
                time.append(self.scanParameters['pixel_points']*self.scanParameters['pixel_delay']/1.0e6)
            startx, starty, startz = stopx, stopy, stopz
            self.curr_x, self.curr_y, self.curr_z = startx, starty, startz
        return time, points
#

class CustomViewBox(pg.ViewBox):
    '''
    Viewbox that allows for selecting range, taken from PyQtGraphs documented examples
    '''
    def __init__(self, *args, **kwds):
        kwds['enableMenu'] = False
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)
    #

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            self.autoRange()
    #

    ## reimplement mouseDragEvent to disable continuous axis zoom
    def mouseDragEvent(self, ev, axis=None):
        if axis is not None and ev.button() == QtCore.Qt.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev, axis=axis)
#

class ScriptSimulator(QtWidgets.QMainWindow, SimulatorWindowUI):
    '''
    A window to display the potential experimental outputs of a given script to
    evaluate it prior to running the script.
    '''
    def __init__(self, reactor, mainWindow, parent=None, *args):
        super(ScriptSimulator, self).__init__(parent)

        self.reactor = reactor

        self.setupUi(self)
        self.setupAdditionalUi()

        # instantiate all the virtual modules
        self.ScanControl = Virtual_ScanControl()
        self.ScanControl.set_real_reference(getattr(mainWindow, "ScanControl"))

        self.Approach = Virtual_Approach(self.ScanControl)
        self.Approach.set_real_reference(getattr(mainWindow, "Approach"))

        self.nSOTChar = Virtual_nSOTChar()
        self.nSOTChar.set_real_reference(getattr(mainWindow, "nSOTChar"))

        self.FieldControl = Virtual_FieldControl()
        self.FieldControl.set_real_reference(getattr(mainWindow, "FieldControl"))

        self.TempControl = Virtual_TempControl()
        self.TempControl.set_real_reference(getattr(mainWindow, "TempControl"))

        self.SampleChar = Virtual_SampleChar()
        self.SampleChar.set_real_reference(getattr(mainWindow, "SampleCharacterizer"))

        self.nSOTBias = Virtual_nSOTBias()
        self.nSOTBias.set_real_reference(getattr(mainWindow, "GoToSetpoint"))

        self.virtual_mods = (self.ScanControl, self.Approach, self.nSOTChar, self.FieldControl, self.TempControl, self.SampleChar, self.nSOTBias)
    #

    def change_labels(self, plot, outputLabel, units):
        plot.setLabel('left', outputLabel, units=units)
        plot.setLabel('bottom', 'time', units = 's')
        plot.showAxis('right', show = True)
        plot.showAxis('top', show = True)
        plot.setTitle(outputLabel+' vs. Time (s)')

    def setupAdditionalUi(self):
        '''
        Add in the plotting components
        '''
        viewB1 = CustomViewBox()
        self.plot1 = pg.PlotWidget(parent=self.plotArea1, viewBox=viewB1)
        viewB2 = CustomViewBox()
        self.plot2 = pg.PlotWidget(parent=self.plotArea2, viewBox=viewB2)
        viewB3 = CustomViewBox()
        self.plot3 = pg.PlotWidget(parent=self.plotArea3, viewBox=viewB3)

        # Link the X axes
        self.plot2.setXLink(self.plot1)
        self.plot3.setXLink(self.plot1)

        self.plots = [self.plot1, self.plot2, self.plot3]
        for plot in self.plots:
            plot.setGeometry(QtCore.QRect(0,0,600,260))
            self.change_labels(plot, "Output", "unit")
    #

    def moveDefault(self):
        self.move(10,170)
    #

    def get_virtual_modules(self):
        '''
        Return all the virtual modules
        '''
        return self.virtual_mods
    #

    def sleep(self, secs):
        '''
        Takes the place of the sleep command without actually sleeping the program.
        '''
        pass
        #print("sleeping " + str(secs))
    #

    def formatVal(self, val):
        if np.abs(val) < 1e-7 and val != 0.0:
            s = str(round(val/1.0e-9, 3)) + 'n'
        elif np.abs(val) < 1e-4 and val != 0.0:
            s = str(round(val/1.0e-6, 3)) + 'u'
        else:
            s = str(round(val, 3))
        return s

    def changePlot(self, lbl, plotNum):
        plotNum = str(plotNum)
        lbl = str(lbl)
        plot = getattr(self, "plot" + plotNum)
        plot.clear()
        data = self.outputs[lbl]
        plot.plot(self.time, data)

        cbox = getattr(self, "var_select_" + plotNum)
        cbox.setCurrentIndex(cbox.findText(lbl))

        # Update the stats
        l = getattr(self, "label_min_"+plotNum)
        l.setText(self.formatVal(np.min(data)))
        l = getattr(self, "label_max_"+plotNum)
        l.setText(self.formatVal(np.max(data)))
        l = getattr(self, "label_avg_"+plotNum)
        l.setText(self.formatVal(np.mean(data)))

        self.change_labels(plot, lbl, self.outputs_units[lbl])
    #

    def showSim(self):
        '''
        Display the simulation module
        '''
        for plot in self.plots:
            plot.clear()

        options = list(self.outputs.keys())
        options.sort()
        for i in range(3):
            cbox = getattr(self, "var_select_" + str(i+1))
            cbox.clear()
            for option in options:
                cbox.addItem(option)
            cbox.activated[str].connect(lambda txt, ix=i+1: self.changePlot(txt, ix))

        defaults = ['X', 'Y', 'Z']
        for i in range(3):
            self.changePlot(defaults[i], i+1)
        #

        self.showNormal()
        self.moveDefault()
        self.raise_()

    # ----------------------------------------------------------------#
    '''
    Functions related to turning the scripting input into simulated outputs
    '''

    def addPoints(self, dt, points):
        '''
        Add points to all the outputs that are in the given 'points' dictionary. All other outputs
        still get points added but are assumed to be held constant during these operations.

        It's assumed that the values of the points dictionary all contain the same number of points,
        otherwise errors can occur.

        Args:
            dt (list) : A list of the time it takes to move to each point
            points (dict) : A dictionary of points to add
        '''
        # get the number of points
        keys = list(points.keys())
        N = len(points[keys[0]])
        self.timing.extend(dt)

        # Loop through the variables in points and add in their
        for k in keys:
            self.outputs[k].extend(points[k])

        # Loop through all the other variables
        for k in list(self.outputs.keys()):
            if k not in keys:
                const = self.outputs[k][-1] # get the last value, which is held constant
                self.outputs[k].extend([const]*N) # Populate that output with constant values
    #

    def compile(self):
        '''
        Takes all the data from the virtual modules
        '''
        try:
            # print(VirtualModule.eventList) # For Debugging

            # Define the various outputs
            self.outputs = dict()
            self.outputs_units = dict()
            self.timing = [0.0]

            # Get starting values for the virtual modules
            for mod in self.virtual_mods:
                mod.get_initial_state()

            # Scanning outputs
            start = self.ScanControl.get_stating_outputs()
            for k in ['X', 'Y']:
                self.outputs[k] = [start[k]]
                self.outputs_units[k] = "m"

            # Z height from approach module
            start = self.Approach.get_stating_outputs()
            self.outputs['Z'] = start["Z"]
            self.outputs_units['Z'] = "m"

            # Sample DAC Outputs
            start = self.SampleChar.get_starting_outputs()
            for k in list(start.keys()):
                self.outputs[k] = [start[k]]
                self.outputs_units[k] = "V"

            # Magnetic Field
            # self.outputs['Magnetic Field'] = []
            # self.outputs_units['Magnetic Field'] = "T"


            # Loop through the event list and handel functions that affect the defined outputs
            N = len(VirtualModule.eventList)
            for i in range(N):
                event = VirtualModule.eventList[i]
                if event[0] in ["setPosition", "startScan"]:
                    # Things that update the X, Y, Z output from the ScanControl Module
                    dt, points = getattr(self.ScanControl, "_"+event[0])(*event[1], **event[2])
                    self.addPoints(dt, points) # Update outputs, all other outputs are assumed to be constant
                elif event[0] in ["setTilt", "setXc", "setYc", "setH", "setW", "setAngle", "setPixels", "setLines", "setSpeed", "setDelay"]:
                    # Things that affect the virtual state of the ScanControl but don't change outputs
                    getattr(self.ScanControl, "_"+event[0])(*event[1], **event[2])
                elif event[0] in ["approachConstHeight", "withdraw"]:
                    # Things that affect the outputs, from the Approach module
                    dt, points = getattr(self.Approach, "_"+event[0])(*event[1], **event[2])
                    self.addPoints(dt, points) # Update outputs, all other outputs are assumed to be constant
                elif event[0] in ["setHeight"]:
                    # Things that affect the virtual state of the Approach module but don't change outputs
                    getattr(self.Approach, "_"+event[0])(*event[1], **event[2])
                elif event[0] in ["FourTerminalSweep", "rampOutputVoltage"]:
                    # Things that affect the sample voltage outputs
                    dt, points = getattr(self.SampleChar, "_"+event[0])(*event[1], **event[2])
                    self.addPoints(dt, points) # Update outputs, all other outputs are assumed to be constant
                elif event[0] in ["setFourTermMinVoltage", "setFourTermMaxVoltage", "setFourTermOutput", "setFourTermVoltageInput", "setFourTermCurrentInput", "setFourTermDelay", "setFourTermVoltageStepSize", "setFourTermVoltagePoints"]:
                    # Things that affect the state of the SampleChar virtual module but do not change the outputs
                    getattr(self.SampleChar, "_"+event[0])(*event[1], **event[2])
                # elif event[0] in ["setField"]:
                #     # Things that affect the magnetic field
                #     dt, points = getattr(self.FieldControl, "_"+event[0])(*event[1], **event[2])
                #     self.addPoints(dt, points) # Update outputs, all other outputs are assumed to be constant
                # elif event[0] in ["setSetpoint", "hold", "setPersist", "setRamprate"]:
                #     # Things that affect the state of the FieldControl virtual but do not change the outputs
                #     getattr(self.FieldControl, "_"+event[0])(*event[1], **event[2])

            # Put everything in numpy format
            N = -1
            for k in list(self.outputs.keys()):
                self.outputs[k] = np.array(self.outputs[k]) # convert to numpy
                if N < 0:
                    N = len(self.outputs[k])
                else:
                    if len(self.outputs[k]) != N:
                        raise ValueError("Outputs have an inconsistent number of points.")

            # Integrate to get the time basis
            if len(self.timing) > 1:
                for i in range(1, len(self.timing)):
                    self.timing[i] = self.timing[i] + self.timing[i-1]
            self.time = np.array(self.timing)

            # Clear the event list for the next simulation
            # There is a better way to do this in python 3
            del VirtualModule.eventList[:]
        except:
            from traceback import format_exc
            print(format_exc())
    #


#
