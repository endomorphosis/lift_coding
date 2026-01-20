/**
 * Notification Settings Utilities
 * 
 * Helper functions for managing notification-related settings
 * stored in AsyncStorage.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY_AUTO_SPEAK = '@handsfree_auto_speak_notifications';
const STORAGE_KEY_PUSH_TOKEN = '@handsfree_push_token';

/**
 * Get the auto-speak notification setting
 * @returns {Promise<boolean>} Whether auto-speak is enabled
 */
export async function getAutoSpeakEnabled() {
  try {
    const value = await AsyncStorage.getItem(STORAGE_KEY_AUTO_SPEAK);
    return value === 'true';
  } catch (error) {
    console.error('Failed to get auto-speak setting:', error);
    return false; // Default to false
  }
}

/**
 * Set the auto-speak notification setting
 * @param {boolean} enabled - Whether to enable auto-speak
 * @returns {Promise<void>}
 */
export async function setAutoSpeakEnabled(enabled) {
  try {
    await AsyncStorage.setItem(STORAGE_KEY_AUTO_SPEAK, enabled.toString());
  } catch (error) {
    console.error('Failed to set auto-speak setting:', error);
    throw error;
  }
}

/**
 * Get the stored push token
 * @returns {Promise<string|null>} The push token or null if not set
 */
export async function getPushToken() {
  try {
    const token = await AsyncStorage.getItem(STORAGE_KEY_PUSH_TOKEN);
    return token;
  } catch (error) {
    console.error('Failed to get push token:', error);
    return null;
  }
}

/**
 * Set the push token
 * @param {string} token - The push token to store
 * @returns {Promise<void>}
 */
export async function setPushToken(token) {
  try {
    if (!token || typeof token !== 'string') {
      throw new Error('Invalid push token: token must be a non-empty string');
    }
    await AsyncStorage.setItem(STORAGE_KEY_PUSH_TOKEN, token);
  } catch (error) {
    console.error('Failed to set push token:', error);
    throw error;
  }
}
