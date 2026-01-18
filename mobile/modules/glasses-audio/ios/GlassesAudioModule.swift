//
//  GlassesAudioModule.swift
//  Native module implementation for React Native
//

import Foundation
import React
import AVFoundation

@objc(GlassesAudioModule)
class GlassesAudioModule: RCTEventEmitter {
    
    private let routeMonitor = AudioRouteMonitor()
    private let recorder = GlassesRecorder()
    private let player = GlassesPlayer()
    
    private var lastRecordingURL: URL?
    
    override init() {
        super.init()
    }
    
    override func supportedEvents() -> [String]! {
        return ["audioRouteChanged", "recordingComplete", "playbackComplete"]
    }
    
    override static func requiresMainQueueSetup() -> Bool {
        return true
    }
    
    // MARK: - Audio Route Monitor
    
    @objc func startRouteMonitoring(_ resolve: @escaping RCTPromiseResolveBlock,
                                     rejecter reject: @escaping RCTPromiseRejectBlock) {
        routeMonitor.start { [weak self] summary in
            self?.sendEvent(withName: "audioRouteChanged", body: ["summary": summary])
        }
        resolve(nil)
    }
    
    @objc func stopRouteMonitoring(_ resolve: @escaping RCTPromiseResolveBlock,
                                    rejecter reject: @escaping RCTPromiseRejectBlock) {
        routeMonitor.stop()
        resolve(nil)
    }
    
    @objc func getCurrentRoute(_ resolve: @escaping RCTPromiseResolveBlock,
                               rejecter reject: @escaping RCTPromiseRejectBlock) {
        let summary = routeMonitor.currentRouteSummary()
        resolve(summary)
    }
    
    @objc func isBluetoothConnected(_ resolve: @escaping RCTPromiseResolveBlock,
                                     rejecter reject: @escaping RCTPromiseRejectBlock) {
        let isConnected = routeMonitor.isBluetoothConnected()
        resolve(isConnected)
    }
    
    @objc func getDetailedRouteInfo(_ resolve: @escaping RCTPromiseResolveBlock,
                                     rejecter reject: @escaping RCTPromiseRejectBlock) {
        let info = routeMonitor.getDetailedRouteInfo()
        resolve(info)
    }
    
    // MARK: - Recorder
    
    @objc func startRecording(_ duration: Double,
                              resolver resolve: @escaping RCTPromiseResolveBlock,
                              rejecter reject: @escaping RCTPromiseRejectBlock) {
        // Create output file URL
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let diagnosticsPath = documentsPath.appendingPathComponent("audio_diagnostics")
        
        do {
            try FileManager.default.createDirectory(at: diagnosticsPath, withIntermediateDirectories: true)
        } catch {
            reject("E_CREATE_DIR", "Failed to create diagnostics directory", error)
            return
        }
        
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let fileName = "glasses_test_\(timestamp).wav"
        let fileURL = diagnosticsPath.appendingPathComponent(fileName)
        
        do {
            try recorder.startRecording(outputURL: fileURL, duration: duration) { [weak self] result in
                switch result {
                case .success(let url):
                    self?.lastRecordingURL = url
                    self?.sendEvent(withName: "recordingComplete", body: [
                        "success": true,
                        "fileUrl": url.absoluteString,
                        "fileName": url.lastPathComponent
                    ])
                case .failure(let error):
                    self?.sendEvent(withName: "recordingComplete", body: [
                        "success": false,
                        "error": error.localizedDescription
                    ])
                }
            }
            
            resolve([
                "started": true,
                "duration": duration,
                "fileUrl": fileURL.absoluteString
            ])
        } catch {
            reject("E_RECORDING", "Failed to start recording", error)
        }
    }
    
    @objc func stopRecording(_ resolve: @escaping RCTPromiseResolveBlock,
                             rejecter reject: @escaping RCTPromiseRejectBlock) {
        recorder.stopRecording()
        
        if let url = lastRecordingURL {
            resolve([
                "fileUrl": url.absoluteString,
                "fileName": url.lastPathComponent
            ])
        } else {
            resolve(nil)
        }
    }
    
    @objc func isRecording(_ resolve: @escaping RCTPromiseResolveBlock,
                           rejecter reject: @escaping RCTPromiseRejectBlock) {
        resolve(recorder.isCurrentlyRecording())
    }
    
    @objc func getRecordingDuration(_ resolve: @escaping RCTPromiseResolveBlock,
                                     rejecter reject: @escaping RCTPromiseRejectBlock) {
        if let duration = recorder.getRecordingDuration() {
            resolve(duration)
        } else {
            resolve(0.0)
        }
    }
    
    // MARK: - Player
    
    @objc func playAudio(_ fileUri: String,
                         resolver resolve: @escaping RCTPromiseResolveBlock,
                         rejecter reject: @escaping RCTPromiseRejectBlock) {
        guard let fileURL = URL(string: fileUri) else {
            reject("E_INVALID_URL", "Invalid file URL", nil)
            return
        }
        
        do {
            try player.play(fileURL: fileURL) { [weak self] error in
                self?.sendEvent(withName: "playbackComplete", body: [
                    "success": error == nil,
                    "error": error?.localizedDescription ?? NSNull()
                ])
            }
            resolve(["started": true])
        } catch {
            reject("E_PLAYBACK", "Failed to play audio", error)
        }
    }
    
    @objc func stopPlayback(_ resolve: @escaping RCTPromiseResolveBlock,
                            rejecter reject: @escaping RCTPromiseRejectBlock) {
        player.stop()
        resolve(nil)
    }
    
    @objc func pausePlayback(_ resolve: @escaping RCTPromiseResolveBlock,
                             rejecter reject: @escaping RCTPromiseRejectBlock) {
        player.pause()
        resolve(nil)
    }
    
    @objc func resumePlayback(_ resolve: @escaping RCTPromiseResolveBlock,
                              rejecter reject: @escaping RCTPromiseRejectBlock) {
        player.resume()
        resolve(nil)
    }
    
    @objc func isPlaying(_ resolve: @escaping RCTPromiseResolveBlock,
                         rejecter reject: @escaping RCTPromiseRejectBlock) {
        resolve(player.isCurrentlyPlaying())
    }
    
    @objc func getPlaybackProgress(_ resolve: @escaping RCTPromiseResolveBlock,
                                    rejecter reject: @escaping RCTPromiseRejectBlock) {
        resolve(player.getPlaybackProgress())
    }
}
