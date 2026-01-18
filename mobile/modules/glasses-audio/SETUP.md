# iOS Native Audio Module Setup Guide

This guide explains how to build and test the Glasses Audio native module on iOS.

## Prerequisites

- macOS with Xcode 14+ installed
- iOS device or simulator
- Node.js and npm
- CocoaPods

## Overview

The Glasses Audio native module provides:
- Real-time Bluetooth audio route monitoring via AVAudioSession
- Detection of Meta AI Glasses connection
- Native audio recording from Bluetooth microphone
- Native audio playback through Bluetooth speakers

## Quick Start

### 1. Install Dependencies

```bash
cd mobile
npm install
```

### 2. Install expo-dev-client

The native module requires a development build (not Expo Go):

```bash
npm install expo-dev-client
```

### 3. Prebuild Native Projects

Generate the native iOS project:

```bash
npx expo prebuild --platform ios
```

This will:
- Create the `ios/` directory with Xcode project
- Install CocoaPods dependencies
- Configure the native module

### 4. Build and Run

```bash
# For simulator
npx expo run:ios

# For physical device
npx expo run:ios --device
```

## Module Architecture

```
mobile/
├── modules/
│   └── glasses-audio/
│       ├── index.ts                 # TypeScript API
│       ├── ios/
│       │   ├── GlassesAudioModule.swift      # Expo module bridge
│       │   ├── AudioRouteMonitor.swift       # Route monitoring
│       │   ├── GlassesRecorder.swift         # Recording
│       │   ├── GlassesPlayer.swift           # Playback
│       │   └── GlassesAudio.podspec          # CocoaPods spec
│       └── app.plugin.js            # Expo config plugin
```

## How It Works

### 1. Native Module Registration

The Expo Modules API automatically discovers and registers `GlassesAudioModule`:

```swift
public class GlassesAudioModule: Module {
  public func definition() -> ModuleDefinition {
    Name("GlassesAudio")
    Events("onAudioRouteChange")
    
    AsyncFunction("startMonitoring") { ... }
    AsyncFunction("getCurrentRoute") { ... }
    // ... more functions
  }
}
```

### 2. Audio Route Monitoring

The module uses AVAudioSession to monitor audio routes:

```swift
NotificationCenter.default.addObserver(
  self,
  selector: #selector(handleRouteChange),
  name: AVAudioSession.routeChangeNotification,
  object: nil
)
```

### 3. JavaScript Bridge

React Native code can call native functions:

```typescript
import GlassesAudio from './modules/glasses-audio';

// Check if native module is loaded
if (GlassesAudio.isAvailable()) {
  // Get current route
  const route = await GlassesAudio.getCurrentRoute();
  console.log(route.inputs, route.outputs);
  
  // Listen for changes
  const subscription = GlassesAudio.addAudioRouteChangeListener((event) => {
    console.log('Route changed:', event.route);
  });
}
```

## Testing

### Test on Physical Device (Recommended)

1. Connect your iPhone via USB
2. Build and run:
   ```bash
   npx expo run:ios --device
   ```
3. Open the app and navigate to "Glasses Diagnostics"
4. Connect Meta AI Glasses via Bluetooth
5. Observe the audio route display updates

### Test on Simulator

Note: Simulator cannot test Bluetooth, but you can verify the module loads:

```bash
npx expo run:ios
```

The diagnostics screen will show "Native iOS module - Available" if successful.

## Troubleshooting

### "Native module not available"

**Cause**: App was built with Expo Go (not a development build)

**Solution**:
```bash
# Install expo-dev-client
npm install expo-dev-client

# Rebuild with native modules
npx expo run:ios
```

### CocoaPods installation fails

**Cause**: Pod dependencies conflict

**Solution**:
```bash
cd ios
pod deintegrate
pod install
cd ..
npx expo run:ios
```

### Xcode build errors

**Cause**: Swift version mismatch or missing files

**Solution**:
1. Open `ios/*.xcworkspace` in Xcode
2. Check Build Settings → Swift Language Version (should be 5.0+)
3. Verify all `.swift` files are in the project navigator
4. Clean build folder (Cmd+Shift+K)
5. Build again (Cmd+B)

### Audio route not updating

**Cause**: Permissions not granted or AVAudioSession not configured

**Solution**:
1. Check Settings → Privacy → Microphone → Allow access
2. Check Settings → Privacy → Bluetooth → Allow access
3. Restart the app
4. Check console logs for errors

## Development Workflow

### Making Changes to Native Code

1. Edit Swift files in `modules/glasses-audio/ios/`
2. Rebuild:
   ```bash
   npx expo run:ios
   ```
3. Changes are reflected in the new build

### Adding New Native Functions

1. Add function to `GlassesAudioModule.swift`:
   ```swift
   AsyncFunction("myNewFunction") { (param: String) -> String in
     return "Result: \(param)"
   }
   ```

2. Add TypeScript definition to `index.ts`:
   ```typescript
   static async myNewFunction(param: string): Promise<string> {
     return await GlassesAudioModule.myNewFunction(param);
   }
   ```

3. Rebuild and test

### Debugging Native Code

1. Open Xcode workspace:
   ```bash
   open ios/*.xcworkspace
   ```

2. Set breakpoints in Swift files
3. Run from Xcode (Cmd+R)
4. Use Xcode debugger when breakpoints hit

## Production Considerations

### App Store Submission

Before submitting to App Store:

1. Ensure all permissions have usage descriptions in `app.json`:
   ```json
   "ios": {
     "infoPlist": {
       "NSMicrophoneUsageDescription": "...",
       "NSBluetoothPeripheralUsageDescription": "...",
       "NSBluetoothAlwaysUsageDescription": "..."
     }
   }
   ```

2. Test on physical device with Bluetooth glasses
3. Verify graceful fallback when Bluetooth unavailable
4. Check battery usage during extended audio sessions

### Performance Tips

- Stop monitoring when not needed (`stopMonitoring()`)
- Release audio resources promptly (`stopRecording()`, `stopPlayback()`)
- Handle background/foreground transitions properly

## References

- [Expo Modules API Documentation](https://docs.expo.dev/modules/overview/)
- [AVAudioSession Programming Guide](https://developer.apple.com/documentation/avfoundation/avaudiosession)
- [Meta AI Glasses Audio Routing Guide](../../../docs/meta-ai-glasses-audio-routing.md)
- [Mobile Development Setup](../../README.md)

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review console logs and Xcode build output
3. See [mobile/glasses/README.md](../../glasses/README.md) for more details
