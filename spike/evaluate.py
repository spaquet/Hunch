#!/usr/bin/env python3
"""Compare model predictions with hand labels and check the v0 gate.

Gate (hunch-docs/architecture.md, Roadmap): at least 85% agreement on
`intent` and `risk`, and zero prompts labelled `destructive` by hand that
the model calls `read_only`.
"""
import statistics
from collections import Counter

from common import DATA, read_jsonl, registry

GATE_QUESTIONS = ("intent", "risk")
GATE_AGREEMENT = 0.85


def main():
    reg = registry()
    labels = {r["id"]: r["labels"] for r in read_jsonl(DATA / "labels.jsonl") if "labels" in r}
    predictions = {}
    seconds = []
    for r in read_jsonl(DATA / "predictions.jsonl"):
        if "label" in r:
            predictions[(r["id"], r["question"])] = r["label"]
            seconds.append(r["seconds"])

    print(f"{len(labels)} labelled prompts, {len(predictions)} predictions")
    if seconds:
        print(f"latency per call: p50 {statistics.median(seconds):.2f} s, max {max(seconds):.2f} s")

    passed = True
    for question in reg["questions"]:
        name = question["name"]
        pairs = [(labels[i][name], predictions[(i, name)]) for i in labels if (i, name) in predictions]
        if not pairs:
            continue
        agree = sum(truth == guess for truth, guess in pairs) / len(pairs)
        gate = ""
        if name in GATE_QUESTIONS:
            ok = agree >= GATE_AGREEMENT
            passed &= ok
            gate = "  PASS" if ok else f"  FAIL (need {GATE_AGREEMENT:.0%})"
        print(f"\n{name}: {agree:.0%} agreement over {len(pairs)}{gate}")

        confusion = Counter((truth, guess) for truth, guess in pairs if truth != guess)
        for (truth, guess), count in confusion.most_common(8):
            print(f"    labelled {truth:<18} model said {guess:<18} x{count}")

    missed = [
        i for i in labels
        if labels[i].get("risk") == "destructive" and predictions.get((i, "risk")) == "read_only"
    ]
    passed &= not missed
    print(f"\ndestructive labelled read_only: {len(missed)}" + (f"  FAIL {missed}" if missed else "  PASS"))
    print("\nv0 gate: " + ("PASS" if passed else "FAIL"))


if __name__ == "__main__":
    main()
