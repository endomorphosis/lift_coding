# PR-025: Mobile/wearable client work tracking (docs-only)

## Goal
Capture the MVP mobile + wearable deliverables as a concrete checklist and define the integration points to the backend.

## Target Platforms for First Demo
The first demo will target:
- **iOS** (iPhone) as the primary mobile platform
- **Meta AI glasses** (Ray-Ban Meta Smart Glasses) as the wearable device

This combination provides:
- iOS ecosystem integration (APNS, iOS Speech framework, iOS audio session management)
- Meta AI glasses for hands-free audio capture and playback via Bluetooth
- Proven Bluetooth audio pipeline (Meta glasses ↔ iPhone)
- Growing developer ecosystem for Meta AI glasses

## Background
The backend is largely MVP-ready, but the plan requires a mobile/wearable client to:
- capture audio (wearable → phone)
- call `/v1/command` (audio/text)
- play TTS responses
- receive push notifications and speak summaries

This repo does not currently contain the mobile client implementation.

## Scope (docs-only in this repo)
- Create a clear checklist of mobile/wearable features:
  - wearable audio capture → phone bridge (Meta AI glasses → iPhone via Bluetooth)
  - push-to-talk UX and error handling
  - STT routing decision (on-device vs backend)
  - TTS playback (phone + wearable)
  - push notification receive + speak
  - dev-mode features (transcript/debug panel, replay fixtures)
- Document API contracts used:
  - `POST /v1/command`
  - `POST /v1/commands/confirm`
  - `GET /v1/status`
  - push registration endpoint(s) (from PR-024)
- Recommend repo/project separation (new mobile workspace) and CI strategy.
- Define Meta AI glasses integration approach (Bluetooth audio, Meta SDK if available)

## Non-goals
- Implementing the mobile app in this repo.

## Acceptance criteria
- Tracking doc exists with a shippable checklist and clear API integration points.
- Identifies dependencies on backend PRs (notably PR-024 for push registration).

---

## MVP Feature Checklist

### 1. Wearable Audio Capture & Phone Bridge
- [ ] **Meta AI Glasses → iPhone Audio Transfer**
  - [ ] Configure iOS app to receive Bluetooth audio from Meta AI glasses
  - [ ] Implement audio session management for Bluetooth input
  - [ ] Handle audio buffering and format conversion
  - [ ] Add fallback for connection issues or audio quality degradation
  - [ ] Test with Ray-Ban Meta Smart Glasses

- [ ] **Apple Watch → iPhone Audio Transfer** (Alternative/Future)
  - [ ] Configure Apple Watch audio session for recording
  - [ ] Implement WatchConnectivity bridge to transfer audio data to iPhone
  - [ ] Handle audio buffering and compression for efficient transfer
  - [ ] Add fallback for when phone is not reachable

- [ ] **Audio Format & Quality**
  - [ ] Support WAV format (`.wav`) for backend compatibility
  - [ ] Support MP3 format (`.mp3`) as alternative
  - [ ] Implement configurable quality settings (bitrate, sample rate)
  - [ ] Add audio duration tracking for UX feedback

### 2. Push-to-Talk UX & Error Handling
- [ ] **Recording Interface**
  - [ ] Push-to-talk trigger via Meta AI glasses button (capture event from glasses)
  - [ ] iPhone app button as backup/alternative trigger
  - [ ] Visual feedback in app (recording indicator)
  - [ ] Audio waveform visualization during recording
  - [ ] Recording duration counter
  - [ ] Haptic feedback on iPhone for start/stop confirmation

- [ ] **Error States**
  - [ ] Handle microphone permission denied
  - [ ] Handle Meta AI glasses Bluetooth disconnection
  - [ ] Handle no network connectivity (queue for retry)
  - [ ] Handle audio capture failures
  - [ ] Display user-friendly error messages
  - [ ] Implement retry logic with exponential backoff
  - [ ] Provide audio quality warnings for poor Bluetooth connection

