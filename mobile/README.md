# Handsfree Mobile Companion App

React Native/Expo mobile app for interacting with the Handsfree backend.

## Features

- **Status Check**: View backend connectivity and status
- **Command Input**: Send text commands to the backend
- **Confirmation Flow**: Confirm/cancel/repeat/next pending actions
- **Text-to-Speech**: Fetch and play TTS audio from backend
- **Developer Settings**: Configure X-User-ID header and backend URL in-app

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

1. Install the [Expo Go](https://expo.dev/go) app on your device
2. Scan the QR code shown in the terminal
3. Make sure your device is on the same network as your computer
4. Update `BASE_URL` in `src/api/config.js` to use your computer's local IP address

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
- Enter a text command (e.g., "what's in my inbox?")
- Tap "Send Command"
- View the response including:
  - Spoken text
  - UI cards
  - Confirmation requirement (if needed)

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
- `POST /v1/command` - Send text command
- `POST /v1/commands/confirm` - Confirm/cancel pending action
- `POST /v1/tts` - Fetch TTS audio

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

### Dependencies issues

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

### Planned Features

- [ ] Push notifications integration (`/v1/notifications/subscriptions`)
- [ ] Audio input for voice commands
- [ ] Bluetooth audio routing (Meta AI Glasses)
- [ ] Secure credential storage (Keychain/Keystore)
- [ ] Biometric authentication
- [ ] Offline mode with queue
- [x] Settings screen (configure BASE_URL, User ID)

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
