'''
This is a new system where I will add functionality to ekpy.analysis to allow you to list all the analysis functions you will use here then ekpy will automatically be able to apply
them as well as spit out a verbose summary of all the functions done, and iterate through each step of applying functions in a seperate dictionary (or data file).
This file should ONLY contain the functions that you want to apply in the order in which they should be applied as well as sufficient documnentation for each
function in order to use the visualize analysis command. Also consider adding an __all__ check in the beginning

Keyword for what it adds should be MODIFIES: (str to be appended and should end with the 3 quotes to mark end of doc)

might also need to note in each doc what should be plotted if the visualize analysis is called. Can have a default that if its 
not specified in the docstring of the funciton whatever is passed into visualize analysis works instead.
PLOT_AGAINST is optional paramater that says what to plot against, otherwise we choose the first element in the data

WOULD LIKE TO ADD A METHOD WHERE BY CONVENTION THE LAST FUNCTION IS WHERE YOU DEFINE YOUR PLOTTING FUNCTION FOR THE FINAL RESULT BUT IT
DOESNT MESS UP WHAT IVE ADDED ALREADY turns out you can add it whenever in the flow and it will not error (note needed to update ekpy for this)

'''

import numpy as np
import scipy.integrate as it
from scipy.signal import find_peaks
import matplotlib.pyplot as plt


__all__ = ('find_peaks_troughs_index_start_and_end', 'find_peaks_troughs_index_start', 'generate_q_wfm', 'drift_correct_q', 'plot',)


def find_peaks_troughs_index_start_and_end(data_dict, **kwargs)->'dict':
    """
    Adds 'start_and_end' to the given data_dict by using scipy to find the peaks and troughs which only finds the start,
    reverses the list and repeats and then transforms the data to find the end.

    Requirements
    ------------
    wfm_v: dict key 
        The data_dict key containing the voltage wf
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the start and end of the pulses added.

    MODIFIES: start_and_end_pulse"""
    arr = data_dict['wfm_v']
    arr_normalized = np.abs(2 * ((arr - np.min(arr)) / (np.max(arr) - np.min(arr))) - 1)
    my_signal = np.abs(arr_normalized)
    pulse_indices = find_pulse_indices(my_signal)
    flat_list = np.array([item for sublist in pulse_indices for item in sublist])

    data_dict['start_and_end_pulse'] = flat_list
    return data_dict

def generate_q_values(data_dict, **kwargs) -> 'dict':
    """
    Adds 'q_vals' to the given data_dict by integrating over the given waveform. Returns a list of values
    corresponding to the 8 measuremnts as described by Radiant used in PUND, p1, p1r, p2, p2r, p3, p3r, p4, p4r

    Requirements
    ------------
    wfm_c: dict key 
        The data_dict key containing the current wf
    time_c: dict key
        The data_dict key containing the time wf
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the q_vals added.
    MODIFIES: q_vals"""
    start_and_end_pulse = data_dict['start_and_end_pulse']
    pulse_width = list(kwargs['pulse_width'])[0]
    t_increment = list(kwargs['x_increment'])[0]
    pulse_index_len = int(pulse_width/t_increment)
    q1 = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[0]:start_and_end_pulse[1]], dx=t_increment)
    q2 = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[2]:start_and_end_pulse[3]], dx=t_increment)
    q3 = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[4]:start_and_end_pulse[5]], dx=t_increment)
    q4 = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[6]:start_and_end_pulse[7]], dx=t_increment)

    #time to also got the remnamnt values by using end values plus 1 plus step size to know how long it is

    q1r = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[1]+1:start_and_end_pulse[1]+pulse_index_len + 1], dx=t_increment)
    q2r = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[3]+1:start_and_end_pulse[3]+pulse_index_len + 1], dx=t_increment)
    q3r = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[5]+1:start_and_end_pulse[5]+pulse_index_len + 1], dx=t_increment)
    q4r = it.trapezoid(data_dict['wfm_c'][start_and_end_pulse[7]+1:start_and_end_pulse[7]+pulse_index_len + 1], dx=t_increment)


    data_dict['q_vals'] = np.array([q1, q1r, q2, q2r, q3, q3r, q4, q4r])
    return data_dict

def get_remanant_polarization(data_dict, **kwargs) -> 'dict':
    """
    Adds 'calc_vals' to the given data_dict by subtracting relevant ones. Returns a list of values
    corresponding to the 8 measuremnts as described by Radiant used in PUND, p1, p1r, p2, p2r, p3, p3r, p4, p4r
    NOTE STILL ONLY CHARGE NOT POLARIZATION HAVENT SCALED IT PROPERLY
    Requirements
    ------------
    q_vals: dict key 
        The data_dict key containing the charge values
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the q_vals added.
    MODIFIES: calc_vals"""
    q_vals = data_dict['q_vals']
    dp12 = q_vals[0] - q_vals[2]
    dp1r2r = q_vals[1] - q_vals[3]
    dp34 = q_vals[4] - q_vals[6]
    dp3r4r = q_vals[5] - q_vals[7]
    data_dict['calc_vals'] = np.array([dp12, dp1r2r, dp34, dp3r4r])

"""
Helper Functions go here
"""

def find_pulse_indices(signal):
    """
    Finds the start and end indices of rectangular pulses in a given signal.

    Args:
        signal (np.ndarray): Input signal (1D array).

    Returns:
        list of tuples: Each tuple contains the start and end indices of a pulse.
    """
    pulse_indices = []
    pulse_start = None
    threshold = 0.9
    for i, value in enumerate(signal):
        if value > threshold:  # Assuming 1 represents the pulse
            if pulse_start is None:
                pulse_start = i
        elif pulse_start is not None:
            pulse_indices.append((pulse_start, i - 1))
            pulse_start = None
    
    return pulse_indices
