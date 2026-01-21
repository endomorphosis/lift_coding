# Build Instructions for iOS Glasses Audio Module

This guide explains how to build and test the iOS native Bluetooth audio functionality.

## Prerequisites

- macOS with Xcode 14+ installed
- Node.js 18+ and npm
- Expo CLI
- Physical iOS device (iOS 13+)
- Meta AI Glasses (Ray-Ban Meta Smart Glasses) paired to device

**Note**: This feature requires native code and cannot run in Expo Go. You must build a development client.

## Setup Steps

### 1. Install Dependencies

```bash
cd mobile
npm ci
```

### 2. Prebuild iOS Project

This generates the native iOS project with your custom modules:

```bash
npx expo prebuild --platform ios --clean
```

This creates:
- `mobile/ios/` directory with Xcode project
- Links native modules automatically
- Configures Info.plist with required permissions

### 3. Open in Xcode

```bash
open ios/mobiletemp.xcworkspace
```

### 4. Configure Signing

In Xcode:
1. Select project in navigator
2. Select target "mobiletemp"
3. Go to "Signing & Capabilities" tab
4. Select your development team
5. Xcode will automatically manage provisioning

### 5. Add Native Files (if not auto-linked)

If the native module files aren't automatically included:

1. In Xcode, right-click on project
2. Select "Add Files to mobiletemp..."
3. Navigate to `mobile/modules/expo-glasses-audio/ios/`
4. Select all `.swift` files
5. Ensure "Copy items if needed" is checked
6. Click "Add"

Note: With Expo Modules (`expo-glasses-audio`), `expo prebuild` should auto-link the module. If you need to add files manually, it's usually a sign the prebuild output is stale; try re-running `npx expo prebuild --platform ios --clean`.

### 6. Build and Run

From Xcode:
1. Select your physical iOS device (not simulator)
2. Click Run (⌘R)

Or from terminal:
```bash
npx expo run:ios --device
```

## Testing

### 1. Pair Meta AI Glasses

Before testing:
1. Open iOS Settings > Bluetooth
2. Put glasses in pairing mode (if not paired)
3. Connect to glasses
4. Verify connection in Bluetooth settings

### 2. Launch Diagnostics Screen

1. Open app on device
2. Navigate to "Glasses Diagnostics" tab
3. You should see:
   - Native module availability indicator
   - Current audio route
   - Connection state

### 3. Toggle Modes

#### DEV Mode (Phone Mic/Speaker)
- Toggle DEV mode ON
- Status shows: "✓ DEV Mode Active"
- Audio route shows: "Phone mic → Phone speaker"
- Uses Expo Audio fallback

#### Glasses Mode (Bluetooth)
- Toggle DEV mode OFF
- Status shows: "✓ Bluetooth Connected" (if glasses paired)
- Audio route shows Bluetooth device details
- Uses native iOS APIs

### 4. Test Recording

1. Tap "Start Recording"
2. Speak into glasses microphone (or phone mic in DEV mode)
3. Recording auto-stops after 10 seconds
4. Check success message with file path

Verify file:
```bash
# On device, files are in:
# Documents/audio_diagnostics/glasses_test_*.wav

# Check file format (if you extract it):
ffprobe glasses_test_*.wav
# Should show: 16000 Hz, mono, s16
```

### 5. Test Playback

1. Tap "Play Last Recording"
2. Audio should play through glasses speakers (or phone in DEV mode)
3. Verify audio is clear and audible
4. Tap "Stop Playback" to interrupt

### 6. Test Route Monitoring

1. While on diagnostics screen, disconnect glasses
2. Watch connection state change to "⚠ No Bluetooth Device"
3. Reconnect glasses
4. Watch connection state change to "✓ Bluetooth Connected"
5. Audio route should update automatically

### 7. Test Backend Integration

1. Record audio (either mode)
2. Tap "Send to Backend & Get Response"
3. Audio is uploaded to `/v1/dev/audio`
4. Sent to `/v1/command` for processing
5. Response displayed in UI

## Troubleshooting

### Build Errors

**"No such module 'React'"**
- Run `npx expo prebuild --clean` again
- Ensure you're opening `.xcworkspace`, not `.xcodeproj`

**"Undefined symbols for architecture arm64"**
- Clean build folder (⌘⇧K)
- Delete `ios/build/` directory
- Rebuild

### Runtime Errors

**"Native module not available"**
- Check module is properly linked
- Verify you're running development build, not Expo Go
- Check logs for module registration

**"No Bluetooth device detected"**
- Verify glasses are paired in Settings
- Check Bluetooth is enabled
- Try forgetting and re-pairing device

**"Recording permission denied"**
- Check Info.plist has microphone usage description
- Reset permissions: Settings > Privacy > Microphone > [Your App]
- Restart app

**"Audio route stuck on phone speaker"**
- Disconnect and reconnect Bluetooth
- Restart app to reset audio session
- Check glasses are not in another audio mode

### Debug Logging

Enable verbose logging:

```javascript
// In GlassesDiagnosticsScreen.js
console.log('Native module available:', GlassesAudio.isAvailable());
console.log('Bluetooth connected:', await GlassesAudio.isBluetoothConnected());
console.log('Route info:', await GlassesAudio.getDetailedRouteInfo());
```

Check Xcode console for native logs:
- Look for "⚠️ Warning" messages about Bluetooth
- Check for AVAudioSession errors

## Development Tips

### Hot Reload

Native module changes require rebuild:
```bash
# After changing Swift code:
npx expo run:ios --device
```

JavaScript changes support hot reload:
- Save file
- App automatically reloads

### Testing Without Glasses

The module gracefully falls back to phone mic/speaker if no Bluetooth device is connected. You can test basic functionality without glasses.

### File Inspection

To inspect recorded WAV files:

1. Connect device to Mac
2. Open Xcode > Window > Devices and Simulators
3. Select your device
4. Download app container
5. Navigate to Documents/audio_diagnostics/
6. Copy WAV files to Mac for analysis

## EAS Build (Production)

For production builds with EAS:

```bash
# Install EAS CLI
npm install -g eas-cli

# Configure project
eas build:configure

# Build for iOS
eas build --platform ios --profile production
```

Update `eas.json`:
```json
{
  "build": {
    "production": {
      "ios": {
        "buildConfiguration": "Release"
      }
    }
  }
}
```

## Next Steps

After confirming iOS works:

1. Test with multiple Bluetooth devices
2. Test interruptions (phone calls)
3. Test background recording
4. Implement Android equivalent
5. Add automated tests
6. Performance profiling
7. Battery usage optimization

## Support

- iOS Issues: Check `mobile/glasses/ios/IMPLEMENTATION.md`
- Module API: Check `mobile/modules/expo-glasses-audio/README.md`
- General: Check `mobile/glasses/README.md`
