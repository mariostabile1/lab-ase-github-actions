import json
from pathlib import Path

LAST_FILE = Path("data/last.json")


def save_last(operation):
    LAST_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_FILE.write_text(json.dumps(operation, indent=2), encoding="utf-8")


def load_last():
    if not LAST_FILE.exists():
        return None
    return json.loads(LAST_FILE.read_text(encoding="utf-8"))
