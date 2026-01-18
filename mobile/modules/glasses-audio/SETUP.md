# Glasses Audio Integration - Setup Guide

This guide walks through setting up the native glasses audio module for development and testing.

## Prerequisites

- Meta AI Glasses (Ray-Ban Meta Smart Glasses) paired with your device
- Physical iOS or Android device (simulators don't support Bluetooth audio routing)
- Xcode 14+ (for iOS)
- Android Studio (for Android)
- Node.js 18+
- Expo CLI

## Quick Start

### 1. Install Dependencies

```bash
cd mobile
npm install
```

### 2. Choose Your Path

#### Option A: Dev Mode (No Native Build Required)

Use phone mic/speaker for rapid development:

1. Run Expo dev server:
   ```bash
   npm start
   ```

2. Open in Expo Go (iOS/Android)

3. Navigate to Glasses Diagnostics screen

4. Enable "DEV Mode" toggle

5. Test recording and playback with phone audio

**Limitations**: Can't test actual glasses audio routing, but can test the full backend pipeline.

#### Option B: Native Build (Full Glasses Support)

Build native apps to test with actual glasses:

**iOS:**

```bash
# Prebuild native project
expo prebuild --platform ios

# Install pods
cd ios && pod install && cd ..

# Open in Xcode
open ios/mobile.xcworkspace
```

In Xcode:
1. Add files from `modules/glasses-audio/ios/` to project
2. Add files from `glasses/ios/` to project
3. Select your device as target
4. Build and run (Cmd+R)

**Android:**

```bash
# Prebuild native project
expo prebuild --platform android

# Open in Android Studio
studio android/
```

In Android Studio:
1. Verify all `.kt` files are included
2. Add package to `MainApplication.java`:
   ```java
   import com.glassesaudio.GlassesAudioPackage;
   
   @Override
   protected List<ReactPackage> getPackages() {
     List<ReactPackage> packages = new PackageList(this).getPackages();
     packages.add(new GlassesAudioPackage());
     return packages;
   }
   ```
3. Build and run

## Testing Workflow

### 1. Verify Module Availability

1. Open app on device
2. Navigate to Glasses Diagnostics screen
3. Check for warning banner:
   - If "Native Module Not Available" shows: Module not compiled, use DEV mode
   - If no warning: Module available, can use Glasses mode

### 2. Test in DEV Mode

1. Enable "DEV Mode" toggle
2. Status should show "✓ DEV Mode Active"
3. Audio Route: "Phone mic → Phone speaker"
4. Tap "🎤 Start Recording"
5. Speak test phrase: "Testing Meta AI Glasses integration"
6. Recording stops after 10 seconds
7. Tap "▶️ Play Last Recording"
8. Verify audio plays through phone speaker

### 3. Test Backend Pipeline

1. Record audio (DEV or Glasses mode)
2. Tap "🚀 Send to Backend & Get Response"
3. Wait for processing
4. Check response shows backend reply
5. Verify no errors

### 4. Test with Glasses (Native Build Only)

1. Pair glasses in Bluetooth settings
2. Disable "DEV Mode" toggle
3. Status should show "✓ Native module active"
4. Audio Route should show Bluetooth device name
5. Tap "🎤 Start Recording"
6. Speak into glasses microphone
7. Recording saves automatically
8. Tap "▶️ Play Last Recording"
9. Verify audio plays through glasses speakers
10. Test TTS: Send recording to backend, TTS should play through glasses

## Troubleshooting

### iOS Build Issues

**Problem**: Files not found during build

**Solution**:
1. In Xcode, right-click project → "Add Files to Project"
2. Navigate to `modules/glasses-audio/ios/` and add all `.swift` and `.m` files
3. Navigate to `glasses/ios/` and add all `.swift` files
4. Ensure "Copy items if needed" is unchecked
5. Ensure target is selected
6. Clean build folder (Cmd+Shift+K)
7. Rebuild (Cmd+B)

**Problem**: Bridging header not found

**Solution**:
1. Create/update `ios/mobile-Bridging-Header.h`:
   ```objc
   #import <React/RCTBridgeModule.h>
   #import <React/RCTEventEmitter.h>
   ```
2. In Xcode, Build Settings → Search "bridging"
3. Set "Objective-C Bridging Header" to `mobile-Bridging-Header.h`

**Problem**: Module not found at runtime

**Solution**:
1. Verify files are included in target (check checkboxes in file inspector)
2. Clean build folder
3. Delete DerivedData: `rm -rf ~/Library/Developer/Xcode/DerivedData`
4. Rebuild

### Android Build Issues

**Problem**: Package not found

**Solution**:
1. Verify package declaration in `GlassesAudioModule.kt`:
   ```kotlin
   package com.glassesaudio
   ```
2. Verify files are in correct directory: `android/app/src/main/java/com/glassesaudio/`
3. Sync Gradle files
4. Clean and rebuild

**Problem**: Duplicate class errors

**Solution**:
1. Check you don't have both source files AND compiled JARs
2. Clean build: `cd android && ./gradlew clean`
3. Rebuild

**Problem**: Module not registered

**Solution**:
1. Check `MainApplication.java` includes package in `getPackages()`
2. Verify import statement is present
3. Rebuild app

### Runtime Issues

**Problem**: `isAvailable()` returns false

**Solution**:
1. You're running in Expo Go (not supported)
2. Native build wasn't created with `expo prebuild`
3. Module files weren't included in native project
4. Rebuild from scratch

**Problem**: Permissions denied

**Solution**:
1. Check permissions in device settings
2. Uninstall and reinstall app to retrigger permission prompts
3. Verify `Info.plist` (iOS) / `AndroidManifest.xml` (Android) has correct permission keys

**Problem**: Route shows "Unknown"

**Solution**:
1. Glasses not paired - pair in Bluetooth settings
2. Glasses not powered on - charge and turn on
3. Bluetooth disabled - enable in device settings
4. Try disconnecting and reconnecting glasses

**Problem**: Recording fails

**Solution**:
1. Check microphone permission granted
2. Verify no other app using microphone
3. Check glasses are connected (for Glasses mode)
4. Try DEV mode to isolate issue
5. Check device logs for native errors

**Problem**: Playback goes to phone speaker

**Solution**:
1. Glasses may have auto-disconnected - check Bluetooth
2. Audio session may need reset - toggle airplane mode
3. Try calling someone on phone - does it route to glasses?
4. Some Android devices require SCO connection to be manually started

## Development Tips

### Rapid Iteration

For fast development without rebuilding native code:

1. Use DEV mode for all functionality testing
2. Only switch to Glasses mode when testing Bluetooth routing
3. Use Metro bundler for hot-reloading JavaScript changes
4. Native changes require full rebuild

### Debugging Native Code

**iOS:**
1. In Xcode, set breakpoints in `.swift` files
2. Run in Debug mode
3. Use Xcode console to see native logs
4. Use `print()` statements in Swift

**Android:**
1. In Android Studio, set breakpoints in `.kt` files
2. Run in Debug mode
3. Use Logcat to see native logs
4. Use `Log.d()` statements in Kotlin

### Testing Without Glasses

1. Enable DEV mode
2. All functionality works except:
   - Actual Bluetooth audio routing
   - Native audio route detection
3. Backend pipeline works the same
4. Use for development when glasses not available

## Expo Development Build

For iterative development with native modules:

1. Create development build:
   ```bash
   eas build --profile development --platform ios
   eas build --profile development --platform android
   ```

2. Install on device

3. Run dev server:
   ```bash
   expo start --dev-client
   ```

4. Native code is frozen, but JavaScript changes hot-reload

5. When native code changes, rebuild development build

## Production Build

When ready to ship:

1. Test thoroughly in development build

2. Create production builds:
   ```bash
   eas build --platform ios
   eas build --platform android
   ```

3. Test production builds before submitting to stores

4. Submit to App Store / Play Store:
   ```bash
   eas submit
   ```

## Next Steps

- Review [GlassesAudio Module README](README.md) for API documentation
- Review [Glasses Implementation TODO](../../glasses/TODO.md) for remaining work
- Test on different devices and OS versions
- Optimize audio quality settings
- Add telemetry and crash reporting
- Prepare for user testing

## Getting Help

If you encounter issues:

1. Check this guide and README.md
2. Review native iOS/Android logs
3. Test in DEV mode to isolate native vs. JS issues
4. Check Meta AI Glasses are working (make test phone call)
5. Verify permissions are granted
6. Try clean rebuild from scratch

## References

- [Expo Custom Native Code](https://docs.expo.dev/workflow/customizing/)
- [React Native Native Modules](https://reactnative.dev/docs/native-modules-intro)
- [AVAudioSession (iOS)](https://developer.apple.com/documentation/avfoundation/avaudiosession)
- [AudioManager (Android)](https://developer.android.com/reference/android/media/AudioManager)
- [Meta AI Glasses](https://www.meta.com/smart-glasses/)
