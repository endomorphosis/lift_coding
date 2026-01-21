# iOS + Ray-Ban Meta MVP1 Runbook

**Version**: 1.0  
**Last Updated**: 2026-01-19  
**Purpose**: Single, reliable, end-to-end runbook for MVP1 demo on iOS with Ray-Ban Meta glasses

---

## Overview

This runbook provides a complete, step-by-step guide for demonstrating the HandsFree MVP1 system using:
- **Input**: iPhone microphone (reliable default)
- **Output**: Ray-Ban Meta glasses speakers via iOS Bluetooth
- **Flow**: Voice command → Backend processing → TTS response → Optional notification deep-link

**Target Audience**: Operators, demo presenters, and new team members

**Time to Complete**: 15-20 minutes (including setup verification)

---

## Quick Start Checklist

Use this checklist for a successful demo:

### Pre-Demo Setup (5-10 minutes)
- [ ] Ray-Ban Meta glasses paired and connected to iPhone via Bluetooth
- [ ] iPhone audio output manually verified to route to glasses
- [ ] Backend server running and accessible from iPhone
- [ ] Environment variables configured correctly
- [ ] Status endpoint verified (`GET /v1/status`)
- [ ] Sample data seeded (if using fixtures)

### Demo Execution (5-10 minutes)
- [ ] Execute Command 1: "Show my inbox"
- [ ] Execute Command 2: "Summarize PR [number]"
- [ ] Execute Command 3: "Next" (navigation)
- [ ] Execute Command 4: "Repeat" (replay)
- [ ] Execute Command 5: (Optional) "Request review" with confirmation

### Post-Demo Verification
- [ ] Audio played correctly through glasses speakers
- [ ] No audio routing issues encountered
- [ ] Backend responded to all commands successfully
- [ ] Optional: Notifications were fetched and displayed

---

## Part 1: Prerequisites

### Hardware Requirements

1. **iPhone** (iOS 15.0 or later recommended)
   - iPhone 11 or newer preferred
   - iOS Bluetooth stack must be functional
   - Physical device required (simulator does not support Bluetooth audio)

2. **Ray-Ban Meta Smart Glasses**
   - Fully charged (check battery level)
   - Firmware up to date
   - Paired with iPhone via official Meta View app (initial setup)

3. **Backend Server**
   - Running locally on development machine, or
   - Accessible via network/HTTPS endpoint
   - Minimum: Python 3.11+, FastAPI stack

### Software Requirements

1. **iOS Companion App**
   - Built from `mobile/` directory
   - Expo dev client or production build
   - Proper permissions granted:
     - Microphone access
     - Bluetooth access
     - Network access

2. **Backend Environment**
   - Dependencies installed: `pip install -r requirements.txt`
   - Environment variables configured (see below)
   - Database migrated if using persistent storage

### Environment Variables

Configure these on the backend server before starting:

#### Authentication (for local demos)
```bash
# Dev mode: Skip authentication, allow all requests
HANDSFREE_AUTH_MODE=dev
```

#### Speech-to-Text (STT)
```bash
# Option 1: Stub mode (no API key, deterministic transcript)
HANDS_FREE_STT_PROVIDER=stub

# Option 2: OpenAI mode (realistic transcription, requires API key)
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

#### Text-to-Speech (TTS)
```bash
# Option 1: Stub mode (no API key, deterministic audio)
HANDSFREE_TTS_PROVIDER=stub

# Option 2: OpenAI mode (realistic voice, requires API key)
HANDSFREE_TTS_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

#### GitHub Integration
```bash
# Option 1: Fixture mode (default, no token needed, uses canned data)
# No configuration required

# Option 2: Live mode (real GitHub API, requires token)
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_...
```

#### Push Notifications (Optional)
```bash
# Expo push notification token (if demonstrating notification deep-links)
EXPO_PUSH_TOKEN=ExponentPushToken[...]
```

---

## Part 2: iOS Setup

### Step 1: Pair Ray-Ban Meta Glasses

1. **Initial Pairing** (if not already paired):
   - Open **Settings** app on iPhone
   - Navigate to **Bluetooth**
   - Turn on Ray-Ban Meta glasses (hold power button until LED flashes)
   - Wait for "Ray-Ban Meta..." to appear in available devices
   - Tap to pair
   - Confirm pairing on both devices if prompted

