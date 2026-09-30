import FoundationModels

@Generable
public enum Risk: String, CaseIterable, Sendable {
    case readOnly, reversibleWrite, destructive, sensitive
}

public enum HunchError: Error {
    case modelUnavailable(String)
}

public struct Classifier: Sendable {
    public init() {}

    public func risk(of task: String) async throws -> Risk {
        let model = SystemLanguageModel.default
        guard case .available = model.availability else {
            throw HunchError.modelUnavailable(String(describing: model.availability))
        }
        let session = LanguageModelSession(
            model: model,
            instructions: "You classify software tasks by risk. You never solve them."
        )
        return try await session.respond(to: task, generating: Risk.self).content
    }
}
