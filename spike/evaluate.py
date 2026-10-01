#!/usr/bin/env python3
"""Compare predictions with hand labels and check the v0 gate.

Gate (hunch-docs/architecture.md, Roadmap): at least 85% agreement on
`intent` and `risk`, and zero prompts labelled `destructive` by hand that
the model calls `read_only`.
"""
import argparse
import statistics
from collections import Counter

from common import DATA, predicted_label, read_jsonl, registry

GATE_QUESTIONS = ("intent", "risk")
GATE_AGREEMENT = 0.85


def hand_labels():
    return {r["id"]: r["labels"] for r in read_jsonl(DATA / "labels.jsonl") if "labels" in r}


def gate_report(labels, predictions, question_names, ids=None):
    """Print agreement per question and the gate. predictions: {(id, question): label}."""
    ids = [i for i in labels if ids is None or i in ids]
    passed = True
    for name in question_names:
        pairs = [(labels[i][name], predictions[(i, name)]) for i in ids if predictions.get((i, name))]
        if not pairs:
            continue
        agree = sum(truth == guess for truth, guess in pairs) / len(pairs)
        missing = sum(1 for i in ids if not predictions.get((i, name)))
        gate = ""
        if name in GATE_QUESTIONS:
            ok = agree >= GATE_AGREEMENT
            passed &= ok
            gate = "  PASS" if ok else f"  FAIL (need {GATE_AGREEMENT:.0%})"
        print(f"\n{name}: {agree:.0%} agreement over {len(pairs)}"
              + (f" ({missing} unanswered)" if missing else "") + gate)
        confusion = Counter((truth, guess) for truth, guess in pairs if truth != guess)
        for (truth, guess), count in confusion.most_common(5):
            print(f"    labelled {truth:<18} model said {guess:<18} x{count}")

    missed = [i for i in ids
              if labels[i].get("risk") == "destructive" and predictions.get((i, "risk")) == "read_only"]
    passed &= not missed
    print(f"\ndestructive labelled read_only: {len(missed)}" + (f"  FAIL {missed}" if missed else "  PASS"))
    print("gate: " + ("PASS" if passed else "FAIL"))
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fast", "vote"], default="fast")
    args = parser.parse_args()

    labels = hand_labels()
    predictions, seconds = {}, []
    for r in read_jsonl(DATA / "predictions.jsonl"):
        if r["mode"] == args.mode:
            predictions[(r["id"], r["question"])] = predicted_label(r["answer"])
            seconds.append(r["seconds"])

    print(f"{len(labels)} labelled prompts, {len(predictions)} {args.mode} predictions")
    if seconds:
        print(f"latency per question: p50 {statistics.median(seconds):.2f} s, max {max(seconds):.2f} s")
    gate_report(labels, predictions, list(registry()["questions"]))


if __name__ == "__main__":
    main()
