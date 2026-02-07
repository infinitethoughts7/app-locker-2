import AppKit
import LocalAuthentication

class AppLockController {
    private var config: AppLockerConfig
    private let configPath: String
    private var authenticatedApps: [String: Date] = [:]
    private var pendingAuth = false
    private let gracePeriod: TimeInterval = 30
    private var lockPanel: NSWindow?

    init(configPath: String) {
        self.configPath = configPath
        self.config = loadConfig(from: configPath)
    }

    func startObserving() {
        let center = NSWorkspace.shared.notificationCenter
        center.addObserver(
            self,
            selector: #selector(appDidActivate(_:)),
            name: NSWorkspace.didActivateApplicationNotification,
            object: nil
        )
        // Watch for app launches too — catches fresh opens
        center.addObserver(
            self,
            selector: #selector(appDidLaunch(_:)),
            name: NSWorkspace.didLaunchApplicationNotification,
            object: nil
        )
        // When a locked app quits, clear its grace period so reopening always requires auth
        center.addObserver(
            self,
            selector: #selector(appDidTerminate(_:)),
            name: NSWorkspace.didTerminateApplicationNotification,
            object: nil
        )
        log(.info, "AppLocker running. Watching for: \(config.lockedApps)")
    }

    @objc private func appDidLaunch(_ notification: Notification) {
        guard let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else {
            return
        }
        guard let appName = app.localizedName else { return }
        guard config.lockedApps.contains(appName) else { return }
        // Clear any stale grace period for this app — fresh launch always requires auth
        authenticatedApps.removeValue(forKey: appName)
        log(.info, "Locked app launched: \(appName)")
    }

    @objc private func appDidTerminate(_ notification: Notification) {
        guard let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else {
            return
        }
        guard let appName = app.localizedName else { return }
        guard config.lockedApps.contains(appName) else { return }
        // App was quit — next open must require auth
        authenticatedApps.removeValue(forKey: appName)
        log(.info, "Locked app quit: \(appName) — grace period cleared")
    }

    // MARK: - Activation handler

    @objc private func appDidActivate(_ notification: Notification) {
        guard let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication else {
            return
        }
        guard let appName = app.localizedName else { return }
        guard config.lockedApps.contains(appName) else { return }

        // Check grace period
        if let lastAuth = authenticatedApps[appName],
           Date().timeIntervalSince(lastAuth) < gracePeriod {
            return
        }

        if pendingAuth { return }

        log(.info, "Locked app activated: \(appName)")
        pendingAuth = true

        // 1) Hide the app — its windows disappear, content is not visible
        app.hide()

        // 2) Show a small lock panel (doesn't block other apps)
        showLockPanel(appName: appName)

        // 3) Authenticate
        let success = authenticate(appName: appName)

        // 4) Remove lock panel
        hideLockPanel()

        if success {
            log(.info, "Authenticated: \(appName)")
            authenticatedApps[appName] = Date()
            // Unhide and bring the app back
            if !app.isTerminated {
                app.unhide()
                app.activate(options: .activateIgnoringOtherApps)
            }
        } else {
            log(.info, "Auth failed, terminating: \(appName)")
            if !app.isTerminated {
                app.forceTerminate()
            }
        }

        pendingAuth = false
    }

    // MARK: - Lock panel (small floating notification — does NOT block other apps)

    private func showLockPanel(appName: String) {
        guard let screen = NSScreen.main else { return }

        let panelWidth: CGFloat = 320
        let panelHeight: CGFloat = 160
        let panelX = (screen.frame.width - panelWidth) / 2
        let panelY = (screen.frame.height - panelHeight) / 2 + 80  // Slightly above center

        let window = NSPanel(
            contentRect: NSRect(x: panelX, y: panelY, width: panelWidth, height: panelHeight),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = true

        // Rounded visual effect background
        let visualEffect = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: panelWidth, height: panelHeight))
        visualEffect.autoresizingMask = [.width, .height]
        visualEffect.blendingMode = .behindWindow
        visualEffect.material = .hudWindow
        visualEffect.state = .active
        visualEffect.wantsLayer = true
        visualEffect.layer?.cornerRadius = 16
        visualEffect.layer?.masksToBounds = true
        window.contentView?.addSubview(visualEffect)

        // Lock icon
        let icon = NSImageView(frame: NSRect(x: panelWidth / 2 - 24, y: 90, width: 48, height: 48))
        icon.image = NSImage(systemSymbolName: "lock.fill", accessibilityDescription: "Locked")
        icon.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 36, weight: .medium)
        icon.contentTintColor = .white
        window.contentView?.addSubview(icon)

        // App name
        let label = NSTextField(labelWithString: "\(appName) is locked")
        label.font = NSFont.systemFont(ofSize: 18, weight: .semibold)
        label.textColor = .white
        label.alignment = .center
        label.sizeToFit()
        label.frame = NSRect(x: (panelWidth - label.frame.width) / 2, y: 55, width: label.frame.width, height: label.frame.height)
        window.contentView?.addSubview(label)

        // Subtitle
        let subtitle = NSTextField(labelWithString: "Authenticate to unlock")
        subtitle.font = NSFont.systemFont(ofSize: 13, weight: .regular)
        subtitle.textColor = NSColor.white.withAlphaComponent(0.6)
        subtitle.alignment = .center
        subtitle.sizeToFit()
        subtitle.frame = NSRect(x: (panelWidth - subtitle.frame.width) / 2, y: 30, width: subtitle.frame.width, height: subtitle.frame.height)
        window.contentView?.addSubview(subtitle)

        window.orderFrontRegardless()
        lockPanel = window
    }

    private func hideLockPanel() {
        lockPanel?.orderOut(nil)
        lockPanel = nil
    }

    // MARK: - Touch ID / password authentication

    private func authenticate(appName: String) -> Bool {
        let context = LAContext()
        var nsError: NSError?

        guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &nsError) else {
            log(.error, "Authentication not available: \(nsError?.localizedDescription ?? "unknown")")
            return false
        }

        var authResult = false
        var authDone = false

        context.evaluatePolicy(
            .deviceOwnerAuthentication,
            localizedReason: "Unlock \(appName)"
        ) { success, error in
            authResult = success
            authDone = true
            if !success, let error = error {
                log(.error, "Auth error: \(error.localizedDescription)")
            }
        }

        // Spin the run loop so the Touch ID dialog stays interactive
        let timeout: TimeInterval = 60
        let start = Date()
        while !authDone && Date().timeIntervalSince(start) < timeout {
            RunLoop.current.run(mode: .default, before: Date(timeIntervalSinceNow: 0.1))
        }

        if !authDone {
            log(.error, "Auth timed out for \(appName)")
            return false
        }

        return authResult
    }

    // MARK: - Config

    func reloadConfig() {
        config = loadConfig(from: configPath)
        log(.info, "Config reloaded: \(config.lockedApps)")
    }
}
