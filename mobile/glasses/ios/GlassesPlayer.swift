import AVFoundation

public final class GlassesPlayer {
    private let audioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var currentAudioFile: AVAudioFile?

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
        
        // Configure for Bluetooth playback with glasses
        // .allowBluetoothA2DP enables high-quality audio routing to Bluetooth devices
        try session.setCategory(
            .playAndRecord,
            mode: .voiceChat,
            options: [.allowBluetooth, .allowBluetoothA2DP]
        )
        try session.setActive(true)

        let audioFile = try AVAudioFile(forReading: fileURL)
        currentAudioFile = audioFile
        
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
        if audioEngine.isRunning {
            audioEngine.stop()
        }
        currentAudioFile = nil
    }
    
    public func isPlaying() -> Bool {
        return playerNode.isPlaying
    }
}
