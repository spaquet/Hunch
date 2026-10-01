// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "Hunch",
    platforms: [.macOS("27.0")],
    products: [
        .library(name: "HunchCore", targets: ["HunchCore"]),
        .executable(name: "hunch", targets: ["hunch"]),
        .executable(name: "hunchd", targets: ["hunchd"]),
        .executable(name: "HunchApp", targets: ["HunchApp"]),
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-argument-parser", from: "1.5.0"),
    ],
    targets: [
        .target(name: "HunchCore"),
        .executableTarget(
            name: "hunch",
            dependencies: [
                "HunchCore",
                .product(name: "ArgumentParser", package: "swift-argument-parser"),
            ]
        ),
        .executableTarget(name: "hunchd", dependencies: ["HunchCore"]),
        .executableTarget(name: "HunchApp", dependencies: ["HunchCore"]),
        .testTarget(name: "HunchCoreTests", dependencies: ["HunchCore"]),
    ]
)
