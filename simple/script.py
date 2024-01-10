'''
Since it has been difficult pin-pointing the issue that has been occuring with the
program to generate the PE loop, let's use this program to ONLY get the data from the scope
including setting up the scope, sending the pulse (will not make a pulse just use the one 
saved on the wavegen) and writing the data to the computer
'''
from ekpy import control
from ekpy.control.instruments import keysightdsox3024a, keysight81150a
import numpy as np

'''
Step 0: Connect to the instruments
'''
rm = control.ResourceManager()
scope = rm.open_resource('USB0::0x0957::0x17A6::MY63080078::INSTR')
wavegen = rm.open_resource('GPIB0::8::INSTR')

'''
Step 1: Setup the scope:
'''

keysightdsox3024a.initialize(scope)
keysightdsox3024a.configure_timebase(scope, scale='5e-5') #This is a random number I picked
keysightdsox3024a.configure_channel(scope, channel='1', vertical_scale='0.25', impedance='ONEM')
keysightdsox3024a.configure_channel(scope, channel='2', vertical_scale='0.008', impedance='FIFT')
keysightdsox3024a.configure_scale(scope, channel='1', vertical_scale='') #All this does is set the timebase again aka scale, and then the vertical range
#NOTE HERE FOR ME TO TEST, THE CONFIGURE SCALE COMMAND IS USELESS IMO SINCE IT IS DONE BEFORE IN CONFIGURE CHANNEL AND NOTHING IS DIFFERENT, HOWEVER IT ADDS A 'V' IN THE COMMAND STRUCTURE
keysightdsox3024a.configure_trigger_characteristics(scope, trigger_source='EXT', low_voltage_level='0.75', high_voltage_level='0.95', sweep='NORM')
keysightdsox3024a.configure_trigger_edge(scope, trigger_source='EXT', input_coupling='DC')
'''
Step 2: Setup the wavegen
'''
keysight81150a.initialize(wavegen)
keysight81150a.configure_impedance(wavegen, '1', source_impedance='50.0', load_impedance='1000000')
keysight81150a.configure_trigger(wavegen, '1', source='MAN')
keysight81150a.configure_output_amplifier(wavegen, '1') #note this is the channel on the wavegen
#note we are just taking the waveform stored on the wavegen
keysight81150a.configure_arb_waveform(wavegen, '1', 'PV', gain='2', freq='1000')

'''
Step 2.5: Enable output? Makes more sense to start the wavegen before we send the DIG command
'''
keysight81150a.enable_output(wavegen)
'''
Step 3: Setup the scope to acquire once via dig
'''
keysightdsox3024a.initiate(scope)
'''
Step 4: Turn on the wavegen
'''
#skipped see above, also not sending the trig command since wtf are u trigging on??? oh bruh might need to connect the scope and wavegen via trig cable fuckkkkkk
'''
step 5: get the data
'''

'''
step 6 turn off instruments
'''