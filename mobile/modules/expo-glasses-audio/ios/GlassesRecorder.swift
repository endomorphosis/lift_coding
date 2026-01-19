import AVFoundation

public enum AudioSource: String {
    case phone = "phone"
    case glasses = "glasses"
    case auto = "auto"
}

public final class GlassesRecorder {
    private let audioEngine = AVAudioEngine()
    private var audioFile: AVAudioFile?

    public init() {}

    public func startRecording(outputURL: URL, audioSource: AudioSource = .auto) throws {
        let session = AVAudioSession.sharedInstance()
        
        // Configure audio session based on audio source preference
        switch audioSource {
        case .phone:
            // Force phone microphone - don't allow Bluetooth
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker])
            try session.setActive(true)
            // Override route to prefer built-in mic
            try session.overrideOutputAudioPort(.speaker)
            
        case .glasses:
            // Prefer Bluetooth microphone
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .allowBluetoothA2DP])
            try session.setActive(true)
            
            // Check if Bluetooth is actually available
            let currentRoute = session.currentRoute
            let hasBluetoothInput = currentRoute.inputs.contains { input in
                input.portType == .bluetoothHFP || input.portType == .bluetoothLE || input.portType == .bluetoothA2DP
            }
            
            if !hasBluetoothInput {
                print("⚠️ Warning: Glasses/Bluetooth source selected but no Bluetooth device detected. Falling back to built-in mic.")
            }
            
        case .auto:
            // Auto mode - allow Bluetooth but don't force it
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
            try session.setActive(true)
        }

        let inputNode = audioEngine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)

        audioFile = try AVAudioFile(
            forWriting: outputURL,
            settings: [
                AVFormatIDKey: kAudioFormatLinearPCM,
                AVSampleRateKey: 16000,
                AVNumberOfChannelsKey: 1,
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsFloatKey: false,
                AVLinearPCMIsBigEndianKey: false
            ]
        )

        inputNode.installTap(onBus: 0, bufferSize: 4096, format: inputFormat) { [weak self] buffer, _ in
            guard let self, let file = self.audioFile else { return }
            try? file.write(from: buffer)
        }

        try audioEngine.start()
    }

    public func stopRecording() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        audioFile = nil
    }
}
