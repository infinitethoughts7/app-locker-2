import Foundation

enum LogLevel: String {
    case info = "INFO"
    case error = "ERROR"
    case debug = "DEBUG"
}

func log(_ level: LogLevel, _ message: String) {
    #if !DEBUG
    if level == .debug { return }
    #endif

    let formatter = DateFormatter()
    formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
    let timestamp = formatter.string(from: Date())
    print("[\(timestamp)] [\(level.rawValue)] \(message)")
    fflush(stdout)
}
