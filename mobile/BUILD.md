# Building with expo-dev-client for Native Modules

This guide explains how to build and run the mobile app with native Bluetooth audio support for Meta AI Glasses.

## Overview

The app includes a native module (`expo-glasses-audio`) that provides Bluetooth audio routing capabilities. To use this functionality, you need to build a development client instead of using Expo Go.

## Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Expo CLI: `npm install -g expo-cli`
- EAS CLI: `npm install -g eas-cli`

**For iOS:**
- macOS with Xcode 14.0 or later
- iOS device (Bluetooth testing requires physical device)
- Apple Developer account

**For Android:**
- Android Studio
- Android device (Bluetooth testing requires physical device)
- Java Development Kit (JDK) 17

## Installation

1. Navigate to the mobile directory:

```bash
cd mobile
```

2. Install dependencies:

```bash
npm ci
```

## Building for Development

### Option 1: Local Build (Recommended for Development)

#### iOS (macOS only)

1. Generate native iOS project:

```bash
npx expo prebuild --platform ios
```

2. Install CocoaPods dependencies:

```bash
cd ios
pod install
cd ..
```

3. Open in Xcode and run:

```bash
npx expo run:ios --device
```

Or open `ios/handsfree-mobile.xcworkspace` in Xcode and build/run to your device.

#### Android

1. Generate native Android project:

```bash
npx expo prebuild --platform android
```

2. Run on connected device:

```bash
npx expo run:android --device
```

### Option 2: EAS Build (Cloud Build)

1. Configure EAS:

```bash
eas init
```

2. Build development client:

For iOS:
```bash
eas build --profile development --platform ios
```

For Android:
```bash
eas build --profile development --platform android
```

3. Install the resulting app on your device

4. Start the development server:

```bash
npx expo start --dev-client
```

## Testing Native Bluetooth Audio

### Setup

1. Pair your Meta AI Glasses (or any Bluetooth headset) with your device through system settings
2. Launch the development build of the app
3. Navigate to the "Glasses" tab
4. Ensure "Glasses Mode" is enabled (toggle should be OFF for dev mode, ON for glasses mode)

### Testing Flow

1. **Check Audio Route**
   - Tap "🔄 Refresh Status"
   - Verify "Connection State" shows "✓ Bluetooth Connected"
   - Verify "Audio Route" displays your Bluetooth device name

2. **Test Recording**
   - Tap "🎤 Start Recording"
   - Speak into your Bluetooth device microphone for ~5 seconds
   - Recording will auto-stop after 10 seconds
   - Verify success message with file location

3. **Test Playback**
   - Tap "▶️ Play Last Recording"
   - Audio should play through Bluetooth device speakers
   - Verify you can hear the recording clearly

4. **Test Backend Integration**
   - After recording, tap "🚀 Send to Backend & Get Response"
   - Verify the pipeline processes successfully
   - Check for response in the "Backend Response" section

### Troubleshooting

**"Native module not available" error:**
- You're running in Expo Go instead of a development build
- Build and install a development client as described above

**"No Bluetooth Device" warning:**
- Ensure Bluetooth device is paired in system settings
- Verify device is connected (check system Bluetooth settings)
- Try disconnecting and reconnecting the device

**Recording has no audio:**
- Check microphone permissions (Settings > [App Name] > Microphone)
- Ensure Bluetooth device microphone is not muted
- Try speaking louder or closer to the microphone

**Playback goes to phone speaker:**
- Verify Bluetooth device is still connected
- Check system audio output settings
- Some Bluetooth devices require manual audio route selection

## DEV Mode vs Glasses Mode

### DEV Mode (Toggle ON)
- Uses phone's built-in microphone and speaker
- No Bluetooth required
- Faster iteration for testing backend integration
- Uses expo-av for audio handling

### Glasses Mode (Toggle OFF)
- Uses Bluetooth audio routing via native modules
- Requires physical Bluetooth device
- Tests end-to-end audio pipeline with actual glasses
- Uses custom native iOS/Android audio code

## Project Structure

```
mobile/
├── modules/
│   └── expo-glasses-audio/          # Local Expo module
│       ├── ios/                      # iOS native code
│       │   ├── ExpoGlassesAudioModule.swift
│       │   ├── AudioRouteMonitor.swift
│       │   ├── GlassesRecorder.swift
│       │   └── GlassesPlayer.swift
│       ├── android/                  # Android native code
│       │   └── src/main/java/expo/modules/glassesaudio/
│       │       ├── ExpoGlassesAudioModule.kt
│       │       ├── AudioRouteMonitor.kt
│       │       ├── GlassesRecorder.kt
│       │       └── GlassesPlayer.kt
│       ├── index.ts                  # TypeScript API
│       └── expo-module.config.json   # Module configuration
├── src/
│   └── screens/
│       └── GlassesDiagnosticsScreen.js  # Main diagnostics UI
├── app.json                          # Expo configuration
├── package.json
└── BUILD.md                          # This file
```

## Native Module API

```typescript
import expoGlassesAudio from 'expo-glasses-audio';

// Get current audio route
const route = expoGlassesAudio.getAudioRoute();
// { inputDevice, outputDevice, sampleRate, isBluetoothConnected }

// Start recording (10 seconds)
const result = await expoGlassesAudio.startRecording(10);
// { uri, duration, size }

// Play audio file
await expoGlassesAudio.playAudio(fileUri);

// Stop playback
await expoGlassesAudio.stopPlayback();

// Listen for route changes
const subscription = expoGlassesAudio.addAudioRouteChangeListener((route) => {
  console.log('Route changed:', route);
});
```

## Permissions

The app requests the following permissions:

**iOS (Info.plist):**
- `NSMicrophoneUsageDescription` - Record audio from glasses
- `NSBluetoothPeripheralUsageDescription` - Connect to Bluetooth devices
- `NSBluetoothAlwaysUsageDescription` - Maintain Bluetooth connection

**Android (AndroidManifest.xml):**
- `RECORD_AUDIO` - Record audio from glasses
- `BLUETOOTH` - Access Bluetooth
- `BLUETOOTH_ADMIN` - Manage Bluetooth connections
- `BLUETOOTH_CONNECT` - Connect to paired devices
- `BLUETOOTH_SCAN` - Scan for devices
- `MODIFY_AUDIO_SETTINGS` - Route audio to Bluetooth

## Backend Setup

Ensure the backend is running and accessible:

```bash
# From repository root
cd /path/to/lift_coding

# Set up and start backend
python -m venv venv
source venv/bin/activate
pip install -e .
export DATABASE_URL="sqlite:///./handsfree.db"
uvicorn handsfree.api:app --host 0.0.0.0 --port 8080
```

Update backend URL in `src/api/config.js`:

```javascript
// For physical device on same network
export const BASE_URL = 'http://YOUR_COMPUTER_IP:8080';
```

## Development Workflow

1. Make changes to native code or JS
2. For native changes:
   - iOS: Rebuild in Xcode or `npx expo run:ios`
   - Android: `npx expo run:android`
3. For JS changes: Just save (Fast Refresh)
4. Test on physical device with Bluetooth headset

## References

- [Expo Dev Client](https://docs.expo.dev/develop/development-builds/introduction/)
- [Expo Modules API](https://docs.expo.dev/modules/overview/)
- [Meta AI Glasses Audio Routing](../../docs/meta-ai-glasses-audio-routing.md)
- [Glasses Audio Implementation](../glasses/README.md)

## Support

For issues or questions:
- Check troubleshooting section above
- Review diagnostic screen error messages
- Check native module console logs
- Verify Bluetooth device is properly paired