2. **Verify Connection**:
   - In Settings → Bluetooth, verify status shows **"Connected"**
   - If status shows "Not Connected", tap the device name to reconnect

3. **Alternative Pairing** (via Meta View app):
   - Open Meta View app
   - Follow in-app pairing instructions
   - This ensures glasses firmware is up to date

### Step 2: Configure Audio Routing

**Critical**: iOS must route audio output to the glasses for TTS playback.

1. **Play a Test Sound**:
   - Open Music app or YouTube
   - Play any audio
   - Listen to confirm audio comes from **glasses speakers**, not iPhone speaker

2. **If Audio Plays on iPhone Speaker**:
   - Open **Control Center** (swipe down from top-right on Face ID iPhones, or swipe up from bottom on Home button iPhones)
   - Long-press the audio card (shows currently playing audio)
   - Tap the **audio output icon** (looks like a triangle with circles)
   - Select **"Ray-Ban Meta..."** from the list
   - Verify audio switches to glasses

3. **Verify Route Persists**:
   - Play audio again
   - Confirm it still plays through glasses
   - Route should persist until glasses disconnect

### Step 3: Launch iOS Companion App

1. **Open Expo Dev Client** (or production app)
2. **Grant Permissions** (if prompted):
   - Microphone: **Allow**
   - Bluetooth: **Allow**
   - Notifications (optional): **Allow**
3. **Configure Backend URL**:
   - Navigate to app settings screen
   - Enter backend URL, e.g., `http://192.168.1.100:8000` or `https://api.example.com`
   - Tap **Save** and verify connection indicator shows green/connected
4. **Verify Glasses Connection Status**:
   - Check app UI for Bluetooth status indicator
   - Should show "Connected to Ray-Ban Meta" or similar

---

## Part 3: Backend Setup

### Step 1: Start the Backend Server

1. **Navigate to Project Root**:
   ```bash
   cd /path/to/lift_coding
   ```

2. **Activate Virtual Environment** (if using one):
   ```bash
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Start the Server**:
   ```bash
   # Development mode
   python -m src.main
   
   # Or via uvicorn directly
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
   ```

4. **Verify Server Started**:
   - Look for output: `Uvicorn running on http://0.0.0.0:8080`
   - Server should be listening and ready

### Step 2: Verify Backend Health

#### Test 1: Status Endpoint

```bash
curl http://localhost:8080/v1/status
```

**Expected Response**:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "stt_provider": "stub",
  "tts_provider": "stub"
}
```

**What This Confirms**:
- ✅ Server is running and responding
- ✅ STT and TTS providers are configured
- ✅ Basic routing works

#### Test 2: TTS Endpoint

```bash
curl -X POST http://localhost:8080/v1/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello from the backend.",
    "voice": "alloy",
    "format": "wav"
  }' \
  --output /tmp/test-tts.wav
```

**Expected Behavior**:
- Command completes successfully
- File `/tmp/test-tts.wav` is created
- File size > 0 bytes (typically 10-50 KB for short text)

**Play the file** (optional):
```bash
# macOS
afplay /tmp/test-tts.wav

# Linux (requires aplay)
aplay /tmp/test-tts.wav
```

**What This Confirms**:
- ✅ TTS provider is working
- ✅ Audio generation pipeline is functional
- ✅ Backend can serve binary audio

#### Test 3: Command Endpoint (Text Input)

```bash
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "type": "text",
      "text": "show my inbox"
    },
    "context": {
      "device_id": "test-device",
      "session_id": "test-session-1"
    }
  }'
```

**Expected Response**:
```json
{
  "status": "success",
  "intent": "inbox.summary",
  "spoken_text": "You have 3 pull requests awaiting review. The first is PR 123...",
  "cards": [
    {
      "type": "pr_summary",
      "title": "PR #123: Add new feature",
      "url": "https://github.com/org/repo/pull/123"
    }
  ]
}
```

**What This Confirms**:
- ✅ Command processing pipeline works
- ✅ Intent recognition is functional
- ✅ Response includes spoken text for TTS
- ✅ Cards are returned for UI display

### Step 3: Seed Sample Data (If Using Fixtures)

If using fixture mode (default when `GITHUB_LIVE_MODE` is not set):

```bash
# No seeding required - fixtures are loaded automatically
# Sample PRs and notifications are available immediately
```

If using live GitHub mode:

```bash
# Ensure GITHUB_TOKEN is set and has access to target repos
# Test by listing issues/PRs:
curl -H "Authorization: Bearer ghp_..." \
  https://api.github.com/repos/YOUR_ORG/YOUR_REPO/pulls
