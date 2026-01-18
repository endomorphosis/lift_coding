# iOS + Ray-Ban Meta implementation queue

This document is the recommended execution order for getting to an end-to-end MVP1 demo on iOS with Ray-Ban Meta glasses as the audio device.

## Definitions
- **MVP1 demo**: speak → command → inbox summary → TTS spoken back through glasses.
- **MVP2 demo**: MVP1 + reliable fallback to phone mic when glasses mic unavailable.
- **MVP3 demo**: MVP2 + confirmation flow for side-effect commands.
- **MVP4 demo**: MVP3 + push notifications + background audio session management.

## Queue (recommended order)

### Stage 0 — Backend ready (already present)
**Status**: Foundation already in place

**Dependencies**: None (backend-only)

**Goal**:
- Ensure backend is reachable: `GET /v1/status`.
- Ensure command loop works with text: `POST /v1/command`.
- Ensure TTS endpoint returns playable audio: `POST /v1/tts`.

**Related PRs**:
- Backend API foundation (already merged)
- OpenAPI contract: `spec/openapi.yaml`

**Verification checklist**:
- [ ] `curl GET http://localhost:8000/v1/status` returns `{"status": "ok"}`
- [ ] `POST /v1/command` with `{"input": {"type": "text", "text": "inbox"}}` returns `CommandResponse` with non-empty `spoken_text`
- [ ] `POST /v1/tts` with `{"text": "hello"}` returns playable audio bytes
- [ ] Play TTS response locally on laptop with `ffplay` or similar

**Demo gate**: Backend operational ✓

---

### Stage 1 — iOS audio output to glasses (lowest risk first)
**Status**: To be implemented

**Dependencies**: 
- Backend: Stage 0
- Mobile: Expo dev client setup
- iOS: `AVAudioSession` configuration for Bluetooth output

**Goal**:
- Make sure audio output routes to the Bluetooth headset (glasses) reliably.
- Implement route monitoring to detect when glasses are connected/disconnected.

**Related PRs**:
- [tracking/PR-047-ios-audio-route-monitor.md](../tracking/PR-047-ios-audio-route-monitor.md) — iOS route monitor
- [tracking/PR-049-ios-glasses-player.md](../tracking/PR-049-ios-glasses-player.md) — iOS player
- [tracking/PR-033-meta-ai-glasses-audio-routing.md](../tracking/PR-033-meta-ai-glasses-audio-routing.md) — Bluetooth routing guidance

**Implementation steps**:
1. Implement PR-047: iOS audio route monitor with JS bridge
2. Implement PR-049: iOS glasses player with `AVAudioSession` configuration
3. Add diagnostics screen to show current audio route

**Verification checklist**:
- [ ] Physical iPhone paired with Ray-Ban Meta glasses
- [ ] Diagnostics screen shows "Bluetooth Headset" as current route
- [ ] Play a short test WAV file (embedded in app)
- [ ] Confirm audio plays through glasses speakers (not phone speaker)
- [ ] Disconnect glasses → route switches to phone speaker automatically
- [ ] Reconnect glasses → route switches back to glasses

**Demo gate**: MVP1 output ✓ (can play through glasses)

---

### Stage 2 — iOS audio capture (with fallback)
**Status**: To be implemented

**Dependencies**: 
- iOS: Stage 1 (route monitor)
- iOS: `AVAudioSession` configuration for Bluetooth input

**Goal**:
- Record audio with a best-effort preference for headset mic (glasses).
- Strong fallback to phone mic if glasses mic is unavailable.
- Save recording as 16kHz WAV format for backend compatibility.

**Related PRs**:
- [tracking/PR-048-ios-glasses-recorder-wav.md](../tracking/PR-048-ios-glasses-recorder-wav.md) — iOS recorder

**Implementation steps**:
1. Implement PR-048: iOS Bluetooth recorder with fallback logic
2. Configure `AVAudioSession` category for recording (`playAndRecord`)
3. Add record button to diagnostics screen
4. Save recording to local file system

**Verification checklist**:
- [ ] Press record button while glasses are connected
- [ ] Speak into glasses mic for 5 seconds
- [ ] Recording saves as 16kHz mono WAV file
- [ ] Play back recording through glasses → confirm it's audible
- [ ] Disconnect glasses mid-recording → recording continues via phone mic
- [ ] Export/inspect WAV file → verify format is correct (16kHz, 16-bit PCM)

**Demo gate**: MVP1 input ✓ (can capture from glasses or phone)

---

### Stage 3 — Audio upload + `/v1/command` as audio input
**Status**: To be implemented

**Dependencies**: 
- Backend: Stage 0 (dev audio endpoint)
- iOS: Stage 2 (can record audio)
- Mobile: API client for audio upload

**Goal**:
- Use the dev loop: upload base64 audio to `POST /v1/dev/audio`, then call `POST /v1/command` with an `audio` input URI.
- Complete the audio → transcription → command → response flow.

