# iOS + Ray-Ban Meta MVP1 Demo Runbook

**Goal**: Demonstrate an end-to-end hands-free workflow using Ray-Ban Meta smart glasses as the audio I/O device for the iOS companion app.

**Flow**: User speaks → glasses mic → iPhone → backend → iPhone → glasses speaker

---

## Overview

This runbook describes how to run an MVP1 demo in under 5 minutes. The demo showcases:

1. **Voice command**: "show my inbox"
2. **Backend processing**: Returns inbox summary + cards
3. **TTS playback**: iOS app calls TTS endpoint and plays audio through glasses
4. **Navigation**: "next", "repeat", "summarize PR 123"

### Prerequisites

- **Hardware**: iPhone paired with Ray-Ban Meta smart glasses via Bluetooth
- **Backend**: Running locally or accessible via network with appropriate environment configuration
- **Mobile app**: iOS companion app from `mobile/` directory built as Expo dev client
- **Implementation**: Depends on PRs 033, 037, 047, 048, 049 (see [Related PRs](#related-prs))

---

## Backend Configuration

### Environment Flags

Configure the backend with these environment variables for an optimal demo experience:

#### Authentication (local dev)
```bash
HANDSFREE_AUTH_MODE=dev
```

#### Speech-to-Text (STT)
Choose one:
```bash
# Stub mode (deterministic transcript, no API key needed)
HANDS_FREE_STT_PROVIDER=stub

# OpenAI mode (realistic transcription)
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Disable STT (force text input only)
HANDSFREE_STT_ENABLED=false
```

#### Text-to-Speech (TTS)
Choose one:
```bash
# Stub mode (deterministic WAV, no API key needed)
HANDSFREE_TTS_PROVIDER=stub

# OpenAI mode (realistic voice)
HANDSFREE_TTS_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

#### GitHub Integration
```bash
# Fixture-only mode (default, no token needed)
# - No configuration required
# - Uses canned fixture data

# Live mode (real GitHub API)
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_...
```

#### Webhooks (optional)
```bash
# Dev mode accepts any signature when secret is unset
# Production should set:
GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

### API Endpoints

The MVP1 demo uses these endpoints (see `spec/openapi.yaml` for full contract):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/status` | GET | Health check, verify backend is reachable |
| `/v1/command` | POST | Submit command (text or audio URI) |
| `/v1/dev/audio` | POST | Upload audio bytes, get `file://` URI (dev-only) |
| `/v1/tts` | POST | Convert text to speech audio |
| `/v1/notifications` | GET | Poll for notifications (optional for MVP1) |

#### Example: Command Request (text)
```json
POST /v1/command
Content-Type: application/json

{
  "input": {
    "type": "text",
    "text": "show my inbox"
  },
  "context": {
    "device_id": "iphone-12345",
    "session_id": "demo-session-1"
  }
}
```

#### Example: Command Request (audio)
```json
POST /v1/command
Content-Type: application/json

{
  "input": {
    "type": "audio",
    "format": "m4a",
    "uri": "file:///tmp/audio/recording-123.m4a"
  },
  "context": {
    "device_id": "iphone-12345",
    "session_id": "demo-session-1"
  }
}
```

#### Example: Command Response
```json
{
  "status": "success",
  "intent": "inbox.summary",
  "spoken_text": "You have 3 pull requests awaiting review...",
  "cards": [
    {
      "type": "pr_summary",
      "title": "PR #123: Add new feature",
      "summary": "This PR adds...",
      "actions": ["review", "approve", "comment"]
    }
  ]
}
```

#### Example: TTS Request
```json
POST /v1/tts
Content-Type: application/json

{
  "text": "You have 3 pull requests awaiting review",
  "voice": "alloy",
  "format": "wav"
}
```

**Response**: Binary audio data (WAV/MP3/OPUS)

---

## Ray-Ban Meta Bluetooth Constraints

### Audio Routing

**Primary use case**: Treat the glasses as **Bluetooth audio output** (speaker).

**Microphone considerations**:
- Bluetooth mic input uses headset profiles (HSP/HFP)
- Can be unreliable on iOS due to profile switching and codec limitations
- May introduce latency, echo, or connection instability

### Fallback Strategy

**Recommended approach for MVP1**:
- ✅ **Use phone mic for recording** (built-in iPhone microphone)
- ✅ **Use glasses speakers for TTS playback** (Bluetooth output)

This hybrid approach maximizes reliability while still providing a hands-free listening experience.

### Known Issues
- **Route changes**: iOS may switch audio routes during calls, interruptions, or app backgrounding
- **Reconnection**: Bluetooth connection may drop and require manual reconnection
- **Latency**: Bluetooth audio has inherent latency (100-200ms typical)
- **Echo**: Feedback can occur if mic and speaker are both active over Bluetooth

### Mitigation
- Monitor audio route changes with `AVAudioSession` notifications
- Provide UI feedback when route switches (e.g., "Audio routing changed to iPhone speaker")
- Allow user to manually select audio output route
- Test with real devices (emulator Bluetooth is not representative)

---

## Demo Runbook (Step-by-Step)

### Step 0: Verify Device Setup

1. **Pair Ray-Ban Meta glasses with iPhone**
   - Settings → Bluetooth → Connect to "Ray-Ban Meta..."
   - Confirm connection status shows "Connected"

2. **Verify audio output routing**
   - Play a test sound from iOS
   - Confirm audio comes from glasses speakers (not phone speaker)
   - If not, manually select glasses as output device in Control Center

3. **Launch mobile app**
   - Open the Expo dev client app
   - Navigate to glasses diagnostics screen (if available)

### Step 1: Verify Backend Connectivity

**Test the status endpoint:**

```bash
curl http://localhost:8080/v1/status
```

**Expected response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "stt_provider": "stub",
  "tts_provider": "stub"
}
```

### Step 2: Trigger an Inbox Command

**Option A: Text Path (fastest)**

Use this approach to quickly verify the command loop without audio recording:

```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "type": "text",
      "text": "show my inbox"
    },
    "context": {
      "device_id": "iphone-demo",
      "session_id": "demo-session-1"
    }
  }'
