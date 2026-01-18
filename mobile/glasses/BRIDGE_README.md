# GlassesAudio - React Native Bridge

React Native bridge for Android glasses audio recording and playback.

## Overview

This module provides native Android functionality for recording from and playing back to Bluetooth-connected Meta AI Glasses:

- **Record audio** from glasses microphone via Bluetooth SCO
- **Play audio** through glasses speakers via Bluetooth SCO
- **Manage Bluetooth SCO** connection automatically
- **Write/Read WAV files** in 16kHz mono format suitable for STT/TTS

## Architecture

```
JavaScript (React Native)
    ↓
GlassesAudio.js (JS Bridge)
    ↓
GlassesAudioModule.kt (React Native Module)
    ↓
├── GlassesRecorder.kt (Recording)
├── GlassesPlayer.kt (Playback)
└── AudioRouteMonitor.kt (Status)
```

## Installation

### For Expo Projects

1. Eject from Expo managed workflow:
```bash
npx expo prebuild
```

2. Add the native module package to your Android app:

Edit `android/app/src/main/java/[your-package]/MainApplication.java`:

```java
import glasses.GlassesAudioPackage;

public class MainApplication extends Application implements ReactApplication {
  @Override
  protected List<ReactPackage> getPackages() {
    return Arrays.asList(
      new MainPackage(),
      new GlassesAudioPackage()  // Add this line
    );
  }
}
```

3. Copy the Kotlin files to your Android project:
```bash
cp mobile/glasses/android/*.kt android/app/src/main/java/glasses/
```

4. Add required permissions to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
```

5. Import the JavaScript module in your React Native code:
```javascript
import GlassesAudio from './glasses/GlassesAudio';
```

### For Bare React Native Projects

Follow steps 2-5 above.

## Usage

### Check Availability

```javascript
import GlassesAudio from './glasses/GlassesAudio';

if (GlassesAudio.isAvailable()) {
  console.log('GlassesAudio module is available');
}
```

### Get Audio Route

```javascript
const route = await GlassesAudio.getAudioRoute();
console.log('Current audio route:', route);
// Example output:
// Inputs:
// Ray-Ban Meta Smart Glasses (TYPE_BLUETOOTH_SCO)
// Outputs:
// Ray-Ban Meta Smart Glasses (TYPE_BLUETOOTH_SCO)
// Mode=3 SCO=true
```

### Record Audio

```javascript
try {
  // Start recording for 10 seconds
  const result = await GlassesAudio.startRecording(10000);
  console.log('Recording saved to:', result.filePath);
  
  // Or stop manually
  // await GlassesAudio.stopRecording();
} catch (error) {
  console.error('Recording failed:', error);
}
```

### Play Audio

```javascript
try {
  // Play last recording
  await GlassesAudio.playLastRecording();
  
  // Or play specific file
  // await GlassesAudio.playAudio('/path/to/file.wav');
  
  // Stop playback
  await GlassesAudio.stopPlayback();
} catch (error) {
  console.error('Playback failed:', error);
}
```

### List Recordings

```javascript
const recordings = await GlassesAudio.listRecordings();
recordings.forEach(rec => {
  console.log(`${rec.name} - ${rec.size} bytes - ${new Date(rec.timestamp)}`);
});
```

### Full Example

```javascript
import React, { useState } from 'react';
import { View, Button, Text } from 'react-native';
import GlassesAudio from './glasses/GlassesAudio';

