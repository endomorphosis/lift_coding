# Meta AI Glasses: Bluetooth Audio Routing (iOS + Android)

This document is the implementation target for the mobile companion app’s audio session plumbing.

## What we want
- Input: Meta AI Glasses microphone -> phone app records clean audio
- Output: phone app plays TTS -> Meta AI Glasses speakers

## Notes
- This uses standard OS Bluetooth headset routing (no vendor SDK assumptions).

## TODO
- iOS: AVAudioSession category/mode/options guidance + sample code
- Android: AudioManager routing guidance + sample code
- Recommended audio format to send to backend (WAV/PCM) and conversion steps
- Debugging checklist (route display, latency, interruptions)
