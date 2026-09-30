#!/usr/bin/env python3
"""Label sampled prompts by hand. Resumable; answers go to spike/data/labels.jsonl.

Keys: a number picks an option, s skips the prompt, x excludes it from the
eval (not a real task), q quits.
"""
from common import DATA, append_jsonl, read_jsonl, registry


def ask(question):
    options = list(question["options"])
    print(f"\n  {question['name']}: {question['question']}")
    for i, (name, desc) in enumerate(question["options"].items(), 1):
        print(f"    {i}. {name:<18} {desc}")
    while True:
        answer = input("  > ").strip().lower()
        if answer in ("s", "x", "q"):
            return answer
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]


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
        for question in reg["questions"]:
            answer = ask(question)
            if answer == "q":
                return
            if answer == "s":
                break
            if answer == "x":
                append_jsonl(DATA / "labels.jsonl", {"id": prompt["id"], "excluded": True})
                break
            labels[question["name"]] = answer
        else:
            append_jsonl(DATA / "labels.jsonl", {"id": prompt["id"], "labels": labels})


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
