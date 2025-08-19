'''# Internal init
from ._version import get_versions

# Set version of pyiron_base
__version__ = get_versions()["version"]

# Try importing frontend components
try:
    from .pyironflow import PyironFlow, GUILayout  # ⬅️ Add GUILayout here
except FileNotFoundError:
    print("WARNING: could not import PyironFlow or GUILayout. This likely means "
          "the JS sources are not built and we're in an environment only fetching the version.")
'''
from .pyironflow import PyironFlow, GUILayout


