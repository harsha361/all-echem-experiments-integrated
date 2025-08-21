#!/usr/bin/env python3
"""
PalmSens MethodSCRIPT example: simple Cyclic Voltammetry (CV) measurement

This example showcases how to run a Cyclic Voltammetry (CV) measurement on
a MethodSCRIPT capable PalmSens instrument, such as the EmStat Pico.

The following features are demonstrated in this example:
  - Connecting to the PalmSens instrument using the serial port.
  - Running a Cyclic Voltammetry (CV) measurement.
  - Receiving and interpreting the measurement data from the device.
  - Plotting the measurement data.

-------------------------------------------------------------------------------
Copyright (c) 2019-2021 PalmSens BV
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

   - Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.
   - Neither the name of PalmSens BV nor the names of its contributors
     may be used to endorse or promote products derived from this software
     without specific prior written permission.
   - This license does not release you from any requirement to obtain separate 
     licenses from 3rd party patent holders to use this software.
   - Use of the software either in source or binary form must be connected to, 
     run on or loaded to an PalmSens BV component.

DISCLAIMER: THIS SOFTWARE IS PROVIDED BY PALMSENS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

# Standard library imports
import datetime
import logging
import os.path
import sys
import shutil

# Third-party imports
import matplotlib.pyplot as plt

# Local imports
import palmsens.instrument
import palmsens.mscript
import palmsens.serial
import csv
import pandas as pd

###############################################################################
# Start of configuration
###############################################################################

# COM port of the device (None = auto detect).
DEVICE_PORT = 'COM15'  

# Location of MethodSCRIPT file to use.
MSCRIPT_FILE_PATH = 'scripts/Script_CV.mscr'

# Location of output files. Directory will be created if it does not exist.
OUTPUT_PATH_csv = 'output/cyclic_voltammetry_measurement/cv_csv_data'
OUTPUT_PATH_plot = 'output/cyclic_voltammetry_measurement/cv_plots_png'

###############################################################################
# End of configuration
###############################################################################

LOG = logging.getLogger(__name__)

def emstat_cv():
    """Run the example."""
    # Configure the logging.
    logging.basicConfig(level=logging.DEBUG, format='[%(module)s] %(message)s',
                        stream=sys.stdout)
    # Uncomment the following line to reduce the log level for our library.
    logging.getLogger('palmsens').setLevel(logging.INFO)
    # Disable excessive logging from matplotlib.
    logging.getLogger('matplotlib').setLevel(logging.INFO)

    port = DEVICE_PORT

    # Create and open serial connection to the device.
    with palmsens.serial.Serial(port, 1) as comm:
        device = palmsens.instrument.Instrument(comm)
        device_type = device.get_device_type()
        LOG.info('Connected to %s.', device_type)

        # Read and send the MethodSCRIPT file.
        LOG.info('Sending MethodSCRIPT.')
        device.send_script(MSCRIPT_FILE_PATH)

        # Read the result lines.
        LOG.info('Waiting for results.')
        result_lines = device.readlines_until_end()

    # Parse the result.
    curves = palmsens.mscript.parse_result_lines(result_lines)

    # Log the results.
    for curve in curves:
        for package in curve:
            LOG.info([str(value) for value in package])
            
    # Get the applied potentials (first column of each row)
    applied_potential = palmsens.mscript.get_values_by_column(curves, 0)
    # Get the measured currents (second column of each row)
    measured_current = palmsens.mscript.get_values_by_column(curves, 1)
            
    # Create a new data frame with the data
    data_file = pd.DataFrame({'Applied Potential(V)': applied_potential, 'Measured Current(A)': measured_current})
    now = datetime.datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M%S')
    data_file.to_csv(f'{OUTPUT_PATH_csv}/csv_data_CV_{now_string}.csv', index=False)

    # Plot the results.
    plt.figure(1)
    plt.plot(applied_potential, measured_current)
    plt.title('Voltammogram')
    plt.xlabel('Applied Potential (V)')
    plt.ylabel('Measured Current (A)')
    plt.grid(visible=True, which='major')
    plt.grid(visible=True, which='minor', color='b', linestyle='-', alpha=0.2)
    plt.minorticks_on()
    plt.savefig(f'{OUTPUT_PATH_plot}/plot_CV_{now_string}.png')
    #plt.show()

# Uncomment the following line to run the script directly
#emstat_cv()
