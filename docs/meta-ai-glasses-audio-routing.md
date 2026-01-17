# Meta AI Glasses: Bluetooth Audio Routing (iOS + Android)

This document provides comprehensive guidance for implementing Bluetooth audio routing to use **Meta AI Glasses (Ray-Ban Meta Smart Glasses)** as the audio I/O device for the mobile companion app.

## Overview

The goal is to route audio seamlessly between the mobile app and the Meta AI Glasses using standard OS Bluetooth headset profiles:
- **Input**: Capture audio from the glasses microphone via Bluetooth headset input
- **Output**: Play TTS audio through the glasses speakers via Bluetooth headset output

This implementation uses standard OS Bluetooth audio routing APIs without requiring vendor-specific SDKs.

## iOS Implementation

### AVAudioSession Configuration

iOS uses `AVAudioSession` to manage audio routing. For Bluetooth headset I/O with the Meta AI Glasses:

```swift
import AVFoundation

func configureAudioSessionForGlasses() throws {
    let audioSession = AVAudioSession.sharedInstance()
    
    // Set category to playAndRecord for bidirectional audio
    // Options:
    // - allowBluetooth: enables Bluetooth audio routing
    // - defaultToSpeaker: fallback to speaker when Bluetooth unavailable
    // - allowBluetoothA2DP: enables high-quality stereo (optional for output)
    try audioSession.setCategory(
        .playAndRecord,
        mode: .voiceChat,  // Optimized for voice with echo cancellation
        options: [.allowBluetooth, .defaultToSpeaker]
    )
    
    // Prefer Bluetooth input when available
    try audioSession.setPreferredInput(findBluetoothInput())
    
    // Set sample rate (16kHz recommended for voice)
    try audioSession.setPreferredSampleRate(16000.0)
    
    // Activate the session
    try audioSession.setActive(true)
}

func findBluetoothInput() -> AVAudioSessionPortDescription? {
    let audioSession = AVAudioSession.sharedInstance()
    return audioSession.availableInputs?.first { port in
        port.portType == .bluetoothHFP || port.portType == .bluetoothLE
    }
}
```

### Audio Recording from Glasses Mic

```swift
import AVFoundation

class GlassesAudioRecorder {
    private var audioEngine = AVAudioEngine()
    private var audioFile: AVAudioFile?
    
    func startRecording(to fileURL: URL) throws {
        let inputNode = audioEngine.inputNode
        let format = inputNode.outputFormat(forBus: 0)
        
        // Create audio file for recording
        audioFile = try AVAudioFile(
            forWriting: fileURL,
            settings: [
                AVFormatIDKey: kAudioFormatLinearPCM,
                AVSampleRateKey: 16000,
                AVNumberOfChannelsKey: 1,
                AVLinearPCMBitDepthKey: 16,
                AVLinearPCMIsFloatKey: false
            ]
        )
        
        // Install tap on input node
        inputNode.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] buffer, time in
            try? self?.audioFile?.write(from: buffer)
        }
        
        try audioEngine.start()
    }
    
    func stopRecording() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
    }
}
```

### Audio Playback to Glasses Speakers

```swift
import AVFoundation

class GlassesAudioPlayer {
    private var audioEngine = AVAudioEngine()
    private var playerNode = AVAudioPlayerNode()
    
    func playAudio(from fileURL: URL) throws {
        let audioFile = try AVAudioFile(forReading: fileURL)
        
        audioEngine.attach(playerNode)
        audioEngine.connect(playerNode, to: audioEngine.mainMixerNode, format: audioFile.processingFormat)
        
        try audioEngine.start()
        
        playerNode.scheduleFile(audioFile, at: nil) {
            // Playback completed
        }
        playerNode.play()
    }
    
    func stop() {
        playerNode.stop()
        audioEngine.stop()
    }
}
```

### Handling Audio Route Changes

```swift
func setupRouteChangeObserver() {
    NotificationCenter.default.addObserver(
        self,
        selector: #selector(handleRouteChange),
        name: AVAudioSession.routeChangeNotification,
        object: nil
    )
}

@objc func handleRouteChange(notification: Notification) {
    guard let userInfo = notification.userInfo,
          let reasonValue = userInfo[AVAudioSessionRouteChangeReasonKey] as? UInt,
          let reason = AVAudioSession.RouteChangeReason(rawValue: reasonValue) else {
        return
    }
    
    switch reason {
    case .newDeviceAvailable:
        // Bluetooth device connected - reconfigure if needed
        try? configureAudioSessionForGlasses()
    case .oldDeviceUnavailable:
        // Bluetooth device disconnected - handle gracefully
        print("Audio device disconnected")
    case .categoryChange, .override:
        // Route changed by system or other app
        print("Audio route changed")
    default:
        break
    }
}
```

