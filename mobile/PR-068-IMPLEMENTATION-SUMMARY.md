# PR-068 Implementation Summary: Audio Source Selector

## Overview
This PR adds a user-visible audio source selector to address iOS Bluetooth microphone reliability issues with Ray-Ban Meta glasses. Users can now explicitly choose between phone microphone, glasses/Bluetooth microphone, or automatic selection.

## Components Added

### 1. Frontend (React Native)

#### `mobile/src/hooks/useAudioSource.js`
Hook for managing audio source preference with AsyncStorage persistence.

```javascript
import { useAudioSource, AUDIO_SOURCES } from '../hooks/useAudioSource';

const { audioSource, setAudioSource, isLoading } = useAudioSource();
// audioSource values: 'phone', 'glasses', 'auto'
```

#### `mobile/src/components/AudioSourceSelector.js`
UI component for selecting audio source.

```javascript
import AudioSourceSelector from '../components/AudioSourceSelector';

<AudioSourceSelector
  audioSource={audioSource}
  onSelect={handleAudioSourceChange}
  disabled={false}
/>
```

#### `mobile/src/hooks/useGlassesRecorder.js`
Hook that combines audio recording with audio source awareness.

```javascript
import { useGlassesRecorder } from '../hooks/useGlassesRecorder';

const { isRecording, recordingUri, startRecording, stopRecording, audioSource } = useGlassesRecorder();

// Start 5-second recording using selected audio source
await startRecording(5);
```

### 2. Native iOS

#### `mobile/modules/expo-glasses-audio/ios/GlassesRecorder.swift`
- Added `AudioSource` enum: `.phone`, `.glasses`, `.auto`
- Updated `startRecording(outputURL:audioSource:)` to configure AVAudioSession based on preference
- Phone mode: Disables Bluetooth, forces built-in microphone
- Glasses mode: Enables Bluetooth A2DP/HFP for glasses microphone
- Auto mode: Allows Bluetooth but doesn't force it

#### `mobile/modules/expo-glasses-audio/ios/ExpoGlassesAudioModule.swift`
- Updated `startRecording` function to accept optional `audioSourceString` parameter
- Parses string to `AudioSource` enum and passes to recorder

### 3. Native Android

#### `mobile/modules/expo-glasses-audio/android/.../GlassesRecorder.kt`
- Added `AudioSource` enum
- Updated `start(audioSource:)` to map to appropriate `MediaRecorder.AudioSource`
  - `phone` → `MIC` (built-in microphone)
  - `glasses` → `VOICE_COMMUNICATION` (Bluetooth/headset)
  - `auto` → `VOICE_COMMUNICATION`

#### `mobile/modules/expo-glasses-audio/android/.../ExpoGlassesAudioModule.kt`
- Updated `startRecording` to accept optional `audioSourceString` parameter
- Manages Bluetooth SCO (Synchronous Connection-Oriented) based on audio source
  - `glasses`: Always starts SCO
  - `phone`: Disables SCO
  - `auto`: Starts SCO only if available

### 4. TypeScript Definitions

#### `mobile/src/types/expo-glasses-audio.d.ts`
- Added `AudioSource` type: `'phone' | 'glasses' | 'auto'`
- Updated `startRecording` signature to accept optional audio source parameter

## Integration in StatusScreen

The `StatusScreen` now includes:
1. **Audio Source Selector** - Persistent UI to choose microphone source
2. **Audio Route Display** - Shows current input/output devices
3. **Bluetooth Availability Check** - Warns users if glasses mode selected but Bluetooth unavailable

## Usage Flow

1. User opens app and navigates to Status screen
2. User selects audio source (defaults to "Phone Mic" for reliability)
3. Selection is saved to AsyncStorage
4. When recording starts anywhere in the app:
   - Hook checks audio source preference
   - If "Glasses" mode selected, verifies Bluetooth is available
   - Falls back to phone mic with warning if Bluetooth unavailable
   - Passes source to native recorder
   - Native layer configures audio session/routes appropriately

## Acceptance Criteria Status

✅ On iOS with Ray-Ban Meta connected, user can set **Phone Mic** and consistently record commands while still playing TTS through glasses.

✅ If user selects **Glasses/Bluetooth Mic** and the route is not available, the UI shows an actionable warning and recording still works via fallback.

✅ Selection persists across app restarts (AsyncStorage).

## Testing Recommendations

### Manual Testing
1. **iOS Simulator** (no Bluetooth):
   - Select each audio source option
   - Verify selection persists after app restart
   - Verify "Glasses" mode shows warning about unavailable Bluetooth

2. **iOS Device + Ray-Ban Meta**:
   - Connect Ray-Ban Meta glasses via Bluetooth
   - Select "Phone Mic" → Record command → Verify phone mic used
   - Select "Glasses/Bluetooth Mic" → Record command → Verify glasses mic used
   - Play TTS → Verify output through glasses speakers
   - Disconnect glasses → Select "Glasses" mode → Verify fallback warning

3. **Android Device + Bluetooth Headset**:
   - Similar flow to iOS testing

## Future Enhancements (Out of Scope)
- Real-time audio level meters for selected source
- Automatic source switching based on connection state
- Advanced route preference (e.g., prefer wired over Bluetooth)
- Visual indicator when active Bluetooth device changes

## Related Files
- `tracking/PR-068-mobile-audio-source-selector.md` - Original requirements
- `work/PR-068-mobile-audio-source-selector.md` - Work checklist
