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
def run_cyclic_voltammetry(
    port: str = "COM5",
    baudrate: int = 1,
    script_path: str = "scripts/Script_CyclicVoltammetry.mscr",
    output_path: str = "output/CyclicVoltammetry_measurement",
    simulate: bool = False
) -> tuple[str, float | None]:
    """
    Run a cyclic voltammetry experiment (PalmSens or simulate).
    Saves CSV + PNG. Returns (csv_path, avg_current_last_10 or None).
    """
    # Prepare output folders (uniform with CA)
    output_csv = os.path.join(output_path, "cyclic_voltammetry_csv_data")
    output_plot = os.path.join(output_path, "cyclic_voltammetry_plots_png")
    os.makedirs(output_csv, exist_ok=True)
    os.makedirs(output_plot, exist_ok=True)

    # Timestamped filenames
    now = datetime.datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M%S')
    csv_file_path = os.path.join(output_csv, f"CyclicVoltammetry_Data_{now_string}.csv")
    plot_file_path = os.path.join(output_plot, f"CyclicVoltammetry_Plot_{now_string}.png")

    # --- SIMULATION ---
    if simulate:
        LOG.info("⚠️ Running CV in simulation mode (no device).")
        applied_potential = [i * 0.01 for i in range(-100, 101)]  # -1.00 .. 1.00
        measured_current  = [0.000001 * (0.5*i) for i in range(len(applied_potential))]

    # --- REAL DEVICE ---
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
            LOG.error("❌ CV: communication error: %s", str(e))
            # still return a path so caller can see where it tried to write
            return csv_file_path, None

        curves = mscript.parse_result_lines(result_lines)
        if not curves:
            LOG.error("❌ CV: no valid curves parsed from device.")
            return csv_file_path, None

        # column 0 = E (V), column 1 = I (A) for CV
        applied_potential = mscript.get_values_by_column(curves, 0)
        measured_current  = mscript.get_values_by_column(curves, 1)

    # --- Save CSV (uniform headers) ---
    df = pd.DataFrame({
        "Applied Potential(V)": applied_potential,
        "Measured Current(A)":  measured_current
    })
    df.to_csv(csv_file_path, index=False)

    # --- Save Plot (uniform style) ---
    plt.figure()
    plt.plot(applied_potential, measured_current, label="Current (A)")
    plt.xlabel("Potential (V)")
    plt.ylabel("Current (A)")
    plt.title("Cyclic Voltammetry")
    plt.grid(True)
    plt.savefig(plot_file_path)
    plt.close()

    # --- Metric: average of last 10 current values (uniform with CA) ---
    avg_current = None
    if len(df) >= 10:
        avg_current = df["Measured Current(A)"].tail(10).mean()
        LOG.info("📊 CV avg of last 10 current values: %.4e A", avg_current)

    return csv_file_path, avg_current


def run_ocp(
    port: str = "COM5",
    baudrate: int = 1,
    script_path: str = "scripts/Script_OCP.mscr",
    output_path: str = "output/OCP_measurement",
    simulate: bool = False
) -> tuple[str, float | None]:
    """
    Run an open-circuit potential experiment (PalmSens or simulate).
    Saves CSV + PNG. Returns (csv_path, avg_potential_last_10 or None).
    """
    # Prepare output folders (uniform with CA)
    output_csv = os.path.join(output_path, "ocp_csv_data")
    output_plot = os.path.join(output_path, "ocp_plots_png")
    os.makedirs(output_csv, exist_ok=True)
    os.makedirs(output_plot, exist_ok=True)

    # Timestamped filenames
    now = datetime.datetime.now()
    now_string = now.strftime('%Y%m%d-%H%M%S')
    csv_file_path = os.path.join(output_csv, f"OCP_Data_{now_string}.csv")
    plot_file_path = os.path.join(output_plot, f"OCP_Plot_{now_string}.png")

    # --- SIMULATION ---
    if simulate:
        LOG.info("⚠️ Running OCP in simulation mode (no device).")
        applied_time       = list(range(60))              # 60 s
        measured_potential = [0.15 + i*1e-4 for i in applied_time]

    # --- REAL DEVICE ---
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
            LOG.error("❌ OCP: communication error: %s", str(e))
            return csv_file_path, None

        curves = mscript.parse_result_lines(result_lines)
        if not curves:
            LOG.error("❌ OCP: no valid curves parsed from device.")
            return csv_file_path, None

        # column 0 = time (s), column 1 = potential (V) for OCP
        applied_time       = mscript.get_values_by_column(curves, 0)
        measured_potential = mscript.get_values_by_column(curves, 1)

    # --- Save CSV (uniform headers) ---
    df = pd.DataFrame({
        "Applied time(s)":        applied_time,
        "Measured Potential(V)":  measured_potential
    })
    df.to_csv(csv_file_path, index=False)

    # --- Save Plot (uniform style) ---
    plt.figure()
    plt.plot(applied_time, measured_potential, label="Potential (V)")
    plt.xlabel("Time (s)")
    plt.ylabel("Potential (V)")
    plt.title("Open Circuit Potential")
    plt.grid(True)
    plt.savefig(plot_file_path)
    plt.close()

    # --- Metric: average of last 10 potential values (uniform metric) ---
    avg_potential = None
    if len(df) >= 10:
        avg_potential = df["Measured Potential(V)"].tail(10).mean()
        LOG.info("📊 OCP avg of last 10 potential values: %.6f V", avg_potential)

    return csv_file_path, avg_potential
