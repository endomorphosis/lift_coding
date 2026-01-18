# PR-051: Android Glasses Recorder + Player Implementation Status

## Overview
This PR implements native Android functionality for recording from and playing back to Bluetooth-connected Meta AI Glasses, completing the Glasses mode implementation that was scaffolded in PR-039.

## Completed Components

### 1. GlassesRecorder.kt ✅
**Location**: `mobile/glasses/android/GlassesRecorder.kt`

**Features**:
- ✅ Bluetooth SCO connection management (start/stop/monitor)
- ✅ 16kHz mono PCM audio recording
- ✅ WAV file writing with proper headers
- ✅ Timed recording support (configurable duration)
- ✅ Callback-based async API
- ✅ Audio source: VOICE_COMMUNICATION (for Bluetooth headset)
- ✅ Automatic cleanup on stop

**API**:
```kotlin
fun startRecording(
    outputFile: File, 
    durationMs: Long = 0,
    callback: (File?, Exception?) -> Unit
)
fun stopRecording()
fun isRecording(): Boolean
fun getRecordingLevel(): Float
```

**Technical Details**:
- Sample Rate: 16000 Hz
- Channels: Mono
- Bit Depth: 16-bit
- Audio Format: PCM signed 16-bit little-endian
- Container: WAV (RIFF format with proper headers)
- Audio Source: MediaRecorder.AudioSource.VOICE_COMMUNICATION
- Audio Mode: AudioManager.MODE_IN_COMMUNICATION
- Bluetooth: Automatic SCO start/stop

**WAV Header Format**:
```
RIFF header (12 bytes):
  - "RIFF" (4 bytes)
  - File size - 8 (4 bytes, little-endian)
  - "WAVE" (4 bytes)

fmt chunk (24 bytes):
  - "fmt " (4 bytes)
  - Subchunk1 size: 16 (4 bytes)
  - Audio format: 1 = PCM (2 bytes)
  - Num channels: 1 (2 bytes)
  - Sample rate: 16000 (4 bytes)
  - Byte rate: 32000 (4 bytes)
  - Block align: 2 (2 bytes)
  - Bits per sample: 16 (2 bytes)

data chunk (8+ bytes):
  - "data" (4 bytes)
  - Data size (4 bytes)
  - Audio samples (N bytes)
```

### 2. GlassesPlayer.kt ✅
**Location**: `mobile/glasses/android/GlassesPlayer.kt`

**Features**:
- ✅ Bluetooth SCO connection management
- ✅ WAV file reading and parsing
- ✅ PCM audio playback through Bluetooth speakers
- ✅ Callback-based async API
- ✅ Play/pause/resume/stop controls
- ✅ Raw PCM array playback support
- ✅ Audio attributes: USAGE_VOICE_COMMUNICATION

**API**:
```kotlin
fun playPcm16Mono(samples: ShortArray, sampleRate: Int = 16000)
fun playAudio(file: File, callback: (Exception?) -> Unit)
fun stop()
fun pause()
fun resume()
fun isPlaying(): Boolean
fun getPlaybackProgress(): Double
```

**Technical Details**:
- Sample Rate: 16000 Hz
- Channels: Mono (CHANNEL_OUT_MONO)
- Bit Depth: 16-bit
- Audio Format: PCM signed 16-bit
- Usage: AudioAttributes.USAGE_VOICE_COMMUNICATION
- Content Type: AudioAttributes.CONTENT_TYPE_SPEECH
- Transfer Mode: AudioTrack.MODE_STREAM
- Audio Mode: AudioManager.MODE_IN_COMMUNICATION

### 3. AudioRouteMonitor.kt (Enhanced) ✅
**Location**: `mobile/glasses/android/AudioRouteMonitor.kt`

**Features**:
- ✅ Real-time audio route monitoring
- ✅ Bluetooth device detection
- ✅ Input/output device enumeration
- ✅ SCO connection status
- ✅ Audio mode reporting

**API**:
```kotlin
fun currentRouteSummary(): String
```