```

---

## Part 4: Demo Script (Known-Good Commands)

Execute these commands in sequence for a successful demo. Each command should result in audio playback through the glasses.

### Command 1: Inbox Summary

**User Action**: Say (or type) "Show my inbox"

**What Happens**:
1. iOS app captures audio or accepts text input
2. Sends `POST /v1/command` with `"text": "show my inbox"`
3. Backend processes and returns inbox summary
4. iOS app calls `POST /v1/tts` with spoken text
5. TTS audio plays through glasses speakers

**Expected Response**:
```json
{
  "status": "success",
  "intent": "inbox.summary",
  "spoken_text": "You have 3 pull requests awaiting review. The first is PR 123 from Alice: Add authentication flow. The second is PR 124 from Bob: Fix bug in API...",
  "cards": [...]
}
```

**Verification**:
- ✅ Audio plays through glasses (not phone speaker)
- ✅ User hears full inbox summary
- ✅ UI shows PR cards

### Command 2: Summarize Specific PR

**User Action**: Say "Summarize PR 123" (or another PR number from inbox)

**What Happens**:
1. Command sent with specific PR number
2. Backend fetches PR details
3. Returns detailed summary
4. TTS plays summary through glasses

**Expected Response**:
```json
{
  "status": "success",
  "intent": "pr.summary",
  "spoken_text": "PR 123 titled Add authentication flow by Alice. This PR introduces a new OAuth 2.0 authentication flow with JWT tokens. It includes 5 commits and modifies 12 files...",
  "cards": [
    {
      "type": "pr_detail",
      "number": 123,
      "title": "Add authentication flow",
      "author": "alice"
    }
  ]
}
```

**Verification**:
- ✅ Correct PR details are spoken
- ✅ Audio quality is clear
- ✅ UI shows PR detail card

### Command 3: Navigation - "Next"

**User Action**: Say "Next"

**What Happens**:
1. Backend advances to next item in current context (inbox)
2. Returns next PR summary
3. TTS plays new item summary

**Expected Response**:
```json
{
  "status": "success",
  "intent": "navigation.next",
  "spoken_text": "Next item: PR 124 titled Fix bug in API by Bob. This PR addresses a critical bug...",
  "cards": [...]
}
```

**Verification**:
- ✅ Different item is spoken (PR 124, not 123)
- ✅ Navigation context is maintained
- ✅ UI updates to show new card

### Command 4: Navigation - "Repeat"

**User Action**: Say "Repeat"

**What Happens**:
1. Backend re-sends previous response
2. Same spoken text is used
3. TTS plays same content again

**Expected Response**:
```json
{
  "status": "success",
  "intent": "navigation.repeat",
  "spoken_text": "Repeating: PR 124 titled Fix bug in API by Bob. This PR addresses a critical bug...",
  "cards": [...]
}
```

**Verification**:
- ✅ Same content as previous command
- ✅ No errors or state changes
- ✅ Audio plays correctly again

### Command 5: Action with Confirmation (Optional)

**User Action**: Say "Request review on PR 123"

**What Happens**:
1. Backend recognizes action intent requiring confirmation
2. Returns confirmation prompt
3. TTS asks user to confirm

**Expected Response**:
```json
{
  "status": "pending",
  "intent": "pr.request_review",
  "spoken_text": "You're about to request a review on PR 123 from Alice. Say confirm to proceed, or cancel to abort.",
  "requires_confirmation": true,
  "confirmation_token": "abc123..."
}
```

**User Follow-Up**: Say "Confirm"

**Confirmation Request**:
```bash
curl -X POST http://localhost:8080/v1/commands/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "confirmation_token": "abc123..."
  }'
