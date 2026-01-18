import AVFoundation

public final class AudioRouteMonitor {
    public typealias UpdateHandler = (_ routeSummary: String) -> Void

    private var updateHandler: UpdateHandler?

    public init() {}

    public func start(updateHandler: @escaping UpdateHandler) {
        self.updateHandler = updateHandler

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleRouteChange),
            name: AVAudioSession.routeChangeNotification,
            object: nil
        )

        updateHandler(currentRouteSummary())
    }

    public func stop() {
        NotificationCenter.default.removeObserver(self)
        updateHandler = nil
    }

    public func currentRouteSummary() -> String {
        let session = AVAudioSession.sharedInstance()
        let inputs = session.currentRoute.inputs.map { "\($0.portName) (\($0.portType.rawValue))" }
        let outputs = session.currentRoute.outputs.map { "\($0.portName) (\($0.portType.rawValue))" }

        let inputStr = inputs.isEmpty ? "None" : inputs.joined(separator: ", ")
        let outputStr = outputs.isEmpty ? "None" : outputs.joined(separator: ", ")

        return "Input: \(inputStr)\nOutput: \(outputStr)\nSampleRate: \(session.sampleRate)"
    }

    @objc private func handleRouteChange(_ notification: Notification) {
        updateHandler?(currentRouteSummary())
    }
}
