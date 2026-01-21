# Meta AI Glasses Audio Diagnostics

This directory contains audio diagnostics for testing and validating Bluetooth audio routing with Meta AI Glasses (Ray-Ban Meta Smart Glasses).

## Status (PR-049)

✅ **Implemented:**
- iOS `GlassesPlayer.swift` with AVAudioEngine and Bluetooth routing
- React Native bridge using Expo Modules API
- JavaScript hooks for easy integration (`useGlassesPlayer.js`)
- UI integration in `GlassesDiagnosticsScreen.js`
- Bluetooth permissions in `app.json`
- Comprehensive build & test documentation

⏳ **Pending:**
- Physical device testing with Meta AI Glasses
- Playback progress tracking
- Audio interruption handling
- Android implementation

📖 **Documentation:**
- [Build & Test Guide](../BUILD_AND_TEST_GLASSES_PLAYER.md)
- [Module README](../modules/expo-glasses-audio/README.md)
- [Implementation TODO](TODO.md)

## Purpose

Provide a diagnostic interface within the mobile companion app to:
1. **Display current audio route** (Bluetooth headset, phone speaker, etc.)
2. **Record audio samples** from glasses microphone at 16kHz WAV
3. **Play back recordings** through glasses speakers
4. **Monitor Bluetooth connection** in real-time
5. **Toggle DEV mode** for rapid iteration with phone mic/speaker

## Quick Start

### For iOS Development

1. **Build development client**:
   ```bash
   cd mobile
   npx expo prebuild --clean
   npx expo run:ios
   ```

2. **Pair Meta AI Glasses**:
   - Open iOS Settings > Bluetooth
   - Pair your Meta AI Glasses
   - Ensure they're connected

3. **Open Diagnostics Screen**:
   - Launch app
   - Navigate to "Glasses Diagnostics" tab
   - Toggle Glasses mode (disable DEV mode)

4. **Test Recording**:
   - Verify Bluetooth connection indicator is green
   - Tap "Start Recording"
   - Speak into glasses microphone
   - Recording auto-stops after 10 seconds
   - Audio saved as 16kHz WAV

5. **Test Playback**:
   - Tap "Play Last Recording"
   - Audio plays through glasses speakers
   - Verify audio quality

## Architecture

```
mobile/glasses/
├── README.md                           # This file
├── TODO.md                             # Implementation checklist
├── IMPLEMENTATION_STATUS.md            # Detailed status
├── UI_PREVIEW.md                       # UI mockups
├── ios/                                # iOS implementation ✅
│   ├── IMPLEMENTATION.md               # iOS implementation guide
│   ├── AudioRouteMonitor.swift         # Route monitoring
│   ├── GlassesRecorder.swift           # 16kHz WAV recording
│   ├── GlassesPlayer.swift             # Playback control
│   └── GlassesAudioDiagnostics.swift   # Native diagnostics UI
└── android/                            # Android implementation ⏳
    ├── AudioRouteMonitor.kt
    ├── GlassesRecorder.kt
    ├── GlassesPlayer.kt
    └── GlassesAudioDiagnostics.kt

mobile/modules/expo-glasses-audio/      # Expo module (source of truth)
├── index.ts                            # JS/TS API surface
├── ios/                                # iOS native implementation
└── android/                            # Android native implementation
```

## Features

### 1. Audio Route Display

**Purpose**: Show real-time audio I/O route information to verify Bluetooth connection.

**iOS Display Format:**
```
Audio Input: Ray-Ban Meta (BluetoothHFP)
Audio Output: Ray-Ban Meta (BluetoothHFP)
Sample Rate: 16000 Hz
Status: ✓ Connected
```

**Android Display Format:**
```
Audio Input: Ray-Ban Meta Smart Glasses (TYPE_BLUETOOTH_SCO)
Audio Output: Ray-Ban Meta Smart Glasses (TYPE_BLUETOOTH_SCO)
SCO Status: Connected
Audio Mode: MODE_IN_COMMUNICATION
```

