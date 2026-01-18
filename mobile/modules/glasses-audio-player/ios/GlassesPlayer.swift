import AVFoundation

public final class GlassesPlayer {
    private let audioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var currentAudioFile: AVAudioFile?

    public init() {
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: nil)
    }

    public func play(fileURL: URL) throws {
        let session = AVAudioSession.sharedInstance()
        
        // Configure for Bluetooth playback with glasses
        try session.setCategory(
            .playAndRecord,
            mode: .voiceChat,
            options: [.allowBluetooth, .allowBluetoothA2DP]
        )
        try session.setActive(true)

        let audioFile = try AVAudioFile(forReading: fileURL)
        currentAudioFile = audioFile
        
        if !audioEngine.isRunning {
            try audioEngine.start()
        }

        playerNode.stop()
        playerNode.scheduleFile(audioFile, at: nil)
        playerNode.play()
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
