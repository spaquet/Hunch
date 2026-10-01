# Hunch — agent instructions

Hunch is a local System 1 decision engine: it recreates TypeSafe Jev and Laya (`system_one`: a JSON state plus typed `choice`, `score` and `noul` questions in; typed answers with probabilities and confidence out) using Apple Intelligence through `fm serve`. Keep the request and response shape compatible with Laya (https://github.com/receptron/laya). Coding agents are the first integration: deterministic policy code turns answers into what the agent may do next. The model labels; code decides. Generation features are secondary to the decision engine.

## Source of truth

- Design: `hunch-docs/architecture.md` and `hunch-docs/architecture.svg`. Read the design doc before changing behaviour, and update it in the same change when a decision changes.
- Distribution (Homebrew cask, signing, release) and its status: `hunch-docs/distribution.md`.
- `docs/` is the public GitHub Pages site; `hunch-docs/` is internal design notes.

## Fixed decisions

- **Local only.** Hunch's own questions go only to Apple's on-device model. Never add PCC, cloud models, Jev or Laya as backends. Jev and Laya are the feature target, not dependencies.
- **Backend:** `hunchd` talks to `fm serve --socket` by default. Linking FoundationModels in-process is an optional backend, added only if LoRA adapters become possible.
- **Sockets, not TCP ports.** Sockets live in a `0700` directory under `~/Library/Application Support/Hunch/`, never `/tmp`.
- **Context window:** 4,096 tokens, shared by instructions, prompt, schema and output.
- **Never trust a model-reported confidence field.** Confidence comes from `fast` (uncalibrated) or `vote` modes; `vote` shares are calibrated against labelled data.
- **No model retraining.** Accuracy comes from two loops: an offline optimization loop (instructions, few-shot, calibration; train/test split) and an online feedback loop (retrieval of the user's own overrides as few-shot). LoRA adapters are blocked (see the design doc).

## Layout

- `Sources/HunchCore`: shared library (classifier, later policy engine and decision log).
- `Sources/hunch`: CLI (swift-argument-parser).
- `Sources/hunchd`: daemon (placeholder).
- `Tests/HunchCoreTests`: Swift Testing tests.
- `spike/`: v0 spike in Python, standard library only. See `spike/README.md`.

## Commands

```bash
swift build
swift test
swift run hunch "task to classify"

cd spike
python3 sample.py      # sample prompts from ~/.claude/history.jsonl
python3 label.py       # label them by hand
python3 classify.py    # ask the on-device model
python3 evaluate.py    # agreement and the v0 gate
```

Requires macOS 27+ with Apple Intelligence enabled, and Swift 6.2+.

## Rules

- `spike/data/` holds the user's private prompts. It is gitignored; never commit it, print it in bulk, or send it anywhere.
- Work on a branch, not `main`.
- Keep the spike dependency-free (Python standard library only).
