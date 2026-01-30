#!/usr/bin/env python3
"""
Simple Touch ID test - run this first to verify auth works
"""

import time
from LocalAuthentication import LAContext, LAPolicyDeviceOwnerAuthenticationWithBiometrics
from Foundation import NSRunLoop, NSDate

def test_touch_id():
    print("Testing Touch ID...")
    
    context = LAContext()
    
    # Check if Touch ID is available
    can_evaluate, error = context.canEvaluatePolicy_error_(
        LAPolicyDeviceOwnerAuthenticationWithBiometrics, None
    )
    
    if not can_evaluate:
        print(f"❌ Touch ID not available: {error}")
        print("Trying with password fallback...")
        
        # Try with device passcode fallback
        from LocalAuthentication import LAPolicyDeviceOwnerAuthentication
        can_evaluate, error = context.canEvaluatePolicy_error_(
            LAPolicyDeviceOwnerAuthentication, None
        )
        if not can_evaluate:
            print(f"❌ Authentication not available at all: {error}")
            return
        policy = LAPolicyDeviceOwnerAuthentication
    else:
        policy = LAPolicyDeviceOwnerAuthenticationWithBiometrics
    
    print("✓ Auth available. Prompting now...")
    print(">>> Look for the Touch ID / Password dialog <<<")
    
    result = {"done": False, "success": False}
    
    def callback(success, error):
        result["success"] = success
        result["done"] = True
        if success:
            print("✅ Authentication SUCCESS!")
        else:
            print(f"❌ Authentication FAILED: {error}")
    
    # Trigger auth
    context.evaluatePolicy_localizedReason_reply_(
        policy,
        "Testing AppLocker authentication",
        callback
    )
    
    # Keep the run loop alive so dialog stays interactive
    print("Waiting for your input...")
    timeout = 30  # 30 second timeout
    start = time.time()
    
    while not result["done"] and (time.time() - start) < timeout:
        # Process events - THIS IS KEY for dialog to work
        NSRunLoop.currentRunLoop().runMode_beforeDate_(
            "NSDefaultRunLoopMode",
            NSDate.dateWithTimeIntervalSinceNow_(0.1)
        )
    
    if not result["done"]:
        print("⏰ Timeout - no response")
    
    return result["success"]


if __name__ == "__main__":
    test_touch_id()
