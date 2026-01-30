#!/bin/bash

# AppLocker Uninstall Script

echo "🗑️  Uninstalling AppLocker..."

PLIST_DEST="$HOME/Library/LaunchAgents/com.applock.daemon.plist"

# Stop the daemon
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Remove plist
rm -f "$PLIST_DEST"

echo "✅ AppLocker uninstalled"
echo "📁 Project files remain in this folder (delete manually if needed)"
