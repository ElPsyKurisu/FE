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


def find_peaks_troughs_index_start_and_end(data_dict)->'dict':
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
    arr_normalized = 2 * ((arr - np.min(arr)) / (np.max(arr) - np.min(arr))) - 1
    peaks, _ = find_peaks(arr_normalized, height=0.8, distance=50)
    troughs, _ = find_peaks(-1*arr_normalized, height=0.8, distance=50)
    all_peaks = np.concatenate((peaks, troughs), axis=0)

    arr2 = data_dict['wfm_v']
    arr_normalized2 = 2 * ((arr2 - np.min(arr2)) / (np.max(arr2) - np.min(arr2))) - 1
    peaks2, _ = find_peaks(arr_normalized2, height=0.8, distance=50)
    troughs2, _ = find_peaks(-1*arr_normalized, height=0.8, distance=50)
    offset = len(arr2) - 1
    all_peaks = offset - np.concatenate((peaks, troughs, peaks2, troughs2), axis=0)

    data_dict['start_and_end_pulse'] = np.sort(all_peaks)
    return data_dict

def find_peaks_troughs_index_end(data_dict)->'dict':
    """
    Adds 'peaks' to the given data_dict by using scipy to find the peaks and troughs.
    modified to skip based on pulse length

    Requirements
    ------------
    wfm_v: dict key 
        The data_dict key containing the voltage wf
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the peaks indexes added.

    MODIFIES: peaks"""
    arr = data_dict['wfm_v'][::-1] #reverse the list and repeat process
    arr_normalized = 2 * ((arr - np.min(arr)) / (np.max(arr) - np.min(arr))) - 1
    peaks, _ = find_peaks(arr_normalized, height=0.8, distance=50)
    troughs, _ = find_peaks(-1*arr_normalized, height=0.8, distance=50)
    offset = len(arr) - 1
    all_peaks = offset - np.concatenate((peaks, troughs), axis=0) 
    data_dict['peaks_reverse'] = np.sort(all_peaks)
    return data_dict