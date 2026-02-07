// swift-tools-version: 5.7

import PackageDescription

let package = Package(
    name: "AppLocker",
    platforms: [
        .macOS(.v12)
    ],
    targets: [
        .executableTarget(
            name: "AppLocker",
            path: "Sources/AppLocker",
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("LocalAuthentication"),
            ]
        )
    ]
)