```

**Final Response**:
```json
{
  "status": "success",
  "intent": "pr.request_review.confirmed",
  "spoken_text": "Review requested on PR 123.",
  "cards": [...]
}
```

**Verification**:
- ✅ Confirmation flow works correctly
- ✅ Action is executed only after confirmation
- ✅ User receives success feedback

---

## Part 5: Troubleshooting

This section covers the **5 most common failure modes** with diagnosis and resolution steps.

### Failure Mode 1: Audio Plays on iPhone Speaker Instead of Glasses

**Symptoms**:
- TTS audio is audible from iPhone speaker
- No audio coming from glasses speakers
- Glasses are connected via Bluetooth

**Diagnosis**:
```bash
# Check iOS audio routing (if app has diagnostics screen)
# Or manually verify in Control Center
```

**Root Causes**:
1. iOS audio route was not set to Bluetooth output
2. Another app changed the audio route
3. Glasses Bluetooth connection is unstable
4. App's AVAudioSession is misconfigured

**Resolution Steps**:

**Step 1**: Manually set audio route
- Open Control Center
- Long-press audio card
- Tap audio output icon
- Select "Ray-Ban Meta..."

**Step 2**: Restart iOS app
- Force quit the app
- Relaunch
- Audio route should initialize correctly on startup

**Step 3**: Toggle Bluetooth
- Settings → Bluetooth → Off
- Wait 5 seconds
- Settings → Bluetooth → On
- Reconnect glasses

**Step 4**: Re-pair glasses (if all else fails)
- Settings → Bluetooth → Tap (i) next to glasses
- Tap "Forget This Device"
- Re-pair glasses from scratch

**Prevention**:
- Configure AVAudioSession category to `.playback` with `.allowBluetooth` option
- Monitor route change notifications and restore preferred route

### Failure Mode 2: Backend Returns 401 Unauthorized

**Symptoms**:
- Command requests fail with HTTP 401
- Status endpoint may work, but command endpoint does not
- Error message: "Unauthorized" or "Missing authentication"

**Diagnosis**:
```bash
# Test authentication
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{"input": {"type": "text", "text": "test"}, "context": {}}' \
  -v
```

**Root Causes**:
1. `HANDSFREE_AUTH_MODE` is not set to `dev`
2. Client is not sending required credentials
3. Session token is expired or invalid

**Resolution Steps**:

**Step 1**: Verify environment variable
```bash
# Check if HANDSFREE_AUTH_MODE is set
echo $HANDSFREE_AUTH_MODE

# Expected output: dev
```

**Step 2**: Set auth mode to dev (for demos)
```bash
export HANDSFREE_AUTH_MODE=dev
```

**Step 3**: Restart backend server
```bash
# Ctrl+C to stop
# Restart with new environment variable
python -m src.main
```

**Step 4**: Verify status endpoint confirms dev mode
```bash
curl http://localhost:8080/v1/status
# Should include: "auth_mode": "dev"
```

**Prevention**:
- Always set `HANDSFREE_AUTH_MODE=dev` in `.env` file for local development
- Document required environment variables in setup instructions

### Failure Mode 3: STT Returns Stub/Placeholder Text

**Symptoms**:
- Audio commands are sent but transcript is generic or placeholder
- Example: "This is a stub transcript for testing"
- Real user speech is not being transcribed

**Diagnosis**:
```bash
# Check STT provider configuration
curl http://localhost:8080/v1/status

# Look for: "stt_provider": "stub"
```

**Root Causes**:
1. `HANDS_FREE_STT_PROVIDER` is set to `stub`
2. OpenAI API key is missing or invalid (if provider is `openai`)
3. Audio format is incompatible with STT provider

**Resolution Steps**:

**Step 1**: Decide if realistic STT is needed
- For demos showcasing UI/flow only: Stub mode is acceptable (use text input)
- For demos showcasing voice input: Switch to OpenAI provider

**Step 2**: Switch to OpenAI STT (if needed)
```bash
export HANDS_FREE_STT_PROVIDER=openai
export OPENAI_API_KEY=sk-...  # Your OpenAI API key
```

**Step 3**: Restart backend
```bash
python -m src.main
```

**Step 4**: Verify configuration
```bash
curl http://localhost:8080/v1/status
# Should show: "stt_provider": "openai"
```

**Step 5**: Test with audio command
```bash
# Upload test audio
curl -X POST http://localhost:8080/v1/dev/audio \
  -H "Content-Type: application/json" \
  -d '{"data_base64": "base64_encoded_audio_here", "format": "m4a"}'

# Use returned URI in command
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "type": "audio",
      "format": "m4a",
      "uri": "file:///tmp/audio/..."
    },
    "context": {}
  }'
