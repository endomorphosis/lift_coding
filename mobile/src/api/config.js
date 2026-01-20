/**
 * API Configuration
 * Update BASE_URL to point to your backend server
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// Default to localhost for development
// Update this based on your environment
export const DEFAULT_BASE_URL = 'http://localhost:8080';
let BASE_URL = DEFAULT_BASE_URL;

// Session management
let sessionToken = null;
let userId = null;
let settingsLoadPromise = null;

const STORAGE_KEYS = {
  USER_ID: '@handsfree_user_id',
  BASE_URL: '@handsfree_base_url',
  USE_CUSTOM_URL: '@handsfree_use_custom_url',
  SPEAK_NOTIFICATIONS: '@handsfree_speak_notifications',
  GITHUB_CONNECTION_ID: '@github_connection_id',
  GITHUB_OAUTH_PENDING: '@github_oauth_pending',
};

/**
 * Load settings from AsyncStorage
 * This is called automatically before making API requests
 * Uses a promise to prevent race conditions
 */
async function loadSettings() {
  // If already loading or loaded, return the existing promise
  if (settingsLoadPromise) {
    return settingsLoadPromise;
  }

  settingsLoadPromise = (async () => {
    try {
      const savedUserId = await AsyncStorage.getItem(STORAGE_KEYS.USER_ID);
      const savedBaseUrl = await AsyncStorage.getItem(STORAGE_KEYS.BASE_URL);
      const savedUseCustomUrl = await AsyncStorage.getItem(STORAGE_KEYS.USE_CUSTOM_URL);

      if (savedUserId) {
        userId = savedUserId;
      }

      if (savedUseCustomUrl === 'true' && savedBaseUrl) {
        BASE_URL = savedBaseUrl;
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  })();

  return settingsLoadPromise;
}

/**
 * Get the current BASE_URL
 * Loads settings from storage if not already loaded
 */
export async function getBaseUrl() {
  try {
    await loadSettings();
  } catch (error) {
    console.error('Failed to load base URL settings:', error);
  }
  return BASE_URL;
}

export function setSession(token, user) {
  sessionToken = token;
  userId = user;
}

export function getSession() {
  return { token: sessionToken, userId };
}

export function clearSession() {
  sessionToken = null;
  userId = null;
}

/**
 * Get headers for API requests
 * Loads settings from storage if not already loaded
 */
export async function getHeaders(includeAuth = true) {
  await loadSettings();

  const headers = {
    'Content-Type': 'application/json',
  };

  if (includeAuth && sessionToken) {
    headers['Authorization'] = `Bearer ${sessionToken}`;
  }

  if (userId) {
    headers['X-User-ID'] = userId;
  }

  return headers;
}

/**
 * Get whether notifications should be spoken
 * Defaults to true in development mode, false in production
 */
export async function getSpeakNotifications() {
  try {
    const value = await AsyncStorage.getItem(STORAGE_KEYS.SPEAK_NOTIFICATIONS);
    if (value === null) {
      // Default to ON in dev builds, OFF in production
      return __DEV__;
    }
    return value === 'true';
  } catch (error) {
    console.error('Failed to get speak notifications setting:', error);
    return __DEV__;
  }
}

/**
 * Set whether notifications should be spoken
 */
export async function setSpeakNotifications(enabled) {
  try {
    await AsyncStorage.setItem(STORAGE_KEYS.SPEAK_NOTIFICATIONS, enabled.toString());
  } catch (error) {
    console.error('Failed to set speak notifications setting:', error);
  }
}

// Export BASE_URL for backwards compatibility
// Note: This is the initial value and may change after loadSettings() is called
export { BASE_URL };

// Export STORAGE_KEYS for use across the app
export { STORAGE_KEYS };
