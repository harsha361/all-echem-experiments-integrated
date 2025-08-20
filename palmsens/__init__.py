"""
PalmSens wrapper + MethodSCRIPT helpers.
"""
from .palmsens_controller import run_chronoamperometry, PalmSensController

# Optional re-exports if these modules exist in your package:
try:
    from .instrument import Instrument
    from .serial import Serial
    from . import mscript
except Exception:
    Instrument = None
    Serial = None
    mscript = None

__all__ = [
    "run_chronoamperometry",
    "PalmSensController",
    "Instrument",
    "Serial",
    "mscript",
]

__version__ = "0.1.0"
