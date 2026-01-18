# iOS + Ray-Ban Meta Troubleshooting Guide

**Purpose**: Fast recovery during live demos when Bluetooth audio routing fails.

---

## 🚨 Emergency Quick Fix (30 seconds)

```
Problem? → Try this first:
1. Check Bluetooth connected (Settings → Bluetooth → Ray-Ban Meta)
2. Restart the app
3. If still broken → use phone mic + glasses speakers
4. Continue demo (fix input routing later)
```

---

## Decision Flowchart: "If It Breaks, Do This"

```
┌─────────────────────────┐
│ Audio not working?      │
└───────────┬─────────────┘
            │
            ▼
    ┌───────────────┐
    │ Glasses paired│
    │ in Bluetooth? │
    └───┬───────┬───┘
       NO      YES
        │       │
        ▼       ▼
    ┌─────┐ ┌──────────────┐
    │PAIR │ │ Output plays │
    │THEM │ │ on glasses?  │
    └─────┘ └───┬──────┬───┘
               NO     YES
                │      │
                ▼      ▼
          ┌──────────┐ ┌────────────┐
          │1. Restart│ │ Mic input  │
          │   app    │ │ working?   │
          │2. Toggle │ └──┬─────┬───┘
          │   BT off/│   NO    YES
          │   on     │    │     │
          │3. Force  │    ▼     ▼
          │   speaker│ ┌─────┐ ┌─────┐
          │   →BT in │ │USE  │ │DEMO │
          │   app    │ │PHONE│ │READY│
          └──────────┘ │MIC  │ └─────┘
                       └─────┘
```

**Key principle**: Never block a demo on mic input. Output to glasses is critical; mic fallback is acceptable.

---

## Common Failure Modes

### 1. Output plays on speaker, not glasses

**Symptoms**: Audio plays from phone speaker instead of glasses.

**Quick fixes** (try in order):
1. **Restart the app** - resets AVAudioSession
2. **Toggle Bluetooth** - Settings → Bluetooth → off/on
3. **Force route in app** - use `MPVolumeView` route picker or manual override
4. **Check connection** - may be paired but not connected

**Root causes**:
- AVAudioSession not configured with `.allowBluetooth` option
- Another app claimed Bluetooth audio (phone call, music app)
- iOS automatically routed to speaker after interruption

**Prevention**:
```swift
// Known-good AVAudioSession configuration
try audioSession.setCategory(
    .playAndRecord,
    mode: .voiceChat,
    options: [.allowBluetooth, .defaultToSpeaker]
)
try audioSession.setActive(true)
```

See: `docs/meta-ai-glasses-audio-routing.md` §iOS Implementation

---

### 2. No headset mic input (or very low quality)

**Symptoms**: 
- Recording is silent
- Mic input is scratchy/low volume
- HFP mic not showing as available input

**Quick fixes**:
1. **Accept the limitation** - use phone mic, keep glasses for output
2. **Check available inputs**:
   ```swift
   let inputs = AVAudioSession.sharedInstance().availableInputs
   // Look for .bluetoothHFP
   ```
3. **Restart Bluetooth** - may need to re-establish HFP profile
4. **Check glasses mic isn't muted** - hardware button on some models

**Root causes**:
- HFP (Hands-Free Profile) not established - only A2DP connected
- iOS prefers phone mic for quality (intentional)
- Glasses mic is lower quality than phone mic (expected)

**Fallback policy for demos**:
```
✅ DO:   Phone mic → backend → glasses output
❌ DON'T: Block demo waiting for glasses mic
```

---

### 3. Route changes mid-session

**Symptoms**: 
- Audio switches to speaker during demo
- Recording stops unexpectedly
- App loses audio focus

**Causes**:
- **Phone call** - interruption + route override
- **Siri invocation** - interruption
- **Notification sound** - may trigger route change
- **Background/foreground** - iOS may deactivate session

**Recovery**:
1. **Handle interruptions gracefully**:
   ```swift
   NotificationCenter.default.addObserver(
       forName: AVAudioSession.interruptionNotification,
       ...
   )
   ```
2. **Reactivate session after interruption ends**
3. **Display status to user** - "Call ended, reconnecting audio..."

**Prevention**:
- Enable background audio mode (Info.plist → `audio` capability)
- Implement interruption handlers (see PR-047)
- Save recording state to resume after interruption

See: `tracking/PR-047-ios-audio-route-monitor.md`

---

### 4. Backend rejects audio input

