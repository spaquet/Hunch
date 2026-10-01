#!/usr/bin/env python3
"""Label sampled prompts by hand. Resumable; answers go to spike/data/labels.jsonl.

Keys: a number picks an option, s skips the prompt, x excludes it from the
eval (not a real task), q quits.
"""
from common import DATA, append_jsonl, options, read_jsonl, registry


def ask(name, question):
    labels = options(question)
    choices = list(labels)
    print(f"\n  {name}: {question['instructions']}")
    for i, (label, desc) in enumerate(labels.items(), 1):
        print(f"    {i}. {label:<18} {desc or ''}")
    while True:
        answer = input("  > ").strip().lower()
        if answer in ("s", "x", "q"):
            return answer
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]


def main():
    reg = registry()
    prompts = read_jsonl(DATA / "prompts.jsonl")
    done = {r["id"] for r in read_jsonl(DATA / "labels.jsonl")}
    todo = [p for p in prompts if p["id"] not in done]
    print(f"{len(done)} labelled, {len(todo)} to go. Keys: number, s skip, x exclude, q quit.")

    for n, prompt in enumerate(todo, len(done) + 1):
        print("\n" + "=" * 72)
        print(f"[{n}/{len(prompts)}] {prompt['project']}\n")
        print(prompt["text"])
        labels = {}
        for name, question in reg["questions"].items():
            answer = ask(name, question)
            if answer == "q":
                return
            if answer == "s":
                break
            if answer == "x":
                append_jsonl(DATA / "labels.jsonl", {"id": prompt["id"], "excluded": True})
                break
            labels[name] = answer
        else:
            append_jsonl(DATA / "labels.jsonl", {"id": prompt["id"], "labels": labels})


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
