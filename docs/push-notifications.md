# Push Notifications Configuration

This document describes how to configure push notifications for mobile (APNS/FCM) and web (WebPush) clients in the HandsFree Dev Companion backend.

## Overview

The notification system supports three delivery platforms:

1. **WebPush** - For browser-based push notifications
2. **APNS** (Apple Push Notification Service) - For iOS devices
3. **FCM** (Firebase Cloud Messaging) - For Android devices

## Architecture

### Device Registration

Mobile clients register their push tokens via the API endpoint:

```
POST /v1/notifications/subscriptions
{
  "endpoint": "<device-token-or-url>",
  "platform": "apns|fcm|webpush",
  "subscription_keys": { /* platform-specific keys */ }
}
```

### Delivery Flow

1. When a notification is created, the system queries all subscriptions for the user
2. For each subscription, the appropriate provider is selected based on the `platform` field
3. The notification is delivered using the platform-specific provider
4. Delivery results are logged (success/failure with details)

### Provider Selection

- Each subscription has a `platform` field (`webpush`, `apns`, or `fcm`)
- The `get_provider_for_platform()` function selects the correct provider
- Providers are initialized with credentials from environment variables

## Configuration

### Development Mode

For development and testing, use the dev logger provider:

```bash
HANDSFREE_NOTIFICATION_PROVIDER=dev
```

This logs notifications without sending them to any external service.

### WebPush (Browser Push)

#### 1. Generate VAPID Keys

```bash
python -c "from pywebpush import webpush; print(webpush.WebPusher.generate_vapid_keys())"
```

#### 2. Configure Environment

```bash
HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY=<your-public-key>
HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY=<your-private-key>
HANDSFREE_WEBPUSH_VAPID_SUBJECT=mailto:your-email@example.com
```

#### 3. Client Registration

Web clients should:
1. Request notification permission
2. Subscribe to push using the service worker
3. Send the subscription object (endpoint + keys) to the API

### APNS (iOS Push)

#### 1. Create APNS Key in Apple Developer Console

