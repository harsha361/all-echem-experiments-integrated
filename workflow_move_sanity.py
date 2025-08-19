import os, sys
from IPython.display import display
import ipywidgets as widgets
from pyiron_workflow import Workflow
from pyironflow import PyironFlow

current_dir = os.getcwd()
nodes_path = os.path.join(current_dir, '..', 'pyiron_nodes')
if nodes_path not in sys.path:
    sys.path.append(nodes_path)

from workingnodes_printer import (
    CellSelector,
    ExperimentConfig,
    MoveSanity,
)

wf = Workflow("cell_movement_test")
wf.cell_selector = CellSelector()
wf.config = ExperimentConfig()
wf.config.selected_cells = wf.cell_selector.outputs.selected_cells
wf.mover = MoveSanity(config=wf.config.outputs.dataclass)

pf = PyironFlow([wf], root_path="../pyiron_nodes", flow_widget_ratio=0.85)
pf.gui.layout = widgets.Layout(
    border='1px solid black',
    flex='1 1 auto',
    width='auto',
    height='700px',
    max_height='700px'
)
display(pf.gui)
