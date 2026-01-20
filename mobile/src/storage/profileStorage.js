/**
 * Profile Storage
 * 
 * Persists the selected user profile (workout, kitchen, commute, default)
 * in AsyncStorage and provides utilities for getting/setting the profile.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

const PROFILE_STORAGE_KEY = '@lift_profile';

/**
 * Valid profile values
 */
export const PROFILES = ['default', 'workout', 'commute', 'kitchen'];

/**
 * Get the stored profile
 * @returns {Promise<string>} The stored profile, or 'default' if not set
 */
export async function getProfile() {
  try {
    const profile = await AsyncStorage.getItem(PROFILE_STORAGE_KEY);
    if (profile && PROFILES.includes(profile)) {
      return profile;
    }
    return 'default';
  } catch (error) {
    console.error('Failed to load profile from storage:', error);
    return 'default';
  }
}

/**
 * Set the profile
 * @param {string} profile - The profile to store (workout, kitchen, commute, default)
 * @returns {Promise<void>}
 */
export async function setProfile(profile) {
  if (!PROFILES.includes(profile)) {
    throw new Error(`Invalid profile: ${profile}. Must be one of: ${PROFILES.join(', ')}`);
  }
  try {
    await AsyncStorage.setItem(PROFILE_STORAGE_KEY, profile);
  } catch (error) {
    console.error('Failed to save profile to storage:', error);
    throw error;
  }
}
