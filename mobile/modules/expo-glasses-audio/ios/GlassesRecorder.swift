import AVFoundation

public final class GlassesRecorder {
    private let audioEngine = AVAudioEngine()
    private var audioFile: AVAudioFile?
    private var isInterrupted = false
    private var shouldResumeAfterInterruption = false

    public init() {
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
            shouldResumeAfterInterruption = audioEngine.isRunning
            if audioEngine.isRunning {
                audioEngine.pause()
                if #available(iOS 15.0, *) {
                    print("[GlassesRecorder] Interruption began - paused recording")
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
                    
                    // Resume recording if it was recording before interruption
                    if shouldResumeAfterInterruption && !audioEngine.isRunning {
                        try audioEngine.start()
                        if #available(iOS 15.0, *) {
                            print("[GlassesRecorder] Interruption ended - resumed recording")
                        }
                        // Clear the flag only after successful resumption
                        shouldResumeAfterInterruption = false
                    }
                } catch {
                    shouldResumeAfterInterruption = false
                    if #available(iOS 15.0, *) {
                        print("[GlassesRecorder] Failed to re-activate session after interruption: \(error)")
                    }
                }
            }
            
        @unknown default:
            break
        }
    }

    public func startRecording(outputURL: URL) throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
        try session.setActive(true)

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

        // Only start if not currently interrupted
        if !isInterrupted {
            try audioEngine.start()
        } else {
            shouldResumeAfterInterruption = true
            if #available(iOS 15.0, *) {
                print("[GlassesRecorder] Recording deferred due to active interruption")
            }
        }
    }

    public func stopRecording() {
        shouldResumeAfterInterruption = false
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        audioFile = nil
    }
    
    deinit {
        NotificationCenter.default.removeObserver(self)
    }
}
