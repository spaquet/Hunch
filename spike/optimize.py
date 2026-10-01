#!/usr/bin/env python3
"""Optimization loop: pick a prompting variant per question, calibrate, test once.

1. Split the labelled prompts into train and test (saved, so it never moves).
2. Screen variants on train in fast mode:
     baseline   zero-shot
     static     one short example per label, drawn from train
     retrieval  the most similar train examples (TF-IDF); this also simulates the
                online feedback loop, where examples are the user's own overrides
3. Keep the best variant per question; run it in vote mode on train and test.
4. Fit calibration on train (top vote share -> observed accuracy) and report on
   test: agreement, the gate, calibration error, and accuracy when acting only
   above an act_probability threshold.

Every call is cached in spike/data/runs.jsonl, so the loop resumes where it stopped.
The question pack (variant, examples, calibration) goes to spike/data/pack.json.
"""
import argparse
import json
import math
import random
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from common import DATA, append_jsonl, options, predicted_label, read_jsonl, registry
from evaluate import gate_report, hand_labels
from systemone import FmServe, ask

RUNS = DATA / "runs.jsonl"
EXAMPLE_CHARS = 600  # keeps four examples inside the context budget
VARIANTS = ("baseline", "static", "retrieval")


# --- similarity, for retrieval -------------------------------------------------

def tokens(text):
    return re.findall(r"[a-z0-9_]+", text.lower())