**Symptoms**:
- 400 or 422 error from `POST /v1/command`
- Error: "Unsupported audio format"

**Quick fixes**:
1. **Verify format** - must be one of: `wav`, `m4a`, `mp3`, `opus`
2. **Use dev endpoint for testing**:
   ```
   POST /v1/dev/audio
   Body: { "audio_base64": "...", "format": "wav" }
   Returns: { "audio_uri": "file://..." }
   ```
3. **Check WAV header** - if using raw PCM, ensure proper WAV wrapper

**Known-good format** (for recording):
- **Container**: WAV
- **Codec**: Linear PCM (uncompressed)
- **Sample rate**: 16 kHz
- **Bit depth**: 16-bit
- **Channels**: Mono

See: `docs/meta-ai-glasses-audio-routing.md` §Audio Format Recommendations

---

### 5. Sample rate / format mismatch

**Symptoms**:
- Recording sounds too fast/slow on playback
- Backend transcription is garbled
- Format errors in backend logs

**Fixes**:
1. **Set explicit sample rate**:
   ```swift
   try audioSession.setPreferredSampleRate(16000.0)
   ```
2. **Match recording and playback rates** - both should be 16 kHz
3. **Verify WAV header** - sample rate field must match actual data

**Debug checklist**:
- [ ] AVAudioSession preferred sample rate = 16000
- [ ] AVAudioEngine input format = 16000 Hz
- [ ] WAV file header sample rate field = 16000
- [ ] Backend expects 16000 Hz (or transcoder handles conversion)

---

## Known-Good Configuration

### AVAudioSession Setup (iOS)

```swift
import AVFoundation

func configureAudioForGlasses() throws {
    let session = AVAudioSession.sharedInstance()
    
    // 1. Set category and options
    try session.setCategory(
        .playAndRecord,              // Bidirectional audio
        mode: .voiceChat,            // Optimized for voice, enables AEC
        options: [
            .allowBluetooth,         // Enable BT routing
            .defaultToSpeaker        // Fallback if BT unavailable
        ]
    )
    
    // 2. Set preferred sample rate
    try session.setPreferredSampleRate(16000.0)
    
    // 3. Prefer Bluetooth input if available
    if let btInput = session.availableInputs?.first(where: { 
        $0.portType == .bluetoothHFP 
    }) {
        try session.setPreferredInput(btInput)
    }
    
    // 4. Activate session
    try session.setActive(true)
    
    // 5. Verify route
    print("Current route: \(session.currentRoute)")
}
```

**Critical options**:
- **Category**: `.playAndRecord` (not `.playback` - need mic input)
- **Mode**: `.voiceChat` (enables hardware echo cancellation, optimizes for voice)
- **Options**: `.allowBluetooth` (mandatory for BT routing)

**Common mistakes**:
- ❌ Using `.playback` category - no mic input
- ❌ Omitting `.allowBluetooth` - forces speaker/receiver
- ❌ Not activating session - configuration has no effect

See full implementation: `docs/meta-ai-glasses-audio-routing.md` (lines 22-51)

---

## On-Device Diagnostics Checklist

**Display these values in-app for rapid debugging:**

### Audio Routing
```
[ ] Current output route: _____________ (expect: "Bluetooth HFP")
[ ] Current input source: _____________ (expect: "Bluetooth HFP" or "Built-in Mic")
[ ] Available inputs: _________________ (should include Bluetooth if connected)
[ ] Route change count: ______________ (increments = instability)
```

### Audio Format
```
[ ] Sample rate: _____ Hz (expect: 16000)
[ ] Channels: ________ (expect: 1 = mono)
[ ] Bit depth: _______ (expect: 16)
[ ] Format: __________ (expect: lpcm or wav)
```

### Last Recording
```
[ ] Duration: ________ seconds
[ ] File size: _______ KB (rough check: 16kHz × 16bit × 1ch = 32KB/sec)
[ ] Upload status: ___ (200 OK / error code)
```

### Last Playback
```
[ ] Backend response time: _____ ms
[ ] TTS audio received: _________ KB
[ ] Playback route: _____________ (expect: "Bluetooth HFP")
[ ] Playback error: _____________ (if any)
```

### Connectivity
```
[ ] Bluetooth status: _____________ (connected / paired / disconnected)
[ ] Glasses device name: __________ (e.g., "Ray-Ban Meta")
[ ] Last route change reason: _____ (e.g., "newDeviceAvailable", "oldDeviceUnavailable")
```

