# Mobile Client Integration Guide

This guide explains how to integrate a mobile iOS or Android application with the HandsFree Dev Companion backend API.

## Overview

The HandsFree system provides a complete hands-free developer assistant experience through:

1. **Command submission** - Send voice/text commands to the backend
2. **Confirmation flow** - Confirm actions that require explicit approval
3. **Notifications** - Receive updates via polling or push notifications
4. **TTS playback** - Get audio responses for hands-free interaction

## Architecture

```
[Mobile App] <---> [Backend API] <---> [Agent System]
     |                  |
     |                  v
     |          [Notification System]
     |                  |
     v                  v
[Push Provider]  [Database]
(APNS/FCM)
```

## API Endpoints

All endpoints use `http://localhost:8080` as the base URL in development. In production, this would be your deployed backend URL.

### Authentication

All API requests require authentication via the `X-User-ID` header:

```bash
curl -H "X-User-ID: 00000000-0000-0000-0000-000000000001" \
     http://localhost:8080/v1/status
```

For production deployments, you would use OAuth tokens or API keys instead of the X-User-ID header.

## 1. Command Submission Flow

### Submit a Text Command

Send a text command to the backend for processing:

**Endpoint:** `POST /v1/command`

**Request:**
```json
{
  "input": {
    "type": "text",
    "text": "Show me my open pull requests"
  },
  "profile": "terse",
  "client_context": {
    "device": "ios",
    "locale": "en-US",
    "timezone": "America/Los_Angeles",
    "app_version": "1.0.0"
  },
  "idempotency_key": "unique-request-id-123"
}
```

**Response:**
```json
{
  "response": {
    "type": "text",
    "text": "You have 3 open pull requests..."
  },
  "intent": {
    "name": "inbox.list",
    "confidence": 0.95,
    "entities": {}
  },
  "pending_action": null,
  "cards": [
    {
      "title": "PR #123: Add feature X",
      "subtitle": "my-repo",
      "lines": ["Status: Open", "Reviews: 2 approved"],
      "deep_link": "https://github.com/owner/repo/pull/123"
    }
  ]
}
```

### Submit an Audio Command

For voice commands, first upload the audio file to a storage service (e.g., S3) and provide a pre-signed URL:

**Request:**
```json
{
  "input": {
    "type": "audio",
    "format": "m4a",
    "uri": "https://storage.example.com/audio/recording-123.m4a",
    "duration_ms": 3500
  },
  "profile": "terse",
  "client_context": {
    "device": "ios",
    "locale": "en-US",
    "timezone": "America/Los_Angeles",
    "app_version": "1.0.0"
  }
}
```

The backend will:
1. Fetch the audio from the provided URI
2. Transcribe it to text (via configured STT provider)
3. Process the command
4. Return a response

### Handling Responses

The `CommandResponse` includes several fields:

- **`response`** - The main response (text, audio URI, or error)
- **`intent`** - Parsed intent with confidence score and extracted entities
- **`pending_action`** - If present, contains a confirmation token for actions requiring approval
- **`cards`** - Optional UI cards with structured data for display
- **`debug`** - Debug information (only if `client_context.debug: true`)

## 2. Confirmation Flow

Some commands (like merging a PR or delegating to an agent) require explicit confirmation for safety.

### When a Confirmation is Required

If the `CommandResponse` includes a `pending_action` field:

```json
{
  "response": {
    "type": "text",
    "text": "Ready to merge PR #456. Say 'confirm' to proceed."
  },
  "pending_action": {
    "token": "conf-abc123xyz",
    "expires_at": "2026-01-17T01:00:00Z",
    "summary": "Merge PR #456 in owner/repo"
  }
}
```

### Confirm the Action

To confirm, send the token to the confirmation endpoint:

**Endpoint:** `POST /v1/commands/confirm`

**Request:**
```json
{
  "token": "conf-abc123xyz",
  "idempotency_key": "confirm-request-456"
}
```

**Response:**
```json
{
  "response": {
    "type": "text",
    "text": "PR #456 merged successfully."
  },
  "intent": {
    "name": "pr.merge",
    "confidence": 1.0,
    "entities": {
      "pr_number": 456
    }
  }
}
```

### Timeout Handling

Confirmation tokens expire (typically after 5-10 minutes). If a token expires, the API returns:

```json
{
  "error": "Pending action not found or expired"
}
```

In this case, the user must re-submit the original command.

## 3. Notifications

The backend sends notifications for important events (PR updates, CI failures, agent task completion, etc.).

### Polling for Notifications

