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
name = Cryo Positioning Systems Controller (CPSC) Server
version = 1.0
description = Communicates with the CPSC which controls the JPE piezo stacks. 
Must be placed in the same directory as cacli.exe in order to work. 
### END NODE INFO
"""

from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor, defer
import labrad.units as units
from labrad.types import Value
import time
import numpy as np
import zhinst
import zhinst.utils
import sys


class HF2LIServer(LabradServer):
    name = "HF2LI Server"    # Will be labrad name of server
 
    def initServer(self):  # Do initialization here
        self.daq = None
        self.dev_ID = None
        self.device_list = None
        self.props = None
        self.sweeper = None
        self.pidAdvisor = None
        print "Server initialization complete"
        
    @inlineCallbacks
    def initPIDAdvisor(self, c = None):
        self.pidAdvisor = yield self.daq.pidAdvisor()
        #Set device
        yield self.pidAdvisor.set('pidAdvisor/device', self.dev_ID)
        #Automatic response calculation triggered by parameter change.
        yield self.pidAdvisor.set('pidAdvisor/auto', 1)
        #Adjusts the demodulator bandwidth to fit best to the specified target bandwidth of the full system.
        yield self.pidAdvisor.set('pidAdvisor/pid/autobw', 1)
        # DUT model
        # source = 4: Internal PLL
        yield self.pidAdvisor.set('pidAdvisor/dut/source', 4)
        # IO Delay of the feedback system describing the earliest response
        # for a step change. This parameter does not affect the shape of
        # the DUT transfer function
        yield self.pidAdvisor.set('pidAdvisor/dut/delay', 0.0)

    @setting(100,returns = '')
    def detect_devices(self,c):
        """ Attempt to connect to the LabOne server (not a LadRAD server) and get a list of devices."""
        try:
            self.daq = yield zhinst.utils.autoConnect()
            print 'LabOne DAQ Server detected.'
            self.device_list = yield zhinst.utils.devices(self.daq)
            print 'Devices connected to LabOne DAQ Server are the following:'
            print self.device_list
        except RuntimeError:
            print ('Failed to detected LabOne DAQ Server and an associated Zurich Instruments device.'
                ' Check that everything is plugged into the computer.')
    
    @setting(101,returns = '*s')
    def get_device_list(self,c):
        """Returns the list of devices. If none have been detected (either because detect_devices has not yet
        been run, or because of a bad connection), this will return None. """
        returnValue(self.device_list)
            
    @setting(102,dev_ID = 's', returns = '')
    def select_device(self, c, dev_ID="None"):
        """Sets the active device ID to the provided dev_ID. If no dev_ID is provided, sets the active
        device to the first device from the device list. Sets the API level to 1, which should provide 
        all the functionality for the HF2LI."""
        if dev_ID == "None":
            self.dev_ID = self.device_list[0]
            (self.daq, self.dev_ID, self.props) = yield zhinst.utils.create_api_session(self.dev_ID, 1)
            self.initPIDAdvisor()
        else: 
            if dev_ID in self.device_list:
                self.dev_ID = dev_ID
                (self.daq, self.dev_ID, self.props) = yield zhinst.utils.create_api_session(self.dev_ID, 1)
                self.initPIDAdvisor()
            else:
                print "Provided device ID is not in the list of possible devices."
   
    @setting(103,settings = '*s', returns = '')
    def set_settings(self, c, settings):
        """Simultaneously set all the settings described in the settings input. Settings should be a 
            list of string and input tuples, where the string provides the node information and the
            input is the required input. For example: 
            setting =   [['/%s/demods/*/enable' % self.dev=ID, 0],
                        ['/%s/demods/*/trigger' % self.dev=ID, 0],
                        ['/%s/sigouts/*/enables/*' % self.dev=ID, 0],
                        ['/%s/scopes/*/enable' % self.dev=ID, 0]]
            This function allows changing multiple settings quickly, however it requires knowledge 
            of the node names. Every setting that can be set through this function can also be 
            set through other functions."""
        yield daq.set(settings)
        
    @setting(104,returns = '')
    def sync(self,c):
        """Perform a global synchronisation between the device and the data server:
            Ensure that the settings have taken effect on the device before setting
            the next configuration."""
        yield self.daq.sync()
               
    @setting(105,returns = '')
    def disable_outputs(self,c):
        """Create a base instrument configuration: disable all outputs, demods and scopes."""
        general_setting = [['/%s/demods/*/enable' % self.dev_ID, 0],
                           ['/%s/demods/*/trigger' % self.dev_ID, 0],
                           ['/%s/sigouts/*/enables/*' % self.dev_ID, 0],
                           ['/%s/scopes/*/enable' % self.dev_ID, 0]]
        yield self.daq.set(general_setting)
        # Perform a global synchronisation between the device and the data server:
        # Ensure that the settings have taken effect on the device before setting
        # the next configuration.

        
    @setting(106,input_channel = 'i', on = 'b', returns = '')
    def set_ac(self, c, input_channel, on):
        """Set the AC coupling of the provided input channel (1 indexed) to on, if on is True, 
        and to off, if on is False"""
        setting = ['/%s/sigins/%d/ac' % (self.dev_ID, input_channel-1), on],
        yield self.daq.set(setting)
        
    @setting(107,input_channel = 'i', on = 'b', returns = '')
    def set_imp50(self, c, input_channel, on):
        """Set the input impedance of the provided input channel (1 indexed) to 50 ohms, if on is True, 
        and to 1 mega ohm, if on is False"""
        setting = ['/%s/sigins/%d/imp50' % (self.dev_ID, input_channel-1), on],
        yield self.daq.set(setting)
        
    @setting(108,input_channel = 'i', amplitude = 'v[]', returns = '')
    def set_range(self, c, input_channel, amplitude):
        """Set the input voltage range of the provided input channel (1 indexed) to the provided amplitude in Volts."""
        setting = ['/%s/sigins/%d/range' % (self.dev_ID, input_channel-1), amplitude],
        yield self.daq.set(setting)
        
    @setting(1080,input_channel = 'i', returns = 'v[]')
    def get_range(self, c, input_channel):
        """Set the input voltage range of the provided input channel (1 indexed) to the provided amplitude in Volts."""
        setting = '/%s/sigins/%d/range' % (self.dev_ID, input_channel-1)
        range = yield self.daq.get(setting, True)
        returnValue(float(range[setting]))
        
    @setting(109,input_channel = 'i', on = 'b', returns = '')
    def set_diff(self, c, input_channel, on):
        """Set the input mode of the provided input channel (1 indexed) to differential, if on is True, 
        and to single ended, if on is False"""
        setting = ['/%s/sigins/%d/diff' % (self.dev_ID, input_channel-1), on],
        yield self.daq.set(setting)
        
    @setting(110,osc_index= 'i', freq = 'v[]', returns = '')
    def set_oscillator_freq(self,c, osc_index, freq):
        """Set the frequency of the designated oscillator (1 indexed) to the provided frequency. The HF2LI Lock-in has
        two oscillators. """
        setting = ['/%s/oscs/%d/freq' % (self.dev_ID, osc_index-1), freq],
        yield self.daq.set(setting)
        
    @setting(111,demod_index= 'i', oscselect = 'i', returns = '')
    def set_demod_osc(self,c, demod_index, oscselect):
        """Sets the provided demodulator to select the provided oscillator as its reference frequency. The HF2LI Lock-in has
        six demodulators and two oscillators."""
        setting = ['/%s/demods/%d/oscselect' % (self.dev_ID, demod_index-1), oscselect-1],
        yield self.daq.set(setting)
        
    @setting(112,demod_index= 'i', harm = 'i', returns = '')
    def set_demod_harm(self,c, demod_index, harm):
        """Sets the provided demodulator harmonic. Demodulation frequency will be the reference oscillator times the provided
        integer harmonic."""
        setting = ['/%s/demods/%d/harmonic' % (self.dev_ID, demod_index-1), harm],
        yield self.daq.set(setting)
        
    @setting(113,demod_index= 'i', phase = 'v[]', returns = '')
    def set_demod_phase(self,c, demod_index, phase):
        """Sets the provided demodulator phase."""
        setting = ['/%s/demods/%d/phaseshift' % (self.dev_ID, demod_index-1), phaseshift],
        yield self.daq.set(setting)
        
    @setting(114,demod_index= 'i', input_channel = 'i', returns = '')
    def set_demod_input(self,c, demod_index, input_channel):
        """Sets the provided demodulator phase."""
        setting = ['/%s/demods/%d/adcselect' % (self.dev_ID, demod_index-1), input_channel-1],
        yield self.daq.set(setting)
        
    @setting(115,demod_index= 'i', time_constant = 'v[]', returns = '')
    def set_demod_time_constant(self,c, demod_index, time_constant):
        """Sets the provided demodulator time constant in seconds."""
        setting = ['/%s/demods/%d/timeconstant' % (self.dev_ID, demod_index-1), time_constant],
        yield self.daq.set(setting)
        
    @setting(1150,demod_index= 'i', returns = 'v[]')
    def get_demod_time_constant(self,c, demod_index):
        """Sets the provided demodulator time constant in seconds."""
        setting = '/%s/demods/%d/timeconstant' % (self.dev_ID, demod_index-1)
        tc = yield self.daq.get(setting, True)
        returnValue(float(tc[setting]))
        
    @setting(116,demod_index = 'i', rec_time= 'v[]', timeout = 'i', returns = '**v[]')
    def poll_demod(self,c, demod_index, rec_time, timeout):
        """This function returns subscribed data previously in the API's buffers or
            obtained during the specified time. It returns a dict tree containing
            the recorded data. This function blocks until the recording time is
            elapsed. Recording time input is in seconds. Timeout time input is in 
            milliseconds. Recommended timeout value is 500ms."""
        
        path = '/%s/demods/%d/sample' % (self.dev_ID, demod_index-1)
        yield self.daq.flush()
        yield self.daq.subscribe(path)
        
        ans = yield self.daq.poll(rec_time, timeout, 1, True)
        
        x_data = ans[path]['x']
        y_data = ans[path]['y']
        
        yield self.daq.unsubscribe(path)
        
        returnValue([x_data, y_data])
        
    @setting(117,output_channel = 'i', on = 'b', returns = '')
    def set_output(self, c, output_channel, on):
        """Turns the output of the provided output channel (1 indexed) to on, if on is True, 
        and to off, if on is False"""
        setting = ['/%s/sigouts/%d/on' % (self.dev_ID, output_channel-1), on],
        yield self.daq.set(setting)
        
    @setting(118,output_channel = 'i', amp = 'v[]', returns = '')
    def set_output_amplitude(self, c, output_channel, amp):
        """Sets the output amplitude of the provided output channel (1 indexed) to the provided input amplitude
        in units of the output range."""
        if output_channel == 1:
            setting = ['/%s/sigouts/%d/amplitudes/6' % (self.dev_ID, output_channel-1), amp],
        elif output_channel == 2:
            setting = ['/%s/sigouts/%d/amplitudes/7' % (self.dev_ID, output_channel-1), amp],
        yield self.daq.set(setting)
        
    @setting(119,output_channel = 'i', range = 'v[]', returns = '')
    def set_output_range(self, c, output_channel, range):
        """Sets the output range of the provided output channel (1 indexed) to the provided input amplitude
        in units of volts. Will automatically go to the value just above the desired provided range. Sets to
        10 mV, 100 mV, 1 V or 10V."""
        setting = ['/%s/sigouts/%d/range' % (self.dev_ID, output_channel-1), range],
        yield self.daq.set(setting)
        
    @setting(120,output_channel = 'i', returns = 'v[]')
    def get_output_range(self, c, output_channel):
        """Gets the output amplitude of the provided output channel (1 indexed) to the provided input amplitude
        in units of the output range."""
        setting = '/%s/sigouts/%d/range' % (self.dev_ID, output_channel-1)
        dic = yield self.daq.get(setting,True)
        range = float(dic[setting])
        returnValue(range)
        
    @setting(121,start = 'v[]', stop = 'v[]', samplecount  = 'i', sweep_param = 's', demod = 'i', log = 'b', bandwidthcontrol = 'i', bandwidth = 'v[]', bandwidthoverlap = 'b', loopcount = 'i', settle_time = 'v[]', settle_inaccuracy = 'v[]', averaging_tc = 'v[]', averaging_sample = 'v[]', returns = 'b')
    def create_sweep_object(self,c,start,stop, samplecount, sweep_param, demod = 1, log = False, bandwidthcontrol = 2, bandwidth = 1000, bandwidthoverlap = False, loopcount = 1, settle_time = 0, settle_inaccuracy = 0.001, averaging_tc = 5, averaging_sample = 5):
        """Sweeps the provided sweep parameter from the provided start value to the provided stop value with 
        the desired number of points. The sweep records all data at each point in the sweep. The sweeper will
        not turn on any outputs or configure anything else. It only sweeps the parameter and records data.
        Available sweep_param inputs are (spaces included): \r\n
        oscillator 1 \r\n
        oscillator 2 \r\n
        output 1 amplitude \r\n
        output 2 amplitude \r\n
        output 1 offset \r\n
        output 2 offset \r\n
        Returns the 4 by samplecount array with the first column corresponding to grid of the swept parameter, 
        the second corresponds to the demodulator R, the third to the phase, and the fourth to the frequency.
        Loop count greater than 1 not yet implemented. """
        
        #Initialize the sweeper object and specify the device
        if self.sweeper is None:
            self.sweeper  = yield self.daq.sweep()
            yield self.sweeper.set('sweep/device', self.dev_ID)
            
        self.sweeper_path = '/%s/demods/%d/sample' % (self.dev_ID, demod - 1)
        #Set the parameter to be swept
        sweep_param_set = False
        if sweep_param == "oscillator 1":
            yield self.sweeper.set('sweep/gridnode', 'oscs/0/freq')
            sweep_param_set = True
        elif sweep_param == "oscillator 2":
            yield self.sweeper.set('sweep/gridnode', 'oscs/1/freq')
            sweep_param_set = True
        elif sweep_param == "output 1 amplitude":
            yield self.sweeper.set('sweep/gridnode', 'sigouts/0/amplitudes/6')
            sweep_param_set = True
        elif sweep_param == "output 2 amplitude":
            yield self.sweeper.set('sweep/gridnode', 'sigouts/1/amplitudes/7')
            sweep_param_set = True
        elif sweep_param == "output 1 offset":
            yield self.sweeper.set('sweep/gridnode', 'sigouts/0/offset')
            sweep_param_set = True
        elif sweep_param == "output 2 offset":
            yield self.sweeper.set('sweep/gridnode', 'sigouts/1/offset')
            sweep_param_set = True

        if sweep_param_set == True:
            #Set the start and stop points
            if start <= stop:
                yield self.sweeper.set('sweep/start', start)
                yield self.sweeper.set('sweep/stop', stop)
                yield self.sweeper.set('sweep/scan', 0)
            else:
                yield self.sweeper.set('sweep/start', stop)
                yield self.sweeper.set('sweep/stop', start)
                yield self.sweeper.set('sweep/scan', 3)
                
            yield self.sweeper.set('sweep/samplecount', samplecount)
            
            #Specify linear or logarithmic grid spacing. Off by default
            yield self.sweeper.set('sweep/xmapping', log)
            # Automatically control the demodulator bandwidth/time constants used.
            # 0=manual, 1=fixed, 2=auto
            # Note: to use manual and fixed, sweep/bandwidth has to be set to a value > 0.
            yield self.sweeper.set('sweep/bandwidthcontrol', bandwidthcontrol)
            if bandwidthcontrol == 0 or bandwidthcontrol == 1:
                yield self.sweeper.set('sweep/bandwidth',bandwidth)
            # Sets the bandwidth overlap mode (default 0). If enabled, the bandwidth of
            # a sweep point may overlap with the frequency of neighboring sweep
            # points. The effective bandwidth is only limited by the maximal bandwidth
            # setting and omega suppression. As a result, the bandwidth is independent
            # of the number of sweep points. For frequency response analysis bandwidth
            # overlap should be enabled to achieve maximal sweep speed (default: 0). 0 =
            # Disable, 1 = Enable.
            yield self.sweeper.set('sweep/bandwidthoverlap', bandwidthoverlap)
            
            # Specify the number of sweeps to perform back-to-back.
            yield self.sweeper.set('sweep/loopcount', loopcount)
            
            #Specify the settling time between data points. 
            yield self.sweeper.set('sweep/settling/time', settle_time)
            
            # The sweep/settling/inaccuracy' parameter defines the settling time the
            # sweeper should wait before changing a sweep parameter and recording the next
            # sweep data point. The settling time is calculated from the specified
            # proportion of a step response function that should remain. The value
            # provided here, 0.001, is appropriate for fast and reasonably accurate
            # amplitude measurements. For precise noise measurements it should be set to
            # ~100n.
            # Note: The actual time the sweeper waits before recording data is the maximum
            # time specified by sweep/settling/time and defined by
            # sweep/settling/inaccuracy.
            yield self.sweeper.set('sweep/settling/inaccuracy', settle_inaccuracy)
            
            # Set the minimum time to record and average data. By default set to 10 demodulator
            # filter time constants.
            yield self.sweeper.set('sweep/averaging/tc', averaging_tc)
            
            # Minimal number of samples that we want to record and average. Note,
            # the number of samples used for averaging will be the maximum number of
            # samples specified by either sweep/averaging/tc or sweep/averaging/sample.
            # By default this is set to 5.
            yield self.sweeper.set('sweep/averaging/sample', averaging_sample)
            
            
            #Subscribe to path defined previously
            yield self.sweeper.subscribe(self.sweeper_path)

            returnValue(True)
        else: 
            print 'Desired sweep parameter does not exist'
            returnValue(False)

    @setting(122, returns = 'b')
    def start_sweep(self,c):
        success = False
        if self.sweeper is not None:
            yield self.sweeper.execute()
            success = True
        returnValue(success)
        
    @setting(123, returns = '**v[]')
    def read_latest_values(self,c):  
        return_flat_dict = True
        data = yield self.sweeper.read(return_flat_dict)
        demod_data = data[self.sweeper_path]
        #print demod_data

        grid = demod_data[0][0]['grid']
        R = np.abs(demod_data[0][0]['x'] + 1j*demod_data[0][0]['y'])
        phi = np.angle(demod_data[0][0]['x'] + 1j*demod_data[0][0]['y'], True)
        frequency  = demod_data[0][0]['frequency']
        
        formatted_data = [[],[],[],[]]
        length = len(grid)
        for i in range(0,length):
            try:
                formatted_data[0].append(float(grid[i]))
                formatted_data[1].append(float(frequency[i]))
                formatted_data[2].append(float(R[i]))
                formatted_data[3].append(float(phi[i]))
            except:
                pass

        returnValue(formatted_data)
        
    @setting(124,returns = 'b')
    def sweep_complete(self,c):
        '''Checks to see if there's a sweep was completed. Returns True if the sweeper is not
        currently sweeping. Returns False if the sweeper is mid sweep.'''
        if self.sweeper is not None:
            done = yield self.sweeper.finished()
        else:
            done = True
        returnValue(done)
        
    @setting(125,returns = 'v[]')
    def sweep_time_remaining(self,c):
        if self.sweeper is not None:
            time = yield self.sweeper.get('sweep/remainingtime')
            time = time['remainingtime'][0]
        else:
            time = float('nan')
        returnValue(time)
    
    @setting(126, returns = 'b')
    def stop_sweep(self,c):
        success = False
        if self.sweeper is not None:
            yield self.sweeper.finish()
            success = True
        returnValue(success)
        
    @setting(127,returns = '')
    def clear_sweep(self,c):
        try:
            # Stop the sweeper thread and clear the memory.
            self.sweeper.unsubscribe(path)
            self.sweeper.clear()
        except: 
            pass

    @setting(128, PLL_index = 'i', targetBW = 'v[]', pidMode = 'i', harmonic = 'i', filter_order = 'i', returns = '*v[]')
    def advise_PLL_PID(self, c, PLL_index, targetBW, pidMode, harmonic, filter_order):
        yield self.pidAdvisor.set('pidAdvisor/type', 'pll')

        if pidMode == 0:
            #P mode
            yield self.pidAdvisor.set('pidAdvisor/pid/mode',1)
        elif pidMode == 1:
            #I mode
            yield self.pidAdvisor.set('pidAdvisor/pid/mode',2)
        elif pidMode == 2:
            #PI mode
            yield self.pidAdvisor.set('pidAdvisor/pid/mode',3)
        elif pidMode == 3:
            #PID mode
            yield self.pidAdvisor.set('pidAdvisor/pid/mode',7)
        
        yield self.pidAdvisor.set('pidAdvisor/pid/targetbw', targetBW)

        # PID index to use (first PID of device: 0)
        yield self.pidAdvisor.set('pidAdvisor/index', PLL_index-1)
        
        yield self.pidAdvisor.set('pidAdvisor/demod/harmonic', harmonic)
        yield self.pidAdvisor.set('pidAdvisor/demod/order', filter_order)

        #Reset everything to 0 prior to calculation
        yield self.pidAdvisor.set('pidAdvisor/pid/p', 0)
        yield self.pidAdvisor.set('pidAdvisor/pid/i', 0)
        yield self.pidAdvisor.set('pidAdvisor/pid/d', 0)
        yield self.pidAdvisor.set('pidAdvisor/calculate', 0)

        # Start the module thread
        yield self.pidAdvisor.execute()
        yield self.sleep(2.0)
        # Advise
        yield self.pidAdvisor.set('pidAdvisor/calculate', 1)
        print('Starting advising. Optimization process may run up to a minute...')
        reply = yield self.pidAdvisor.get('pidAdvisor/calculate')

        t_start = time.time()
        t_timeout = t_start + 60
        while reply['calculate'][0] == 1:
            reply = yield self.pidAdvisor.get('pidAdvisor/calculate')
            if time.time() > t_timeout:
                yield self.pidAdvisor.finish()
                raise Exception("PID advising failed due to timeout.")

        print("Advice took {:0.1f} s.".format(time.time() - t_start))

        # Get all calculated parameters.
        result = yield self.pidAdvisor.get('pidAdvisor/*')
        # Check that the dictionary returned by poll contains the data that are needed.
        assert result, "pidAdvisor returned an empty data dictionary?"
        assert 'pid' in result, "data dictionary has no key 'pid'"
        assert 'step' in result, "data dictionary has no key 'step'"
        assert 'bode' in result, "data dictionary has no key 'bode'"

        if result is not None:
            print result['pid']
            # Now copy the values from the PID Advisor to the PID and enable the PID.
            p_adv = result['pid']['p'][0]
            i_adv = result['pid']['i'][0]
            d_adv = result['pid']['d'][0]
            dlimittimeconstant_adv = result['pid']['dlimittimeconstant'][0]
            rate_adv = result['pid']['rate'][0]
            bw_adv = result['bw'][0]

            returnValue([p_adv, i_adv, d_adv, dlimittimeconstant_adv, rate_adv, bw_adv])
        else:
            returnValue([0, 0, 0, 0, 0, 0])

    #@setting(1280,returns = '')
    #def get_simulated_pm(self, c)
            
    @setting(129,PLL = 'i', freq = 'v[]', returns = '')
    def set_PLL_freqcenter(self, c, PLL, freq):
        """Sets the center frequency of the specified PLL (either 1 or 2)"""
        setting = ['/%s/plls/%d/freqcenter' % (self.dev_ID, PLL-1), freq],
        yield self.daq.set(setting)

    @setting(130, PLL = 'i', returns = 'v[]')
    def get_PLL_freqcenter(self, c, PLL):
        """Gets the PLL center frequency of the specified PLL (either 1 or 2)."""
        setting = '/%s/plls/%d/freqcenter' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        freq = float(dic[setting])
        returnValue(freq)

    @setting(131,PLL = 'i', freq = 'v[]', returns = '')
    def set_PLL_freqrange(self, c, PLL, freq):
        """Sets the frequency range of the specified PLL (either 1 or 2)"""
        setting = ['/%s/plls/%d/freqrange' % (self.dev_ID, PLL-1), freq],
        yield self.daq.set(setting)

    @setting(132, PLL = 'i', returns = 'v[]')
    def get_PLL_freqrange(self, c, PLL):
        """Gets the PLL frequency range of the specified PLL (either 1 or 2)."""
        setting = '/%s/plls/%d/freqrange' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        freq = float(dic[setting])
        returnValue(freq)

    @setting(133,PLL = 'i', harm = 'i', returns = '')
    def set_PLL_harmonic(self, c, PLL, harm):
        """Sets the phase detector harmonic (1 or 2) of the specified PLL (either 1 or 2)"""
        setting = ['/%s/plls/%d/harmonic' % (self.dev_ID, PLL-1), harm],
        yield self.daq.set(setting)

    @setting(134, PLL = 'i', returns = 'i')
    def get_PLL_harmonic(self, c, PLL):
        """Gets the phase detector harmonic of the specified PLL (either 1 or 2)."""
        setting = '/%s/plls/%d/harmonic' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        harm = int(dic[setting])
        returnValue(harm)

    @setting(135,PLL = 'i', tc = 'v[]', returns = '')
    def set_PLL_TC(self, c, PLL, tc):
        """Sets the time constant of the specified PLL (either 1 or 2)"""
        setting = ['/%s/plls/%d/timeconstant' % (self.dev_ID, PLL-1), tc],
        yield self.daq.set(setting)

    @setting(136, PLL = 'i', returns = 'v[]')
    def get_PLL_TC(self, c, PLL):
        """Gets the PLL center frequency of the specified PLL (either 1 or 2)."""
        setting = '/%s/plls/%d/timeconstant' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        tc = float(dic[setting])
        returnValue(tc)

    @setting(137,PLL = 'i', order = 'i', returns = '')
    def set_PLL_filterorder(self, c, PLL, order):
        """Sets the filter order (1 through 8) of the specified PLL (either 1 or 2)"""
        setting = ['/%s/plls/%d/order' % (self.dev_ID, PLL-1), order],
        yield self.daq.set(setting)

    @setting(138, PLL = 'i', returns = 'i')
    def get_PLL_filterorder(self, c, PLL):
        """Gets the filter order of the specified PLL (either 1 or 2)."""
        setting = '/%s/plls/%d/order' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        order = int(dic[setting])
        returnValue(order)

    @setting(139,PLL = 'i', setpoint = 'v[]', returns = '')
    def set_PLL_setpoint(self, c, PLL, setpoint):
        """Sets the phase setpoint in degrees of the specified PLL (either 1 or 2)"""
        setting = ['/%s/plls/%d/setpoint' % (self.dev_ID, PLL-1), setpoint],
        yield self.daq.set(setting)

    @setting(140, PLL = 'i', returns = 'v[]')
    def get_PLL_setpoint(self, c, PLL):
        """Gets the phase setpoint of the specified PLL (either 1 or 2)."""
        setting = '/%s/plls/%d/setpoint' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        setpoint = float(dic[setting])
        returnValue(setpoint)
        
    @setting(141,PLL = 'i', P = 'v[]', returns = '')
    def set_PLL_P(self, c, PLL, P):
        """Sets the proportional term of the specified PLL (either 1 or 2) PID loop"""
        setting = ['/%s/plls/%d/p' % (self.dev_ID, PLL-1), P],
        yield self.daq.set(setting)

    @setting(142, PLL = 'i', returns = 'v[]')
    def get_PLL_P(self, c, PLL):
        """Gets the proportional term of the specified PLL (either 1 or 2) PID loop"""
        setting = '/%s/plls/%d/p' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        P = float(dic[setting])
        returnValue(P)
        
    @setting(143,PLL = 'i', I = 'v[]', returns = '')
    def set_PLL_I(self, c, PLL, I):
        """Sets the intergral term of the specified PLL (either 1 or 2) PID loop"""
        setting = ['/%s/plls/%d/i' % (self.dev_ID, PLL-1), I],
        yield self.daq.set(setting)

    @setting(144, PLL = 'i', returns = 'v[]')
    def get_PLL_I(self, c, PLL):
        """Gets the integral term of the specified PLL (either 1 or 2) PID loop"""
        setting = '/%s/plls/%d/i' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        I = float(dic[setting])
        returnValue(I)

    @setting(145,PLL = 'i', D = 'v[]', returns = '')
    def set_PLL_D(self, c, PLL, D):
        """Sets the derivative term of the specified PLL (either 1 or 2) PID loop"""
        setting = ['/%s/plls/%d/d' % (self.dev_ID, PLL-1), D],
        yield self.daq.set(setting)

    @setting(146, PLL = 'i', returns = 'v[]')
    def get_PLL_D(self, c, PLL):
        """Gets the derivative term of the specified PLL (either 1 or 2) PID loop"""
        setting = '/%s/plls/%d/d' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        I = float(dic[setting])
        returnValue(I)

    @setting(147,PLL = 'i', returns = '')
    def set_PLL_on(self, c, PLL):
        """Enables the PLL"""
        setting = ['/%s/plls/%d/enable' % (self.dev_ID, PLL-1), 1],
        yield self.daq.set(setting)

    @setting(148,PLL = 'i', returns = '')
    def set_PLL_off(self, c, PLL):
        """Turns off the PLL"""
        setting = ['/%s/plls/%d/enable' % (self.dev_ID, PLL-1), 0],
        yield self.daq.set(setting)

    @setting(149,PLL = 'i', sigin = 'i', returns = '')
    def set_PLL_input(self, c, PLL, sigin):
        """Sets the PLL input signal (1/2 correspond to sig in 1/2, 3/4 correspond to Aux In 1/2, and 5/6 correspond to
            DIO D0/D1"""
        setting = ['/%s/plls/%d/adcselect' % (self.dev_ID, PLL-1), sigin-1],
        yield self.daq.set(setting)

    @setting(150, PLL = 'i', returns = 'v[]')
    def get_PLL_input(self, c, PLL):
        """Gets the PID input signal channel"""
        setting = '/%s/plls/%d/adcselect' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        sigin = int(dic[setting])
        returnValue(sigin+1)
        
    @setting(151,PLL = 'i', rate = 'v[]', returns = '')
    def set_PLL_rate(self, c, PLL, rate):
        """Sets the PLL PID sampling rate"""
        setting = ['/%s/plls/%d/rate' % (self.dev_ID, PLL-1), rate],
        yield self.daq.set(setting)
        
    @setting(152, PLL = 'i', returns = 'v[]')
    def get_PLL_rate(self, c, PLL):
        """Gets the PLL PID sampling rate"""
        setting = '/%s/plls/%d/rate' % (self.dev_ID, PLL-1)
        dic = yield self.daq.get(setting,True)
        rate = float(dic[setting])
        returnValue(rate)
        
    @setting(153, PLL = 'i', returns = 'v[]')
    def get_PLL_PM(self, c, PLL):
        """Gets the PLL PID phase marging"""
        setting = '/pidAdvisor/pm' 
        dic = yield self.pidAdvisor.get(setting,True)
        PM = float(dic[setting])
        returnValue(PM)
        
    @setting(154,PLL_index = 'i', rec_time= 'v[]', timeout = 'i', returns = '**v[]')
    def poll_PLL(self,c, PLL_index, rec_time, timeout):
        """This function returns subscribed data previously in the API's buffers or
            obtained during the specified time. It returns a dict tree containing
            the recorded data. This function blocks until the recording time is
            elapsed. Recording time input is in seconds. Timeout time input is in 
            milliseconds. Recommended timeout value is 500ms."""

        path = '/%s/plls/%d/*' % (self.dev_ID, PLL_index-1)
        path_freqdelta = '/%s/plls/%d/freqdelta' % (self.dev_ID, PLL_index-1)
        path_error = '/%s/plls/%d/error' % (self.dev_ID, PLL_index-1)

        yield self.daq.flush()
        yield self.daq.subscribe(path)

        ans = yield self.daq.poll(rec_time, timeout, 1, True)

        #print ans[path_freqdelta]
        #print ans[path_error]

        yield self.daq.unsubscribe(path)
        
        returnValue([ans[path_freqdelta],ans[path_error]])
   
    @setting(155, returns = 's')
    def version(self,c):
		"""Returns the version of the software installed on this computer"""
		ver = yield self.daq.version()
		returnValue(ver)

    def sleep(self,secs):
        """Asynchronous compatible sleep command. Sleeps for given time in seconds, but allows
        other operations to be done elsewhere while paused."""
        d = defer.Deferred()
        reactor.callLater(secs,d.callback,'Sleeping')
        return d

__server__ = HF2LIServer()
  
if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)