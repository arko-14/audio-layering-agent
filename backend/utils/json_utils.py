import json
from pathlib import Path
from typing import Any

def write_json(path: str, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

def read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))