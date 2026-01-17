# Meta AI Glasses Integration Guide

This guide explains how to integrate Meta AI Glasses (or similar AR/wearable audio devices) with the HandsFree Dev Companion mobile app for a seamless hands-free developer experience.

## Overview

Meta AI Glasses provide:
- **Audio input** - Built-in microphone for voice commands
- **Audio output** - Built-in speakers for TTS responses
- **Push-to-talk** - Physical button or gesture to trigger recording
- **Bluetooth connectivity** - Wireless connection to iOS/Android device

The HandsFree system leverages these capabilities to enable completely hands-free interactions with your development workflow.

## Architecture

```
[Meta AI Glasses] <-Bluetooth-> [Mobile App] <-HTTP-> [Backend API]
       |                             |                      |
   Mic + Speaker              Audio Processing         Command Processing
                              + API Calls              + Agent System
```

## Audio Routing

### Input: Microphone to Mobile App

When Meta AI Glasses are connected via Bluetooth:

1. **iOS (AVAudioSession):**
   ```swift
   let session = AVAudioSession.sharedInstance()
   try session.setCategory(.playAndRecord, mode: .default, options: [.allowBluetooth])
   try session.setActive(true)
   ```

2. **Android (AudioManager):**
   ```kotlin
   val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
   audioManager.startBluetoothSco()
   audioManager.isBluetoothScoOn = true
   ```

The OS automatically routes audio input from the glasses' microphone to your app when recording.

### Output: Mobile App to Speakers

For TTS playback through the glasses:

1. **iOS:**
   ```swift
   let session = AVAudioSession.sharedInstance()
   try session.setCategory(.playback, mode: .default, options: [.allowBluetooth])
   
   // Play audio - it will automatically route to connected Bluetooth device
   let player = try AVAudioPlayer(data: ttsAudioData)
   player.play()
   ```

2. **Android:**
   ```kotlin
   val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
   audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
   audioManager.startBluetoothSco()
   
   val mediaPlayer = MediaPlayer()
   mediaPlayer.setAudioStreamType(AudioManager.STREAM_VOICE_CALL)
   mediaPlayer.setDataSource(ttsAudioFile.absolutePath)
   mediaPlayer.prepare()
   mediaPlayer.start()
   ```

### Automatic Routing

Modern mobile OSes handle Bluetooth audio routing automatically:

- When glasses are connected and active, the OS routes audio I/O to them
- If glasses disconnect, audio falls back to phone speakers/mic
- No special app logic needed beyond setting the correct audio session category

## Push-to-Talk UX

### Hardware Button

Meta AI Glasses typically include a physical button for triggering actions. The recommended UX:

1. **User presses button** → App starts recording
2. **User speaks command** → Audio is captured from glasses mic
3. **User releases button** (or after timeout) → Recording stops
4. **App processes**:
   - Upload audio to storage (S3, etc.)
   - Send command to backend with audio URI
   - Backend transcribes and processes
   - Backend returns response
5. **App plays TTS** → Audio plays through glasses speakers

### Implementation

**iOS (SpeechRecognizer + AVAudioRecorder):**

```swift
class VoiceCommandHandler {
    private var audioRecorder: AVAudioRecorder?
    private var recordingURL: URL?
    
    func startRecording() {
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.record, mode: .default, options: [.allowBluetooth])
        try? session.setActive(true)
        
        recordingURL = getTemporaryAudioURL()
        let settings = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 16000,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        audioRecorder = try? AVAudioRecorder(url: recordingURL!, settings: settings)
        audioRecorder?.record()
    }
    
    func stopRecording() async -> URL? {
        audioRecorder?.stop()
        guard let url = recordingURL else { return nil }
        
        // Upload to S3 or similar
        let preSignedURL = await uploadAudio(url)
        return preSignedURL
    }
    
    func sendCommand(audioURI: URL) async {
        let request = CommandRequest(
            input: .audio(format: "m4a", uri: audioURI.absoluteString),
            profile: "terse",
            clientContext: ClientContext(device: "ios", ...)
        )
        let response = await api.sendCommand(request)
        
        // Play TTS response
        if let ttsText = response.response.text {
            await playTTS(text: ttsText)
        }
    }
    
    func playTTS(text: String) async {
        let ttsAudio = await api.fetchTTS(text: text, format: "mp3")
        
        let session = AVAudioSession.sharedInstance()
        try? session.setCategory(.playback, mode: .default, options: [.allowBluetooth])
        
        let player = try? AVAudioPlayer(data: ttsAudio)
        player?.play()
    }
}
```

