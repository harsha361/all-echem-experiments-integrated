# palmsens_controller.py
'''
import os
import time
import logging
from palmsens.serial import Serial
from palmsens.instrument import Instrument
from palmsens import mscript

LOG = logging.getLogger(__name__)

class PalmSensController:
    def __init__(self, port="COM5", simulate=False):
        self.port = port
        self.simulate = simulate
        self.instrument = None
        self.serial = None

    def connect(self):
        if self.simulate:
            LOG.info("Simulating PalmSens connection.")
            return

        try:
            # Full serial settings to avoid Windows COM port issues
            self.serial = Serial(
                port=self.port,
                 # Try 9600 or 57600 if this fails
                
            )
            self.instrument = Instrument(self.serial)
            LOG.info(f"✅ Connected to PalmSens on {self.port}")
        except Exception as e:
            LOG.error(f"❌ Failed to connect to PalmSens on {self.port}: {e}")
            raise

    def run_measurement(self, cell_name="cell_1", script_path="scripts/Script_CV.mscr"):
        if self.simulate:
            LOG.info(f"[SIMULATION] Measuring {cell_name}...")
            time.sleep(0.5)
            return {
                "cell": cell_name,
                "status": "SIMULATED",
                "data": [[0, 0.1], [1, 0.2], [2, 0.3]]
            }

        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script file not found: {script_path}")

        LOG.info(f"Running measurement on {cell_name} using {script_path}")
        self.instrument.abort_and_sync()
        self.instrument.send_script(script_path)
        self.instrument.write("r\n")

        lines = self.instrument.readlines_until_end()
        curves = mscript.parse_result_lines(lines)
        values = mscript.get_values_by_column(curves, column=1)
        time_values = mscript.get_values_by_column(curves, column=0)

        return {
            "cell": cell_name,
            "status": "MEASURED",
            "data": list(zip(time_values, values))
        }
'''

import serial, time

class PalmSensController:
    def __init__(self, port="COM5", baudrate=230400, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        print(f"✅ Connected to PalmSens on {self.port}")

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("🔌 Disconnected PalmSens")

    def run_script(self, script_path):
        if not self.ser or not self.ser.is_open:
            raise Exception("Not connected")

        with open(script_path, "r") as f:
            lines = f.readlines()

        print(f"▶ Sending {len(lines)} lines from {script_path}")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):  # skip comments
                continue

            cmd = (line + "\n").encode("utf-8")
            self.ser.write(cmd)
            time.sleep(0.05)  # small delay

            resp = self.ser.readline().decode(errors="ignore").strip()
            if resp:
                print("📥", resp)

        print("✅ Script finished sending")


import os
import sys
import datetime
import logging
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from palmsens import instrument, mscript, serial

# Configure logger
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(module)s] %(message)s', stream=sys.stdout)


def run_chronoamperometry(
    port: str = "COM5",
    baudrate: int = 1,
    script_path: str = "scripts/Script_Chronoamperometry.mscr",
    output_path: str = "output/Chronoamperometry_measurement",
    simulate: bool = False
) -> tuple[str, float | None]:
    """
    Run a chronoamperometry experiment using a PalmSens device or simulate data.
    - Sends the MethodSCRIPT file
    - Collects time-current data
    - Saves CSV and PNG
    - Returns:
        - CSV file path
        - Average current of last 10 values (if available)
    """

    # Prepare output folders
    output_csv = os.path.join(output_path, "chronoamperometry_csv_data")
    output_plot = os.path.join(output_path, "chronoamperometry_plots_png")
    os.makedirs(output_csv, exist_ok=True)
    os.makedirs(output_plot, exist_ok=True)

    # Timestamp
    now = datetime.datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M%S')
    csv_file_path = os.path.join(output_csv, f"Chronoamperometry_Data_{now_string}.csv")
    plot_file_path = os.path.join(output_plot, f"Chronoamperometry_Plot_{now_string}.png")

    # --- SIMULATION MODE ---
    if simulate:
        LOG.info("⚠️ Running in simulation mode (no device).")
        applied_time = list(range(20))
        measured_current = [0.001 * (i + 1) for i in range(20)]

    # --- REAL DEVICE MODE ---
    else:
        LOG.info("🔌 Connecting to PalmSens on %s", port)
        try:
            with serial.Serial(port, baudrate) as comm:
                dev = instrument.Instrument(comm)
                dev_type = dev.get_device_type()
                LOG.info("✅ Connected to device: %s", dev_type)

                LOG.info("📤 Sending script: %s", script_path)
                dev.send_script(script_path)

                LOG.info("⏳ Waiting for device response...")
                result_lines = dev.readlines_until_end()
        except Exception as e:
            LOG.error("❌ Failed to communicate with PalmSens: %s", str(e))
            return csv_file_path, None

        curves = mscript.parse_result_lines(result_lines)
        if not curves:
            LOG.error("❌ No valid curves parsed from device.")
            return csv_file_path, None

        applied_time = []
        measured_current = []

        for curve in curves:
            for row in curve:
                if len(row) >= 3:
                    applied_time.append(row[0].value)
                    measured_current.append(row[2].value)
                else:
                    LOG.warning("⚠️ Skipping incomplete row: %s", row)

    # --- Save CSV ---
    df = pd.DataFrame({
        "Applied time(s)": applied_time,
        "Measured Current(A)": measured_current
    })
    df.to_csv(csv_file_path, index=False)

    # --- Save Plot ---
    plt.figure()
    plt.plot(applied_time, measured_current, label="Current (A)")
    plt.xlabel("Time (s)")
    plt.ylabel("Current (A)")
    plt.title("Chronoamperometry Measurement")
    plt.grid(True)
    plt.savefig(plot_file_path)
    plt.close()

    # --- Compute Average ---
    avg_current = None
    if len(df) >= 10:
        avg_current = df["Measured Current(A)"].tail(10).mean()
        LOG.info("📊 Average of last 10 current values: %.4e A", avg_current)

    return csv_file_path, avg_current

