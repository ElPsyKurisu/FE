import numpy as np
import time
import os
from ekpy.control import core
from ekpy.control.instruments import keysight81150a, keysightdsox3024a
from scipy import interpolate
import scipy.integrate as it
import pandas as pd
from ekpy.control import plotting
import matplotlib.pyplot as plt
from datetime import timedelta

"""
This program is used to generate a dataset on a FE sample to then calculate Hysteresis. It works by sending in a series of triangle pulses
and then meauring the current and the voltage across the capacitor sample. Connect channel 1 of the wavegen to channel 1 of the scope, and connect
channel 2 of the wavegen in parallel with the sample which is in series with channel 2 of the scope. AKA connect channel 2 of the wavegen to port A via
BNC and connect channel 2 of the scope to port B also via BNC (no bannannas needed)
"""



def pv_hysteresis_wf(initial_delay, freq, pulse_delay, qtimepoints=12):
    '''
    Creates the waveform used to calculate the hysteresis of the sample, should create 2 sawtooth waveforms followed
    by 2 inverted ones. This code was taken from labview and alot of it is not needed but since it works we shall leave
    it as is for now. Despite the fact we never use q_time 

    Currently doesnt work if voltage is not 1, but it should always be 1
    '''
    #first build Qtime
    initial_delay = float(initial_delay)
    freq = float(freq)
    pulse_delay = float(pulse_delay)
    q_time = []
    t_increment = 0.0005/freq
    sumsofar = initial_delay
    q_time.append(sumsofar)
    count = 0
    for i in range(qtimepoints - 1):
        if count == 2:
            count = 0
            value = sumsofar + pulse_delay
        else:
            value = sumsofar + t_increment
            count += 1
        q_time.append(value)
        sumsofar = value
    #Now we build the time_array
    time_array = []
    time_array.append(0)
    time_array.append(initial_delay)
    t_increment2 = 0.00025/freq
    for i in range(4):
        sumsofar2 = 0
        last_element = time_array[-1]
        sumsofar2 = t_increment2 + last_element
        time_array.append(sumsofar2)
        sumsofar2 += t_increment
        time_array.append(sumsofar2)
        sumsofar2 += t_increment2
        time_array.append(sumsofar2)
        sumsofar2 += pulse_delay
        time_array.append(sumsofar2)
    
    #Now we calculate the Waveform frequency
    waveform_freq = 1/time_array[-1]
    #Now we calculate the interpolated time [This is a dumb method probably way easier way to do it]
    interp_time = []
    interp_time.append(0)
    iteration_count = 10000 - 1
    for i in range(iteration_count):
        interp_time.append((i + 1) * (time_array[-1]/iteration_count))
    #note this was the same shit as doing like np.linearinterpolate or linspace with max being the last element

    #Now we make a voltage array
    voltage_array = np.array([0,0,1,-1,0,0,1,-1,0,0,-1,1,0,0,-1,1,0,0])
    temp = interpolate.interp1d(time_array, voltage_array)
    interp_voltage_array = temp(interp_time)
    #only thing we use from this is interp_voltage_array wtf
    plt.plot(interp_time, interp_voltage_array)
    return q_time, time_array, waveform_freq, interp_time, interp_voltage_array

def setup_scope(scope, time_scale, voltage_channel, current_channel,
                voltage_scale, current_scale):
    keysightdsox3024a.initialize(scope)
    keysightdsox3024a.configure_timebase(scope, time_base_type='MAIN', reference='CENTer', scale=f'{time_scale}', position=f'{5*time_scale}')
    keysightdsox3024a.configure_channel(scope, channel=voltage_channel, vertical_scale=voltage_scale, impedance='FIFT')#set both to 50ohm
    keysightdsox3024a.configure_channel(scope, channel=current_channel, vertical_scale=voltage_scale, impedance='FIFT') #use ONEM if using the 50ohm feedthrough
    #NOTE changing the position now to 5* the timebase to hopefully get the full signal
    keysightdsox3024a.configure_trigger_characteristics(scope, trigger_source='EXT', low_voltage_level='0.75', high_voltage_level='0.95', sweep='NORM')
    keysightdsox3024a.configure_trigger_edge(scope, trigger_source='EXT', input_coupling='DC')

    
