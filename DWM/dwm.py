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

"""
This program is used to generate a dataset on a FE sample to then calculate 3 curves. This program follows the basic framework outlined in 
this paper: insertdoihere where the authors construct a method to seperate the ferroelectric charge component from the conductive and dielectric
charge componenets.

A Brief Description is given here:
The waveform: See image in the same directory. But principle is the same as Jessy PUND

Send in triangle waveform than 2 identical up triangle pulses and 2 identical down triangle pulses (this is literally Jessy's PUND no?)

Can write a version for use with a reference capacitor and one for the same method I've been doing up till no. First lets figure out how to make the waveform lol



 It works by sending in a series of square pulses first
polling the sample negative then two positive pulses followed by two negative ones allowing you to subtract away unwanted effects from the two
positive and two negative pulses

 Connect channel 1 of the wavegen to channel 1 of the scope, and connect
channel 2 of the wavegen in parallel with the sample which is in series with channel 2 of the scope. AKA connect channel 2 of the wavegen to port A via
BNC and connect channel 2 of the scope to port B also via BNC (no bannannas needed)

"""

"""
NOTE TO BE DELETED JUST MY NOTES FOR WHAT TO DO

"""


def setup_scope(scope, time_range, voltage_channel, current_channel,
                voltage_scale):
    keysightdsox3024a.initialize(scope)
    keysightdsox3024a.configure_timebase(scope, time_base_type='MAIN', reference='CENTer', range=f'{time_range}', position=f'{time_range/2.1}') #divid by 2 gives us right when it starts so 2.1 gives us a bit of leeway to start with
    keysightdsox3024a.configure_channel(scope, channel=voltage_channel, vertical_scale=voltage_scale, impedance='FIFT')#set both to 50ohm
    keysightdsox3024a.configure_channel(scope, channel=current_channel, vertical_scale=voltage_scale, impedance='FIFT')
    #NOTE changing the position now to 5* the timebase to hopefully get the full signal NOTE this might not work for this program
    keysightdsox3024a.configure_trigger_characteristics(scope, trigger_source='EXT', low_voltage_level='0.75', high_voltage_level='0.95', sweep='NORM')
    keysightdsox3024a.configure_trigger_edge(scope, trigger_source='EXT', input_coupling='DC')

def setup_wavegen(wavegen, voltage_channel, current_channel, wf, waveform_freq, voltage):
    keysight81150a.initialize(wavegen)
    keysight81150a.couple_channels(wavegen)
    keysight81150a.configure_impedance(wavegen, voltage_channel, source_impedance='50.0', load_impedance='50')
    keysight81150a.configure_trigger(wavegen, voltage_channel, source='MAN')
    keysight81150a.create_arb_wf(wavegen, wf, 'DWM') #does not work with volatile
    keysight81150a.configure_arb_wf(wavegen, voltage_channel, 'DWM', gain=f'{2*float(voltage)}', freq=f'{waveform_freq}')
    keysight81150a.configure_arb_wf(wavegen, current_channel, 'DWM', gain=f'{2*float(voltage)}', freq=f'{waveform_freq}')


def create_DWM_wf(pulse_width, pulse_delay):
    """
    Helper function that creates the DWM wf, can be later replaced by a read file if it is desired
    to have an external file hold the DWM wf and gives us the frequnecy
    Returns the full_wf file as well as the required frequency to setup the wavegen with, note hardcoded
    100 so if pulse_delay and pulse_width are too far apart we can have problems
    NOTE: Triangle version not sinusoidal like paper
    """
    ratio = pulse_width/pulse_delay

    if ratio > 1:
        sampling_rate = int(100 * ratio/2)
        delay_length = 100
    else:
        sampling_rate = 100
        delay_length = int(100/ratio)
    a = np.linspace(0,1,sampling_rate, endpoint=False) #end at 0.9
    b= np.linspace(1,-1,2*sampling_rate, endpoint=False) #ends at -0.9
    c=np.linspace(-1, 0, sampling_rate, endpoint=False) #ends at 0 so we need to remove last element
    triangle_wf = np.concatenate((a,b,c)) #can round at the end after I make the entire array lol

    a = np.linspace(0,1,sampling_rate, endpoint=False) #end at 0.9
    b=np.linspace(1, 0, sampling_rate, endpoint=False) #doesnt end at 0
    pos_pulse = np.concatenate((a,b))
    neg_pulse = -1* pos_pulse
    delay_pulse = np.zeros(delay_length)

    full_wf = np.round(np.concatenate((triangle_wf, delay_pulse, pos_pulse, delay_pulse, pos_pulse, delay_pulse, neg_pulse, delay_pulse, neg_pulse, delay_pulse)), decimals=3)

    total_time = 5*pulse_delay + 6*pulse_width
    freq = 1/total_time
    return full_wf, freq, total_time




def run_function(scope, wavegen, pulse_width, pulse_delay, voltage, capacitor_area=None, thickness=None, permittivity=None,
                 voltage_channel:str='1', current_channel:str='2'):
    """Run function for PUND PV Curve expirement.

    args:
        wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
        scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
        pulse_width (str): Pulse width in seconds (see img for more information)
        pulse_delay (str): Pulse delay in seconds (see img for more information)
        voltage (str): Voltage in units of volts where the program should end
        capacitor_area (str): In units of m^2 use scientific notation (maybe add logic for suffixes)
        thickness (str): In units of m use scientific notation
        permittivity (str): Dielectric constant, gets multiplied by epsilon_0
    returns:
        (DWM): Experiment
        
        
        notes: wip but getting there, analysis part will be a pain
    
    """

    #first we initialize the meta_data
    meta_data = locals() #this just passes in all the arguments from the run function
    del meta_data['scope'], meta_data['wavegen'], meta_data['voltage_channel'], meta_data['current_channel']
    capacitance = float(capacitor_area)*float(permittivity)*8.854e-12/float(thickness)
    DWM_wf, freq, total_wf_len = create_DWM_wf(float(pulse_width), float(pulse_delay))
    setup_scope(scope, total_wf_len, voltage_channel, current_channel, voltage)

    setup_wavegen(wavegen, voltage_channel, current_channel, DWM_wf, freq, voltage)

    keysightdsox3024a.initiate(scope)
    keysight81150a.enable_output(wavegen)
    keysight81150a.enable_output(wavegen, '2')
    keysight81150a.send_software_trigger(wavegen)
    scope.query("*OPC?")
    keysightdsox3024a.setup_wf(scope, source='CHAN1', points_mode='MAX', points='100000')
    metadata_v, time_v, wfm_v = keysightdsox3024a.query_wf(scope) #currently times out here
    meta_data.update(metadata_v)
    time.sleep(.2)
    keysightdsox3024a.setup_wf(scope, source='CHAN2', points_mode='MAX', points='100000')
    metadata_c, time_c, wfm_c = keysightdsox3024a.query_wf(scope)

    meta_data.update(metadata_c)
    #How to structure the data that comes out, its going to be in a pandas df, but how. Kind of want to make it nested with raw and pv but idk
    df = pd.DataFrame({'time_v':time_v, 'wfm_v':wfm_v, 'time_c':time_c, 'wfm_c':wfm_c})
    base_name = 'fe_DWM_'
    return base_name, meta_data, df


class DWM(core.experiment):
    """Experiment class for running a DWM curve.

    args:
        wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
        scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
        run_function (function): Run function.

    returns:
        (PUND): Experiment

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
    