**Auto-refresh**: Updates every 2 seconds or on route change notification.

### 2. Audio Recording

**Features:**
- Record button with visual feedback (recording indicator)
- Duration: 5-10 seconds (configurable)
- Format: 16kHz, 16-bit, mono PCM WAV
- Automatic Bluetooth route selection
- Recording level meter (visual feedback)
- Save to app's documents directory

**User Flow:**
1. User taps "Record Test Audio"
2. App verifies Bluetooth connection (shows error if not connected)
3. Recording starts with visual countdown (10, 9, 8...)
4. User speaks test phrase: "Testing Meta AI Glasses audio"
5. Recording stops automatically after duration
6. File saved with timestamp: `glasses_test_20260117_084500.wav`
7. Success message displayed with file location

### 3. Audio Playback

**Features:**
- Play last recorded sample
- Playback through current audio route (glasses speakers)
- Visual playback indicator
- Stop button to interrupt playback
- Volume control

**User Flow:**
1. User taps "Play Last Recording"
2. App verifies audio file exists
3. Playback starts through glasses speakers
4. Progress indicator shows playback position
5. Playback completes or user stops manually

### 4. File Export

**Features:**
- List all recorded samples
- Export via share sheet (iOS) / share intent (Android)
- Send to other apps (email, cloud storage, etc.)
- Delete individual files

**User Flow:**
1. User taps "Export Recordings"
2. List of recorded files displayed with metadata (date, size, duration)
3. User selects file(s) to export
4. System share dialog appears
5. User chooses destination (AirDrop, email, Files app, etc.)

## Implementation Guide

### iOS Implementation

**File: `ios/GlassesAudioDiagnostics.swift`**

Main view controller coordinating the diagnostics UI.

```swift
import UIKit
import AVFoundation

class GlassesAudioDiagnosticsViewController: UIViewController {
    // MARK: - Properties
    private let routeMonitor = AudioRouteMonitor()
    private let recorder = GlassesRecorder()
    private let player = GlassesPlayer()
    
    // MARK: - UI Components
    private let routeLabel = UILabel()
    private let recordButton = UIButton()
    private let playButton = UIButton()
    private let exportButton = UIButton()
    private let statusLabel = UILabel()
    
    // MARK: - Lifecycle
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        startMonitoring()
    }
    
    // Implementation details in ios/GlassesAudioDiagnostics.swift
}
```

**File: `ios/AudioRouteMonitor.swift`**

Monitors and reports current audio route.

```swift
import AVFoundation

class AudioRouteMonitor {
    private var updateHandler: ((String) -> Void)?
    
    func startMonitoring(updateHandler: @escaping (String) -> Void) {
        self.updateHandler = updateHandler
        
        // Set up route change observer
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleRouteChange),
            name: AVAudioSession.routeChangeNotification,
            object: nil
        )
        
        // Initial update
        updateHandler(getCurrentRoute())
    }
    
    func getCurrentRoute() -> String {
        // Implementation in ios/AudioRouteMonitor.swift
    }
    
    @objc private func handleRouteChange() {
        updateHandler?(getCurrentRoute())
    }
}
```

**File: `ios/GlassesRecorder.swift`**

Handles audio recording from glasses microphone.

```swift
import AVFoundation

class GlassesRecorder {
    private var audioEngine: AVAudioEngine?
    private var audioFile: AVAudioFile?
    
    func startRecording(duration: TimeInterval, completion: @escaping (URL?, Error?) -> Void) {
        // Configure audio session for Bluetooth headset input
        // Start recording with AVAudioEngine
        // Save to WAV file
        // Implementation in ios/GlassesRecorder.swift
    }
    
    func stopRecording() {
        // Stop recording and finalize file
    }
}
```

**File: `ios/GlassesPlayer.swift`**

Handles audio playback through glasses speakers.