```

**Option B: Audio Path (full demo)**

Use this approach to demonstrate the complete audio pipeline:

1. **Record audio on iOS**
   - Press and hold record button in the app
   - Say: "show my inbox"
   - Release to stop recording
   - Audio captured as WAV/M4A/MP3 (16kHz recommended)

2. **Upload audio to dev endpoint** (if using dev mode):
   ```bash
   # From iOS app code:
   const audioBase64 = await convertToBase64(recordingUri);
  const response = await fetch('http://localhost:8080/v1/dev/audio', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       data_base64: audioBase64,
       format: 'm4a'
     })
   });
   const { uri } = await response.json();
   // uri example: "file:///tmp/audio/abc123.m4a"
   ```

3. **Submit command with audio URI**:
   ```bash
  curl -X POST http://localhost:8080/v1/command \
     -H "Content-Type: application/json" \
     -d '{
       "input": {
         "type": "audio",
         "format": "m4a",
         "uri": "file:///tmp/audio/abc123.m4a"
       },
       "context": {
         "device_id": "iphone-demo",
         "session_id": "demo-session-1"
       }
     }'
   ```

**Expected response (both options)**:
```json
{
  "status": "success",
  "intent": "inbox.summary",
  "spoken_text": "You have 3 pull requests awaiting review. The first is PR 123 from Alice...",
  "cards": [
    {
      "type": "pr_summary",
      "title": "PR #123: Add new feature",
      "url": "https://github.com/org/repo/pull/123"
    }
  ]
}
```

### Step 3: Play TTS Through Glasses

1. **Extract `spoken_text` from the command response**
   ```javascript
   const { spoken_text } = commandResponse;
   ```

2. **Call TTS endpoint**
   ```bash
  curl -X POST http://localhost:8080/v1/tts \
     -H "Content-Type: application/json" \
     -d '{
       "text": "You have 3 pull requests awaiting review...",
       "voice": "alloy",
       "format": "wav"
     }' \
     --output /tmp/tts-response.wav
   ```

3. **Play audio through glasses**
   - iOS app should:
     - Configure `AVAudioSession` for Bluetooth output
     - Load TTS audio bytes
     - Play via `AVAudioPlayer` or `AVAudioEngine`
     - Verify audio routes to glasses speakers

   ```swift
   // Example iOS code (simplified)
   let session = AVAudioSession.sharedInstance()
   try session.setCategory(.playback, mode: .voiceChat, options: [.allowBluetooth])
   try session.setActive(true)
   
   let player = try AVAudioPlayer(data: ttsAudioData)
   player.play()
   ```

**Verification**:
- ✅ Audio plays through glasses speakers (not phone)
- ✅ User hears the inbox summary clearly
- ✅ No echo or feedback

### Step 4: Navigation Commands

Test the navigation intents:

**"Next" command**:
```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "type": "text",
      "text": "next"
    },
    "context": {
      "device_id": "iphone-demo",
      "session_id": "demo-session-1"
    }
  }'
