# expo-glasses-audio

Expo native module for Meta AI Glasses audio route monitoring.

## Features

- Real-time audio route monitoring
- Bluetooth device detection
- Bluetooth SCO (Synchronous Connection-Oriented) status tracking
- Audio mode detection
- Device change event notifications
- Input/output device enumeration

## Installation

This is a local Expo module. It's automatically linked when you run the app.

```bash
cd mobile
npm install
```

## Usage

```typescript
import GlassesAudio from './modules/expo-glasses-audio';

// Get current audio route
const route = await GlassesAudio.getCurrentRoute();
console.log('Audio route:', route);

// Check if Bluetooth is connected
const isConnected = await GlassesAudio.isBluetoothConnected();

// Check if SCO is active
const isScoActive = await GlassesAudio.isScoConnected();

// Start monitoring for changes
GlassesAudio.startMonitoring();

// Listen for route changes
const subscription = GlassesAudio.addAudioRouteChangeListener((event) => {
  console.log('Route changed:', event.route);
});

// Stop monitoring
GlassesAudio.stopMonitoring();
subscription.remove();
```

## API Reference

### Methods

#### `getCurrentRoute(): Promise<AudioRouteInfo>`

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

#### `getCurrentRouteSummary(): Promise<string>`

Returns a human-readable string summary of the current audio route.

#### `isBluetoothConnected(): Promise<boolean>`

Returns true if any Bluetooth audio device is currently connected.

#### `isScoConnected(): Promise<boolean>`

Returns true if Bluetooth SCO is currently active.

#### `startMonitoring(): void`

Starts monitoring audio route changes. Emits `onAudioRouteChange` events when the route changes.

#### `stopMonitoring(): void`

Stops monitoring audio route changes.

#### `addAudioRouteChangeListener(listener: (event: AudioRouteChangeEvent) => void): Subscription`

Adds a listener for audio route changes. Returns a subscription that can be used to remove the listener.

### Events

#### `onAudioRouteChange`

Emitted when the audio route changes (device added/removed, SCO state changed, etc.).

**Event data:**
```typescript
{
  route: AudioRouteInfo;
}
```

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

## Platform Support

- ✅ Android (API 23+) - Full audio route monitoring with Bluetooth SCO support
- ✅ iOS (11.0+) - Audio route monitoring with recording and playback capabilities

### iOS Implementation Notes

The iOS implementation provides audio route monitoring using AVAudioSession with additional recording and playback features:

**Supported on iOS:**
- Real-time audio route monitoring via AVAudioSession
- Audio route change notifications
- Bluetooth device detection
- Device enumeration (inputs/outputs)
- Audio recording (via `startRecording`/`stopRecording`)
- Audio playback (via `playAudio`/`stopPlayback`)
- Diagnostics UI

**iOS API Differences:**
- `getAudioRoute()` returns simplified route info:
  ```typescript
  {
    inputDevice: string;      // e.g., "iPhone Microphone (MicrophoneBuiltIn)"
    outputDevice: string;     // e.g., "iPhone Speaker (Speaker)"
    sampleRate: number;       // e.g., 48000
    isBluetoothConnected: boolean;
  }
  ```
- No Bluetooth SCO-specific methods (`isScoConnected`, `isScoAvailable`) - iOS manages Bluetooth audio connections automatically through AVAudioSession route changes rather than explicit SCO state management
- No `audioMode` field - iOS uses audio session categories (e.g., playAndRecord, record) instead of Android's audio modes
- Recording and playback methods are iOS-specific extensions

## Permissions

### Android

The module requires the following Android permissions:

```xml
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

### iOS

The module requires the following iOS permissions (configured in `app.json` under `ios.infoPlist`):

- **NSMicrophoneUsageDescription**: Required for audio recording
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

These permissions are already configured in `app.json`.

## Implementation Details

### Android

The module uses Android's AudioManager API to monitor audio routing:

- `AudioManager.getDevices()` - Enumerate input/output devices
- `AudioManager.AudioDeviceCallback` - Monitor device additions/removals (API 23+)
- `AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED` - Monitor Bluetooth SCO state changes
- `AudioManager.ACTION_HEADSET_PLUG` - Monitor wired headset connections

### iOS

The module uses iOS's AVAudioSession API for audio routing:

- `AVAudioSession.currentRoute` - Get current input/output devices
- `AVAudioSession.routeChangeNotification` - Monitor route changes
- `AVAudioRecorder` - Record audio from the selected input device
- `AVAudioPlayer` - Play audio to the selected output device

## iOS-Specific API Extensions

The iOS implementation includes additional methods for recording and playback:

### Recording

```typescript
// Start recording for a specified duration (in seconds)
const result = await GlassesAudio.startRecording(10); // Records for 10 seconds
console.log('Recording saved to:', result.uri);

// Stop recording early
await GlassesAudio.stopRecording();
```

### Playback

```typescript
// Play an audio file
await GlassesAudio.playAudio('file:///path/to/audio.wav');

// Stop playback
await GlassesAudio.stopPlayback();
```

## References

- [Android AudioManager Documentation](https://developer.android.com/reference/android/media/AudioManager)
- [iOS AVAudioSession Documentation](https://developer.apple.com/documentation/avfoundation/avaudiosession)
- [Meta AI Glasses Audio Routing Documentation](../../../docs/meta-ai-glasses-audio-routing.md)
- [Parent README](../../glasses/README.md)