```swift
import AVFoundation

class GlassesPlayer {
    private var audioEngine: AVAudioEngine?
    private var playerNode: AVAudioPlayerNode?
    
    func playAudio(from fileURL: URL, completion: @escaping (Error?) -> Void) {
        // Configure audio session for Bluetooth headset output
        // Play audio through AVAudioPlayerNode
        // Implementation in ios/GlassesPlayer.swift
    }
    
    func stop() {
        // Stop playback
    }
}
```

### Android Implementation

**File: `android/GlassesAudioDiagnostics.kt`**

Main activity/fragment for diagnostics UI.

```kotlin
import android.os.Bundle
import androidx.fragment.app.Fragment
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup

class GlassesAudioDiagnosticsFragment : Fragment() {
    private lateinit var routeMonitor: AudioRouteMonitor
    private lateinit var recorder: GlassesRecorder
    private lateinit var player: GlassesPlayer
    
    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        val view = inflater.inflate(R.layout.fragment_glasses_diagnostics, container, false)
        
        // Initialize components
        routeMonitor = AudioRouteMonitor(requireContext())
        recorder = GlassesRecorder(requireContext())
        player = GlassesPlayer(requireContext())
        
        setupUI(view)
        startMonitoring()
        
        return view
    }
    
    // Implementation details in android/GlassesAudioDiagnostics.kt
}
```

**File: `android/AudioRouteMonitor.kt`**

Monitors and reports current audio route.

```kotlin
import android.content.Context
import android.media.AudioManager
import android.media.AudioDeviceInfo

class AudioRouteMonitor(private val context: Context) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    
    fun getCurrentRoute(): String {
        val devices = audioManager.getDevices(AudioManager.GET_DEVICES_ALL)
        val inputs = devices.filter { it.isSource }
        val outputs = devices.filter { it.isSink }
        
        // Format route information
        // Implementation in android/AudioRouteMonitor.kt
    }
    
    fun startMonitoring(callback: (String) -> Unit) {
        // Register audio device callback
        // Implementation in android/AudioRouteMonitor.kt
    }
}
```

**File: `android/GlassesRecorder.kt`**

Handles audio recording from glasses microphone.

```kotlin
import android.content.Context
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.AudioFormat
import java.io.File

class GlassesRecorder(private val context: Context) {
    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    
    fun startRecording(duration: Int, callback: (File?, Exception?) -> Unit) {
        // Set up AudioManager for Bluetooth SCO
        // Create AudioRecord with VOICE_COMMUNICATION source
        // Record to WAV file
        // Implementation in android/GlassesRecorder.kt
    }
    
    fun stopRecording() {
        // Stop recording and finalize file
    }
}
```

**File: `android/GlassesPlayer.kt`**

Handles audio playback through glasses speakers.

```kotlin
import android.content.Context
import android.media.AudioTrack
import android.media.AudioAttributes
import android.media.AudioFormat
import java.io.File

class GlassesPlayer(private val context: Context) {
    private var audioTrack: AudioTrack? = null
    
    fun playAudio(file: File, callback: (Exception?) -> Unit) {
        // Set up AudioManager for Bluetooth SCO
        // Create AudioTrack with VOICE_COMMUNICATION usage
        // Play audio file
        // Implementation in android/GlassesPlayer.kt
    }
    
    fun stop() {
        // Stop playback
    }
}
```

## UI Mockup