- [ ] **UX Polish**
  - [ ] Loading states while processing command
  - [ ] Success/failure visual feedback
  - [ ] Cancel recording capability
  - [ ] Audio playback preview before sending (optional)

### 3. STT Routing Decision
- [ ] **Backend STT (Primary)**
  - [ ] Send audio to backend `/v1/command` endpoint
  - [ ] Backend transcribes using configured STT provider
  - [ ] Display transcript in debug panel

- [ ] **On-Device STT (Optional)**
  - [ ] Implement iOS Speech framework integration
  - [ ] Use on-device STT for immediate feedback
  - [ ] Send text instead of audio to backend when available
  - [ ] Add toggle in settings for STT preference

- [ ] **Hybrid Approach**
  - [ ] Use on-device STT for instant transcript preview
  - [ ] Send audio to backend for authoritative processing
  - [ ] Compare on-device vs backend transcripts (dev mode)

### 4. Command Processing Integration
- [ ] **POST /v1/command Implementation**
  - [ ] Send audio input with proper format metadata
  - [ ] Send text input for text-based commands
  - [ ] Include required headers (X-Session-Id, X-Request-ID)
  - [ ] Handle idempotency keys for retry safety
  - [ ] Parse CommandResponse model

- [ ] **Request Configuration**
  - [ ] Set user profile (commute/focused/relaxed)
  - [ ] Set privacy mode (strict/balanced/debug)
  - [ ] Set device context (device type, locale)
  - [ ] Generate session IDs for conversation continuity

- [ ] **Response Handling**
  - [ ] Parse spoken_text for TTS playback
  - [ ] Render UICard components in app
  - [ ] Handle pending_action confirmations
  - [ ] Display debug info in dev panel

