from pyiron_workflow import as_dataclass_node, as_function_node
from dataclasses import field
import os, time
from printer.printer_setup import check_printer, send_gcode

@as_function_node("selected_cells")
def CellSelector(
    cell_1: bool = True, cell_2: bool = True, cell_3: bool = True, cell_4: bool = True,
    cell_5: bool = True, cell_6: bool = True, cell_7: bool = True, cell_8: bool = True,
    cell_9: bool = True, cell_10: bool = True, cell_11: bool = True, cell_12: bool = True,
    cell_13: bool = True, cell_14: bool = True, cell_15: bool = True, cell_16: bool = True
):
    return [i for i, selected in enumerate([
        cell_1, cell_2, cell_3, cell_4,
        cell_5, cell_6, cell_7, cell_8,
        cell_9, cell_10, cell_11, cell_12,
        cell_13, cell_14, cell_15, cell_16
    ], start=1) if selected]

@as_dataclass_node
class ExperimentConfig:
    step_1: str = "Cyclic Voltammetry"
    step_2: str = "Open Circuit Potential"
    step_3: str = "Chronoamperometry"
    step_4: str = "Cyclic Voltammetry"
    step_5: str = "Open Circuit Potential"
    step_6: str = "Chronoamperometry"
    num_repeats: int = 1
    delta_cell: int = 2
    delta_repeat: int = 3
    setup_no: str = "Setup_1"
    selected_cells: list = field(default_factory=list)
    printer_port: str = "COM4"
    palmsens_port: str = "COM5"
    printer_baud: int = 115200
    palmsens_baud: int = 115200
    simulate: bool = True
    show_plot: bool = False

@as_function_node("ready", use_cache=False)
def printer_ready(config: ExperimentConfig.dataclass) -> bool:
    return check_printer(
        port=config.printer_port,
        baudrate=config.printer_baud,
        simulate=config.simulate,
        safe_park=True,
    )

@as_function_node("status", use_cache=False)
def MoveSanity(config):
    if hasattr(config, "__dict__"):
        config = config.__dict__
    selected_cells = config.get("selected_cells", [])
    port = config.get("printer_port", "COM4")
    baud = config.get("printer_baud", 115200)
    simulate = config.get("simulate", True)
    delay = config.get("delay_between", 1)
    print(f"[MoveSanity] Moving to {len(selected_cells)} selected cells...")
    step = 73
    safe_z = 45
    working_z = 25
    for cell in selected_cells:
        cell -= 1
        row, col = divmod(cell, 4)
        x = col * step
        y = row * step
        print(f"[MoveSanity] Cell {cell+1} → X{x} Y{y}")
        send_gcode(f"G1 Z{safe_z:.2f} F1500", port, baud, simulate)
        send_gcode(f"G1 X{x:.2f} Y{y:.2f} F3000", port, baud, simulate)
        send_gcode(f"G1 Z{working_z:.2f} F1500", port, baud, simulate)
        time.sleep(delay)
    send_gcode(f"G1 Z{safe_z:.2f} F1500", port, baud, simulate)
    return True



from pyiron_workflow import as_function_node
import os
from palmsens.palmsens_controller import PalmSensController

from pyiron_workflow import as_function_node
from palmsens.palmsens_controller import PalmSensController
import os

@as_function_node()
def MeasureExperiment(config: ExperimentConfig.dataclass):  # ✅ use dataclass type directly
    print("[MeasureExperiment] Starting with config:", config)

    ps = PalmSensController(port="COM4", simulate=False)

    for rep in range(config.num_repeats):
        print(f"[MeasureExperiment] Repetition {rep+1}/{config.num_repeats}")
        for cell in config.selected_cells:
            print(f"[MeasureExperiment] Measuring {cell}...")

            script_path = os.path.join("scripts", "Script_CV.mscr")
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Missing script: {script_path}")

            with open(script_path, "r") as f:
                method_script = f.read()

            result_csv = f"measurement_{cell}_rep{rep+1}.csv"
            ps.run_script(method_script=method_script, save_path=result_csv)
            print(f"[MeasureExperiment] Saved to {result_csv}")
