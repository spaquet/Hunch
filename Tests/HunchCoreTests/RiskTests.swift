import Testing
@testable import HunchCore

@Test func riskLabelsAreStable() {
    #expect(Risk.allCases.map(\.rawValue) == [
        "readOnly", "reversibleWrite", "destructive", "sensitive",
    ])
}
