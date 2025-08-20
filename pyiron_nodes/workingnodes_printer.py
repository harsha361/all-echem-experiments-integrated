
# pyiron_nodes/workingnodes_printer.py
from pyiron_workflow import as_dataclass_node, as_function_node
from dataclasses import field
import os, time

# --- printer & palmsens helpers ---
from printer.printer_setup import check_printer, send_gcode
from palmsens.palmsens_controller import run_chronoamperometry

# ========== Basic selector & config ==========


@as_function_node("selected_cells")
def CellSelector(
    cell_1: bool = True, cell_2: bool = True, cell_3: bool = True, cell_4: bool = True,
    cell_5: bool = True, cell_6: bool = True, cell_7: bool = True, cell_8: bool = True,
    cell_9: bool = True, cell_10: bool = True, cell_11: bool = True, cell_12: bool = True,
    cell_13: bool = True, cell_14: bool = True, cell_15: bool = True, cell_16: bool = True
):
    """Return list of selected cell indices (1..16)."""
    flags = [
        cell_1, cell_2, cell_3, cell_4,
        cell_5, cell_6, cell_7, cell_8,
        cell_9, cell_10, cell_11, cell_12,
        cell_13, cell_14, cell_15, cell_16
    ]
    return [i for i, sel in enumerate(flags, start=1) if sel]




@as_dataclass_node
class ExperimentConfig:
    # future method plan – currently we only run Chronoamperometry
    step_1: str = "Cyclic Voltammetry"
    step_2: str = "Open Circuit Potential"
    step_3: str = "Chronoamperometry"
    step_4: str = "Cyclic Voltammetry"
    step_5: str = "Open Circuit Potential"
    step_6: str = "Chronoamperometry"

    num_repeats: int = 1
    delta_cell: int = 2          # delay between cells (s)
    delta_repeat: int = 3        # delay between repeats (s)
    setup_no: str = "Setup_1"

    selected_cells: list = field(default_factory=list)

    printer_port: str = "COM4"
    palmsens_port: str = "COM5"
    printer_baud: int = 115200
    palmsens_baud: int = 115200

    simulate: bool = True
    show_plot: bool = False


# ========== Utility nodes ==========

@as_function_node("ready", use_cache=False)
def printer_ready(config: ExperimentConfig.dataclass) -> bool:
    """Check printer connectivity; optionally safe-park."""
    return check_printer(
        port=config.printer_port,
        baudrate=config.printer_baud,
        simulate=config.simulate,
        safe_park=True,
    )


# Legacy simple mover (kept for convenience)
@as_function_node("status", use_cache=False)
def MoveSanity(config):
    """
    Move across all selected cells (no measurement).
    Legacy/simple mover kept on request.
    """
    if hasattr(config, "__dict__"):
        config = config.__dict__

    selected_cells = config.get("selected_cells", [])
    port = config.get("printer_port", "COM4")
    baud = config.get("printer_baud", 115200)
    simulate = config.get("simulate", True)
    # support both keys; prefer explicit delay_between if present
    delay = config.get("delay_between", config.get("delta_cell", 1))

    print(f"[MoveSanity] Moving to {len(selected_cells)} selected cells...")

    STEP = 73     # mm pitch between cells
    SAFE_Z = 45   # mm
    WORK_Z = 25   # mm

    for cell in selected_cells:
        ci = cell - 1
        row, col = divmod(ci, 4)
        x = col * STEP
        y = row * STEP
        print(f"[MoveSanity] Cell {cell} → X{x} Y{y}")
        send_gcode(f"G1 Z{SAFE_Z:.2f} F1500", port, baud, simulate)
        send_gcode(f"G1 X{x:.2f} Y{y:.2f} F3000", port, baud, simulate)
        send_gcode(f"G1 Z{WORK_Z:.2f} F1500", port, baud, simulate)
        time.sleep(delay)

    send_gcode(f"G1 Z{SAFE_Z:.2f} F1500", port, baud, simulate)
    return True