# palmsens_single_node.py

from pyiron_workflow import as_function_node
from palmsens.serial import Serial
from palmsens.instrument import Instrument
from palmsens import mscript
import os, time, datetime, pandas as pd

from pyiron_workflow import as_function_node
from palmsens.serial import Serial
from palmsens.instrument import Instrument
from palmsens import mscript
import os, time, datetime, pandas as pd

from pyiron_workflow import as_function_node
from palmsens.serial import Serial
from palmsens.instrument import Instrument
from palmsens import mscript
import os, time, datetime, pandas as pd

@as_function_node("status", "csv_path")
def PalmSensRun(port: str = "COM5", script_path: str = "scripts/Script_Chronoamperometry.mscr"):
    """
    Minimal PalmSens test node with only one return statement (required by PyironFlow).
    """
    status = "Unknown error"
    csv_path = ""
    
    # Output file
    out_dir = os.path.join("output", "PalmSens_Test")
    os.makedirs(out_dir, exist_ok=True)
    now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    csv_path = os.path.join(out_dir, f"palmsens_{now_str}.csv")

    try:
        if not os.path.exists(script_path):
            status = "Script not found"
            pd.DataFrame([{"error": status}]).to_csv(csv_path, index=False)
        
        else:
            with Serial(port=port, timeout=1) as comm:
                device = Instrument(comm)
                try:
                    device.abort_and_sync()
                except Exception:
                    pass

                device.send_script(script_path)
                time.sleep(0.2)
                device.write("r\n")
                lines = device.readlines_until_end()

            curves = mscript.parse_result_lines(lines)
            rows = []
            for curve in curves:
                for pkg in curve:
                    m = {v.type.id: v.value for v in pkg}
                    rows.append({
                        "time_s":      m.get("eb"),
                        "potential_V": m.get("ab"),
                        "current_A":   m.get("ba"),
                    })

            if rows:
                pd.DataFrame(rows).to_csv(csv_path, index=False)
                status = "OK"
            else:
                # Fallback: write raw data if parsing failed
                with open(csv_path, "w") as f:
                    f.write("\n".join([l.strip() for l in lines]))
                status = "No parsed data"

    except Exception as e:
        status = f"Error: {str(e)}"
        pd.DataFrame([{"error": status}]).to_csv(csv_path, index=False)

    # ✅ Single return path
    return status, csv_path
from pyiron_workflow import as_function_node

from palmsens.palmsens_controller import run_chronoamperometry

@as_function_node("measurement_results")
def RunElectrochemistry(config):
    """
    Generalized green node to run electrochemical measurements (currently chronoamperometry).
    Reads all parameters from the purple config node.
    """
    csv_file_path, avg_current = run_chronoamperometry(
        port=config.palmsens_port,
        baudrate=config.palmsens_baud,
        script_path="scripts/Script_Chronoamperometry.mscr",  # Fixed for now
        output_path=f"output/{config.setup_no}/Chronoamperometry_measurement",
        simulate=config.simulate
    )

    return {
        "csv_file_path": csv_file_path,
        "avg_current": avg_current
    }
from pyiron_workflow import as_function_node
from palmsens.palmsens_controller import run_chronoamperometry
from printer.printer_setup import send_gcode
import time
import os

