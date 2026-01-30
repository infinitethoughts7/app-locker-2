#!/bin/bash

# AppLocker Install Script for macOS

set -e

echo "🔐 Installing AppLocker..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCKER_PATH="$SCRIPT_DIR/locker.py"
PLIST_SRC="$SCRIPT_DIR/com.applock.daemon.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.applock.daemon.plist"

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ This only works on macOS"
    exit 1
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install it first."
    exit 1
fi

PYTHON_PATH="$(which python3)"
echo "✓ Python found: $PYTHON_PATH"

# Create virtual environment
echo "📦 Setting up virtual environment..."
python3 -m venv "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

# Create Launch Agent directory if needed
mkdir -p "$HOME/Library/LaunchAgents"

# Configure plist with correct paths
echo "⚙️  Configuring Launch Agent..."
sed -e "s|PYTHON_PATH|$VENV_PYTHON|g" \
    -e "s|LOCKER_PATH|$LOCKER_PATH|g" \
    "$PLIST_SRC" > "$PLIST_DEST"

# Unload if already loaded
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the agent
echo "🚀 Starting AppLocker..."
launchctl load "$PLIST_DEST"

echo ""
echo "✅ AppLocker installed successfully!"
echo ""
echo "📝 Edit locked apps: $SCRIPT_DIR/config.json"
echo "📋 View logs: tail -f /tmp/applock.log"
echo ""
echo "Commands:"
echo "  Stop:    launchctl unload ~/Library/LaunchAgents/com.applock.daemon.plist"
echo "  Start:   launchctl load ~/Library/LaunchAgents/com.applock.daemon.plist"
echo "  Restart: launchctl kickstart -k gui/\$(id -u)/com.applock.daemon"
