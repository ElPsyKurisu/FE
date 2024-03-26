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


__all__ = ('find_peaks_troughs_index', 'start_and_end_pulse', 'generate_q_wfm', 'drift_correct_q', 'plot',)


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
    if len(x)%2 == 1:
        x = x[:-1] #if odd remove last element fixes errors
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
    data_dict['start_and_end_pulse'] = np.array(green_points)
    return data_dict

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

def drift_correct_q(data_dict)-> 'dict':
    """
    Changes 'wfm_q' to the given data_dict by integrating over the given waveform. Also will be used
    to show how when u modify an existing key the non drift corrected version can still be obtained
    by use of the data_saver method (since a seperate data object is created for each function)

    modifying to not take the last element rn, since there is a time delay between voltage and current wf so we are shifted
    and that is messing up the drift corrects A better drift correct could be using the pulse lengths, by averaging across
    all 4 pulses

    Requirements
    ------------
    wfm_q: dict key 
        The data_dict key containing the charge wf
    time_c: dict key
        The data_dict key containing the time wf
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the q_wfm added.
    PLOT_AGAINST: time_c
    MODIFIES: wfm_q"""
    slope = (data_dict['wfm_q'][-1] - data_dict['wfm_q'][0])/(data_dict['time_c'][-1] - data_dict['time_c'][0])
    wfm_q_drift_corrected = []
    for i in range(len(data_dict['wfm_q'])):
        wfm_q_drift_corrected.append(data_dict['wfm_q'][i]-(slope*data_dict['time_c'][i]))
    data_dict['wfm_q'] = wfm_q_drift_corrected
    return data_dict

def plot(data_dict) -> None:
    """
    Plots 'wfm_q' vs 'wfm_v' to make a PV plot.

    Requirements
    ------------
    wfm_q: dict key 
        The data_dict key containing the charge wf
    wfm_v: dict key
        The data_dict key containing the voltage wf
    Returns
    -------
    None
    PLOT_AGAINST: None
    MODIFIES: None"""
    start_and_end_pulse = data_dict['start_and_end_pulse']
    i = 0
    start = start_and_end_pulse[0]
    end = start_and_end_pulse[1]
    y_arr = data_dict['wfm_q']
    x_arr = data_dict['wfm_v']
    max = np.max(y_arr[start:end])
    while i < len(start_and_end_pulse):
        start = start_and_end_pulse[i]
        end = start_and_end_pulse[i+1]
        other_max = np.max(y_arr[start:end])
        y_offset = max - other_max
        y_arr[start:end] += y_offset
        plt.plot(x_arr[start:end], y_arr[start:end])
        i += 2
    plt.title('PV Loops')
    plt.xlabel('Voltage (V)')
    plt.ylabel('Charge Q')


