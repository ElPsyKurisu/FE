import numpy as np
import time
import os
from ekpy.control import core
from ekpy.control.instruments import keysight81150a, keysightdsox3024a
from scipy import interpolate
import scipy.integrate as it
import pandas as pd

def pv_hysteresis_wf(initial_delay, freq, pulse_delay, voltage, qtimepoints=12):
	#first build Qtime
	initial_delay = np.float(initial_delay)
	freq = np.float(freq)
	pulse_delay = np.float(pulse_delay)
	voltage = np.float(voltage)
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
	iteration_count = 10000
	for i in range(iteration_count):
		interp_time.append((i + 1) * (time_array[-1]/iteration_count))
	#note this was the same shit as doing like np.linearinterpolate or linspace with max being the last element

	#Now we make a voltage array
	voltage_array = voltage*[0,1,-1,0,1,-1,0,-1,1,0,-1,1,0]
	temp = interpolate.interp1d(time_array, voltage_array)
	interp_voltage_array = temp(interp_time)
	#only thing we use from this is interp_voltage_array wtf
	return q_time, time_array, waveform_freq, interp_time, interp_voltage_array


def setup_scope(scope, initial_delay, pulse_delay, freq, voltage_channel, current_channel,
				voltage_scale, current_scale):
	#Note this is made copying from LabVIEW, current order of arguments do not make sense imo
    keysightdsox3024a.initialize(scope)
    time.sleep(1)
    timescale = (np.float(initial_delay) + (np.float(pulse_delay) * 4) + (16 * np.float(freq) * 4000)) / 10 #Taken from LabVIEW idk what it does really
    keysightdsox3024a.configure_timebase(scope, time_base_type='MAIN', reference='CENTer', scale=f'{timescale}', position=f'{timescale}') #WHY is position not at 0?? its wired in labivew to same as scale
    #configure the voltage channel
    keysightdsox3024a.configure_channel(voltage_channel, vertical_scale=voltage_scale, impedance='ONEM')
    time.sleep(1)
    #configure the current channel
    keysightdsox3024a.configure_channel(current_channel, vertical_scale=current_scale, impedance='FIFT')
    time.sleep(1)
    #configure the time scale for voltage channel
    keysightdsox3024a.configure_scale(scope, voltage_channel, timescale, voltage_scale)
	#Setup Trigger Settings
    keysightdsox3024a.configure_trigger_characteristics(scope, trigger_source='EXT', low_voltage_level='0.75', high_voltage_level='0.95', sweep='NORM')
    keysightdsox3024a.configure_trigger_edge(scope, trigger_source='EXT', input_coupling='DC')
	

def setup_wavegen(wavegen, voltage_channel, initial_delay, freq, pulse_delay, voltage):
    keysight81150a.reset(wavegen)
    time.sleep(0.5)
    keysight81150a.configure_impedance(wavegen, voltage_channel, source_impedance='50.0', load_impedance='1000000')
    keysight81150a.configure_trigger(wavegen, voltage_channel, source='MAN')
    keysight81150a.configure_output_amplifier(wavegen, voltage_channel)
    time.sleep(0.5)
    q_time_arr, time_arrray, waveform_freq, interp_time_arr, interp_voltage_array = pv_hysteresis_wf(initial_delay, freq, pulse_delay, voltage)
    keysight81150a.create_arbitrary_waveform(wavegen, interp_voltage_array, 'PV')
    keysight81150a.configure_arb_waveform(wavegen, voltage_channel, 'PV', gain=f'{voltage*2}', freq=f'{waveform_freq}')
    return q_time_arr

def find_index(some_array, some_value):
	'''
	Helper Function to return both the array index and the value associated with that index
	'''
	diff_array = np.abs(some_array - some_value)
	index_of_closest_value = np.argmin(diff_array)
	closest_value = some_array[index_of_closest_value]
	return index_of_closest_value, closest_value

def max_min_div2(arr):
	"""
	Helper function to simply do (max + min) /2 of an array
	"""
	return (np.max(arr) + np.min(arr))/2