@as_function_node("measurement_data", use_cache=False)
def RunMeasurementLoop(config):
    if hasattr(config, "__dict__"):
        config = config.__dict__

    selected_cells = config.get("selected_cells", [])
    port = config.get("printer_port", "COM4")
    baud = config.get("printer_baud", 115200)
    palmsens_port = config.get("palmsens_port", "COM5")
    palmsens_baud = config.get("palmsens_baud", 115200)
    simulate = config.get("simulate", True)
    setup_no = config.get("setup_no", "Setup_1")
    delta = config.get("delta_repeat", 3)

    csv_paths = []
    avg_currents = []

    step = 73
    safe_z = 45
    working_z = 25

    for cell in selected_cells:
        print(f"🔁 Measuring Cell {cell}")
        cell -= 1
        row, col = divmod(cell, 4)
        x = col * step
        y = row * step

        send_gcode(f"G1 Z{safe_z:.2f} F1500", port, baud, simulate)
        send_gcode(f"G1 X{x:.2f} Y{y:.2f} F3000", port, baud, simulate)
        send_gcode(f"G1 Z{working_z:.2f} F1500", port, baud, simulate)

        time.sleep(1)

        csv_path, avg_current = run_chronoamperometry(
            port=palmsens_port,
            baudrate=palmsens_baud,
            script_path="scripts/Script_Chronoamperometry.mscr",
            output_path=os.path.join("output", setup_no, f"cell_{cell+1:02}"),
            simulate=simulate
        )

        csv_paths.append(csv_path)
        avg_currents.append(avg_current)

        send_gcode(f"G1 Z{safe_z:.2f} F1500", port, baud, simulate)
        time.sleep(delta)

    return {
        "csv_file_paths": csv_paths,
        "avg_currents": avg_currents
    }
# pyiron_nodes/sample_printer_mover.py

# pyiron_nodes/sample_printer_mover.py
# pyiron_nodes/printer_jog_control.py

# pyiron_nodes/sample_printer_mover.py

# pyiron_nodes/sample_printer_mover.py

from pyiron_workflow import as_function_node
import ipywidgets as widgets
import serial

def send_gcode(gcode: str, port: str = "COM4", baudrate: int = 115200):
    """Send raw G-code to the printer via serial."""
    try:
        with serial.Serial(port, baudrate, timeout=2) as ser:
            ser.write((gcode + "\n").encode())
            ser.flush()
    except Exception as e:
        print("Error sending G-code:", e)

  # real device sender

from pyiron_workflow import as_function_node
import ipywidgets as widgets
from printer.printer_setup import send_gcode

