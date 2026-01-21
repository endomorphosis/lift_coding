# expo-glasses-audio

Expo native module for Meta AI Glasses audio route monitoring, recording, and playback.

## Features

### Audio Route Monitoring
- Real-time audio route monitoring
- Bluetooth device detection
- Bluetooth SCO (Synchronous Connection-Oriented) status tracking
- Audio mode detection
- Device change event notifications
- Input/output device enumeration

### Audio Recording & Playback
- WAV audio recording (PCM 16-bit mono, 16kHz)
- WAV audio playback through Bluetooth SCO
- Recording progress events
- Playback status events
- Automatic SCO routing for glasses/BT audio

## Installation

This is a local Expo module. It's automatically linked when you run the app.

```bash
cd mobile
npm install
```

## Usage

### Audio Route Monitoring

```typescript
import { glassesAudio } from 'expo-glasses-audio';

// Get current audio route
const route = await glassesAudio.getCurrentRoute();
console.log('Audio route:', route);

// Check if Bluetooth is connected
const isConnected = await glassesAudio.isBluetoothConnected();

// Check if SCO is active
const isScoActive = await glassesAudio.isScoConnected();

// Start monitoring for changes
glassesAudio.startMonitoring();

// Listen for route changes
const subscription = glassesAudio.addAudioRouteChangeListener((event) => {
  console.log('Route changed:', event.route);
});

// Stop monitoring
glassesAudio.stopMonitoring();
subscription.remove();
```

### Audio Recording

```typescript
import expoGlassesAudio from 'expo-glasses-audio';

// Start recording for 3 seconds
const result = await expoGlassesAudio.startRecording(3);
console.log('Recording saved to:', result.uri);
console.log('Duration:', result.duration, 'seconds');
console.log('File size:', result.size, 'bytes');

// Listen for recording progress
const progressSub = expoGlassesAudio.addRecordingProgressListener((event) => {
  console.log('Recording:', event.isRecording, 'Duration:', event.duration);
});

// Stop recording manually (before duration expires)
const result = await expoGlassesAudio.stopRecording();
progressSub.remove();
```

### Audio Playback

```typescript
import expoGlassesAudio from 'expo-glasses-audio';

// Play a WAV file
await expoGlassesAudio.playAudio('/path/to/audio.wav');

// Listen for playback status
const playbackSub = expoGlassesAudio.addPlaybackStatusListener((event) => {
  console.log('Playing:', event.isPlaying);
  if (event.error) {
    console.error('Playback error:', event.error);
  }
});

// Stop playback
await expoGlassesAudio.stopPlayback();
playbackSub.remove();
```

## API Reference

### Audio Route Monitoring (glassesAudio)

#### Methods

##### `getCurrentRoute(): Promise<AudioRouteInfo>`

Returns the current audio route information including inputs, outputs, Bluetooth status, and audio mode.

**Returns:**
```typescript
{
  inputs: AudioDevice[];
  outputs: AudioDevice[];
  audioMode: number;
  audioModeName: string;
  isScoOn: boolean;
  isScoAvailable: boolean;
  isBluetoothConnected: boolean;
  timestamp: number;
}
```

##### `getCurrentRouteSummary(): Promise<string>`

Returns a human-readable string summary of the current audio route.

##### `isBluetoothConnected(): Promise<boolean>`

Returns true if any Bluetooth audio device is currently connected.

##### `isScoConnected(): Promise<boolean>`

Returns true if Bluetooth SCO is currently active.

##### `startMonitoring(): void`

Starts monitoring audio route changes. Emits `onAudioRouteChange` events when the route changes.

##### `stopMonitoring(): void`

Stops monitoring audio route changes.

##### `addAudioRouteChangeListener(listener: (event: AudioRouteChangeEvent) => void): Subscription`

Adds a listener for audio route changes. Returns a subscription that can be used to remove the listener.

### Audio Recording & Playback (expoGlassesAudio)

#### Methods

##### `getAudioRoute(): SimpleAudioRouteInfo`

Get the current audio route information in simplified format.

**Returns:**
```typescript
{
  inputDevice: string;
  outputDevice: string;
  sampleRate: number;
  isBluetoothConnected: boolean;
}
```

##### `startRecording(durationSeconds: number): Promise<RecordingResult>`

Start recording audio to a WAV file for the specified duration.

**Parameters:**
- `durationSeconds`: Number of seconds to record

**Returns:**
```typescript
{
  uri: string;       // Absolute path to the recorded WAV file
  duration: number;  // Recording duration in seconds
  size: number;      // File size in bytes
}
```

##### `stopRecording(): Promise<RecordingResult>`

Stop the current recording session before the duration expires.

**Returns:** Same as `startRecording()`

##### `playAudio(fileUri: string): Promise<void>`

Play a WAV audio file through Bluetooth SCO. Supports PCM 16-bit mono format. The promise resolves when playback completes.

**Parameters:**
- `fileUri`: Absolute path to the WAV file to play

**Returns:** Promise that resolves when playback finishes or rejects on error

##### `stopPlayback(): Promise<void>`

Stop the current audio playback.

##### `addRecordingProgressListener(listener: (event: RecordingProgressEvent) => void): Subscription`

Add a listener for recording progress updates.

**Event data:**
```typescript
{
  isRecording: boolean;
  duration: number;
}
```

##### `addPlaybackStatusListener(listener: (event: PlaybackStatusEvent) => void): Subscription`

Add a listener for playback status updates.