### 5. TTS Playback (Phone + Wearable)
- [ ] **Meta AI Glasses TTS Playback** (Primary)
  - [ ] Call `/v1/tts` with spoken text from response
  - [ ] Play audio response through Meta AI glasses speakers via Bluetooth
  - [ ] Handle Bluetooth audio routing and connection issues
  - [ ] Provide fallback to iPhone speaker if glasses disconnected
  - [ ] Add playback controls (pause, replay via app if glasses don't support)

- [ ] **iPhone TTS Playback** (Backup/Alternative)
  - [ ] Call `/v1/tts` with spoken text from response
  - [ ] Play audio response through iPhone speaker
  - [ ] Add playback controls (pause, replay, speed adjust)
  - [ ] Handle TTS errors gracefully

- [ ] **Apple Watch TTS Playback** (Future)
  - [ ] Transfer TTS audio to Apple Watch
  - [ ] Play audio through watch speaker
  - [ ] Sync playback state between phone and watch
  - [ ] Add watch-specific playback controls

- [ ] **Audio Session Management**
  - [ ] Configure audio session for playback
  - [ ] Handle interruptions (calls, other apps)
  - [ ] Implement ducking for notifications
  - [ ] Resume playback after interruption

### 6. Push Notification Receive & Speak
- [ ] **Push Registration (PR-024 Dependency)**
  - [ ] Register device with backend push endpoint
  - [ ] Store push token and platform (APNS for iOS)
  - [ ] Handle token refresh and re-registration
  - [ ] Unregister on logout/app deletion

- [ ] **Notification Reception**
  - [ ] Receive APNS notifications from backend
  - [ ] Parse notification payload (event_type, message, metadata)
  - [ ] Display notification banner/alert
  - [ ] Handle foreground vs background states

- [ ] **Speak Notification Summaries**
  - [ ] Generate spoken summary from notification message
  - [ ] Use TTS to speak notification (optional/configurable)
  - [ ] Respect do-not-disturb and quiet hours
  - [ ] Add notification history view

- [ ] **Notification Actions**
  - [ ] Tap to open relevant app screen (deep linking)
  - [ ] Quick actions from notification (mark as read, reply)
  - [ ] Badge count management

### 7. Confirmation Flow (POST /v1/commands/confirm)
- [ ] **Pending Action UI**
  - [ ] Display confirmation prompt for side-effect actions
  - [ ] Show action summary and consequences
  - [ ] Provide clear confirm/cancel buttons
  - [ ] Handle token expiration gracefully

- [ ] **Confirmation Submission**
  - [ ] Send pending_action token to `/v1/commands/confirm`
  - [ ] Display confirmation result
  - [ ] Update UI based on action result
  - [ ] Handle idempotency for retries

### 8. Dev-Mode Features
- [ ] **Transcript/Debug Panel**
  - [ ] Display raw transcript from STT
  - [ ] Show parsed intent and entities
  - [ ] Display full request/response JSON
  - [ ] Show API latency and timing info
  - [ ] View conversation history

- [ ] **Replay Fixtures**
  - [ ] Load pre-recorded audio samples
  - [ ] Load pre-defined command fixtures
  - [ ] Replay commands with fixed responses
  - [ ] Compare fixture vs live backend responses

- [ ] **Developer Settings**
  - [ ] Toggle between dev/staging/production backends
  - [ ] Configure mock responses for offline testing
  - [ ] Enable verbose logging
  - [ ] Export logs and debug data

### 9. Service Status Monitoring
- [ ] **GET /v1/status Implementation**
  - [ ] Poll status endpoint on app startup
  - [ ] Display service health in settings
  - [ ] Show dependency status (DuckDB, Redis, etc.)
  - [ ] Warn user if service degraded

- [ ] **Network Monitoring**
  - [ ] Detect network connectivity changes
  - [ ] Show offline indicator
  - [ ] Queue commands when offline
  - [ ] Auto-retry when connection restored

### 10. Authentication & Security
- [ ] **API Key Authentication**
  - [ ] Create API key via `/v1/admin/api-keys`
  - [ ] Securely store API key in iOS Keychain
  - [ ] Include Authorization header in all requests
  - [ ] Handle 401/403 errors and prompt re-auth

- [ ] **GitHub OAuth Flow (PR-023 Dependency)**
  - [ ] Implement OAuth login flow
  - [ ] Store GitHub token for live mode features
  - [ ] Refresh token when expired
  - [ ] Logout and token revocation

### 11. Navigation & UI
- [ ] **Main Screens**
  - [ ] Home screen with push-to-talk button
  - [ ] Inbox view (recent notifications and items)
  - [ ] Conversation history
  - [ ] Settings/preferences screen

- [ ] **UICard Rendering**
  - [ ] Render title, subtitle, lines
  - [ ] Handle deep_link navigation
  - [ ] Support multiple card types
  - [ ] Implement card actions (tap, long-press)

- [ ] **Accessibility**
  - [ ] VoiceOver support for all UI elements
  - [ ] Dynamic type support
  - [ ] High contrast mode
  - [ ] Haptic feedback for key actions

### 12. Testing & Quality
- [ ] **Unit Tests**
  - [ ] Test audio capture and encoding
  - [ ] Test API request/response parsing
  - [ ] Test TTS playback logic
  - [ ] Test notification handling

- [ ] **Integration Tests**
  - [ ] Test end-to-end command flow (record → send → receive → play)
  - [ ] Test push notification delivery
  - [ ] Test confirmation flow
  - [ ] Test offline/retry scenarios

- [ ] **UI Tests**
  - [ ] Test push-to-talk interaction
  - [ ] Test recording cancellation
  - [ ] Test notification tap actions
  - [ ] Test settings changes

---

## Meta AI Glasses Integration Details

### Hardware: Ray-Ban Meta Smart Glasses

The first demo targets Ray-Ban Meta Smart Glasses, which provide:
- **Microphones**: Built-in mics for voice capture
- **Speakers**: Open-ear speakers for audio playback
- **Button**: Physical button for triggering actions
- **Bluetooth**: Standard Bluetooth connectivity to iPhone
- **Battery**: Independent power source

### Integration Architecture

**Audio Capture Flow**:
1. User presses button on Meta AI glasses
2. Glasses capture audio via built-in microphones
3. Audio streams to iPhone via Bluetooth (standard Bluetooth audio profile)
4. iPhone app receives audio and sends to backend `/v1/command`
5. Backend processes and returns response

**Audio Playback Flow**:
1. Backend returns `spoken_text` in response
2. iPhone app calls `/v1/tts` to get audio
3. Audio plays through Meta AI glasses speakers via Bluetooth
4. User hears response through glasses

### Meta SDK/API Considerations

**Option 1: Standard Bluetooth Audio** (Recommended for MVP)
- Use iOS CoreBluetooth and AVAudioSession APIs
- Treat Meta glasses as standard Bluetooth audio device
- No Meta-specific SDK required
- Works with any Bluetooth audio device (headphones, other smart glasses)
- **Pros**: Simple, no vendor lock-in, faster to implement
- **Cons**: Limited to basic audio I/O, no glasses-specific features

**Option 2: Meta SDK Integration** (Future enhancement)
- Use Meta's official SDK if/when available for developers
- Access to glasses-specific features (button events, LED indicators, etc.)
- Potential for richer integration (visual indicators, gesture support)
- **Pros**: Better UX, more control over glasses features
- **Cons**: Vendor-specific, SDK availability uncertain, more complex

**MVP Recommendation**: Start with **Option 1** (standard Bluetooth) for fastest time-to-demo. Upgrade to Meta SDK if/when available and if enhanced features are needed.

### Button Trigger Handling

**Approach 1: Audio-Based Trigger** (MVP)
- User presses button on glasses
- Glasses emit a specific audio tone or start recording
- iPhone detects audio start and begins processing
- Simple to implement with standard Bluetooth audio

**Approach 2: SDK-Based Trigger** (If Meta SDK available)
- Meta SDK sends button press event to iPhone app
- App explicitly starts recording audio stream
- More precise control, better UX

### Testing Strategy

**Hardware Testing**:
- [ ] Test with actual Ray-Ban Meta Smart Glasses
- [ ] Test in various environments (quiet, noisy, outdoor)
- [ ] Test with different Bluetooth distances
- [ ] Test battery life impact on iPhone

**Fallback Testing**:
- [ ] Test with standard Bluetooth headphones (AirPods, etc.)
- [ ] Test with iPhone microphone/speaker only
- [ ] Ensure graceful degradation without glasses

**Audio Quality Testing**:
- [ ] Test STT accuracy with glasses microphones
- [ ] Test TTS clarity through glasses speakers
- [ ] Compare vs iPhone native audio quality

### Meta AI Glasses Checklist Items

Added to relevant sections above:
- Bluetooth audio capture from Meta AI glasses
- Button press trigger handling
- TTS playback through glasses speakers
- Connection/disconnection handling
- Audio quality monitoring for Bluetooth
- Fallback to iPhone when glasses unavailable

### Future Enhancements for Meta Glasses

- Multi-modal input (audio + camera if Meta provides SDK access)
- Visual feedback via LED indicators (if SDK supports)
- Gesture controls (if glasses hardware supports)
- On-glasses notifications (if SDK supports display/audio cues)

---

## API Integration Contracts

### 1. POST /v1/command

**Purpose**: Submit a hands-free command (audio or text)

**Request**:
```json
{
  "input": {
    "type": "audio",
    "uri": "data:audio/wav;base64,<base64-audio>",
    "format": "wav",
    "duration_ms": 3500
  },
  "profile": "commute",
  "client_context": {
    "device": "iphone",
    "privacy_mode": "balanced",
    "debug": false
  },
  "idempotency_key": "uuid-v4"
}
```

**Response**:
```json
{
  "status": "ok",
  "intent": {
    "name": "inbox.list",
    "confidence": 0.95,
    "entities": {}
  },
  "spoken_text": "You have 3 items in your inbox...",
  "cards": [
    {
      "title": "PR #123",
      "subtitle": "Review needed",
      "lines": ["Opened by alice", "+50 -10 lines"],
      "deep_link": "https://github.com/..."
    }
  ],
  "pending_action": {
    "token": "uuid",
    "expires_at": "2026-01-16T08:00:00Z",
    "summary": "Request review from bob on PR #123"
  },
  "debug": {
    "transcript": "what's in my inbox",
    "profile_metadata": {"profile": "commute", ...}
  }
}
```

**Headers**:
- `Authorization: Bearer <api-key>`
- `X-Session-Id: <session-uuid>` (optional, for conversation continuity)
- `X-Request-ID: <request-uuid>` (optional, for tracing)

### 2. POST /v1/commands/confirm

**Purpose**: Confirm a side-effect action

**Request**:
```json
{
  "token": "pending-action-token",
  "idempotency_key": "uuid-v4"
}
```

**Response**:
```json
{
  "status": "ok",
  "intent": {
    "name": "request_review.confirmed",
    "confidence": 1.0,
    "entities": {"repo": "acme/backend", "pr_number": 123}
  },
  "spoken_text": "Review requested from bob on acme/backend#123"
}
```

**Headers**:
- `Authorization: Bearer <api-key>`

### 3. GET /v1/status

**Purpose**: Check service health and version

**Response**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-01-16T07:00:00Z",
  "dependencies": [
    {
      "name": "duckdb",
      "status": "ok",
      "message": "Database connection healthy"
    }
  ]
}
```

### 4. POST /v1/tts

**Purpose**: Convert text to speech audio

**Request**:
```json
{
  "text": "You have 3 items in your inbox",
  "voice": "default",
  "format": "mp3"
}
```

**Response**: Audio bytes (audio/mpeg or audio/wav)

**Headers**:
- `Content-Type: audio/mpeg` or `audio/wav`
- `Content-Disposition: attachment; filename="speech.mp3"`

### 5. POST /v1/notifications/subscriptions (PR-024 Dependency)

**Purpose**: Register device for push notifications

**Request**:
```json
{
  "endpoint": "apns-device-token",
  "subscription_keys": {
    "platform": "apns",
    "device_token": "<apns-token>"
  }
}
```

**Response**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "endpoint": "apns-device-token",
  "subscription_keys": {...},
  "created_at": "2026-01-16T07:00:00Z",
  "updated_at": "2026-01-16T07:00:00Z"
}
```

