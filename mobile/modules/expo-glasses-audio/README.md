# expo-glasses-audio

Expo native module for Meta AI Glasses audio route monitoring on Android.

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

- ✅ Android (API 23+)
- ⚠️ iOS (not yet implemented)

## Permissions

The module requires the following Android permissions:

```xml
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

These are already configured in `app.json`.

## Implementation Details

The module uses Android's AudioManager API to monitor audio routing:

- `AudioManager.getDevices()` - Enumerate input/output devices
- `AudioManager.AudioDeviceCallback` - Monitor device additions/removals (API 23+)
- `AudioManager.ACTION_SCO_AUDIO_STATE_UPDATED` - Monitor Bluetooth SCO state changes
- `AudioManager.ACTION_HEADSET_PLUG` - Monitor wired headset connections

## References

- [Android AudioManager Documentation](https://developer.android.com/reference/android/media/AudioManager)
- [Meta AI Glasses Audio Routing Documentation](../../../docs/meta-ai-glasses-audio-routing.md)
- [Parent README](../../glasses/README.md)