**Android (MediaRecorder + API calls):**

```kotlin
class VoiceCommandHandler(private val context: Context) {
    private var mediaRecorder: MediaRecorder? = null
    private var recordingFile: File? = null
    
    fun startRecording() {
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.startBluetoothSco()
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        
        recordingFile = File.createTempFile("recording", ".m4a", context.cacheDir)
        
        mediaRecorder = MediaRecorder().apply {
            setAudioSource(MediaRecorder.AudioSource.VOICE_COMMUNICATION)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioSamplingRate(16000)
            setOutputFile(recordingFile!!.absolutePath)
            prepare()
            start()
        }
    }
    
    suspend fun stopRecording(): String? {
        mediaRecorder?.stop()
        mediaRecorder?.release()
        mediaRecorder = null
        
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.stopBluetoothSco()
        
        // Upload to S3 or similar
        return uploadAudio(recordingFile!!)
    }
    
    suspend fun sendCommand(audioURI: String) {
        val request = CommandRequest(
            input = AudioInput(type = "audio", format = "m4a", uri = audioURI),
            profile = "terse",
            clientContext = ClientContext(device = "android", ...)
        )
        val response = api.sendCommand(request)
        
        // Play TTS response
        response.response.text?.let { playTTS(it) }
    }
    
    suspend fun playTTS(text: String) {
        val ttsAudio = api.fetchTTS(text, format = "mp3")
        val tempFile = File.createTempFile("tts", ".mp3", context.cacheDir)
        tempFile.writeBytes(ttsAudio)
        
        val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        audioManager.startBluetoothSco()
        
        val mediaPlayer = MediaPlayer().apply {
            setAudioStreamType(AudioManager.STREAM_VOICE_CALL)
            setDataSource(tempFile.absolutePath)
            prepare()
            start()
        }
    }
}
```

## UX Flow Details

### Typical Interaction

1. **User puts on glasses** → App detects connection via Bluetooth
2. **App shows status**: "Meta AI Glasses connected"
3. **User presses button on glasses** → App starts recording
4. **Visual feedback**: App shows recording indicator (red dot, waveform)
5. **User says**: "Show my open pull requests"
6. **User releases button** → App stops recording
7. **App uploads audio** → Shows "Processing..." indicator
8. **Backend processes** → Transcribes, routes to agent, generates response
9. **App receives response** → Shows cards on phone screen
10. **App plays TTS** → "You have 3 open pull requests..." through glasses
11. **User can tap cards** → Opens GitHub app or web view

### Visual + Audio Feedback

The mobile app should provide **both** visual and audio feedback:

| Event | Visual (Phone Screen) | Audio (Glasses) |
|-------|----------------------|-----------------|
| Recording start | Red dot, waveform | Beep/chime |
| Recording stop | Processing spinner | Beep/chime |
| Response ready | Cards appear | TTS playback |
| Error | Error message | "Sorry, something went wrong" |

### Confirmation Flow with Glasses

For commands requiring confirmation (e.g., "merge this PR"):

1. **User**: "Merge PR 123"
2. **Backend**: Returns `pending_action` with token
3. **App plays TTS**: "Ready to merge PR 123. Say 'confirm' to proceed."
4. **App shows card**: "Pending: Merge PR 123" with Confirm/Cancel buttons
5. **User can**:
   - **Say "confirm"** → App detects keyword, sends confirmation
   - **Tap "Confirm" button** → App sends confirmation
   - **Say nothing** → Token expires after 5-10 minutes
6. **App sends confirmation** → Backend executes action
7. **App plays TTS**: "PR 123 merged successfully"

## Audio Format Recommendations

### Recording (Microphone Input)

