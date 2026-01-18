# GlassesAudio Native Module

This module provides a React Native bridge to native iOS and Android audio functionality for Meta AI Glasses integration.

## Overview

The GlassesAudio module enables:
- **Audio Route Monitoring**: Real-time detection of Bluetooth glasses connection
- **Recording**: Capture audio from glasses microphone via Bluetooth HFP/SCO
- **Playback**: Play audio through glasses speakers
- **TTS Integration**: Play backend TTS responses through glasses

## Architecture

```
mobile/
├── modules/glasses-audio/          # React Native bridge module
│   ├── index.js                    # JavaScript API
│   ├── ios/                        # iOS native bridge
│   │   ├── GlassesAudioModule.m    # Objective-C bridge header
│   │   ├── GlassesAudioModule.swift # Swift implementation
│   │   ├── GlassesRecorderBridge.swift
│   │   └── GlassesPlayerBridge.swift
│   └── android/                    # Android native bridge
│       ├── GlassesAudioModule.kt   # Module implementation
│       ├── GlassesAudioPackage.kt  # Package registration
│       ├── GlassesRecorderBridge.kt
│       └── GlassesPlayerBridge.kt
└── glasses/                        # Core native implementations
    ├── ios/
    │   ├── AudioRouteMonitor.swift
    │   ├── GlassesRecorder.swift
    │   └── GlassesPlayer.swift
    └── android/
        ├── AudioRouteMonitor.kt
        ├── GlassesRecorder.kt
        └── GlassesPlayer.kt
```

## Installation

### For Expo Development

**Note**: This module requires native code compilation and will NOT work with Expo Go.

1. **Prebuild the native projects**:
   ```bash
   cd mobile
   expo prebuild
   ```

