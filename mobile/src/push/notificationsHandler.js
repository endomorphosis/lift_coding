/**
 * Notifications Handler
 * 
 * Handles:
 * - Setting up notification listeners
 * - Parsing incoming notification payloads
 * - Fetching TTS audio and playing it
 * - Polling fallback for development/testing
 * - Background-safe TTS deferral
 */

import * as Notifications from 'expo-notifications';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { AppState } from 'react-native';
import { getBaseUrl, getHeaders } from '../api/config';
import { fetchTTS } from '../api/client';

// Notification queue for sequential TTS playback
let notificationQueue = [];
let isProcessingQueue = false;

// Background state tracking
let isAppInBackground = false;
let pendingSpeakQueue = [];
let appStateSubscription = null;
let isProcessingPendingQueue = false;
let appStateMonitoringInitialized = false;

/**
 * Helper to check if an app state represents background/inactive
 * @param {string} state - AppState value
 * @returns {boolean} True if app is backgrounded or inactive
 */
function isBackgroundState(state) {
  return state === 'background' || state === 'inactive';
}

// Debug state for UI visibility
let debugState = {
  lastNotificationReceived: null,
  lastSpokenText: null,
  lastPlaybackError: null,
  lastNotificationTime: null,
};

// Configure how notifications are handled when app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false, // We'll play TTS instead
    shouldSetBadge: false,
  }),
});

/**
 * Set up notification listeners and background state monitoring
 * @param {Function} onNotification - Callback when notification is received
 */
export function setupNotificationListeners(onNotification) {
  // Set up AppState monitoring for background/foreground detection
  setupAppStateMonitoring();

  // Handle notifications received while app is foregrounded
  const foregroundSubscription = Notifications.addNotificationReceivedListener(
    async (notification) => {
      console.log('Notification received (foreground):', notification);
      await handleNotification(notification);
      if (onNotification) {
        onNotification(notification);
      }
    }
  );

  // Handle notification responses (user tapped notification)
  const responseSubscription = Notifications.addNotificationResponseReceivedListener(
    async (response) => {
      console.log('Notification response:', response);
      await handleNotification(response.notification);
      if (onNotification) {
        onNotification(response.notification);
      }
    }
  );

  // Return cleanup function
  return () => {
    foregroundSubscription.remove();
    responseSubscription.remove();
    if (appStateSubscription) {
      appStateSubscription.remove();
      appStateSubscription = null;
    }
  };
}

/**
 * Set up AppState monitoring to detect background/foreground transitions
 * This enables deferred speaking when app is backgrounded
 */
function setupAppStateMonitoring() {
  // Only set up once - prevent multiple initializations
  if (appStateMonitoringInitialized) {
    return;
  }

  // Remove any existing subscription first
  if (appStateSubscription) {
    appStateSubscription.remove();
    appStateSubscription = null;
  }

  // Initialize current state - use explicit comparison instead of regex match
  const currentState = AppState.currentState;
  isAppInBackground = isBackgroundState(currentState);

  appStateSubscription = AppState.addEventListener('change', (nextAppState) => {
    const wasInBackground = isAppInBackground;
    isAppInBackground = isBackgroundState(nextAppState);

    console.log(`AppState changed to: ${nextAppState}, background: ${isAppInBackground}`);

    // If app just came to foreground, process any pending speak requests
    if (wasInBackground && !isAppInBackground) {
      console.log('App foregrounded, processing pending speak queue');
      processPendingSpeakQueue();
    }
  });

  appStateMonitoringInitialized = true;
}

/**
 * Handle an incoming notification
 * @param {Object} notification - Notification object from Expo
 */
async function handleNotification(notification) {
  const data = notification.request.content.data;
  const body = notification.request.content.body;
  
  // Update debug state
  debugState.lastNotificationReceived = {
    data,
    body,
    time: new Date().toISOString(),
  };
  debugState.lastNotificationTime = new Date().toISOString();
  
  // Extract message from notification
  let message = data.message || body || 'New notification';
  
  // If notification has an ID, we could fetch full details from backend
  const notificationId = data.notification_id || data.id;
  if (notificationId) {
    try {
      const details = await fetchNotificationDetails(notificationId);
      if (details && details.message) {
        message = details.message;
      }
    } catch (error) {
      console.error('Failed to fetch notification details:', error);
      // Fall back to basic message
    }
  }

  // Speak the notification via TTS (with background awareness)
  await speakNotification(message);
}

/**
 * Fetch full notification details from backend
 * @param {string} notificationId - Notification ID
 * @returns {Promise<Object>} Notification details
 */