### Handling Interruptions

```swift
func setupInterruptionObserver() {
    NotificationCenter.default.addObserver(
        self,
        selector: #selector(handleInterruption),
        name: AVAudioSession.interruptionNotification,
        object: nil
    )
}

@objc func handleInterruption(notification: Notification) {
    guard let userInfo = notification.userInfo,
          let typeValue = userInfo[AVAudioSessionInterruptionTypeKey] as? UInt,
          let type = AVAudioSession.InterruptionType(rawValue: typeValue) else {
        return
    }
    
    switch type {
    case .began:
        // Interruption began (e.g., phone call) - pause recording/playback
        pauseAudio()
    case .ended:
        // Interruption ended - resume if appropriate
        if let optionsValue = userInfo[AVAudioSessionInterruptionOptionKey] as? UInt {
            let options = AVAudioSession.InterruptionOptions(rawValue: optionsValue)
            if options.contains(.shouldResume) {
                resumeAudio()
            }
        }
    @unknown default:
        break
    }
}
```

## Android Implementation

### AudioManager Configuration

Android uses `AudioManager` for Bluetooth audio routing and SCO (Synchronous Connection Oriented) for headset profiles:

```kotlin
import android.media.AudioManager
import android.content.Context

class GlassesAudioManager(private val context: Context) {
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    
    fun setupBluetoothAudio() {
        // Set audio mode to communication for voice chat
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
        
        // Start Bluetooth SCO (required for headset mic input)
        if (audioManager.isBluetoothScoAvailableOffCall) {
            audioManager.startBluetoothSco()
            audioManager.isBluetoothScoOn = true
        }
        
        // Route audio to Bluetooth headset
        audioManager.isSpeakerphoneOn = false
    }
    
    fun teardownBluetoothAudio() {
        audioManager.stopBluetoothSco()
        audioManager.isBluetoothScoOn = false
        audioManager.mode = AudioManager.MODE_NORMAL
    }
    
    fun isBluetoothHeadsetConnected(): Boolean {
        return audioManager.isBluetoothScoAvailableOffCall
    }
}
```

### Audio Recording from Glasses Mic

```kotlin
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.AudioFormat
import java.io.File
import java.io.FileOutputStream

class GlassesAudioRecorder(private val audioManager: GlassesAudioManager) {
    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    
    companion object {
        const val SAMPLE_RATE = 16000
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }
    
    fun startRecording(outputFile: File) {
        audioManager.setupBluetoothAudio()
        
        val bufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT
        )
        
        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,  // Use communication source for BT headset
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT,
            bufferSize * 2
        )
        
        audioRecord?.startRecording()
        isRecording = true
        
        // Record in background thread
        Thread {
            val buffer = ByteArray(bufferSize)
            FileOutputStream(outputFile).use { fos ->
                while (isRecording) {
                    val bytesRead = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (bytesRead > 0) {
                        fos.write(buffer, 0, bytesRead)
                    }
                }
            }
        }.start()
    }
    
    fun stopRecording() {
        isRecording = false
        audioRecord?.stop()
        audioRecord?.release()
        audioRecord = null
        audioManager.teardownBluetoothAudio()
    }
}
```

### Audio Playback to Glasses Speakers

```kotlin
import android.media.AudioTrack
import android.media.AudioAttributes
import android.media.AudioFormat
import java.io.File
import java.io.FileInputStream

class GlassesAudioPlayer(private val audioManager: GlassesAudioManager) {
    private var audioTrack: AudioTrack? = null
    
    fun playAudio(audioFile: File) {
        audioManager.setupBluetoothAudio()
        
        val bufferSize = AudioTrack.getMinBufferSize(
            GlassesAudioRecorder.SAMPLE_RATE,
            AudioFormat.CHANNEL_OUT_MONO,
            GlassesAudioRecorder.AUDIO_FORMAT
        )
        
        val audioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()
        
        val audioFormat = AudioFormat.Builder()
            .setSampleRate(GlassesAudioRecorder.SAMPLE_RATE)
            .setEncoding(GlassesAudioRecorder.AUDIO_FORMAT)
            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
            .build()
        
        audioTrack = AudioTrack.Builder()
            .setAudioAttributes(audioAttributes)
            .setAudioFormat(audioFormat)
            .setBufferSizeInBytes(bufferSize * 2)
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()
        
        audioTrack?.play()
        
        // Play in background thread
        Thread {
            val buffer = ByteArray(bufferSize)
            FileInputStream(audioFile).use { fis ->
                var bytesRead: Int
                while (fis.read(buffer).also { bytesRead = it } != -1) {
                    audioTrack?.write(buffer, 0, bytesRead)
                }
            }
        }.start()
    }
    
    fun stop() {
        audioTrack?.stop()
        audioTrack?.release()
        audioTrack = null
        audioManager.teardownBluetoothAudio()
    }
}
```

