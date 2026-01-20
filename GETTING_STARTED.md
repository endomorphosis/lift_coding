# Getting Started with HandsFree Dev Companion

**Welcome!** This guide will help you get up and running with the HandsFree Dev Companion system, whether you're a developer, tester, or agent working on this project.

## Table of Contents

1. [Overview](#overview)
2. [What You'll Need](#what-youll-need)
3. [Quick Start Paths](#quick-start-paths)
4. [Backend Setup](#backend-setup)
5. [Mobile App Setup](#mobile-app-setup)
6. [iPhone & Meta Glasses Testing](#iphone--meta-glasses-testing)
7. [Verification & Testing](#verification--testing)
8. [Next Steps](#next-steps)
9. [Troubleshooting](#troubleshooting)

---

## Overview

HandsFree Dev Companion is a hands-free AI assistant for GitHub that helps developers manage pull requests, issues, and code reviews using:

- **Voice commands** via mobile app or Meta AI Glasses
- **Text-to-speech responses** through Bluetooth audio devices
- **Push notifications** for real-time updates
- **Agent delegation** for automated GitHub operations

### System Architecture

```
┌─────────────────┐     Bluetooth      ┌──────────────────┐      HTTPS       ┌─────────────────┐
│   Meta Glasses  │ ◄───────────────── │  Mobile App      │ ◄──────────────► │  Backend API    │
│   (Audio I/O)   │                    │  (iOS/Android)   │                  │  (FastAPI)      │
└─────────────────┘                    └──────────────────┘                  └─────────────────┘
                                              │                                       │
                                              │ Push                                  │
                                              │ Notifications                         │
                                              ▼                                       ▼
                                       ┌──────────────────┐                  ┌─────────────────┐
                                       │  Expo Push       │                  │   GitHub API    │
                                       │  Service         │                  │   Redis         │
                                       └──────────────────┘                  │   DuckDB        │
                                                                              └─────────────────┘
```

### Key Components

1. **Backend Server** (Python/FastAPI)
   - Command processing and intent recognition
   - GitHub API integration
   - Text-to-speech (TTS) generation
   - Speech-to-text (STT) processing
   - Push notification management

2. **Mobile App** (React Native/Expo)
   - Voice command capture
   - Audio playback through Bluetooth
   - Push notification handling
   - Native iOS/Android modules for Bluetooth

3. **Meta AI Glasses Integration**
   - Bluetooth audio routing
   - Hands-free voice input
   - Ambient audio output

---

## What You'll Need

### For Backend Development

- **Python 3.11+** (required)
- **Docker & Docker Compose** (for Redis)
- **Git**
- **Text editor/IDE** (VS Code recommended)

### For Mobile Development

- **Node.js 18+** and npm
- **Expo CLI** (`npm install -g expo-cli`)
- **iOS Development** (macOS only):
  - Xcode 14.0+
  - iOS Simulator or physical iPhone (iOS 15+)
  - Apple Developer account (for device testing)
- **Android Development**:
  - Android Studio
  - Android Emulator or physical device
  - JDK 17

### For iPhone & Meta Glasses Testing

- **Physical iPhone** (iOS 15+) - Simulator doesn't support Bluetooth
- **Meta AI Glasses** (Ray-Ban Meta or compatible)
- **Bluetooth connection** between devices
- **Network access** to backend server

### Optional

- **OpenAI API Key** (for realistic TTS/STT)
- **GitHub Personal Access Token** (for live GitHub integration)
- **Expo account** (for push notifications)

---

## Quick Start Paths

Choose your path based on what you want to do:

### Path 1: Backend Development (No Mobile)

**Goal**: Work on backend API, command processing, or GitHub integration

**Time**: 10 minutes

```bash
# 1. Clone repo
git clone https://github.com/endomorphosis/lift_coding.git
cd lift_coding

# 2. Install Python dependencies
make deps

# 3. Start Redis
make compose-up

# 4. Start backend server
make dev

# 5. Test it works
curl http://localhost:8080/v1/status
```

See [Backend Setup](#backend-setup) for details.

---

### Path 2: Mobile App Development (Simulator)

**Goal**: Work on mobile UI without Bluetooth/glasses

**Time**: 15 minutes

**Prerequisites**: Backend running (see Path 1)

```bash
# 1. Navigate to mobile directory
cd mobile

# 2. Install dependencies
npm ci

# 3. Start Expo dev server
npm start

# 4. Run on simulator
npm run ios  # or: npm run android
```

See [Mobile App Setup](#mobile-app-setup) for details.

---

### Path 3: Full Stack with iPhone & Meta Glasses

**Goal**: Test complete hands-free experience with real hardware

**Time**: 30-45 minutes

**Prerequisites**: 
- Physical iPhone
- Meta AI Glasses (paired with iPhone)
- Backend running

```bash
# 1. Setup backend (Path 1)
# 2. Build mobile app with native modules
cd mobile
npx expo run:ios --device

# 3. Configure Bluetooth audio routing
# 4. Test voice commands → TTS through glasses
```

See [iPhone & Meta Glasses Testing](#iphone--meta-glasses-testing) for details.

---

## Backend Setup

### Step 1: Clone and Install

```bash
# Clone repository
git clone https://github.com/endomorphosis/lift_coding.git
cd lift_coding

# Install Python dependencies
make deps

# Or manually:
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

### Step 2: Configure Environment

Create a `.env` file (or use `.env.example`):

```bash
# Copy example environment
cp .env.example .env

# Edit .env with your settings
```

**Minimal Configuration (Dev Mode)**:

```bash
# Authentication
HANDSFREE_AUTH_MODE=dev

# TTS/STT (stub = no API keys needed)
HANDSFREE_TTS_PROVIDER=stub
HANDS_FREE_STT_PROVIDER=stub

# GitHub (fixture = uses sample data)
GITHUB_LIVE_MODE=false

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Production/Realistic Configuration**:

```bash
# Authentication
HANDSFREE_AUTH_MODE=api_key

# TTS/STT (requires OpenAI API key)
HANDSFREE_TTS_PROVIDER=openai
HANDS_FREE_STT_PROVIDER=openai
OPENAI_API_KEY=sk-...

# GitHub (requires personal access token)
GITHUB_LIVE_MODE=true
GITHUB_TOKEN=ghp_...

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Step 3: Start Services

```bash
# Start Redis
make compose-up

# Or manually with docker compose:
docker compose up -d
```

### Step 4: Start Backend Server

```bash
# Using Makefile
make dev

# Or manually:
uvicorn handsfree.api:app --host 0.0.0.0 --port 8080 --reload
```

### Step 5: Verify Backend

```bash
# Check status
curl http://localhost:8080/v1/status

# Expected response:
# {
#   "status": "ok",
#   "version": "0.1.0",
#   "stt_provider": "stub",
#   "tts_provider": "stub"
# }

# Test TTS endpoint
curl -X POST http://localhost:8080/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "alloy", "format": "wav"}' \
  --output test.wav

# Test command endpoint
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"type": "text", "text": "show my inbox"},
    "profile": "dev"
  }'
```

**✅ Backend is ready when all three tests pass!**

---

## Mobile App Setup

### Step 1: Install Node Dependencies

```bash
cd mobile
npm ci
```

### Step 2: Configure Backend URL

For iOS Simulator (connecting to localhost):

```javascript
// Already configured by default in src/api/config.js
export const BASE_URL = 'http://localhost:8080';
```

For Android Emulator:

```javascript
// Edit src/api/config.js
export const BASE_URL = 'http://10.0.2.2:8080';
```

For Physical Device (on same network):

```javascript
// Edit src/api/config.js
// Replace with your computer's local IP
export const BASE_URL = 'http://192.168.1.100:8080';
```

You can also configure this in the app's Settings screen after launching.

### Step 3: Start Expo Development Server

```bash
npm start
```

This will:
- Start the Expo development server
- Show a QR code
- Display menu options (press `i` for iOS, `a` for Android)

### Step 4: Run on Simulator

**iOS Simulator** (macOS only):

```bash
npm run ios
```

**Android Emulator**:

```bash
npm run android
```

### Step 5: Run on Physical Device

**Option A: Using Expo Go** (Limited - no Bluetooth/native modules)

1. Install [Expo Go](https://expo.dev/go) app on your device
2. Scan QR code from `npm start`
3. Update BASE_URL to use your computer's IP
4. Note: Native Bluetooth features won't work in Expo Go

**Option B: Development Build** (Full features - includes native modules)

```bash
# Build and install on iOS device
npx expo run:ios --device

# Build and install on Android device
npx expo run:android --device
```

See [mobile/BUILD.md](mobile/BUILD.md) for detailed build instructions.

### Step 6: Verify Mobile App

1. **Status Tab**: Check that backend shows "Connected"
2. **Command Tab**: Send a test command ("show my inbox")
3. **Settings Tab**: Verify User ID and Backend URL

**✅ Mobile app is ready when you can send commands and see responses!**

---

## iPhone & Meta Glasses Testing

This section covers the complete setup for hands-free voice interaction with Meta AI Glasses.

### Prerequisites

- ✅ Backend server running and accessible from iPhone
- ✅ Physical iPhone (iOS 15+)
- ✅ Meta AI Glasses (Ray-Ban Meta or compatible)
- ✅ Glasses paired with iPhone via Bluetooth
- ✅ Development build of mobile app (not Expo Go)

### Step 1: Pair Meta Glasses with iPhone

**Initial Pairing**:

1. Open **Settings** app on iPhone
2. Navigate to **Bluetooth**
3. Turn on Meta AI Glasses (hold power button until LED flashes)
4. Wait for "Ray-Ban Meta..." to appear in available devices
5. Tap to pair
6. Confirm pairing on both devices

**Verify Connection**:

- In Settings → Bluetooth
- Status should show **"Connected"** next to glasses

**Alternative**: Use Meta View app for pairing (ensures firmware is up to date)

### Step 2: Build Mobile App with Native Modules

The native Bluetooth audio modules require a development build (not Expo Go):

```bash
cd mobile

# iOS - Build and install on device
npx expo run:ios --device

# This will:
# - Generate native iOS project
# - Install CocoaPods dependencies
# - Build the app
# - Install on connected iPhone
```

See [mobile/BUILD.md](mobile/BUILD.md) for troubleshooting build issues.

### Step 3: Configure Audio Routing

**Critical**: iOS must route audio output to glasses for TTS playback.

1. **Test Audio Routing**:
   - Open Music app or YouTube on iPhone
   - Play any audio
   - Listen to confirm audio comes from **glasses speakers**, not iPhone speaker

2. **If Audio Plays on iPhone Speaker**:
   - Open **Control Center** (swipe down from top-right)
   - Long-press the audio card
   - Tap the **audio output icon** (triangle with circles)
   - Select **"Ray-Ban Meta..."** from the list
   - Verify audio switches to glasses

3. **Verify Route Persists**:
   - Play audio again
   - Confirm it still plays through glasses
   - Route should persist until glasses disconnect

### Step 4: Configure Backend URL

In the mobile app:

1. Navigate to **Settings** tab
2. Enter backend URL: `http://YOUR_COMPUTER_IP:8080`
3. Example: `http://192.168.1.100:8080`
4. Tap **Save Settings**
5. Verify connection indicator shows green/connected

**Finding Your Computer's IP**:

```bash
# macOS/Linux
ifconfig | grep "inet "

# Windows
ipconfig
```

### Step 5: Grant Permissions

When prompted, grant these permissions:

- **Microphone**: Allow (required for voice commands)
- **Bluetooth**: Allow (required for glasses connection)
- **Notifications**: Allow (optional, for push notifications)

### Step 6: Test Voice Commands

**Test 1: Simple Command**

1. Open mobile app → **Command** tab
2. Tap **"🎤 Start Recording"**
3. Speak: "Show my inbox"
4. Tap **"⏹ Stop"**
5. Tap **"Send Audio"**
6. Wait for response
7. **Verify**: TTS response plays through **glasses speakers**

**Test 2: PR Summary**

1. Record command: "Summarize PR 123"
2. **Verify**: Response plays through glasses
3. **Verify**: UI shows PR card

**Test 3: Navigation**

1. Record command: "Next"
2. **Verify**: Different item is spoken
3. Record command: "Repeat"
4. **Verify**: Same item is spoken again

### Step 7: Verify Bluetooth Audio

In the mobile app's **Glasses** tab (diagnostics):

1. **Check Status**:
   - Connection State: "✓ Bluetooth Connected"
   - Audio Route: Shows "Ray-Ban Meta..."

2. **Test Recording**:
   - Tap "🎤 Start Recording"
   - Speak into glasses microphone
   - Verify recording captures audio

3. **Test Playback**:
   - Tap "▶️ Play Last Recording"
   - Verify audio plays through glasses speakers

**✅ iPhone & Meta Glasses integration is working when:**
- Voice commands are captured via phone mic (or glasses mic in native mode)
- TTS responses play through glasses speakers
- Bluetooth connection remains stable
- No audio routing issues occur

---

## Verification & Testing

### Backend Health Checks

```bash
# 1. Status endpoint
curl http://localhost:8080/v1/status

# 2. TTS generation
curl -X POST http://localhost:8080/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Test", "voice": "alloy", "format": "wav"}' \
  --output test.wav

# 3. Command processing
curl -X POST http://localhost:8080/v1/command \
  -H "Content-Type: application/json" \
  -d '{"input": {"type": "text", "text": "show my inbox"}}'
```

### Mobile App Testing

**Smoke Test Checklist**:

- [ ] Status screen shows backend connected
- [ ] Can send text command and receive response
- [ ] Can record audio command
- [ ] Can send audio command and receive response
- [ ] TTS audio plays correctly
- [ ] Settings persist after app restart
- [ ] Push notifications are received (if configured)

### iPhone & Glasses Testing

**Integration Test Checklist**:

- [ ] Glasses paired and connected
- [ ] Audio routes to glasses speakers
- [ ] Voice commands are captured
- [ ] TTS plays through glasses
- [ ] Bluetooth connection remains stable
- [ ] Audio routing persists across app restarts
- [ ] No echo or feedback issues

### Run Automated Tests

```bash
# Backend tests
make test

# Or manually:
pytest tests/

# Mobile tests (if configured)
cd mobile
npm test
```

---

## Next Steps

### For Backend Developers

1. Review [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow
2. Explore [implementation_plan/](implementation_plan/) for design docs
3. Check [spec/openapi.yaml](spec/openapi.yaml) for API reference
4. Read [docs/agent-runner-setup.md](docs/agent-runner-setup.md) for agent delegation

### For Mobile Developers

1. Review [mobile/README.md](mobile/README.md) for app architecture
2. Check [mobile/BUILD.md](mobile/BUILD.md) for native module development
3. Explore [mobile/glasses/](mobile/glasses/) for Bluetooth implementation
4. Read [docs/mobile-client-integration.md](docs/mobile-client-integration.md)

### For Testing with Meta Glasses

1. Review [docs/meta-ai-glasses.md](docs/meta-ai-glasses.md) for integration guide
2. Check [docs/ios-rayban-mvp1-runbook.md](docs/ios-rayban-mvp1-runbook.md) for demo runbook
3. Read [docs/ios-rayban-troubleshooting.md](docs/ios-rayban-troubleshooting.md) for common issues
4. See [docs/meta-ai-glasses-audio-routing.md](docs/meta-ai-glasses-audio-routing.md) for technical details

### For Agents/Autonomous Development

1. Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design (see below)
2. Check [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for auth flows
3. Explore API endpoints in [spec/openapi.yaml](spec/openapi.yaml)
4. Read [SECURITY.md](SECURITY.md) for security considerations

---

## Troubleshooting

### Backend Won't Start

**Symptom**: `uvicorn` command fails or server crashes on startup

**Solutions**:

1. **Check Python version**:
   ```bash
   python --version  # Should be 3.11+
   ```

2. **Reinstall dependencies**:
   ```bash
   make deps
   # Or: pip install -e . && pip install -r requirements-dev.txt
   ```

3. **Check Redis is running**:
   ```bash
   docker ps | grep redis
   # Should show redis container running
   ```

4. **Check port 8080 is not in use**:
   ```bash
   lsof -i :8080  # macOS/Linux
   netstat -an | grep 8080  # Windows
   ```

### Mobile App Can't Connect to Backend

**Symptom**: Status screen shows "Connection failed" or timeout

**Solutions**:

1. **Verify backend is running**:
   ```bash
   curl http://localhost:8080/v1/status
   ```

2. **Check backend URL in app Settings**:
   - iOS Simulator: `http://localhost:8080`
   - Android Emulator: `http://10.0.2.2:8080`
   - Physical Device: `http://YOUR_COMPUTER_IP:8080`

3. **Check firewall**:
   ```bash
   # macOS
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --listapps
   
   # Linux
   sudo ufw allow 8080/tcp
   ```

4. **Ensure backend binds to all interfaces**:
   ```bash
   uvicorn handsfree.api:app --host 0.0.0.0 --port 8080
   ```

### Audio Plays on iPhone Speaker Instead of Glasses

**Symptom**: TTS audio comes from iPhone, not glasses

**Solutions**:

1. **Manually set audio route**:
   - Open Control Center
   - Long-press audio card
   - Select "Ray-Ban Meta..."

2. **Verify Bluetooth connection**:
   - Settings → Bluetooth
   - Ensure glasses show "Connected"

3. **Restart iOS app**:
   - Force quit app
   - Relaunch
   - Audio route should initialize correctly

4. **Re-pair glasses** (last resort):
   - Settings → Bluetooth → Forget device
   - Pair again from scratch

### Voice Commands Return Stub/Placeholder Text

**Symptom**: Transcripts show "This is a stub transcript"

**Solutions**:

1. **Check STT provider**:
   ```bash
   curl http://localhost:8080/v1/status
   # Look for "stt_provider": "stub"
   ```

2. **Switch to OpenAI STT**:
   ```bash
   export HANDS_FREE_STT_PROVIDER=openai
   export OPENAI_API_KEY=sk-...
   # Restart backend
   ```

3. **Alternative**: Use text input instead of voice in mobile app

### Native Module Not Available

**Symptom**: Error: "Native module not available" in Glasses tab

**Solutions**:

1. **Build development client** (not Expo Go):
   ```bash
   cd mobile
   npx expo run:ios --device
   ```

2. **Verify native module**:
   - Check `modules/expo-glasses-audio/` exists
   - Verify CocoaPods installed: `cd ios && pod install`

3. **Clean and rebuild**:
   ```bash
   cd mobile/ios
   rm -rf build/ Pods/ Podfile.lock
   pod install
   cd ..
   npx expo run:ios --device
   ```

For more troubleshooting, see:
- [docs/ios-rayban-troubleshooting.md](docs/ios-rayban-troubleshooting.md)
- [mobile/README.md](mobile/README.md) - Troubleshooting section
- [GitHub Issues](https://github.com/endomorphosis/lift_coding/issues)

---

## Getting Help

- **Documentation**: Check [docs/](docs/) directory for detailed guides
- **Issues**: Search or open [GitHub Issues](https://github.com/endomorphosis/lift_coding/issues)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
- **Security**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

---

**Ready to build hands-free development experiences? Let's go! 🚀**
