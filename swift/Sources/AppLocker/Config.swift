import Foundation

struct AppLockerConfig: Codable {
    var lockedApps: [String]

    enum CodingKeys: String, CodingKey {
        case lockedApps = "locked_apps"
    }
}

func resolveConfigPath() -> String {
    let args = CommandLine.arguments
    if let idx = args.firstIndex(of: "--config"), idx + 1 < args.count {
        let path = args[idx + 1]
        return (path as NSString).expandingTildeInPath
    }
    // Fall back to config.json next to the binary
    let binaryDir = (CommandLine.arguments[0] as NSString).deletingLastPathComponent
    return (binaryDir as NSString).appendingPathComponent("config.json")
}

func loadConfig(from path: String) -> AppLockerConfig {
    let url = URL(fileURLWithPath: path)
    do {
        let data = try Data(contentsOf: url)
        let config = try JSONDecoder().decode(AppLockerConfig.self, from: data)
        return config
    } catch {
        log(.error, "Failed to load config from \(path): \(error.localizedDescription)")
        return AppLockerConfig(lockedApps: [])
    }
}
