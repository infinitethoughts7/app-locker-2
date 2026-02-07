#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SWIFT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$SWIFT_DIR/.." && pwd)"

INSTALL_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/applocker"
BINARY_NAME="AppLocker"
PLIST_NAME="com.applocker.agent"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "=== AppLocker Install ==="

# Check prerequisites
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: macOS required."
    exit 1
fi

if ! command -v swift &>/dev/null; then
    echo "Error: Swift not found. Install Xcode or Command Line Tools."
    exit 1
fi

# Build release binary
echo "Building..."
cd "$SWIFT_DIR"
swift build -c release

BUILT_BINARY="$SWIFT_DIR/.build/release/$BINARY_NAME"
if [[ ! -f "$BUILT_BINARY" ]]; then
    echo "Error: Build failed — binary not found."
    exit 1
fi

# Install binary
mkdir -p "$INSTALL_DIR"
cp "$BUILT_BINARY" "$INSTALL_DIR/$BINARY_NAME"
echo "Installed binary to $INSTALL_DIR/$BINARY_NAME"

# Ad-hoc code sign (required for Touch ID dialog to show "AppLocker")
codesign --force --sign - "$INSTALL_DIR/$BINARY_NAME"
echo "Code signed (ad-hoc)."

# Copy config if not already present
mkdir -p "$CONFIG_DIR"
if [[ ! -f "$CONFIG_DIR/config.json" ]]; then
    if [[ -f "$REPO_DIR/config.json" ]]; then
        cp "$REPO_DIR/config.json" "$CONFIG_DIR/config.json"
        echo "Copied config.json to $CONFIG_DIR/"
    else
        echo '{"locked_apps": []}' > "$CONFIG_DIR/config.json"
        echo "Created empty config at $CONFIG_DIR/config.json"
    fi
else
    echo "Config already exists at $CONFIG_DIR/config.json"
fi

# Unload old Python daemon if present
if launchctl list 2>/dev/null | grep -q "com.applock.daemon"; then
    echo "Unloading old Python daemon..."
    launchctl bootout "gui/$(id -u)/com.applock.daemon" 2>/dev/null || true
fi

# Unload existing AppLocker agent if present
if launchctl list 2>/dev/null | grep -q "$PLIST_NAME"; then
    echo "Unloading existing AppLocker agent..."
    launchctl bootout "gui/$(id -u)/$PLIST_NAME" 2>/dev/null || true
fi

# Install LaunchAgent plist
mkdir -p "$LAUNCH_AGENTS"
sed -e "s|BINARY_PATH|$INSTALL_DIR/$BINARY_NAME|g" \
    -e "s|CONFIG_PATH|$CONFIG_DIR/config.json|g" \
    "$SWIFT_DIR/$PLIST_NAME.plist" > "$LAUNCH_AGENTS/$PLIST_NAME.plist"
echo "Installed LaunchAgent plist."

# Load the agent
launchctl bootstrap "gui/$(id -u)" "$LAUNCH_AGENTS/$PLIST_NAME.plist"
echo "Agent loaded."

echo ""
echo "=== Done ==="
echo "AppLocker is now running."
echo "Config: $CONFIG_DIR/config.json"
echo "Logs:   /tmp/applocker.log"
echo ""
echo "To reload config:  kill -HUP \$(pgrep AppLocker)"
echo "To stop:           launchctl bootout gui/$(id -u)/$PLIST_NAME"
echo ""
echo "NOTE: You may need to grant Accessibility access to AppLocker in"
echo "      System Settings > Privacy & Security > Accessibility"
