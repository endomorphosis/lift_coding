# Handsfree Mobile Companion App

React Native/Expo mobile app for interacting with the Handsfree backend.

## Features

- **Status Check**: View backend connectivity and status
- **Command Input**: Send text commands to the backend
- **Confirmation Flow**: Confirm/cancel/repeat/next pending actions
- **Text-to-Speech**: Fetch and play TTS audio from backend
- **Developer Settings**: Configure X-User-ID header and backend URL in-app
- **Glasses Diagnostics**: Test Meta AI Glasses audio routing (iOS native module)
  - Real-time Bluetooth audio route monitoring
  - Native recording from glasses microphone
  - Native playback through glasses speakers
  - Dev mode bypass for testing without glasses

## Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Expo CLI (installed globally: `npm install -g expo-cli`)
- iOS Simulator (macOS only) or Android Emulator
- Alternatively, use the Expo Go app on your physical device

## Backend Setup

Before running the mobile app, ensure the backend is running and accessible:

```bash
# From the repository root
cd /path/to/lift_coding

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
pip install -r requirements-dev.txt

# Set environment variables
export DATABASE_URL="sqlite:///./handsfree.db"
export SECRET_KEY="your-secret-key"
export OPENAI_API_KEY="your-openai-key"  # Optional, for TTS

# Run migrations
python -m handsfree.db.migrations

# Start the backend server
uvicorn handsfree.api:app --host 0.0.0.0 --port 8080
```

The backend should now be accessible at `http://localhost:8080`.

## Installation

1. Navigate to the mobile directory:

```bash
cd mobile
```

2. Install dependencies:

```bash
npm install
```

3. Configure the backend URL:

Edit `src/api/config.js` and update the `BASE_URL`:

```javascript
// For iOS Simulator connecting to localhost
export const BASE_URL = 'http://localhost:8080';

// For Android Emulator connecting to localhost
// export const BASE_URL = 'http://10.0.2.2:8080';

// For physical device on same network
// export const BASE_URL = 'http://YOUR_COMPUTER_IP:8080';
```

## Running the App

### Start the development server:

```bash
npm start
```

This will start the Expo development server and show a QR code.

### Run on iOS Simulator (macOS only):

```bash
npm run ios
```

### Run on Android Emulator:

```bash
npm run android
```

### Run on physical device:

1. **With Expo Go** (limited features):
   - Install the [Expo Go](https://expo.dev/go) app on your device
   - Scan the QR code shown in the terminal
   - Make sure your device is on the same network as your computer
   - Update `BASE_URL` in `src/api/config.js` to use your computer's local IP address
   - Note: Native modules (Glasses Audio) not available in Expo Go

2. **With Development Build** (full features, including native modules):
   ```bash
   # First time setup
   npm install expo-dev-client
   
   # Build and run on iOS
   npx expo run:ios --device
   
   # Build and run on Android
   npx expo run:android --device
   ```
   - This includes the native Glasses Audio module for Bluetooth support
   - See `modules/glasses-audio/SETUP.md` for detailed setup instructions

### Run in web browser:

```bash
npm run web
```

Note: Audio playback may have limited functionality in web mode.

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

### 4. Configure Settings (Optional)

Navigate to the **Settings** tab:
- Set a custom **User ID** (used in X-User-ID header)
- Generate a random UUID if needed
- Configure a custom **Backend URL** (useful for testing against different environments)
- Changes are saved to local storage and persist across app restarts

### 5. Test TTS

Navigate to the **TTS** tab:
- Enter text to convert to speech
- Tap "Fetch & Play"
- The app will fetch audio from the backend and play it

## Smoke Test: Audio Command Flow with TTS Playback

This test verifies the complete audio capture, command submission, and TTS playback pipeline.

### Prerequisites
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
  -d '{"audio_base64": "'$(cat /tmp/test_audio.b64)'", "format": "m4a"}'

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
- See `modules/glasses-audio/SETUP.md` for detailed instructions

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

- [ ] Push notifications integration (`/v1/notifications/subscriptions`)
- [x] Audio input for voice commands (dev mode via `/v1/dev/audio`)
- [ ] Production audio upload (pre-signed URLs, object storage)
- [x] Bluetooth audio routing (Meta AI Glasses) - **iOS native module implemented**
- [ ] Secure credential storage (Keychain/Keystore)
- [ ] Biometric authentication
- [ ] Offline mode with queue
- [x] Settings screen (configure BASE_URL, User ID)

### iOS Native Audio Module

The app includes a native iOS module for Meta AI Glasses integration:

**Location**: `modules/glasses-audio/`

**Features**:
- Real-time AVAudioSession monitoring
- Bluetooth audio route detection
- Native recording from Bluetooth mic
- Native playback through Bluetooth speakers
- Event-driven route change notifications

**Setup**:
See detailed instructions in `modules/glasses-audio/SETUP.md`

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

## Contributing

See the main repository [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](../LICENSE) in the repository root.