```

**Alternative**: Use text input for demos
- In iOS app, use text input field instead of voice recording
- Bypasses STT entirely while still demonstrating TTS and command processing

**Prevention**:
- Document which provider mode is intended for which environment
- Add environment variable validation at server startup

### Failure Mode 4: Backend Not Responding / Connection Timeout

**Symptoms**:
- iOS app shows "Connection failed" or "Timeout"
- Backend logs show no incoming requests
- `curl` commands from iOS device fail

**Diagnosis**:
```bash
# From iOS device (via SSH or terminal app)
curl http://BACKEND_IP:8080/v1/status -v

# From backend machine
curl http://localhost:8080/v1/status -v
```

**Root Causes**:
1. Backend server is not running
2. Firewall is blocking port 8000
3. Backend is bound to localhost only (not accessible from network)
4. iOS app has wrong backend URL configured

**Resolution Steps**:

**Step 1**: Verify backend is running
```bash
# Check process
ps aux | grep uvicorn

# Check listening ports
lsof -i :8080  # macOS/Linux
netstat -an | grep 8080  # Windows
```

**Step 2**: Ensure server binds to 0.0.0.0 (all interfaces)
```bash
# Start with explicit host
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

**Step 3**: Check firewall rules
```bash
# macOS
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps

# Linux (ufw)
sudo ufw status
sudo ufw allow 8080/tcp

# Linux (firewalld)
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=8080/tcp --permanent
sudo firewall-cmd --reload
```

**Step 4**: Verify network connectivity
```bash
# Get backend machine IP
ifconfig  # macOS/Linux
ipconfig  # Windows

# Ping from iOS device (if possible)
ping BACKEND_IP
```

**Step 5**: Update iOS app backend URL
- Open app settings
- Change from `http://localhost:8080` to `http://ACTUAL_IP:8080`
- Example: `http://192.168.1.100:8080`
- Save and retry

**Prevention**:
- Always start backend with `--host 0.0.0.0` for network demos
- Document firewall setup in prerequisites
- Use HTTPS with proper DNS for production demos

### Failure Mode 5: TTS Not Playing / Silent Audio

**Symptoms**:
- Command succeeds but no audio plays
- iOS app shows playback completed but nothing was heard
- No errors in app logs

**Diagnosis**:
```bash
# Test TTS endpoint directly
curl -X POST http://localhost:8080/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test audio", "voice": "alloy", "format": "wav"}' \
  --output /tmp/test.wav

# Check file size
ls -lh /tmp/test.wav

# Play on backend machine
afplay /tmp/test.wav  # macOS
aplay /tmp/test.wav   # Linux
```

**Root Causes**:
1. TTS provider is misconfigured or returning empty audio
2. Audio format is incompatible with iOS player
3. AVAudioSession is not configured for playback
4. Audio routing is broken (see Failure Mode 1)

**Resolution Steps**:

**Step 1**: Verify TTS provider is working
```bash
curl http://localhost:8080/v1/status
# Check "tts_provider" field

# If "stub", switch to OpenAI for realistic audio
export HANDSFREE_TTS_PROVIDER=openai
export OPENAI_API_KEY=sk-...
# Restart backend
```

**Step 2**: Test TTS output locally
- Download TTS output from backend
- Play on backend machine to confirm audio is valid
- If silent, TTS provider is the issue

**Step 3**: Check iOS AVAudioSession configuration
- Ensure `.playback` or `.playAndRecord` category is set
- Ensure session is activated before playback
- Check app logs for AVAudioSession errors

**Step 4**: Verify audio format compatibility
- iOS supports: WAV (PCM), MP3, AAC, OPUS
- Recommended for TTS: WAV with 16kHz, 16-bit, mono
- If backend returns MP3, ensure iOS decoder is working

**Step 5**: Test with simple audio file
- Use a known-good WAV file
- Attempt playback in iOS app
- If simple file plays but TTS doesn't, issue is with TTS endpoint

**Prevention**:
- Always test TTS pipeline separately before full demo
- Use stub mode initially to isolate audio playback issues
- Log audio buffer sizes and formats in iOS app for debugging

### Failure Mode 6: Bluetooth Disconnection Mid-Demo (Bonus)

**Symptoms**:
- Demo starts successfully
- Mid-demo, audio stops playing through glasses
- Glasses LED may blink or show disconnected status

**Diagnosis**:
- Check Bluetooth connection status in iOS Settings
- Look for "Not Connected" status

