import Foundation
import React
import AVFoundation

@objc(GlassesAudioModule)
class GlassesAudioModule: RCTEventEmitter {
    
    private var routeMonitor: AudioRouteMonitor?
    private var recorder: GlassesRecorderBridge?
    private var player: GlassesPlayerBridge?
    private var recordingTimer: Timer?
    private var isRecording = false
    
    override init() {
        super.init()
        self.routeMonitor = AudioRouteMonitor()
        self.recorder = GlassesRecorderBridge()
        self.player = GlassesPlayerBridge()
    }
    
    override func supportedEvents() -> [String]! {
        return ["onRouteChange", "onRecordingComplete", "onPlaybackComplete"]
    }
    
    @objc
    func startMonitoring(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            
            self.routeMonitor?.start { [weak self] routeSummary in
                self?.sendEvent(withName: "onRouteChange", body: ["route": routeSummary])
            }
            
            let currentRoute = self.routeMonitor?.currentRouteSummary() ?? "Unknown"
            resolve(currentRoute)
        }
    }
    
    @objc
    func stopMonitoring(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async { [weak self] in
            self?.routeMonitor?.stop()
            resolve(nil)
        }
    }
    
    @objc
    func getCurrentRoute(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        DispatchQueue.main.async { [weak self] in
            let currentRoute = self?.routeMonitor?.currentRouteSummary() ?? "Unknown"
            resolve(currentRoute)
        }
    }
    
    @objc
    func startRecording(_ durationSeconds: Double, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        guard !isRecording else {
            reject("RECORDING_IN_PROGRESS", "Recording is already in progress", nil)
            return
        }
        
        isRecording = true
        
        recorder?.startRecording(duration: TimeInterval(durationSeconds)) { [weak self] fileURL, error in
            guard let self = self else { return }
            self.isRecording = false
            
            if let error = error {
                self.sendEvent(withName: "onRecordingComplete", body: [
                    "error": error.localizedDescription
                ])
                reject("RECORDING_FAILED", error.localizedDescription, error)
            } else if let fileURL = fileURL {
                let fileUri = fileURL.path
                self.sendEvent(withName: "onRecordingComplete", body: [
                    "fileUri": fileUri
                ])
                resolve(fileUri)
            } else {
                let error = NSError(domain: "GlassesAudioModule", code: -1, userInfo: [NSLocalizedDescriptionKey: "Recording failed without error"])
                self.sendEvent(withName: "onRecordingComplete", body: [
                    "error": "Recording failed"
                ])
                reject("RECORDING_FAILED", "Recording failed without error", error)
            }
        }
    }
    
    @objc
    func stopRecording(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        guard isRecording else {
            reject("NO_RECORDING", "No recording in progress", nil)
            return
        }
        
        recorder?.stopRecording()
        isRecording = false
        resolve(nil)
    }
    
    @objc
    func playAudio(_ fileUri: String, resolver resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        let fileURL = URL(fileURLWithPath: fileUri)
        
        player?.playAudio(from: fileURL) { [weak self] error in
            if let error = error {
                self?.sendEvent(withName: "onPlaybackComplete", body: [
                    "error": error.localizedDescription
                ])
                reject("PLAYBACK_FAILED", error.localizedDescription, error)
            } else {
                self?.sendEvent(withName: "onPlaybackComplete", body: [:])
                resolve(nil)
            }
        }
    }
    
    @objc
    func stopPlayback(_ resolve: @escaping RCTPromiseResolveBlock, rejecter reject: @escaping RCTPromiseRejectBlock) {
        player?.stop()
        resolve(nil)
    }
}
