import ExpoModulesCore

public class ExpoGlassesAudioModule: Module {
  private let routeMonitor = AudioRouteMonitor()
  private let recorder = GlassesRecorder()
  private let player = GlassesPlayer()
  
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
    AsyncFunction("startRecording") { (durationSeconds: Int, promise: Promise) in
      do {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let timestamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
        let filename = "glasses_recording_\(timestamp).wav"
        let fileURL = documentsPath.appendingPathComponent(filename)
        
        try recorder.startRecording(outputURL: fileURL)
        
        // Schedule stop after duration
        DispatchQueue.main.asyncAfter(deadline: .now() + .seconds(durationSeconds)) {
          self.recorder.stopRecording()
          
          do {
            let attributes = try FileManager.default.attributesOfItem(atPath: fileURL.path)
            let fileSize = attributes[.size] as? Int ?? 0
            
            promise.resolve([
              "uri": fileURL.absoluteString,
              "duration": durationSeconds,
              "size": fileSize
            ])
          } catch {
            promise.reject("ERR_FILE_ATTRIBUTES", "Failed to get file attributes: \(error.localizedDescription)")
          }
        }
      } catch {
        promise.reject("ERR_START_RECORDING", "Failed to start recording: \(error.localizedDescription)")
      }
    }
    
    // Stop recording
    AsyncFunction("stopRecording") { (promise: Promise) in
      recorder.stopRecording()
      promise.resolve([
        "uri": "",
        "duration": 0,
        "size": 0
      ])
    }
    
    // Play audio file
    AsyncFunction("playAudio") { (fileUri: String, promise: Promise) in
      do {
        guard let url = URL(string: fileUri) else {
          promise.reject("ERR_INVALID_URI", "Invalid file URI")
          return
        }
        
        try player.play(fileURL: url)
        promise.resolve(nil)
      } catch {
        promise.reject("ERR_PLAY_AUDIO", "Failed to play audio: \(error.localizedDescription)")
      }
    }
    
    // Stop playback
    AsyncFunction("stopPlayback") { (promise: Promise) in
      player.stop()
      promise.resolve(nil)
    }
    
    // Setup audio route monitoring
    OnCreate {
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
    }
    
    OnDestroy {
      routeMonitor.stop()
      recorder.stopRecording()
      player.stop()
    }
  }
}