export default function GlassesTest() {
  const [status, setStatus] = useState('Ready');
  const [recording, setRecording] = useState(false);
  const [playing, setPlaying] = useState(false);

  const handleRecord = async () => {
    try {
      setStatus('Recording...');
      setRecording(true);
      
      const result = await GlassesAudio.startRecording(10000);
      
      setRecording(false);
      setStatus(`Recorded: ${result.filePath}`);
    } catch (error) {
      setRecording(false);
      setStatus(`Error: ${error.message}`);
    }
  };

  const handlePlay = async () => {
    try {
      setStatus('Playing...');
      setPlaying(true);
      
      await GlassesAudio.playLastRecording();
      
      setPlaying(false);
      setStatus('Playback complete');
    } catch (error) {
      setPlaying(false);
      setStatus(`Error: ${error.message}`);
    }
  };

  const handleStop = async () => {
    if (recording) {
      await GlassesAudio.stopRecording();
      setRecording(false);
    }
    if (playing) {
      await GlassesAudio.stopPlayback();
      setPlaying(false);
    }
    setStatus('Stopped');
  };

  return (
    <View style={{ padding: 20 }}>
      <Text>{status}</Text>
      <Button 
        title={recording ? 'Recording...' : 'Record (10s)'} 
        onPress={handleRecord}
        disabled={recording || playing}
      />
      <Button 
        title={playing ? 'Playing...' : 'Play Last'} 
        onPress={handlePlay}
        disabled={recording || playing}
      />
      <Button 
        title="Stop" 
        onPress={handleStop}
        disabled={!recording && !playing}
      />
    </View>
  );
}
```

## API Reference

### `isAvailable()`
Check if the native module is available (Android only).
- **Returns:** `boolean`

### `getAudioRoute()`
Get current audio route information.
- **Returns:** `Promise<string>` - Audio route description

### `startRecording(durationMs)`
Start recording audio to a WAV file.
- **Parameters:**
  - `durationMs` (number, optional): Recording duration in milliseconds. Default: 10000. Use 0 for unlimited.
- **Returns:** `Promise<{filePath: string, duration: number}>`

### `stopRecording()`
Stop the current recording.
- **Returns:** `Promise<void>`

### `isRecording()`
Check if currently recording.
- **Returns:** `Promise<boolean>`

### `playAudio(filePath)`
Play audio from a WAV file.
- **Parameters:**
  - `filePath` (string): Path to WAV file
- **Returns:** `Promise<void>`

### `playLastRecording()`
Play the last recorded audio.
- **Returns:** `Promise<void>`

### `stopPlayback()`
Stop audio playback.
- **Returns:** `Promise<void>`

### `pausePlayback()`
Pause audio playback.
- **Returns:** `Promise<void>`

### `resumePlayback()`
Resume audio playback.
- **Returns:** `Promise<void>`

### `isPlaying()`
Check if currently playing.
- **Returns:** `Promise<boolean>`

### `getLastRecordingPath()`
Get the file path of the last recording.
- **Returns:** `Promise<string|null>`

### `listRecordings()`
List all recording files.
- **Returns:** `Promise<Array<{path: string, name: string, size: number, timestamp: number}>>`

### `deleteRecording(filePath)`
Delete a recording file.
- **Parameters:**
  - `filePath` (string): Path to recording file
- **Returns:** `Promise<boolean>`

## Technical Details

### Audio Format
- **Sample Rate:** 16 kHz
- **Bit Depth:** 16-bit
- **Channels:** Mono
- **Container:** WAV with proper headers
- **Audio Source:** VOICE_COMMUNICATION (for Bluetooth SCO)

### Bluetooth SCO
The module automatically manages Bluetooth SCO (Synchronous Connection Oriented) connections:
- Starts SCO when recording/playback begins
- Stops SCO when recording/playback ends
- Monitors SCO connection state
- Handles connection/disconnection gracefully

### File Storage
Recordings are saved to: `[External Files Dir]/Music/audio_diagnostics/`

Files are named: `glasses_recording_YYYYMMDD_HHMMSS.wav`

### Permissions
Required Android permissions:
- `RECORD_AUDIO` - For microphone access
- `BLUETOOTH_CONNECT` - For Bluetooth device connection (Android 12+)
- `MODIFY_AUDIO_SETTINGS` - For audio routing control

## Troubleshooting

### "No Bluetooth device detected"
- Ensure glasses are paired in Android Bluetooth settings
- Check glasses are powered on and in range
- Try disconnecting and reconnecting in Settings

### "Recording fails to start"
- Check microphone permissions are granted
- Verify Bluetooth connection is active
- Ensure no other app is using the microphone

### "Playback goes to phone speaker"
- Verify Bluetooth connection
- Check audio route with `getAudioRoute()`
- Restart the app

### "Module not found"
- Ensure you've ejected from Expo managed workflow
- Verify Kotlin files are in correct location
- Check `GlassesAudioPackage` is added to `MainApplication`
- Rebuild the Android app

## Testing

### Prerequisites
1. Physical Android device (Android 8.0+)
2. Meta AI Glasses paired via Bluetooth
3. Microphone and Bluetooth permissions granted

### Test Steps
1. Launch app on physical device
2. Navigate to glasses diagnostics screen
3. Check audio route shows Bluetooth connection
4. Tap "Record" and speak into glasses mic
5. Tap "Play" to hear playback through glasses speakers
6. Verify WAV file is valid (use `listRecordings()`)

## References
- [Android AudioRecord Documentation](https://developer.android.com/reference/android/media/AudioRecord)
- [Android AudioTrack Documentation](https://developer.android.com/reference/android/media/AudioTrack)
- [Android AudioManager Documentation](https://developer.android.com/reference/android/media/AudioManager)
- [React Native Native Modules](https://reactnative.dev/docs/native-modules-android)
- [Meta AI Glasses Audio Routing](../../docs/meta-ai-glasses-audio-routing.md)