async function fetchNotificationDetails(notificationId) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(
    `${baseUrl}/v1/notifications/${notificationId}`,
    {
      method: 'GET',
      headers,
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch notification: ${response.status}`);
  }

  return await response.json();
}

/**
 * Convert notification text to speech and play it
 * Background-safe: defers speaking if app is backgrounded
 * @param {string} message - Message to speak
 */
export async function speakNotification(message) {
  // If app is in background, defer speaking until app is foregrounded
  if (isAppInBackground) {
    console.log('App is backgrounded, deferring speech:', message);
    // Avoid enqueueing duplicate messages while backgrounded
    // Note: includes() is O(n) but acceptable for typical queue sizes (< 100 items)
    // For high-volume scenarios, consider using a Set for O(1) lookups
    if (!pendingSpeakQueue.includes(message)) {
      pendingSpeakQueue.push(message);
    }
    debugState.lastSpokenText = `(deferred) ${message}`;
    return;
  }

  let sound = null;
  let tempFileUri = null;
  
  try {
    console.log('Speaking notification:', message);
    debugState.lastSpokenText = message;
    
    // Fetch TTS audio from backend
    const audioBlob = await fetchTTS(message);
    
    // Convert blob to base64
    const base64Audio = await blobToBase64(audioBlob);
    
    // Save to temporary file using expo-file-system
    const filename = `tts_${Date.now()}_${Math.random().toString(36).substring(2, 9)}.mp3`;
    tempFileUri = `${FileSystem.cacheDirectory}${filename}`;
    
    await FileSystem.writeAsStringAsync(tempFileUri, base64Audio, {
      encoding: FileSystem.EncodingType.Base64,
    });

    console.log('TTS audio saved to:', tempFileUri);

    // Configure audio session for playback
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
      staysActiveInBackground: true,
      shouldDuckAndroid: true,
    });

    // Play the audio
    const soundObject = await Audio.Sound.createAsync(
      { uri: tempFileUri },
      { shouldPlay: true }
    );
    sound = soundObject.sound;

    // Clean up after playback completes
    sound.setOnPlaybackStatusUpdate(async (status) => {
      if (status.didJustFinish || status.error) {
        try {
          await sound.unloadAsync();
          // Delete the temporary file
          if (tempFileUri) {
            await FileSystem.deleteAsync(tempFileUri, { idempotent: true });
          }
        } catch (cleanupError) {
          console.error('Cleanup error:', cleanupError);
        }
      }
    });

    // Clear error state on success
    debugState.lastPlaybackError = null;

  } catch (error) {
    console.error('Failed to speak notification:', error);
    debugState.lastPlaybackError = error.message;
    
    // Clean up on error
    if (sound) {
      try {
        await sound.unloadAsync();
      } catch (cleanupError) {
        console.error('Sound cleanup error:', cleanupError);
      }
    }
    // Delete temp file on error
    if (tempFileUri) {
      try {
        await FileSystem.deleteAsync(tempFileUri, { idempotent: true });
      } catch (cleanupError) {
        console.error('Temp file cleanup error:', cleanupError);
      }
    }
  }
}

/**
 * Process any pending speak requests that were deferred while app was backgrounded
 */
async function processPendingSpeakQueue() {
  // Guard against concurrent execution
  if (isProcessingPendingQueue || pendingSpeakQueue.length === 0) {
    return;
  }

  isProcessingPendingQueue = true;

  try {
    console.log(`Processing ${pendingSpeakQueue.length} deferred speak requests`);
    
    // Atomically extract all pending messages to avoid race conditions
    // Any new messages added during processing will be handled in the next call
    const messagesToProcess = pendingSpeakQueue.splice(0);
    
    for (const message of messagesToProcess) {
      try {
        await speakNotification(message);
        // Small delay between messages
        await new Promise(resolve => setTimeout(resolve, 500));
      } catch (error) {
        console.error('Error processing deferred speak request:', error);
      }
    }
  } finally {
    isProcessingPendingQueue = false;
  }
}

/**
 * Convert a Blob to base64 string
 * Uses FileReader to read the blob as a data URL, then extracts the base64 portion.
 * Includes comprehensive error handling for invalid data URLs and reader errors.
 * 
 * @param {Blob} blob - The Blob object to convert (typically audio data)
 * @returns {Promise<string>} Promise that resolves to the base64-encoded string (without data URL prefix)
 * @throws {Error} If FileReader fails, returns null result, or produces invalid data URL format
 */
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      // Validate that we have a result
      if (!reader.result) {
        reject(new Error('FileReader returned null result'));
        return;
      }
      
      // Remove the data URL prefix (e.g., "data:audio/mpeg;base64,")
      const resultStr = String(reader.result);
      const commaIndex = resultStr.indexOf(',');
      
      if (commaIndex === -1) {
        reject(new Error('Invalid data URL format: no comma found'));
        return;
      }
      
      const base64 = resultStr.substring(commaIndex + 1);
      if (!base64) {
        reject(new Error('Empty base64 data after data URL prefix'));
        return;
      }
      
      resolve(base64);
    };
    reader.onerror = () => {
      reject(new Error('FileReader error: ' + (reader.error?.message || 'Unknown error')));
    };
    reader.readAsDataURL(blob);
  });
}

/**
 * Poll for new notifications (fallback for development/testing)
 * @param {Function} onNewNotifications - Callback with array of new notifications
 * @param {number} intervalMs - Polling interval in milliseconds (default: 30000)
 * @returns {Function} Cleanup function to stop polling
 */
export function startNotificationPolling(onNewNotifications, intervalMs = 30000) {
  let lastTimestamp = new Date().toISOString();
  let intervalId = null;

  const poll = async () => {
    try {
      const baseUrl = await getBaseUrl();
      const headers = await getHeaders();
      const response = await fetch(
        `${baseUrl}/v1/notifications?since=${lastTimestamp}&limit=20`,
        {
          method: 'GET',
          headers,
        }
      );

      if (!response.ok) {
        console.error('Polling failed:', response.status);
        return;
      }

      const data = await response.json();
      const notifications = data.notifications || [];

      if (notifications.length > 0) {
        console.log(`Received ${notifications.length} new notifications`);
        
        // Queue notifications for sequential playback
        for (const notification of notifications) {
          if (notification.message) {
            queueNotification(notification.message);
          }
          // Update timestamp to latest
          if (notification.created_at) {
            lastTimestamp = notification.created_at;
          }
        }

        // Call callback with new notifications
        if (onNewNotifications) {
          onNewNotifications(notifications);
        }
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  };

  // Start polling
  intervalId = setInterval(poll, intervalMs);

  // Return cleanup function
  return () => {
    if (intervalId) {
      clearInterval(intervalId);
    }
  };
}

/**
 * Queue a notification message for TTS playback
 * @param {string} message - Message to queue
 */
function queueNotification(message) {
  notificationQueue.push(message);
  processNotificationQueue();
}

/**
 * Process queued notifications sequentially
 */
async function processNotificationQueue() {
  if (isProcessingQueue || notificationQueue.length === 0) {
    return;
  }

  isProcessingQueue = true;

  while (notificationQueue.length > 0) {
    const message = notificationQueue.shift();
    try {
      await speakNotification(message);
      // Small delay between notifications
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (error) {
      console.error('Error processing notification from queue:', error);
    }
  }

  isProcessingQueue = false;
}

/**
 * Manually check for and speak latest notification (useful for testing)
 * @returns {Promise<Object|null>} Latest notification or null
 */
export async function checkAndSpeakLatestNotification() {
  try {
    const baseUrl = await getBaseUrl();
    const headers = await getHeaders();
    const response = await fetch(
      `${baseUrl}/v1/notifications?limit=1`,
      {
        method: 'GET',
        headers,
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch notifications: ${response.status}`);
    }

    const data = await response.json();
    const notifications = data.notifications || [];

    if (notifications.length > 0) {
      const latest = notifications[0];
      if (latest.message) {
        await speakNotification(latest.message);
      }
      return latest;
    }

    return null;
  } catch (error) {
    console.error('Failed to check latest notification:', error);
    throw error;
  }
}