**Root Causes**:
1. Low battery on glasses
2. Bluetooth interference
3. User moved too far from phone
4. Another device took over Bluetooth connection

**Resolution Steps**:

**Step 1**: Reconnect immediately
- Tap glasses in Bluetooth settings to reconnect
- Audio routing should restore automatically

**Step 2**: Check battery level
- Glasses may disconnect when battery is critically low
- Charge glasses if needed

**Step 3**: Reduce interference
- Move away from Wi-Fi routers, microwaves
- Limit number of active Bluetooth devices nearby

**Step 4**: Keep phone close to glasses
- Bluetooth range: typically 10 meters
- Keep phone in pocket or within 1-2 meters for best stability

**Prevention**:
- Fully charge glasses before demo
- Minimize Bluetooth interference sources
- Test connection stability before starting demo

---

## Part 6: Optional - Notifications Deep-Link

If demonstrating push notifications and deep-linking:

### Setup Push Notifications

1. **Configure Expo Push Token**:
   ```bash
   export EXPO_PUSH_TOKEN=ExponentPushToken[YOUR_TOKEN]
   ```

2. **Create a Notification Subscription**:
   ```bash
   curl -X POST http://localhost:8080/v1/notifications/subscriptions \
     -H "Content-Type: application/json" \
     -d '{
       "push_token": "ExponentPushToken[YOUR_TOKEN]",
       "platform": "ios",
       "device_id": "test-device"
     }'
   ```

### Trigger a Test Notification

```bash
# Simulate a webhook event that generates a notification
curl -X POST http://localhost:8080/v1/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -d '{
    "action": "opened",
    "pull_request": {
      "number": 999,
      "title": "Test PR for Notification",
      "html_url": "https://github.com/test/repo/pull/999"
    },
    "repository": {
      "full_name": "test/repo"
    }
  }'
```

### Fetch Notifications

```bash
# List notifications
curl http://localhost:8080/v1/notifications

# Get specific notification
curl http://localhost:8080/v1/notifications/{notification_id}
```

**Expected Response**:
```json
{
  "notifications": [
    {
      "id": "notif-123",
      "type": "pr_opened",
      "title": "New PR: Test PR for Notification",
      "body": "PR #999 by alice in test/repo",
      "timestamp": "2026-01-19T00:30:00Z",
      "read": false,
      "data": {
        "pr_number": 999,
        "repo": "test/repo"
      }
    }
  ]
}
```

### Deep-Link to PR from Notification

1. **User taps notification** in iOS notification center
2. **App opens** and navigates to notification detail screen
3. **App calls** `GET /v1/notifications/{notification_id}` for details
4. **App displays** PR summary card
5. **User can** tap card to open PR in browser or in-app web view

---

## Part 7: Rollback and Fallback Procedures

If issues arise during a demo, use these fallback strategies:

### Fallback 1: Switch to Phone Speaker

**When**: Glasses Bluetooth audio routing fails

**Steps**:
1. Open Control Center
2. Select audio output
3. Choose "iPhone" speaker
4. Continue demo with phone speaker output
5. Explain: "For today's demo, we're using the phone speaker as a fallback"

**Pros**: Demo can continue without delay  
**Cons**: Not hands-free; less impressive

### Fallback 2: Use Text Input Instead of Voice

**When**: STT is not working or audio capture fails

**Steps**:
1. In iOS app, switch to text input mode
2. Type commands instead of speaking them
3. Backend and TTS pipeline still function normally
4. Explain: "For today's demo, we're using text input to simulate voice commands"

**Pros**: Bypasses STT issues; consistent results  
**Cons**: Not truly voice-driven

### Fallback 3: Disable Push Notifications

**When**: Notification webhook or push system is broken

**Steps**:
1. Skip notification deep-link portion of demo
2. Focus on core command → TTS → audio playback flow
3. Explain: "Notifications are an optional feature we're still refining"

**Pros**: Core demo still works  
**Cons**: Cannot show end-to-end notification flow

### Fallback 4: Use Fixture Mode

**When**: Live GitHub API is slow or rate-limited

**Steps**:
1. Ensure `GITHUB_LIVE_MODE` is not set (or set to `false`)
2. Restart backend
3. Backend will use canned fixture data (fast, predictable)
4. Explain: "For today's demo, we're using sample data for speed"

**Pros**: Consistent, fast responses; no API dependencies  
**Cons**: Data is not real-time

