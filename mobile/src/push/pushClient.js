/**
 * Push Notifications Client
 * 
 * Handles:
 * - Requesting push notification permissions
 * - Obtaining device push token (Expo)
 * - Registering/unregistering with backend
 */

import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { getBaseUrl, getHeaders } from '../api/config';

/**
 * Request push notification permissions and get token
 * @returns {Promise<string|null>} Push token or null if failed/not available
 */
export async function registerForPushAsync() {
  // Check if running on physical device
  if (!Device.isDevice) {
    console.log('Push notifications only work on physical devices');
    return null;
  }

  // Request permissions
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;
  
  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('Push notification permission not granted');
    return null;
  }

  // Get Expo push token
  try {
    const tokenData = await Notifications.getExpoPushTokenAsync();
    return tokenData.data;
  } catch (error) {
    console.error('Failed to get push token:', error);
    return null;
  }
}

/**
 * Register push token with backend
 * @param {string} token - Push token from Expo
 * @param {string} platform - Platform identifier (default: 'expo')
 * @returns {Promise<Object>} Subscription object with { id, endpoint, platform, ... }
 */
export async function registerSubscriptionWithBackend(token, platform = 'expo') {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(`${baseUrl}/v1/notifications/subscriptions`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      endpoint: token,
      platform: platform,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Failed to register subscription: ${response.status}`);
  }

  const subscription = await response.json();
  return subscription;
}

/**
 * Unregister push subscription from backend
 * @param {string} subscriptionId - Subscription ID to delete
 * @returns {Promise<void>}
 */
export async function unregisterSubscriptionWithBackend(subscriptionId) {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(
    `${baseUrl}/v1/notifications/subscriptions/${subscriptionId}`,
    {
      method: 'DELETE',
      headers,
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to unregister subscription: ${response.status}`);
  }
}

/**
 * List all subscriptions for the current user
 * @returns {Promise<Array>} Array of subscription objects
 */
export async function listSubscriptions() {
  const baseUrl = await getBaseUrl();
  const headers = await getHeaders();

  const response = await fetch(`${baseUrl}/v1/notifications/subscriptions`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    throw new Error(`Failed to list subscriptions: ${response.status}`);
  }

  const data = await response.json();
  return data.subscriptions || [];
}
