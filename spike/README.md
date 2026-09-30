# v0 spike

Tests whether Apple's on-device model can answer Hunch's questions well enough before any more Swift is written. See Roadmap in `hunch-docs/architecture.md`.

**Gate:** at least 85% agreement with hand labels on `intent` and `risk`, and zero prompts labelled `destructive` by hand that the model calls `read_only`.

| Step | Command | Output (in `data/`, gitignored) |
| --- | --- | --- |
| 1. Sample 100 prompts from Claude Code history, round-robin across projects | `python3 sample.py` | `prompts.jsonl` |
| 2. Label them by hand, without seeing the model's answers | `python3 label.py` | `labels.jsonl` |
| 3. Ask the model, one greedy `fm respond` call per question | `python3 classify.py` | `predictions.jsonl` |
| 4. Compare and check the gate | `python3 evaluate.py` | report on stdout |

Questions and their options live in `questions.json`. When you change a question, bump `version`; each prediction records the version it was made with.

Steps 2 and 3 are resumable. Label before you look at predictions, so the model's answers don't bias yours.

Prompts whose pasted text is no longer in `~/.claude/paste-cache` are skipped, since neither you nor the model could see what was pasted.