2. **iOS Setup**:
   ```bash
   cd ios
   pod install
   ```

   Then open `ios/mobile.xcworkspace` in Xcode and:
   - Add all files from `modules/glasses-audio/ios/` to the project
   - Add all files from `glasses/ios/` to the project
   - Build and run on a physical device (simulators don't support Bluetooth audio routing)

3. **Android Setup**:
   
   Open `android/` in Android Studio and:
   - Ensure all `.kt` files from `modules/glasses-audio/android/` are in the project
   - Ensure all `.kt` files from `glasses/android/` are in the project
   - Add the package to `MainApplication.java`:
     ```java
     import com.glassesaudio.GlassesAudioPackage;
     
     @Override
     protected List<ReactPackage> getPackages() {
       List<ReactPackage> packages = new PackageList(this).getPackages();
       packages.add(new GlassesAudioPackage());
       return packages;
     }
     ```
   - Build and run on a physical device

### For React Native (non-Expo)

If using standard React Native CLI:

1. **Link the module** (if auto-linking doesn't work):
   ```bash
   cd mobile
   react-native link
   ```

2. **iOS**:
   - Add module files to Xcode project
   - Run `pod install`
   
3. **Android**:
   - Add the package to `MainApplication.java` (see above)
   - Sync Gradle

## JavaScript API

### Import

```javascript
import GlassesAudio from '../modules/glasses-audio';
```

### Check Availability

```javascript
if (GlassesAudio.isAvailable()) {
  // Native module is compiled and available
} else {
  // Fall back to Expo APIs or show warning
}
```

### Start Monitoring

```javascript
try {
  const currentRoute = await GlassesAudio.startMonitoring();
  console.log('Current audio route:', currentRoute);
} catch (error) {
  console.error('Failed to start monitoring:', error);
}
```

### Listen for Route Changes

```javascript
const subscription = GlassesAudio.addRouteChangeListener((event) => {
  console.log('Route changed:', event.route);
});

// Later: cleanup
subscription.remove();
```

### Record Audio

```javascript
try {
  // Start 10-second recording
  const fileUri = await GlassesAudio.startRecording(10);
  console.log('Recording saved to:', fileUri);
} catch (error) {
  console.error('Recording failed:', error);
}

// Or listen for completion event
const subscription = GlassesAudio.addRecordingCompleteListener((event) => {
  if (event.error) {
    console.error('Recording error:', event.error);
  } else {
    console.log('Recording complete:', event.fileUri);
  }
});
```

### Play Audio

```javascript
try {
  await GlassesAudio.playAudio(fileUri);
  console.log('Playback started');
} catch (error) {
  console.error('Playback failed:', error);
}

// Listen for completion
const subscription = GlassesAudio.addPlaybackCompleteListener((event) => {
  if (event.error) {
    console.error('Playback error:', event.error);
  } else {
    console.log('Playback complete');
  }
});
```

### Stop Playback

```javascript
await GlassesAudio.stopPlayback();
```

### Stop Monitoring

```javascript
await GlassesAudio.stopMonitoring();
```

## Events

The module emits the following events:

### `onRouteChange`

Fired when audio route changes (e.g., glasses connected/disconnected).

```javascript
{
  route: string  // Human-readable route description
}
```

### `onRecordingComplete`

Fired when recording completes (either automatically or manually stopped).

```javascript
{
  fileUri?: string,  // Path to recorded file
  error?: string     // Error message if failed
}
```

### `onPlaybackComplete`

Fired when audio playback completes or is stopped.

```javascript
{
  error?: string  // Error message if failed
}
```

## File Formats

### Recording Output

- **iOS**: 16kHz, 16-bit, mono, WAV format
- **Android**: 16kHz, 16-bit, mono, WAV format
- **Location**: 
  - iOS: `Documents/audio_diagnostics/glasses_<timestamp>.wav`
  - Android: `<app-files-dir>/audio_diagnostics/glasses_<timestamp>.wav`

### Playback Input

Supports WAV files (PCM 16-bit, mono or stereo, any sample rate).

## Permissions

### iOS

Add to `Info.plist`:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Record audio from your Meta AI Glasses</string>
<key>NSBluetoothPeripheralUsageDescription</key>
<string>Connect to Meta AI Glasses for audio routing</string>
<key>NSBluetoothAlwaysUsageDescription</key>
<string>Connect to Meta AI Glasses for audio routing</string>
```

### Android

Add to `AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

Request at runtime:
```javascript
import { PermissionsAndroid, Platform } from 'react-native';

if (Platform.OS === 'android') {
  await PermissionsAndroid.requestMultiple([
    PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
    PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
  ]);
}
```

## Testing

### With Expo Dev Client

1. Create a development build:
   ```bash
   expo prebuild
   eas build --profile development --platform ios
   eas build --profile development --platform android
   ```

2. Install the development build on your device

3. Run the dev server:
   ```bash
   expo start --dev-client
   ```

4. Pair Meta AI Glasses with your device via Bluetooth

5. Open the app and navigate to Glasses Diagnostics screen

6. Test:
   - Route monitoring should show Bluetooth connection
   - Recording should capture from glasses mic
   - Playback should output to glasses speakers

### Without Glasses (Dev Mode)

The GlassesDiagnosticsScreen includes a DEV mode toggle that falls back to using phone mic/speaker when glasses aren't available or native module isn't compiled.

## Troubleshooting

### Module Not Available

**Symptom**: `GlassesAudio.isAvailable()` returns `false`

**Solutions**:
1. Ensure you've run `expo prebuild`
2. Verify native files are included in Xcode/Android Studio project
3. For Android, verify package is registered in `MainApplication.java`
4. Rebuild the app from scratch
5. Cannot use Expo Go - must use development build or standalone build

### Route Not Detected

**Symptom**: Audio route shows "Unknown" or doesn't detect glasses

**Solutions**:
1. Ensure glasses are paired in Bluetooth settings
2. Verify glasses are powered on and charged
3. Test with phone call to verify glasses work for audio
4. Check permissions are granted
5. Try disconnecting/reconnecting glasses

### Recording Fails

**Symptom**: Recording throws error or saves empty file

**Solutions**:
1. Check microphone permission is granted
2. Verify Bluetooth connection is active
3. Ensure no other app is using microphone
4. Test with built-in Voice Memos app first
5. Check audio session configuration

### Playback Goes to Phone Speaker

**Symptom**: Audio plays through phone speaker instead of glasses

**Solutions**:
1. Verify glasses are connected and showing in audio route
2. Check Bluetooth audio is enabled on glasses
3. Try manually selecting glasses in Bluetooth settings
4. Restart audio session by toggling airplane mode
5. Restart app

## Implementation Notes

### iOS

- Uses `AVAudioSession` for route management
- Uses `AVAudioEngine` for recording and playback
- Audio session category: `.playAndRecord`
- Audio session mode: `.voiceChat`
- Options: `.allowBluetooth`, `.defaultToSpeaker`

### Android

- Uses `AudioManager` for route management
- Uses `AudioRecord` with `VOICE_COMMUNICATION` source for recording
- Uses `AudioTrack` with `VOICE_COMMUNICATION` usage for playback
- Automatically manages Bluetooth SCO connection

### Bluetooth Routing

Both platforms automatically route audio to Bluetooth HFP (Hands-Free Profile) devices when available. The implementations prioritize Bluetooth devices for both input and output when connected.

## Future Enhancements

- [ ] Add recording level monitoring
- [ ] Add playback progress callbacks
- [ ] Support for multiple audio formats
- [ ] Streaming recording (real-time data callbacks)
- [ ] Audio effects (noise cancellation, echo cancellation)
- [ ] Background recording support
- [ ] Audio ducking for notifications

## Related Documentation

- [Meta AI Glasses Audio Routing](../../../docs/meta-ai-glasses-audio-routing.md)
- [Glasses Implementation README](../../glasses/README.md)
- [Glasses Implementation TODO](../../glasses/TODO.md)

## License

See LICENSE file in repository root.