1. Go to [Apple Developer Console](https://developer.apple.com/account/resources/authkeys/list)
2. Navigate to **Certificates, Identifiers & Profiles** → **Keys**
3. Create a new key with **Apple Push Notifications service (APNs)** enabled
4. Download the `.p8` key file (save it securely, you can't download it again)
5. Note the **Key ID** displayed after creation

#### 2. Get Your Team ID

1. Go to [Apple Developer Account](https://developer.apple.com/account/)
2. Find your **Team ID** in the membership section

#### 3. Configure Environment

```bash
HANDSFREE_APNS_TEAM_ID=<your-team-id>
HANDSFREE_APNS_KEY_ID=<your-key-id>
HANDSFREE_APNS_KEY_PATH=/path/to/AuthKey_<key-id>.p8
HANDSFREE_APNS_BUNDLE_ID=com.example.yourapp
HANDSFREE_APNS_USE_SANDBOX=true  # Set to false for production
```

#### 4. Client Registration

iOS clients should:
1. Request notification permission via `UNUserNotificationCenter`
2. Get the device token from `application(_:didRegisterForRemoteNotificationsWithDeviceToken:)`
3. Send the device token to the API with `platform: "apns"`

```swift
// Example iOS code
func application(_ application: UIApplication, 
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
    // Send token to API
    registerPushToken(token: token, platform: "apns")
}
```

### FCM (Android Push)

#### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing one
3. Add your Android app to the project

#### 2. Generate Service Account Credentials

1. In Firebase Console, go to **Project Settings** → **Service Accounts**
2. Click **Generate New Private Key**
3. Download the JSON credentials file
4. Save it securely (e.g., `/etc/secrets/fcm-credentials.json`)

#### 3. Configure Environment

```bash
HANDSFREE_FCM_PROJECT_ID=<your-firebase-project-id>
HANDSFREE_FCM_CREDENTIALS_PATH=/path/to/fcm-credentials.json
```

#### 4. Client Registration

Android clients should:
1. Add Firebase Cloud Messaging to your app
2. Get the FCM token via `FirebaseMessaging.getInstance().token`
3. Send the token to the API with `platform: "fcm"`

```kotlin
// Example Android code
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val token = task.result
        // Send token to API
        registerPushToken(token, platform = "fcm")
    }
}
```

## API Endpoints

### Register Push Token

```http
POST /v1/notifications/subscriptions
Content-Type: application/json
X-User-ID: <user-id>

{
  "endpoint": "<device-token-or-subscription-url>",
  "platform": "apns",
  "subscription_keys": {}
}
```

**Response:**
```json
{
  "id": "subscription-uuid",
  "user_id": "user-id",
  "endpoint": "device-token",
  "platform": "apns",
  "subscription_keys": {},
  "created_at": "2026-01-16T07:00:00Z",
  "updated_at": "2026-01-16T07:00:00Z"
}
```

### List Subscriptions

```http
GET /v1/notifications/subscriptions
X-User-ID: <user-id>
```

### Unregister Push Token

```http
DELETE /v1/notifications/subscriptions/{subscription-id}
X-User-ID: <user-id>
```

## Database Schema

The `notification_subscriptions` table stores device registrations:

```sql
CREATE TABLE notification_subscriptions (
  id                  UUID PRIMARY KEY,
  user_id             UUID NOT NULL,
  endpoint            TEXT NOT NULL,        -- Device token or subscription URL
  platform            VARCHAR(20) NOT NULL, -- 'webpush', 'apns', or 'fcm'
  subscription_keys   JSON,                 -- Platform-specific keys
  created_at          TIMESTAMPTZ NOT NULL,
  updated_at          TIMESTAMPTZ NOT NULL
);
```

## Implementation Status

### Current Implementation (Stub Mode)

- ✅ **WebPush**: Fully implemented with pywebpush library
- ⚠️ **APNS**: Stub implementation (logs but doesn't send)
- ⚠️ **FCM**: Stub implementation (logs but doesn't send)

### Production Hardening (Future Work)

To make APNS/FCM production-ready:

1. **APNS**: Integrate `aioapns` library
   ```bash
   pip install aioapns
   ```

2. **FCM**: Integrate `firebase-admin` library
   ```bash
   pip install firebase-admin
   ```

3. Update provider implementations to use these libraries instead of stub logic

## Security Considerations

1. **Credential Storage**: Store APNS keys and FCM credentials securely
   - Use environment variables for development
   - Use secret managers (Vault, AWS Secrets Manager) for production
   - Never commit credentials to version control

2. **Token Validation**: Validate device tokens before storing
   - Check format and length
   - Consider implementing token refresh logic

3. **Rate Limiting**: Implement rate limiting on registration endpoints
   - Prevent abuse of registration API
   - Monitor for unusual registration patterns

4. **Token Rotation**: Handle token expiration and updates
   - Clients should re-register on token change
   - Clean up expired/invalid tokens

## Troubleshooting

### WebPush Issues

- **pywebpush not installed**: Run `pip install pywebpush`
- **Invalid VAPID keys**: Regenerate keys using the command above
- **410 Gone errors**: Subscription expired, client should re-subscribe

### APNS Issues (When Implemented)

- **Invalid credentials**: Verify Team ID, Key ID, and key file path
- **Sandbox vs Production**: Ensure `USE_SANDBOX` matches your app build
- **Invalid device token**: Token format should be hex string (64 chars)

### FCM Issues (When Implemented)

- **Invalid credentials**: Verify JSON file path and permissions
- **Project ID mismatch**: Ensure project ID matches Firebase console
- **Invalid token**: Token should be base64 string from FCM SDK

## Testing

### Manual Testing

1. Start the server with dev logger:
   ```bash
   HANDSFREE_NOTIFICATION_PROVIDER=dev python -m uvicorn handsfree.api:app
   ```

2. Register a test subscription:
   ```bash
   curl -X POST http://localhost:8000/v1/notifications/subscriptions \
     -H "Content-Type: application/json" \
     -H "X-User-ID: test-user" \
     -d '{"endpoint": "test-device-token", "platform": "apns"}'
   ```

3. Trigger a notification and check logs for delivery attempts

### Automated Testing

Run the notification tests:
```bash
pytest tests/test_notification*.py -v
```

## References

- [Web Push Protocol](https://tools.ietf.org/html/rfc8030)
- [APNS Documentation](https://developer.apple.com/documentation/usernotifications)
- [FCM Documentation](https://firebase.google.com/docs/cloud-messaging)
- [VAPID Specification](https://tools.ietf.org/html/rfc8292)
