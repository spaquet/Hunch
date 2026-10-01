#!/usr/bin/env python3
"""Ask every question about every sampled prompt through system_one on `fm serve`.

Resumable; results go to spike/data/predictions.jsonl, one line per prompt and
question, with the full Laya-shaped answer.
"""
import argparse
import time

from common import DATA, append_jsonl, predicted_label, read_jsonl, registry
from systemone import FmServe, ask


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fast", "vote"], default="fast")
    parser.add_argument("-k", type=int, default=5, help="samples per question in vote mode")
    parser.add_argument("--limit", type=int, help="stop after this many prompts")
    args = parser.parse_args()

    reg = registry()
    out = DATA / "predictions.jsonl"
    done = {(r["id"], r["question"], r["mode"]) for r in read_jsonl(out) if "error" not in r["answer"]}
    prompts = read_jsonl(DATA / "prompts.jsonl")[: args.limit]

    server = FmServe()
    server.ensure_running()
    try:
        for n, prompt in enumerate(prompts, 1):
            for name, question in reg["questions"].items():
                if (prompt["id"], name, args.mode) in done:
                    continue
                started = time.monotonic()
                answer, usage = ask(server, prompt["text"], question, mode=args.mode, k=args.k,
                                    context=reg["context"])
                seconds = round(time.monotonic() - started, 3)
                append_jsonl(out, {"id": prompt["id"], "question": name, "mode": args.mode,
                                   "registry_version": reg["version"], "answer": answer,
                                   "usage": usage, "seconds": seconds})
                shown = predicted_label(answer) or f"ERROR {answer['error']}"
                print(f"[{n}/{len(prompts)}] {prompt['id']} {name:<15} {shown} ({seconds} s)")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
