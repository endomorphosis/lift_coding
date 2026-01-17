import AVFoundation

public final class GlassesPlayer {
    private let audioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()

    public init() {
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: nil)
    }

    public func play(fileURL: URL) throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
        try session.setActive(true)

        let audioFile = try AVAudioFile(forReading: fileURL)
        if !audioEngine.isRunning {
            try audioEngine.start()
        }

        playerNode.stop()
        playerNode.scheduleFile(audioFile, at: nil)
        playerNode.play()
    }

    public func stop() {
        playerNode.stop()
        audioEngine.stop()
    }
}