### Handling Bluetooth SCO Connection

```kotlin
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioManager

class BluetoothScoReceiver(private val onConnected: () -> Unit, private val onDisconnected: () -> Unit) : BroadcastReceiver() {
    
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.getIntExtra(AudioManager.EXTRA_SCO_AUDIO_STATE, -1)) {
            AudioManager.SCO_AUDIO_STATE_CONNECTED -> {
                onConnected()
            }
            AudioManager.SCO_AUDIO_STATE_DISCONNECTED -> {
                onDisconnected()
            }
        }
    }
    
    companion object {
        fun register(context: Context, receiver: BluetoothScoReceiver) {
            val filter = IntentFilter(AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED)
            context.registerReceiver(receiver, filter)
        }
    }
}
```

## Audio Format Recommendations

### Recording Format (Glasses Mic → Backend)

**Recommended format for voice processing:**
- **Format**: Linear PCM (uncompressed)
- **Sample Rate**: 16 kHz (good balance between quality and bandwidth)
- **Bit Depth**: 16-bit
- **Channels**: Mono
- **Container**: WAV (with proper headers)

**WAV file structure:**
```
RIFF header (12 bytes)
fmt chunk (24 bytes for PCM)
data chunk (8 bytes header + audio samples)
```

### Converting Raw PCM to WAV

**iOS (Swift):**
```swift
func writeWAVHeader(to file: FileHandle, dataSize: Int, sampleRate: Int = 16000) {
    var header = Data()
    
    // RIFF header
    header.append("RIFF".data(using: .ascii)!)
    header.append(UInt32(dataSize + 36).littleEndian.data)
    header.append("WAVE".data(using: .ascii)!)
    
    // fmt chunk
    header.append("fmt ".data(using: .ascii)!)
    header.append(UInt32(16).littleEndian.data)  // Subchunk size
    header.append(UInt16(1).littleEndian.data)   // Audio format (PCM)
    header.append(UInt16(1).littleEndian.data)   // Num channels
    header.append(UInt32(sampleRate).littleEndian.data)
    header.append(UInt32(sampleRate * 2).littleEndian.data)  // Byte rate
    header.append(UInt16(2).littleEndian.data)   // Block align
    header.append(UInt16(16).littleEndian.data)  // Bits per sample
    
    // data chunk
    header.append("data".data(using: .ascii)!)
    header.append(UInt32(dataSize).littleEndian.data)
    
    file.write(header)
}

extension FixedWidthInteger {
    var data: Data {
        return withUnsafeBytes(of: self.littleEndian) { Data($0) }
    }
}
```

**Android (Kotlin):**
```kotlin
fun writeWAVHeader(outputStream: FileOutputStream, dataSize: Int, sampleRate: Int = 16000) {
    val header = ByteArray(44)
    val channels = 1
    val bitsPerSample = 16
    val byteRate = sampleRate * channels * bitsPerSample / 8
    val blockAlign = channels * bitsPerSample / 8
    
    // RIFF header
    header[0] = 'R'.code.toByte()
    header[1] = 'I'.code.toByte()
    header[2] = 'F'.code.toByte()
    header[3] = 'F'.code.toByte()
    writeInt(header, 4, dataSize + 36)
    header[8] = 'W'.code.toByte()
    header[9] = 'A'.code.toByte()
    header[10] = 'V'.code.toByte()
    header[11] = 'E'.code.toByte()
    
    // fmt chunk
    header[12] = 'f'.code.toByte()
    header[13] = 'm'.code.toByte()
    header[14] = 't'.code.toByte()
    header[15] = ' '.code.toByte()
    writeInt(header, 16, 16)  // Subchunk size
    writeShort(header, 20, 1) // Audio format (PCM)
    writeShort(header, 22, channels)
    writeInt(header, 24, sampleRate)
    writeInt(header, 28, byteRate)
    writeShort(header, 32, blockAlign)
    writeShort(header, 34, bitsPerSample)
    
    // data chunk
    header[36] = 'd'.code.toByte()
    header[37] = 'a'.code.toByte()
    header[38] = 't'.code.toByte()
    header[39] = 'a'.code.toByte()
    writeInt(header, 40, dataSize)
    
    outputStream.write(header)
}

private fun writeInt(buffer: ByteArray, offset: Int, value: Int) {
    buffer[offset] = (value and 0xff).toByte()
    buffer[offset + 1] = (value shr 8 and 0xff).toByte()
    buffer[offset + 2] = (value shr 16 and 0xff).toByte()
    buffer[offset + 3] = (value shr 24 and 0xff).toByte()
}

private fun writeShort(buffer: ByteArray, offset: Int, value: Int) {
    buffer[offset] = (value and 0xff).toByte()
    buffer[offset + 1] = (value shr 8 and 0xff).toByte()
}
```