- **Format**: M4A (AAC)
- **Sample rate**: 16 kHz (sufficient for speech)
- **Channels**: Mono (1 channel)
- **Bitrate**: 64 kbps
- **Max duration**: 30 seconds per command

**Why M4A?**
- Good compression (smaller uploads)
- Widely supported by STT providers
- Native iOS format

### Playback (TTS Output)

- **Format**: MP3 (preferred) or WAV
- **Sample rate**: 22.05 kHz or 24 kHz
- **Channels**: Mono
- **Bitrate**: 64-96 kbps

**Why MP3?**
- Smaller file size → faster downloads
- Good quality at low bitrates
- Universal support

## Bluetooth Connection Management

### Detection

**iOS:**
```swift
import ExternalAccessory

class GlassesConnectionManager: NSObject, EAAccessoryDelegate {
    func checkConnection() -> Bool {
        let connectedAccessories = EAAccessoryManager.shared().connectedAccessories
        return connectedAccessories.contains { 
            $0.name.contains("Meta") || $0.name.contains("Ray-Ban")
        }
    }
}
```

**Android:**
```kotlin
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice

class GlassesConnectionManager(private val context: Context) {
    fun checkConnection(): Boolean {
        val bluetoothAdapter = BluetoothAdapter.getDefaultAdapter()
        val pairedDevices: Set<BluetoothDevice>? = bluetoothAdapter?.bondedDevices
        return pairedDevices?.any { 
            it.name.contains("Meta") || it.name.contains("Ray-Ban")
        } ?: false
    }
}
```

### Reconnection

Handle disconnection gracefully:

1. **App detects disconnection** → Show "Glasses disconnected" message
2. **Audio routing** → Falls back to phone speaker/mic
3. **User reconnects glasses** → App detects, switches back to glasses
4. **Resume interaction** → Continue where user left off

## Battery & Performance

### Optimize for Battery Life

- **Record only when needed**: Don't keep mic active continuously
- **Stop Bluetooth SCO**: Call `stopBluetoothSco()` when not recording/playing
- **Cache TTS audio**: Cache common responses ("You have no notifications", etc.)
- **Limit recording duration**: Auto-stop after 30 seconds
- **Use background tasks wisely**: Only fetch notifications when app is active

### Performance Tips

- **Stream audio uploads**: Don't wait for entire file before uploading
- **Preload TTS**: Preload common phrases on app launch
- **Use low-latency audio**: Configure audio session for low latency
- **Debounce button**: Prevent accidental double-triggers (100ms debounce)

## Vendor SDK Constraints

### Meta AI Glasses Policies

⚠️ **Important:** Meta's SDK for Ray-Ban Meta Glasses may have additional policies:

1. **Audio Privacy**: Don't record without explicit user consent
2. **Data Retention**: Don't store audio recordings longer than necessary
3. **Third-party Sharing**: Check if audio can be sent to external APIs
4. **Camera Usage**: If glasses have a camera, additional privacy rules apply
5. **LED Indicators**: Respect hardware privacy indicators (red LED when recording)

**Action Required:** Review Meta's developer agreement and SDK documentation before shipping.

### Alternative Wearables

This integration pattern works with other Bluetooth audio devices:

- **AirPods** (iOS/Android)
- **Bose Frames** (audio sunglasses)
- **Amazon Echo Frames**
- **Generic Bluetooth headsets**

The same audio routing and push-to-talk patterns apply universally.

## Accessibility Considerations

### Voice-First UX

For users relying on voice-only interaction:

- **Always provide audio feedback**: Don't rely on visual-only cues
- **Speak errors aloud**: "Sorry, I didn't understand that"
- **Confirm actions verbally**: "Opening pull request 123"
- **Provide help**: "Say 'help' to hear available commands"

### Example Audio Responses

| Situation | Audio Feedback |
|-----------|---------------|
| Recording started | "Listening..." |
| Recording stopped | "Processing..." |
| Command understood | "Checking your inbox..." |
| Command unclear | "Sorry, I didn't catch that. Please try again." |
| Network error | "Connection issue. Retrying..." |
| Success | "You have 3 open pull requests..." |

## Testing Without Hardware

### Simulator Testing

Test the core flows without physical glasses:

