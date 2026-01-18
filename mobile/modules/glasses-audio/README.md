# Glasses Audio Module

Native Bluetooth audio recording and playback module for React Native, designed for Meta AI Glasses integration.

## Features

- **Audio Route Monitoring**: Real-time monitoring of audio input/output routes
- **Bluetooth Detection**: Automatic detection of Bluetooth HFP/LE/A2DP devices
- **16kHz WAV Recording**: High-quality audio recording optimized for backend processing
- **Playback Control**: Full control over audio playback with progress tracking

## Installation

This module is included as a local module in the mobile app. No additional installation required.

## Usage

```javascript
import { GlassesAudio } from './modules/glasses-audio';

// Check if native module is available (iOS only)
if (GlassesAudio.isAvailable()) {
  // Start monitoring audio routes
  const subscription = await GlassesAudio.startRouteMonitoring((event) => {
    console.log('Audio route changed:', event.summary);
  });

  // Check if Bluetooth is connected
  const isConnected = await GlassesAudio.isBluetoothConnected();
  
  // Start recording (10 seconds)
  await GlassesAudio.startRecording(10.0);
  
  // Stop recording
  const result = await GlassesAudio.stopRecording();
  console.log('Recording saved:', result.fileUrl);
  
  // Play audio
  await GlassesAudio.playAudio(result.fileUrl);
  
  // Stop route monitoring
  subscription.remove();
  await GlassesAudio.stopRouteMonitoring();
}
```

## API

### Route Monitoring

- `isAvailable()`: Check if native module is available
- `startRouteMonitoring(callback)`: Start monitoring audio routes
- `stopRouteMonitoring()`: Stop monitoring
- `getCurrentRoute()`: Get current route summary
- `isBluetoothConnected()`: Check if Bluetooth device is connected
- `getDetailedRouteInfo()`: Get detailed route information

### Recording

- `startRecording(duration)`: Start recording for specified duration (seconds)
- `stopRecording()`: Stop recording and return file URL
- `isRecording()`: Check if currently recording
- `getRecordingDuration()`: Get current recording duration

### Playback

- `playAudio(fileUri)`: Play audio file
- `stopPlayback()`: Stop playback
- `pausePlayback()`: Pause playback
- `resumePlayback()`: Resume playback
- `isPlaying()`: Check if currently playing
- `getPlaybackProgress()`: Get playback progress (0.0 - 1.0)

## Platform Support

- iOS: ✅ Full support
- Android: ⏳ Coming soon

## Requirements

- iOS 13.0+
- Microphone and Bluetooth permissions

## License

MIT
