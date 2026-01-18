import ExpoModulesCore

public class GlassesAudioPlayerModule: Module {
  private let player = GlassesPlayer()
  
  public func definition() -> ModuleDefinition {
    Name("GlassesAudioPlayer")
    
    // Play audio from a file URI
    AsyncFunction("playAudio") { (fileUri: String) in
      return try await withCheckedThrowingContinuation { continuation in
        do {
          guard let url = URL(string: fileUri) else {
            continuation.resume(throwing: NSError(
              domain: "GlassesAudioPlayer",
              code: 1,
              userInfo: [NSLocalizedDescriptionKey: "Invalid file URI: \(fileUri)"]
            ))
            return
          }
          
          // Convert file:// URI to local file path if needed
          let fileURL: URL
          if url.scheme == "file" {
            fileURL = url
          } else if !url.absoluteString.starts(with: "/") {
            // Assume it's a relative path
            fileURL = URL(fileURLWithPath: url.absoluteString)
          } else {
            fileURL = URL(fileURLWithPath: url.absoluteString)
          }
          
          try player.play(fileURL: fileURL)
          continuation.resume()
        } catch {
          continuation.resume(throwing: error)
        }
      }
    }
    
    // Stop audio playback
    AsyncFunction("stopAudio") {
      player.stop()
    }
    
    // Check if audio is currently playing
    AsyncFunction("isPlaying") { () -> Bool in
      return player.isPlaying()
    }
  }
}