### Rollback: Revert to Last Known Good Config

**When**: New changes break the demo entirely

**Steps**:
1. Stop backend server
2. Revert code to last stable commit:
   ```bash
   git checkout <last-stable-commit-sha>
   ```
3. Restore environment variables from backup `.env` file
4. Restart backend
5. Re-test status endpoint

---

## Part 8: API Endpoint Reference

### Core Endpoints Used in MVP1 Demo

#### `POST /v1/command`

**Purpose**: Submit a voice command (text or audio metadata)

**Request**:
```json
{
  "input": {
    "type": "text",  // or "audio"
    "text": "show my inbox"  // if type is "text"
    // OR
    // "format": "m4a", "uri": "file://..." if type is "audio"
  },
  "context": {
    "device_id": "iphone-12345",
    "session_id": "session-abc"
  }
}
```

**Response**:
```json
{
  "status": "success",
  "intent": "inbox.summary",
  "spoken_text": "You have 3 pull requests...",
  "cards": [...]
}
```

**Used for**: All command processing

---

#### `POST /v1/tts`

**Purpose**: Convert text to speech audio

**Request**:
```json
{
  "text": "You have 3 pull requests awaiting review.",
  "voice": "alloy",  // or "echo", "fable", etc.
  "format": "wav"    // or "mp3", "opus"
}
```

**Response**: Binary audio data (WAV/MP3/OPUS)

**Used for**: Generating spoken responses for glasses playback

---

#### `GET /v1/notifications`

**Purpose**: Fetch list of notifications for the user

**Response**:
```json
{
  "notifications": [
    {
      "id": "notif-123",
      "type": "pr_opened",
      "title": "New PR: Add feature X",
      "body": "PR #123 by alice",
      "timestamp": "2026-01-19T00:30:00Z",
      "read": false
    }
  ]
}
```

**Used for**: Notification polling (optional in MVP1)

---

#### `GET /v1/notifications/{notification_id}`

**Purpose**: Fetch details of a specific notification

**Response**:
```json
{
  "id": "notif-123",
  "type": "pr_opened",
  "title": "New PR: Add feature X",
  "body": "PR #123 by alice in org/repo",
  "timestamp": "2026-01-19T00:30:00Z",
  "read": false,
  "data": {
    "pr_number": 123,
    "repo": "org/repo",
    "url": "https://github.com/org/repo/pull/123"
  }
}
```

**Used for**: Deep-linking from push notification to PR details

---

#### `GET /v1/status`

**Purpose**: Health check and configuration verification

**Response**:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "stt_provider": "stub",
  "tts_provider": "stub",
  "auth_mode": "dev"
}
```

**Used for**: Pre-demo verification and troubleshooting

---

## Part 9: Success Criteria

A successful MVP1 demo meets these criteria:

- ✅ **Audio Routing**: TTS audio plays through Ray-Ban Meta glasses speakers (not phone)
- ✅ **Command Processing**: All 5 demo commands execute successfully
- ✅ **Voice Input**: Phone microphone captures commands reliably (or text input works as fallback)
- ✅ **Backend Responsiveness**: All API endpoints respond within 2 seconds
- ✅ **Audio Quality**: TTS playback is clear, audible, and free of distortion/echo
- ✅ **Navigation**: "Next" and "Repeat" commands maintain session state correctly
- ✅ **Error Handling**: Any failures are handled gracefully with clear error messages
- ✅ **Optional - Notifications**: Push notifications are received and deep-links work (if demonstrated)

---

## Part 10: Additional Resources

- **OpenAPI Specification**: `spec/openapi.yaml` - Complete API contract
- **Command Grammar**: `spec/command_grammar.md` - Supported intents and patterns
- **Bluetooth Audio Routing Guide**: `docs/meta-ai-glasses-audio-routing.md` - iOS/Android technical details
- **Mobile Client Integration**: `docs/mobile-client-integration.md` - General app setup
- **iOS Audio Route Monitor**: PR-047 tracking doc - Native module for route diagnostics
- **iOS Glasses Player**: PR-049 tracking doc - TTS playback implementation

---

## Part 11: Maintenance and Updates

**Runbook Version History**:
- v1.0 (2026-01-19): Initial release

**Next Review**: 2026-02-01

**Feedback**: Report issues or suggest improvements via GitHub issues in `endomorphosis/lift_coding` repo

---

**End of Runbook**
