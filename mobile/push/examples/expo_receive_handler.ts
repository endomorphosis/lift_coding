// Expo TypeScript: Push Notification Receive Handler with TTS Playback
//
// This example demonstrates how to handle incoming push notifications
// and play the notification message using TTS audio from the backend.
//
// Usage:
// 1. Install: expo install expo-notifications expo-av
// 2. Call setupNotificationHandlers() during app initialization
// 3. Ensure Audio permissions are granted for playback

import * as Notifications from 'expo-notifications';
import { Audio } from 'expo-av';
import { Platform } from 'react-native';

const BACKEND_URL = 'http://localhost:8080'; // Change to production URL
const USER_ID = '00000000-0000-0000-0000-000000000001'; // Get from auth

let currentSound: Audio.Sound | null = null;

/**
 * Setup notification handlers for foreground and background
 * @returns Cleanup function to remove listeners
 */
export function setupNotificationHandlers(): () => void {
  // Configure notification handler
  Notifications.setNotificationHandler({
    handleNotification: async (notification) => {
      // Handle notification in foreground
      await handleNotificationReceived(notification);

      return {
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
      };
    },
  });

  // Add listener for notifications received while app is in foreground
  const receivedSubscription = Notifications.addNotificationReceivedListener(
    handleNotificationReceived
  );

  // Add listener for user tapping on notification
  const responseSubscription = Notifications.addNotificationResponseReceivedListener(
    (response) => {
      const notification = response.notification;
      console.log('User tapped notification:', notification.request.identifier);
      handleNotificationReceived(notification);
    }
  );

  // Return cleanup function
  return () => {
    receivedSubscription.remove();
    responseSubscription.remove();
  };
}

/**
 * Handle received notification
 */
async function handleNotificationReceived(
  notification: Notifications.Notification
): Promise<void> {
  const data = notification.request.content.data;

  console.log('Notification received:', {
    title: notification.request.content.title,
    body: notification.request.content.body,
    data,
  });

  const notificationId = data.notification_id as string;
  const eventType = data.event_type as string;
  const message = (data.message as string) || notification.request.content.body;

  console.log(`Event type: ${eventType}`);

  if (message) {
    // Speak the notification message
    await speakNotification(message, notificationId);
  } else if (notificationId) {
    // Fetch notification details from backend if not in payload
    await fetchNotificationDetails(notificationId);
  }
}

/**
 * Fetch notification details from backend
 */
async function fetchNotificationDetails(notificationId: string): Promise<void> {
  try {
    const response = await fetch(`${BACKEND_URL}/v1/notifications`, {
      headers: {
        'X-User-ID': USER_ID,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch notifications: ${response.statusText}`);
    }

    const data = await response.json();
    const notification = data.notifications.find((n: any) => n.id === notificationId);

    if (notification && notification.message) {
      await speakNotification(notification.message, notificationId);
    }
  } catch (error) {
    console.error('Failed to fetch notification details:', error);
  }
}

/**
 * Generate TTS audio and play it
 */
async function speakNotification(
  message: string,
  notificationId: string | undefined
): Promise<void> {
  console.log('Speaking notification:', message);

  try {
    // Fetch TTS audio from backend
    const audioData = await fetchTTS(message);

    if (audioData) {
      await playAudio(audioData);
    } else {
      console.error('Failed to fetch TTS audio');
    }
  } catch (error) {
    console.error('Error speaking notification:', error);
  }
}

/**
 * Fetch TTS audio from backend
 */
async function fetchTTS(text: string): Promise<ArrayBuffer | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/v1/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': USER_ID,
      },
      body: JSON.stringify({
        text: text,
        format: 'mp3',
        voice: 'default',
      }),
    });

    if (!response.ok) {
      throw new Error(`TTS request failed: ${response.statusText}`);
    }

    const audioData = await response.arrayBuffer();
    console.log(`TTS audio fetched successfully (${audioData.byteLength} bytes)`);

    return audioData;
  } catch (error) {
    console.error('Failed to fetch TTS audio:', error);
    return null;
  }
}

/**
 * Play audio data using Expo AV
 */
async function playAudio(audioData: ArrayBuffer): Promise<void> {
  try {
    // Release previous sound if exists
    if (currentSound) {
      await currentSound.unloadAsync();
      currentSound = null;
    }

    // Configure audio mode for playback
    await Audio.setAudioModeAsync({
      allowsRecordingIOS: false,
      playsInSilentModeIOS: true,
      staysActiveInBackground: true,
      shouldDuckAndroid: true,
      playThroughEarpieceAndroid: false,
    });

    // Convert ArrayBuffer to base64 for Expo
    const base64Audio = arrayBufferToBase64(audioData);
    const uri = `data:audio/mp3;base64,${base64Audio}`;

    // Create and load sound
    const { sound } = await Audio.Sound.createAsync(
      { uri },
      { shouldPlay: true }
    );

    currentSound = sound;

    // Set up completion handler
    sound.setOnPlaybackStatusUpdate((status) => {
      if (status.isLoaded && status.didJustFinish) {
        console.log('TTS playback completed');
        sound.unloadAsync();
        currentSound = null;
      }
    });

    console.log('Playing TTS audio');
  } catch (error) {
    console.error('Failed to play audio:', error);
  }
}

/**
 * Convert ArrayBuffer to base64 string
 */
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Polling fallback for when push notifications aren't available
 */
export async function startPollingForNotifications(
  intervalMs: number = 30000
): Promise<() => void> {
  let lastTimestamp = new Date().toISOString();

  const pollInterval = setInterval(async () => {
    try {
      const response = await fetch(
        `${BACKEND_URL}/v1/notifications?since=${lastTimestamp}&limit=20`,
        {
          headers: {
            'X-User-ID': USER_ID,
          },
        }
      );

      if (!response.ok) {
        console.error('Polling failed:', response.statusText);
        return;
      }

      const data = await response.json();

      if (data.notifications && data.notifications.length > 0) {
        console.log(`Received ${data.notifications.length} notification(s) via polling`);

        for (const notification of data.notifications) {
          await speakNotification(notification.message, notification.id);
          lastTimestamp = notification.created_at;
        }
      }
    } catch (error) {
      console.error('Polling error:', error);
    }
  }, intervalMs);

  // Return cleanup function
  return () => {
    clearInterval(pollInterval);
    console.log('Stopped polling for notifications');
  };
}

/**
 * Stop audio playback
 */
export async function stopAudioPlayback(): Promise<void> {
  if (currentSound) {
    await currentSound.stopAsync();
    await currentSound.unloadAsync();
    currentSound = null;
    console.log('Audio playback stopped');
  }
}

// Example usage in App.tsx:
/*
import { useEffect } from 'react';
import { setupNotificationHandlers, startPollingForNotifications } from './notificationHandler';

export default function App() {
  useEffect(() => {
    // Setup push notification handlers
    const cleanupNotifications = setupNotificationHandlers();

    // Optional: Start polling fallback for development/testing
    // const stopPolling = await startPollingForNotifications(30000);

    return () => {
      cleanupNotifications();
      // stopPolling && stopPolling();
    };
  }, []);

  return (
    // Your app components
  );
}
*/