/**
 * DEV-ONLY: Simulate a notification with a custom message for testing TTS playback
 * This helps verify that the notification → TTS flow works without needing a real push
 * @param {string} message - The message to speak
 * @returns {Promise<void>}
 * @throws {Error} If called in production mode
 */
export async function simulateNotificationForDev(message = 'This is a test notification') {
  // Runtime check to prevent use in production
  if (!__DEV__) {
    throw new Error('simulateNotificationForDev is only available in development mode');
  }
  
  console.log('[DEV] Simulating notification with message:', message);
  
  try {
    // Create a mock notification object similar to what Expo sends
    const mockNotification = {
      request: {
        content: {
          data: {
            message: message,
            notification_id: 'dev-test-' + Date.now(),
          },
          body: message,
        },
      },
    };

    // Handle the notification as if it came from Expo
    await handleNotification(mockNotification);
    
    console.log('[DEV] Simulated notification processed successfully');
  } catch (error) {
    console.error('[DEV] Failed to simulate notification:', error);
    throw error;
  }
}

/**
 * Get the current debug state for UI display
 * @returns {Object} Debug state with last notification, spoken text, and error
 */
export function getDebugState() {
  return {
    ...debugState,
    isAppInBackground,
    pendingCount: pendingSpeakQueue.length,
  };
}