**Event data:**
```typescript
{
  isPlaying: boolean;
  error?: string;
}
```

### Events

#### Audio Route Monitoring Events

##### `onAudioRouteChange`

Emitted when the audio route changes (device added/removed, SCO state changed, etc.).

**Event data:**
```typescript
{
  route: AudioRouteInfo;
}
```

#### Recording & Playback Events

##### `onRecordingProgress`

Emitted when recording starts or stops.

##### `onPlaybackStatus`

Emitted when playback starts, stops, or encounters an error.

## Types

### `AudioDevice`

```typescript
interface AudioDevice {
  id: number;
  type: number;
  typeName: string;
  productName: string;
  address?: string;
}
```

### `AudioRouteInfo`

```typescript
interface AudioRouteInfo {
  inputs: AudioDevice[];
  outputs: AudioDevice[];
  audioMode: number;
  audioModeName: string;
  isScoOn: boolean;
  isScoAvailable: boolean;
  isBluetoothConnected: boolean;
  timestamp: number;
}
```

### `SimpleAudioRouteInfo`

```typescript
interface SimpleAudioRouteInfo {
  inputDevice: string;
  outputDevice: string;
  sampleRate: number;
  isBluetoothConnected: boolean;
}
```

### `RecordingResult`

```typescript
interface RecordingResult {
  uri: string;
  duration: number;
  size: number;
}
```

## Audio Format Support

### Recording
- **Format**: WAV (RIFF)
- **Encoding**: PCM 16-bit
- **Channels**: Mono (1)
- **Sample Rate**: 16 kHz
- **Audio Source**: VOICE_COMMUNICATION (optimized for BT SCO)

### Playback
- **Supported Formats**: WAV with PCM 16-bit mono
- **Audio Route**: USAGE_VOICE_COMMUNICATION (routes through BT SCO when available)

## Platform Support

- ✅ Android (API 23+) - Full audio route monitoring with Bluetooth SCO support
- ✅ iOS (11.0+) - Audio route monitoring with AVAudioSession

### iOS Implementation Notes

The iOS implementation provides audio route monitoring using AVAudioSession:

**Supported on iOS:**
- Real-time audio route monitoring via AVAudioSession
- Audio route change notifications
- Bluetooth device detection
- Device enumeration (inputs/outputs)
- Diagnostics UI (native iOS implementation available)

**iOS API Differences:**
- iOS uses simplified route monitoring through AVAudioSession
- Bluetooth SCO-specific methods (`isScoConnected`, `isScoAvailable`) may return fallback values. This is because iOS manages Bluetooth audio connections automatically through AVAudioSession route changes rather than explicit SCO state management
- `audioMode` field may not be populated - iOS uses audio session categories (e.g., playAndRecord, record) instead of Android's audio modes
- Device enumeration provides iOS-specific port types (e.g., MicrophoneBuiltIn, Speaker, BluetoothHFP)

## Permissions

### Android

The module requires the following Android permissions:

```xml
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

### iOS

The module requires the following iOS permissions (configured in `app.json` under `ios.infoPlist`):

- **NSMicrophoneUsageDescription**: Required for audio input monitoring
- **NSBluetoothAlwaysUsageDescription**: Required for Bluetooth device access
- **NSBluetoothPeripheralUsageDescription**: Required for Bluetooth peripheral communication
- **UIBackgroundModes**: Array containing "audio" for background audio support

Info.plist format (configured automatically via app.json):
```xml
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access to record audio commands for your Meta AI Glasses.</string>
<key>NSBluetoothAlwaysUsageDescription</key>
<string>This app needs Bluetooth access to connect to your Meta AI Glasses for audio playback.</string>
<key>NSBluetoothPeripheralUsageDescription</key>
<string>This app needs Bluetooth access to connect to your Meta AI Glasses for audio playback.</string>
<key>UIBackgroundModes</key>
<array>
  <string>audio</string>
</array>
```

All permissions are configured in `app.json`.

## Implementation Details

### Audio Route Monitoring

The module uses Android's AudioManager API to monitor audio routing:

- `AudioManager.getDevices()` - Enumerate input/output devices
- `AudioManager.AudioDeviceCallback` - Monitor device additions/removals (API 23+)
- `AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED` - Monitor Bluetooth SCO state changes
- `AudioManager.ACTION_HEADSET_PLUG` - Monitor wired headset connections

### Audio Recording

The module uses Android's AudioRecord API for recording:

- `AudioRecord` with `VOICE_COMMUNICATION` source for BT SCO compatibility
- Writes standard WAV file format (RIFF header + PCM data)
- Background thread reads audio samples and writes to file
- WAV header is updated with final sizes when recording stops

### Audio Playback

The module uses Android's AudioTrack API for playback:

- Parses WAV header to extract format information
- Reads PCM data into memory
- Uses `AudioTrack` with `USAGE_VOICE_COMMUNICATION` for BT SCO routing
- Notifies completion through events and callbacks

## References

- [Android AudioManager Documentation](https://developer.android.com/reference/android/media/AudioManager)
- [Android AudioRecord Documentation](https://developer.android.com/reference/android/media/AudioRecord)
- [Android AudioTrack Documentation](https://developer.android.com/reference/android/media/AudioTrack)
- [WAV File Format Specification](http://soundfile.sapp.org/doc/WaveFormat/)
- [Meta AI Glasses Audio Routing Documentation](../../../docs/meta-ai-glasses-audio-routing.md)
- [Parent README](../../glasses/README.md)
