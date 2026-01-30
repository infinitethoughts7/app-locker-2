# 🔐 AppLocker for macOS

Lock any macOS app with **Touch ID** / **Face ID**. Lightweight Python daemon that runs in the background.

![macOS](https://img.shields.io/badge/macOS-10.15+-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- 🔒 Lock any app with Touch ID / Face ID
- 🚀 Starts automatically on login
- ⚡ Lightweight (~10MB RAM)
- 🛠️ Simple JSON config
- 💯 100% local, no internet needed

## Requirements

- macOS 10.15+ (Catalina or later)
- Python 3.8+
- Touch ID or Face ID capable Mac

## Quick Install

```bash
git clone https://github.com/YOUR_USERNAME/app-locker.git
cd app-locker
chmod +x install.sh
./install.sh
```

## Configure Locked Apps

Edit `config.json`:

```json
{
  "locked_apps": [
    "WhatsApp",
    "Telegram",
    "Notes",
    "Photos"
  ]
}
```

> **Tip**: App names must match exactly. Check via `Activity Monitor` or run:
> ```bash
> osascript -e 'tell application "System Events" to get name of every process'
> ```

## Commands

```bash
# View logs
tail -f /tmp/applock.log

# Stop daemon
launchctl unload ~/Library/LaunchAgents/com.applock.daemon.plist

# Start daemon
launchctl load ~/Library/LaunchAgents/com.applock.daemon.plist

# Restart after config change
launchctl kickstart -k gui/$(id -u)/com.applock.daemon
```

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## How It Works

1. Launch Agent starts `locker.py` on login
2. Daemon listens for app launch events via `NSWorkspace`
3. When a locked app opens → immediately hides it
4. Touch ID prompt appears
5. Success → app unhides | Fail → app terminates

## Troubleshooting

**Touch ID prompt not appearing?**
- Grant Terminal/iTerm accessibility permissions:
  `System Settings → Privacy & Security → Accessibility`

**App not getting locked?**
- Check exact app name in `config.json`
- View logs: `tail -f /tmp/applock.log`

**Daemon not starting?**
- Check: `launchctl list | grep applock`
- View errors: `cat /tmp/applock.error.log`

## License

MIT License - Use freely, modify as needed.

## Contributing

PRs welcome! Ideas:
- [ ] Menu bar UI for config
- [ ] Password fallback when Touch ID unavailable
- [ ] Time-based auto-lock rules
