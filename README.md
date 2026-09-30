# Hunch

Local System 1 decisions for coding agents, powered by Apple's on-device Foundation Model.

Hunch answers small typed questions about a task (intent, scope, risk) in under a second, on your Mac. Deterministic policy code turns those answers into a route: answer locally, gather evidence, hand off to a frontier model, or ask a human.

> Status: early prototype.

## Requirements

- macOS 27 or later with Apple Intelligence enabled
- Xcode 27 / Swift 6.2 or later

## Build

```bash
swift build
swift run hunch "delete all git branches"
swift test
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
