# Spike

Tests whether Apple's on-device model, reached through `fm serve`, can act as a Jev-style System 1 (with ideas from Laya and GLiNER2) before more Swift is written. See Roadmap and "Improving accuracy: two loops" in `hunch-docs/architecture.md`.

**Gate:** at least 85% agreement with hand labels on `intent` and `risk`, and zero prompts labelled `destructive` by hand that the model calls `read_only`. v0 (zero-shot, `fm respond`) failed it; v0.5 measures the same gate on a held-out test set.

## The engine

`systemone.py` is a Laya-compatible `system_one(state, questions)` on `fm serve --socket`. It starts `fm serve` if nothing is listening, under `~/Library/Application Support/Hunch/`. Questions use Laya's format (`type`, `instructions`, `criteria`) and answers carry Laya's fields (`choice`, `score`, `noul`, `probabilities`, `confidence`, `rl_agent.act_probability`).

```bash
python3 systemone.py    # Laya's own ticket example, fast and vote mode
```

## Steps

| Step | Command | Output (in `data/`, gitignored) |
| --- | --- | --- |
| 1. Sample 100 prompts from Claude Code history, round-robin across projects | `python3 sample.py` | `prompts.jsonl` |
| 2. Label them by hand, without seeing the model's answers | `python3 label.py` | `labels.jsonl` |
| 3. Ask every question through `system_one` | `python3 classify.py [--mode vote]` | `predictions.jsonl` |
| 4. Compare with labels and check the gate | `python3 evaluate.py [--mode vote]` | report on stdout |
| 5. Optimization loop: screen variants, calibrate, test once | `python3 optimize.py` | `split.json`, `runs.jsonl`, `pack.json` |

`optimize.py` screens three variants per question on the train split (zero-shot, one static example per label, and retrieval of the most similar labelled prompts, which simulates the online feedback loop), then runs the best one in vote mode, fits calibration on train, and reports agreement, calibration error and the gate on test. Every call is cached, so it resumes where it stopped.

Questions and their criteria live in `questions.json`. When you change one, bump `version`; predictions and cached runs record the version they were made with.

Prompts whose pasted text is no longer in `~/.claude/paste-cache` are skipped, since neither you nor the model could see what was pasted.
