#!/bin/bash
# Build Hunch.app from the SwiftPM products and sign it.
#
#   scripts/bundle.sh                         ad hoc signature, for local use
#   SIGN_IDENTITY="Developer ID Application: …" scripts/bundle.sh
#
# Output: .build/bundle/Hunch.app. See hunch-docs/distribution.md.
set -euo pipefail

cd "$(dirname "$0")/.."

# Keep in step with HunchIdentity in Sources/HunchCore/Identity.swift.
BUNDLE_ID="io.github.spaquet.hunch"
DAEMON_LABEL="$BUNDLE_ID.hunchd"

VERSION="${VERSION:-0.1.0}"
BUILD_NUMBER="${BUILD_NUMBER:-1}"
SIGN_IDENTITY="${SIGN_IDENTITY:--}"
APP=".build/bundle/Hunch.app"

swift build -c release --arch arm64
BIN="$(swift build -c release --arch arm64 --show-bin-path)"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Library/LaunchAgents"

# The app executable is HunchApp, not Hunch: macOS volumes are usually
# case-insensitive, so "Hunch" would collide with the "hunch" CLI.
cp "$BIN/HunchApp" "$BIN/hunch" "$BIN/hunchd" "$APP/Contents/MacOS/"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleName</key>
    <string>Hunch</string>
    <key>CFBundleDisplayName</key>
    <string>Hunch</string>
    <key>CFBundleExecutable</key>
    <string>HunchApp</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>$BUILD_NUMBER</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>27.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLIST

cat > "$APP/Contents/Library/LaunchAgents/$DAEMON_LABEL.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$DAEMON_LABEL</string>
    <key>BundleProgram</key>
    <string>Contents/MacOS/hunchd</string>
    <key>AssociatedBundleIdentifiers</key>
    <array>
        <string>$BUNDLE_ID</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
</dict>
</plist>
PLIST

plutil -lint -s "$APP/Contents/Info.plist" "$APP/Contents/Library/LaunchAgents/$DAEMON_LABEL.plist"

# Sign inside out: helpers first, then the bundle (which signs HunchApp).
if [ "$SIGN_IDENTITY" = "-" ]; then
    SIGN_FLAGS=(--force --options runtime --timestamp=none --sign -)
else
    SIGN_FLAGS=(--force --options runtime --timestamp --sign "$SIGN_IDENTITY")
fi
codesign "${SIGN_FLAGS[@]}" --identifier "$BUNDLE_ID.cli" "$APP/Contents/MacOS/hunch"
codesign "${SIGN_FLAGS[@]}" --identifier "$DAEMON_LABEL" "$APP/Contents/MacOS/hunchd"
codesign "${SIGN_FLAGS[@]}" "$APP"
codesign --verify --strict --deep "$APP"

echo "$APP"