**Related PRs**:
- [tracking/PR-037-mobile-audio-capture-upload.md](../tracking/PR-037-mobile-audio-capture-upload.md) — Audio capture + upload
- [tracking/PR-029-mobile-ios-android-meta-glasses.md](../tracking/PR-029-mobile-ios-android-meta-glasses.md) — Client integration contract

**Implementation steps**:
1. Implement base64 encoding for recorded WAV
2. Add API client method for `POST /v1/dev/audio`
3. Wire audio URI into `POST /v1/command` input
4. Display command response in UI

**Verification checklist**:
- [ ] Record a voice command: "inbox"
- [ ] Upload audio bytes to `POST /v1/dev/audio` → receive `file://` URI
- [ ] Submit command: `POST /v1/command` with `{"input": {"type": "audio", "uri": "file://..."}}`
- [ ] Backend returns `CommandResponse` with transcription in logs
- [ ] If STT is stubbed, verify deterministic transcript appears
- [ ] If STT is real (OpenAI), verify accurate transcription in response

**Demo gate**: MVP1 audio input ✓ (backend understands voice commands)

---

### Stage 4 — TTS playback through glasses (end-to-end)
**Status**: To be implemented

**Dependencies**: 
- Backend: Stage 0 (TTS endpoint)
- iOS: Stage 1 (can play audio through glasses)
- Mobile: Stage 3 (can send commands and get responses)

**Goal**:
- Complete end-to-end flow: voice → command → response → TTS → glasses playback.
- Use `spoken_text` from `CommandResponse` → `POST /v1/tts` → play bytes through glasses.

**Related PRs**:
- [tracking/PR-049-ios-glasses-player.md](../tracking/PR-049-ios-glasses-player.md) — iOS player
- [tracking/PR-029-mobile-ios-android-meta-glasses.md](../tracking/PR-029-mobile-ios-android-meta-glasses.md) — Client integration contract

**Implementation steps**:
1. Extract `spoken_text` from `CommandResponse`
2. Call `POST /v1/tts` with spoken text
3. Save TTS audio bytes to temporary file
4. Play TTS audio through glasses using player from Stage 1

**Verification checklist**:
- [ ] Record voice command: "inbox"
- [ ] Submit to backend via audio upload + command
- [ ] Receive `CommandResponse` with `spoken_text` (e.g., "You have 3 new notifications...")
- [ ] Call `POST /v1/tts` with `spoken_text`
- [ ] Save TTS response bytes to file
- [ ] Play TTS file through glasses
- [ ] Confirm inbox summary is audible and intelligible through glasses
- [ ] No audio routing glitches (stays on glasses throughout)

**Demo gate**: **MVP1 complete** ✓ (full voice loop works)

---

### Stage 5 — Confirmations + safety (MVP3 readiness)
**Status**: Future work

**Dependencies**: 
- Backend: Stage 0 (confirmation endpoint exists)
- Mobile: Stage 4 (end-to-end flow works)
- Mobile: Confirmation UI (buttons + state management)

**Goal**:
- Implement the mobile UI flow for confirmation and fallback buttons.
- Handle commands that require explicit user confirmation before execution.

**Related PRs**:
- [tracking/PR-029-mobile-ios-android-meta-glasses.md](../tracking/PR-029-mobile-ios-android-meta-glasses.md) — Confirmation flow

**Verification checklist**:
- [ ] Send a side-effect command (e.g., "create a GitHub issue")
- [ ] Backend returns `needs_confirmation: true` in `CommandResponse`
- [ ] Mobile UI displays confirmation prompt with action details
- [ ] User taps "Confirm" → `POST /v1/commands/{id}/confirm`
- [ ] Backend executes action and returns success response
- [ ] User taps "Cancel" → no action taken
- [ ] Confirmation state persists across app backgrounding

**Demo gate**: **MVP3 complete** ✓ (safe side-effect commands)

---

### Stage 6 — Push notifications (MVP4 readiness)
**Status**: Future work

**Dependencies**: 
- Backend: Push notification infrastructure (APNS/FCM)
- Mobile: Push token registration
- iOS: Background audio session handling

**Goal**:
- Enable push notifications so commands can be triggered by backend events.
- Handle notification delivery while app is backgrounded or glasses session is active.

**Related PRs**:
- [tracking/PR-029-mobile-ios-android-meta-glasses.md](../tracking/PR-029-mobile-ios-android-meta-glasses.md) — Mobile integration contract (push section)
- Backend push notification PRs (separate tracking)

**Verification checklist**:
- [ ] Register APNS token with `POST /v1/notifications/subscriptions`
- [ ] Trigger test notification from backend
- [ ] Notification appears on device (banner or silent)
- [ ] App can handle notification while in background
- [ ] Audio session resumes correctly after notification

**Demo gate**: MVP4 ✓ (push-enabled voice assistant)

---

## Environment flags (backend)

These environment variables control backend behavior for development and testing.

