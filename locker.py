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

AUTH_GRACE_PERIOD = 10


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"locked_apps": []}


def authenticate(app_name: str) -> bool:
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
        if not success and error:
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
    
    def init(self):
        self = objc.super(AppLaunchObserver, self).init()
        if self is None:
            return None
        self.config = load_config()
        self.authenticated_pids = set()
        self.authenticated_apps = {}
        self.pending_auth = False
        self.pending_app = None
        return self
    
    def startObserving(self):
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
        app_info = notification.userInfo()
        app_name = app_info["NSApplicationName"]
        app = app_info["NSWorkspaceApplicationKey"]
        pid = app.processIdentifier()
        
        if app_name not in self.config["locked_apps"]:
            return
        
        if pid in self.authenticated_pids:
            return
        
        if app_name in self.authenticated_apps:
            elapsed = time.time() - self.authenticated_apps[app_name]
            if elapsed < AUTH_GRACE_PERIOD:
                print(f"[SKIP] {app_name} in grace period")
                self.authenticated_pids.add(pid)
                return
        
        if self.pending_auth:
            return
        
        print(f"Locked app detected: {app_name} (PID: {pid})")
        
        self.pending_auth = True
        self.pending_app = (app_name, app, pid)
        
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.3, self, "performAuth:", None, False
        )
    
    def performAuth_(self, timer):
        if not self.pending_app:
            self.pending_auth = False
            return
        
        app_name, app, pid = self.pending_app
        self.pending_app = None
        
        if app.isTerminated():
            self.pending_auth = False
            return
        
        success = authenticate(app_name)
        
        if success:
            print(f"✅ Authenticated: {app_name}")
            self.authenticated_pids.add(pid)
            self.authenticated_apps[app_name] = time.time()
            
            # Debug: check app state
            print(f"[DEBUG] App terminated? {app.isTerminated()}")
            print(f"[DEBUG] App hidden? {app.isHidden()}")
            print(f"[DEBUG] App active? {app.isActive()}")
            
            if not app.isTerminated():
                # Force unhide and activate
                if app.isHidden():
                    print("[DEBUG] Unhiding app...")
                    app.unhide()
                
                time.sleep(0.3)
                
                print("[DEBUG] Activating app...")
                app.activateWithOptions_(1)  # NSApplicationActivateIgnoringOtherApps
                
                time.sleep(0.2)
                print(f"[DEBUG] App active now? {app.isActive()}")
        else:
            print(f"❌ Auth failed, terminating: {app_name}")
            if not app.isTerminated():
                app.terminate()
        
        self.pending_auth = False
    
    def reloadConfig(self):
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