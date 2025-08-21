

import datetime
import logging
import os
import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import palmsens.instrument
import palmsens.mscript
import palmsens.serial

# Configuration
DEVICE_PORT = 'COM5'
MSCRIPT_FILE_PATH = 'E:\Decuments\Main2_Integration\scripts\Script_Chronoamperometry.mscr'
OUTPUT_PATH_csv = 'output/Chronoamperometry_measurement/chronoamperometry_csv_data'
OUTPUT_PATH_plot = 'output/Chronoamperometry_measurement/chronoamperometry_plots_png'

LOG = logging.getLogger(__name__)

def create_directories():
    os.makedirs(OUTPUT_PATH_csv, exist_ok=True)
    os.makedirs(OUTPUT_PATH_plot, exist_ok=True)

def emstat_chronoamperometry():
    logging.basicConfig(level=logging.DEBUG, format='[%(module)s] %(message)s', stream=sys.stdout)
    logging.getLogger('palmsens').setLevel(logging.INFO)
    logging.getLogger('matplotlib').setLevel(logging.INFO)

    port = DEVICE_PORT

    with palmsens.serial.Serial(port, 1) as comm:
        device = palmsens.instrument.Instrument(comm)
        device_type = device.get_device_type()
        LOG.info('Connected to %s.', device_type)

        LOG.info('Sending MethodSCRIPT.')
        device.send_script(MSCRIPT_FILE_PATH)

        LOG.info('Waiting for results.')
        result_lines = device.readlines_until_end()

    curves = palmsens.mscript.parse_result_lines(result_lines)
    applied_time = []
    measured_current = []
    if not curves:
        LOG.error('No curves parsed from the device data.')
        return None, None

    for curve in curves:
        for row in curve:
            if len(row) >= 2:
                applied_time.append(row[0].value)
                measured_current.append(row[2].value)
            else:
                LOG.warning(f"Skipping row with insufficient data: {row}")
            
    # applied_time = palmsens.mscript.get_values_by_column(curves, 0)
    # measured_current = palmsens.mscript.get_values_by_column(curves, 2)

    data_file = pd.DataFrame({'Applied time(s)': applied_time, 'Measured Current(A)': measured_current})
    now = datetime.datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M%S')
    csv_file_path = f'{OUTPUT_PATH_csv}/Chronoamperometry_Data_{now_string}.csv'
    data_file.to_csv(csv_file_path, index=False)

    plt.figure(1)
    plt.plot(applied_time, measured_current)
    plt.title('Chronoamperometry measurement')
    plt.xlabel('time(s)')
    plt.ylabel('measured Current (A)')
    plt.grid(visible=True, which='major')
    plt.grid(visible=True, which='minor', color='b', linestyle='-', alpha=0.2)
    plt.minorticks_on()
    plt.savefig(f'{OUTPUT_PATH_plot}/Chronoamperometry_Plot_{now_string}.png')

    # Compute average of the last 10 rows
    if len(data_file) >= 10:
        last_10_avg = data_file['Measured Current(A)'].tail(10).mean()
        average_row = pd.DataFrame({'Applied time(s)': ['Average'], 'Measured Current(A)': [last_10_avg]})
        data_file = pd.concat([data_file, average_row], ignore_index=True)
        data_file.to_csv(csv_file_path, index=False)
        return csv_file_path, last_10_avg
    else:
        LOG.warning('Not enough data to compute the average of the last 10 rows.')
        return csv_file_path, None

#emstat_chronoamperometry()


emstat_chronoamperometry()