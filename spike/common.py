import json
from pathlib import Path

from systemone import labels_for

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def registry():
    return json.loads((ROOT / "questions.json").read_text())


def options(question):
    """Label -> description, for every question type (noul: true/false)."""
    return labels_for(question)


def predicted_label(answer):
    """The single label an answer stands for: the choice, or true/false for noul."""
    if "error" in answer:
        return None
    if answer["type"] == "noul":
        return "true" if answer["noul"] >= 0.5 else "false"
    if answer["type"] == "score":
        return answer["legend"][str(round(answer["score"]))]
    return answer["choice"]


def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.open() if line.strip()]


def append_jsonl(path: Path, record: dict):
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")