@as_function_node("ui_panel", use_cache=False)
def SamplePrinterMover(
    port: str = "COM4",
    speed: int = 2000,
    default_x: float = 0.0, default_y: float = 0.0, default_z: float = 0.0,
    x_step: float = 1.0, y_step: float = 1.0, z_step: float = 0.5,
    safe_x: float = 0.0, safe_y: float = 220.0, safe_z: float = 150.0,
):
    # Absolute move inputs
    x_in = widgets.FloatText(value=default_x, description="X:")
    y_in = widgets.FloatText(value=default_y, description="Y:")
    z_in = widgets.FloatText(value=default_z, description="Z:")
    speed_in = widgets.IntText(value=speed, description="Speed:")

    # Per-axis jog increments
    xstep_in = widgets.FloatText(value=x_step, description="ΔX:")
    ystep_in = widgets.FloatText(value=y_step, description="ΔY:")
    zstep_in = widgets.FloatText(value=z_step, description="ΔZ:")

    # Presets
    defx_in = widgets.FloatText(value=default_x, description="Def X:")
    defy_in = widgets.FloatText(value=default_y, description="Def Y:")
    defz_in = widgets.FloatText(value=default_z, description="Def Z:")
    safx_in = widgets.FloatText(value=safe_x, description="Safe X:")
    safy_in = widgets.FloatText(value=safe_y, description="Safe Y:")
    safz_in = widgets.FloatText(value=safe_z, description="Safe Z:")

    # Action buttons
    home_btn   = widgets.Button(description="Home (G28)", button_style="info")
    move_btn   = widgets.Button(description="Move to X/Y/Z", button_style="success")
    default_btn= widgets.Button(description="Go Default", button_style="success")
    safe_btn   = widgets.Button(description="Go Safe Park", button_style="warning")

    # Jog buttons
    jog_xm = widgets.Button(description="X-"); jog_xp = widgets.Button(description="X+")
    jog_ym = widgets.Button(description="Y-"); jog_yp = widgets.Button(description="Y+")
    jog_zm = widgets.Button(description="Z-"); jog_zp = widgets.Button(description="Z+")

    # Safety buttons
    quick_btn  = widgets.Button(description="Quick Stop (M410)", button_style="warning")
    kill_btn   = widgets.Button(description="EMERGENCY STOP (M112)", button_style="danger")
    motors_btn = widgets.Button(description="Motors OFF (M18)")
    reset_btn  = widgets.Button(description="Reset FW (M999)", button_style="info")

    note = widgets.HTML(
        "<b>⚠ Safety:</b> <i>M112</i> halts immediately and puts firmware in alarm; "
        "send <i>M999</i> (Reset) then <i>G28</i> (Home) before moving again."
    )

    out = widgets.Output(layout={"border": "1px solid #ccc", "max_height": "200px", "overflow": "auto"})

    def send(g: str):
        with out: print("→", g)
        send_gcode(g, port=port, baudrate=115200, simulate=False)

    # Handlers
    def on_move(_):   send("G90"); send("G21"); send(f"G1 X{x_in.value} Y{y_in.value} Z{z_in.value} F{speed_in.value}")
    def on_home(_):   send("G90"); send("G21"); send("G28")
    def on_default(_):
        send("G90"); send("G21")
        send(f"G1 Z{max(defz_in.value, safz_in.value)} F{speed_in.value}")
        send(f"G1 X{defx_in.value} Y{defy_in.value} F{speed_in.value}")
        send(f"G1 Z{defz_in.value} F{speed_in.value}")
    def on_safe(_):
        send("G90"); send("G21")
        send(f"G1 Z{safz_in.value} F{speed_in.value}")
        send(f"G1 X{safx_in.value} Y{safy_in.value} F{speed_in.value}")

    def jog(dx=0, dy=0, dz=0):
        send("G91")
        parts = []
        if dx: parts.append(f"X{dx}")
        if dy: parts.append(f"Y{dy}")
        if dz: parts.append(f"Z{dz}")
        if parts: send("G1 " + " ".join(parts) + f" F{speed_in.value}")
        send("G90")

    # Safety handlers
    def on_quick(_):  send("M410")
    def on_kill(_):   send("M112")
    def on_motors(_): send("M18")
    def on_reset(_):  send("M999")

    # Bind
    move_btn.on_click(on_move); home_btn.on_click(on_home)
    default_btn.on_click(on_default); safe_btn.on_click(on_safe)
    jog_xm.on_click(lambda _: jog(dx=-xstep_in.value)); jog_xp.on_click(lambda _: jog(dx=+xstep_in.value))
    jog_ym.on_click(lambda _: jog(dy=-ystep_in.value)); jog_yp.on_click(lambda _: jog(dy=+ystep_in.value))
    jog_zm.on_click(lambda _: jog(dz=-zstep_in.value)); jog_zp.on_click(lambda _: jog(dz=+zstep_in.value))
    quick_btn.on_click(on_quick); kill_btn.on_click(on_kill)
    motors_btn.on_click(on_motors); reset_btn.on_click(on_reset)

    panel = widgets.VBox([
        widgets.HTML("<b>Manual Printer Control</b>"),
        widgets.HBox([x_in, y_in, z_in, speed_in]),
        widgets.HBox([xstep_in, ystep_in, zstep_in]),
        widgets.HBox([move_btn, home_btn]),
        widgets.HBox([jog_xm, jog_xp, jog_ym, jog_yp, jog_zm, jog_zp]),
        widgets.HTML("<hr/>"),
        widgets.HBox([quick_btn, kill_btn, motors_btn, reset_btn]),
        note,
        widgets.HTML("<hr/>"),
        widgets.HTML("<b>Presets</b>"),
        widgets.HBox([defx_in, defy_in, defz_in, default_btn]),
        widgets.HBox([safx_in, safy_in, safz_in, safe_btn]),
        out
    ])
    return panel
