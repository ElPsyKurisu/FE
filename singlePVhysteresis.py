import numpy as np
import time
import os
from ekpy.control import core
from ekpy.control.instruments import keysight81150a, keysightdsox3024a
from scipy import interpolate

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
		freq (str): Frequency, assumed in Hz unless a suffix is used (need to add logic)
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
    timescale = (np.float(initial_delay) + (np.float(pulse_delay) * 4) + (16 * np.float(freq) * 4000)) / 10
    voltage_channel_scale = np.float(v_end)/4
	#make sure that current scale >= 0.008
    setup_scope(scope, initial_delay, pulse_delay, freq, voltage_channel, current_channel, f'{voltage_channel_scale}', '0.008')

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
        keysightdsox3024a.setup_wf(scope, source='CHAN1')


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