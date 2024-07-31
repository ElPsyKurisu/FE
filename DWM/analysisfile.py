'''
This is a new system where I will add functionality to ekpy.analysis to allow you to list all the analysis functions you will use here then ekpy will automatically be able to apply
them as well as spit out a verbose summary of all the functions done, and iterate through each step of applying functions in a seperate dictionary (or data file).
This file should ONLY contain the functions that you want to apply in the order in which they should be applied as well as sufficient documnentation for each
function in order to use the visualize analysis command. Also consider adding an __all__ check in the beginning

Keyword for what it adds should be MODIFIES: (str to be appended and should end with the 3 quotes to mark end of doc)

might also need to note in each doc what should be plotted if the visualize analysis is called. Can have a default that if its 
not specified in the docstring of the funciton whatever is passed into visualize analysis works instead.
PLOT_AGAINST is optional paramater that says what to plot against, otherwise we try the first element in the data else we skip


WILL ERROR if **kwargs is not included in function since it passes defn by default, can add a toggle later to use analysis

'''

import numpy as np
import scipy.integrate as it
from scipy.signal import find_peaks
import matplotlib.pyplot as plt


__all__ = ('find_peaks_troughs_index', 'start_and_end_pulse', 'generate_q_wfm', 'drift_correct_q','generate_wfm_v_piecewise', 'generate_dwm_wfm', 'generate_primary_wfm', 'generate_secondary_wfm', 'plot',)


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
    distance_between_peaks = len(arr)/10
    peaks, _ = find_peaks(arr_normalized, height=0.95, distance=distance_between_peaks)
    troughs, _ = find_peaks(-1*arr_normalized, height=0.95, distance=distance_between_peaks)
    all_peaks = np.concatenate((peaks, troughs), axis=0)
    data_dict['peaks'] = np.sort(all_peaks)
    return data_dict

def start_and_end_pulse(data_dict)->'dict':
    """
    Adds 'start_and_end_pulse' to the given data_dict by using the first two peaks to determine peak width. Format
    is start1, end1, start2...

    Requirements
    ------------
    peaks: dict key 
        The data_dict key containing the peak indices
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the start_and_else_pulse added. Format is an array of tuples where the first
        element is the start and the second is the end
    
    MODIFIES: start_and_end_pulse"""
    x = data_dict['peaks']
    if len(x) != 6:
        print("Error found {} peaks instead of 6".format(len(x))) #change to error
    pulse_width = x[1] - x[0]
    start_1 = int(x[2] - pulse_width/2)
    end_1 = int(x[2] + pulse_width/2)
    start_2 = int(x[3] - pulse_width/2)
    end_2 = int(x[3] + pulse_width/2)
    start_3 = int(x[4] - pulse_width/2)
    end_3 = int(x[4] + pulse_width/2)
    start_4 = int(x[5] - pulse_width/2)
    end_4 = int(x[5] + pulse_width/2)
    data_dict['start_and_end_pulse'] = np.array([start_1, end_1, start_2, end_2, start_3, end_3, start_4, end_4]) #cannot make multidimensional
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

def drift_correct_q(data_dict)-> 'dict': #not sure if i should do here, but maybe? could change to drift_correct_all which does dwm, primary, and secondary (raw too?)
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

def generate_wfm_v_piecewise(data_dict) -> 'dict':
    """
    Generates piecewise v waveform to be used in plotting DWM, Primary, and Secondary.

    Requirements
    ------------
    wfm_v: dict key 
        The data_dict key containing the voltage wf
    start_and_end_pulse: dict key 
        The data_dict key containing the start and end of the pulses
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the wfm_dwm added.
    MODIFIES: wfm_v_piecewise"""
    wfm_v = data_dict['wfm_v']
    start_and_end_pulse = data_dict['start_and_end_pulse']
    wfm_v_piecewise = np.concatenate((wfm_v[start_and_end_pulse[0]:start_and_end_pulse[1]],wfm_v[start_and_end_pulse[4]:start_and_end_pulse[5]]))
    data_dict['wfm_v_piecewise'] = wfm_v_piecewise
    return data_dict

def generate_dwm_wfm(data_dict) -> 'dict': 
    """
    Generates piecewise Q waveform by subtracting Pulse 1 from 2 and 3 from 4.

    Requirements
    ------------
    wfm_q: dict key 
        The data_dict key containing the current wf
    time_c: dict key
        The data_dict key containing the time wf
    start_and_end_pulse: dict key 
        The data_dict key containing the start and end of the pulses
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the wfm_dwm added.
    MODIFIES: wfm_dwm"""
    wfm_q = data_dict['wfm_q']
    start_and_end_pulse = data_dict['start_and_end_pulse']
    pos = wfm_q[start_and_end_pulse[0]:start_and_end_pulse[1]] - wfm_q[start_and_end_pulse[2]:start_and_end_pulse[3]]
    neg = wfm_q[start_and_end_pulse[4]:start_and_end_pulse[5]] - wfm_q[start_and_end_pulse[6]:start_and_end_pulse[7]]
    wfm_dwm = np.concatenate((pos, neg)) #can argue if i should also put the actual voltage there or we use the same one for all four?
    data_dict['wfm_dwm'] = wfm_dwm
    return data_dict