```

**Expected**: Backend returns the next item in the inbox

**"Repeat" command**:
```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "type": "text",
      "text": "repeat"
    },
    "context": {
      "device_id": "iphone-demo",
      "session_id": "demo-session-1"
    }
  }'
```

**Expected**: Backend returns the same content as the previous response

### Step 5: PR Summary (Optional)

Demonstrate a specific PR query:

```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "type": "text",
      "text": "summarize PR 123"
    },
    "context": {
      "device_id": "iphone-demo",
      "session_id": "demo-session-1"
    }
  }'
```

**Expected response**:
```json
{
  "status": "success",
  "intent": "pr.summary",
  "spoken_text": "PR 123 adds a new authentication flow...",
  "cards": [
    {
      "type": "pr_detail",
      "number": 123,
      "title": "Add new authentication flow",
      "author": "alice",
      "summary": "This PR introduces..."
    }
  ]
}
```

---

## Troubleshooting

### Audio Not Routing to Glasses

**Symptoms**: TTS plays through iPhone speaker instead of glasses

**Solutions**:
1. Check Bluetooth connection in Settings
2. Manually select glasses in Control Center → Audio Output
3. Restart the iOS app
4. Toggle Bluetooth off/on
5. Re-pair the glasses

### Backend Not Responding

**Symptoms**: Connection refused or timeout errors

**Solutions**:
1. Verify backend is running: `curl http://localhost:8080/v1/status`
2. Check firewall settings if accessing over network
3. Verify correct IP address in mobile app config
4. Check backend logs for errors

### STT Not Working

**Symptoms**: Audio command returns error or empty transcript

**Solutions**:
1. Verify `HANDS_FREE_STT_PROVIDER` is set correctly
2. If using OpenAI provider, check `OPENAI_API_KEY` is valid
3. Verify audio format is supported (WAV, M4A, MP3, OPUS)
4. Check audio file is not empty or corrupted
5. Use text path as fallback during demo

### TTS Not Playing

**Symptoms**: No audio or playback error

**Solutions**:
1. Verify `HANDSFREE_TTS_PROVIDER` is configured
2. Check audio session configuration in iOS app
3. Verify TTS endpoint returns audio bytes (not error JSON)
4. Test with a simple local audio file first
5. Check iOS logs for AVAudioSession errors

---

## Related PRs

This runbook synthesizes work from multiple implementation PRs:

- **[PR-033](../tracking/PR-033-meta-ai-glasses-audio-routing.md)**: Meta AI glasses Bluetooth audio routing guide
  - Documents iOS `AVAudioSession` configuration for Bluetooth
  - Known failure modes and mitigations
  - Audio diagnostics scaffold

- **[PR-037](../tracking/PR-037-mobile-audio-capture-upload.md)**: Mobile audio capture + upload
  - Audio recorder UI implementation
  - Base64 upload to `POST /v1/dev/audio`
  - Integration with command endpoint

- **[PR-047](../tracking/PR-047-ios-audio-route-monitor.md)**: iOS audio route monitor
  - Native module for monitoring route changes
  - React Native bridge for diagnostics screen

- **[PR-048](../tracking/PR-048-ios-glasses-recorder-wav.md)**: iOS glasses Bluetooth recorder
  - 16kHz WAV recording from Bluetooth mic
  - Fallback to phone mic when Bluetooth unreliable

- **[PR-049](../tracking/PR-049-ios-glasses-player.md)**: iOS glasses Bluetooth player
  - TTS playback through glasses speakers
  - React Native bridge for playback control

---

## Additional Resources

- **OpenAPI Specification**: `spec/openapi.yaml` - Complete API contract
- **Command Grammar**: `spec/command_grammar.md` - Supported intents and patterns
- **Meta AI Glasses Guide**: `docs/meta-ai-glasses-audio-routing.md` - Detailed Bluetooth routing guide
- **Mobile Client Integration**: `docs/mobile-client-integration.md` - General mobile app setup

---

## Success Criteria

A successful MVP1 demo includes:

✅ User speaks a command  
✅ Backend processes and returns appropriate response  
✅ TTS audio plays through Ray-Ban Meta glasses  
✅ Navigation commands work (next, repeat)  
✅ Optional: PR summary query works  
✅ Fallback to phone mic when Bluetooth mic is unreliable  
✅ Clear audio output through glasses with no echo  

---

**Last updated**: 2026-01-18  
**Maintainer**: endomorphosis/lift_coding team