class TfIdf:
    def __init__(self, docs: dict):
        self.ids = list(docs)
        df = Counter(t for text in docs.values() for t in set(tokens(text)))
        self.idf = {t: math.log(len(docs) / n) + 1 for t, n in df.items()}
        self.vectors = {i: self.vector(text) for i, text in docs.items()}

    def vector(self, text):
        counts = Counter(tokens(text))
        vec = {t: c * self.idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def nearest(self, text, n, exclude):
        query = self.vector(text)
        scored = [(sum(query.get(t, 0) * v for t, v in self.vectors[i].items()), i)
                  for i in self.ids if i != exclude]
        return [i for _, i in sorted(scored, reverse=True)[:n]]


# --- calibration -----------------------------------------------------------------

def fit_calibration(points):
    """points: [(top vote share, correct)]. Returns a monotone share -> accuracy table."""
    bins = {}
    for share, correct in points:
        hits, total = bins.get(share, (0, 0))
        bins[share] = (hits + correct, total + 1)
    # Laplace-smoothed accuracy per share, then pool adjacent violators to keep it monotone.
    blocks = [[(h + 1) / (t + 2), t, [s]] for s, (h, t) in sorted(bins.items())]
    merged = []
    for block in blocks:
        merged.append(block)
        while len(merged) > 1 and merged[-2][0] > merged[-1][0]:
            b = merged.pop()
            a = merged.pop()
            weight = a[1] + b[1]
            merged.append([(a[0] * a[1] + b[0] * b[1]) / weight, weight, a[2] + b[2]])
    return {str(s): round(acc, 4) for acc, _, shares in merged for s in shares}


def calibrated(table, share):
    nearest = min(table, key=lambda s: abs(float(s) - share))
    return table[nearest]


def calibration_error(points):
    """Expected calibration error over (predicted probability, correct) pairs."""
    bins = {}
    for p, correct in points:
        bins.setdefault(round(p, 1), []).append((p, correct))
    n = len(points)
    return sum(len(b) / n * abs(sum(p for p, _ in b) / len(b) - sum(c for _, c in b) / len(b))
               for b in bins.values())


# --- the loop --------------------------------------------------------------------

def split(ids, test_size, seed):
    path = DATA / "split.json"
    if path.exists():
        return json.loads(path.read_text())
    shuffled = sorted(ids)
    random.Random(seed).shuffle(shuffled)
    result = {"test": shuffled[:test_size], "train": shuffled[test_size:]}
    path.write_text(json.dumps(result, indent=1))
    return result


def static_examples(name, question, train, labels, texts):
    """Shortest train prompt per label: one example each, cheapest on context."""
    examples = []
    for label in options(question):
        candidates = [i for i in train if labels[i][name] == label]
        if candidates:
            best = min(candidates, key=lambda i: len(texts[i]))
            examples.append({"state": texts[best][:EXAMPLE_CHARS], "label": label})
    return examples


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--shots", type=int, default=4, help="examples per call for retrieval")
    parser.add_argument("-k", type=int, default=5, help="samples per question in vote mode")
    parser.add_argument("--threshold", type=float, default=0.8, help="act_probability needed to act")
    parser.add_argument("--screen-only", action="store_true", help="stop after screening variants")
    args = parser.parse_args()

    reg = registry()
    context, questions, version = reg["context"], reg["questions"], reg["version"]
    labels = hand_labels()
    texts = {p["id"]: p["text"] for p in read_jsonl(DATA / "prompts.jsonl") if p["id"] in labels}
    parts = split(list(texts), args.test_size, args.seed)
    train, test = parts["train"], parts["test"]
    index = TfIdf({i: texts[i] for i in train})
    print(f"train {len(train)}, test {len(test)}, registry v{version}")

    cache = {(r["variant"], r["question"], r["id"], r["mode"], r["registry_version"]): r["answer"]
             for r in read_jsonl(RUNS) if "error" not in r["answer"]}
    server = FmServe()
    server.ensure_running()

    def examples_for(variant, name, item):
        if variant == "static":
            return static_examples(name, questions[name], train, labels, texts)
        if variant == "retrieval":
            return [{"state": texts[i][:EXAMPLE_CHARS], "label": labels[i][name]}
                    for i in index.nearest(texts[item], args.shots, exclude=item)]
        return []

    def run(variant, name, item, mode):
        key = (variant, name, item, mode, version)
        if key not in cache:
            answer, _ = ask(server, texts[item], questions[name], mode=mode, k=args.k,
                            examples=examples_for(variant, name, item), context=context)
            append_jsonl(RUNS, {"variant": variant, "question": name, "id": item, "mode": mode,
                                "registry_version": version, "answer": answer})
            cache[key] = answer
        return cache[key]

    try:
        # Screen variants on train, fast mode.
        best = {}
        print("\nscreening on train (fast):")
        for name in questions:
            scores = {}
            for variant in VARIANTS:
                with ThreadPoolExecutor(2) as pool:
                    answers = list(pool.map(lambda i: run(variant, name, i, "fast"), train))
                pairs = [(labels[i][name], predicted_label(a)) for i, a in zip(train, answers)]
                scores[variant] = sum(t == g for t, g in pairs) / len(pairs)
            best[name] = max(scores, key=scores.get)
            print(f"  {name:<15} " + "  ".join(f"{v} {s:.0%}" for v, s in scores.items())
                  + f"  -> {best[name]}")
        if args.screen_only:
            return

        # Vote mode with the best variant; calibrate on train, report on test.
        pack = {"registry_version": version, "k": args.k, "questions": {}}
        test_predictions = {}
        print(f"\nvote mode (k={args.k}) with the best variant, calibrated on train, scored on test:")
        for name in questions:
            variant = best[name]
            votes = {i: run(variant, name, i, "vote") for i in train + test}

            def point(i):
                answer = votes[i]
                if "error" in answer:
                    return None
                share = max(answer["probabilities"].values()) if "probabilities" in answer \
                    else max(answer["noul"], 1 - answer["noul"])
                return share, int(predicted_label(answer) == labels[i][name])

            train_points = [p for p in map(point, train) if p]
            table = fit_calibration(train_points)
            test_points = [(i, point(i)) for i in test if point(i)]
            raw = [(share, c) for _, (share, c) in test_points]
            cal = [(calibrated(table, share), c) for _, (share, c) in test_points]
            acting = [c for p, c in cal if p >= args.threshold]
            for i in test:
                test_predictions[(i, name)] = predicted_label(votes[i])

            accuracy = sum(c for _, c in raw) / len(raw)
            print(f"  {name:<15} {variant:<9} test agreement {accuracy:.0%}; "
                  f"calibration error raw {calibration_error(raw):.2f} -> calibrated {calibration_error(cal):.2f}; "
                  f"act at >= {args.threshold}: {len(acting)}/{len(cal)} prompts, "
                  + (f"{sum(acting) / len(acting):.0%} right" if acting else "none"))
            pack["questions"][name] = {"variant": variant, "calibration": table,
                                       "shots": args.shots if variant == "retrieval" else None}

        print("\ntest set gate (vote mode):")
        gate_report(labels, test_predictions, list(questions), ids=set(test))
        (DATA / "pack.json").write_text(json.dumps(pack, indent=1))
        print(f"\nquestion pack written to {DATA / 'pack.json'}")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
