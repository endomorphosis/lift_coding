# HandsFree Mobile Companion App

React Native/Expo mobile app for hands-free GitHub operations through voice commands and Meta AI Glasses integration.

## 📱 Features

### Core Functionality
- **Voice Commands**: Record and send voice commands to backend
- **Text Commands**: Type commands for quick testing
- **TTS Playback**: Hear responses through phone or Bluetooth device
- **Push Notifications**: Real-time updates with auto-speaking (optional)
- **Confirmation Flow**: Safe confirmation for destructive operations

### Meta AI Glasses Integration
- **Bluetooth Audio Routing**: Route audio to/from glasses
- **Native Recording**: Capture audio from glasses microphone
- **Native Playback**: Play TTS through glasses speakers
- **Real-time Monitoring**: Audio route change detection
- **Diagnostics Screen**: Test and debug Bluetooth connectivity

### Developer Features
- **In-App Settings**: Configure backend URL and user ID
- **Debug Panel**: View request/response details
- **Audio Upload**: Dev endpoint for audio testing
- **Auto-play TTS**: Toggle automatic TTS playback

## 🚀 Quick Start

Choose your path based on what you want to test:

### Path 1: Basic Testing (Expo Go)

**Best for**: UI testing without Bluetooth features

**Time**: 5 minutes

```bash
cd mobile
npm ci
npm start
# Scan QR code with Expo Go app
```

**⚠️ Limitations**: Native Bluetooth features won't work in Expo Go

---

### Path 2: Simulator Testing

**Best for**: Full feature testing without hardware

**Time**: 10 minutes

```bash
cd mobile
npm ci

# iOS Simulator (macOS only)
npm run ios

# Android Emulator
npm run android
```

**⚠️ Limitations**: No Bluetooth, no physical device features

---

### Path 3: Full Hardware Testing

**Best for**: Complete iPhone + Meta Glasses integration

**Time**: 30 minutes

**Requirements**:
- Physical iPhone (iOS 15+)
- Meta AI Glasses (optional but recommended)
- Backend accessible from iPhone

```bash
cd mobile

# Build development client with native modules
npx expo run:ios --device

# Follow on-screen instructions
```

