# Copyright (C) 2011 Peter O'Malley/Charles Neill
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
name = sr1
version = 2.7
description =
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from math import log10, log2
from labrad import types as T, gpib, units
from labrad.server import setting
from labrad.gpib import GPIBManagedServer, GPIBDeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue
import numpy as np

class sr1Wrapper(GPIBDeviceWrapper):
    @inlineCallbacks
    def inputMode(self):
        mode = yield self.query('ISRC?')
        returnValue(int(mode))

    @inlineCallbacks
    def set_setting(self, sett):
        yield self.write(sett)

    @inlineCallbacks
    def get_setting(self, sett):
        resp = yield self.query(sett)
        returnValue(resp)
    
    @inlineCallbacks
    def analyzer_function(self, analyzer, funcInd = None):
        if funcInd is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):Function?')
            returnValue(int(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):Function ' + str(funcInd))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):Function?')
            returnValue(int(resp))
    
    @inlineCallbacks
    def converter(self, analyzer, convInd = None):
        if convInd is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):SampleRate?')
            returnValue(int(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):SampleRate ' + str(convInd))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):SampleRate?')
            returnValue(int(resp))
    
    @inlineCallbacks
    def fs(self, analyzer):
        resp = yield self.query(':Alyzr(' + str(analyzer) + '):SampleRateRdg?')
        returnValue(float(resp))
    
    @inlineCallbacks
    def source(self, analyzer, srcInd = None):
        if srcInd is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):Source?')
            returnValue(int(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):Source ' + str(srcInd))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):Source?')
            returnValue(int(resp))
    
    @inlineCallbacks
    def resolution(self, analyzer, resInd = None):
        if resInd is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:Lines?')
            returnValue(int(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:Lines ' + str(resInd))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:Lines?')
            returnValue(int(resp))
    
    @inlineCallbacks
    def show_aliased_lines(self, analyzer, val = None):
        if val is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:ShowAllLines?')
            returnValue(bool(int(resp)))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:ShowAllLines ' + str(val))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:ShowAllLines?')
            returnValue(bool(int(resp)))
    
    @inlineCallbacks
    def bandwidth(self, analyzer, bwInd = None):
        if bwInd is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:Span?')
            returnValue(int(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:Span ' + str(bwInd))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:Span?')
            returnValue(int(resp))
    
    @inlineCallbacks
    def start_frequency(self, analyzer, freq = None):
        if freq is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:StartFreq?')
            returnValue(float(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:StartFreq ' + str(freq))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:StartFreq?')
            returnValue(float(resp))
    
    @inlineCallbacks
    def center_frequency(self, analyzer, freq = None):
        if freq is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:CenterFreq?')
            returnValue(float(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:CenterFreq ' + str(freq))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:CenterFreq?')
            returnValue(float(resp))
    
    @inlineCallbacks
    def end_frequency(self, analyzer, freq = None):
        if freq is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:StopFreq?')
            returnValue(float(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:StopFreq ' + str(freq))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:StopFreq?')
            returnValue(float(resp))
    
    @inlineCallbacks
    def acq_time(self, analyzer):
        resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:TimeRecordDuration?')
        returnValue(float(resp))
    
    @inlineCallbacks
    def averaging_mode(self, analyzer, mdInd = None):
        if mdInd is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:Averaging?')
            returnValue(int(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:Averaging ' + str(mdInd))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:Averaging?')
            returnValue(int(resp))
    
    @inlineCallbacks
    def num_avgs(self, analyzer, num = None):
        if num is None:
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:NumAverages?')
            returnValue(int(resp))
        else:
            yield self.write(':Alyzr(' + str(analyzer) + '):FFT:NumAverages ' + str(num))
            resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:NumAverages?')
            returnValue(int(resp))
    
    @inlineCallbacks
    def avg_done(self, analyzer):
        resp = yield self.query(':Alyzr(' + str(analyzer) + '):FFT:AvgDone?')
        returnValue(bool(int(resp)))
    
    @inlineCallbacks
    def clear_avg(self, analyzer):
        yield self.write(':Alyzr(' + str(analyzer) + '):FFT:ResetAvg')
    
    @inlineCallbacks
    def get_fft_power_spec(self, analyzer, unit):
        data = yield self.query(':Instrument:LastVectorMeas? ' + str(analyzer+1) + '111, "' + unit + '"') #1111/2111 corresponds to msA0/A1FFTspectrum
        returnValue(str(data)) #There might be an issue with the amount of data returned, namely it maybe can return more but default byetes may be prematurely truncating it, idk if thats a problem with the way labrad does it tho
    
    @inlineCallbacks
    def get_fft_freq(self, analyzer):
        data = yield self.query(':Instrument:LastVectorXMeas? ' + str(analyzer+1) + '111, "Hz"') #1111/2111 corresponds to msA0/A1FFTspectrum
        returnValue(str(data)) #There might be an issue with the amount of data returned, namely it maybe can return more but default byetes may be prematurely truncating it, idk if thats a problem with the way labrad does it tho

class sr1Server(GPIBManagedServer): 
    name = 'sr1'
    deviceName = 'Stanford_Research_Systems SR1'
    deviceIdentFunc = 'identify_device' 
    deviceWrapper = sr1Wrapper

    @setting(9988, server='s', address='s')
    def identify_device(self, c, server, address):
        print('identifying:', server, address)
        try:
            s = self.client[server]
            p = s.packet()
            p.address(address)
            p.write_termination('\r')
            p.read_termination('\r')
            p.write('*IDN?')
            p.read()
            p.write('*IDN?')
            p.read()
            ans = yield p.send()
            resp = ans.read[1].strip()
            print('got ident response:', resp)
            if resp:
                returnValue(resp)
            else:
                returnValue("Device not identified")
        except Exception as e:
            print('failed:', e)
            print('what what...')
            raise

    @setting(90, sett='s', returns='')
    def set_setting(self, c, sett):
        dev = self.selectedDevice(c)
        yield dev.set_setting(sett)

    @setting(91, sett='s', returns='s')
    def get_setting(self, c, sett):
        dev = self.selectedDevice(c)
        resp = yield dev.get_setting(sett)
        returnValue(resp)

    @setting(96, analyzer='i', returns='s')
    def set_to_fft1(self, c, analyzer):
        """
        Sets the given analyzer to FFT1. This is needed before querying spectrum.
        """
        dev = self.selectedDevice(c)
        resp = yield dev.analyzer_function(analyzer, 1)
        if resp == 1:
            returnValue('Analyzer A' + str(analyzer) + ' set to FFT1.')
        else:
            returnValue('Failed!')
    
    @setting(99, analyzer='i', conv='s', returns='s')
    def converter(self, c, analyzer, conv = None):
        """
        Sets/gets the converter/sample rate: "Hi BW" or "Hi Res" (case insensitive).
        """
        dev = self.selectedDevice(c)
        Converters = {'Hi BW'.lower():0, 'Hi Res'.lower():1}
        rev_Converters = {0:'Hi BW', 1:'Hi Res'}
        if conv is None:
            resp = yield dev.converter(analyzer)
            returnValue(rev_Converters[resp])
        else:
            resp = yield dev.converter(analyzer, Converters.get(conv.lower(), 0))
            returnValue(rev_Converters[resp])
    
    @setting(98, analyzer='i', returns='v')
    def fs(self, c, analyzer):
        """
        Gets the effective sample rate (Fs) in Hz.
        """
        dev = self.selectedDevice(c)
        resp = yield dev.fs(analyzer)
        returnValue(resp)
    
    @setting(97, analyzer='i', src='s', returns='s')
    def source(self, c, analyzer, src = None):
        """
        Sets/gets the source: "Analog A" or "Analog B" (case insensitive).
        """
        dev = self.selectedDevice(c)
        Sources = {'Analog A'.lower():2, 'Analog B'.lower():3}
        rev_Sources = {2:'Analog A', 3:'Analog B'}
        if src is None:
            resp = yield dev.source(analyzer)
            returnValue(rev_Sources[resp])
        else:
            resp = yield dev.source(analyzer, Sources.get(src.lower(), 0))
            returnValue(rev_Sources[resp])
    
    @setting(101, analyzer='i', res='i', returns='i')
    def resolution(self, c, analyzer, res = None):
        """
        Sets/gets the resolution: 32k, 16k, 8k, 4k, 2k, 1k, 512, 256. Will default to the nearest if input integer is non-standard.
        """
        dev = self.selectedDevice(c)
        if res is None:
            resp = yield dev.resolution(analyzer)
            returnValue(256*2**(7-resp))
        else:
            resInd = 7-int(round(log2(res/256)))
            if resInd > 7:
                resInd = 7
            if resInd < 0:
                resInd = 0
            resp = yield dev.resolution(analyzer, resInd)
            returnValue(256*2**(7-resp))
    
    @setting(102, analyzer='i', val='b', returns='b')
    def show_aliased_lines(self, c, analyzer, val = None):
        """
        Sets/gets the state of the "Show Aliased Lines" checkbox. Takes boolean (True/False) as input.
        """
        dev = self.selectedDevice(c)
        if val is None:
            resp = yield dev.show_aliased_lines(analyzer)
            returnValue(resp)
        else:
            resp = yield dev.show_aliased_lines(analyzer, bool(val))
            returnValue(resp)
    
    @setting(103, analyzer='i', bw='s', returns='s')
    def bandwidth_fs(self, c, analyzer, bw = None):
        """
        Sets/gets the bandwidth (frequency span): Fs/2 all the way to Fs/1024 (case insensitive).
        """
        dev = self.selectedDevice(c)
        Spans = {}
        for i in range(10):
            Spans.update({'fs/' + str(2**(i+1)): i})
        if bw is None:
            resp = yield dev.bandwidth(analyzer)
            returnValue('Fs/' + str(2**(resp+1)))
        else:
            resp = yield dev.bandwidth(analyzer, Spans.get(bw.lower(), 0))
            returnValue('Fs/' + str(2**(resp+1)))
    
    @setting(104, analyzer='i', freq='v', returns='v')
    def start_frequency(self, c, analyzer, freq = None):
        """
        Sets/gets the lowest frequency (in Hz).
        """
        dev = self.selectedDevice(c)
        if freq is None:
            resp = yield dev.start_frequency(analyzer)
            returnValue(resp)
        else:
            resp = yield dev.start_frequency(analyzer, freq)
            returnValue(resp)
    
    @setting(105, analyzer='i', freq='v', returns='v')
    def center_frequency(self, c, analyzer, freq = None):
        """
        Sets/gets the midpoint of frequency span (in Hz).
        """
        dev = self.selectedDevice(c)
        if freq is None:
            resp = yield dev.center_frequency(analyzer)
            returnValue(resp)
        else:
            resp = yield dev.center_frequency(analyzer, freq)
            returnValue(resp)
    
    @setting(106, analyzer='i', freq='v', returns='v')
    def end_frequency(self, c, analyzer, freq = None):
        """
        Sets/gets the highest frequency (in Hz).
        """
        dev = self.selectedDevice(c)
        if freq is None:
            resp = yield dev.end_frequency(analyzer)
            returnValue(resp)
        else:
            resp = yield dev.end_frequency(analyzer, freq)
            returnValue(resp)
    
    @setting(107, analyzer='i', bwHz='v', returns='v')
    def bandwidth_Hz(self, c, analyzer, bwHz = None):
        """
        Sets/gets the actual bandwidth in Hz. Will default to the nearest for non-standard input.
        """
        dev = self.selectedDevice(c)
        f0 = yield dev.start_frequency(analyzer)
        f1 = yield dev.end_frequency(analyzer)
        if (bwHz is None) or (bwHz == f1 - f0):
            returnValue(f1 - f0)
        else:
            resp = yield dev.bandwidth(analyzer)
            rt = bwHz/(f1 - f0)
            rt2 = rt
            if rt > 1: # actual bandwidth too low, increase it gradually until roughly matching set value
                while (resp > 0) and (rt2 > 1):
                    rt = rt2
                    resp = yield dev.bandwidth(analyzer, resp-1)
                    f0 = yield dev.start_frequency(analyzer)
                    f1 = yield dev.end_frequency(analyzer)
                    rt2 = bwHz/(f1 - f0)
                if rt*rt2 > 1:
                    returnValue(f1 - f0)
                else:
                    resp = yield dev.bandwidth(analyzer, resp+1)
                    f0 = yield dev.start_frequency(analyzer)
                    f1 = yield dev.end_frequency(analyzer)
                    returnValue(f1 - f0)
            else: # actual bandwidth too high, decrease it gradually until roughly matching set value
                while (resp < 9) and (rt2 < 1):
                    rt = rt2
                    resp = yield dev.bandwidth(analyzer, resp+1)
                    f0 = yield dev.start_frequency(analyzer)
                    f1 = yield dev.end_frequency(analyzer)
                    rt2 = bwHz/(f1 - f0)
                if rt*rt2 < 1:
                    returnValue(f1 - f0)
                else:
                    resp = yield dev.bandwidth(analyzer, resp-1)
                    f0 = yield dev.start_frequency(analyzer)
                    f1 = yield dev.end_frequency(analyzer)
                    returnValue(f1 - f0)
    
    @setting(108, analyzer='i', returns='v')
    def acq_time(self, c, analyzer):
        """
        Gets the acquistion time (in seconds).
        """
        dev = self.selectedDevice(c)
        resp = yield dev.acq_time(analyzer)
        returnValue(resp)
    
    @setting(109, analyzer='i', md='s', returns='s')
    def averaging_mode(self, c, analyzer, md = None):
        """
        Sets/gets the averaging mode: "None", "Fixed Length", or "Continuous" (case insensitive).
        """
        dev = self.selectedDevice(c)
        Modes = {'None'.lower():0, 'Fixed Length'.lower():1, 'Continuous'.lower():2}
        rev_Modes = {0:'None', 1:'Fixed Length', 2:'Continuous'}
        if md is None:
            resp = yield dev.averaging_mode(analyzer)
            returnValue(rev_Modes[resp])
        else:
            resp = yield dev.averaging_mode(analyzer, Modes.get(md.lower(), 0))
            returnValue(rev_Modes[resp])
    
    @setting(110, analyzer='i', num='i', returns='i')
    def num_avgs(self, c, analyzer, num = None):
        """
        Sets/gets the number of averages.
        """
        dev = self.selectedDevice(c)
        if num is None:
            resp = yield dev.num_avgs(analyzer)
            returnValue(resp)
        else:
            resp = yield dev.num_avgs(analyzer, num)
            returnValue(resp)
    
    @setting(111, analyzer='i', returns='b')
    def avg_done(self, c, analyzer):
        """
        Queries if averaging is done.
        """
        dev = self.selectedDevice(c)
        resp = yield dev.avg_done(analyzer)
        returnValue(resp)
    
    @setting(112, analyzer='i')
    def clear_avg(self, c, analyzer):
        """
        Clears the average buffer.
        """
        dev = self.selectedDevice(c)
        yield dev.clear_avg(analyzer)
    
    @setting(191, analyzer='i', unit='s', returns='s')
    def get_fft_power_spec_str(self, c, analyzer, unit='V/rtHz'):
        """
        Gets the FFT power spectrum as an unformatted string. Default unit is 'V/rtHz'.
        """
        dev = self.selectedDevice(c)
        data = yield dev.get_fft_power_spec(analyzer, unit)
        returnValue(data.strip('"'))
    
    @setting(192, analyzer='i', returns='s')
    def get_fft_freq_str(self, c, analyzer):
        """
        Gets the FFT frequency points as an unformatted string.
        """
        dev = self.selectedDevice(c)
        data = yield dev.get_fft_freq(analyzer)
        returnValue(data.strip('"'))
        
    @setting(193, analyzer='i', unit='s', returns='*v')
    def get_fft_power_spec_list(self, c, analyzer, unit='V/rtHz'):
        """
        Gets the FFT power spectrum as a list. Default unit is 'V/rtHz'.
        """
        data = yield self.get_fft_power_spec_str(c, analyzer, unit)
        data2 = [float(item) for item in data.split(',')]
        returnValue(data2)
    
    @setting(194, analyzer='i', returns='*v')
    def get_fft_freq_list(self, c, analyzer):
        """
        Gets the FFT frequencies as a list.
        """
        data = yield self.get_fft_freq_str(c, analyzer)
        data2 = [float(item) for item in data.split(',')]
        returnValue(data2)
    
    @setting(195, analyzer='i', unit='s', returns='**v')
    def get_fft_freq_power_spec(self, c, analyzer, unit='V/rtHz'):
        """
        Gets the FFT power spectrum (default unit is 'V/rtHz') vs frequency as a double list. Returns [[f1, f2, ...], [p1, p2, ...]].
        """
        xdata = yield self.get_fft_freq_list(c, analyzer)
        ydata = yield self.get_fft_power_spec_list(c, analyzer, unit)
        returnValue([xdata, ydata])

__server__ = sr1Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
