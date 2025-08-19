from pyiron_workflow import as_dataclass_node, as_function_node
from dataclasses import field
import os, time
from .printer_setup import check_printer, send_gcode

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

@as_function_node("status", "csv_path", "setup_no")
def MeasureExperiment(config):
    if hasattr(config, "__dict__"):
        config = config.__dict__
    return "Measurement complete", "/tmp/fake_data.csv", config.get("setup_no", 1)
