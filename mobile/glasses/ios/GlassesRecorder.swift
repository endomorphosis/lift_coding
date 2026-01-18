import AVFoundation

public final class GlassesRecorder {
    private let audioEngine = AVAudioEngine()
    private var audioFile: AVAudioFile?
    private var recordingStartTime: Date?
    private var isRecording = false
    private var outputURL: URL?
    
    public typealias RecordingCompletion = (Result<URL, Error>) -> Void
    private var completionHandler: RecordingCompletion?
    
    public enum RecorderError: LocalizedError {
        case alreadyRecording
        case notRecording
        case audioSessionSetupFailed(Error)
        case audioEngineStartFailed(Error)
        case fileCreationFailed(Error)
        case noBluetoothDevice
        
        public var errorDescription: String? {
            switch self {
            case .alreadyRecording:
                return "Recording is already in progress"
            case .notRecording:
                return "No recording in progress"
            case .audioSessionSetupFailed(let error):
                return "Failed to set up audio session: \(error.localizedDescription)"
            case .audioEngineStartFailed(let error):
                return "Failed to start audio engine: \(error.localizedDescription)"
            case .fileCreationFailed(let error):
                return "Failed to create audio file: \(error.localizedDescription)"
            case .noBluetoothDevice:
                return "No Bluetooth audio device connected"
            }
        }
    }

    public init() {}

    public func startRecording(outputURL: URL, duration: TimeInterval? = nil, completion: RecordingCompletion? = nil) throws {
        guard !isRecording else {
            throw RecorderError.alreadyRecording
        }
        
        self.outputURL = outputURL
        self.completionHandler = completion
        
        // Configure audio session for Bluetooth input
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
            try session.setActive(true)
        } catch {
            throw RecorderError.audioSessionSetupFailed(error)
        }
        
        // Verify Bluetooth input is available
        let currentRoute = session.currentRoute
        let hasBluetoothInput = currentRoute.inputs.contains { input in
            input.portType == .bluetoothHFP || input.portType == .bluetoothLE || input.portType == .bluetoothA2DP
        }
        
        // Allow fallback to built-in mic for development/testing
        if !hasBluetoothInput {
            print("⚠️ Warning: No Bluetooth audio device detected. Using built-in microphone.")
        }

        let inputNode = audioEngine.inputNode
        let inputFormat = inputNode.outputFormat(forBus: 0)
        
        // Create 16kHz mono PCM file format for backend compatibility
        let outputFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16000,
            channels: 1,
            interleaved: false
        )
        
        guard let outputFormat = outputFormat else {
            throw RecorderError.fileCreationFailed(NSError(domain: "GlassesRecorder", code: -1, userInfo: [NSLocalizedDescriptionKey: "Failed to create output format"]))
        }

        do {
            audioFile = try AVAudioFile(
                forWriting: outputURL,
                settings: outputFormat.settings
            )
        } catch {
            throw RecorderError.fileCreationFailed(error)
        }
        
        // Create converter to handle sample rate conversion
        guard let converter = AVAudioConverter(from: inputFormat, to: outputFormat) else {
            throw RecorderError.fileCreationFailed(NSError(domain: "GlassesRecorder", code: -2, userInfo: [NSLocalizedDescriptionKey: "Failed to create audio converter"]))
        }

        inputNode.installTap(onBus: 0, bufferSize: 4096, format: inputFormat) { [weak self] buffer, _ in
            guard let self, let file = self.audioFile else { return }
            
            // Convert input buffer to 16kHz
            let capacity = AVAudioFrameCount(Double(buffer.frameLength) * outputFormat.sampleRate / inputFormat.sampleRate)
            guard let convertedBuffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: capacity) else {
                return
            }
            
            var error: NSError?
            let inputBlock: AVAudioConverterInputBlock = { _, outStatus in
                outStatus.pointee = .haveData
                return buffer
            }
            
            converter.convert(to: convertedBuffer, error: &error, withInputFrom: inputBlock)
            
            if error == nil {
                try? file.write(from: convertedBuffer)
            }
        }

        do {
            try audioEngine.start()
        } catch {
            audioEngine.inputNode.removeTap(onBus: 0)
            audioFile = nil
            throw RecorderError.audioEngineStartFailed(error)
        }
        
        isRecording = true
        recordingStartTime = Date()
        
        // Auto-stop after duration if specified
        if let duration = duration {
            DispatchQueue.main.asyncAfter(deadline: .now() + duration) { [weak self] in
                self?.stopRecording()
            }
        }
    }

    public func stopRecording() {
        guard isRecording else {
            completionHandler?(.failure(RecorderError.notRecording))
            return
        }
        
        isRecording = false
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        audioFile = nil
        
        if let url = outputURL {
            completionHandler?(.success(url))
        }
        
        outputURL = nil
        completionHandler = nil
        recordingStartTime = nil
    }
    
    public func getRecordingDuration() -> TimeInterval? {
        guard let startTime = recordingStartTime else { return nil }
        return Date().timeIntervalSince(startTime)
    }
    
    public func isCurrentlyRecording() -> Bool {
        return isRecording
    }
}
