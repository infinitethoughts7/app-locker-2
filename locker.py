#!/usr/bin/env python3
"""
AppLocker - Touch ID protected app lock for macOS
Uses activation observation instead of launch observation
"""

import json
import time
from pathlib import Path

from Foundation import NSObject, NSRunLoop, NSDate
from AppKit import NSWorkspace, NSApplication, NSApplicationActivateIgnoringOtherApps
from LocalAuthentication import LAContext, LAPolicyDeviceOwnerAuthentication
import objc

CONFIG_PATH = Path(__file__).parent / "config.json"

AUTH_GRACE_PERIOD = 30


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"locked_apps": []}


def get_app_by_name(app_name):
    """Find running app by name"""
    workspace = NSWorkspace.sharedWorkspace()
    for app in workspace.runningApplications():
        if app.localizedName() == app_name:
            return app
    return None


def authenticate(app_name: str) -> bool:
    """Trigger Touch ID authentication with password fallback"""
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
        self.authenticated_apps = {}
        self.pending_auth = False
        return self
    
    def startObserving(self):
        workspace = NSWorkspace.sharedWorkspace()
        center = workspace.notificationCenter()
        
        center.addObserver_selector_name_object_(
            self,
            "appDidActivate:",
            "NSWorkspaceDidActivateApplicationNotification",
            None
        )
        print("AppLocker running. Watching for:", self.config["locked_apps"])
    
    def appDidActivate_(self, notification):
        """Called when any app becomes active (foreground)"""
        app_info = notification.userInfo()
        
        # Activation notification uses NSWorkspaceApplicationKey directly
        app = app_info.get("NSWorkspaceApplicationKey")
        if not app:
            return
        
        app_name = app.localizedName()
        if not app_name:
            return
        
        if app_name not in self.config["locked_apps"]:
            return
        
        # Check grace period
        if app_name in self.authenticated_apps:
            elapsed = time.time() - self.authenticated_apps[app_name]
            if elapsed < AUTH_GRACE_PERIOD:
                return
        
        if self.pending_auth:
            return
        
        print(f"Locked app activated: {app_name}")
        self.pending_auth = True
        
        success = authenticate(app_name)
        
        if success:
            print(f"✅ Authenticated: {app_name}")
            self.authenticated_apps[app_name] = time.time()
            
            time.sleep(0.2)
            fresh_app = get_app_by_name(app_name)
            if fresh_app and not fresh_app.isTerminated():
                fresh_app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        else:
            print(f"❌ Auth failed, terminating: {app_name}")
            fresh_app = get_app_by_name(app_name)
            if fresh_app and not fresh_app.isTerminated():
                fresh_app.terminate()
        
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