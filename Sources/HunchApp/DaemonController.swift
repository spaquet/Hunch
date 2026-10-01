import HunchCore
import Observation
import ServiceManagement

/// Registers `hunchd` with launchd through the launch agent plist in the app bundle.
@MainActor
@Observable
final class DaemonController {
    private let service = SMAppService.agent(plistName: HunchIdentity.daemonPlistName)
    private(set) var status: SMAppService.Status
    private(set) var lastError: String?

    init() {
        status = service.status
        // First launch: register without asking; macOS shows its own notice.
        // A never-registered agent reports .notFound, not .notRegistered.
        if status == .notRegistered || status == .notFound {
            register()
        }
    }

    func refresh() {
        status = service.status
    }

    func register() {
        do {
            try service.register()
            lastError = nil
        } catch {
            lastError = error.localizedDescription
        }
        refresh()
    }

    func unregister() {
        do {
            try service.unregister()
            lastError = nil
        } catch {
            lastError = error.localizedDescription
        }
        refresh()
    }

    func openLoginItems() {
        SMAppService.openSystemSettingsLoginItems()
    }
}

extension SMAppService.Status {
    var summary: String {
        switch self {
        case .enabled: "running"
        case .requiresApproval: "needs approval in Login Items"
        case .notRegistered: "not registered"
        case .notFound: "not registered"
        @unknown default: "unknown"
        }
    }
}
