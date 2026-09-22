"""Repair common malformed JSON with a Rust parser.

See https://github.com/kyle-mirich/repairjson for repair rules and limitations.
"""

from .repairjson import MAX_DEPTH, __version__, loads, repair, repair_json, repair_to_string

__all__ = ["MAX_DEPTH", "__version__", "loads", "repair", "repair_json", "repair_to_string"]