```
┌─────────────────────────────────────┐
│  Meta AI Glasses Audio Diagnostics │
├─────────────────────────────────────┤
│                                     │
│  📱 Audio Route                     │
│  ┌───────────────────────────────┐ │
│  │ Input: Ray-Ban Meta           │ │
│  │ Output: Ray-Ban Meta          │ │
│  │ Status: ✓ Connected           │ │
│  └───────────────────────────────┘ │
│                                     │
│  🎤 Record Test Audio               │
│  ┌───────────────────────────────┐ │
│  │  [  Record (10s)  ]           │ │
│  │                               │ │
│  │  ⚫ Ready to record            │ │
│  └───────────────────────────────┘ │
│                                     │
│  🔊 Playback                        │
│  ┌───────────────────────────────┐ │
│  │  [  Play Last  ]  [  Stop  ]  │ │
│  │                               │ │
│  │  Last: glasses_test_..._wav   │ │
│  └───────────────────────────────┘ │
│                                     │
│  📤 Export                          │
│  ┌───────────────────────────────┐ │
│  │  [  View All Recordings  ]    │ │
│  │  [  Export Last Recording  ]  │ │
│  └───────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

## Testing Workflow

### Prerequisites
1. Meta AI Glasses paired and connected via Bluetooth
2. App has microphone and Bluetooth permissions
3. Glasses are charged and in range

### Test Steps

1. **Launch Diagnostics Screen**
   - Navigate to Settings > Audio Diagnostics
   - Verify route display shows Bluetooth connection

2. **Test Recording**
   - Tap "Record (10s)"
   - Speak clearly: "Testing Meta AI Glasses microphone one two three"
   - Wait for recording to complete
   - Verify success message and file saved

3. **Test Playback**
   - Tap "Play Last"
   - Verify audio plays through glasses speakers
   - Verify audio quality is clear
   - Tap "Stop" to interrupt

4. **Test Export**
   - Tap "View All Recordings"
   - Verify list shows recorded files with metadata
   - Select file and tap export
   - Send to email/files app
   - Verify file is valid WAV format

5. **Test Route Changes**
   - While on diagnostics screen, disconnect glasses
   - Verify route display updates to show phone audio
   - Reconnect glasses
   - Verify route display updates to show Bluetooth

## Integration with Main App

The diagnostics UI should be accessible from:
- **Settings Menu**: Settings > Developer Options > Audio Diagnostics
- **Debug Menu**: Long-press app version in About screen
- **Voice Command**: "Test audio routing" (development builds only)

## File Storage

**iOS**: 
- Recordings saved to: `Documents/audio_diagnostics/`
- Access via Files app > On My iPhone > [App Name]

**Android**:
- Recordings saved to: `getExternalFilesDir(Environment.DIRECTORY_MUSIC)/audio_diagnostics/`
- Access via Files app > Internal Storage > [App Name] > audio_diagnostics

## Permissions Required

**iOS** (`Info.plist`):
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Record audio from your Meta AI Glasses for diagnostics</string>
<key>NSBluetoothPeripheralUsageDescription</key>
<string>Connect to Meta AI Glasses for audio routing</string>
```

**Android** (`AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

## Troubleshooting

### "No Bluetooth device detected"
- Check glasses are paired in phone settings
- Ensure glasses are powered on
- Try disconnecting and reconnecting
- Restart Bluetooth on phone

### "Recording fails to start"
- Check microphone permissions
- Verify Bluetooth connection is active
- Restart audio session
- Check another app isn't using microphone

### "Playback goes to phone speaker"
- Verify Bluetooth connection
- Check audio route display shows Bluetooth output
- Manually select Bluetooth device in phone settings
- Restart app

### "Exported file has no audio"
- Verify you spoke during recording
- Check microphone isn't muted/blocked
- Test with phone's built-in recorder
- Check WAV file header is valid

## Next Steps

1. Implement iOS diagnostics UI and audio components
2. Implement Android diagnostics UI and audio components
3. Add to main app navigation
4. Test with actual Meta AI Glasses
5. Document results and refine based on real-world usage
6. Consider adding to end-user features (not just diagnostics)

## References

- [Main Audio Routing Documentation](../../docs/meta-ai-glasses-audio-routing.md)
- iOS AVAudioSession: https://developer.apple.com/documentation/avfoundation/avaudiosession
- Android AudioManager: https://developer.android.com/reference/android/media/AudioManager
- Meta AI Glasses: https://www.meta.com/smart-glasses/
