import AVFoundation
import Foundation

public final class GlassesRecorderBridge {
    private let audioEngine = AVAudioEngine()
    private var audioFile: AVAudioFile?
    private var completion: ((URL?, Error?) -> Void)?
    private var timer: Timer?
    private var outputURL: URL?
    
    public init() {}
    
    public func startRecording(duration: TimeInterval, completion: @escaping (URL?, Error?) -> Void) {
        self.completion = completion
        
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
            try session.setActive(true)
            
            // Create output file
            let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            let audioDir = documentsPath.appendingPathComponent("audio_diagnostics")
            try? FileManager.default.createDirectory(at: audioDir, withIntermediateDirectories: true)
            
            let timestamp = Int(Date().timeIntervalSince1970)
            outputURL = audioDir.appendingPathComponent("glasses_\(timestamp).wav")
            
            guard let outputURL = outputURL else {
                completion(nil, NSError(domain: "GlassesRecorder", code: -1, userInfo: [NSLocalizedDescriptionKey: "Failed to create output URL"]))
                return
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
            
            // Set up timer to stop recording after duration
            timer = Timer.scheduledTimer(withTimeInterval: duration, repeats: false) { [weak self] _ in
                self?.stopRecordingAndComplete()
            }
        } catch {
            completion(nil, error)
        }
    }
    
    public func stopRecording() {
        timer?.invalidate()
        timer = nil
        stopRecordingAndComplete()
    }
    
    private func stopRecordingAndComplete() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        audioFile = nil
        
        if let completion = completion, let url = outputURL {
            completion(url, nil)
            self.completion = nil
        }
    }
}