"""
def setup_wavegen(wavegen, voltage_channel, current_channel, interp_voltage_array, waveform_freq, voltage):
    keysight81150a.initialize(wavegen)
    keysight81150a.configure_impedance(wavegen, voltage_channel, source_impedance='50.0', load_impedance='50')
    keysight81150a.configure_impedance(wavegen, current_channel, source_impedance='50.0', load_impedance='50') #changed load from 1000000
    keysight81150a.configure_trigger(wavegen, voltage_channel, source='MAN')
    keysight81150a.configure_output_amplifier(wavegen, voltage_channel)
    keysight81150a.configure_output_amplifier(wavegen, current_channel)
    keysight81150a.create_arb_wf(wavegen, interp_voltage_array, 'PV')
    keysight81150a.configure_arb_wf(wavegen, voltage_channel, 'PV', gain=f'{voltage*2}', freq=f'{waveform_freq}') 
    keysight81150a.configure_arb_wf(wavegen, current_channel, 'PV', gain=f'{voltage*2}', freq=f'{waveform_freq}')
"""
def setup_wavegen(wavegen, voltage_channel, current_channel, interp_voltage_array, waveform_freq, voltage):
    """
    New version to take into account that you can couple channels 1 and 2 making things simpler,
    note still need to configure arb wf for channel 2 otherwise it goes to exp rise,
    had to remove configure output amplifier cuz you cant sync them
    """
    keysight81150a.initialize(wavegen)
    keysight81150a.couple_channels(wavegen)
    keysight81150a.configure_impedance(wavegen, voltage_channel, source_impedance='50.0', load_impedance='50')
    keysight81150a.configure_trigger(wavegen, voltage_channel, source='MAN')
    #keysight81150a.configure_output_amplifier(wavegen, voltage_channel) causes program to error as differentail amplifier and channel coupling bad
    keysight81150a.create_arb_wf(wavegen, interp_voltage_array, 'PV')
    keysight81150a.configure_arb_wf(wavegen, voltage_channel, 'PV', gain=f'{voltage*2}', freq=f'{waveform_freq}') 
    keysight81150a.configure_arb_wf(wavegen, current_channel, 'PV', gain=f'{voltage*2}', freq=f'{waveform_freq}')


def run_function(scope, wavegen, initial_delay, pulse_delay, freq, voltage, 
                 capacitor_area, thickness, permittivity, amplification, 
                 voltage_channel:str='1', current_channel:str='2'):
    """Run function for PVHysteresis expirement. 
    
    NOTE MIGHT WANT TO ADD TO BE ABLE TO ACCEPT FOR FREQ: '10KHZ' SYNTAX LIKE BEFORE.

    args:
        wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
        scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
        initial_delay (str): Intial delay in seconds
        pulse_delay (str): Same as Tdelay in seconds
        freq (str): Frequency, assumed in kHz unless a suffix is used (need to add logic)
        v_end (str): Voltage in units of volts (for vertical scale of osc), gets divided by 4 to scale voltage/div. Is later divided by loop_count to get the voltage step for each subsequent loop.
        capacitor_area (str): In units of m^2 use scientific notation (maybe add logic for suffixes)
        thickness (str): In units of m use scientific notation
        permittivity (str): Dielectric constant, gets multiplied by epsilon_0
        amplification (str): How much to amplify capacitor formula by used to calculate the current chnnl resolution which I dont use rn
    returns:
        (FE): Experiment
        
        
        notes:
        basicaly just calculate capacitance of sample from basic formula"""
    #first we initialize the meta_data
    meta_data = locals() #this just passes in all the arguments from the run function
    del meta_data['scope'], meta_data['wavegen'], meta_data['voltage_channel'], meta_data['current_channel'] 
    #NOTE I do not use current_chnnl_resolution at all in erics code
    capacitance = float(capacitor_area)*float(permittivity)*8.854e-12/float(thickness)
    current_chnnl_resolution = capacitance*50*float(amplification)
    if current_chnnl_resolution < 0.008: #changed from 0.008
        current_chnnl_resolution = 0.008
    time_scale = (float(initial_delay) + (float(pulse_delay) * 4) + (16 * (1/(float(freq) * 4000)))) / 10
    voltage_channel_scale = float(voltage)/4
    #make sure that current scale >= 0.008
    setup_scope(scope, time_scale, voltage_channel, current_channel, f'{voltage_channel_scale}', f'{current_chnnl_resolution}')
    #Loop over the loop count
    voltage = float(voltage)
    #first we need to setup the wavegen
    q_time_arr, time_array, waveform_freq, interp_time_arr, interp_voltage_array = pv_hysteresis_wf(initial_delay, freq, pulse_delay)
    setup_wavegen(wavegen, voltage_channel, current_channel, interp_voltage_array, waveform_freq, voltage)
    #NOW we actually take the data, send out the pulse and get the data, f labview for this part
    #Now we need to enable the wavegen, then acquire the data
    keysightdsox3024a.initiate(scope)
    keysight81150a.enable_output(wavegen, '1')

    '''
    Modiciation to add enable output to chnnl 2 of the wavegen
    '''
    keysight81150a.enable_output(wavegen, '2')


    keysight81150a.send_software_trigger(wavegen)
    scope.query("*OPC?")
    keysightdsox3024a.setup_wf(scope, source='CHAN1')
    metadata_v, time_v, wfm_v = keysightdsox3024a.query_wf(scope) 
    meta_data.update(metadata_v)
    time.sleep(.2)
    keysightdsox3024a.setup_wf(scope, source='CHAN2')
    metadata_c, time_c, wfm_c = keysightdsox3024a.query_wf(scope)

    meta_data.update(metadata_c)
    #How to structure the data that comes out, its going to be in a pandas df, but how. Kind of want to make it nested with raw and pv but idk
    df = pd.DataFrame({'time_v':time_v, 'wfm_v':wfm_v, 'time_c':time_c, 'wfm_c':wfm_c})
    base_name = 'fe_pv_'
    return base_name, meta_data, df