# ========== Measurement nodes ==========

@as_function_node("measurement_results", use_cache=False)
def RunElectrochemistry(config: ExperimentConfig.dataclass):
    """
    Single CA run using PalmSens wrapper (no printer movement).
    """
    csv_file_path, avg_current = run_chronoamperometry(
        port=config.palmsens_port,
        baudrate=config.palmsens_baud,
        script_path="scripts/Script_Chronoamperometry.mscr",
        output_path=os.path.join("output", config.setup_no, "Chronoamperometry_measurement"),
        simulate=config.simulate,
    )
    return {"csv_file_path": csv_file_path, "avg_current": avg_current}



@as_function_node("measurement_data", use_cache=False)
def RunMeasurementLoop(config):
    """
    Integrated loop: for each selected cell
      - move printer → run chronoamperometry → save CSV
    Uses PalmSens wrapper; returns all CSV paths and averages.
    """
    if hasattr(config, "__dict__"):
        config = config.__dict__

    selected_cells = config.get("selected_cells", [])
    port = config.get("printer_port", "COM4")
    baud = config.get("printer_baud", 115200)
    palmsens_port = config.get("palmsens_port", "COM5")
    palmsens_baud = config.get("palmsens_baud", 115200)
    simulate = config.get("simulate", True)
    setup_no = config.get("setup_no", "Setup_1")
    delay_between_cells = config.get("delta_cell", 2)

    STEP = 73
    SAFE_Z = 45
    WORK_Z = 25

    csv_paths, avg_currents = [], []

    for cell in selected_cells:
        print(f"[RunMeasurementLoop] Cell {cell}")
        ci = cell - 1
        row, col = divmod(ci, 4)
        x = col * STEP
        y = row * STEP

        # move
        send_gcode(f"G1 Z{SAFE_Z:.2f} F1500", port, baud, simulate)
        send_gcode(f"G1 X{x:.2f} Y{y:.2f} F3000", port, baud, simulate)
        send_gcode(f"G1 Z{WORK_Z:.2f} F1500", port, baud, simulate)
        time.sleep(1)

        # measure
        out_dir = os.path.join("output", setup_no, f"cell_{cell:02}")
        csv_path, avg_current = run_chronoamperometry(
            port=palmsens_port,
            baudrate=palmsens_baud,
            script_path="scripts/Script_Chronoamperometry.mscr",
            output_path=out_dir,
            simulate=simulate,
        )
        csv_paths.append(csv_path)
        avg_currents.append(avg_current)

        # retract & pause
        send_gcode(f"G1 Z{SAFE_Z:.2f} F1500", port, baud, simulate)
        time.sleep(delay_between_cells)

    return {"csv_file_paths": csv_paths, "avg_currents": avg_currents}



# ========== Manual printer control (GUI panel node) ==========

