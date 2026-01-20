import AVFoundation

public final class GlassesPlayer {
    private let audioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var isInterrupted = false
    private var shouldResumeAfterInterruption = false

    public init() {
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: nil)
        setupInterruptionHandling()
    }
    
    private func setupInterruptionHandling() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleInterruption),
            name: AVAudioSession.interruptionNotification,
            object: AVAudioSession.sharedInstance()
        )
    }
    
    @objc private func handleInterruption(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let typeValue = userInfo[AVAudioSessionInterruptionTypeKey] as? UInt,
              let type = AVAudioSession.InterruptionType(rawValue: typeValue) else {
            return
        }
        
        switch type {
        case .began:
            // Interruption began (phone call, Siri, etc.)
            isInterrupted = true
            shouldResumeAfterInterruption = playerNode.isPlaying
            if playerNode.isPlaying {
                playerNode.pause()
                if #available(iOS 15.0, *) {
                    print("[GlassesPlayer] Interruption began - paused playback")
                }
            }
            
        case .ended:
            // Interruption ended
            isInterrupted = false
            
            guard let optionsValue = userInfo[AVAudioSessionInterruptionOptionKey] as? UInt else {
                return
            }
            let options = AVAudioSession.InterruptionOptions(rawValue: optionsValue)
            
            if options.contains(.shouldResume) {
                // Re-activate audio session
                do {
                    let session = AVAudioSession.sharedInstance()
                    try session.setActive(true)
                    
                    // Resume playback if it was playing before interruption
                    if shouldResumeAfterInterruption {
                        playerNode.play()
                        if #available(iOS 15.0, *) {
                            print("[GlassesPlayer] Interruption ended - resumed playback")
                        }
                    }
                } catch {
                    if #available(iOS 15.0, *) {
                        print("[GlassesPlayer] Failed to re-activate session after interruption: \(error)")
                    }
                }
            }
            shouldResumeAfterInterruption = false
            
        @unknown default:
            break
        }
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
        
        // Only play if not currently interrupted
        if !isInterrupted {
            playerNode.play()
        } else {
            shouldResumeAfterInterruption = true
            if #available(iOS 15.0, *) {
                print("[GlassesPlayer] Playback deferred due to active interruption")
            }
        }
    }

    public func stop() {
        shouldResumeAfterInterruption = false
        playerNode.stop()
        audioEngine.stop()
    }
    
    deinit {
        NotificationCenter.default.removeObserver(self)
    }
}
