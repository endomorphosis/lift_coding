/**
 * Notification Settings Utilities
 * 
 * Helper functions for managing notification-related settings
 * stored in AsyncStorage.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = '@handsfree_auto_speak_notifications';

/**
 * Get the auto-speak notification setting
 * @returns {Promise<boolean>} Whether auto-speak is enabled
 */
export async function getAutoSpeakEnabled() {
  try {
    const value = await AsyncStorage.getItem(STORAGE_KEY);
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
    await AsyncStorage.setItem(STORAGE_KEY, enabled.toString());
  } catch (error) {
    console.error('Failed to set auto-speak setting:', error);
    throw error;
  }
}
