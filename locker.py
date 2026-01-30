#!/usr/bin/env python3
"""
AppLocker - Touch ID protected app lock for macOS
Run as Launch Agent for automatic startup
"""

import json
import time
from pathlib import Path

from Foundation import NSObject, NSRunLoop, NSDate, NSTimer
from AppKit import NSWorkspace, NSApplication
from LocalAuthentication import LAContext, LAPolicyDeviceOwnerAuthentication
import objc

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    """Load locked apps list from config"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"locked_apps": []}


def authenticate(app_name: str) -> bool:
    """Trigger Touch ID authentication with password fallback"""
    time.sleep(0.5)
    
    context = LAContext()
    
    can_evaluate, error = context.canEvaluatePolicy_error_(
        LAPolicyDeviceOwnerAuthentication, None
    )
    
    if not can_evaluate:
        print(f"Authentication not available: {error}")
        return False
    
    result = {"success": False, "done": False}
    
    def callback(success, error):
        result["success"] = success
        result["done"] = True
        if error:
            print(f"Auth error: {error}")
    
    context.evaluatePolicy_localizedReason_reply_(
        LAPolicyDeviceOwnerAuthentication,
        f"Unlock {app_name}",
        callback
    )
    
    timeout = 60
    start = time.time()
    
    while not result["done"] and (time.time() - start) < timeout:
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            "NSDefaultRunLoopMode",
            NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )
    
    return result["success"]


class AppLaunchObserver(NSObject):
    """Observes app launches and triggers auth for locked apps"""
    
    def init(self):
        self = objc.super(AppLaunchObserver, self).init()
        if self is None:
            return None
        self.config = load_config()
        self.authenticated_pids = set()
        self.pending_auth = False
        self.pending_app = None
        return self
    
    def startObserving(self):
        """Start watching for app launches"""
        workspace = NSWorkspace.sharedWorkspace()
        center = workspace.notificationCenter()
        
        center.addObserver_selector_name_object_(
            self,
            "appDidLaunch:",
            "NSWorkspaceDidLaunchApplicationNotification",
            None
        )
        print("AppLocker running. Watching for:", self.config["locked_apps"])
    
    def appDidLaunch_(self, notification):
        """Called when any app launches"""
        app_info = notification.userInfo()
        app_name = app_info["NSApplicationName"]
        app = app_info["NSWorkspaceApplicationKey"]
        pid = app.processIdentifier()
        
        if app_name not in self.config["locked_apps"]:
            return
        
        if pid in self.authenticated_pids:
            return
        
        if self.pending_auth:
            app.terminate()
            return
        
        print(f"Locked app detected: {app_name}")
        
        app.hide()
        
        self.pending_auth = True
        self.pending_app = (app_name, app, pid)
        
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.3, self, "performAuth:", None, False
        )
    
    def performAuth_(self, timer):
        """Perform authentication after delay"""
        if not self.pending_app:
            self.pending_auth = False
            return
        
        app_name, app, pid = self.pending_app
        self.pending_app = None
        
        if app.isTerminated():
            self.pending_auth = False
            return
        
        if authenticate(app_name):
            print(f"✅ Authenticated: {app_name}")
            self.authenticated_pids.add(pid)
            app.unhide()
            app.activateWithOptions_(0)
        else:
            print(f"❌ Auth failed, terminating: {app_name}")
            app.terminate()
        
        self.pending_auth = False
    
    def reloadConfig(self):
        """Reload config without restart"""
        self.config = load_config()
        print("Config reloaded:", self.config["locked_apps"])


def main():
    app = NSApplication.sharedApplication()
    
    observer = AppLaunchObserver.alloc().init()
    observer.startObserving()
    
    print("AppLocker started. Press Ctrl+C to stop.")
    
    try:
        NSRunLoop.currentRunLoop().run()
    except KeyboardInterrupt:
        print("\nStopping AppLocker...")


if __name__ == "__main__":
    main()