**Endpoint:** `GET /v1/notifications`

**Parameters:**
- `since` (optional) - ISO 8601 timestamp; return notifications after this time
- `limit` (optional) - Max notifications to return (default: 50, max: 100)

**Request:**
```bash
curl -H "X-User-ID: 00000000-0000-0000-0000-000000000001" \
     "http://localhost:8080/v1/notifications?since=2026-01-17T00:00:00Z&limit=20"
```

**Response:**
```json
{
  "notifications": [
    {
      "id": "notif-123",
      "user_id": "00000000-0000-0000-0000-000000000001",
      "event_type": "pr.checks_failed",
      "message": "CI checks failed on PR #789",
      "data": {
        "repo": "owner/repo",
        "pr_number": 789,
        "failed_checks": ["build", "lint"]
      },
      "priority": "high",
      "created_at": "2026-01-17T00:45:00Z",
      "read_at": null
    }
  ],
  "count": 1
}
```

### Polling Best Practices

- **Poll interval**: Every 30-60 seconds when app is in foreground
- **Use `since` parameter**: Track the most recent notification timestamp and use it in subsequent polls
- **Handle `read_at`**: Mark notifications as read by storing their IDs locally

## 4. Push Notifications (APNS/FCM)

For real-time updates, register a push notification subscription.

### iOS (APNS) Registration

**Step 1:** Obtain a device token from APNs in your iOS app:

```swift
// In AppDelegate or SceneDelegate
func application(_ application: UIApplication, 
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    // Register with backend
    registerPushToken(token: tokenString, platform: "apns")
}
```

**Step 2:** Register the token with the backend:

**Endpoint:** `POST /v1/notifications/subscriptions`

**Request:**
```json
{
  "endpoint": "a1b2c3d4e5f6...",
  "platform": "apns"
}
```

**Response:**
```json
{
  "id": "sub-abc123",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "endpoint": "a1b2c3d4e5f6...",
  "platform": "apns",
  "subscription_keys": {},
  "created_at": "2026-01-17T00:50:00Z",
  "updated_at": "2026-01-17T00:50:00Z"
}
```

### Android (FCM) Registration

**Step 1:** Obtain an FCM token in your Android app:

```kotlin
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val token = task.result
        // Register with backend
        registerPushToken(token, "fcm")
    }
}
```

**Step 2:** Register the token with the backend using the same endpoint as iOS, but with `"platform": "fcm"`.

### Push Notification Payload

When a notification is triggered, the backend sends a push message:

**APNS Payload:**
```json
{
  "aps": {
    "alert": {
      "title": "HandsFree Dev",
      "body": "CI checks failed on PR #789"
    },
    "badge": 1,
    "sound": "default"
  },
  "data": {
    "notification_id": "notif-123",
    "event_type": "pr.checks_failed",
    "pr_number": 789
  }
}
```

**FCM Payload:**
```json
{
  "notification": {
    "title": "HandsFree Dev",
    "body": "CI checks failed on PR #789"
  },
  "data": {
    "notification_id": "notif-123",
    "event_type": "pr.checks_failed",
    "pr_number": "789"
  }
}
```

### Managing Subscriptions

**List all subscriptions:**
```
GET /v1/notifications/subscriptions
```

**Delete a subscription:**
```
DELETE /v1/notifications/subscriptions/{subscription_id}
```

Call this when:
- The user logs out
- The app is uninstalled
- The device token is invalidated

## 5. Text-to-Speech (TTS) Playback

For hands-free interaction, convert text responses to audio.

### Generate TTS Audio

**Endpoint:** `POST /v1/tts`

**Request:**
```json
{
  "text": "You have 3 open pull requests requiring review.",
  "voice": "default",
  "format": "mp3"
}
```

**Response:**
- Content-Type: `audio/mpeg` (for mp3) or `audio/wav` (for wav)
- Body: Binary audio data

**Example (cURL):**
```bash
curl -X POST http://localhost:8080/v1/tts \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 00000000-0000-0000-0000-000000000001" \
  -d '{"text": "Hello, developer.", "format": "mp3"}' \
  --output response.mp3
```

### Client-Side Integration

**iOS (AVFoundation):**
```swift
let audioData = try await fetchTTS(text: "Your PR was merged")
let player = try AVAudioPlayer(data: audioData)
player.play()
```

**Android (MediaPlayer):**
```kotlin
val audioData = fetchTTS("Your PR was merged")
val tempFile = File.createTempFile("tts", ".mp3", cacheDir)
tempFile.writeBytes(audioData)

val mediaPlayer = MediaPlayer()
mediaPlayer.setDataSource(tempFile.absolutePath)
mediaPlayer.prepare()
mediaPlayer.start()
```

