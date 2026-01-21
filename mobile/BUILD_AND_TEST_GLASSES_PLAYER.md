# Glasses Audio Playback - Build & Test Guide

## Overview

This implementation provides native audio playback through Meta AI Glasses using the `expo-glasses-audio` Expo module (AVAudioEngine routing on iOS; Bluetooth SCO routing on Android).

## Architecture

```
mobile/
├── modules/expo-glasses-audio/        # Native Expo module (record + playback)
│   ├── ios/
│   │   └── GlassesPlayer.swift        # Core audio player with Bluetooth routing
│   ├── android/
│   │   └── ...                        # Bluetooth SCO playback + WAV parsing
│   └── index.ts                        # Public JS API
├── src/
│   ├── hooks/
│   │   └── useGlassesPlayer.js        # React hook for native player
│   └── screens/
│       └── GlassesDiagnosticsScreen.js  # UI with native player controls
└── glasses/ios/
    └── GlassesPlayer.swift             # Reference implementation
```

## Building for iOS

### Prerequisites

1. **macOS with Xcode** (required for iOS development)
2. **Physical iPhone** (Bluetooth doesn't work in simulator)
3. **Meta AI Glasses** paired via Bluetooth
4. **Expo CLI** installed: `npm install -g expo-cli`
5. **EAS CLI** (optional): `npm install -g eas-cli`

### Option 1: Local Development Build

```bash
cd mobile

# Install dependencies
npm ci

# Generate native iOS project
expo prebuild --platform ios

# Build and run on connected device
expo run:ios --device

# Or open in Xcode for more control
open ios/*.xcworkspace
# Then build & run from Xcode
```

### Option 2: EAS Build (Cloud Build)

```bash
cd mobile

# Configure EAS (first time only)
eas build:configure

# Create development build
eas build --profile development --platform ios

# Install on device
# Download .ipa from EAS dashboard
# Install via Apple Configurator or Xcode Devices window
```

### Option 3: Expo Development Client

```bash
# Install Expo's pre-built development client
# Available on TestFlight or App Store

# Then run expo start and scan QR code
expo start --dev-client
```

## Testing

### 1. Verify Native Module Loaded

1. Open the app
2. Navigate to "Glasses Diagnostics" screen
3. Scroll to "Native Glasses Player" section
4. Should show: **"✓ Native player available"**

If you see "⚠️ Native player only available in iOS development builds":
- You're running in Expo Go (doesn't support custom native modules)
- Need to create a development build (see build instructions above)

### 2. Test Bluetooth Routing

**Prerequisites:**
- iPhone with iOS 13+
- Meta AI Glasses paired via Bluetooth
- Glasses should appear in Settings > Bluetooth as "Connected"

**Test steps:**

1. **Record audio:**
   - Tap "🎤 Start Recording"
   - Speak a test phrase
   - Tap "⏹ Stop Recording"
   - Verify "✓ Recording saved locally" appears

2. **Play through glasses:**
   - Scroll to "Native Glasses Player" section
   - Tap "🔊 Play Through Glasses"
   - Audio should play through glasses speakers
   - Tap "⏹ Stop Native Playback" to stop

3. **Verify Bluetooth routing:**
   - During playback, check Control Center audio routing
   - Should show Meta AI Glasses as output device
   - If it doesn't route automatically, manually select glasses in Control Center

### 3. Test TTS Playback

To test with backend TTS audio:

```javascript
// In GlassesDiagnosticsScreen.js, add function:
const playTTSFromBackend = async () => {
  try {
    // Fetch TTS from backend
    const response = await fetch('http://YOUR_BACKEND/v1/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: 'Hello from your glasses' })
    });
    
    // Save to file
    const audioBlob = await response.blob();
    const fileUri = FileSystem.documentDirectory + 'tts_audio.wav';
    // ... save blob to file ...
    
    // Play through glasses
    await playAudioThroughGlasses(fileUri);
  } catch (error) {
    console.error('TTS playback failed:', error);
  }
};
```