**Output Format**:
```
Inputs:
[Device Name] (type=[TYPE])

Outputs:
[Device Name] (type=[TYPE])

Mode=[AUDIO_MODE] SCO=[true/false]
```

### 4. GlassesAudioModule.kt (NEW) ✅
**Location**: `mobile/glasses/android/GlassesAudioModule.kt`

**Features**:
- ✅ React Native bridge module
- ✅ Promise-based API for JavaScript
- ✅ Recording management
- ✅ Playback management
- ✅ File management (list/delete recordings)
- ✅ Audio route monitoring
- ✅ Automatic cleanup

**React Native Methods**:
```kotlin
@ReactMethod fun getAudioRoute(promise: Promise)
@ReactMethod fun startRecording(durationMs: Int, promise: Promise)
@ReactMethod fun stopRecording(promise: Promise)
@ReactMethod fun isRecording(promise: Promise)
@ReactMethod fun playAudio(filePath: String, promise: Promise)
@ReactMethod fun playLastRecording(promise: Promise)
@ReactMethod fun stopPlayback(promise: Promise)
@ReactMethod fun pausePlayback(promise: Promise)
@ReactMethod fun resumePlayback(promise: Promise)
@ReactMethod fun isPlaying(promise: Promise)
@ReactMethod fun getLastRecordingPath(promise: Promise)
@ReactMethod fun listRecordings(promise: Promise)
@ReactMethod fun deleteRecording(filePath: String, promise: Promise)
```

### 5. GlassesAudioPackage.kt (NEW) ✅
**Location**: `mobile/glasses/android/GlassesAudioPackage.kt`

**Features**:
- ✅ React Native package registration
- ✅ Module instantiation

### 6. GlassesAudio.js (NEW) ✅
**Location**: `mobile/glasses/GlassesAudio.js`

**Features**:
- ✅ JavaScript wrapper for native module
- ✅ Promise-based API
- ✅ Platform checking (Android only)
- ✅ Comprehensive JSDoc documentation
- ✅ Error handling

**JavaScript API**:
```javascript
GlassesAudio.isAvailable()
GlassesAudio.getAudioRoute()
GlassesAudio.startRecording(durationMs)
GlassesAudio.stopRecording()
GlassesAudio.isRecording()
GlassesAudio.playAudio(filePath)
GlassesAudio.playLastRecording()
GlassesAudio.stopPlayback()
GlassesAudio.pausePlayback()
GlassesAudio.resumePlayback()
GlassesAudio.isPlaying()
GlassesAudio.getLastRecordingPath()
GlassesAudio.listRecordings()
GlassesAudio.deleteRecording(filePath)
```

### 7. BRIDGE_README.md (NEW) ✅
**Location**: `mobile/glasses/BRIDGE_README.md`

**Features**:
- ✅ Comprehensive integration guide
- ✅ Installation instructions (Expo and bare RN)
- ✅ Usage examples
- ✅ Full API reference
- ✅ Troubleshooting guide
- ✅ Testing checklist

## Architecture

```
┌─────────────────────────────────────────────────┐
│  React Native (JavaScript)                      │
│  - GlassesDiagnosticsScreen.js                  │
│  - Uses GlassesAudio.js for native calls        │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│  JavaScript Bridge                              │
│  - GlassesAudio.js                              │
│  - Platform-aware wrapper                       │
│  - Error handling                               │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│  React Native Module                            │
│  - GlassesAudioModule.kt                        │
│  - GlassesAudioPackage.kt                       │
│  - Promise-based callbacks                      │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│  Native Android Components                      │
├─────────────────────────────────────────────────┤
│  GlassesRecorder.kt                             │
│  - Bluetooth SCO management                     │
│  - AudioRecord (VOICE_COMMUNICATION)            │
│  - WAV file writing                             │
│                                                  │
│  GlassesPlayer.kt                               │
│  - Bluetooth SCO management                     │
│  - AudioTrack (USAGE_VOICE_COMMUNICATION)       │
│  - WAV file reading                             │
│                                                  │
│  AudioRouteMonitor.kt                           │
│  - AudioManager device monitoring               │
│  - SCO state tracking                           │
└─────────────────────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│  Android System                                 │
│  - AudioManager (MODE_IN_COMMUNICATION)         │
│  - Bluetooth SCO                                │
│  - Meta AI Glasses (Bluetooth HFP)              │
└─────────────────────────────────────────────────┘
```

