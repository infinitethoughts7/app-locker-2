# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

macOS App Locker — a Python daemon that locks specified apps behind Touch ID / Face ID (or system password fallback). macOS 10.15+, Python 3.8+.

## Two Implementations

There are two separate app-locking implementations with different architectures:

1. **`locker.py`** (primary, used by `install.sh` daemon) — Uses PyObjC (`NSWorkspace` activation notifications via `NSRunLoop`) and macOS `LocalAuthentication` framework for Touch ID. Observes `NSWorkspaceDidActivateApplicationNotification` — triggers auth when a locked app gains foreground. Config: `config.json` (app names must be exact, case-sensitive matches against `localizedName()`).

2. **`app_locker.py`** (standalone CLI alternative) — Uses `psutil` polling loop to detect locked processes by keyword (case-insensitive partial match). Kills the process immediately, shows a native AppleScript password dialog (SHA256-hashed password, default "1234"), then relaunches on success. Config: `locker_config.json` (lowercase keywords). Has a CLI menu for password changes and app management.

These two implementations are **independent** and use different config files, different auth mechanisms, and different detection strategies.

## Running

```bash
# Primary (Touch ID, requires PyObjC — installed via venv):
./install.sh          # Sets up venv, installs deps, configures launchd agent
python3 locker.py     # Run directly (needs PyObjC in environment)

# Standalone (password-based, needs psutil):
./start_locker.sh     # Or: python3 app_locker.py
```

## Config Files

- `config.json` — Used by `locker.py`. App names are **exact, case-sensitive** (e.g., "WhatsApp", not "whatsapp").
- `locker_config.json` — Used by `app_locker.py`. Keywords are **lowercase, partial-match** (e.g., "whatsapp").

## Key Dependencies

- `locker.py`: PyObjC (`Foundation`, `AppKit`, `LocalAuthentication`, `objc`) — these come from the system Python bridge, not pip
- `app_locker.py`: `psutil` (from `requirements.txt`)

## Daemon (launchd)

`com.applock.daemon.plist` is a template — `install.sh` replaces `PYTHON_PATH` and `LOCKER_PATH` placeholders via sed and copies it to `~/Library/LaunchAgents/`. Logs go to `/tmp/applock.log` and `/tmp/applock.error.log`.

## Testing

```bash
python3 test_touchid.py   # Verifies Touch ID / LocalAuthentication works on this machine
```

There is no test suite. `test_touchid.py` is a manual smoke test for the biometric auth flow.

## Architecture Notes

- `locker.py` runs a Cocoa `NSRunLoop` event loop (not a polling loop) — the observer pattern means it reacts to activation events rather than scanning processes.
- `app_locker.py` uses a tight polling loop (`check_interval: 0.3s`) iterating `psutil.process_iter()`, spawning threads per locked-app detection.
- Both implementations have a grace period after successful auth (30s in `locker.py`, 60s in `app_locker.py`) to avoid re-locking immediately.
- `locker.py` uses a `pending_auth` flag to prevent concurrent auth dialogs.
- `app_locker.py` tracks PIDs in `locked_pids` set to avoid duplicate handling, uses `threading.Lock` for concurrency.

## macOS Permissions Required

Terminal/iTerm needs Accessibility access: System Settings > Privacy & Security > Accessibility.