def wakeup_sherry(wavegen, channel='2', num_cycles='1e8', voltage='2', pulse_width='2e-6'):
    """
    This program will make a bipolar pulse and then configure it accordingly
    wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
    channel (str): channel to output too ['1', '2']
    
    notes: do not need an offset by default half is positive half is negative. Also Voltage is measured from 0 to a peak
    not peak-to-peak even though the instrument panel says it is... Make sure to change cabling
    """
    frequency = 1/(2*float(pulse_width))
    keysight81150a.initialize(wavegen)
    keysight81150a.set_output_wf(wavegen, channel, 'squ', frequency, voltage)
    total_wait_time = int(float(num_cycles)*(2* float(pulse_width)))
    td_str = str(timedelta(seconds=total_wait_time))
    print("Estimated total wait time is: {}".format(td_str))
    print("Check cabling is good to go for wakeup")
    #check for user input if itme is ok
    affirmative = input("Print y if the allotted time is correct")
    if affirmative == 'y':
        keysight81150a.enable_output(wavegen, channel)
        time.sleep(total_wait_time)
        keysight81150a.enable_output(wavegen, channel, False)
        print("Make sure to check cabling is correct now")
    

class PVHysteresis(core.experiment):
    """Experiment class for running creating hysteresis loops of PV. 

    args:
        wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
        scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
        run_function (function): Run function.

    returns:
        (FE): Experiment

    """

    def __init__(self, wavegen, scope, run_function=run_function):
        super().__init__(run_function)
        self.run_function = run_function
        self.wavegen = wavegen
        self.scope = scope
        return
    
    def _plot(self, data, scan_params):
        if hasattr(self, 'fig') and hasattr(self, 'ax'):
            pass
        else:
            fig, ax = plt.subplots()
            self.fig = fig
            self.ax = ax
        self.ax.scatter(data['time_v'], data['wfm_v'], color='blue')
        plt.show(self.fig)
        plotting.update_plot(self.fig)
        return


    def checks(self, params):
        """Checks during initialization."""
        if self.wavegen != params['wavegen']:
            try:
                raise ValueError('wavegen provided in initialization ({}) does not match that provided as an argument for run_function ({})'.format(self.wavegen, params['wavegen']))

            except KeyError:
                raise ValueError('wavegen provided in initialization ({}) does not match that provided as an argument for run_function ({})'.format(self.wavegen, None))

        
        if self.scope != params['scope']:
            try:
                raise ValueError('scope provided in initialization ({}) does not match that provided as an argument for run_function ({})'.format(self.scope, params['scope']))

            except KeyError:
                raise ValueError('scope provided in initialization ({}) does not match that provided as an argument for run_function ({})'.format(self.scope, None))
        
    def terminate(self):
        """Termination."""
        keysight81150a.stop(self.wavegen)
        return