import ipywidgets as widgets  # GUI
@as_function_node("ui_panel", use_cache=False)
def SamplePrinterMover(
    port: str = "COM4",
    speed: int = 2000,
    # absolute move defaults
    default_x: float = 0.0, default_y: float = 0.0, default_z: float = 0.0,
    # per-axis jog increments
    x_step: float = 1.0, y_step: float = 1.0, z_step: float = 0.5,
    # safe/default presets
    safe_x: float = 0.0, safe_y: float = 220.0, safe_z: float = 150.0,
):
    import ipywidgets as widgets
    import serial
    import re

    # absolute inputs
    x_in = widgets.FloatText(value=default_x, description="X:")
    y_in = widgets.FloatText(value=default_y, description="Y:")
    z_in = widgets.FloatText(value=default_z, description="Z:")
    speed_in = widgets.IntText(value=speed, description="Speed:")

    # jog increments
    xstep_in = widgets.FloatText(value=x_step, description="ΔX:")
    ystep_in = widgets.FloatText(value=y_step, description="ΔY:")
    zstep_in = widgets.FloatText(value=z_step, description="ΔZ:")

    # presets
    defx_in = widgets.FloatText(value=default_x, description="Def X:")
    defy_in = widgets.FloatText(value=default_y, description="Def Y:")
    defz_in = widgets.FloatText(value=default_z, description="Def Z:")
    safx_in = widgets.FloatText(value=safe_x, description="Safe X:")
    safy_in = widgets.FloatText(value=safe_y, description="Safe Y:")
    safz_in = widgets.FloatText(value=safe_z, description="Safe Z:")

    # buttons
    home_btn   = widgets.Button(description="Home (G28)", button_style="info")
    move_btn   = widgets.Button(description="Move to X/Y/Z", button_style="success")
    default_btn= widgets.Button(description="Go Default", button_style="success")
    safe_btn   = widgets.Button(description="Go Safe Park", button_style="warning")
    getpos_btn = widgets.Button(description="Get Position (M114)", button_style="primary")

    jog_xm = widgets.Button(description="X-"); jog_xp = widgets.Button(description="X+")
    jog_ym = widgets.Button(description="Y-"); jog_yp = widgets.Button(description="Y+")
    jog_zm = widgets.Button(description="Z-"); jog_zp = widgets.Button(description="Z+")

    quick_btn  = widgets.Button(description="Quick Stop (M410)", button_style="warning")
    kill_btn   = widgets.Button(description="EMERGENCY STOP (M112)", button_style="danger")
    motors_btn = widgets.Button(description="Motors OFF (M18)")
    reset_btn  = widgets.Button(description="Reset FW (M999)", button_style="info")

    note = widgets.HTML(
        "<b>⚠ Safety:</b> <i>M112</i> halts immediately and puts firmware in alarm; "
        "send <i>M999</i> (Reset) then <i>G28</i> (Home) before moving again."
    )
    out = widgets.Output(layout={"border": "1px solid #ccc", "max_height": "200px", "overflow": "auto"})

    def send(g: str, expect_response=False):
        with out:
            print("→", g)
            try:
                with serial.Serial(port, 115200, timeout=2) as ser:
                    ser.write((g + "\n").encode())
                    if expect_response:
                        while True:
                            line = ser.readline().decode().strip()
                            if line:
                                print("←", line)
                                if "X:" in line and "Y:" in line:
                                    # Try to parse coordinates
                                    match = re.search(r"X:([\d\.\-]+) Y:([\d\.\-]+) Z:([\d\.\-]+)", line)
                                    if match:
                                        x, y, z = match.groups()
                                        print(f"📍 Current Position → X={x}, Y={y}, Z={z}")
                                    break
            except Exception as e:
                print(f"⚠ Error: {e}")

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

    def on_getpos(_):
        send("M114", expect_response=True)

    # bind
    move_btn.on_click(on_move); home_btn.on_click(on_home)
    default_btn.on_click(on_default); safe_btn.on_click(on_safe)
    jog_xm.on_click(lambda _: jog(dx=-xstep_in.value)); jog_xp.on_click(lambda _: jog(dx=+xstep_in.value))
    jog_ym.on_click(lambda _: jog(dy=-ystep_in.value)); jog_yp.on_click(lambda _: jog(dy=+ystep_in.value))
    jog_zm.on_click(lambda _: jog(dz=-zstep_in.value)); jog_zp.on_click(lambda _: jog(dz=+zstep_in.value))
    quick_btn.on_click(lambda _: send("M410"))
    kill_btn.on_click(lambda _: send("M112"))
    motors_btn.on_click(lambda _: send("M18"))
    reset_btn.on_click(lambda _: send("M999"))
    getpos_btn.on_click(on_getpos)

    panel = widgets.VBox([
        widgets.HTML("<b>Manual Printer Control</b>"),
        widgets.HBox([x_in, y_in, z_in, speed_in]),
        widgets.HBox([xstep_in, ystep_in, zstep_in]),
        widgets.HBox([move_btn, home_btn, getpos_btn]),
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
