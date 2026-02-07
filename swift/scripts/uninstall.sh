#!/bin/bash
set -euo pipefail

PLIST_NAME="com.applocker.agent"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
INSTALL_DIR="$HOME/.local/bin"
BINARY_NAME="AppLocker"

echo "=== AppLocker Uninstall ==="

# Unload the agent
if launchctl list 2>/dev/null | grep -q "$PLIST_NAME"; then
    echo "Unloading agent..."
    launchctl bootout "gui/$(id -u)/$PLIST_NAME" 2>/dev/null || true
fi

# Remove plist
if [[ -f "$LAUNCH_AGENTS/$PLIST_NAME.plist" ]]; then
    rm "$LAUNCH_AGENTS/$PLIST_NAME.plist"
    echo "Removed LaunchAgent plist."
fi

# Remove binary
if [[ -f "$INSTALL_DIR/$BINARY_NAME" ]]; then
    rm "$INSTALL_DIR/$BINARY_NAME"
    echo "Removed binary."
fi

echo ""
echo "=== Done ==="
echo "AppLocker has been uninstalled."
echo "Config left intact at ~/.config/applocker/config.json"
echo "(Delete manually if no longer needed.)"