## Bluetooth SCO Management

### Connection Flow
1. **Setup**: When recording/playback starts
   - Set audio mode: `MODE_IN_COMMUNICATION`
   - Start Bluetooth SCO: `startBluetoothSco()`
   - Enable SCO: `isBluetoothScoOn = true`
   - Wait ~500ms for connection

2. **Monitoring**: During operation
   - Register BroadcastReceiver for `ACTION_SCO_AUDIO_STATE_UPDATED`
   - Track connection state (CONNECTED/DISCONNECTED)
   - Handle state changes

3. **Teardown**: When recording/playback stops
   - Stop Bluetooth SCO: `stopBluetoothSco()`
   - Disable SCO: `isBluetoothScoOn = false`
   - Reset audio mode: `MODE_NORMAL`
   - Unregister BroadcastReceiver

### State Diagram
```
IDLE
  │
  ├─→ startBluetoothSco()
  │   MODE = MODE_IN_COMMUNICATION
  │   isBluetoothScoOn = true
  ↓
SCO_CONNECTING (wait ~500ms)
  ↓
SCO_CONNECTED
  │   (Recording/Playback active)
  │   AudioRecord/AudioTrack uses Bluetooth
  ↓
SCO_DISCONNECTING
  ├─→ stopBluetoothSco()
  │   isBluetoothScoOn = false
  │   MODE = MODE_NORMAL
  ↓
IDLE
```

## File Storage

### Location
Recordings are saved to:
```
[External Files Dir]/Music/audio_diagnostics/
```

Example path:
```
/storage/emulated/0/Android/data/[package]/files/Music/audio_diagnostics/
```

### File Naming
```
glasses_recording_YYYYMMDD_HHMMSS.wav
```

Example:
```
glasses_recording_20260117_143022.wav
```

### File Format
- Container: WAV (RIFF)
- Codec: PCM (uncompressed)
- Sample Rate: 16000 Hz
- Channels: 1 (Mono)
- Bit Depth: 16-bit
- Byte Order: Little-endian
- Signed: Yes

## Permissions Required

### AndroidManifest.xml
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

### Runtime Permissions (Android 6.0+)
- `RECORD_AUDIO` - Required for microphone access
- `BLUETOOTH_CONNECT` - Required for Bluetooth device access (Android 12+)

## Integration Steps

### For Expo Projects (Requires Ejecting)

1. **Eject from Expo managed workflow**:
```bash
cd mobile
npx expo prebuild
```

2. **Copy Kotlin files to Android project**:
```bash
mkdir -p android/app/src/main/java/glasses
cp mobile/glasses/android/*.kt android/app/src/main/java/glasses/
```

3. **Register the package in MainApplication**:

Edit `android/app/src/main/java/[package]/MainApplication.java`:
```java
import glasses.GlassesAudioPackage;

@Override
protected List<ReactPackage> getPackages() {
  return Arrays.asList(
    new MainPackage(),
    new GlassesAudioPackage()
  );
}
```

4. **Add permissions to AndroidManifest.xml**:
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

5. **Import JavaScript module**:
```javascript
import GlassesAudio from './glasses/GlassesAudio';
```

6. **Rebuild Android app**:
```bash
cd android
./gradlew clean
./gradlew assembleDebug
```

## Testing Requirements

### Prerequisites
- Physical Android device (Android 8.0+)
- Meta AI Glasses paired via Bluetooth
- Microphone permission granted
- Bluetooth permission granted (Android 12+)

### Test Scenarios

