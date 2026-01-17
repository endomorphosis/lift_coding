// Expo TypeScript: Push Notification Token Registration
//
// This example demonstrates how to request notification permissions,
// obtain an Expo push token, and register it with the backend.
//
// Usage:
// 1. Install: expo install expo-notifications expo-device
// 2. Call registerForPushNotifications() during app initialization
// 3. Store the returned token for later use

import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = 'http://localhost:8080'; // Change to production URL
const USER_ID = '00000000-0000-0000-0000-000000000001'; // Get from auth
const SUBSCRIPTION_ID_KEY = 'push_subscription_id';

/**
 * Request notification permissions and register push token with backend
 * @returns Push token if successful, null otherwise
 */
export async function registerForPushNotifications(): Promise<string | null> {
  // Check if running on physical device (required for push notifications)
  if (!Device.isDevice) {
    console.warn('Push notifications only work on physical devices, not simulators/emulators');
    return null;
  }

  try {
    // Request permission
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== 'granted') {
      console.warn('Notification permission not granted');
      return null;
    }

    console.log('Notification permission granted');

    // Get Expo push token
    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: 'your-expo-project-id', // Replace with your Expo project ID
    });

    const token = tokenData.data;
    console.log('Expo push token:', token);

    // Register with backend
    await registerTokenWithBackend(token, 'expo');

    return token;
  } catch (error) {
    console.error('Error registering for push notifications:', error);
    return null;
  }
}

/**
 * Register push token with backend API
 */
async function registerTokenWithBackend(token: string, platform: string): Promise<void> {
  try {
    const response = await fetch(`${BACKEND_URL}/v1/notifications/subscriptions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': USER_ID,
      },
      body: JSON.stringify({
        endpoint: token,
        platform: platform,
      }),
    });

    if (!response.ok) {
      throw new Error(`Token registration failed: ${response.statusText}`);
    }

    const subscription = await response.json();
    console.log('Token registered successfully. Subscription ID:', subscription.id);

    // Store subscription ID for later deletion
    await AsyncStorage.setItem(SUBSCRIPTION_ID_KEY, subscription.id);
  } catch (error) {
    console.error('Failed to register token with backend:', error);
    throw error;
  }
}

/**
 * Unregister push notification subscription from backend
 */
export async function unregisterFromBackend(): Promise<void> {
  try {
    const subscriptionId = await AsyncStorage.getItem(SUBSCRIPTION_ID_KEY);

    if (!subscriptionId) {
      console.warn('No subscription to delete');
      return;
    }

    const response = await fetch(
      `${BACKEND_URL}/v1/notifications/subscriptions/${subscriptionId}`,
      {
        method: 'DELETE',
        headers: {
          'X-User-ID': USER_ID,
        },
      }
    );

    if (response.ok || response.status === 204) {
      console.log('Successfully unregistered from push notifications');
      await AsyncStorage.removeItem(SUBSCRIPTION_ID_KEY);
    } else {
      console.error('Unregistration failed:', response.status);
    }
  } catch (error) {
    console.error('Failed to unregister from backend:', error);
  }
}

/**
 * Configure notification behavior (iOS-specific options)
 */
export function configureNotifications(): void {
  // Configure how notifications should be handled when app is in foreground
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
    }),
  });

  // Set notification category actions (iOS)
  if (Platform.OS === 'ios') {
    Notifications.setNotificationCategoryAsync('default', [
      {
        identifier: 'view',
        buttonTitle: 'View',
        options: {
          opensAppToForeground: true,
        },
      },
      {
        identifier: 'dismiss',
        buttonTitle: 'Dismiss',
        options: {
          opensAppToForeground: false,
        },
      },
    ]);
  }
}

// Example usage in App.tsx:
/*
import { useEffect } from 'react';
import { registerForPushNotifications, configureNotifications } from './pushManager';

export default function App() {
  useEffect(() => {
    configureNotifications();
    registerForPushNotifications();
  }, []);

  return (
    // Your app components
  );
}
*/
