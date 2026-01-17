import AVFoundation
import Foundation

public final class GlassesPlayerBridge {
    private let audioEngine = AVAudioEngine()
    private let playerNode = AVAudioPlayerNode()
    private var completion: ((Error?) -> Void)?
    
    public init() {
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: nil)
    }
    
    public func playAudio(from fileURL: URL, completion: @escaping (Error?) -> Void) {
        self.completion = completion
        
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.allowBluetooth, .defaultToSpeaker])
            try session.setActive(true)
            
            let audioFile = try AVAudioFile(forReading: fileURL)
            
            if !audioEngine.isRunning {
                try audioEngine.start()
            }
            
            playerNode.stop()
            
            playerNode.scheduleFile(audioFile, at: nil) { [weak self] in
                DispatchQueue.main.async {
                    self?.completion?(nil)
                    self?.completion = nil
                }
            }
            
            playerNode.play()
        } catch {
            completion(error)
        }
    }
    
    public func stop() {
        playerNode.stop()
        audioEngine.stop()
        completion?(nil)
        completion = nil
    }
}
