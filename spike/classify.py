#!/usr/bin/env python3
"""Ask Apple's on-device model every question about every sampled prompt.

One `fm respond` call per prompt and question, greedy, with the options
compiled into an enum schema. Resumable; results go to
spike/data/predictions.jsonl.
"""
import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

from common import DATA, append_jsonl, read_jsonl, registry


def schema_file(question, tmp: Path) -> Path:
    schema = {
        "type": "object",
        "title": "Answer",
        "required": ["label"],
        "x-order": ["label"],
        "additionalProperties": False,
        "properties": {"label": {"type": "string", "enum": list(question["options"])}},
    }
    path = tmp / f"{question['name']}.json"
    path.write_text(json.dumps(schema))
    return path


def instructions(context, question):
    options = "\n".join(f"- {name}: {desc}" for name, desc in question["options"].items())
    return f"{context}\n\n{question['question']}\nPick exactly one label:\n{options}"


def ask(prompt, question, schema: Path, context):
    started = time.monotonic()
    result = subprocess.run(
        [
            "fm", "respond", "--greedy", "--no-stream",
            "--schema", str(schema),
            "-i", instructions(context, question),
            f"<prompt>\n{prompt['text']}\n</prompt>",
        ],
        capture_output=True, text=True, timeout=60,
    )
    elapsed = round(time.monotonic() - started, 3)
    if result.returncode != 0:
        return {"error": result.stderr.strip()[:300], "seconds": elapsed}
    try:
        return {"label": json.loads(result.stdout)["label"], "seconds": elapsed}
    except (json.JSONDecodeError, KeyError):
        return {"error": f"bad output: {result.stdout[:200]}", "seconds": elapsed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="stop after this many prompts")
    args = parser.parse_args()

    reg = registry()
    out = DATA / "predictions.jsonl"
    done = {(r["id"], r["question"]) for r in read_jsonl(out) if "label" in r}
    prompts = read_jsonl(DATA / "prompts.jsonl")[: args.limit]

    with tempfile.TemporaryDirectory() as tmp:
        schemas = {q["name"]: schema_file(q, Path(tmp)) for q in reg["questions"]}
        for n, prompt in enumerate(prompts, 1):
            for question in reg["questions"]:
                if (prompt["id"], question["name"]) in done:
                    continue
                answer = ask(prompt, question, schemas[question["name"]], reg["context"])
                append_jsonl(out, {
                    "id": prompt["id"], "question": question["name"],
                    "registry_version": reg["version"], **answer,
                })
                shown = answer.get("label") or f"ERROR {answer['error']}"
                print(f"[{n}/{len(prompts)}] {prompt['id']} {question['name']:<15} {shown} ({answer['seconds']} s)")


if __name__ == "__main__":
    main()
