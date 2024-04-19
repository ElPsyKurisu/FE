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
This program is used to generate a dataset on a FE sample to then calculate PV Curve. It works by sending in a series of square pulses first
polling the sample negative then two positive pulses followed by two negative ones allowing you to subtract away unwanted effects from the two
positive and two negative pulses

 Connect channel 1 of the wavegen to channel 1 of the scope, and connect
channel 2 of the wavegen in parallel with the sample which is in series with channel 2 of the scope. AKA connect channel 2 of the wavegen to port A via
BNC and connect channel 2 of the scope to port B also via BNC (no bannannas needed)

Will work the same way where there will be a timing issue between the two waveforms but oh well which
probably causes the slope issue I have with PV loops
"""

def setup_scope(scope, time_range, voltage_channel, current_channel,
                voltage_scale):
    keysightdsox3024a.initialize(scope)
    keysightdsox3024a.configure_timebase(scope, time_base_type='MAIN', reference='CENTer', range=f'{time_range}', position=f'{time_range/2.1}') #divid by 2 gives us right when it starts so 2.1 gives us a bit of leeway to start with
    keysightdsox3024a.configure_channel(scope, channel=voltage_channel, vertical_scale=voltage_scale, impedance='ONEM')#set both to 50ohm
    keysightdsox3024a.configure_channel(scope, channel=current_channel, vertical_scale=voltage_scale, impedance='ONEM')
    #NOTE changing the position now to 5* the timebase to hopefully get the full signal NOTE this might not work for this program
    keysightdsox3024a.configure_trigger_characteristics(scope, trigger_source='EXT', low_voltage_level='0.75', high_voltage_level='0.95', sweep='NORM')
    keysightdsox3024a.configure_trigger_edge(scope, trigger_source='EXT', input_coupling='DC')

def setup_wavegen(wavegen, voltage_channel, current_channel, wf, waveform_freq, voltage):
    keysight81150a.initialize(wavegen)
    keysight81150a.couple_channels(wavegen)
    keysight81150a.configure_impedance(wavegen, voltage_channel, source_impedance='50.0', load_impedance='1e6')
    keysight81150a.configure_impedance(wavegen, current_channel, source_impedance='50.0', load_impedance='1e6')
    keysight81150a.configure_trigger(wavegen, voltage_channel, source='MAN')
    keysight81150a.create_arb_wf(wavegen, wf, 'PUND') #does not work with volatile
    keysight81150a.configure_arb_wf(wavegen, voltage_channel, 'PUND', gain=f'{voltage*4}', freq=f'{waveform_freq}')
    keysight81150a.configure_arb_wf(wavegen, current_channel, 'PUND', gain=f'{voltage*4}', freq=f'{waveform_freq}')


def create_PUND_wf(pulse_width, pulse_delay):
    """
    Helper function that creates the PUND wf, can be later replaced by a read file if it is desired
    to have an external file hold the PUND wf and gives us the frequnecy
    """
    pulse_width = float(pulse_width)
    pulse_delay = float(pulse_delay)
    if pulse_delay < pulse_width:
        raise ValueError("Pulse delay cannot be lower than pulse width, check your values and try again")
    ratio = int(pulse_delay/pulse_width) #this tells us how much longer the pulse width is careful cuz its rounding to nearest int btw
    delay_list = [0] * ratio
    pulse_1 = [-1, 0] + delay_list
    pulse_2 = [1, 0] + delay_list
    pulse_3 = [1, 0] + delay_list
    pulse_4 = [-1, 0] + delay_list
    pulse_5 = [-1, 0] + delay_list
    PUND_wf = pulse_1 + pulse_2 + pulse_3 + pulse_4 + pulse_5
    scale_factor = 5
    index = 0
    scaled_PUND_wf = PUND_wf[:]
    for i in range(len(PUND_wf)):
        value = PUND_wf[i]
        to_be_inserted = [value]*scale_factor 
        scaled_PUND_wf[index:index] = to_be_inserted
        index += 5
    scaled_PUND_wf = scaled_PUND_wf[:-len(PUND_wf)] #this removes original from the list

    total_wf_len = 10*(pulse_width) + 5*(pulse_delay) #see img for reasoning
    freq = 1/total_wf_len
    return scaled_PUND_wf, freq, total_wf_len




def run_function(scope, wavegen, pulse_width, pulse_delay, voltage_max, num_points=20, step_size=None, capacitor_area=None, thickness=None, permittivity=None,
                 voltage_channel:str='1', current_channel:str='2'):
    """Run function for PUND PV Curve expirement.

    args:
        wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
        scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
        pulse_width (str): Pulse width in seconds (see img for more information)
        pulse_delay (str): Pulse delay in seconds (see img for more information)
        voltage_max (str): Voltage in units of volts where the program should end
        num_points (str): Total number of data points for PV plot, optional default is 20
        step_size (str): Step size in volts, optional if not given uses num_points
        capacitor_area (str): In units of m^2 use scientific notation (maybe add logic for suffixes)
        thickness (str): In units of m use scientific notation
        permittivity (str): Dielectric constant, gets multiplied by epsilon_0
    returns:
        (PUND): Experiment
        
        
        notes: wip
    
    """

    #first we initialize the meta_data
    meta_data = locals() #this just passes in all the arguments from the run function
    del meta_data['scope'], meta_data['wavegen'], meta_data['voltage_channel'], meta_data['current_channel']
    capacitance = float(capacitor_area)*float(permittivity)*8.854e-12/float(thickness)
    PUND_wf, freq, total_wf_len = create_PUND_wf(pulse_width, pulse_delay)
    voltage_channel_scale = 1 #note will change later once i implement actual loop lol
    voltage = 1
    setup_scope(scope, total_wf_len, voltage_channel, current_channel, f'{voltage_channel_scale}')

    setup_wavegen(wavegen, voltage_channel, current_channel, PUND_wf, freq, voltage)

    keysightdsox3024a.initiate(scope)
    keysight81150a.enable_output(wavegen)
    keysight81150a.enable_output(wavegen, '2')
    keysight81150a.send_software_trigger(wavegen)
    scope.query("*OPC?")
    keysightdsox3024a.setup_wf(scope, source='CHAN1')
    metadata_v, time_v, wfm_v = keysightdsox3024a.query_wf(scope) #currently times out here
    meta_data.update(metadata_v)
    time.sleep(.2)
    keysightdsox3024a.setup_wf(scope, source='CHAN2')
    metadata_c, time_c, wfm_c = keysightdsox3024a.query_wf(scope)

    meta_data.update(metadata_c)
    #How to structure the data that comes out, its going to be in a pandas df, but how. Kind of want to make it nested with raw and pv but idk
    df = pd.DataFrame({'time_v':time_v, 'wfm_v':wfm_v, 'time_c':time_c, 'wfm_c':wfm_c})
    base_name = 'fe_PUND_PV_'
    return base_name, meta_data, df


class PUNDPVCurve(core.experiment):
    """Experiment class for running a PUND PV curve.

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
    

