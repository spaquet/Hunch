# Hunch — distribution

Oct 1, 2026 · Stephane Paquet

How Hunch gets onto a Mac, and the status of each piece. Design decisions live in [architecture.md](architecture.md); this file tracks packaging, signing, release and install.

## Decision

One Homebrew cask installs everything: the menu-bar app, the `hunch` CLI and the `hunchd` daemon. The app bundle carries all three binaries; the cask symlinks the CLI onto the `PATH`, and the app registers the daemon with launchd.

```
Hunch.app/
  Contents/MacOS/HunchApp           menu-bar app and settings (LSUIElement, no Dock icon)
  Contents/MacOS/hunch              CLI, symlinked by the cask
  Contents/MacOS/hunchd             daemon
  Contents/Library/LaunchAgents/
    io.github.spaquet.hunch.hunchd.plist   registered with SMAppService.agent
```

The app executable is `HunchApp`, not `Hunch`: macOS volumes are usually case-insensitive, so `Hunch` and `hunch` would be the same file. The bundle is still named and shown as Hunch.

Install: `brew install --cask spaquet/hunch/hunch`, from our own tap (`spaquet/homebrew-hunch`). Moving to the official `homebrew/cask` waits until Hunch meets Homebrew's notability rules.

## Why a cask, not a formula

| Option | Pros | Cons |
| --- | --- | --- |
| **A. One cask with the app bundle (chosen)** | One signed, notarized artifact; app lands in `/Applications`; `binary` puts the CLI on the `PATH`; `SMAppService` shows the daemon in Login Items under Hunch's name | Needs a Developer ID; no build from source |
| B. Formula for CLI and daemon, plus a cask for the app | Formula builds from source; `brew services` runs the daemon | Two packages to keep in step; a formula cannot install a `.app` properly; `brew services` plists sit outside the app's control |
| C. Formula only, no app | Simplest | No menu bar or settings; against the UI plan |

## Requirements

- **Developer ID and notarization.** Homebrew is removing `--no-quarantine` and unsigned casks, and macOS 15+ dropped the Control-click bypass for unsigned apps. Releases are signed with a Developer ID (`codesign --options runtime`), notarized with `notarytool` and stapled. This needs a paid Apple Developer Program account, which the LoRA adapter entitlement would also need.
- **Daemon registration lives in the app.** `SMAppService.agent(plistName:)` only works from an app bundle. The app registers `hunchd` on first launch. A CLI-only user runs `hunch setup`, which runs `open -g -a Hunch --args --register-daemon`; the app registers the agent and exits without showing its menu-bar item. `--unregister-daemon` and `--daemon-status` work the same way. (`open` does not pass arguments to an app that is already running.) `hunchd` runs whether or not the menu-bar app is open.
- **`fm` is not a dependency.** It ships with macOS 27. The cask's only gate is `depends_on macos`; `hunch doctor` checks that Apple Intelligence is enabled and `fm` is present.
- **Updates through Homebrew.** `auto_updates false`; no Sparkle. `brew upgrade` replaces the bundle; the app re-registers the agent if its plist changed.
- **Uninstall is clean.** `uninstall` quits the app and unloads the agent; `zap` removes `~/Library/Application Support/Hunch` and `~/.config/hunch`.

## Build

SwiftPM builds all three executables; `scripts/bundle.sh` assembles the bundle, so the repo keeps `swift build` and needs no Xcode project. A SwiftUI `MenuBarExtra` app builds fine as a SwiftPM executable; only the bundle layout, `Info.plist` and signing are done by the script. If entitlements or asset catalogs outgrow the script, add an Xcode project for the app target only.

Release steps (`scripts/release.sh`, later a GitHub Actions job):

1. `swift build -c release --arch arm64` (Apple Intelligence needs Apple silicon, so no universal binary).
2. Assemble `Hunch.app`: the three binaries, `Info.plist`, the launch agent plist, the icon.
3. Sign inside out (`hunch`, `hunchd`, then the app) with Developer ID and the hardened runtime.
4. Zip with `ditto -c -k --keepParent`, submit with `notarytool submit --wait`, staple, zip again.
5. Upload to a GitHub Release and bump the cask's `version` and `sha256` in the tap.

Local development: `scripts/bundle.sh` builds `.build/bundle/Hunch.app` and signs it ad hoc. `SMAppService` registers and runs the agent from an ad hoc signed bundle (checked 1 Oct 2026 on macOS 27.2), so no certificate is needed until release. `SIGN_IDENTITY="Developer ID Application: …"` switches the same script to release signing.

## Cask

```ruby
cask "hunch" do
  version "0.1.0"
  sha256 "…"

  url "https://github.com/spaquet/Hunch/releases/download/v#{version}/Hunch-#{version}.zip"
  name "Hunch"
  desc "Local System 1 decision engine on Apple Intelligence"
  homepage "https://spaquet.github.io/Hunch/"

  depends_on macos: ">= :<macOS 27 symbol>"
  depends_on arch: :arm64

  app "Hunch.app"
  binary "#{appdir}/Hunch.app/Contents/MacOS/hunch"

  uninstall quit:      "io.github.spaquet.hunch",
            launchctl: "io.github.spaquet.hunch.hunchd"

  zap trash: [
    "~/Library/Application Support/Hunch",
    "~/.config/hunch",
  ]
end
```

## Roadmap impact

The architecture roadmap puts the menu-bar app in v1.5, but v1 already needs an app bundle to register `hunchd`. v1 therefore ships a minimal app (a status item: daemon and `fm serve` up or down, pause, quit), which grows into the full settings panels in v1.5.

The packaging skeleton was built on 1 Oct 2026, before the spike passed its gate, by decision of the owner: packaging does not depend on classifier accuracy. The roadmap hold still applies to the daemon's features (socket server, policy engine, hooks).

## Status

| Step | Status |
| --- | --- |
| Decide: one cask, own tap | Done (1 Oct 2026) |
| Bundle id `io.github.spaquet.hunch`, agent label `io.github.spaquet.hunch.hunchd` | Done (provisional until a custom domain exists) |
| Apple Developer Program account and Developer ID certificate | Open (owner action) |
| `HunchApp` SwiftPM target: minimal `MenuBarExtra`, `SMAppService` registration, headless flags | Done |
| `hunchd` stays resident under launchd and creates the `0700` support directory | Done (no socket server yet) |
| `hunch setup` and `hunch doctor` | Not started |
| `scripts/bundle.sh`: assemble and ad hoc sign `Hunch.app` locally | Done |
| App icon | Not started (menu bar uses the `brain` SF Symbol) |
| `scripts/release.sh`: Developer ID signing, notarization, stapling | Not started |
| `spaquet/homebrew-hunch` tap with the cask | Not started |
| GitHub Actions release job that bumps the tap | Not started |
| Website install instructions switch to `brew install --cask` | Not started |
| Submit to `homebrew/cask` | Later |

## Open questions

- [x] Bundle id: `io.github.spaquet.hunch` for now; reverse DNS on a domain we control. Changing it later means users re-approve the Login Item.
- [ ] Homebrew's symbol for macOS 27 in `depends_on macos`.
- [x] `SMAppService` registers an agent from an ad hoc signed bundle; local development needs no certificate. Before the first registration its status is `.notFound`, not `.notRegistered`.
- [ ] Is the cask token `hunch` free in `homebrew/cask`, for when we move there?
- [ ] Can a GitHub-hosted macOS runner build against the macOS 27 SDK, or does the release job need a self-hosted Mac?
