import ArgumentParser
import HunchCore

@main
struct Hunch: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        abstract: "Local System 1 decisions for coding agents."
    )

    @Argument(help: "The task to classify.")
    var task: String

    func run() async throws {
        print(try await Classifier().risk(of: task).rawValue)
    }
}
