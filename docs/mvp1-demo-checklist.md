# MVP1 Demo Checklist

This checklist provides a step-by-step guide for running the MVP1 demo consistently. A new team member should be able to execute this demo successfully using this document alone.

## Pre-Demo Setup

### 1. Hardware Setup
- [ ] Meta AI Glasses (or compatible Bluetooth headset) charged and ready
- [ ] Glasses paired with iOS device via Bluetooth
- [ ] Verify Bluetooth connection is active and stable
- [ ] iOS device charged and ready

### 2. Network Setup
- [ ] Backend server is accessible (same WiFi network or reachable endpoint)
- [ ] Note backend URL (e.g., `http://192.168.1.100:8080` or `http://localhost:8080`)
- [ ] Verify mobile device can reach backend:
  ```bash
  curl http://<backend-url>/v1/status
  ```
  Expected response: `{"status":"ok","version":"..."}`

### 3. Backend Configuration

Choose either **Option A** (deterministic/stubbed) or **Option B** (realistic):

#### Option A: Deterministic Demo (Stub STT/TTS)
Use this for controlled demos where you want predictable behavior.

- [ ] Ensure backend is running with stub providers enabled
- [ ] Stub STT will transcribe audio input to predefined commands
- [ ] Stub TTS will return canned audio responses
- [ ] Set environment variables:
  ```bash
  export USE_STUB_STT=true
  export USE_STUB_TTS=true
  ```

#### Option B: Realistic Demo (OpenAI STT/TTS)
Use this for realistic demos with actual speech recognition.

- [ ] Set `OPENAI_API_KEY` in backend environment
- [ ] Verify OpenAI providers are enabled:
  ```bash
  export USE_STUB_STT=false
  export USE_STUB_TTS=false
  export OPENAI_API_KEY=sk-...
  ```
- [ ] Test OpenAI connectivity from backend
- [ ] Practice voice commands clearly and at normal speaking volume

### 4. Mobile App Setup
- [ ] Mobile app installed and running
- [ ] App connected to backend (verify in settings)
- [ ] Audio routing configured:
  - iOS: Bluetooth audio input/output enabled
  - Android: Bluetooth SCO enabled
- [ ] Test microphone input (check audio levels)
- [ ] Test speaker output (play test sound through glasses)

### 5. Backend Authentication
- [ ] GitHub OAuth token configured (for real GitHub API calls)
  ```bash
  export GITHUB_TOKEN=ghp_...
  ```
- [ ] Or use mock GitHub data for demo (if provider supports it)
- [ ] Verify authentication:
  ```bash
  curl -H "X-User-ID: test-user" http://<backend-url>/v1/inbox
  ```

## Demo Script

Follow this script in order. Each step includes the voice command, expected backend behavior, and success criteria.

### Step 1: Show My Inbox
**Voice Command:** "Show my inbox"

**What happens:**
1. Mobile app captures audio from glasses microphone
2. Audio sent to backend for STT processing
3. Backend recognizes intent: `inbox.list`
4. Backend fetches GitHub PRs and notifications
5. Backend generates spoken summary via TTS
6. Audio response played through glasses speakers

**Expected Response (spoken):**
> "You have 3 pull requests. PR 456 from main, status checks passing. PR 789 from feature branch, 2 comments. PR 123 from alice, awaiting review."

**Success Criteria:**
- [ ] Audio captured from glasses mic
- [ ] Command recognized correctly
- [ ] Backend returns `CommandResponse` with `spoken_text`
- [ ] Audio plays through glasses speakers
- [ ] Response summarizes PRs with key details

**Troubleshooting:**
- If no audio: Check Bluetooth connection, verify glasses are selected audio device
- If wrong command recognized: Speak more clearly, check STT configuration
- If no response: Check backend logs for errors, verify GitHub token

### Step 2: Next Item
**Voice Command:** "Next"

**What happens:**
1. Backend recognizes navigation intent: `inbox.next`
2. Backend moves to next item in inbox
3. TTS generates spoken summary of next item

**Expected Response (spoken):**
> "Next: PR 789 from feature-auth branch. 2 new comments. Last updated 3 hours ago. Checks are running."

**Success Criteria:**
- [ ] Command recognized as navigation
- [ ] Backend advances to next inbox item
- [ ] Response provides details of next PR

### Step 3: Repeat
**Voice Command:** "Repeat"

**What happens:**
1. Backend recognizes repeat intent
2. Backend retrieves last spoken response
3. TTS plays previous response again

**Expected Response (spoken):**
> (Same as Step 2 response)

**Success Criteria:**
- [ ] Command recognized correctly
- [ ] Previous response is spoken again verbatim
- [ ] No new data is fetched (cached response)

### Step 4: Summarize PR
**Voice Command:** "Summarize PR 123" or "Tell me about PR one two three"

**What happens:**
1. Backend recognizes intent: `pr.summarize`
2. Backend extracts PR number from command (123)
3. Backend fetches PR details: description, diff stats, checks, reviews
4. Backend generates comprehensive summary via TTS

**Expected Response (spoken):**
> "PR 123: Add authentication endpoint. 3 files changed, 156 additions, 42 deletions. Status checks: all passing. 2 approving reviews from Alice and Bob. No merge conflicts."