#### 1. Audio Route Detection
- [ ] Launch app with glasses connected
- [ ] Verify `getAudioRoute()` shows Bluetooth device
- [ ] Disconnect glasses
- [ ] Verify route updates to show phone audio
- [ ] Reconnect glasses
- [ ] Verify route updates to show Bluetooth again

#### 2. Recording
- [ ] Start 10-second recording
- [ ] Speak test phrase into glasses mic
- [ ] Verify recording completes successfully
- [ ] Check WAV file is created
- [ ] Verify file size is reasonable (~320KB for 10s @ 16kHz mono 16-bit)
- [ ] Verify WAV header is valid

#### 3. Playback
- [ ] Play last recording
- [ ] Verify audio plays through glasses speakers
- [ ] Verify audio is audible and clear
- [ ] Test stop functionality mid-playback
- [ ] Test pause/resume functionality

#### 4. Error Handling
- [ ] Test without microphone permission
- [ ] Test with no Bluetooth device connected
- [ ] Test with Bluetooth device disconnected mid-recording
- [ ] Test recording while already recording
- [ ] Test playback of non-existent file

#### 5. File Management
- [ ] List all recordings
- [ ] Verify list shows correct metadata
- [ ] Delete a recording
- [ ] Verify file is removed from filesystem
- [ ] Verify list updates correctly

## Acceptance Criteria Status

✅ **Recording from glasses microphone**
- Uses Bluetooth SCO for glasses mic input
- Writes 16kHz mono WAV files
- Proper audio routing via MODE_IN_COMMUNICATION

✅ **Playback through glasses speakers**
- Uses Bluetooth SCO for glasses speaker output
- Reads WAV files correctly
- Proper audio routing via USAGE_VOICE_COMMUNICATION

✅ **Bluetooth SCO routing management**
- Automatic start/stop on record/play
- State monitoring via BroadcastReceiver
- Proper cleanup on errors

✅ **React Native bridge APIs**
- Complete JavaScript wrapper (GlassesAudio.js)
- Promise-based API
- Record/play/stop/status methods
- File management methods

✅ **WAV output suitable for backend STT**
- 16kHz sample rate
- Mono channel
- 16-bit PCM
- Proper RIFF/WAV headers

✅ **Documentation**
- Comprehensive bridge README
- API reference
- Integration guide
- Troubleshooting guide

## Known Limitations

1. **Expo Managed Workflow**: Requires ejecting to use native modules
2. **Platform Support**: Android only (iOS implementation separate)
3. **Recording Duration**: Fixed at start time (no dynamic extension)
4. **Progress Tracking**: Recording level and playback progress are placeholders
5. **Background Recording**: Not implemented (would require foreground service)

## Next Steps

### Immediate (PR-051)
- [x] Implement GlassesRecorder.kt
- [x] Implement GlassesPlayer.kt
- [x] Create React Native bridge
- [x] Write documentation
- [ ] Test on physical device with Meta AI Glasses
- [ ] Update GlassesDiagnosticsScreen.js to use native module

### Future Enhancements
- [ ] Implement recording level monitoring
- [ ] Implement playback progress tracking
- [ ] Add foreground service for background recording
- [ ] Add real-time audio streaming support
- [ ] Optimize WAV file writing (reduce I/O)
- [ ] Add audio visualization
- [ ] Support multiple sample rates
- [ ] Add audio effects (echo cancellation, noise reduction)

## References

- [BRIDGE_README.md](BRIDGE_README.md) - Integration and usage guide
- [TODO.md](TODO.md) - Implementation checklist
- [README.md](README.md) - Feature specifications
- [../docs/meta-ai-glasses-audio-routing.md](../../docs/meta-ai-glasses-audio-routing.md) - Audio routing documentation
- [Android AudioRecord](https://developer.android.com/reference/android/media/AudioRecord)
- [Android AudioTrack](https://developer.android.com/reference/android/media/AudioTrack)
- [Android AudioManager](https://developer.android.com/reference/android/media/AudioManager)
- [React Native Native Modules](https://reactnative.dev/docs/native-modules-android)