See [iPhone & Glasses Testing](#iphone--meta-glasses-testing) section for complete setup.

---

## 📋 Prerequisites

### For All Paths

- **Node.js** 18+ and npm
- **Expo CLI**: `npm install -g expo-cli`
- **Backend server** running and accessible

### For iOS Development

- macOS with **Xcode 14.0+**
- iOS Simulator or physical iPhone (iOS 15+)
- **Apple Developer account** (for device deployment)

### For Android Development

- **Android Studio**
- Android Emulator or physical device
- **JDK 17**

### For iPhone & Meta Glasses Testing

- **Physical iPhone** (iOS 15+) - Simulator doesn't support Bluetooth
- **Meta AI Glasses** (Ray-Ban Meta or compatible)
- Glasses paired with iPhone via Bluetooth

---

## 🔧 Installation

### 1. Navigate to Mobile Directory

```bash
cd mobile
```

### 2. Install Dependencies

```bash
npm ci
```

### 3. Configure Backend URL

**Option A: In-App Settings** (Recommended)

1. Launch the app
2. Navigate to **Settings** tab
3. Enter backend URL (e.g., `http://192.168.1.100:8080`)
4. Tap **Save Settings**

**Option B: Configuration File**

Edit `src/api/config.js`:

```javascript
// iOS Simulator
export const BASE_URL = 'http://localhost:8080';

// Android Emulator
// export const BASE_URL = 'http://10.0.2.2:8080';

// Physical device on same network
// export const BASE_URL = 'http://192.168.1.100:8080';
```

**Finding Your Computer's IP**:

```bash
# macOS/Linux
ifconfig | grep "inet "

# Windows
ipconfig
```

---

## 🏃 Running the App

### Start Development Server

```bash
npm start
```

This will:
- Start Expo development server
- Show QR code and menu
- Display available options

### Run on Simulator

**iOS Simulator** (macOS only):

```bash
npm run ios
```

**Android Emulator**:

```bash
npm run android
```

### Run on Physical Device

**Option 1: Expo Go** (Limited Features)

1. Install [Expo Go](https://expo.dev/go) on your device
2. Scan QR code from `npm start`
3. ⚠️ Native Bluetooth features won't work

**Option 2: Development Build** (Full Features)

```bash
# Build and install on iOS device
npx expo run:ios --device

# Build and install on Android device
npx expo run:android --device
```

For detailed build instructions, see [BUILD.md](BUILD.md).

---

## 📱 App Screens

### Status Screen

- View backend connection status
- Check API version
- Verify authentication

### Command Screen

**Text Commands**:
- Type command (e.g., "show my inbox")
- Send to backend
- View response with TTS

**Voice Commands**:
- 🎤 Record audio
- ⏹ Stop recording
- 📤 Send to backend
- 🔊 Auto-play TTS response (optional)

**Features**:
- Debug panel (toggle on/off)
- Manual TTS control
- Response cards display

### Confirmation Screen

- View pending actions requiring confirmation
- Confirm, cancel, or repeat actions
- Enter action ID from previous command

### TTS Screen

- Test text-to-speech generation
- Enter text and generate audio
- Play through current audio output

### Settings Screen

- **Backend URL**: Configure server address
- **User ID**: Set user identifier
- **Generate UUID**: Create random user ID
- **Notification Settings**: Toggle auto-speaking
- Persists across app restarts

### Glasses Diagnostics Screen

**Status Information**:
- Bluetooth connection state
- Audio input/output devices
- Real-time route monitoring

**Testing Tools**:
- 🎤 Record from Bluetooth mic
- ▶️ Play last recording
- 🚀 Send to backend and process
- 🔄 Refresh audio route status

**Dev Mode Toggle**:
- ON: Use phone mic/speaker (fast testing)
- OFF: Use Bluetooth audio (real glasses)

---

## 🎧 iPhone & Meta Glasses Testing

### Complete Setup Guide

**See**: [docs/ios-rayban-mvp1-runbook.md](../docs/ios-rayban-mvp1-runbook.md) for the complete, step-by-step runbook.

### Quick Overview

#### 1. Pair Glasses with iPhone

1. Open **Settings** → **Bluetooth**
2. Turn on Meta AI Glasses
3. Tap "Ray-Ban Meta..." to pair
4. Verify status shows "Connected"

#### 2. Build Native Development Client

```bash
cd mobile
npx expo run:ios --device
```

This builds the app with native Bluetooth modules.

#### 3. Configure Audio Routing

1. Play test audio (Music app)
2. Open **Control Center**
3. Long-press audio card
4. Select "Ray-Ban Meta..." as output
5. Verify audio plays through glasses

#### 4. Test Voice Commands

1. Open app → **Command** tab
2. Tap **🎤 Start Recording**
3. Speak: "Show my inbox"
4. Tap **⏹ Stop** → **Send Audio**
5. **Verify**: Response plays through glasses

#### 5. Verify Bluetooth Integration

1. Navigate to **Glasses** tab
2. Check status: "✓ Bluetooth Connected"
3. Test recording from glasses mic
4. Test playback through glasses speakers

### Troubleshooting

**Audio plays on phone instead of glasses**:
- Manually set audio route in Control Center
- Restart iOS app
- Reconnect glasses via Bluetooth settings

**Native module not available**:
- Build with `npx expo run:ios --device` (not Expo Go)
- Clean and rebuild if necessary

**Bluetooth connection unstable**:
- Check glasses battery level
- Reduce Bluetooth interference
- Keep phone within 1-2 meters of glasses

For comprehensive troubleshooting, see [docs/ios-rayban-troubleshooting.md](../docs/ios-rayban-troubleshooting.md).

---

## 🧪 Testing

### Smoke Test: Voice Command Flow

**Purpose**: Verify complete audio → command → TTS pipeline

**Prerequisites**:
- Backend running with `HANDSFREE_AUTH_MODE=dev`
- Mobile app with microphone permissions
- Audio playback enabled

**Steps**:

1. **Navigate to Command screen**
2. **Enable settings**:
   - Toggle "Auto-play TTS" ON
   - Toggle "Show Debug Panel" ON (optional)
3. **Record command**:
   - Tap "🎤 Start Recording"
   - Speak: "Show my inbox"
   - Tap "⏹ Stop"
4. **Send command**:
   - Tap "Send Audio"
   - Wait for upload and processing
5. **Verify response**:
   - ✅ Response appears with spoken text
   - ✅ TTS auto-plays
   - ✅ Audio plays through correct device (glasses if connected)
   - ✅ No errors in debug panel

**Expected Result**: Complete voice → text → response → audio flow works end-to-end

### Smoke Test: Push Notifications

**Purpose**: Verify push notifications are received and auto-spoken

**Prerequisites**:
- Physical device (push notifications don't work in simulator)
- Backend with push notifications configured
- "Speak notifications" enabled in Settings

**Steps**:

1. **Verify settings**:
   - Navigate to Settings tab
   - Check "Speak notifications" is ON
2. **Trigger test notification**:
   ```bash
   curl -X POST http://localhost:8080/v1/dev/send-test-notification \
     -H "Content-Type: application/json" \
     -H "X-User-ID: YOUR_USER_ID" \
     -d '{"message": "Test notification"}'
   ```
3. **Verify foreground behavior**:
   - App receives notification
   - TTS auto-plays notification text
   - Banner appears at top of screen

**Expected Result**: Notification is received and automatically spoken

For more tests, see [PUSH_NOTIFICATIONS_TESTING.md](PUSH_NOTIFICATIONS_TESTING.md)

---

## 🏗️ Project Structure

```
mobile/
├── src/
│   ├── api/                      # Backend API client
│   │   ├── config.js            # Configuration (BASE_URL, auth)
│   │   └── client.js            # API methods
│   │
│   ├── screens/                 # App screens (navigation)
│   │   ├── StatusScreen.js      # Backend status check
│   │   ├── CommandScreen.js     # Voice/text commands
│   │   ├── ConfirmationScreen.js
│   │   ├── TTSScreen.js
│   │   ├── SettingsScreen.js
│   │   └── GlassesDiagnosticsScreen.js
│   │
│   ├── components/              # Reusable UI components
│   │   ├── AudioRecorder.js
│   │   ├── AudioPlayer.js
│   │   └── NotificationBanner.js
│   │
│   └── utils/                   # Utilities
│       ├── storage.js           # AsyncStorage wrapper
│       ├── permissions.js
│       └── bluetooth.js
│
├── modules/                     # Native modules
│   └── expo-glasses-audio/      # Bluetooth audio routing
│       ├── ios/                 # Swift native code
│       │   ├── ExpoGlassesAudioModule.swift
│       │   ├── AudioRouteMonitor.swift
│       │   ├── GlassesRecorder.swift
│       │   └── GlassesPlayer.swift
│       ├── android/             # Kotlin native code
│       └── index.ts             # TypeScript interface
│
├── assets/                      # Images, fonts, etc.
├── App.js                       # Root component
├── index.js                     # Entry point
├── app.json                     # Expo configuration
├── package.json                 # Dependencies
├── BUILD.md                     # Native build instructions
└── README.md                    # This file
```

---

## 🔌 API Integration

### Backend Endpoints

The app integrates with these backend endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/status` | GET | Health check |
| `/v1/command` | POST | Process command |
| `/v1/commands/confirm` | POST | Confirm action |
| `/v1/tts` | POST | Generate TTS audio |
| `/v1/dev/audio` | POST | Upload audio (dev only) |
| `/v1/notifications` | GET | List notifications |
| `/v1/notifications/subscriptions` | POST | Register device |

### Command Request Example

```javascript
const response = await fetch(`${BASE_URL}/v1/command`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-User-ID': userId,
  },
  body: JSON.stringify({
    input: {
      type: 'audio',
      uri: 'file:///path/to/audio.m4a',
      format: 'm4a',
      duration_ms: 3000
    },
    profile: 'terse',
    client_context: {
      device_type: 'mobile',
      app_version: '1.0.0'
    }
  })
});

const data = await response.json();
// {
//   status: 'success',
//   intent: 'inbox.summary',
//   spoken_text: 'You have 3 PRs...',
//   ui_cards: [...]
// }
```

For detailed API documentation, see [../spec/openapi.yaml](../spec/openapi.yaml)

---

## 🔐 Authentication

The app supports session-based authentication:

### X-User-ID Header (Dev Mode)

```javascript
headers: {
  'X-User-ID': 'your-user-id'
}
```

- Set via Settings screen
- Stored in AsyncStorage
- Automatically included in all requests

### Bearer Token (Production)

```javascript
headers: {
  'Authorization': 'Bearer YOUR_API_KEY'
}
```

- API key generated via backend
- Stored securely (future: Keychain/Keystore)

For authentication setup, see [../docs/AUTHENTICATION.md](../docs/AUTHENTICATION.md)

---

## 📚 Additional Documentation

### Core Documentation
- **[Getting Started](../GETTING_STARTED.md)** - Complete setup guide
- **[Architecture](../ARCHITECTURE.md)** - System design
- **[Configuration](../CONFIGURATION.md)** - Environment variables

### Mobile-Specific
- **[Build Instructions](BUILD.md)** - Native module development
- **[Meta Glasses Integration](../docs/meta-ai-glasses.md)** - Bluetooth audio guide
- **[Mobile Client Integration](../docs/mobile-client-integration.md)** - API usage patterns

### iPhone & Glasses Testing
- **[MVP1 Runbook](../docs/ios-rayban-mvp1-runbook.md)** - Complete testing guide
- **[Troubleshooting](../docs/ios-rayban-troubleshooting.md)** - Common issues
- **[Audio Routing](../docs/meta-ai-glasses-audio-routing.md)** - Technical details

---

## 🐛 Troubleshooting

### Can't Connect to Backend

**Symptom**: Status screen shows "Connection failed"

**Solutions**:
1. Verify backend is running: `curl http://localhost:8080/v1/status`
2. Check backend URL in Settings:
   - iOS Simulator: `http://localhost:8080`
   - Android Emulator: `http://10.0.2.2:8080`
   - Physical Device: `http://YOUR_COMPUTER_IP:8080`
3. Check firewall settings
4. Ensure backend binds to `0.0.0.0` not `127.0.0.1`

### Audio Not Playing

**Symptom**: TTS response doesn't play

**Solutions**:
1. Check device volume
2. Verify backend TTS is configured (OpenAI API key)
3. Check audio format compatibility
4. Try toggling "Auto-play TTS" off/on
5. Manually tap "🔊 Play TTS" button

### Native Module Not Available

**Symptom**: "Native module not available" error in Glasses tab

**Solutions**:
1. Build development client:
   ```bash
   npx expo run:ios --device
   ```
2. Clean and rebuild:
   ```bash
   cd ios
   rm -rf build/ Pods/ Podfile.lock
   pod install
   cd ..
   npx expo run:ios --device
   ```
3. Verify you're NOT using Expo Go

### Bluetooth Audio Routing Issues

**Symptom**: Audio plays on phone instead of glasses

**Solutions**:
1. Manually set audio route in Control Center
2. Restart iOS app
3. Toggle Bluetooth off/on
4. Re-pair glasses if necessary

**See**: [../docs/ios-rayban-troubleshooting.md](../docs/ios-rayban-troubleshooting.md) for comprehensive troubleshooting

---

## 🚀 Next Steps

### Planned Features

- [ ] Production audio upload (pre-signed URLs, S3)
- [ ] Secure credential storage (Keychain/Keystore)
- [ ] Biometric authentication
- [ ] Offline mode with queue sync
- [ ] Multiple user profiles
- [ ] Voice customization (speed, voice selection)

### Contributing

See the main repository [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on:
- Development workflow
- Code style
- Testing requirements
- PR process

---

## 📄 License

See [LICENSE](../LICENSE) in the repository root.

---

**Mobile App Documentation Version**: 1.0  
**Last Updated**: 2026-01-20

## Development Workflow

### 1. Check Backend Status

Open the app and navigate to the **Status** tab. This will show:
- Backend connectivity status
- API version
- User ID (if authenticated)

### 2. Send Commands

Navigate to the **Command** tab:

#### Text Commands
- Enter a text command (e.g., "what's in my inbox?")
- Tap "Send Command"
- View the response including:
  - Spoken text
  - UI cards
  - Confirmation requirement (if needed)

#### Audio Commands (Dev Mode)
The Command screen now supports recording and sending audio commands with automatic TTS playback:
- Tap "🎤 Start Recording" to begin recording
- Speak your command
- Tap "⏹ Stop" to end recording
- Review duration and file size
- Tap "Send Audio" to upload and submit as a command
- Or tap "Discard" to delete the recording and start over

The audio flow:
1. Records audio using the device microphone
2. Encodes as base64
3. Uploads to `POST /v1/dev/audio` (dev endpoint)
4. Receives a `file://` URI
5. Submits to `POST /v1/command` with `input.type=audio`
6. Displays the command response
7. **Automatically plays TTS response** (if enabled)

**Features:**
- **Auto-play TTS**: Toggle to automatically play text-to-speech for responses
- **Debug Panel**: Toggle to show/hide detailed debug information (status, intent, debug data)
- **Manual TTS Control**: Play button to manually trigger TTS playback when auto-play is off
- **Enhanced Error Messages**: Clear error messages with hints for common issues (backend unreachable, dev mode disabled, etc.)

**Note:** Audio commands require the backend dev endpoint to be enabled (`HANDSFREE_AUTH_MODE=dev`).

### 3. Confirm Actions

If a command requires confirmation:
- Note the `action_id` from the command response
- Navigate to the **Confirm** tab
- Enter the action ID
- Choose: Confirm, Cancel, Repeat, or Next

### Configure Settings (Optional)

Navigate to the **Settings** tab:
- Set a custom **User ID** (used in X-User-ID header)
- Generate a random UUID if needed
- Configure a custom **Backend URL** (useful for testing against different environments)
- **Speak notifications** toggle: Enable/disable automatic speaking of push notifications
  - Defaults to ON in development builds, OFF in production
  - When enabled, push notifications are automatically spoken via TTS through the selected audio output (glasses when connected)
- Changes are saved to local storage and persist across app restarts

### 5. Push Notifications

The app supports push notification delivery and automatic speaking of notifications.

#### Setup
1. Ensure the backend has push notification provider configured (Expo)
2. The app automatically requests notification permissions on physical devices
3. Push tokens are registered with the backend at app launch

#### Foreground Behavior
- When a push notification arrives while the app is in the foreground:
  - The notification is received by the app
  - If "Speak notifications" is enabled in Settings, the notification text is automatically fetched and spoken via TTS
  - Audio is played through the current audio output (glasses when connected, phone speaker otherwise)
  - The notification is displayed as a banner at the top of the screen

#### Background Behavior
- When a push notification arrives while the app is in the background:
  - On **iOS**: The system displays the notification, but background execution is limited. The app may not be able to speak the notification automatically due to iOS background restrictions.
  - On **Android**: The system displays the notification. Background task limitations may prevent automatic TTS playback.
  - When the user taps on the notification, the app opens and the notification can be spoken if the toggle is enabled.

**Platform Limitations:**
- iOS restricts background audio playback and task execution for push notifications
- Android has similar restrictions depending on the device's power-saving settings
- For reliable auto-speaking, notifications should arrive while the app is in the foreground
- Background behavior depends on OS version and device settings

#### Configuring Notification Speech
Navigate to **Settings** → **Notifications**:
- Toggle "Speak notifications" ON/OFF
- When disabled, notifications are still received but not automatically spoken
- This is useful if you prefer silent notifications or want to manually check them

### 6. Test TTS

Navigate to the **TTS** tab:
- Enter text to convert to speech
- Tap "Fetch & Play"
- The app will fetch audio from the backend and play it

## Smoke Test: Audio Command Flow with TTS Playback

This test verifies the complete audio capture, command submission, and TTS playback pipeline.

## Smoke Test: Push Notification Auto-Speaking

This test verifies that push notifications are automatically spoken when received.

### Prerequisites
- Backend running with push notification provider configured
- Mobile app running on a physical device (push notifications don't work in simulators)
- Notification permissions granted
- "Speak notifications" toggle enabled in Settings (default ON in dev builds)

### Test Steps

1. **Start the mobile app on a physical device**
   ```bash
   cd mobile
   npx expo start
   # Use Expo Go app or development build
   ```

2. **Verify Settings**
   - Navigate to **Settings** tab
   - Check that "Speak notifications" is enabled (toggle should be ON)
   - Note your User ID

3. **Trigger a test notification from backend**
   ```bash
   # From backend terminal, send a test notification
   curl -X POST http://localhost:8080/v1/dev/send-test-notification \
     -H "Content-Type: application/json" \
     -H "X-User-ID: YOUR_USER_ID" \
     -d '{"message": "Test notification from backend"}'
   ```

4. **Verify foreground behavior**
   - With the app in the foreground, trigger a notification
   - You should hear the notification spoken via TTS
   - Audio should play through the current audio output (glasses if connected)
   - A notification banner should appear at the top of the screen

5. **Test the toggle**
   - Navigate to **Settings** and disable "Speak notifications"
   - Trigger another notification
   - Verify that it is NOT spoken (silent notification)
   - Re-enable the toggle and test again

6. **Document background behavior** (informational only)
   - Send the app to background (press home button)
   - Trigger a notification
   - Note: iOS and Android have limitations on background TTS playback
   - Notification will display, but may not be automatically spoken
   - Tapping the notification should open the app

### Expected Results
- ✅ Foreground notifications are spoken automatically when toggle is ON
- ✅ Notifications are silent when toggle is OFF
- ✅ Audio routes through selected output (glasses when connected)
- ⚠️ Background notifications may not be spoken due to platform limitations

### Common Issues
- **No sound**: Check device volume, verify backend TTS is configured
- **Notifications not received**: Check notification permissions, verify push token is registered
- **Background speaking not working**: This is expected due to iOS/Android limitations

#### Standard Development (Expo Go)

For basic testing without native Bluetooth features:

```bash
cd mobile
npm install
npm start
```

Then scan the QR code with Expo Go app on your device.

**Note**: Native Bluetooth audio features require a development build (see below).

### Development Build (Native Modules)

For testing Bluetooth audio with Meta AI Glasses:

```bash
cd mobile
./setup.sh
```

Then follow the build instructions in [BUILD.md](BUILD.md) to create a development client.

## Prerequisites
- Backend running on `http://localhost:8080` (or configured BASE_URL)
- Backend must have `HANDSFREE_AUTH_MODE=dev` enabled
- Mobile app running on simulator/device
- Microphone permissions granted
- Audio playback permissions granted

### Test Steps

1. **Start the mobile app**
   ```bash
   cd mobile
   npm start
   # Then press 'i' for iOS or 'a' for Android
   ```

2. **Navigate to Command screen**
   - Open the app
   - Tap the "Command" tab

3. **Configure dev settings** (top of screen)
   - Verify "Show Debug Panel" is ON
   - Verify "Auto-play TTS" is ON

4. **Record an audio command**
   - Tap "🎤 Start Recording"
   - Speak a command (e.g., "What's in my inbox?")
   - Tap "⏹ Stop"
   - Verify duration and file size are displayed

5. **Submit the audio command**
   - Tap "Send Audio"
   - Wait for upload and processing
   - Should see loading indicator

6. **Verify response and TTS playback**
   - Check that a response appears with:
     - Status field (if debug panel is on)
     - Intent field (if debug panel is on)
     - `spoken_text` field with the response
     - Optional `ui_cards`
     - No errors
   - **Verify TTS automatically starts playing** (🔊 Playing TTS... indicator should appear)
   - TTS audio should play through the device speaker
   - You can tap "⏹ Stop" to stop TTS playback early

7. **Test manual TTS control** (optional)
   - Toggle "Auto-play TTS" OFF
   - Send another command (text or audio)
   - Verify TTS does NOT auto-play
   - Verify a "🔊 Play TTS" button appears in the response
   - Tap the button to manually trigger TTS playback

### Expected Backend Logs
```
INFO: Wrote dev audio: dev/audio/{id}.m4a (XXXX bytes)
INFO: Processing audio command with uri: file://...
INFO: TTS request for text: ...
```

### Common Issues
- **"No audio recorded"**: Ensure you stopped recording before sending
- **"Upload failed" or 403 error**: Check backend is running with `HANDSFREE_AUTH_MODE=dev` and `/v1/dev/audio` endpoint is accessible
- **"Backend unreachable"**: Verify backend URL in settings, check network connectivity
- **Microphone permission denied**: Grant permissions in device settings
- **"Command failed"**: Check backend logs for audio processing errors
- **TTS not playing**: Check backend has TTS enabled, verify audio playback permissions, check device volume
- **No TTS response**: Backend may not have TTS configured or the command may not generate spoken_text

### Verifying the Dev Endpoint

Test the backend dev endpoint directly:
```bash
# Create a test audio file
echo "test" | base64 > /tmp/test_audio.b64

# Upload to dev endpoint
curl -X POST http://localhost:8000/v1/dev/audio \
  -H "Content-Type: application/json" \
  -d '{"data_base64": "'$(cat /tmp/test_audio.b64)'", "format": "m4a"}'

# Should return: {"uri": "file:///.../dev/audio/{id}.m4a", "format": "m4a"}
```

## Project Structure

```
mobile/
├── App.js                          # Main app with navigation
├── src/
│   ├── api/
│   │   ├── config.js              # API configuration (BASE_URL, auth)
│   │   └── client.js              # API client methods
│   ├── screens/
│   │   ├── StatusScreen.js        # Backend status check
│   │   ├── CommandScreen.js       # Send text commands
│   │   ├── ConfirmationScreen.js  # Confirm pending actions
│   │   ├── TTSScreen.js           # Text-to-speech playback
│   │   └── SettingsScreen.js      # Developer settings (User ID, URL)
│   └── components/                # Reusable components (future)
├── assets/                         # Images, fonts, etc.
├── package.json                    # Dependencies
└── README.md                       # This file
```

## API Integration

The app integrates with the following backend endpoints:

- `GET /v1/status` - Check backend status
- `POST /v1/command` - Send text or audio command
- `POST /v1/commands/confirm` - Confirm/cancel pending action
- `POST /v1/tts` - Fetch TTS audio
- `POST /v1/dev/audio` - Upload audio (dev only) and get file:// URI

### Audio Command Support

The app now supports sending audio commands via the `POST /v1/command` endpoint with:
```json
{
  "input": {
    "type": "audio",
    "uri": "file:///.../dev/audio/{id}.m4a",
    "format": "m4a",
    "duration_ms": 3000
  },
  "profile": "dev",
  "client_context": {
    "device_type": "mobile",
    "app_version": "1.0.0"
  }
}
```

See `src/api/client.js` for implementation details.

## Authentication

The app supports session-based authentication via:
- Bearer token in `Authorization` header
- User ID in `X-User-ID` header

### Setting User ID via Settings Screen

The easiest way to configure authentication:
1. Open the app and go to the **Settings** tab
2. Enter or generate a User ID
3. Tap "Save Settings"

The User ID will be automatically included in the `X-User-ID` header for all API requests.

### Programmatic Authentication

Alternatively, set credentials programmatically:

```javascript
import { setSession } from './src/api/config';
setSession('your-token', 'user-id');
```

Future: OAuth, API key auth, secure storage.

## Troubleshooting

### Cannot connect to backend

- Ensure backend is running: `curl http://localhost:8080/v1/status`
- Use the **Settings** tab in the app to configure the backend URL
- For Android Emulator, use `http://10.0.2.2:8080`
- For physical device, use your computer's IP address
- Check firewall settings

### Audio not playing

- Ensure `expo-av` is properly installed
- Check backend TTS configuration (OpenAI API key)
- Verify audio format compatibility
- Check device volume

### Native module issues (Glasses Audio)

**"Native module not available"**:
- You're using Expo Go instead of a development build
- Solution: Run `npx expo run:ios --device` to build with native modules
- See `BUILD.md` and `modules/expo-glasses-audio/` for details

**Bluetooth audio not routing correctly**:
- Check iOS permissions (Settings → Privacy → Bluetooth)
- Ensure Meta AI Glasses are paired and connected
- Try toggling DEV mode in Glasses Diagnostics screen
- Check console logs for AVAudioSession errors

### Dependencies issues

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

### Planned Features

- [x] Push notifications integration (`/v1/notifications/subscriptions`)
- [x] Auto-speak push notifications with toggle (Settings screen)
- [x] Audio input for voice commands (dev mode via `/v1/dev/audio`)
- [ ] Production audio upload (pre-signed URLs, object storage)
- [x] Bluetooth audio routing (Meta AI Glasses) - **iOS native module implemented**
- [ ] Secure credential storage (Keychain/Keystore)
- [ ] Biometric authentication
- [ ] Offline mode with queue
- [x] Settings screen (configure BASE_URL, User ID)

### iOS Native Audio Module

The app includes a native module (`expo-glasses-audio`) for Meta AI Glasses integration:

**Location**: `modules/expo-glasses-audio/`

**Features**:
- Real-time AVAudioSession monitoring
- Bluetooth audio route detection
- Native recording from Bluetooth mic
- Native playback through Bluetooth speakers
- Event-driven route change notifications

**Setup**:
See `BUILD.md` (dev-client builds) and the module package at `modules/expo-glasses-audio/`.

**Quick start**:
```bash
cd mobile
npm install expo-dev-client
npx expo run:ios --device
```

**Testing**:
1. Build development build with native module
2. Open app and navigate to "Glasses Diagnostics"
3. Connect Meta AI Glasses via Bluetooth
4. Toggle DEV mode off to use native Bluetooth routing
5. Observe real-time audio route information

### Production Readiness

Before production deployment:

1. **Security**:
   - Implement secure token storage
   - Use HTTPS for all API calls
   - Add certificate pinning

2. **Performance**:
   - Add request caching
   - Implement retry logic
   - Add error boundaries

3. **UX**:
   - Add loading states
   - Improve error messages
   - Add accessibility features

4. **Testing**:
   - Add unit tests
   - Add integration tests
   - Test on multiple devices

## Meta AI Glasses Audio Diagnostics

The **Glasses** tab provides comprehensive diagnostics for testing Bluetooth audio routing with Meta AI Glasses.

### Features

**DEV Mode vs Glasses Mode:**
- **DEV Mode** (toggle ON): Uses phone mic/speaker for rapid testing
- **Glasses Mode** (toggle OFF): Uses Bluetooth audio routing via native modules

**Audio Route Monitoring:**
- Real-time display of audio input/output devices
- Bluetooth connection status
- Automatic updates on route changes

**Recording & Playback:**
- 10-second audio recording from Bluetooth mic (or phone mic in DEV mode)
- Playback through Bluetooth speakers (or phone speaker in DEV mode)
- WAV file format with proper headers

**Backend Integration:**
- Upload recordings to `/v1/dev/audio`
- Send to `/v1/command` for processing
- Display backend responses

### Testing Bluetooth Audio

1. **Pair Meta AI Glasses** (or any Bluetooth headset) with your device
2. **Build development client** (see [BUILD.md](BUILD.md))
3. **Launch app** and navigate to Glasses tab
4. **Disable DEV Mode** (toggle should be OFF)
5. **Check Status**: Verify "✓ Bluetooth Connected"
6. **Record Audio**: Tap "Start Recording" and speak
7. **Play Back**: Tap "Play Last Recording" to hear through glasses
8. **Test Pipeline**: Tap "Send to Backend" to process command

### Troubleshooting

- **"Native module not available"**: Build a development client (not Expo Go)
- **"No Bluetooth Device"**: Ensure device is paired and connected in system settings
- **Audio routes to phone**: Check Bluetooth connection, may need to reconnect device

For detailed instructions, see:
- [BUILD.md](BUILD.md) - Development build setup
- [glasses/README.md](glasses/README.md) - Native implementation details
- [../docs/meta-ai-glasses-audio-routing.md](../docs/meta-ai-glasses-audio-routing.md) - Audio routing guide

## Contributing

See the main repository [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](../LICENSE) in the repository root.
