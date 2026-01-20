import ExpoModulesCore
import UIKit

public class ExpoGlassesAudioModule: Module {
  private let routeMonitor = AudioRouteMonitor()
  private let recorder = GlassesRecorder()
  private let player = GlassesPlayer()
  private var foregroundObserver: NSObjectProtocol?

  private var isRecording = false
  private var recordingFileURL: URL?
  private var recordingStartedAt: Date?
  private var recordingStopWorkItem: DispatchWorkItem?
  private var pendingStartRecordingPromise: Promise?
  
  public func definition() -> ModuleDefinition {
    Name("ExpoGlassesAudio")
    
    // Events
    Events("onAudioRouteChange", "onRecordingProgress", "onPlaybackStatus")
    
    // Get current audio route information
    Function("getAudioRoute") { () -> [String: Any] in
      let summary = routeMonitor.currentRouteSummary()
      let session = AVAudioSession.sharedInstance()
      
      // Parse the summary to extract device info
      let lines = summary.components(separatedBy: "\n")
      var inputDevice = "Unknown"
      var outputDevice = "Unknown"
      
      for line in lines {
        if line.hasPrefix("Input:") {
          inputDevice = line.replacingOccurrences(of: "Input: ", with: "")
        } else if line.hasPrefix("Output:") {
          outputDevice = line.replacingOccurrences(of: "Output: ", with: "")
        }
      }
      
      let isBluetoothConnected = outputDevice.contains("Bluetooth") || inputDevice.contains("Bluetooth")
      
      return [
        "inputDevice": inputDevice,
        "outputDevice": outputDevice,
        "sampleRate": session.sampleRate,
        "isBluetoothConnected": isBluetoothConnected
      ]
    }
    
    // Start recording audio
    AsyncFunction("startRecording") { (durationSeconds: Int, audioSourceString: String?, promise: Promise) in
      do {
        if self.isRecording {
          promise.reject("ERR_ALREADY_RECORDING", "Recording already in progress")
          return
        }

        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let filename = "glasses_recording_\(timestamp).wav"
        let fileURL = documentsPath.appendingPathComponent(filename)
        
        // Parse audio source
        let audioSource: AudioSource
        if let sourceStr = audioSourceString {
          audioSource = AudioSource(rawValue: sourceStr) ?? .auto
        } else {
          audioSource = .auto
        }

        try recorder.startRecording(outputURL: fileURL, audioSource: audioSource)

        self.isRecording = true
        self.recordingFileURL = fileURL
        self.recordingStartedAt = Date()
        self.pendingStartRecordingPromise = promise

        // Emit recording started event
        self.sendEvent("onRecordingProgress", [
          "isRecording": true,
          "duration": 0
        ])

        // Schedule stop after duration
        let workItem = DispatchWorkItem { [weak self] in
          self?.finishRecording(reason: "timer", promisedDurationSeconds: durationSeconds)
        }
        self.recordingStopWorkItem?.cancel()
        self.recordingStopWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(durationSeconds), execute: workItem)
      } catch {
        promise.reject("ERR_START_RECORDING", "Failed to start recording: \(error.localizedDescription)")
      }
    }
    
    // Stop recording
    AsyncFunction("stopRecording") { (promise: Promise) in
      if !self.isRecording {
        promise.resolve([
          "uri": "",
          "duration": 0,
          "size": 0
        ])
        return
      }

      self.finishRecording(reason: "manual", promisedDurationSeconds: nil, stopPromise: promise)
    }
    
    // Play audio file
    AsyncFunction("playAudio") { (fileUri: String, promise: Promise) in
      do {
        guard let url = URL(string: fileUri) else {
          promise.reject("ERR_INVALID_URI", "Invalid file URI")
          return
        }

        self.sendEvent("onPlaybackStatus", ["isPlaying": true])

        try player.play(fileURL: url) { [weak self] in
          self?.sendEvent("onPlaybackStatus", ["isPlaying": false])
        }
        promise.resolve(nil)
      } catch {
        self.sendEvent("onPlaybackStatus", [
          "isPlaying": false,
          "error": error.localizedDescription
        ])
        promise.reject("ERR_PLAY_AUDIO", "Failed to play audio: \(error.localizedDescription)")
      }
    }
    
