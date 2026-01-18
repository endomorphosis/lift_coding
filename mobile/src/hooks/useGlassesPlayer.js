import { Platform } from 'react-native';

let GlassesAudioPlayer = null;

// Try to load the native module, but gracefully handle if it's not available
try {
  if (Platform.OS === 'ios') {
    GlassesAudioPlayer = require('../../modules/glasses-audio-player').default;
  }
} catch (error) {
  console.log('Native glasses audio player not available:', error.message);
}

/**
 * Play audio through Meta AI Glasses (iOS only)
 * @param {string} fileUri - File URI (file:// or local path)
 * @returns {Promise<void>}
 */
export async function playAudioThroughGlasses(fileUri) {
  if (!GlassesAudioPlayer) {
    throw new Error('Native glasses audio player not available. This feature requires a development build on iOS.');
  }
  
  return await GlassesAudioPlayer.playAudio(fileUri);
}

/**
 * Stop audio playback through glasses
 * @returns {Promise<void>}
 */
export async function stopGlassesAudio() {
  if (!GlassesAudioPlayer) {
    throw new Error('Native glasses audio player not available.');
  }
  
  return await GlassesAudioPlayer.stopAudio();
}

/**
 * Check if audio is currently playing through glasses
 * @returns {Promise<boolean>}
 */
export async function isGlassesAudioPlaying() {
  if (!GlassesAudioPlayer) {
    return false;
  }
  
  return await GlassesAudioPlayer.isPlaying();
}

/**
 * Check if the native glasses audio player is available
 * @returns {boolean}
 */
export function isGlassesPlayerAvailable() {
  return GlassesAudioPlayer !== null && Platform.OS === 'ios';
}
