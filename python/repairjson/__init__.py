from . import repairjson as _repairjson
from .repairjson import *


__doc__ = _repairjson.__doc__
if hasattr(_repairjson, "__all__"):
    __all__ = _repairjson.__all__