### TTS Best Practices

- **Cache responses**: Cache TTS audio for frequently used phrases
- **Background playback**: Use system audio APIs for background playback
- **Interruption handling**: Pause/resume playback when phone calls or other audio sources interrupt
- **Voice selection**: Use the `voice` parameter to select different voices (provider-specific)

## Complete Integration Example

Here's a typical interaction flow:

1. **User speaks**: "Show my PRs"
2. **App records audio** → uploads to storage → gets pre-signed URL
3. **App sends command**:
   ```json
   {
     "input": {"type": "audio", "uri": "https://storage/.../recording.m4a"},
     "profile": "terse",
     "client_context": {"device": "ios", ...}
   }
   ```
4. **Backend processes** → returns response with cards
5. **App displays cards** and/or **generates TTS**:
   ```json
   {"text": "You have 3 open PRs", "format": "mp3"}
   ```
6. **App plays audio** through device speakers or connected wearable
7. **Backend sends push notification** if a PR status changes
8. **App receives push** → fetches notification details → shows alert

## Configuration

### Backend Environment Variables

For real push delivery, configure the backend:

**APNS:**
```bash
export HANDSFREE_NOTIFICATION_PROVIDER=apns
export HANDSFREE_APNS_TEAM_ID="<team-id>"
export HANDSFREE_APNS_KEY_ID="<key-id>"
export HANDSFREE_APNS_KEY_PATH="/secrets/AuthKey_<key-id>.p8"
export HANDSFREE_APNS_BUNDLE_ID="com.example.handsfree"
export HANDSFREE_APNS_MODE=real
```

**FCM:**
```bash
export HANDSFREE_NOTIFICATION_PROVIDER=fcm
export HANDSFREE_FCM_PROJECT_ID="<firebase-project-id>"
export HANDSFREE_FCM_CREDENTIALS_PATH="/secrets/firebase-service-account.json"
export HANDSFREE_FCM_MODE=real
```

### Mobile App Configuration

**iOS (Info.plist):**
```xml
<key>UIBackgroundModes</key>
<array>
    <string>remote-notification</string>
    <string>audio</string>
</array>
```

**Android (AndroidManifest.xml):**
```xml
<service
    android:name=".MyFirebaseMessagingService"
    android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

## Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "error": "Authentication required"
}
```

**400 Bad Request:**
```json
{
  "error": "Invalid command input: text is required for text input type"
}
```

**500 Internal Server Error:**
```json
{
  "error": "TTS synthesis failed"
}
```

### Retry Strategy

- **Network errors**: Exponential backoff (1s, 2s, 4s, 8s)
- **401 errors**: Re-authenticate immediately
- **500 errors**: Retry up to 3 times with exponential backoff
- **400 errors**: Don't retry; show error to user

## Testing

### Local Development

1. Start the backend:
   ```bash
   make run
   ```

2. Use the reference client (see `dev/reference_mobile_client.py`) to test flows

3. Or use cURL:
   ```bash
   # Send a command
   curl -X POST http://localhost:8080/v1/command \
     -H "Content-Type: application/json" \
     -H "X-User-ID: 00000000-0000-0000-0000-000000000001" \
     -d '{"input": {"type": "text", "text": "show my inbox"}, "profile": "terse", "client_context": {"device": "ios", "locale": "en-US", "timezone": "America/Los_Angeles", "app_version": "1.0.0"}}'
   ```

### Push Notification Testing

Use the development provider to test without real APNS/FCM:

```bash
export HANDSFREE_NOTIFICATION_PROVIDER=logger
```

This logs push attempts instead of sending them.

## Security Considerations

1. **Authentication**: Use secure tokens (OAuth, API keys) in production, not X-User-ID headers
2. **HTTPS**: Always use HTTPS in production to encrypt data in transit
3. **Token validation**: Validate push tokens before accepting subscriptions
4. **Rate limiting**: Implement rate limits on all endpoints to prevent abuse
5. **Audio storage**: Use pre-signed URLs with short expiration times for audio uploads
6. **Data privacy**: Don't log sensitive user data (audio transcripts, notification content)

## Next Steps

- See `docs/meta-ai-glasses.md` for integrating with Meta AI Glasses
- See `dev/reference_mobile_client.py` for a working example
- Review the OpenAPI spec in `spec/openapi.yaml` for complete API documentation
