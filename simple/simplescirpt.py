'''
This is an even simple script which will simply autoscale the scope
'''

from ekpy import control
from ekpy.control.instruments import keysightdsox3024a, keysight81150a
import numpy as np
import time
import matplotlib.pyplot as plt


rm = control.ResourceManager()
scope = rm.open_resource('USB0::0x0957::0x17A6::MY63080078::INSTR')
wavegen = rm.open_resource('GPIB0::8::INSTR')
time.sleep(3)

keysightdsox3024a.initialize(scope)

keysight81150a.initialize(wavegen)
keysight81150a.configure_impedance(wavegen, '1', source_impedance='50.0', load_impedance='1000000')
keysight81150a.configure_arb_waveform(wavegen, '1', 'PV', gain='2', freq='1000') #note should be volatile idk why, but sure and i need to create the wf
keysight81150a.enable_output(wavegen)

scope.write(":AUToscale")
time.sleep(3)

scope.write(":WAVeform:SOURce 1")
meta_data_v, time_v, wfm_v = keysightdsox3024a.query_wf(scope)
scope.write(":WAVeform:SOURce 2")
meta_data_c, time_c, wfm_c = keysightdsox3024a.query_wf(scope)

mydata = [meta_data_v, time_v, wfm_v, meta_data_c, time_c, wfm_c]

plt.plot(time_v, wfm_v)
plt.title('Waveform')
plt.xlabel('Time (sec)')
plt.ylabel('Voltage (V)')
plt.show()