### 6. GET /v1/notifications

**Purpose**: Poll for new notifications (alternative to push)

**Query Parameters**:
- `since`: ISO 8601 timestamp (optional)
- `limit`: Max results (default: 50, max: 100)

**Response**:
```json
{
  "notifications": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "event_type": "webhook.pr_opened",
      "message": "PR #123 opened in acme/backend",
      "metadata": {"pr_number": 123, "repo": "acme/backend"},
      "created_at": "2026-01-16T07:00:00Z",
      "read": false
    }
  ],
  "count": 1
}
```

---

## Backend Dependencies

### PR-024: Push Notifications via APNS/FCM Scaffolding

**Status**: Required for mobile push notifications

**Key Deliverables**:
- Device push registration endpoints
- APNS/FCM provider stubs
- Database persistence for device tokens
- Notification delivery provider selection

**Mobile Client Impact**:
- Must call `/v1/notifications/subscriptions` to register APNS token
- Backend will select APNS provider based on platform
- Notifications will be delivered via APNS when backend emits events

**Migration Path**:
- Phase 1: Use polling (`GET /v1/notifications`) without PR-024
- Phase 2: Enable push after PR-024 is merged and deployed

### PR-023: GitHub OAuth Flow

**Status**: Required for live GitHub integration

**Key Deliverables**:
- OAuth login/callback endpoints
- Token storage and refresh
- Live GitHub API access

