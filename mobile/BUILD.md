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

## Verified Local Android Build

This repo now has a host-verified Android debug build path that uses the repo-local toolchains already bootstrapped under `/home/barberb/lift_coding/.tools`.

From `mobile/`:

```bash
npm run android:debug:local
```

Or prepare a connected Android handset end-to-end in one command:

```bash
npm run android:prepare:local
```

What it does:
- sets `JAVA_HOME` to the repo-local JDK 17
- sets `ANDROID_HOME` / `ANDROID_SDK_ROOT` to the repo-local Android SDK
- rewrites `android/local.properties` with that SDK path
- runs Expo Android prebuild with Node 20
- runs `./gradlew assembleDebug`

APK output:

```bash
android/app/build/outputs/apk/debug/app-debug.apk
```

## Meta DAT Reference Mode

The checked-in `expo-meta-wearables-dat` module is now treated as a first-party bridge and diagnostics surface, not as a hard dependency on Meta's GitHub Packages artifacts.

Reason:
- the official Android DAT artifacts exist in GitHub Packages, but this environment does not currently have package-read access to that feed
- the app build should remain reproducible without private or preview package credentials

Current behavior:
- the mobile app builds without the official DAT Maven artifacts
- the native module still exposes a stable diagnostics and session interface
- Android uses reflection so the bridge can detect DAT classes if they are ever added by some other path later
- the Meta DAT repositories remain in the repo as reference implementations and API examples

Engineering direction:
- keep iterating on the local bridge contract for discovery, registration, transport, audio, and camera diagnostics
- use the upstream DAT repositories as reference material rather than required build inputs

Install and launch it on a connected Android handset:

```bash
npm run android:install:local
```

Grant the runtime permissions needed for Bluetooth peer testing:

```bash
npm run android:grant:local
```

Inspect install state, granted permissions, and current foreground activity:

```bash
npm run android:check:local
```

Tail Android logs relevant to the peer bridge and app runtime:

```bash
npm run android:logcat:local
```

To target a specific device when multiple phones are connected:

```bash
./scripts/install-android-debug-apk.sh <adb-serial>
./scripts/prepare-android-local-device.sh <adb-serial>
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

If you want the known-good host build path used in verification, use:

```bash
npm run android:debug:local
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

## Android Peer Bring-Up

After `npm run android:debug:local`, use this exact sequence on two Android handsets:

1. Install and launch the debug APK on each handset.
2. The shortest setup path is `npm run android:prepare:local` once per handset.
3. If two handsets are attached at once, run `./scripts/prepare-android-local-device.sh <adb-serial>` for each one.
4. Open the `Glasses` tab in the app.
5. On device A, tap `Advertise Local Identity`.
6. On device B, tap `Scan Nearby Peers`.
7. Select the discovered row for device A and tap `Connect This Peer`.
8. On either side, tap `Send Ping Frame`.
9. On the receiving side, use `Validate + Replay Ack via Backend` or enable auto inbound validation.
10. Confirm that `frameReceived` and decoded `ack` details appear in the diagnostics card.
11. If reconnects look stuck after backend restart or app reset, use `Load Transport Sessions` in the `Glasses` tab first and inspect the matched cursor health.
12. Treat `fresh` as likely expected, `aging` as suspicious, and `stale` as a strong signal that the persisted cursor may need to be cleared before reconnect.
13. Use `Clear Matched Transport Session` or `Clear Transport Session` for the affected peer before retrying the connect flow when the matched cursor looks stale.
14. For backend relay validation, switch to the `Peer Chat` tab and use:
    `Refresh All Peer Chat Diagnostics`, `Load Chat History`, `Refresh Backend Outbox Status`, the transport-session controls, and the urgent/leased-message controls.
15. If a handset reconnect path still looks stuck, use `Load Transport Sessions` in the `Peer Chat` tab to inspect the same persisted runtime cursors with more backend context.
16. Watch the `Last synced` and `Sync health` lines in the `Peer Chat` summary card. They now update as relative freshness signals, so you can see when the diagnostics state is fresh, aging, or stale without comparing wall-clock times.

If anything fails during steps 5-10, run `npm run android:logcat:local` and repeat the action to capture:
- `BluetoothPeerBridge` scan, advertise, connect, and frame logs
- `ReactNativeJS` diagnostics screen logs
- `AndroidRuntime` crashes

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
│       ├── GlassesDiagnosticsScreen.js  # BLE/audio/session diagnostics UI
│       └── PeerChatDiagnosticsScreen.js # Backend chat/outbox diagnostics UI
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
