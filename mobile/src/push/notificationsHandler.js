/**
 * Notifications Handler
 * 
 * Handles:
 * - Setting up notification listeners
 * - Parsing incoming notification payloads
 * - Fetching TTS audio and playing it
 * - Polling fallback for development/testing
 */

import * as Notifications from 'expo-notifications';
import { Audio } from 'expo-av';
import { BASE_URL, getHeaders } from '../api/config';
import { fetchTTS } from '../api/client';

// Notification queue for sequential TTS playback
let notificationQueue = [];
let isProcessingQueue = false;

// Configure how notifications are handled when app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false, // We'll play TTS instead
    shouldSetBadge: false,
  }),
});

/**
 * Set up notification listeners
 * @param {Function} onNotification - Callback when notification is received
 */
export function setupNotificationListeners(onNotification) {
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
  };
}

/**
 * Handle an incoming notification
 * @param {Object} notification - Notification object from Expo
 */
async function handleNotification(notification) {
  const data = notification.request.content.data;
  const body = notification.request.content.body;
  
  // Extract message from notification
  let message = data.message || body || 'New notification';
  
  // If notification has an ID, we could fetch full details from backend
  if (data.notification_id) {
    try {
      const details = await fetchNotificationDetails(data.notification_id);
      if (details && details.message) {
        message = details.message;
      }
    } catch (error) {
      console.error('Failed to fetch notification details:', error);
      // Fall back to basic message
    }
  }

  // Speak the notification via TTS
  await speakNotification(message);
}

/**
 * Fetch full notification details from backend
 * @param {string} notificationId - Notification ID
 * @returns {Promise<Object>} Notification details
 */
async function fetchNotificationDetails(notificationId) {
  const response = await fetch(
    `${BASE_URL}/v1/notifications/${notificationId}`,
    {
      method: 'GET',
      headers: getHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch notification: ${response.status}`);
  }

  return await response.json();
}

/**
 * Convert notification text to speech and play it
 * @param {string} message - Message to speak
 */
export async function speakNotification(message) {
  let sound = null;
  
  try {
    console.log('Speaking notification:', message);
    
    // Fetch TTS audio from backend
    const audioBlob = await fetchTTS(message);
    
    // Use URL.createObjectURL for better performance
    const audioUri = URL.createObjectURL(audioBlob);

    // Configure audio session for playback
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
      staysActiveInBackground: true,
      shouldDuckAndroid: true,
    });

    // Play the audio
    const soundObject = await Audio.Sound.createAsync(
      { uri: audioUri },
      { shouldPlay: true }
    );
    sound = soundObject.sound;

    // Clean up after playback completes
    sound.setOnPlaybackStatusUpdate(async (status) => {
      if (status.didJustFinish || status.error) {
        try {
          await sound.unloadAsync();
          URL.revokeObjectURL(audioUri);
        } catch (cleanupError) {
          console.error('Cleanup error:', cleanupError);
        }
      }
    });

  } catch (error) {
    console.error('Failed to speak notification:', error);
    // Clean up on error
    if (sound) {
      try {
        await sound.unloadAsync();
      } catch (cleanupError) {
        console.error('Sound cleanup error:', cleanupError);
      }
    }
  }
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
      const response = await fetch(
        `${BASE_URL}/v1/notifications?since=${lastTimestamp}&limit=20`,
        {
          method: 'GET',
          headers: getHeaders(),
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
    const response = await fetch(
      `${BASE_URL}/v1/notifications?limit=1`,
      {
        method: 'GET',
        headers: getHeaders(),
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
