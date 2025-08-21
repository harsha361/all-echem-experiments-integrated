

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
import pandas as pd

###############################################################################
# Start of configuration
###############################################################################

# COM port of the device (None = auto detect)
DEVICE_PORT = 'COM19'  

# Location of MethodSCRIPT file to use.
MSCRIPT_FILE_PATH = 'scripts/Script_OCP.mscr'

# Location of output files. Directory will be created if it does not exist.
OUTPUT_PATH_csv = 'output/OCP_measurement/ocp_csv_data'
OUTPUT_PATH_plot = 'output/OCP_measurement/ocp_plots_png'

###############################################################################
# End of configuration
###############################################################################

LOG = logging.getLogger(__name__)

def emstat_ocp():
    """Run the example"""
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
            
    # Get the applied times (first column of each row)
    applied_time = palmsens.mscript.get_values_by_column(curves, 0)
    # Get the measured potentials (second column of each row)
    measured_potential = palmsens.mscript.get_values_by_column(curves, 1)

    if len(measured_potential) > 0:
        ocp_value = measured_potential[-1]  # Assuming last value is the OCP value
    else:
        ocp_value = None
    
    # Create a new data frame with the data
    data_file = pd.DataFrame({'Applied time (seconds)': applied_time, 'Measured potential (V)': measured_potential})
    now = datetime.datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M%S')
    data_file.to_csv(f'{OUTPUT_PATH_csv}/csv_data_ocp_{now_string}.csv', index=False)
    
    # Plot the results.
    plt.figure(1)
    plt.plot(applied_time, measured_potential)
    plt.title('OCP Plot')
    plt.xlabel('Applied time (seconds)')
    plt.ylabel('Measured potential (V)')
    plt.grid(visible=True, which='major')
    plt.grid(visible=True, which='minor', color='b', linestyle='-', alpha=0.2)
    plt.minorticks_on()
    plt.savefig(f'{OUTPUT_PATH_plot}/plot_OCP_{now_string}.png')
    plt.close()
    return ocp_value

# Uncomment the following line to run the script directly
#emstat_ocp()
