/**
 * API Configuration
 * Update BASE_URL to point to your backend server
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// Default to localhost for development
// Update this based on your environment
let BASE_URL = 'http://localhost:8080';

// Session management
let sessionToken = null;
let userId = null;
let settingsLoaded = false;

const STORAGE_KEYS = {
  USER_ID: '@handsfree_user_id',
  BASE_URL: '@handsfree_base_url',
  USE_CUSTOM_URL: '@handsfree_use_custom_url',
};

/**
 * Load settings from AsyncStorage
 * This is called automatically before making API requests
 */
async function loadSettings() {
  if (settingsLoaded) return;

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

    settingsLoaded = true;
  } catch (error) {
    console.error('Failed to load settings:', error);
  }
}

/**
 * Get the current BASE_URL
 * Loads settings from storage if not already loaded
 */
export async function getBaseUrl() {
  await loadSettings();
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

// Export BASE_URL for backwards compatibility
// Note: This is the initial value and may change after loadSettings() is called
export { BASE_URL };
