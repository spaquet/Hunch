import Foundation

/// Names shared by the app bundle, the launch agent and the daemon.
/// `scripts/bundle.sh` writes the same values into the plists; keep them in step.
public enum HunchIdentity {
    public static let bundleID = "io.github.spaquet.hunch"
    public static let daemonLabel = "\(bundleID).hunchd"
    public static let daemonPlistName = "\(daemonLabel).plist"
}

public enum HunchPaths {
    /// `~/Library/Application Support/Hunch`, home of Hunch's sockets.
    public static var supportDirectory: URL {
        URL.applicationSupportDirectory.appending(path: "Hunch", directoryHint: .isDirectory)
    }

    /// Creates the support directory if needed and forces it to `0700`.
    public static func ensureSupportDirectory() throws {
        let fm = FileManager.default
        let path = supportDirectory.path
        try fm.createDirectory(atPath: path, withIntermediateDirectories: true)
        try fm.setAttributes([.posixPermissions: 0o700], ofItemAtPath: path)
    }
}
