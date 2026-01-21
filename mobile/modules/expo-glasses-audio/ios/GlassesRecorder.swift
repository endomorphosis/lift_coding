import AVFoundation

public enum AudioSource: String {
    case phone = "phone"
    case glasses = "glasses"
    case auto = "auto"
}

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

    public func startRecording(outputURL: URL, audioSource: AudioSource = .auto) throws {
        let session = AVAudioSession.sharedInstance()
        
        // Configure audio session based on audio source preference
        switch audioSource {
        case .phone:
            // Force phone microphone - don't allow Bluetooth
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker])
            
        case .glasses:
            // Prefer Bluetooth microphone
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .allowBluetoothA2DP])
            
        case .auto:
            // Auto mode - allow Bluetooth but don't force it
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
        }

        // Prefer a 16kHz mono capture format for STT and backend consistency.
        // The underlying hardware route may not support it directly; AVAudioEngine
        // will format-convert buffers delivered to the tap.
        try? session.setPreferredSampleRate(16000)
        try session.setActive(true)

        switch audioSource {
        case .phone:
            // Prefer built-in output (and avoid surprising Bluetooth routes).
            try? session.overrideOutputAudioPort(.speaker)
        case .glasses:
            // Check if Bluetooth is actually available
            let currentRoute = session.currentRoute
            let hasBluetoothInput = currentRoute.inputs.contains { input in
                input.portType == .bluetoothHFP || input.portType == .bluetoothLE || input.portType == .bluetoothA2DP
            }
            if !hasBluetoothInput {
                print("⚠️ Warning: Glasses/Bluetooth source selected but no Bluetooth device detected. Falling back to built-in mic.")
            }
        case .auto:
            break
        }

        guard let desiredFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16000,
            channels: 1,
            interleaved: true
        ) else {
            throw NSError(
                domain: "GlassesRecorder",
                code: -1,
                userInfo: [NSLocalizedDescriptionKey: "Failed to create desired audio format"]
            )
        }

        let inputNode = audioEngine.inputNode

        audioFile = try AVAudioFile(forWriting: outputURL, settings: desiredFormat.settings)

        inputNode.installTap(onBus: 0, bufferSize: 4096, format: desiredFormat) { [weak self] buffer, _ in
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
