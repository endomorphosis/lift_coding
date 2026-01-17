# Android Implementation

This directory will contain the Android-specific implementation of the Meta AI Glasses audio diagnostics.

## Files to Implement

### `GlassesAudioDiagnostics.kt`
Main fragment/activity for the diagnostics UI.

**Key responsibilities:**
- Present the diagnostics interface
- Coordinate between AudioRouteMonitor, GlassesRecorder, and GlassesPlayer
- Handle user interactions (record, play, export buttons)
- Display route information and status updates
- Manage permissions (microphone, Bluetooth, audio settings)

**Jetpack Compose Example Structure:**
```kotlin
@Composable
fun GlassesAudioDiagnosticsScreen(
    viewModel: GlassesAudioDiagnosticsViewModel = viewModel()
) {
    // UI implementation
}
```

### `AudioRouteMonitor.kt`
Monitors and reports current audio routing.

**Key responsibilities:**
- Monitor AudioManager device changes
- Detect Bluetooth SCO connections
- Format route information for display
- Provide callbacks for route updates
- Track SCO connection state

**Interface:**
```kotlin
class AudioRouteMonitor(private val context: Context) {
    fun startMonitoring(callback: (AudioRouteInfo) -> Unit)
    fun stopMonitoring()
    fun getCurrentRoute(): AudioRouteInfo
    fun isBluetoothConnected(): Boolean
    fun isScoConnected(): Boolean
}
```

### `GlassesRecorder.kt`
Handles audio recording from Bluetooth microphone.

**Key responsibilities:**
- Configure AudioManager for Bluetooth SCO
- Use AudioRecord with VOICE_COMMUNICATION source
- Write WAV files with proper headers
- Handle Bluetooth SCO connection
- Provide recording level feedback
- Handle timed recordings

**Interface:**
```kotlin
class GlassesRecorder(private val context: Context) {
    fun startRecording(duration: Int, callback: (File?, Exception?) -> Unit)
    fun stopRecording()
    fun getRecordingLevel(): Float  // 0.0f to 1.0f
    fun isRecording(): Boolean
}
```

### `GlassesPlayer.kt`
Handles audio playback through Bluetooth speakers.

**Key responsibilities:**
- Configure AudioManager for Bluetooth SCO
- Use AudioTrack with proper attributes
- Handle Bluetooth SCO connection
- Provide playback progress updates
- Handle stop/pause functionality

**Interface:**
```kotlin
class GlassesPlayer(private val context: Context) {
    fun playAudio(file: File, callback: (Exception?) -> Unit)
    fun stop()
    fun pause()
    fun resume()
    fun getPlaybackProgress(): Double  // 0.0 to 1.0
    fun isPlaying(): Boolean
}
```

## Implementation Notes

### AudioManager Configuration

For Bluetooth SCO:
```kotlin
val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
audioManager.startBluetoothSco()
audioManager.isBluetoothScoOn = true
```

### AudioRecord Setup

Use VOICE_COMMUNICATION source for Bluetooth:
```kotlin
val audioRecord = AudioRecord(
    MediaRecorder.AudioSource.VOICE_COMMUNICATION,
    16000,  // Sample rate
    AudioFormat.CHANNEL_IN_MONO,
    AudioFormat.ENCODING_PCM_16BIT,
    bufferSize
)
```

### AudioTrack Setup

Use proper attributes for voice communication:
```kotlin
val audioAttributes = AudioAttributes.Builder()
    .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
    .build()

val audioFormat = AudioFormat.Builder()
    .setSampleRate(16000)
    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
    .build()
```

### Bluetooth SCO Connection Monitoring

Register broadcast receiver:
```kotlin
val filter = IntentFilter(AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED)
context.registerReceiver(scoReceiver, filter)
```

### WAV File Format

Implement WAV header writing:
```kotlin
private fun writeWAVHeader(output: FileOutputStream, dataSize: Int) {
    val header = ByteArray(44)
    // RIFF header
    header[0] = 'R'.code.toByte()
    header[1] = 'I'.code.toByte()
    header[2] = 'F'.code.toByte()
    header[3] = 'F'.code.toByte()
    // ... (see full implementation in audio routing doc)
}
```

### File Storage

Save to app-specific external files directory:
```kotlin
val diagnosticsDir = File(
    context.getExternalFilesDir(Environment.DIRECTORY_MUSIC),
    "audio_diagnostics"
)
diagnosticsDir.mkdirs()
```

### Permissions

Add to AndroidManifest.xml:
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

Request at runtime (Android 6.0+):
```kotlin
requestPermissions(
    arrayOf(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.BLUETOOTH_CONNECT
    ),
    REQUEST_CODE
)
```

### Foreground Service (Optional)

If recording in background, use foreground service:
```kotlin
val notification = NotificationCompat.Builder(context, CHANNEL_ID)
    .setContentTitle("Recording Audio")
    .setContentText("Recording from Meta AI Glasses")
    .setSmallIcon(R.drawable.ic_mic)
    .build()

startForeground(NOTIFICATION_ID, notification)
```

## Testing Checklist

- [ ] Test with Meta AI Glasses connected via Bluetooth
- [ ] Test route display updates on connect/disconnect
- [ ] Test recording and verify WAV file format
- [ ] Test playback through glasses speakers
- [ ] Test file export via share intent
- [ ] Test SCO connection/disconnection handling
- [ ] Test with no Bluetooth device connected
- [ ] Test with multiple Bluetooth devices
- [ ] Test background recording with foreground service
- [ ] Test audio focus handling (other apps)

## References

- [Parent README](../README.md)
- [Audio Routing Documentation](../../../docs/meta-ai-glasses-audio-routing.md)
- [Android AudioManager Documentation](https://developer.android.com/reference/android/media/AudioManager)
- [Android AudioRecord Documentation](https://developer.android.com/reference/android/media/AudioRecord)
- [Android AudioTrack Documentation](https://developer.android.com/reference/android/media/AudioTrack)
