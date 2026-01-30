"""
macOS App Locker
Locks specified apps (WhatsApp, etc.) until correct password is entered.

PASSWORD: 1234 (default)
"""

import psutil
import time
import threading
import hashlib
import json
import os
import subprocess

# ============== CONFIGURATION ==============
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locker_config.json")

DEFAULT_CONFIG = {
    # SHA256 hash of password (default: "1234")
    "password_hash": hashlib.sha256("1234".encode()).hexdigest(),
    # Apps to lock (keywords - case insensitive partial match)
    "locked_apps": [
        "whatsapp",
        "telegram",
        "discord",
        # Add more as needed (lowercase)
    ],
    # Check interval in seconds (faster = more responsive)
    "check_interval": 0.3
}

def load_config():
    """Load config from file or create default."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

def save_config(config):
    """Save config to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def hash_password(password):
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

# ============== macOS APP CONTROL ==============

def run_applescript(script):
    """Run AppleScript and return output."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"AppleScript error: {e}")
        return None

def hide_app(app_name):
    """Hide an app using AppleScript."""
    script = f'''
    tell application "System Events"
        set visible of process "{app_name}" to false
    end tell
    '''
    return run_applescript(script)

def show_app(app_name):
    """Show and activate an app using AppleScript."""
    script = f'''
    tell application "{app_name}"
        activate
    end tell
    '''
    return run_applescript(script)

def quit_app(app_name):
    """Quit an app using AppleScript."""
    script = f'''
    tell application "{app_name}"
        quit
    end tell
    '''
    return run_applescript(script)

def open_app(app_name):
    """Open/launch an app using the open command."""
    try:
        subprocess.run(['open', '-a', app_name], capture_output=True, timeout=5)
        return True
    except:
        return False

def terminate_process(pid):
    """Terminate a process by PID using SIGKILL."""
    try:
        os.kill(pid, 9)  # SIGKILL
        return True
    except:
        try:
            proc = psutil.Process(pid)
            proc.kill()
            return True
        except:
            return False

# ============== PASSWORD DIALOG (Native macOS) ==============

def show_password_dialog(app_name):
    """Show native macOS password dialog. Returns True if correct password."""
    config = load_config()
    max_attempts = 3

    for attempt in range(max_attempts):
        remaining = max_attempts - attempt

        # Native macOS dialog using AppleScript
        script = f'''
        tell application "System Events"
            activate
            set userInput to display dialog "🔒 {app_name} is locked\\n\\nEnter password to unlock:\\n({remaining} attempts remaining)" ¬
                default answer "" ¬
                with hidden answer ¬
                buttons {{"Cancel", "Unlock"}} ¬
                default button "Unlock" ¬
                with icon caution ¬
                with title "App Locker"
            return text returned of userInput
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=60
            )

            # User clicked Cancel or closed dialog
            if result.returncode != 0:
                return False

            entered_password = result.stdout.strip()

            # Check password
            if hash_password(entered_password) == config["password_hash"]:
                return True
            else:
                # Wrong password - show error
                error_script = f'''
                tell application "System Events"
                    display dialog "❌ Wrong password!" ¬
                        buttons {{"OK"}} ¬
                        default button "OK" ¬
                        with icon stop ¬
                        with title "App Locker"
                end tell
                '''
                subprocess.run(['osascript', '-e', error_script], capture_output=True, timeout=10)

        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            print(f"Dialog error: {e}")
            return False

    return False

# ============== MAIN LOCKER ==============

class AppLocker:
    # Grace period in seconds - app won't be blocked again after unlock
    GRACE_PERIOD = 60  # 1 minute grace period after unlock

    def __init__(self):
        self.config = load_config()
        self.locked_pids = set()  # Track PIDs we've already handled
        self.unlocked_apps = {}   # Track app_keyword -> unlock_timestamp
        self.running = False
        self.handling_lock = threading.Lock()

    def get_matching_keyword(self, proc_name):
        """Get the locked app keyword that matches this process name."""
        proc_name_lower = proc_name.lower()
        for locked_app in self.config["locked_apps"]:
            if locked_app.lower() in proc_name_lower:
                return locked_app.lower()
        return None

    def is_locked_app(self, proc_name):
        """Check if process name matches any locked app (case-insensitive partial match)."""
        keyword = self.get_matching_keyword(proc_name)
        if keyword is None:
            return False

        # Check if this app was recently unlocked (grace period)
        with self.handling_lock:
            if keyword in self.unlocked_apps:
                unlock_time = self.unlocked_apps[keyword]
                if time.time() - unlock_time < self.GRACE_PERIOD:
                    return False  # Still in grace period, don't block
                else:
                    # Grace period expired, remove from unlocked
                    del self.unlocked_apps[keyword]

        return True

    def handle_locked_app(self, proc, display_name):
        """Handle a detected locked app - KILL FIRST, ASK LATER."""
        pid = proc.pid
        keyword = self.get_matching_keyword(display_name)

        # Thread-safe check if already handling
        with self.handling_lock:
            if pid in self.locked_pids:
                return
            self.locked_pids.add(pid)

        try:
            # IMMEDIATELY KILL THE PROCESS - no window should appear
            print(f"🚫 Blocked: {display_name} (PID: {pid})")
            try:
                proc.kill()  # Force kill immediately
            except:
                terminate_process(pid)

            # Now show password dialog
            authenticated = show_password_dialog(display_name)

            if authenticated:
                # Add to unlocked apps with grace period
                with self.handling_lock:
                    self.unlocked_apps[keyword] = time.time()

                # Relaunch the app
                print(f"✅ {display_name} unlocked (grace: {self.GRACE_PERIOD}s)")
                open_app(display_name)
            else:
                print(f"❌ {display_name} access denied")

        finally:
            # Remove from tracked PIDs
            time.sleep(0.5)
            with self.handling_lock:
                self.locked_pids.discard(pid)

    def monitor(self):
        """Main monitoring loop."""
        print("=" * 50)
        print("🔒 App Locker Active")
        print(f"Monitoring (keywords): {', '.join(self.config['locked_apps'])}")
        print("")
        print("⚠️  PASSWORD: 1234")
        print("")
        print("Press Ctrl+C to stop")
        print("=" * 50)

        self.running = True

        while self.running:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        name = proc.info['name']
                        pid = proc.info['pid']

                        # Skip if already being handled
                        if pid in self.locked_pids:
                            continue

                        if self.is_locked_app(name):
                            # Handle in separate thread to not block monitoring
                            threading.Thread(
                                target=self.handle_locked_app,
                                args=(proc, name),
                                daemon=True
                            ).start()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                time.sleep(self.config["check_interval"])

            except KeyboardInterrupt:
                print("\n🛑 App Locker stopped")
                self.running = False
                break

    def stop(self):
        """Stop the locker."""
        self.running = False

# ============== CLI INTERFACE ==============

def change_password():
    """Change the locker password."""
    config = load_config()

    current = input("Enter current password: ")
    if hash_password(current) != config["password_hash"]:
        print("❌ Wrong password!")
        return

    new_pass = input("Enter new password: ")
    confirm = input("Confirm new password: ")

    if new_pass != confirm:
        print("❌ Passwords don't match!")
        return

    config["password_hash"] = hash_password(new_pass)
    save_config(config)
    print("✅ Password changed successfully!")

def add_app():
    """Add an app to the lock list."""
    config = load_config()

    print("\nCurrently locked apps:")
    for app in config["locked_apps"]:
        print(f"  - {app}")

    print("\nTip: Enter a keyword (partial match, case-insensitive)")
    print("Examples: whatsapp, telegram, discord, slack, messages, chrome")
    app_name = input("\nEnter app keyword: ").strip().lower()

    if app_name and app_name not in config["locked_apps"]:
        config["locked_apps"].append(app_name)
        save_config(config)
        print(f"✅ Added '{app_name}' to lock list")
    else:
        print(f"⚠️ '{app_name}' is already in the list or empty")

def remove_app():
    """Remove an app from the lock list."""
    config = load_config()

    print("\nCurrently locked apps:")
    for i, app in enumerate(config["locked_apps"], 1):
        print(f"  {i}. {app}")

    try:
        choice = int(input("\nEnter number to remove (0 to cancel): "))
        if choice == 0:
            return
        if 1 <= choice <= len(config["locked_apps"]):
            removed = config["locked_apps"].pop(choice - 1)
            save_config(config)
            print(f"✅ Removed {removed}")
    except ValueError:
        print("Invalid input")

def main():
    """Main entry point with menu."""
    print("\n" + "=" * 50)
    print("       🔒 macOS APP LOCKER")
    print("=" * 50)
    print("\n1. Start App Locker")
    print("2. Change Password")
    print("3. Add App to Lock")
    print("4. Remove App from Lock")
    print("5. Exit")

    choice = input("\nSelect option: ").strip()

    if choice == "1":
        locker = AppLocker()
        locker.monitor()
    elif choice == "2":
        change_password()
    elif choice == "3":
        add_app()
    elif choice == "4":
        remove_app()
    elif choice == "5":
        print("Goodbye!")
        return
    else:
        print("Invalid option")

    # Loop back to menu
    main()

if __name__ == "__main__":
    main()
