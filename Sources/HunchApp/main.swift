import Foundation

// `open -g -a Hunch --args --register-daemon` lets the CLI register hunchd
// without showing the menu-bar item.
if let status = HeadlessCommand.run(CommandLine.arguments) {
    exit(status)
}

HunchApp.main()
