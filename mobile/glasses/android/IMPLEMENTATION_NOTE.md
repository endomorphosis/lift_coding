# Note on AudioRouteMonitor.kt

This is a reference implementation of the AudioRouteMonitor class for Android.

For the **active implementation used in the Expo app**, see:
`mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/AudioRouteMonitor.kt`

This copy is maintained for:
1. Reference documentation
2. Standalone Android app implementations (non-Expo)
3. Testing and development outside of React Native

## Usage in Expo App

The Expo app uses the version in the `expo-glasses-audio` module, which is automatically linked and accessible via JavaScript/TypeScript:

```javascript
import GlassesAudio from '../../modules/expo-glasses-audio';

const route = await GlassesAudio.getCurrentRoute();
```

## Standalone Usage (Non-Expo)

For standalone Android apps (pure Kotlin/Java), you can use this implementation directly:

```kotlin
val monitor = AudioRouteMonitor(context)
val route = monitor.getCurrentRoute()

// Start monitoring
monitor.startMonitoring { routeInfo ->
    // Handle route changes
}
```

## Keeping in Sync

If changes are needed, update both copies:
1. Primary: `mobile/modules/expo-glasses-audio/android/.../AudioRouteMonitor.kt`
2. Reference: `mobile/glasses/android/AudioRouteMonitor.kt`

Or better yet, consider extracting to a shared Kotlin library if significant divergence occurs.