def run_function(scope, wavegen, initial_delay, pulse_delay, freq, v_end, 
				 capacitor_area, thickness, permittivity, amplification, 
				 loop_count:str='1', voltage_channel:str='1', current_channel:str='2'):
    """Run function for FEHysteresis expirement. 
	
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
		permittivity (str): Dielectric constant, gets mulitplied by epsilon_0
		amplification (str): How much to amplify capacitor formula by
		loop_count (str): Number of steps aka how many times to loop through generating one hysteresis loop
	returns:
		(FE): Experiment
		
		
		notes:
		basicaly just calculate capacitance of sample from basic formula"""
    #First Initialize the Oscilloscope and setup for measurement
    capacitance = np.float(capacitor_area)*np.float(permittivity)*8.854e-12/np.float(thickness)
    current_chnnl_resolution = capacitance*50*np.float(amplification)
    if current_chnnl_resolution < 0.008:
        current_chnnl_resolution = 0.008
    timescale = (np.float(initial_delay) + (np.float(pulse_delay) * 4) + (16 * np.float(freq) * 4000)) / 10
    voltage_channel_scale = np.float(v_end)/4
	#make sure that current scale >= 0.008
    setup_scope(scope, initial_delay, pulse_delay, freq, voltage_channel, current_channel, f'{voltage_channel_scale}', f'{current_chnnl_resolution}')

    #Now we initialize the wavegen
    keysight81150a.initialize(wavegen)
	
    #Loop over the loop count
    voltage_step = np.float(v_end)/np.int(loop_count)
    for i in range(len(np.int(loop_count))):
        voltage = (i+1)*voltage_step
        #first we need to setup the wavegen
        q_time_arr = setup_wavegen(wavegen, voltage_channel, initial_delay, freq, pulse_delay, voltage)
        total_time = 0.004/np.float(freq) + (np.float(pulse_delay) * 4) + np.float(initial_delay)

		#NOW we actually take the data, send out the pulse and get the data, f labview for this part
		#First need to make sure the scope is ready to acquire
        keysightdsox3024a.setup_acquire(scope, type='NORM')
		#Now we need to enable the wavegen, then acquire the data
        keysight81150a.enable_output(wavegen)
        time.sleep(.1) #Note may need to digitize to ensure that I am getting the same stuff at the same time
        keysightdsox3024a.setup_wf(scope, source='CHAN1', points='1000')
        metadata_v, time_v, wfm_v = keysightdsox3024a.query_wf(scope)
        keysightdsox3024a.setup_wf(scope, source='CHAN2', points='1000')
        metadata_c, time_c, wfm_c = keysightdsox3024a.query_wf(scope)
        '''
		#Now we calculcate the offset in the waveforms sike this is useless i believe since my awesome command already scales it
        null_element_amount = len(wfm_c)/(total_time/np.float(initial_delay))
        null_sum_c = np.sum(wfm_c[:null_element_amount]) #truncates waveform to this many elements and sums elements
        offset_c = (null_sum_c/null_element_amount)*-1/50 #I have no idea what this is doing but okay'''
		#Now we need to integrate current to get charge Q
        wfm_q = it.cumulative_trapezoid(wfm_c, time_c, initial=metadata_c["x_origin"]) #not sure if this is correct, but makes sense since x_origin is t0
        q_arr = []
        index_arr = []
        nearest_value_arr = []
        scaled_cap = 100/capacitor_area
        wfm_q_scaled = wfm_q*scaled_cap
        for i in q_time_arr:
            index, closest_val = find_index(time_c - metadata_c['x_origin'], i)
            index_arr.append(index)
            nearest_value_arr.append(closest_val)
            q_arr.append(wfm_q_scaled[index])
        q_arr = np.array(q_arr) #convert to array to allow for subtracting
        index_arr = np.array(index_arr)
        nearest_value_arr = np.array(nearest_value_arr)
        #Now we want to calculate PV P1, PV P2, PV P3, PV P4, PV hysteresis
        p1_length = index_arr[2] - index_arr[0]
        p2_length = index_arr[5] - index_arr[3]
        p3_length = index_arr[8] - index_arr[6]
        p4_length = index_arr[11] - index_arr[9]
        pos_half_length = index_arr[11] - index_arr[10]
        neg_half_length = index_arr[5] - index_arr[4]
        #note v is not scaled but Q is for the next part
        q1 = wfm_q_scaled[0:p1_length]
        q2 = wfm_q_scaled[3:p2_length]
        q3 = wfm_q_scaled[6:p3_length]
        q4 = wfm_q_scaled[9:p4_length]
        qpos = wfm_q_scaled[10:pos_half_length]
        qneg = wfm_q_scaled[4:neg_half_length]
        v1 = wfm_v[0:p1_length]
        v2 = wfm_v[3:p2_length]
        v3 = wfm_v[6:p3_length]
        v4 = wfm_v[9:p4_length]
        vpos = wfm_v[10:pos_half_length]
        vneg = wfm_v[4:neg_half_length]
        pv_p1 = np.concatenate((v1, q1 - max_min_div2(q1)))
        pv_p2 = np.concatenate((v2, q2 - max_min_div2(q2)))
        pv_p3 = np.concatenate((v3, q3 - max_min_div2(q3)))
        pv_p4 = np.concatenate((v4, q4 - max_min_div2(q4)))
        temporary = vneg - q_arr[4]
        temp2 = vpos - q_arr[10] + temporary[-1]
        temp_arr = np.concatenate((temporary, temp2))
        pv_hyst = [np.concatenate([vneg, vpos]), [temp_arr - max_min_div2(temp_arr)]] #list of arrays!
		#All thats left do to is write all the data to files which is split into RAW and PV
		#TBH THIS WILL ERROR MOST LIKELY SINCE MY ARRAYS ARE OF DIFFERENT SIZES AND I AM CONCAT MIGHT NEED TO LIKE MAKE A COPY AND APPEND ETC
		#pv_hyst[0] is x to plot, and pv_hyst[1] is y to plot which is the data i wanna write
		#all data should be returned as a pandas df apparently ((str) base_name, (dict) meta_data, (pandas.dataframe) data) like so
		#so we should build metadata here, where I want it to be contained with both scan params, but also include entire scope meta_data
        exp_params_meta_data = {
			'capacitance':capacitance,
			'initial_delay': initial_delay,
			'pulse_delay': pulse_delay,
			'frequency': freq,
			'v_end': v_end,
			'amplification': amplification,
			'loop_count': loop_count,
		}
        meta_data = {'exp_params': exp_params_meta_data, 'scope_c': metadata_c, 'scope_v': metadata_v}
		#How to structure the data that comes out, its going to be in a pandas df, but how. Kind of want to make it nested with raw and pv but idk
        df_pv_hyst = pd.DataFrame(pv_hyst)
        df_pv_p = pd.DataFrame([pv_p1,pv_p2,pv_p3,pv_p4])
        df_raw = pd.DataFrame([time_v,wfm_v,time_c,wfm_c, wfm_q, wfm_q_scaled])
        df = pd.DataFrame([df_pv_hyst,df_pv_p,df_raw])
        """
        Note that the v_waveform is plotted raw, just how he gets it so I would plot basically what the scope gives me aka wfm_v vs time_v
		I(t) is also raw like we saw
		then Q(t) is also raw, aka not the scaled one we did so plot the wfm_q!
		"""

        base_name = 'fe_pv_'
        return base_name, meta_data, df

class FEHysteresis(core.experiment):
	"""Experiment class for running creating hysteresis loops of PV. 

	args:
		wavegen (pyvisa.resources.gpib.GPIBInstrument): Keysight 81150a
		scope (pyvisa.resources.gpib.GPIBInstrument): Keysight DSOX3024A
		run_function (function): Run function.

	returns:
		(FE): Experiment

	"""

	def __init__(self, wavegen, scope, run_function= run_function):
		super().__init__()
		self.run_function = run_function
		self.wavegen = wavegen
		self.scope = scope
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