**Success Criteria:**
- [ ] PR number extracted correctly
- [ ] Summary includes: title, diff stats, checks, reviews
- [ ] Clear indication of merge readiness

### Step 5: (Optional) Request Review
**Voice Command:** "Request review from Alice"

**What happens:**
1. Backend recognizes write action intent: `pr.request_review`
2. Backend triggers confirmation flow (if enabled)
3. User confirms action
4. Backend calls GitHub API to request review
5. Backend logs action and responds with confirmation

**Expected Response (spoken):**
> "Review requested from Alice on PR 123. Notification sent."

**Success Criteria:**
- [ ] Action requires confirmation (if policy enabled)
- [ ] GitHub API called successfully
- [ ] Action logged in audit trail
- [ ] Confirmation spoken back to user

## Fallback Behaviors

### Audio Input Issues
If glasses microphone is unreliable or not working:

1. **Use phone microphone:**
   - Switch mobile app to "Phone Mic" mode
   - Hold phone near mouth when speaking commands
   - Audio routing: Phone mic → Backend STT

2. **Use text input mode:**
   - Switch mobile app to "Text Mode"
   - Type commands in text box: `show my inbox`, `next`, etc.
   - Backend processes text directly (no STT needed)

### Audio Output Issues
If glasses speakers not working:

1. **Use phone speakers:**
   - Switch audio output to phone
   - Response plays through phone speakers
   - Audio routing: Backend TTS → Phone speakers

2. **Use text output mode:**
   - Enable "Text Response" in mobile app
   - Responses displayed as text on screen
   - No TTS needed

### Backend Issues
If backend is unresponsive:

1. **Check backend status:**
   ```bash
   curl http://<backend-url>/v1/status
   ```
2. **Check backend logs:**
   ```bash
   docker-compose logs -f backend
   ```
3. **Restart backend:**
   ```bash
   docker-compose restart backend
   ```

### STT/TTS Provider Issues
If OpenAI or other providers fail:

1. **Switch to stub providers:**
   ```bash
   export USE_STUB_STT=true
   export USE_STUB_TTS=true
   ```
2. **Restart backend to apply changes**
3. **Continue demo with stubbed responses**

## Post-Demo Artifacts

After completing the demo, capture these artifacts for review and debugging:

### 1. Backend Logs
- [ ] Export timestamped logs for demo duration:
  ```bash
  docker-compose logs --since=30m backend > demo-backend-logs.txt
  ```
- [ ] Include: STT inputs, intent recognition, API calls, TTS outputs

### 2. Command Responses
- [ ] Capture `CommandResponse` JSON for each step
- [ ] Save from backend logs or API responses
- [ ] Example:
  ```json
  {
    "command_id": "cmd_abc123",
    "intent": "inbox.list",
    "spoken_text": "You have 3 pull requests...",
    "audio_url": "http://backend/audio/abc123.mp3",
    "timestamp": "2026-01-18T07:00:00Z"
  }
  ```

### 3. Mobile App Screenshots
- [ ] Screenshot: Initial app state (connected, ready)
- [ ] Screenshot: Audio routing diagnostics (Bluetooth device selected)
- [ ] Screenshot: Each command sent with response received
- [ ] Screenshot: Any error messages or warnings

### 4. Audio Recordings (Optional)
- [ ] Record demo audio from glasses (if supported)
- [ ] Save TTS output audio files from backend
- [ ] Compare input vs recognized text for accuracy

### 5. Metrics and Timing
- [ ] Record timestamp for each command
- [ ] Measure latency: command → response (end-to-end)
- [ ] Note any delays or performance issues
- [ ] Example timing:
  - STT latency: ~500ms
  - Backend processing: ~1-2s
  - TTS generation: ~1s
  - Total: ~3-4s per command

### 6. Error Log
- [ ] Document any errors encountered
- [ ] Include error messages, stack traces
- [ ] Note workarounds applied during demo

## Success Criteria Summary

The demo is successful if:
- [ ] All 4 core commands executed successfully (inbox, next, repeat, summarize)
- [ ] Audio captured from glasses microphone
- [ ] Audio played through glasses speakers
- [ ] Commands recognized accurately (>90% accuracy for Option B)
- [ ] Backend responses were timely (<5s per command)
- [ ] No crashes or critical errors
- [ ] Fallback behaviors work when needed

## Related Documentation

For more detailed information, see:

- **Mobile Client Integration:** `docs/mobile-client-integration.md`  
  Complete API reference for mobile app development

- **Meta AI Glasses Setup:** `docs/meta-ai-glasses.md`  
  Hardware setup and audio routing details

- **Meta AI Glasses Audio Routing:** `docs/meta-ai-glasses-audio-routing.md`  
  Advanced audio configuration and troubleshooting

- **MVP Implementation Plan:** `implementation_plan/docs/10-mvp-checklists.md`  
  High-level MVP1-4 checklists and requirements

- **Backend API Documentation:** `docs/mobile-client-integration.md`  
  Full API endpoint reference and examples

## Notes

- This checklist is compatible with both stubbed and real STT/TTS providers
- Stubbed providers are recommended for first-time demos or when network is unreliable
- Real providers (OpenAI) provide better experience but require stable internet
- Practice the demo 2-3 times before presenting to external audience
- Keep backend logs running during demo for troubleshooting
