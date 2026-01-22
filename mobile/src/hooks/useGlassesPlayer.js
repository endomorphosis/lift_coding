import { getGlassesAudio } from '../native/glassesAudio';

let ExpoGlassesAudio = null;
let lastIsPlaying = false;
let playbackStatusSubscription = null;

// Try to load the native module, but gracefully handle if it's not available
async function ensurePlaybackListener(module) {
  if (!module || playbackStatusSubscription) return;

  try {
    playbackStatusSubscription = module.addPlaybackStatusListener((event) => {
      if (event && typeof event.isPlaying === 'boolean') {
        lastIsPlaying = event.isPlaying;
      }
    });
  } catch (error) {
    console.warn(
      'Failed to add glasses playback status listener; events may not be available in this runtime:',
      error
    );
  }
}

/**
 * Play audio through Meta AI Glasses (iOS only)
 * @param {string} fileUri - File URI (file:// or local path)
 * @returns {Promise<void>}
 */
export async function playAudioThroughGlasses(fileUri) {
  const module = await getGlassesAudio();
  ExpoGlassesAudio = module;
  await ensurePlaybackListener(module);
  await module.playAudio(fileUri);
}

/**
 * Stop audio playback through glasses
 * @returns {Promise<void>}
 */
export async function stopGlassesAudio() {
  const module = await getGlassesAudio();
  ExpoGlassesAudio = module;
  await ensurePlaybackListener(module);
  await module.stopPlayback();
}

/**
 * Check if audio is currently playing through glasses
 * Note: Returns cached playback state from the last event or API call.
 * May be stale if playback completes naturally without calling stopGlassesAudio().
 * @returns {boolean}
 */
export function isGlassesAudioPlaying() {
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
  return ExpoGlassesAudio !== null;
}