**Mobile Client Impact**:
- Can implement OAuth flow for production use
- Dev/test can continue with API key auth
- Enables live GitHub actions (merge, request review, etc.)

---

## Repository & CI Strategy

### Recommended Approach: Separate Mobile Workspace

**Option 1: New Repository (Recommended)**
- Create `lift_coding_mobile` repository
- Independent release cycle
- Mobile-specific CI/CD (Xcode, TestFlight, App Store)
- Easier dependency management

**Option 2: Monorepo with Mobile Workspace**
- Add `/mobile` directory to this repo
- Shared documentation and tracking
- Requires CI configuration for iOS builds
- Potential for path-based CI triggers

**Recommendation**: **Option 1** (New Repository) for the following reasons:
- Different toolchains (Python backend vs Swift/iOS)
- Different deployment targets (server vs App Store)
- Cleaner separation of concerns
- Easier to scale separate teams

### Mobile CI Strategy

**Required Workflows**:
1. **Build & Test**: Run on every PR
   - Xcode build
   - Unit tests
   - UI tests
   - SwiftLint

2. **TestFlight Deploy**: Run on main branch merge
   - Build release variant
   - Upload to TestFlight
   - Notify team of new build

3. **App Store Deploy**: Manual trigger
   - Build production variant
   - Submit for App Store review
   - Track release status