**Minimal diagnostic screen** - implement in `mobile/glasses/` diagnostics view:
1. Display all checklist values above
2. Button: "Test Recording" (record 3 sec, show waveform, play back)
3. Button: "Test Playback" (play test tone through glasses)
4. Button: "Refresh Route Info" (query AVAudioSession)
5. Button: "Force Bluetooth Route" (override route picker)

See scaffold: `mobile/glasses/README.md` (from PR-033)

---

## Pre-Demo Checklist (5 minutes)

**Before every demo, verify:**

1. **Pairing**
   - [ ] Glasses paired in Settings → Bluetooth
   - [ ] Glasses show "Connected" (not just "Paired")
   - [ ] No other BT audio devices connected (AirPods, car, etc.)

2. **App Configuration**
   - [ ] App has Bluetooth permission (Settings → App → Bluetooth)
   - [ ] App has Microphone permission
   - [ ] Background audio mode enabled (if needed)

3. **Audio Route**
   - [ ] Open app diagnostics screen
   - [ ] Confirm output route = "Bluetooth HFP"
   - [ ] Run "Test Playback" - hear tone in glasses
   - [ ] Run "Test Recording" - see waveform, hear playback

4. **Backend Connection**
   - [ ] App can reach backend API
   - [ ] Test TTS request: POST /v1/tts { "text": "test" }
   - [ ] Receive and play audio response

5. **Fallback Plan**
   - [ ] If glasses fail, switch to phone speaker mode
   - [ ] Keep a backup device with known-good setup

**Time budget**:
- Pairing check: 1 min
- Route verification: 2 min
- Test recording/playback: 2 min

---

## References

### Related Implementation Docs
- **Audio Routing Guide**: `docs/meta-ai-glasses-audio-routing.md`  
  Comprehensive iOS + Android Bluetooth audio implementation
  
- **PR-033**: `tracking/PR-033-meta-ai-glasses-audio-routing.md`  
  Original audio routing prototype and integration guide

### Related Implementation PRs
- **PR-047**: iOS audio route monitor - observes route changes and interruptions
- **PR-048**: iOS glasses recorder (WAV format) - records from glasses mic
- **PR-049**: iOS glasses player - plays TTS through glasses
- **PR-050**: Android audio route monitor
- **PR-051**: Android glasses recorder/player
- **PR-052**: Glasses JS integration + TTS wiring

### API Contracts
- **OpenAPI Spec**: `spec/openapi.yaml`  
  - `POST /v1/command` - upload audio for transcription
  - `POST /v1/tts` - generate TTS audio
  - `POST /v1/dev/audio` - dev endpoint for base64 audio upload

### Additional Resources
- **Apple AVAudioSession**: https://developer.apple.com/documentation/avfaudio/avaudiosession
- **Apple Audio Interruptions**: https://developer.apple.com/documentation/avfaudio/avaudiosession/responding_to_audio_session_interruptions
- **Bluetooth HFP Spec**: Hands-Free Profile 1.8 (for reference)

---

## Appendix: Common Error Messages

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `AVAudioSessionErrorCodeCannotStartPlaying` | Session not activated | Call `setActive(true)` |
| `AVAudioSessionErrorCodeCannotStartRecording` | No mic permission | Request permission |
| `The operation couldn't be completed. (com.apple.coreaudio.avfaudio error -50)` | Invalid audio format | Check sample rate, channels, bit depth |
| Backend: `422 Unsupported format` | Audio not in wav/m4a/mp3/opus | Convert to supported format |
| Backend: `400 Invalid audio_uri` | Malformed URI or missing file | Check URI format and file exists |
| `Bluetooth device not available` | Glasses not connected | Reconnect in Settings → Bluetooth |

---

## Quick Command Reference (Debug Console)

**Query current route**:
```swift
print(AVAudioSession.sharedInstance().currentRoute)
```

**List available inputs**:
```swift
AVAudioSession.sharedInstance().availableInputs?.forEach { 
    print("\($0.portName): \($0.portType)")
}
```

**Force speaker route** (for comparison):
```swift
try AVAudioSession.sharedInstance().overrideOutputAudioPort(.speaker)
```

**Get Bluetooth device name**:
```swift
let btOutput = AVAudioSession.sharedInstance().currentRoute.outputs.first {
    $0.portType == .bluetoothHFP || $0.portType == .bluetoothA2DP
}
print(btOutput?.portName ?? "No BT device")
```

---

**Last updated**: 2026-01-18  
**Maintained by**: Lift Coding Team  
**Feedback**: Create issue in `endomorphosis/lift_coding`
