# Hunch — design

Sep 30, 2026 · Stephane Paquet

Hunch is a local System 1 layer for coding agents. It runs Apple's on-device Foundation Model, asks it typed questions, and lets deterministic policy code decide what Claude Code, Codex, OpenCode or Cursor may do next. It covers what TypeSafe's Jev does, plus generation work Jev cannot do.

## At a glance

![Hunch architecture · agents, surfaces, daemon, backends](architecture.svg)

Agents reach `hunchd` through hooks (enforced) or the CLI (on request). The model only answers typed questions; the policy engine turns those answers into a route, and every decision is logged.

## Jev vs Laya vs fm

Apple's model can match Jev's typed output, but not its calibrated probabilities; Hunch has to estimate confidence another way.

A System 1 model answers typed questions about a state in one pass: `choice` (pick a label, with a probability for each), `score` (a position on an ordered scale) and `noul` (probability of yes). Callers act when confidence clears a threshold and escalate to a bigger model when it doesn't.

|  | Jev (TypeSafe) | Laya (open source) | fm (Apple, on-device) |
| --- | --- | --- | --- |
| Model | Proprietary, hosted | ModernBERT / mmBERT encoders, 322–421M params | AFM 3 Core, generative LLM |
| Output | Typed by architecture | Typed by architecture | Typed by constrained decoding |
| Probabilities | Yes, calibrated | Yes, calibrated after temperature fit | No: no logprobs exposed |
| Latency, one question | 236–276 ms | \~33 ms | \~630 ms warm (measured) |
| Generates text | No | No | Yes: summaries, rewrites, vision, OCR |
| Runs where | TypeSafe cloud | Your machine or server | Your Mac (Apple also offers PCC; Hunch does not use it) |
| Zero-shot quality | Strong | Weak until fine-tuned | Good general reasoning |

Jev and Laya set the goal: typed `choice`, `score` and `noul` answers, with confidence callers can act on, fast enough for every prompt. Hunch reaches that goal with Apple's on-device model alone, on your Mac, for speed and privacy: no prompt, state or image leaves the machine to be classified. Hunch does not call Jev or Laya; it has to earn their confidence another way (see Question API and confidence).

## Measured on macOS 27.2

`fm` enforces enum values and returns strict JSON in about 0.6–0.8 s warm; it exposes no token probabilities.

| Test | Result |
| --- | --- |
| `fm respond --schema`, hand-written `"enum"` | Enforced. Told to output `deploy_to_prod`, it still returned a listed value |
| `fm respond`, greedy, warm | 0.76 s per call (1.58 s cold) |
| `fm serve`, `response_format: json_schema`, warm | 0.63 s per call (1.78 s cold) |
| `fm serve` with `logprobs: true` | Ignored; it also streams even when not asked to |
| `fm serve` binding | Loopback only, or a Unix socket via `--socket` |
| `fm serve --socket`, warm | 0.50–0.56 s per call (1.50 s cold); socket created `srwxr-xr-x`, so other users cannot connect |
| PCC from a process started by an agent | Unavailable: "not available in this context. Please use the Terminal app." |
| Built-in tools | `ocr`, `barcode`; `--image` input; `--use-case content-tagging` |
| `fm serve`, image as `data:image/png;base64,…` | Accepted; about 3 s per call, warm |
| `fm serve`, image as `file://` URL | Rejected (400): "image_url must be inlined as 'data:image/<type>;base64,<bytes>'… fm serve does not fetch remote URLs" |
| `fm serve`, image plus `json_schema` enum | Enum enforced |
| Prompt tokens, one image plus a short prompt | 64 px → 79; 256 px → 129; 512 px → 207; 1024 px → 207 |
| `fm count-tokens --image` | Fails: "ModelManagerError error 1001"; text-only counting works |
| Other backends | `--model-provider` routes to any Chat Completions server, such as Ollama or LM Studio. Hunch does not use it |

