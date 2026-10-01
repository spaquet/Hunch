import SwiftUI

struct HunchApp: App {
    @State private var daemon = DaemonController()

    var body: some Scene {
        MenuBarExtra("Hunch", systemImage: "brain") {
            MenuContent(daemon: daemon)
        }
    }
}

struct MenuContent: View {
    let daemon: DaemonController

    var body: some View {
        Text("hunchd: \(daemon.status.summary)")
        if let error = daemon.lastError {
            Text(error)
        }
        Divider()
        switch daemon.status {
        case .enabled:
            Button("Unregister hunchd") { daemon.unregister() }
        case .requiresApproval:
            Button("Allow in Login Items…") { daemon.openLoginItems() }
        default:
            Button("Register hunchd") { daemon.register() }
        }
        Button("Refresh") { daemon.refresh() }
        Divider()
        Button("Quit Hunch") { NSApplication.shared.terminate(nil) }
            .keyboardShortcut("q")
    }
}
