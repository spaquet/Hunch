import Foundation
import HunchCore
import ServiceManagement

/// Flags that act on the launch agent and exit without starting the UI.
enum HeadlessCommand {
    static func run(_ arguments: [String]) -> Int32? {
        let service = SMAppService.agent(plistName: HunchIdentity.daemonPlistName)
        do {
            if arguments.contains("--register-daemon") {
                try service.register()
            } else if arguments.contains("--unregister-daemon") {
                try service.unregister()
            } else if !arguments.contains("--daemon-status") {
                return nil
            }
        } catch {
            FileHandle.standardError.write(Data("hunchd: \(error.localizedDescription)\n".utf8))
            return 1
        }
        print("hunchd: \(service.status.summary)")
        return 0
    }
}
