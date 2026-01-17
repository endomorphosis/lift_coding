# Mobile Push Notifications Implementation Guide

This guide provides step-by-step instructions and code scaffolding for implementing push notifications with TTS playback on iOS and Android mobile clients.

## Quick Start

The Expo mobile app already includes push notification support. To use it:

1. **Install dependencies**:
   ```bash
   cd mobile
   npm install
   ```

2. **Start the app**:
   ```bash
   npm start
   ```

3. **Enable push notifications**:
   - Open the app on a physical device (push doesn't work on simulator)
   - Navigate to the "Status" screen
   - Tap "Enable Push" to register for notifications
   - Grant permission when prompted

4. **Test notifications**:
   - Use the "Test Notification (Polling)" button to fetch and speak the latest notification
   - Or trigger a real notification from your backend

## Implementation Overview

The push notification system is implemented in `mobile/src/push/`:

- **`pushClient.js`**: Handles token registration and backend subscription management
- **`notificationsHandler.js`**: Processes incoming notifications and triggers TTS playback
- **`index.js`**: Exports all push functionality

The Status screen (`mobile/src/screens/StatusScreen.js`) provides the UI for:
- Enabling/disabling push notifications
- Viewing current push token and subscription status
- Testing notification delivery via polling fallback

## Overview

The mobile push notification system enables real-time delivery of developer notifications (PR updates, CI failures, agent task completion, etc.) with hands-free audio playback via text-to-speech.

### Architecture Flow

```
[Push Provider] --> [Mobile App] --> [Backend API] --> [TTS Audio]
 (APNS/FCM)         (Receive)       (Fetch details)     (Play)
```

### Backend Endpoints

- **Register token**: `POST /v1/notifications/subscriptions`
- **List subscriptions**: `GET /v1/notifications/subscriptions`
- **Delete subscription**: `DELETE /v1/notifications/subscriptions/{id}`
- **Poll fallback**: `GET /v1/notifications`
- **Generate TTS**: `POST /v1/tts`

## Implementation Options

### Option 1: Expo Notifications (Recommended for Cross-Platform)

Expo provides a unified API for both iOS and Android push notifications, simplifying development and testing.

**Pros:**
- Single codebase for iOS and Android
- Easier testing and development
- Built-in permission handling
- Simplified token management

**Cons:**
- Requires Expo dev environment
- Limited customization for advanced features

### Option 2: Native APNS/FCM

Direct integration with Apple Push Notification Service and Firebase Cloud Messaging.

**Pros:**
- Full control over notification behavior
- Access to all platform-specific features
- No third-party dependencies

**Cons:**
- Separate implementation for iOS and Android
- More complex setup and testing

## Setup Instructions

### Prerequisites

1. **Backend running locally** or accessible endpoint:
   ```bash
   make run  # or docker-compose up
   ```

2. **User ID for authentication**:
   ```bash
   export USER_ID="00000000-0000-0000-0000-000000000001"
   ```

3. **Development environment**:
   - For Expo: Node.js, Expo CLI
   - For Native iOS: Xcode, Apple Developer account
   - For Native Android: Android Studio, Firebase project

## iOS Implementation (Native Swift)

### Step 1: Configure Capabilities

In Xcode, enable:
- Push Notifications
- Background Modes (Remote notifications, Audio)

### Step 2: Request Permission and Get Token

See `examples/ios_swift_token_registration.swift` for complete example:

```swift
import UserNotifications
import UIKit

class PushManager {
    func requestPermission() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .sound, .badge]
        ) { granted, error in
            if granted {
                DispatchQueue.main.async {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            }
        }
    }
    
    func didRegisterForRemoteNotifications(deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        registerTokenWithBackend(token: token, platform: "apns")
    }
}
```

### Step 3: Handle Incoming Notifications

See `examples/ios_swift_receive_handler.swift`:

```swift
func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    didReceive response: UNNotificationResponse
) {
    let userInfo = response.notification.request.content.userInfo
    
    if let notificationId = userInfo["notification_id"] as? String,
       let message = userInfo["message"] as? String {
        speakNotification(message: message)
    }
}

func speakNotification(message: String) {
    fetchTTS(text: message) { audioData in
        playAudio(data: audioData)
    }
}
```

## Android Implementation (Native Kotlin)

### Step 1: Add Firebase Dependencies

In `build.gradle`:

```gradle
dependencies {
    implementation 'com.google.firebase:firebase-messaging:23.0.0'
}
```

### Step 2: Request Permission and Get Token

See `examples/android_kotlin_token_registration.kt`:

```kotlin
import com.google.firebase.messaging.FirebaseMessaging

class PushManager(private val context: Context) {
    fun requestPermissionAndToken() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ActivityCompat.requestPermissions(
                context as Activity,
                arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                NOTIFICATION_PERMISSION_REQUEST_CODE
            )
        }
        
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result
                registerTokenWithBackend(token, "fcm")
            }
        }
    }
}
```

### Step 3: Handle Incoming Notifications

See `examples/android_kotlin_receive_handler.kt`:

```kotlin
class MyFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        val notificationId = remoteMessage.data["notification_id"]
        val message = remoteMessage.data["message"]
        
        if (message != null) {
            speakNotification(message)
        }
    }
    
    private fun speakNotification(message: String) {
        fetchTTS(message) { audioData ->
            playAudio(audioData)
        }
    }
}
```

## Expo Implementation (Cross-Platform)

### Step 1: Install Expo Notifications

```bash
expo install expo-notifications expo-device
```

### Step 2: Request Permission and Get Token

See `examples/expo_token_registration.ts`:

```typescript
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';

async function registerForPushNotifications() {
  if (!Device.isDevice) {
    console.log('Push notifications only work on physical devices');
    return;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;
  
  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('Permission not granted for push notifications');
    return;
  }

  const token = (await Notifications.getExpoPushTokenAsync()).data;
  await registerTokenWithBackend(token, 'expo');
}
```

### Step 3: Handle Incoming Notifications

See `examples/expo_receive_handler.ts`:

```typescript
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

Notifications.addNotificationReceivedListener(notification => {
  const data = notification.request.content.data;
  const message = data.message as string;
  
  if (message) {
    speakNotification(message);
  }
});

async function speakNotification(message: string) {
  const audioData = await fetchTTS(message);
  await playAudio(audioData);
}
```

## Backend Integration

### Register Token with Backend

```typescript
async function registerTokenWithBackend(token: string, platform: string) {
  const response = await fetch('http://localhost:8080/v1/notifications/subscriptions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': process.env.USER_ID || '00000000-0000-0000-0000-000000000001',
    },
    body: JSON.stringify({
      endpoint: token,
      platform: platform,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to register token: ${response.statusText}`);
  }

  const subscription = await response.json();
  console.log('Registered subscription:', subscription.id);
  return subscription;
}
```

### Fetch TTS Audio

```typescript
async function fetchTTS(text: string): Promise<ArrayBuffer> {
  const response = await fetch('http://localhost:8080/v1/tts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': process.env.USER_ID || '00000000-0000-0000-0000-000000000001',
    },
    body: JSON.stringify({
      text: text,
      format: 'mp3',
      voice: 'default',
    }),
  });

  if (!response.ok) {
    throw new Error(`TTS failed: ${response.statusText}`);
  }

  return await response.arrayBuffer();
}
```

### Delete Subscription

```typescript
async function deleteSubscription(subscriptionId: string) {
  const response = await fetch(
    `http://localhost:8080/v1/notifications/subscriptions/${subscriptionId}`,
    {
      method: 'DELETE',
      headers: {
        'X-User-ID': process.env.USER_ID || '00000000-0000-0000-0000-000000000001',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to delete subscription: ${response.statusText}`);
  }
}
```

## Polling Fallback

When real push notifications aren't available (development, testing, or push provider issues), use polling:

```typescript
async function pollForNotifications() {
  let lastTimestamp = new Date().toISOString();

  setInterval(async () => {
    const response = await fetch(
      `http://localhost:8080/v1/notifications?since=${lastTimestamp}&limit=20`,
      {
        headers: {
          'X-User-ID': process.env.USER_ID || '00000000-0000-0000-0000-000000000001',
        },
      }
    );

    const data = await response.json();
    
    if (data.notifications.length > 0) {
      for (const notification of data.notifications) {
        await speakNotification(notification.message);
        lastTimestamp = notification.created_at;
      }
    }
  }, 30000); // Poll every 30 seconds
}
```

## Smoke Test Procedure

This procedure validates the end-to-end notification flow without requiring real push delivery.

### Step 1: Start Backend

```bash
cd /path/to/lift_coding
make run
```

### Step 2: Register a Test Subscription

```bash
curl -X POST http://localhost:8080/v1/notifications/subscriptions \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 00000000-0000-0000-0000-000000000001" \
  -d '{
    "endpoint": "test-device-token-12345",
    "platform": "apns"
  }'
