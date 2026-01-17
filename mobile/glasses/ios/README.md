# iOS Implementation

This directory will contain the iOS-specific implementation of the Meta AI Glasses audio diagnostics.

## Files to Implement

### `GlassesAudioDiagnostics.swift`
Main view controller coordinating the diagnostics UI.

**Key responsibilities:**
- Present the diagnostics interface
- Coordinate between AudioRouteMonitor, GlassesRecorder, and GlassesPlayer
- Handle user interactions (record, play, export buttons)
- Display route information and status updates
- Manage permissions (microphone, Bluetooth)

**SwiftUI Example Structure:**
```swift
struct GlassesAudioDiagnosticsView: View {
    @StateObject private var viewModel = GlassesAudioDiagnosticsViewModel()
    
    var body: some View {
        // UI implementation
    }
}
```

### `AudioRouteMonitor.swift`
Monitors and reports current audio routing.

**Key responsibilities:**
- Observe AVAudioSession route change notifications
- Detect Bluetooth HFP/LE devices
- Format route information for display
- Provide callbacks for route updates

**Interface:**
```swift
class AudioRouteMonitor {
    func startMonitoring(updateHandler: @escaping (AudioRouteInfo) -> Void)
    func stopMonitoring()
    func getCurrentRoute() -> AudioRouteInfo
    func isBluetoothConnected() -> Bool
}
```

### `GlassesRecorder.swift`
Handles audio recording from Bluetooth microphone.

**Key responsibilities:**
- Configure AVAudioSession for Bluetooth input
- Use AVAudioEngine to capture audio
- Write WAV files with proper headers
- Provide recording level feedback
- Handle timed recordings

**Interface:**
```swift
class GlassesRecorder {
    func startRecording(duration: TimeInterval, completion: @escaping (URL?, Error?) -> Void)
    func stopRecording()
    func getRecordingLevel() -> Float  // 0.0 to 1.0
}
```

### `GlassesPlayer.swift`
Handles audio playback through Bluetooth speakers.

**Key responsibilities:**
- Configure AVAudioSession for Bluetooth output
- Use AVAudioEngine + AVAudioPlayerNode for playback
- Provide playback progress updates
- Handle stop/pause functionality

**Interface:**
```swift
class GlassesPlayer {
    func playAudio(from fileURL: URL, completion: @escaping (Error?) -> Void)
    func stop()
    func pause()
    func resume()
    func getPlaybackProgress() -> Double  // 0.0 to 1.0
}
```

## Implementation Notes

### AVAudioSession Configuration

For Bluetooth headset I/O:
```swift
let session = AVAudioSession.sharedInstance()
try session.setCategory(
    .playAndRecord,
    mode: .voiceChat,
    options: [.allowBluetooth, .defaultToSpeaker]
)
try session.setActive(true)
```

### WAV File Format

Use 16kHz, 16-bit, mono PCM:
```swift
let settings: [String: Any] = [
    AVFormatIDKey: kAudioFormatLinearPCM,
    AVSampleRateKey: 16000,
    AVNumberOfChannelsKey: 1,
    AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false
]
```

### File Storage

Save to Documents directory:
```swift
let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
let diagnosticsPath = documentsPath.appendingPathComponent("audio_diagnostics")
try FileManager.default.createDirectory(at: diagnosticsPath, withIntermediateDirectories: true)
```

### Permissions

Add to Info.plist:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Record audio from your Meta AI Glasses for diagnostics</string>
<key>NSBluetoothPeripheralUsageDescription</key>
<string>Connect to Meta AI Glasses for audio routing</string>
```

## Testing Checklist

- [ ] Test with Meta AI Glasses connected via Bluetooth
- [ ] Test route display updates on connect/disconnect
- [ ] Test recording and verify WAV file format
- [ ] Test playback through glasses speakers
- [ ] Test file export via share sheet
- [ ] Test interruption handling (phone calls)
- [ ] Test with no Bluetooth device connected
- [ ] Test with multiple Bluetooth devices
- [ ] Test background audio recording (if needed)

## References

- [Parent README](../README.md)
- [Audio Routing Documentation](../../../docs/meta-ai-glasses-audio-routing.md)
- [Apple AVAudioSession Documentation](https://developer.apple.com/documentation/avfoundation/avaudiosession)
- [Apple AVAudioEngine Documentation](https://developer.apple.com/documentation/avfoundation/avaudioengine)