1. **Use phone mic/speaker**: Audio routing logic is the same
2. **Mock Bluetooth**: Simulate connection state changes
3. **Use reference client**: `dev/reference_mobile_client.py` tests API flows
4. **Test with cURL**: Manually test API endpoints

### Bluetooth Emulation

**iOS Simulator**: Doesn't support Bluetooth, but you can test audio recording/playback

**Android Emulator**: Supports Bluetooth, but may not route audio correctly

**Physical Testing**: Use any Bluetooth headset/earbuds to test the full flow

## Troubleshooting

### Common Issues

**Audio not routing to glasses:**
- Check Bluetooth connection status
- Verify audio session category (`.playAndRecord` or `.playback`)
- Ensure glasses are set as default audio device in phone settings

**Recording quality poor:**
- Check sample rate (should be 16 kHz minimum)
- Verify format (M4A/AAC recommended)
- Test in quiet environment first

**TTS not playing:**
- Check audio format (MP3 or WAV)
- Verify API returned audio data (not JSON error)
- Check audio session is active and category is correct

**Button press not detected:**
- If using glasses SDK: Check button event handlers
- If using generic Bluetooth: May need to poll Bluetooth input events
- Fall back to on-screen button for testing

### Debug Logs

Enable audio session logging:

**iOS:**
```swift
try? AVAudioSession.sharedInstance().setCategory(.record, options: [.allowBluetooth])
print("Audio inputs: \(AVAudioSession.sharedInstance().availableInputs)")
```

**Android:**
```kotlin
val audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
Log.d("Audio", "SCO connected: ${audioManager.isBluetoothScoOn}")
Log.d("Audio", "Current audio device: ${audioManager.mode}")
```

## Security & Privacy

### Audio Data Handling

1. **Encryption in transit**: Always use HTTPS for audio uploads
2. **Temporary storage**: Delete local audio files after upload
3. **Server retention**: Backend should delete audio after transcription
4. **User consent**: Always ask permission before recording

### Privacy Indicators

**iOS**: Automatically shows orange dot when mic is active

**Android**: Show persistent notification when recording

**Glasses**: Most have LED indicators when recording

## Example Integration (Swift)

```swift
class HandsFreeGlassesManager {
    private let api: HandsFreeAPI
    private let voiceHandler: VoiceCommandHandler
    private var isGlassesConnected = false
    
    init() {
        self.api = HandsFreeAPI(baseURL: "https://api.handsfree.dev")
        self.voiceHandler = VoiceCommandHandler()
        setupBluetoothMonitoring()
    }
    
    func setupBluetoothMonitoring() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(accessoryConnected),
            name: .EAAccessoryDidConnect,
            object: nil
        )
    }
    
    @objc func accessoryConnected(notification: Notification) {
        guard let accessory = notification.userInfo?[EAAccessoryKey] as? EAAccessory else { return }
        if accessory.name.contains("Meta") {
            isGlassesConnected = true
            playTTS("Glasses connected")
        }
    }
    
    func handleButtonPress() {
        if isGlassesConnected {
            startVoiceCommand()
        }
    }
    
    func startVoiceCommand() {
        voiceHandler.startRecording()
        // Show visual feedback
    }
    
    func stopVoiceCommand() async {
        guard let audioURI = await voiceHandler.stopRecording() else { return }
        await voiceHandler.sendCommand(audioURI: audioURI)
    }
    
    func playTTS(_ text: String) {
        Task {
            await voiceHandler.playTTS(text: text)
        }
    }
}
```

## Next Steps

- See `docs/mobile-client-integration.md` for complete API documentation
- See `dev/reference_mobile_client.py` for a working backend integration example
- Review Meta's developer documentation for SDK-specific requirements
- Test the full flow with a Bluetooth headset before acquiring glasses

## Resources

- [Apple AVAudioSession Programming Guide](https://developer.apple.com/documentation/avfoundation/avaudiosession)
- [Android Audio Capture Guide](https://developer.android.com/guide/topics/media/mediarecorder)
- [Meta Developer Portal](https://developers.meta.com/) (for official glasses SDK)
- HandsFree API Spec: `spec/openapi.yaml`