### Playback Format (Backend → Glasses Speakers)

The backend TTS endpoint typically returns audio in various formats. Convert to the same PCM format for playback:
- **Sample Rate**: 16 kHz
- **Bit Depth**: 16-bit
- **Channels**: Mono
- **Format**: Linear PCM

If the backend returns MP3 or other compressed formats, decode to PCM before playback.

## Debugging and Diagnostics

### Audio Route Verification

**iOS:**
```swift
func getCurrentAudioRoute() -> String {
    let session = AVAudioSession.sharedInstance()
    let route = session.currentRoute
    
    var routeDescription = "Inputs:\n"
    for input in route.inputs {
        routeDescription += "  - \(input.portName) (\(input.portType.rawValue))\n"
    }
    
    routeDescription += "Outputs:\n"
    for output in route.outputs {
        routeDescription += "  - \(output.portName) (\(output.portType.rawValue))\n"
    }
    
    return routeDescription
}
```

**Android:**
```kotlin
fun getCurrentAudioRoute(): String {
    val audioDevices = audioManager.getDevices(AudioManager.GET_DEVICES_ALL)
    val activeInputs = audioDevices.filter { it.isSource }
    val activeOutputs = audioDevices.filter { it.isSink }
    
    var description = "Inputs:\n"
    activeInputs.forEach { device ->
        description += "  - ${device.productName} (${device.type})\n"
    }
    
    description += "Outputs:\n"
    activeOutputs.forEach { device ->
        description += "  - ${device.productName} (${device.type})\n"
    }
    
    return description
}
```

### Known Issues and Mitigations

#### 1. Bluetooth Connection Delay
**Issue**: Bluetooth SCO (Android) or HFP (iOS) can take 1-3 seconds to establish.

**Mitigation**:
- On Android, call `startBluetoothSco()` early and wait for `SCO_AUDIO_STATE_CONNECTED` before recording
- Show a "Connecting to glasses..." indicator during setup
- Implement timeout handling (5-10 seconds) with fallback to phone mic/speaker

#### 2. Audio Route Changes Mid-Session
**Issue**: User may disconnect glasses or receive a phone call.

**Mitigation**:
- Monitor route change notifications (iOS) or SCO state broadcasts (Android)
- Pause recording/playback gracefully
- Prompt user to reconnect or continue with phone audio
- Save recording state to resume after interruption

#### 3. Echo and Feedback
**Issue**: Audio played through speakers can be picked up by the microphone.

