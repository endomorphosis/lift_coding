import ExpoModulesCore
import AVFoundation

public class GlassesAudioModule: Module {
  private let audioRouteMonitor = AudioRouteMonitor()
  private var recorder: GlassesRecorder?
  private var player: GlassesPlayer?
  
  // Define the module name
  public func definition() -> ModuleDefinition {
    Name("GlassesAudio")
    
    // Define events this module can emit
    Events("onAudioRouteChange")
    
    // Start monitoring audio route changes
    AsyncFunction("startMonitoring") { (promise: Promise) in
      self.audioRouteMonitor.start { [weak self] routeSummary in
        // Parse the route summary and emit event
        let route = self?.parseRouteSummary(routeSummary) ?? [:]
        self?.sendEvent("onAudioRouteChange", [
          "route": route
        ])
      }
      
      // Return current route immediately
      let currentRoute = self.parseRouteSummary(self.audioRouteMonitor.currentRouteSummary())
      promise.resolve(currentRoute)
    }
    
    // Stop monitoring
    AsyncFunction("stopMonitoring") {
      self.audioRouteMonitor.stop()
    }
    
    // Get current route without starting monitoring
    AsyncFunction("getCurrentRoute") { () -> [String: Any] in
      return self.parseRouteSummary(self.audioRouteMonitor.currentRouteSummary())
    }
    
    // Start recording
    AsyncFunction("startRecording") { (outputPath: String, promise: Promise) in
      do {
        let url = URL(fileURLWithPath: outputPath)
        self.recorder = GlassesRecorder()
        try self.recorder?.startRecording(outputURL: url)
        promise.resolve(nil)
      } catch {
        promise.reject("RECORDING_ERROR", "Failed to start recording: \(error.localizedDescription)")
      }
    }
    
    // Stop recording
    AsyncFunction("stopRecording") {
      self.recorder?.stopRecording()
      self.recorder = nil
    }
    
    // Play audio
    AsyncFunction("playAudio") { (filePath: String, promise: Promise) in
      do {
        let url = URL(fileURLWithPath: filePath)
        self.player = GlassesPlayer()
        try self.player?.play(fileURL: url)
        promise.resolve(nil)
      } catch {
        promise.reject("PLAYBACK_ERROR", "Failed to play audio: \(error.localizedDescription)")
      }
    }
    
    // Stop playback
    AsyncFunction("stopPlayback") {
      self.player?.stop()
      self.player = nil
    }
  }
  
  // Helper to parse route summary into structured data
  private func parseRouteSummary(_ summary: String) -> [String: Any] {
    let session = AVAudioSession.sharedInstance()
    
    let inputs = session.currentRoute.inputs.map { port in
      "\(port.portName) (\(port.portType.rawValue))"
    }
    
    let outputs = session.currentRoute.outputs.map { port in
      "\(port.portName) (\(port.portType.rawValue))"
    }
    
    return [
      "inputs": inputs.isEmpty ? ["None"] : inputs,
      "outputs": outputs.isEmpty ? ["None"] : outputs,
      "sampleRate": session.sampleRate
    ]
  }
}
