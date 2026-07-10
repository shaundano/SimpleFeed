#!/bin/bash
# Install Signal Digest as a macOS background service (launchd).
# Runs at login, restarts on crash. Re-run any time to reinstall.
# Usage: ./run-in-background.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"
LABEL="com.signaldigest.app"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$DIR/logs" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$DIR/app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$DIR/logs/app.log</string>
    <key>StandardErrorPath</key>
    <string>$DIR/logs/app.err.log</string>
</dict>
</plist>
PLISTEOF

# Reinstall cleanly (ignore "not loaded" on first run).
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Signal Digest is running at http://127.0.0.1:5050"
echo "Bookmark that in your browser. It'll start automatically at login."
echo "Stop it with:  launchctl bootout gui/\$(id -u)/$LABEL"