**Mitigation**:
- iOS: Use `.voiceChat` mode (enables hardware echo cancellation)
- Android: Use `AudioSource.VOICE_COMMUNICATION` (enables AEC)
- Keep volume at moderate levels
- Use half-duplex communication (don't record while playing)

#### 4. Latency
**Issue**: Bluetooth audio has inherent latency (100-300ms).

**Mitigation**:
- Use small buffer sizes (but not too small to avoid glitches)
- Optimize for voice communication, not music
- Set user expectations for slight delays

#### 5. Permission Denied
**Issue**: Microphone or Bluetooth permissions not granted.

**Mitigation**:
- Request permissions with clear explanations
- Handle permission denial gracefully
- Provide in-app guidance to enable permissions in Settings

#### 6. Background Mode Issues
**Issue**: Recording may stop when app goes to background.

**Mitigation**:
- iOS: Enable "Audio, AirPlay, and Picture in Picture" background mode
- Android: Use foreground service for recording/playback
- Keep audio session active with visible indicator

## End-to-End Test Checklist

Use this checklist to validate the complete glasses audio pipeline:

### Setup
- [ ] Meta AI Glasses paired with phone via Bluetooth
- [ ] Glasses connected and showing in Bluetooth devices list
- [ ] App has microphone and Bluetooth permissions granted

### Audio Route Verification
- [ ] App shows "Bluetooth Headset" as current audio route
- [ ] Manually verify route: Play test tone, confirm it's audible in glasses
- [ ] Manually verify input: Record test clip, speak into glasses mic, verify clean audio

### Recording Flow (Glasses Mic → Backend)
- [ ] Start recording through glasses mic
- [ ] Speak test phrase: "Hello, this is a test from my Meta AI Glasses"
- [ ] Stop recording
- [ ] Verify audio file created (WAV format, 16kHz, 16-bit, mono)
- [ ] Verify audio quality: No clipping, minimal background noise
- [ ] Upload to backend `POST /v1/command` endpoint
- [ ] Verify backend accepts and processes audio

### Playback Flow (Backend → Glasses Speakers)
- [ ] Request TTS from backend: `POST /v1/tts` with sample text
- [ ] Receive audio response from backend
- [ ] Convert to PCM if needed
- [ ] Play through glasses speakers
- [ ] Verify audio is clear and audible in glasses
- [ ] Verify no echo or feedback

### Interruption Handling
- [ ] Start recording
- [ ] Receive phone call (interrupt)
- [ ] Verify recording pauses/stops gracefully
- [ ] End call
- [ ] Verify app can resume recording

### Route Change Handling
- [ ] Start recording with glasses connected
- [ ] Disconnect glasses mid-recording
- [ ] Verify app handles disconnection (fallback or error message)
- [ ] Reconnect glasses
- [ ] Verify app detects and routes to glasses again

### Background Mode
- [ ] Start recording
- [ ] Put app in background
- [ ] iOS: Verify recording continues (if background mode enabled)
- [ ] Android: Verify foreground service keeps recording
- [ ] Return to foreground
- [ ] Verify recording completes successfully

### Latency Check
- [ ] Record and immediately play back
- [ ] Measure perceived latency (should be < 500ms total)
- [ ] If latency > 500ms, optimize buffer sizes

### Battery Impact
- [ ] Monitor battery usage during extended recording session (10+ minutes)
- [ ] Verify impact is reasonable (< 10% per hour of active use)

## Troubleshooting Guide

### "No Bluetooth device found"
- Verify glasses are paired in phone's Bluetooth settings
- Try disconnecting and reconnecting glasses
- Restart Bluetooth on phone
- Restart glasses (check manufacturer instructions)

### "Audio routing to phone speaker instead of glasses"
- Check that glasses are connected (not just paired)
- Verify app has Bluetooth permissions
- Try manually selecting output device in phone settings
- Restart app to re-initialize audio session

### "Recording produces silent audio"
- Check microphone permissions
- Verify glasses microphone is active (not muted)
- Check that another app isn't monopolizing audio input
- Test with phone's built-in recorder app to rule out hardware issues

### "Echo or feedback during playback"
- Lower glasses speaker volume
- Ensure `.voiceChat` mode (iOS) or `VOICE_COMMUNICATION` (Android) is active
- Implement half-duplex: Don't record while playing
- Check that echo cancellation is enabled

### "Connection drops frequently"
- Check Bluetooth signal strength (keep phone close to glasses)
- Minimize interference (Wi-Fi, other Bluetooth devices)
- Update phone's Bluetooth firmware
- Replace glasses battery if low

## Additional Resources

- **iOS**: [AVAudioSession Programming Guide](https://developer.apple.com/documentation/avfaudio/avaudiosession)
- **iOS**: [Audio Guidelines for User-Controlled Playback and Recording](https://developer.apple.com/documentation/avfaudio/audio_engine)
- **Android**: [AudioManager Reference](https://developer.android.com/reference/android/media/AudioManager)
- **Android**: [Building audio apps for Bluetooth devices](https://developer.android.com/guide/topics/connectivity/bluetooth)
- **WAV Format**: [WAVE PCM soundfile format](http://soundfile.sapp.org/doc/WaveFormat/)

## Future Enhancements

- Support for higher sample rates (24kHz, 48kHz) when glasses support it
- Adaptive bitrate based on Bluetooth connection quality
- Noise cancellation and audio enhancement on device
- Multi-device support (switch between multiple paired glasses)
- Background recording with cloud sync