```

Save the returned `subscription_id` for cleanup.

### Step 3: Trigger a Notification Event

Use existing development flows to trigger a notification (e.g., create a PR update, CI failure, etc.), or manually create a notification in the database for testing.

### Step 4: Poll for Notifications

```bash
curl -H "X-User-ID: 00000000-0000-0000-0000-000000000001" \
  "http://localhost:8080/v1/notifications?limit=10"
```

You should see your test notification in the response.

### Step 5: Fetch TTS Audio

```bash
curl -X POST http://localhost:8080/v1/tts \
  -H "Content-Type: application/json" \
  -H "X-User-ID: 00000000-0000-0000-0000-000000000001" \
  -d '{"text": "CI checks failed on PR 789", "format": "mp3"}' \
  --output notification.mp3
```

### Step 6: Play Audio

On your development machine:
```bash
# macOS
afplay notification.mp3

# Linux
mpg123 notification.mp3

# Windows
start notification.mp3
```

### Step 7: Cleanup

```bash
curl -X DELETE http://localhost:8080/v1/notifications/subscriptions/{subscription_id} \
  -H "X-User-ID: 00000000-0000-0000-0000-000000000001"
```

## Platform Constraints & Limitations

### iOS
- **Background execution**: iOS limits background time for push handlers (~30 seconds)
- **Audio playback**: Requires "Audio" background mode enabled
- **Silent pushes**: Limited to `content-available` flag; may be throttled by iOS
- **Token invalidation**: Tokens can change; handle `didInvalidateTokenForPush` delegate method

### Android
- **Battery optimization**: Users can restrict background execution per app
- **Doze mode**: Notifications may be delayed when device is idle
- **Custom sounds**: Require notification channel configuration (API 26+)
- **Foreground service**: Consider using for guaranteed background execution

### General
- **Network reliability**: Use exponential backoff for API calls
- **Token refresh**: Implement token refresh logic (FCM tokens can change)
- **Permission changes**: Monitor permission status changes at app launch
- **Testing**: Use platform-specific testing tools (APNS Sandbox, FCM Test Lab)

## Testing Tips

### iOS Simulator Limitations
- **Cannot receive real push notifications** (use device or polling fallback)
- **Use Xcode push notification testing** (Xcode 11.4+)
- **Simulate push with CLI**:
  ```bash
  xcrun simctl push booted com.example.handsfree notification.json
  ```

### Android Emulator
- **Requires Google Play Services** for FCM
- **Use Firebase Console** to send test notifications
- **Use adb to simulate**:
  ```bash
  adb shell am broadcast -a com.google.firebase.MESSAGING_EVENT
  ```

### Development Mode
Set backend to logger mode to avoid real push delivery:
```bash
export HANDSFREE_NOTIFICATION_PROVIDER=logger
```

## Troubleshooting

### Token Not Registering
- Verify backend is accessible from mobile device
- Check X-User-ID header is set correctly
- Confirm push permission is granted
- Review backend logs for registration errors

### Notifications Not Arriving
- Verify backend is configured with valid APNS/FCM credentials
- Check push provider dashboards (Apple Developer, Firebase Console)
- Confirm token is still valid (not expired/revoked)
- Use polling fallback to verify notification generation

### TTS Playback Issues
- Verify audio format is supported (mp3, wav)
- Check audio session configuration (iOS)
- Confirm audio permissions are granted
- Test TTS endpoint directly with cURL

### Background Execution
- Ensure background modes are enabled (iOS)
- Configure foreground service (Android)
- Handle app state transitions (foreground/background)
- Test with device locked and unlocked

## Production Considerations

### Security
- **Use HTTPS** for all API calls in production
- **Rotate tokens** regularly; implement refresh logic
- **Validate push payloads** to prevent injection attacks
- **Implement rate limiting** to prevent abuse

### Monitoring
- Track token registration success/failure rates
- Monitor push delivery rates from provider dashboards
- Log TTS fetch failures for debugging
- Alert on permission denial rates

### User Experience
- **Respect user preferences**: Allow disabling notifications
- **Implement DND mode**: Silence notifications during specific hours
- **Show notification history**: Allow users to review past notifications
- **Provide clear onboarding**: Explain why permissions are needed

## Additional Resources

- [Apple Push Notification Service Documentation](https://developer.apple.com/documentation/usernotifications)
- [Firebase Cloud Messaging Documentation](https://firebase.google.com/docs/cloud-messaging)
- [Expo Notifications Documentation](https://docs.expo.dev/versions/latest/sdk/notifications/)
- [Backend API Documentation](../../docs/mobile-client-integration.md)
- [Smoke Test Guide](../../docs/mobile-push-smoke-test.md)

## Code Examples

All code examples referenced in this guide are available in the `examples/` directory:

- `examples/ios_swift_token_registration.swift`
- `examples/ios_swift_receive_handler.swift`
- `examples/android_kotlin_token_registration.kt`
- `examples/android_kotlin_receive_handler.kt`
- `examples/expo_token_registration.ts`
- `examples/expo_receive_handler.ts`
- `examples/backend_client.ts` (shared backend integration code)
