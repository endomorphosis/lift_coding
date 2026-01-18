# Glasses Audio Native Module

This module provides native iOS audio routing capabilities for the Meta AI Glasses integration.

## Overview

The Glasses Audio module exposes native AVAudioSession functionality to React Native/Expo, enabling:
- Real-time Bluetooth audio route monitoring
- Detection of Meta AI Glasses connection
- Native audio recording from Bluetooth mic
- Native audio playback through Bluetooth speakers

## Architecture

This module consists of:
- **JavaScript/TypeScript API** (`index.ts`) - High-level interface for React Native
- **iOS Native Module** (`ios/GlassesAudioModule.swift`) - Swift implementation using AVAudioSession
- **Native Audio Classes** - Wrappers around existing Swift implementations in `mobile/glasses/ios/`

## Usage

### Check Availability

```typescript
import GlassesAudio from './modules/glasses-audio';

if (GlassesAudio.isAvailable()) {
  // Native module is loaded
} else {
  // Fall back to Expo Audio APIs
}
```

### Monitor Audio Route

```typescript
// Start monitoring and get current route
const route = await GlassesAudio.startMonitoring();
console.log('Inputs:', route.inputs);
console.log('Outputs:', route.outputs);
console.log('Sample Rate:', route.sampleRate);

// Listen for changes
const subscription = GlassesAudio.addAudioRouteChangeListener((event) => {
  console.log('Route changed:', event.route);
});

// Stop monitoring when done
await GlassesAudio.stopMonitoring();
subscription?.remove();
```

### Recording

```typescript
const outputPath = `${FileSystem.documentDirectory}recording.wav`;
await GlassesAudio.startRecording(outputPath);
// ... record audio ...
await GlassesAudio.stopRecording();
```

### Playback

```typescript
await GlassesAudio.playAudio(filePath);
// ... audio plays ...
await GlassesAudio.stopPlayback();
```

## Development

### Building with Native Module

This module requires a development build (not Expo Go):

```bash
# Install expo-dev-client
npm install expo-dev-client

# Create development build
npx expo run:ios
```

### Testing without Native Module

The module provides mock data when native implementation is not available, allowing development with Expo Go or web.

## Implementation Details

### iOS (Swift)

The native module wraps existing implementations from `mobile/glasses/ios/`:
- `AudioRouteMonitor.swift` - AVAudioSession route monitoring
- `GlassesRecorder.swift` - Audio recording via AVAudioEngine
- `GlassesPlayer.swift` - Audio playback via AVAudioEngine

### Event Flow

1. Native module observes `AVAudioSession.routeChangeNotification`
2. On route change, queries AVAudioSession for current route
3. Formats route data and sends event to JavaScript
4. JavaScript listeners receive event via EventEmitter

## Permissions

Required iOS permissions in `app.json`:

```json
{
  "ios": {
    "infoPlist": {
      "NSMicrophoneUsageDescription": "Access microphone for voice commands via Meta AI Glasses",
      "NSBluetoothPeripheralUsageDescription": "Connect to Meta AI Glasses for audio routing",
      "UIBackgroundModes": ["audio"]
    }
  }
}
```

## Troubleshooting

### "Native module not available"

- Ensure you're using a development build, not Expo Go
- Run `npx expo prebuild` to generate native projects
- Check that `GlassesAudioModule.swift` is included in Xcode project

### No audio route events

- Check iOS permissions are granted
- Ensure Bluetooth device is connected before starting monitoring
- Verify AVAudioSession category allows Bluetooth (`playAndRecord` with `.allowBluetooth`)

## References

- [iOS AVAudioSession Documentation](https://developer.apple.com/documentation/avfoundation/avaudiosession)
- [Expo Modules API](https://docs.expo.dev/modules/overview/)
- [Meta AI Glasses Audio Routing Guide](../../docs/meta-ai-glasses-audio-routing.md)