### Speech-to-Text (STT)
- `HANDS_FREE_STT_PROVIDER=stub` — Default for dev; returns deterministic transcript
- `HANDS_FREE_STT_PROVIDER=openai` — Use OpenAI Whisper (requires `OPENAI_API_KEY`)
- `HANDS_FREE_STT_ENABLED=false` — Disable audio input path entirely (text-only mode)

### Text-to-Speech (TTS)
- `HANDS_FREE_TTS_PROVIDER=stub` — Default for dev; returns sine wave test audio
- `HANDS_FREE_TTS_PROVIDER=openai` — Use OpenAI TTS (requires `OPENAI_API_KEY`)

### GitHub integration
- `GITHUB_LIVE_MODE=true` — Enable live GitHub API calls (requires `GITHUB_TOKEN`)
- `GITHUB_TOKEN=ghp_...` — Personal access token for GitHub API

### Dev audio upload
- Dev audio endpoint `POST /v1/dev/audio` is enabled by default in development
- Audio files saved to `dev_audio_uploads/` directory

---

## MVP gate summary

| Gate | Criteria | Enables |
|------|----------|---------|
| **Backend operational** | Stage 0 complete | Foundation for all mobile work |
| **MVP1 output** | Stage 1 complete | Can play responses through glasses |
| **MVP1 input** | Stage 2 complete | Can capture voice from glasses or phone |
| **MVP1 audio input** | Stage 3 complete | Backend understands voice commands |
| **MVP1 complete** | Stage 4 complete | Full voice loop: speak → hear response |
| **MVP3 complete** | Stage 5 complete | Safe execution of side-effect commands |
| **MVP4 complete** | Stage 6 complete | Push-enabled voice assistant |

---

## Related documentation

### Tracking PRs
- [PR-029: Mobile iOS/Android + Meta Glasses](../tracking/PR-029-mobile-ios-android-meta-glasses.md) — Client integration contract
- [PR-033: Meta AI Glasses Bluetooth audio routing](../tracking/PR-033-meta-ai-glasses-audio-routing.md) — Bluetooth routing guidance
- [PR-037: Mobile audio capture + upload](../tracking/PR-037-mobile-audio-capture-upload.md) — Audio capture implementation
- [PR-047: iOS audio route monitor](../tracking/PR-047-ios-audio-route-monitor.md) — Route detection and monitoring
- [PR-048: iOS glasses recorder](../tracking/PR-048-ios-glasses-recorder-wav.md) — Audio recording implementation
- [PR-049: iOS glasses player](../tracking/PR-049-ios-glasses-player.md) — Audio playback implementation

### Implementation docs
- [docs/mobile-client-integration.md](./mobile-client-integration.md) — Mobile API integration guide
- [docs/meta-ai-glasses-audio-routing.md](./meta-ai-glasses-audio-routing.md) — Bluetooth audio routing details
- `spec/openapi.yaml` — Backend API contract

### Development tools
- `dev/` directory — Reference client scripts for testing backend integration

---

## Execution strategy

### Parallel work streams
The stages can be partially parallelized:

**Stream 1: Audio output (least risk)**
- Stage 1 → Stage 4 (player path)

**Stream 2: Audio input (higher complexity)**
- Stage 2 → Stage 3 (recorder + upload path)

**Stream 3: Backend integration**
- Stage 3 → Stage 4 (command + TTS flow)

**Convergence point**: Stage 4 (end-to-end demo) requires all three streams complete.

### Recommended first steps
1. Complete Stage 1 (audio output) — validates hardware connection
2. Complete Stage 2 (audio input) — validates recording works
3. Complete Stage 3 (audio upload) — validates backend integration
4. Complete Stage 4 (TTS playback) — validates full loop

### Testing strategy
- **Unit tests**: iOS native modules (Swift/Objective-C)
- **Integration tests**: JS bridge ↔ native module communication
- **Manual tests**: Physical device with Ray-Ban Meta glasses
- **Smoke tests**: Each stage's verification checklist

### Known risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Glasses disconnect mid-session | Recording/playback fails | Implement automatic fallback to phone mic/speaker |
| Bluetooth latency | Poor UX | Use low-latency audio session configuration |
| iOS audio session interruption | Audio stops | Handle interruptions gracefully, resume session |
| Background audio limits | App suspended | Use appropriate audio session categories |
| Expo limitations | Can't access native APIs | Use Expo dev client, not Expo Go |

---

## Success metrics

### MVP1 success criteria
- ✅ Developer can complete full voice loop in < 10 seconds
- ✅ Audio routes correctly to glasses 95%+ of the time
- ✅ Fallback to phone mic works when glasses unavailable
- ✅ TTS response is intelligible through glasses
- ✅ No manual audio routing intervention required

### MVP3 success criteria  
- ✅ All MVP1 criteria met
- ✅ Confirmation UI appears for side-effect commands
- ✅ User can approve/reject actions before execution
- ✅ Confirmation state persists across app lifecycle

### MVP4 success criteria
- ✅ All MVP3 criteria met  
- ✅ Push notifications trigger voice responses
- ✅ App handles background audio sessions correctly
- ✅ Notifications don't disrupt active audio sessions