**CI Platforms**:
- **GitHub Actions**: Native integration, good for open source
- **Xcode Cloud**: Apple's native CI, easiest for iOS
- **Fastlane**: Automation tool for builds and releases

### Version Management

**Backend API Versioning**:
- All endpoints under `/v1/` prefix
- Backend maintains API compatibility within v1
- Mobile client includes API version in User-Agent header

**Mobile App Versioning**:
- Semantic versioning (e.g., 1.0.0)
- Build numbers for TestFlight (auto-incremented)
- Update checks at app startup (optional)

### Testing Against Backend

**Local Development**:
- Run backend locally (Docker Compose)
- Mobile app points to `http://localhost:8080`
- Use dev mode with fixture responses

**Staging Environment**:
- Deploy backend to staging server
- Mobile app points to staging URL
- Test with real push notifications

**Production**:
- Mobile app points to production backend
- Use production APNS certificates
- Monitor error rates and crashes

---

## Implementation Phases

### Phase 1: Core Command Loop (2-3 weeks)
- Meta AI glasses Bluetooth audio capture
- Push-to-talk button trigger from glasses
- `/v1/command` integration (audio)
- Basic TTS playback through glasses speakers
- Error handling and retry logic
- **Goal**: End-to-end "record via Meta glasses → transcribe → respond → play through glasses" loop

### Phase 2: Confirmation & Actions (1-2 weeks)
- Pending action UI (on iPhone)
- `/v1/commands/confirm` integration
- UICard rendering
- Deep linking
- **Goal**: Handle side-effect actions with confirmation

### Phase 3: Push Notifications (1-2 weeks)
- APNS registration
- Push notification reception
- Notification UI and history (on iPhone)
- Optional TTS playback through Meta glasses for notifications
- **Goal**: Receive backend events in real-time and speak through glasses

### Phase 4: Dev Tools & Polish (1-2 weeks)
- Debug panel and transcript viewer (on iPhone)
- Fixture replay
- Settings screen (iPhone) - configure glasses behavior
- Accessibility improvements
- Bluetooth connection monitoring and diagnostics
- **Goal**: Developer-friendly testing and refinement

### Phase 5: Production Readiness (1 week)
- OAuth login flow
- Production backend configuration
- TestFlight distribution for beta testing with Meta glasses
- Privacy policy and permissions
- **Goal**: Beta testing with real users and Meta glasses

---

## Open Questions & Future Work

**Open Questions**:
1. Should mobile app include on-device intent parsing?
2. What's the strategy for offline command queuing?
3. Does Meta provide an official SDK for Ray-Ban Meta Smart Glasses developer access?
4. How to handle wearable-only mode (Meta glasses without phone nearby)?
5. Should we support Android or focus on iOS first? (Meta glasses work with both platforms)
6. Can we access camera feed from Meta glasses for multi-modal commands?

**Future Enhancements**:
- Background audio monitoring (always-listening mode via glasses)
- Siri Shortcuts integration
- Widget for quick actions
- CarPlay support for in-car use
- Multi-device sync (iPad, Mac)
- Apple Watch support as alternative wearable
- Android support for Meta glasses + Android phone
- Camera-based commands if Meta SDK provides access
