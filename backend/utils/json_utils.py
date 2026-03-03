"""
JSON Utility Functions
======================

Simple helpers for reading and writing JSON files with consistent
encoding and directory creation.
"""
import json
from pathlib import Path
from typing import Any


def write_json(path: str, obj: Any) -> None:
    """
    Write an object to a JSON file with pretty formatting.
    
    Creates parent directories if they don't exist.
    Uses UTF-8 encoding for consistent cross-platform behavior.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def read_json(path: str) -> Any:
    """
    Read and parse a JSON file.
    
    Returns:
        Parsed JSON as dict, list, or primitive type
    """
    return json.loads(Path(path).read_text(encoding="utf-8"))