## Troubleshooting

### Native module not found

**Error:** `"Native glasses audio player not available"`

**Solution:**
- You're running in Expo Go
- Create a development build: `expo prebuild && expo run:ios --device`

### Audio not routing to glasses

**Symptoms:** Audio plays through phone speaker instead of glasses

**Solutions:**
1. **Check Bluetooth connection:**
   - Open Settings > Bluetooth
   - Verify glasses are "Connected" (not just "Paired")
   - Disconnect and reconnect if needed

2. **Check audio route manually:**
   - Open Control Center during playback
   - Tap audio card
   - Select Meta AI Glasses as output

3. **Reset audio session:**
   ```swift
   // In GlassesPlayer.swift, try adding to play():
   try session.setActive(false)
   try session.setActive(true)
   ```

4. **Check AVAudioSession category:**
   - Ensure using `.playAndRecord` with `.voiceChat` mode
   - Ensure `.allowBluetooth` and `.allowBluetoothA2DP` options set

### Build fails

**Error:** `"Module 'ExpoModulesCore' not found"`

**Solution:**
```bash
cd mobile
rm -rf ios node_modules
npm ci
expo prebuild --clean
```

**Error:** `"No such module 'GlassesAudioPlayer'"`

**Solution:**
- Module not linked properly
- Try: `expo prebuild --clean`
- Or in Xcode: Product > Clean Build Folder

### Runtime crashes

**Error:** App crashes when playing audio

**Debug steps:**
1. Check Xcode console for error messages
2. Verify file URI is valid: `file:///path/to/audio.wav`
3. Check audio file format (WAV, M4A supported)
4. Add error handling in Swift:
   ```swift
   do {
     try player.play(fileURL: fileURL)
   } catch {
     print("Playback error: \(error)")
     throw error
   }
   ```

## Permissions

The following permissions are configured in `app.json`:

```json
{
  "ios": {
    "infoPlist": {
      "NSMicrophoneUsageDescription": "Record audio commands for Meta AI Glasses",
      "NSBluetoothAlwaysUsageDescription": "Connect to Meta AI Glasses for audio",
      "NSBluetoothPeripheralUsageDescription": "Connect to Meta AI Glasses for audio"
    }
  }
}
```

Users will be prompted to grant these permissions on first use.

## API Reference

### JavaScript API

```typescript
import { playAudioThroughGlasses, stopGlassesAudio, isGlassesPlayerAvailable } from '../hooks/useGlassesPlayer';

// Check if native module available
if (isGlassesPlayerAvailable()) {
  // Play audio file
  await playAudioThroughGlasses('file:///path/to/audio.wav');
  
  // Stop playback
  await stopGlassesAudio();
}
```

### Swift API

```swift
let player = GlassesPlayer()

// Play audio
try player.play(fileURL: URL(fileURLWithPath: "/path/to/audio.wav"))

// Check if playing
let playing = player.isPlaying()

// Stop
player.stop()
```

## Known Limitations

1. **Expo Go not supported:** Requires a development build with native code
2. **Physical device required:** Bluetooth doesn't work in iOS Simulator
3. **No progress tracking:** Currently no playback progress callbacks
4. **No volume control:** Uses system volume

## Next Steps

1. Add playback progress events
2. Add volume control
3. Implement audio interruption handling (phone calls)
4. Add Android support with Bluetooth SCO
5. Add audio format conversion for unsupported formats

## References

- [mobile/glasses/README.md](../../glasses/README.md) - Full glasses audio guide
- [mobile/glasses/TODO.md](../../glasses/TODO.md) - Implementation checklist
- [docs/meta-ai-glasses-audio-routing.md](../../../docs/meta-ai-glasses-audio-routing.md) - Audio routing docs
- [Expo Modules API](https://docs.expo.dev/modules/overview/)
- [Apple AVAudioSession](https://developer.apple.com/documentation/avfoundation/avaudiosession)
- [Apple AVAudioEngine](https://developer.apple.com/documentation/avfoundation/avaudioengine)
