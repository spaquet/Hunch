#!/usr/bin/env python3
"""Sample prompts from Claude Code history into spike/data/prompts.jsonl."""
import argparse
import hashlib
import json
import random
import re
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "data"
MAX_CHARS = 4000  # keeps prompt + schema well inside the 4,096-token window
PASTE_CACHE = Path.home() / ".claude/paste-cache"
PASTE_REF = re.compile(r"\[Pasted text #(\d+)[^\]]*\]")


def expand_pastes(entry):
    """Replace [Pasted text #N] with its content; None if any paste is gone."""
    pastes = entry.get("pastedContents") or {}

    def content(match):
        paste = pastes.get(match.group(1)) or {}
        if "content" in paste:
            return paste["content"]
        cached = PASTE_CACHE / f"{paste.get('contentHash')}.txt"
        if paste.get("contentHash") and cached.exists():
            return cached.read_text()
        raise LookupError

    try:
        return PASTE_REF.sub(content, entry.get("display") or "")
    except LookupError:
        return None


def load(history: Path):
    seen = set()
    for line in history.open():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = (expand_pastes(entry) or "").strip()
        if text.startswith(("/", "!", "#")) or len(text) < 15:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        yield {
            "id": hashlib.sha1(text.encode()).hexdigest()[:10],
            "project": Path(entry.get("project") or "unknown").name,
            "text": text[:MAX_CHARS],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, default=Path.home() / ".claude/history.jsonl")
    parser.add_argument("-n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    by_project = defaultdict(list)
    for prompt in load(args.history):
        by_project[prompt["project"]].append(prompt)

    # Round-robin across projects so one busy repo does not dominate the set.
    rng = random.Random(args.seed)
    for prompts in by_project.values():
        rng.shuffle(prompts)
    sample = []
    while len(sample) < args.n and any(by_project.values()):
        for project in sorted(by_project):
            if by_project[project] and len(sample) < args.n:
                sample.append(by_project[project].pop())
    rng.shuffle(sample)

    DATA.mkdir(exist_ok=True)
    out = DATA / "prompts.jsonl"
    with out.open("w") as f:
        for prompt in sample:
            f.write(json.dumps(prompt) + "\n")
    projects = len({p["project"] for p in sample})
    print(f"wrote {len(sample)} prompts from {projects} projects to {out}")


if __name__ == "__main__":
    main()
