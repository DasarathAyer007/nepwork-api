import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # adjust if needed


def load_json(relative_path: str):
    file_path = PROJECT_ROOT / relative_path
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)