Corrections to the first research:

- `--number` does not exist; the flag is `--double`.
- `--array` is a modifier on the property before it (`--string tools --array`), not a type.
- Enums are enforced when written into the schema JSON; the CLI builder just has no flag for them.
- The sample script exits with `Unknown argument: classify` because its parser never handles the subcommand.
- A self-reported `confidence` field is invented by the model. Policy must not use it as a threshold.

Starting a new `fm` process for each call costs only about 0.13 s, because the OS already keeps the model loaded.

The on-device context window is 4,096 tokens, shared by instructions, prompt, schema and output ([Apple docs](https://developer.apple.com/documentation/foundationmodels/managing-the-context-window)). `fm count-tokens -q` measures a prompt before sending it.

## Runtime: a resident daemon, written in Swift

Decision: one Swift package builds `hunchd` (a launchd agent), the `hunch` CLI, and later the menu-bar app. All three share one core library. `hunchd` reaches Apple's on-device model through `fm serve` over a Unix socket by default; linking the FoundationModels framework in-process is a second, optional backend behind the same interface.

The daemon saves only about 0.13 s per call. It is still worth having because it:

- keeps policy, decision log and config in one place;
- lets hook scripts stay thin (`curl --unix-socket`, a few ms) instead of running a model;
- handles concurrent requests from several agents at once;
- gives the UI one process to control.

Local only. Hunch never calls PCC or any cloud model to answer its questions. This keeps every call fast and every input on the Mac, and it sidesteps PCC's managed entitlement, which an open-source daemon installed from Homebrew cannot hold ([Apple](https://developer.apple.com/private-cloud-compute/)). Routing the agent's own work to a frontier model remains a policy decision, made per repo (see Policy engine).

| Option | Pros | Cons |
| --- | --- | --- |
| **A. `hunchd` talks to `fm serve --socket` (default)** | Apple's supported CLI path; the Chat Completions API measured above; images as base64 data URLs; no framework API to track | No `prewarm()`, no adapters; a second process to supervise; needs an HTTP client that speaks Unix sockets |
| B. `hunchd` links FoundationModels in-process (optional) | `@Generable` enums, `prewarm()`, LoRA adapters, token counting and availability checks; no second process | Tied to the framework's Swift API; only needed once adapters land |
| C. No daemon; spawn `fm respond` per call | Zero setup; best for the v0 spike | No shared state, log or UI |

Plan: use C for a one-week v0 spike to test the questions, then build A. Add B in v2, when LoRA adapters need it; the backend interface keeps both behind one protocol.

Why a Unix socket rather than a TCP port:

- **Access control.** Loopback TCP accepts any local process, and any web page in a browser can send requests to `localhost:<port>`. `fm serve` has no authentication. A socket file is guarded by filesystem permissions: `fm serve` creates it `srwxr-xr-x`, and macOS requires write permission to connect, so only the owner can use it.
- **No port to pick** and no clash with other local servers.
- **Apple recommends it** in `fm serve --help` for local bindings.
- Speed is not a reason: the transport saves well under a millisecond against about 0.5 s of model time.

Socket details:

- Location: `~/Library/Application Support/Hunch/fm.sock`, in a directory created `0700`. Never `/tmp`, which every user can write to. `hunchd` serves its own API on a second socket in the same directory.
- Supervision: `hunchd` starts `fm serve --socket <path>` as a child, checks `GET /health`, and restarts it if it exits.
- Client: `URLSession` cannot connect to Unix sockets, so `hunchd` uses SwiftNIO's HTTP client (or a small HTTP/1.1 client over a raw socket). Hook scripts use `curl --unix-socket`.

## Integration: hooks, CLI and skills; MCP deferred

Hooks enforce, skills advise, and MCP adds only discovery. So skipping MCP in v1 is right, but keep it as a later option rather than ruling it out.

| Surface | Enforced? | Used for |
| --- | --- | --- |
| Agent hooks | Yes: the agent must wait for the hook's verdict | Classify every prompt; gate risky tool calls |
| `hunch` CLI | Only when called | Called by skills, scripts, CI and humans |
| Skills / custom commands | No: advisory text the agent may ignore | Tell the agent when to call `hunch summarize`, `hunch pack` and similar |
| MCP stdio shim (later) | No: the agent may skip a tool | Tool discovery in Cursor or Claude Desktop without shell access |

Hook points to use:

- **Claude Code:** `UserPromptSubmit` classifies the prompt and adds the route as context, or blocks it. `PreToolUse` on `Bash`, `Write` and `Edit` returns allow, deny or ask.
- **OpenCode:** a plugin on `tool.execute.before` and the prompt events.
- **Cursor:** `hooks.json` with `beforeSubmitPrompt` and `beforeShellExecution`.
- **Codex:** hooks.json or a \[hooks\] table in config.toml, with the same UserPromptSubmit and PreToolUse events and JSON output as Claude Code, plus PermissionRequest. One set of hook scripts serves both.

Latency budget: 0.6 s per prompt is fine. 0.6 s on every tool call is not. So `PreToolUse` checks deterministic allow and deny rules first and calls the model only for commands no rule covers.

The MCP shim, when it comes, is a \~100-line adapter over the same socket. No logic lives in it.

## Question API and confidence

Hunch uses Laya's Jev-compatible `/v1/systemone` request shape and adds its own measure of confidence, so clients written for Jev can call Hunch unchanged. Only the Apple on-device model answers.

A request is a state plus named questions. Each question is `choice` (with options), `score` (with ordered levels) or `noul`. Questions live in a versioned registry file, not in prompts spread across hooks. Example questions for v1:

- `intent`: choice (explain, diagnose, small\_change, multi\_file\_change, refactor, review, run\_command, research, ambiguous)
- `scope`: choice (trivial, single\_file, localized, repo\_wide, unknown)
- `risk`: choice (read\_only, reversible\_write, destructive, sensitive)
- `needs_evidence`: noul
- `injection`: noul, run on fetched or pasted content
- `urgency` or `complexity`: score 0–3

The Apple backend compiles each question into an enum schema and returns the chosen value. Confidence comes from one of two modes:

| Mode | Cost | Confidence | Use for |
| --- | --- | --- | --- |
| `fast` | 1 greedy call (\~0.6 s) | Reported as `uncalibrated` | Routing hints; low stakes |
| `vote` | k samples at temperature > 0 (k=5, \~3 s) | Share of votes for the winner | Risk and cloud-egress questions |

Thresholds are set per question from the decision log (see UI), never guessed. The response always says which mode produced the confidence.

Context budget: every call must fit in 4,096 tokens.

- About 600 tokens go to instructions and schema, and about 100 to the output. That leaves roughly 3,000 for the state.
- The daemon counts tokens before each call. When the state is too large, it keeps the head and tail of logs and sends one file excerpt at a time.
- Long logs and diffs are compressed in two steps: split into chunks of about 2,500 tokens, summarize each chunk, then summarize the summaries.

## Multimodal input (planned, not in v1)

Apple's on-device model accepts images, so a question can carry a screenshot as part of its state. Nothing in v1 depends on this; the section records what the platform supports so the question API does not rule it out.

What Apple documents ([multimodal prompting](https://developer.apple.com/documentation/FoundationModels/analyzing-images-with-multimodal-prompting), [`Attachment`](https://developer.apple.com/documentation/foundationmodels/attachment)):

- In Swift, an image goes into the prompt as `Attachment(image)`. It accepts `CGImage`, `NSImage`, `CVPixelBuffer` and file URLs; `.label("name")` names it and `orientation:` rotates it first.
- Any size and aspect ratio is allowed and the framework scales it. Larger images cost more tokens and latency.
- Guided generation works with images: Apple's own example classifies an image into a `@Generable` enum with greedy sampling, the same pattern as `choice`.
- `OCRTool` and `BarcodeReaderTool` are built-in tools that find an image by its label.

What we measured (see the table under Measured on macOS 27.2):

- `fm serve` takes images only as inline base64 data URLs. The daemon must read and encode the file itself.
- Token cost looks capped: 512 px and 1024 px images both cost 207 prompt tokens, about 5% of the 4,096 window.
- An image question takes about 3 s, roughly 5× a text question. It fits `fast` mode; `vote` (k=5) would take about 15 s and is too slow for hooks.
- `fm count-tokens --image` fails, so the daemon cannot measure an image before sending it. It reads `usage.prompt_tokens` from the response instead.
- One PNG was tested. Several images per request, JPEG and HEIC are untested.

Design so the API stays open to images:

- The state becomes a list of parts, text or image, instead of a single string. Images travel as a path (CLI) or base64 (socket). The `fm serve` backend sends them as data URLs; the in-process backend uses `Attachment(imageURL:)`.
- The context budget reserves about 210 tokens per image; the daemon downscales to 512 px on the long edge before sending.
- The decision log stores an image hash and dimensions, not the image, so screenshots do not accumulate on disk.

## Policy engine

The model labels; code decides. Anything with side effects or privacy impact is decided by deterministic rules that can be tested.

| Decided by the model (labels) | Decided by policy code |
| --- | --- |
| Intent, scope and risk labels | Which provider, model and effort level to use |
| Whether evidence is needed first | Which commands may run, with timeouts and output caps |
| Whether the text looks like prompt injection | Whether source code may leave the machine |
| Summaries and task packets | Scanning for and redacting secrets (regex first) |
|  | Cost caps, rate limits, human-approval gates |

Rules are a small ordered file (YAML or TOML): match on labels, confidence mode and repo, then emit a route. Examples:

1. `risk in [destructive, sensitive]` → ask a human, whatever the confidence.
2. The repo is marked `local_only` → no cloud provider, ever.
3. Low confidence, or `needs_evidence` true → gather local evidence, then classify again.
4. `intent: explain` or `summarize` → answer with the Apple model locally.
5. `small_change` in one file → frontier model at medium effort; `repo_wide` refactor → high effort.
6. No rule matches → human review.

Every decision is logged with its inputs, labels, confidence mode, the rule that fired, and any later override. Rules have unit tests: a fixture of labels in, an expected route out.

## Beyond Jev

Jev only decides. Apple's model can also generate text and see images, which adds seven features, ranked by expected value:

1. **Compress context before it goes to the frontier model.** Summarize test logs, stack traces and diffs locally, then send a compact packet. This probably saves more tokens than routing does.
2. **Guard against prompt injection.** A `noul` check on fetched pages, issue text and READMEs before an agent reads them.
3. **Classify secrets and PII,** layered on top of a regex scanner, which stays authoritative.
4. **Draft locally:** commit messages, PR descriptions and changelog lines.
5. **Triage screenshots:** error dialogs and UI bug screenshots via `--image` and the `ocr` tool; check QR codes and barcodes with the `barcode` tool. See Multimodal input.
6. **Custom adapters:** train a LoRA adapter on the override log with Apple's adapter toolkit. This is the path to better accuracy on your own questions, and needs the in-process backend.
7. **App Intents and Shortcuts:** expose the classifier outside coding, for example to triage mail or sort files.

## UI: menu-bar app

A SwiftUI menu-bar app, built on the same core as `hunchd`, controls backends, policy and privacy, and turns your overrides into eval data.

| Panel | Controls |
| --- | --- |
| Status (menu bar) | Daemon and `fm serve` up or down; last decision; a kill switch for frontier routing; pause Hunch |
| Model | Backend (`fm serve` or in-process); per question: confidence mode and k for voting |
| Policy | Ordered rules table; thresholds per question; dry-run a prompt and see which rule fires |
| Repos | Per-repo profile: `local_only`, allowed providers, allowed tools, evidence commands |
| Privacy | Redaction patterns, secret-scanner settings, egress log |
| Decision log | Live feed with inputs, labels and route; one-click override, which stores a label |
| Quality | Accuracy and calibration per question, from the labelled log |
| Usage | Token counts, latency, estimated frontier spend avoided |

Config lives in plain files under `~/.config/hunch/`. The UI edits those files, so everything can also be version-controlled and edited by hand.

## Roadmap

Four phases, each ending with a measurable gate; the Swift work starts only once the v0 spike shows the questions work.

1. **v0 — spike (1 week, no Swift).** A script calls `fm respond` with enum schemas; a question registry; 100 prompts from your real Claude Code history, labelled by hand. *Gate:* at least 85% agreement on `intent` and `risk`, and zero `destructive` prompts labelled `read_only`.
2. **v1 — daemon and hooks.** A Swift package with `hunchd`, the `hunch` CLI, the policy engine and the decision log; `fm serve --socket` supervised by `hunchd`; Claude Code `UserPromptSubmit` and `PreToolUse` hooks; `fast` and `vote` confidence modes; context compression; the Codex adapter, which reuses the Claude Code hook scripts. *Gate:* a week of daily use with p50 hook latency under 1 s and no bypassed approval gates.
3. **v1.5 — menu-bar app.** The panels above; OpenCode and Cursor adapters. *Gate:* thresholds set from at least 300 logged decisions.
4. **v2 — quality and reach.** the in-process FoundationModels backend; a LoRA adapter trained on overrides; the MCP shim; App Intents. *Gate:* the adapter beats the base model on the held-out set.

## Open questions

- [x] Context window: 4,096 tokens on-device, per Apple's docs.
- [x] Codex hooks: yes, with the same events and JSON as Claude Code.
- [x] Open source from day one: yes.
- [x] Name: the product is Hunch; package names can differ and are chosen later.
- [x] Licence for fm serve: accepted; `fm serve` is the default backend.
- [x] PCC: not used. Hunch runs only the local on-device model, for speed and privacy.
- [x] Backends: Apple's on-device model only. Jev and Laya are the feature target, not backends; custom providers are out.
- [ ] Images: does token cost stay capped above 1024 px and for other formats; how do several images in one request behave; does `fm count-tokens --image` work outside an agent context?
- [ ] Does `fm serve` stay warm between bursts of hook calls, or does `hunchd` need to send a keep-warm request? Compare p50 against the in-process backend.

## Sources

- [Laya repository](https://github.com/NandhaKishorM/laya)
- [TypeSafe manifesto](https://typesafe.ai/manifesto)
- [MarkTechPost: TypeSafe releases Jev](https://www.marktechpost.com/2026/09/19/typesafe-ai-releases-jev/)
- [Jev API examples](https://jevmodel.org/api/)
- [WWDC26 session 334: the fm command-line tool](https://developer.apple.com/videos/play/wwdc2026/334/)
- [Apple Developer Forums: fm serve thread](https://developer.apple.com/forums/thread/842813)
- [Apple: Managing the context window](https://developer.apple.com/documentation/foundationmodels/managing-the-context-window)
- [Apple: Analyzing images with multimodal prompting](https://developer.apple.com/documentation/FoundationModels/analyzing-images-with-multimodal-prompting)
- [WWDC26 session 241: What's new in the Foundation Models framework](https://developer.apple.com/videos/play/wwdc2026/241/)
- [Apple: Private Cloud Compute requirements](https://developer.apple.com/private-cloud-compute/)
- [Codex hooks documentation](https://learn.chatgpt.com/docs/hooks)
- Local measurements: `fm` on macOS 27.2 (Darwin 27.2.0), AFM 3 Core, 30 Sep 2026
