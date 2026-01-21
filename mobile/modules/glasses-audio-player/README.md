# Glasses Audio Player Module

> **⚠️ DEPRECATED**: This module has been superseded by [`expo-glasses-audio`](../expo-glasses-audio/). 
> 
> Please use `expo-glasses-audio` instead, which provides:
> - Cross-platform support (iOS + Android)
> - Recording + playback capabilities
> - Audio route monitoring
> - Better error handling and graceful fallbacks
>
> **Migration:** Update your imports from:
> ```typescript
> import { playAudio } from '../../modules/glasses-audio-player';
> ```
> to:
> ```typescript
> import ExpoGlassesAudio from 'expo-glasses-audio';
> await ExpoGlassesAudio.playAudio(fileUri);
> ```
> 
> See the [expo-glasses-audio README](../expo-glasses-audio/README.md) for full documentation.

---

## Legacy Documentation

Native iOS module for playing audio through Meta AI Glasses via Bluetooth.

## Features

- Plays audio files through Bluetooth-connected Meta AI Glasses
- Configures AVAudioSession for proper Bluetooth routing
- Supports WAV and other audio formats supported by AVAudioEngine

## Installation

This module is included in the mobile app and doesn't need separate installation.

## Usage

```typescript
import { playAudio, stopAudio, isPlaying } from './modules/glasses-audio-player';

// Play an audio file
await playAudio('file:///path/to/audio.wav');

// Check if playing
const playing = await isPlaying();

// Stop playback
await stopAudio();
```

## iOS Configuration

The module automatically configures AVAudioSession with:
- Category: `.playAndRecord`
- Mode: `.voiceChat`
- Options: `.allowBluetooth`, `.allowBluetoothA2DP`

This ensures audio routes to Bluetooth devices (Meta AI Glasses) when available.

## Requirements

- iOS 13.0+
- Expo SDK 50+
- Physical iOS device with Bluetooth capability
- Meta AI Glasses paired via Bluetooth

## Implementation Details

The module uses:
- `AVAudioEngine` for audio playback
- `AVAudioPlayerNode` for file scheduling
- `AVAudioSession` for Bluetooth routing configuration

## Testing

This module requires:
1. An Expo development build (not Expo Go)
2. A physical iPhone (Bluetooth doesn't work in simulator)
3. Meta AI Glasses paired via Bluetooth

To test:
```bash
# Create development build
expo prebuild
expo run:ios --device

# Or build with EAS
eas build --profile development --platform ios
```
