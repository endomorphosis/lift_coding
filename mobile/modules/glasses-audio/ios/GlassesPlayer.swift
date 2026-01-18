import AVFoundation

public final class GlassesPlayer {
    private let audioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var audioFile: AVAudioFile?
    private var isPlaying = false
    private var completionHandler: ((Error?) -> Void)?
    
    public enum PlayerError: LocalizedError {
        case alreadyPlaying
        case notPlaying
        case audioSessionSetupFailed(Error)
        case audioEngineStartFailed(Error)
        case fileLoadFailed(Error)
        case noBluetoothDevice
        
        public var errorDescription: String? {
            switch self {
            case .alreadyPlaying:
                return "Audio is already playing"
            case .notPlaying:
                return "No audio is currently playing"
            case .audioSessionSetupFailed(let error):
                return "Failed to set up audio session: \(error.localizedDescription)"
            case .audioEngineStartFailed(let error):
                return "Failed to start audio engine: \(error.localizedDescription)"
            case .fileLoadFailed(let error):
                return "Failed to load audio file: \(error.localizedDescription)"
            case .noBluetoothDevice:
                return "No Bluetooth audio device connected"
            }
        }
    }

    public init() {
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: nil)
    }

    public func play(fileURL: URL, completion: ((Error?) -> Void)? = nil) throws {
        guard !isPlaying else {
            throw PlayerError.alreadyPlaying
        }
        
        self.completionHandler = completion
        
        // Configure audio session for Bluetooth output
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
            try session.setActive(true)
        } catch {
            throw PlayerError.audioSessionSetupFailed(error)
        }
        
        // Verify Bluetooth output is available
        let currentRoute = session.currentRoute
        let hasBluetoothOutput = currentRoute.outputs.contains { output in
            output.portType == .bluetoothHFP || output.portType == .bluetoothLE || output.portType == .bluetoothA2DP
        }
        
        // Allow fallback to built-in speaker for development/testing
        if !hasBluetoothOutput {
            print("⚠️ Warning: No Bluetooth audio device detected. Using built-in speaker.")
        }

        do {
            audioFile = try AVAudioFile(forReading: fileURL)
        } catch {
            throw PlayerError.fileLoadFailed(error)
        }
        
        guard let audioFile = audioFile else {
            throw PlayerError.fileLoadFailed(NSError(domain: "GlassesPlayer", code: -1, userInfo: [NSLocalizedDescriptionKey: "Audio file is nil"]))
        }

        if !audioEngine.isRunning {
            do {
                try audioEngine.start()
            } catch {
                throw PlayerError.audioEngineStartFailed(error)
            }
        }

        playerNode.stop()
        
        // Schedule file and track completion
        playerNode.scheduleFile(audioFile, at: nil) { [weak self] in
            DispatchQueue.main.async {
                self?.isPlaying = false
                self?.completionHandler?(nil)
                self?.completionHandler = nil
            }
        }
        
        playerNode.play()
        isPlaying = true
    }

    public func stop() {
        playerNode.stop()
        audioEngine.stop()
        isPlaying = false
        audioFile = nil
        completionHandler?(nil)
        completionHandler = nil
    }
    
    public func pause() {
        guard isPlaying else { return }
        playerNode.pause()
        isPlaying = false
    }
    
    public func resume() {
        guard !isPlaying else { return }
        playerNode.play()
        isPlaying = true
    }
    
    public func isCurrentlyPlaying() -> Bool {
        return isPlaying
    }
    
    public func getPlaybackProgress() -> Double {
        guard let audioFile = audioFile, let lastRenderTime = playerNode.lastRenderTime,
              let playerTime = playerNode.playerTime(forNodeTime: lastRenderTime) else {
            return 0.0
        }
        
        let sampleRate = audioFile.processingFormat.sampleRate
        let currentTime = Double(playerTime.sampleTime) / sampleRate
        let totalTime = Double(audioFile.length) / sampleRate
        
        return min(max(currentTime / totalTime, 0.0), 1.0)
    }
}
