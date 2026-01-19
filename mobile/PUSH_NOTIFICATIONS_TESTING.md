# Push Notifications Testing Guide

This guide explains how to test the push notification auto-speak functionality on a physical device.

## Prerequisites

1. Physical iOS or Android device with Expo dev client installed
2. Backend server running and accessible from the device
3. User ID configured in Settings screen
4. Device connected to same network as backend (or backend exposed via ngrok/tunnel)

## Setup

1. **Configure Settings:**
   - Open the mobile app
   - Go to Settings tab
   - Set your User ID
   - Configure Base URL if using custom backend
   - Save settings

2. **Register for Push Notifications:**
   - The app automatically sets up notification listeners on startup
   - On first launch, you'll be prompted to allow notifications
   - Grant notification permissions

3. **Register Device Token:**
   - Use the backend API or admin panel to register the device's Expo push token
   - The token can be obtained via `registerForPushAsync()` from the push client

## Testing Scenarios

### 1. Foreground Notification with Auto-Speak

**Steps:**
1. Keep the app open (foreground)
2. Send a test push notification from backend with a message
3. **Expected behavior:**
   - Notification appears at top of screen
   - TTS audio is fetched from backend
   - Message is spoken immediately through device speaker
   - No crash or errors

**Verify:**
- Go to Glasses Diagnostics screen
- Check "Push Notifications Debug" section
- Confirm "Last Spoken" shows your message
- Confirm "App State" shows "☀️ Foreground"

### 2. Background Notification with Deferred Speaking

**Steps:**
1. Keep the app open
2. Press home button to background the app
3. Send a test push notification from backend
4. Return to the app (tap app icon or notification)
5. **Expected behavior:**
   - When backgrounded: notification received but speaking is deferred
   - When foregrounded: pending messages are spoken automatically
   - No crash or errors

**Verify:**
- Check "Push Notifications Debug" section
- While backgrounded, "Pending Speak Queue" should show count
- After foregrounding, pending count should go to 0
- "Last Spoken" should show the message

### 3. Notification Response (Tapped Notification)

**Steps:**
1. Background the app
2. Send a test push notification
3. Tap the notification when it appears
4. **Expected behavior:**
   - App opens to foreground
   - Message is spoken immediately
   - No crash or errors

### 4. Simulated Notification (Dev Testing)

**Steps:**
1. Open Glasses Diagnostics screen
2. Tap "🔔 Simulate Test Notification" button
3. **Expected behavior:**
   - Alert shows "Simulated notification sent"
   - TTS audio plays immediately
   - Debug section updates with notification info

**Use case:** Test TTS flow without needing real push infrastructure

## Debug UI

The **Glasses Diagnostics** screen includes a "Push Notifications Debug" section showing:

- **App State:** Whether app is in foreground or background
- **Pending Speak Queue:** Number of messages deferred while backgrounded
- **Last Notification:** Timestamp of most recent notification
- **Last Spoken:** Text of most recently spoken message
- **Last TTS Error:** Any playback errors (if occurred)

This updates in real-time (every 2 seconds) to help diagnose issues.

## Known Limitations

1. **Background TTS not supported:** iOS and Android restrict audio playback when app is fully backgrounded. Speaking is deferred until app returns to foreground.

2. **Network required:** TTS audio is fetched from backend, so device must have network connectivity.

3. **Notification payload:** If notification includes a `notification_id`, the app will attempt to fetch full details from backend. If fetch fails, it falls back to the basic message in the notification payload.

## Troubleshooting

### No sound when notification arrives

1. Check device volume is up
2. Check device is not in silent mode
3. Check "Last TTS Error" in debug section for error details
4. Verify backend `/v1/tts` endpoint is accessible

### Notification not received

1. Verify notification permissions are granted
2. Check device token is registered with backend
3. Verify notification was sent from backend (check backend logs)
4. Try sending to Expo's push notification tool first to isolate issues

### App crashes on notification

1. Check console logs for error messages
2. Verify backend returns valid audio from `/v1/tts`
3. Try "Simulate Test Notification" button to reproduce locally

## Backend Integration

The notification payload should include:

```json
{
  "data": {
    "message": "Your notification message here",
    "notification_id": "optional-id-for-details-fetch"
  },
  "body": "Fallback message",
  "sound": "default"
}
```

The app will:
1. Extract `message` from `data.message` or fall back to `body`
2. If `notification_id` is present, fetch full details from `GET /v1/notifications/{id}`
3. Call `POST /v1/tts` with the message text
4. Play the returned audio (immediately or deferred based on app state)

## Next Steps

- Add push token management UI in Settings
- Add notification history view
- Support rich notifications with actions
- Add notification sound preferences
