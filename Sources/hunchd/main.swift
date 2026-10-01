import Dispatch
import Foundation
import HunchCore
import os

// Resident skeleton: stays up under launchd until the socket server lands.

enum Daemon {
    static let log = Logger(subsystem: HunchIdentity.daemonLabel, category: "hunchd")
}

do {
    try HunchPaths.ensureSupportDirectory()
} catch {
    Daemon.log.error("cannot create support directory: \(error.localizedDescription, privacy: .public)")
    exit(1)
}

signal(SIGTERM, SIG_IGN)
let termination = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
termination.setEventHandler {
    Daemon.log.info("stopping")
    exit(0)
}
termination.resume()

Daemon.log.info("started, pid \(getpid())")
dispatchMain()
