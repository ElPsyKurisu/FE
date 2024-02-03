'''
This is a new system where I will add functionality to ekpy.analysis to allow you to list all the analysis functions you will use here then ekpy will automatically be able to apply
them as well as spit out a verbose summary of all the functions done, and iterate through each step of applying functions in a seperate dictionary (or data file).
This file should ONLY contain the functions that you want to apply in the order in which they should be applied as well as sufficient documnentation for each
function in order to use the visualize analysis command. Also consider adding an __all__ check in the beginning

Keyword for what it adds should be MODIFIES: (str to be appended and should end with the 3 quotes to mark end of doc)

might also need to note in each doc what should be plotted if the visualize analysis is called. Can have a default that if its 
not specified in the docstring of the funciton whatever is passed into visualize analysis works instead.
PLOT_AGAINST is optional paramater that says what to plot against, otherwise we choose the first element in the data

'''

import numpy as np
import scipy.integrate as it
from scipy.signal import find_peaks
from inspect import getdoc, getmembers, isfunction


#__all__ = ('generate_q_wfm', 'generate_q_wfm_wrong',)
__all__ = ('generate_q_wfm', 'generate_q_wfm_wrong', 'find_peaks_troughs_index', 'start_and_end_pulse', )


def generate_q_wfm(data_dict) -> 'dict':
    """
    Adds 'wfm_q' to the given data_dict by integrating over the given waveform.

    Requirements
    ------------
    wfm_c: dict key 
        The data_dict key containing the current wf
    time_c: dict key
        The data_dict key containing the time wf
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the q_wfm added.
    PLOT_AGAINST: time_c
    MODIFIES: wfm_q"""
    wfm_q = it.cumulative_trapezoid(data_dict['wfm_c'], data_dict['time_c'], initial=0) 
    data_dict['wfm_q'] = wfm_q
    return data_dict

def generate_q_wfm_wrong(data_dict) -> 'dict':
    """
    Adds 'wfm_q_wrong' to the given data_dict by integrating over the given waveform.

    Requirements
    ------------
    wfm_c: dict key 
        The data_dict key containing the current wf
    time_c: dict key
        The data_dict key containing the time wf
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the q_wfm_wrong added.
    PLOT_AGAINST: time_c
    MODIFIES: wfm_q_wrong"""
    wfm_q = it.cumulative_trapezoid(data_dict['wfm_v'], data_dict['time_v'], initial=0) 
    data_dict['wfm_q_wrong'] = wfm_q
    return data_dict

def find_peaks_troughs_index(data_dict)->'dict':
    """
    Adds 'peaks' to the given data_dict by using scipy to find the peaks and troughs.

    Requirements
    ------------
    wfm_v: dict key 
        The data_dict key containing the voltage wf
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the peaks indexes added.

    MODIFIES: peaks"""
    arr = data_dict['wfm_v']
    arr_normalized = 2 * ((arr - np.min(arr)) / (np.max(arr) - np.min(arr))) - 1
    peaks, _ = find_peaks(arr_normalized, height=0.8)
    troughs, _ = find_peaks(-1*arr_normalized, height=0.8)
    all_peaks = np.concatenate((peaks, troughs), axis=0)
    data_dict['peaks'] = np.sort(all_peaks)
    return data_dict

def start_and_end_pulse(data_dict)->'dict':
    """
    Adds 'start_and_end_pulse' to the given data_dict by using the given peaks and the fact that each
    pulse is symmetric such that the difference between peaks is equal to have a pulse length.

    Requirements
    ------------
    peaks: dict key 
        The data_dict key containing the peak indices
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the start_and_else_pulse added. Format is index 0 and 1 is the start
        and end of the first pulse, index 2 and 3 is start and end of 2nd pulse, and so forth
    
    MODIFIES: start_and_end_pulse"""
    x = data_dict['peaks']
    counter = 0
    green_points = []
    while counter <(len(x)):
        half_pulse_len = x[counter+1] - x[counter]
        quarter_pulse_len = half_pulse_len/2
        start_of_pulse = x[counter] - quarter_pulse_len
        end_of_pulse = x[counter+1] + quarter_pulse_len
        green_points.append(int(start_of_pulse))
        green_points.append(int(end_of_pulse))
        counter +=2
    data_dict['start_and_end_pulse'] = green_points
    return data_dict

def do_nothing_test(data_dict):
    """
    Should not be able to be called since its not in __all__
    """
    return
