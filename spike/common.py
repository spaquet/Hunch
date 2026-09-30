import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def registry():
    return json.loads((ROOT / "questions.json").read_text())


def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open() if line.strip()]


def append_jsonl(path: Path, record: dict):
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