def shift_dwm_wfm(data_dict) -> 'dict':
    """
    Modifies the wfm_dwm waveform by adding an offset to the second half.

    Requirements
    ------------
    wfm_dwm: dict key 
        The data_dict key containing the dwm wf
    start_and_end_pulse: dict key 
        The data_dict key containing the start and end of the pulses
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the wfm_dwm added.
    MODIFIES: wfm_dwm"""
    start_and_end_pulse = data_dict['start_and_end_pulse']
    wfm_dwm = data_dict['wfm_dwm']
    end_of_first_half = start_and_end_pulse[1] - start_and_end_pulse[0]
    second_half = wfm_dwm[end_of_first_half:]

def generate_primary_wfm(data_dict) -> 'dict':
    """
    Generates piecewise Q waveform by stitching together pulse 1 and 3.

    Requirements
    ------------
    wfm_q: dict key 
        The data_dict key containing the current wf
    time_c: dict key
        The data_dict key containing the time wf
    start_and_end_pulse: dict key 
        The data_dict key containing the start and end of the pulses
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the wfm_primary added.
    MODIFIES: wfm_primary"""
    wfm_q = data_dict['wfm_q']
    start_and_end_pulse = data_dict['start_and_end_pulse']
    pos = wfm_q[start_and_end_pulse[0]:start_and_end_pulse[1]]
    neg = wfm_q[start_and_end_pulse[4]:start_and_end_pulse[5]] 
    wfm_primary = np.concatenate((pos, neg)) #can argue if i should also put the actual voltage there or we use the same one for all four?
    data_dict['wfm_primary'] = wfm_primary
    return data_dict

def generate_secondary_wfm(data_dict) -> 'dict':
    """
    Generates piecewise Q waveform by stitching together pulse 2 and 4.

    Requirements
    ------------
    wfm_q: dict key 
        The data_dict key containing the current wf
    time_c: dict key
        The data_dict key containing the time wf
    start_and_end_pulse: dict key 
        The data_dict key containing the start and end of the pulses
    Returns
    -------
    data_dict: dict
        The mutated dictionary with the wfm_secondary added.
    MODIFIES: wfm_secondary"""
    wfm_q = data_dict['wfm_q']
    start_and_end_pulse = data_dict['start_and_end_pulse']
    pos = wfm_q[start_and_end_pulse[2]:start_and_end_pulse[3]]
    neg = wfm_q[start_and_end_pulse[6]:start_and_end_pulse[7]] 
    wfm_secondary = np.concatenate((pos, neg)) #can argue if i should also put the actual voltage there or we use the same one for all four?
    data_dict['wfm_secondary'] = wfm_secondary
    return data_dict

def plot(data_dict) -> None:
    """
    Creates a plot similar to the one in the paper where you can see all 3 loops as well as final big loop.
    goal, use all piecewise ones in inset on the same plot like paper, and then a seperate plot for just the DWM 
    PV loop which is the final answer

    Requirements
    ------------
    wfm_q: dict key 
        The data_dict key containing the charge wf
    wfm_v: dict key
        The data_dict key containing the voltage wf
    start_and_end_pulse: dict key 
        The data_dict key containing the start and end of the pulses
    wfm_dwm: dict key
        The data_dict key containing the dwm wf
    wfm_primary: dict key
        The data_dict key containing the prmary wf
    wfm_secondary: dict key
        The data_dict key containing the secondary wf
    Returns
    -------
    None
    PLOT_AGAINST: None
    MODIFIES: None"""
    wfm_v = data_dict['wfm_v']
    wfm_dwm = data_dict['wfm_dwm']
    wfm_primary = data_dict['wfm_primary']
    wfm_secondary = data_dict['wfm_secondary']
    start_and_end_pulse = data_dict['start_and_end_pulse']
    wfm_v_small = data_dict['wfm_v_piecewise']
    fig, ax = plt.subplots()
    ax.set_title("DWM Method PV")
    ax.set_ylabel("Charge Q")
    ax.set_xlabel("Voltage (V)")
    ax.plot(wfm_v_small, wfm_dwm)

    fig1, ax1 = plt.subplots()
    ax1.set_title("Combined DWM, Primary, Secondary")
    ax1.set_ylabel("Charge Q")
    ax1.set_xlabel("Voltage (V)")
    ax1.plot(wfm_v_small, wfm_dwm, label='DWM')
    ax1.plot(wfm_v_small, wfm_primary, linestyle='-', label='Primary')
    ax1.plot(wfm_v_small, wfm_secondary, linestyle='--', label='Secondary')
    ax1.legend()