    // Stop playback
    AsyncFunction("stopPlayback") { (promise: Promise) in
      player.stop()
      self.sendEvent("onPlaybackStatus", ["isPlaying": false])
      promise.resolve(nil)
    }
    
    // Setup audio route monitoring and lifecycle handling
    OnCreate {
      // Setup route monitoring
      routeMonitor.start { [weak self] summary in
        let session = AVAudioSession.sharedInstance()
        let lines = summary.components(separatedBy: "\n")
        var inputDevice = "Unknown"
        var outputDevice = "Unknown"
        
        for line in lines {
          if line.hasPrefix("Input:") {
            inputDevice = line.replacingOccurrences(of: "Input: ", with: "")
          } else if line.hasPrefix("Output:") {
            outputDevice = line.replacingOccurrences(of: "Output: ", with: "")
          }
        }
        
        let isBluetoothConnected = outputDevice.contains("Bluetooth") || inputDevice.contains("Bluetooth")
        
        self?.sendEvent("onAudioRouteChange", [
          "inputDevice": inputDevice,
          "outputDevice": outputDevice,
          "sampleRate": session.sampleRate,
          "isBluetoothConnected": isBluetoothConnected
        ])
      }
      
      // Observe app lifecycle events to re-apply audio session configuration
      foregroundObserver = NotificationCenter.default.addObserver(
        forName: UIApplication.willEnterForegroundNotification,
        object: nil,
        queue: .main
      ) { [weak self] _ in
        self?.reapplyAudioSessionConfiguration()
      }
    }
    
    OnDestroy {
      routeMonitor.stop()
      recorder.stopRecording()
      player.stop()
      recordingStopWorkItem?.cancel()
      recordingStopWorkItem = nil
      pendingStartRecordingPromise = nil
      recordingFileURL = nil
      recordingStartedAt = nil
      isRecording = false
      if let observer = foregroundObserver {
        NotificationCenter.default.removeObserver(observer)
      }
    }
  }

  private func finishRecording(
    reason: String,
    promisedDurationSeconds: Int?,
    stopPromise: Promise? = nil
  ) {
    guard isRecording else {
      stopPromise?.resolve([
        "uri": "",
        "duration": 0,
        "size": 0
      ])
      return
    }

    // Ensure we only finish once
    isRecording = false
    recordingStopWorkItem?.cancel()
    recordingStopWorkItem = nil

    recorder.stopRecording()

    let fileURL = recordingFileURL
    let startedAt = recordingStartedAt
    recordingFileURL = nil
    recordingStartedAt = nil

    let elapsed = startedAt.map { max(0, Date().timeIntervalSince($0)) } ?? 0
    let durationSeconds = promisedDurationSeconds ?? Int(elapsed.rounded())

    var fileSize = 0
    if let fileURL {
      do {
        let attributes = try FileManager.default.attributesOfItem(atPath: fileURL.path)
        fileSize = attributes[.size] as? Int ?? 0
      } catch {
        // If we can't read attributes, still return the URI.
      }
    }

    let result: [String: Any] = [
      "uri": fileURL?.absoluteString ?? "",
      "duration": durationSeconds,
      "size": fileSize
    ]

    // Emit recording stopped event
    sendEvent("onRecordingProgress", [
      "isRecording": false,
      "duration": durationSeconds
    ])

    // Resolve both the original startRecording promise (if any) and the explicit stopRecording promise.
    if let startPromise = pendingStartRecordingPromise {
      startPromise.resolve(result)
      pendingStartRecordingPromise = nil
    }
    stopPromise?.resolve(result)
  }
  
  private func reapplyAudioSessionConfiguration() {
    do {
      let session = AVAudioSession.sharedInstance()
      try session.setCategory(
        .playAndRecord,
        mode: .voiceChat,
        options: [.allowBluetooth, .defaultToSpeaker]
      )
      try session.setActive(true)
      if #available(iOS 15.0, *) {
        print("[ExpoGlassesAudio] Re-applied audio session configuration on foreground")
      }
    } catch {
      if #available(iOS 15.0, *) {
        print("[ExpoGlassesAudio] Failed to re-apply audio session: \(error)")
      }
    }
  }
}
