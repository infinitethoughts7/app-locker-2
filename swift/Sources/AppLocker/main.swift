import AppKit

let app = NSApplication.shared
app.setActivationPolicy(.accessory)  // No dock icon, but can create windows
let configPath = resolveConfigPath()
let controller = AppLockController(configPath: configPath)
controller.startObserving()

// SIGHUP → reload config
let hupSource = DispatchSource.makeSignalSource(signal: SIGHUP, queue: .main)
signal(SIGHUP, SIG_IGN)
hupSource.setEventHandler {
    controller.reloadConfig()
}
hupSource.resume()

// SIGTERM → graceful exit
let termSource = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
signal(SIGTERM, SIG_IGN)
termSource.setEventHandler {
    log(.info, "Received SIGTERM, exiting.")
    exit(0)
}
termSource.resume()

log(.info, "AppLocker started. Config: \(configPath)")

app.run()
