import numpy as np
import time
import os
from ekpy.control import core
from ekpy.control.instruments import keysight81150a, keysightdsox3024a
from scipy import interpolate
import scipy.integrate as it
import pandas as pd
from ekpy.control import plotting
import matplotlib.pyplot as plt

"""
This program is used to generate a dataset on a FE sample to then calculate IV Curve. It works by sending in a series of triangle pulses
and then meauring the current and the voltage across the capacitor sample. Connect channel 1 of the wavegen to channel 1 of the scope, and connect
channel 2 of the wavegen in parallel with the sample which is in series with channel 2 of the scope. AKA connect channel 2 of the wavegen to port A via
BNC and connect channel 2 of the scope to port B also via BNC (no bannannas needed)
"""