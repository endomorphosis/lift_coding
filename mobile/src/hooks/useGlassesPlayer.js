import { Platform } from 'react-native';

let ExpoGlassesAudio = null;
let lastIsPlaying = false;
let playbackStatusSubscription = null;

// Try to load the native module, but gracefully handle if it's not available
try {
  ExpoGlassesAudio = require('expo-glasses-audio').default;
} catch (error) {
  console.log('Native expo-glasses-audio module not available:', error.message);
}

function ensurePlaybackListener() {
  if (!ExpoGlassesAudio || playbackStatusSubscription) return;

  try {
    playbackStatusSubscription = ExpoGlassesAudio.addPlaybackStatusListener((event) => {
      if (event && typeof event.isPlaying === 'boolean') {
        lastIsPlaying = event.isPlaying;
      }
    });
  } catch (error) {
    console.warn('Failed to add glasses playback status listener; events may not be available in this runtime:', error);
  }
}

function getExpoGlassesAudioOrThrow() {
  if (!ExpoGlassesAudio) {
    throw new Error(
      'Native expo-glasses-audio module not available. This feature requires a development build (expo-dev-client).'
    );
  }
  return ExpoGlassesAudio;
}

/**
 * Play audio through Meta AI Glasses (iOS only)
 * @param {string} fileUri - File URI (file:// or local path)
 * @returns {Promise<void>}
 */
export async function playAudioThroughGlasses(fileUri) {
  if (Platform.OS !== 'ios') {
    throw new Error('Glasses audio playback is currently supported on iOS only.');
  }

  const module = getExpoGlassesAudioOrThrow();
  ensurePlaybackListener();
  await module.playAudio(fileUri);
  lastIsPlaying = true;
}

/**
 * Stop audio playback through glasses
 * @returns {Promise<void>}
 */
export async function stopGlassesAudio() {
  const module = getExpoGlassesAudioOrThrow();
  ensurePlaybackListener();
  await module.stopPlayback();
  lastIsPlaying = false;
}

/**
 * Check if audio is currently playing through glasses
 * Note: Returns cached playback state from the last event or API call.
 * May be stale if playback completes naturally without calling stopGlassesAudio().
 * @returns {boolean}
 */
export function isGlassesAudioPlaying() {
  ensurePlaybackListener();
  return lastIsPlaying;
}

/**
 * Clean up the playback status subscription
 * Call this when shutting down to prevent memory leaks
 */
export function cleanupGlassesPlayer() {
  if (playbackStatusSubscription) {
    playbackStatusSubscription.remove();
    playbackStatusSubscription = null;
  }
  lastIsPlaying = false;
}

/**
 * Check if the native glasses audio player is available
 * @returns {boolean}
 */
export function isGlassesPlayerAvailable() {
  return ExpoGlassesAudio !== null && Platform.OS === 'ios';
}
