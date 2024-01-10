'''
This is an even simple script which will simply autoscale the scope but will allow us to make our 
OWN arb wf. currently it just takes in a hard coded list
'''

from ekpy import control
from ekpy.control.instruments import keysightdsox3024a, keysight81150a
import numpy as np
import time
import matplotlib.pyplot as plt
from scipy import interpolate
import scipy.integrate as it


def pv_hysteresis_wf(initial_delay, freq, pulse_delay, voltage, qtimepoints=12):
	'''
	Modified from my original one to only return my time_arr thats been interpolated using good commands
	ayo this already interps the voltage array??? 
	'''
	#first build Qtime
	initial_delay = float(initial_delay)
	freq = float(freq)
	pulse_delay = float(pulse_delay)
	voltage = float(voltage)
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
	iteration_count = 10000 - 1
	for i in range(iteration_count):
		interp_time.append((i + 1) * (time_array[-1]/iteration_count))
	#note this was the same shit as doing like np.linearinterpolate or linspace with max being the last element

	#Now we make a voltage array
	voltage_array = voltage*np.array([0,0,1,-1,0,0,1,-1,0,0,-1,1,0,0,-1,1,0,0])
	temp = interpolate.interp1d(time_array, voltage_array)
	interp_voltage_array = temp(interp_time)
	#only thing we use from this is interp_voltage_array wtf
	return q_time, time_array, waveform_freq, interp_time, interp_voltage_array


rm = control.ResourceManager()
scope = rm.open_resource('USB0::0x0957::0x17A6::MY63080078::INSTR')
wavegen = rm.open_resource('GPIB0::8::INSTR')
time.sleep(3)

keysightdsox3024a.initialize(scope)

keysight81150a.initialize(wavegen)
keysight81150a.configure_impedance(wavegen, '1', source_impedance='50.0', load_impedance='1000000')

q_time_arr, time_array, waveform_freq, interp_time_arr, interp_voltage_array = pv_hysteresis_wf('0.0001', '10', '0.0001', '1')
keysight81150a.create_arb_wf(wavegen, interp_voltage_array)

keysight81150a.configure_arb_wf(wavegen, '1', 'VOLATILE', gain='2', freq='1000') #note should be volatile idk why, but sure and i need to create the wf
keysight81150a.enable_output(wavegen)

scope.write(":AUToscale")
time.sleep(3)

scope.write(":WAVeform:SOURce 1")
meta_data_v, time_v, wfm_v = keysightdsox3024a.query_wf(scope)
scope.write(":WAVeform:SOURce 2")
metadata_c, time_c, wfm_c = keysightdsox3024a.query_wf(scope)

mydata = [meta_data_v, time_v, wfm_v, metadata_c, time_c, wfm_c]

#NOW we want to get the charge and stuff and calulate the FE. going to copy paste from old code to see if it works :D

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

capacitor_area = 6.4e-9
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
print(q3, p3_length, index_arr, q1, q_time_arr) #taking last element for some reason
pv_p1 = np.concatenate((v1, q1 - max_min_div2(q1)))
pv_p2 = np.concatenate((v2, q2 - max_min_div2(q2)))
pv_p3 = np.concatenate((v3, q3 - max_min_div2(q3)))
pv_p4 = np.concatenate((v4, q4 - max_min_div2(q4)))
temporary = vneg - q_arr[4]
temp2 = vpos - q_arr[10] + temporary[-1]
temp_arr = np.concatenate((temporary, temp2))
pv_hyst = [np.concatenate([vneg, vpos]), [temp_arr - max_min_div2(temp_arr)]] #list of arrays!

plt.plot(time_v, wfm_v)
plt.title('Waveform')
plt.xlabel('Time (sec)')
plt.ylabel('Voltage (V)')
plt.show()