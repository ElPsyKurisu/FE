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
This program is used to generate a dataset on a FE sample to then calculate IV Curve. It works by sending in a series of triangle pulses
and then meauring the current and the voltage across the capacitor sample. Connect channel 1 of the wavegen to channel 1 of the scope, and connect
channel 2 of the wavegen in parallel with the sample which is in series with channel 2 of the scope. AKA connect channel 2 of the wavegen to port A via
BNC and connect channel 2 of the scope to port B also via BNC (no bannannas needed)

Will work the same way where there will be a timing issue between the two waveforms but oh well which
probably causes the slope issue I have with PV loops
"""

def setup_scope(scope, time_scale, voltage_channel, current_channel,
                voltage_scale):
    keysightdsox3024a.initialize(scope)
    keysightdsox3024a.configure_timebase(scope, time_base_type='MAIN', reference='CENTer', scale=f'{time_scale}', position=f'{5*time_scale}')
    keysightdsox3024a.configure_channel(scope, channel=voltage_channel, vertical_scale=voltage_scale, impedance='FIFT')#set both to 50ohm
    keysightdsox3024a.configure_channel(scope, channel=current_channel, vertical_scale=voltage_scale, impedance='FIFT')
    #NOTE changing the position now to 5* the timebase to hopefully get the full signal NOTE this might not work for this program
    keysightdsox3024a.configure_trigger_characteristics(scope, trigger_source='EXT', low_voltage_level='0.75', high_voltage_level='0.95', sweep='NORM')
    keysightdsox3024a.configure_trigger_edge(scope, trigger_source='EXT', input_coupling='DC')

def setup_wavegen(wavegen, voltage_channel, current_channel, waveform_freq, voltage):
    keysight81150a.initialize(wavegen)
    keysight81150a.configure_impedance(wavegen, voltage_channel, source_impedance='50.0', load_impedance='50')
    keysight81150a.configure_impedance(wavegen, current_channel, source_impedance='50.0', load_impedance='50') #changed load from 1000000
    keysight81150a.configure_trigger(wavegen, voltage_channel, source='MAN')
    keysight81150a.configure_output_amplifier(wavegen, voltage_channel)
    keysight81150a.configure_output_amplifier(wavegen, current_channel)

    keysight81150a.set_output_wf(wavegen, voltage_channel, 'RAMP', waveform_freq, voltage)
    keysight81150a.set_output_wf(wavegen, current_channel, 'RAMP', waveform_freq, voltage)


def run_function(scope, wavegen, freq, voltage, capacitor_area, thickness, permittivity,
                 voltage_channel:str='1', current_channel:str='2'):
    """Run function for IV Curve expirement.

    args:
        wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
        scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
        freq (str): Frequency, assumed in kHz unless a suffix is used (need to add logic)
        voltage (str): Voltage in units of volts (for vertical scale of osc), gets divided by 4 to scale voltage/div. Is later divided by loop_count to get the voltage step for each subsequent loop.
        capacitor_area (str): In units of m^2 use scientific notation (maybe add logic for suffixes)
        thickness (str): In units of m use scientific notation
        permittivity (str): Dielectric constant, gets multiplied by epsilon_0
    returns:
        (IV): Experiment
        
        
        notes: wip
    
    """

    #first we initialize the meta_data
    meta_data = locals() #this just passes in all the arguments from the run function
    del meta_data['scope'], meta_data['wavegen'], meta_data['voltage_channel'], meta_data['current_channel']
    capacitance = float(capacitor_area)*float(permittivity)*8.854e-12/float(thickness)
    time_scale = 1/float(freq)
    voltage_channel_scale = float(voltage)/4
    setup_scope(scope, time_scale, voltage_channel, current_channel, f'{voltage_channel_scale}')

    setup_wavegen(wavegen, voltage_channel, current_channel, freq, voltage)

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
    base_name = 'fe_iv_'
    return base_name, meta_data, df


class IVCurve(core.experiment):
    """Experiment class for running an IV curve.

    args:
        wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
        scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
        run_function (function): Run function.

    returns:
        (IV): Experiment

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
    

