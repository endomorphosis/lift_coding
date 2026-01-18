import AVFoundation

public final class AudioRouteMonitor {
    public typealias UpdateHandler = (_ routeSummary: String) -> Void

    private var updateHandler: UpdateHandler?
    private var timer: Timer?

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
        
        // Also update periodically to catch any missed changes
        timer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.updateHandler?(self.currentRouteSummary())
        }
    }

    public func stop() {
        NotificationCenter.default.removeObserver(self)
        timer?.invalidate()
        timer = nil
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
    
    public func isBluetoothConnected() -> Bool {
        let session = AVAudioSession.sharedInstance()
        let route = session.currentRoute
        
        // Check for Bluetooth in inputs
        let hasBluetoothInput = route.inputs.contains { input in
            input.portType == .bluetoothHFP || 
            input.portType == .bluetoothLE || 
            input.portType == .bluetoothA2DP
        }
        
        // Check for Bluetooth in outputs
        let hasBluetoothOutput = route.outputs.contains { output in
            output.portType == .bluetoothHFP || 
            output.portType == .bluetoothLE || 
            output.portType == .bluetoothA2DP
        }
        
        return hasBluetoothInput || hasBluetoothOutput
    }
    
    public func getBluetoothDeviceName() -> String? {
        let session = AVAudioSession.sharedInstance()
        let route = session.currentRoute
        
        // Try to find Bluetooth device name
        if let bluetoothDevice = route.inputs.first(where: { input in
            input.portType == .bluetoothHFP || 
            input.portType == .bluetoothLE || 
            input.portType == .bluetoothA2DP
        }) {
            return bluetoothDevice.portName
        }
        
        if let bluetoothDevice = route.outputs.first(where: { output in
            output.portType == .bluetoothHFP || 
            output.portType == .bluetoothLE || 
            output.portType == .bluetoothA2DP
        }) {
            return bluetoothDevice.portName
        }
        
        return nil
    }
    
    public func getDetailedRouteInfo() -> [String: Any] {
        let session = AVAudioSession.sharedInstance()
        let route = session.currentRoute
        
        var info: [String: Any] = [:]
        
        info["sampleRate"] = session.sampleRate
        info["ioBufferDuration"] = session.ioBufferDuration
        info["isBluetoothConnected"] = isBluetoothConnected()
        info["bluetoothDeviceName"] = getBluetoothDeviceName() ?? NSNull()
        
        info["inputs"] = route.inputs.map { input in
            [
                "portName": input.portName,
                "portType": input.portType.rawValue,
                "uid": input.uid,
                "channels": input.channels?.map { channel in
                    ["channelName": channel.channelName, "channelNumber": channel.channelNumber]
                } ?? []
            ]
        }
        
        info["outputs"] = route.outputs.map { output in
            [
                "portName": output.portName,
                "portType": output.portType.rawValue,
                "uid": output.uid,
                "channels": output.channels?.map { channel in
                    ["channelName": channel.channelName, "channelNumber": channel.channelNumber]
                } ?? []
            ]
        }
        
        return info
    }

    @objc private func handleRouteChange(_ notification: Notification) {
        updateHandler?(currentRouteSummary())
    }
}
