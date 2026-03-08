import { NativeModules, NativeEventEmitter, Platform } from 'react-native';

const { GlassesAudioModule } = NativeModules;

// Create event emitter for native events
const glassesAudioEmitter = GlassesAudioModule 
  ? new NativeEventEmitter(GlassesAudioModule)
  : null;

const MODULE_UNAVAILABLE_ERROR =
  'Glasses audio module not available. Make sure you are running on a device with native code compiled.';

function unavailableError() {
  return new Error(MODULE_UNAVAILABLE_ERROR);
}

/**
 * GlassesAudio module for interacting with Meta AI Glasses audio routing
 * 
 * This module provides:
 * - Audio route monitoring (detect Bluetooth glasses connection)
 * - Recording from glasses microphone
 * - Playback through glasses speakers
 * - TTS audio playback
 */
const GlassesAudio = {
  /**
   * Start monitoring audio route changes
   * @returns {Promise<string>} Current route summary
   */
  startMonitoring: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    return await GlassesAudioModule.startMonitoring();
  },

  /**
   * Stop monitoring audio route changes
   */
  stopMonitoring: async () => {
    if (!GlassesAudioModule) {
      return;
    }
    await GlassesAudioModule.stopMonitoring();
  },

  /**
   * Get current audio route information
   * @returns {Promise<string>} Current route summary
   */
  getCurrentRoute: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    return await GlassesAudioModule.getCurrentRoute();
  },

  /**
   * Legacy alias for startMonitoring with optional callback registration.
   * Preserved for older JS callers and tests.
   */
  startRouteMonitoring: async (callback) => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    const summary = await GlassesAudio.startMonitoring();
    if (typeof callback === 'function') {
      GlassesAudio.addRouteChangeListener(callback);
    }
    return summary;
  },

  /**
   * Legacy alias for stopMonitoring.
   */
  stopRouteMonitoring: async () => {
    await GlassesAudio.stopMonitoring();
  },

  /**
   * Legacy helper retained for compatibility.
   */
  isBluetoothConnected: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    const route = await GlassesAudio.getCurrentRoute();
    if (typeof route === 'object' && route !== null) {
      return Boolean(route.isBluetoothConnected);
    }
    return String(route).toLowerCase().includes('bluetooth');
  },

  /**
   * Legacy detailed route info helper retained for compatibility.
   */
  getDetailedRouteInfo: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    return await GlassesAudio.getCurrentRoute();
  },

  /**
   * Start recording audio from glasses microphone
   * @param {number} durationSeconds - Recording duration in seconds
   * @returns {Promise<string>} File path/URI of recorded audio
   */
  startRecording: async (durationSeconds = 10) => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    return await GlassesAudioModule.startRecording(durationSeconds);
  },

  /**
   * Stop recording (if currently recording)
   * @returns {Promise<string>} File path/URI of recorded audio
   */
  stopRecording: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    return await GlassesAudioModule.stopRecording();
  },

  /**
   * Compatibility stub retained for the legacy wrapper contract.
   */
  isRecording: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    if (typeof GlassesAudioModule.isRecording === 'function') {
      return await GlassesAudioModule.isRecording();
    }
    return false;
  },

  /**
   * Compatibility stub retained for the legacy wrapper contract.
   */
  getRecordingDuration: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    if (typeof GlassesAudioModule.getRecordingDuration === 'function') {
      return await GlassesAudioModule.getRecordingDuration();
    }
    return 0;
  },

  /**
   * Play audio file through glasses speakers
   * @param {string} fileUri - File path or URI to play
   * @returns {Promise<void>}
   */
  playAudio: async (fileUri) => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    return await GlassesAudioModule.playAudio(fileUri);
  },

  /**
   * Stop audio playback
   * @returns {Promise<void>}
   */
  stopPlayback: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    return await GlassesAudioModule.stopPlayback();
  },

  /**
   * Compatibility stub retained for the legacy wrapper contract.
   */
  pausePlayback: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    if (typeof GlassesAudioModule.pausePlayback === 'function') {
      return await GlassesAudioModule.pausePlayback();
    }
  },

  /**
   * Compatibility stub retained for the legacy wrapper contract.
   */
  resumePlayback: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    if (typeof GlassesAudioModule.resumePlayback === 'function') {
      return await GlassesAudioModule.resumePlayback();
    }
  },

  /**
   * Compatibility stub retained for the legacy wrapper contract.
   */
  isPlaying: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    if (typeof GlassesAudioModule.isPlaying === 'function') {
      return await GlassesAudioModule.isPlaying();
    }
    return false;
  },

  /**
   * Compatibility stub retained for the legacy wrapper contract.
   */
  getPlaybackProgress: async () => {
    if (!GlassesAudioModule) {
      throw unavailableError();
    }
    if (typeof GlassesAudioModule.getPlaybackProgress === 'function') {
      return await GlassesAudioModule.getPlaybackProgress();
    }
    return 0;
  },

  /**
   * Add listener for audio route changes
   * @param {Function} callback - Called when route changes with route summary string
   * @returns {Object} Subscription object with remove() method
   */
  addRouteChangeListener: (callback) => {
    if (!glassesAudioEmitter) {
      console.warn('GlassesAudioModule event emitter not available');
      return { remove: () => {} };
    }
    return glassesAudioEmitter.addListener('onRouteChange', callback);
  },

  /**
   * Add listener for recording completion
   * @param {Function} callback - Called when recording completes with {fileUri, error}
   * @returns {Object} Subscription object with remove() method
   */
  addRecordingCompleteListener: (callback) => {
    if (!glassesAudioEmitter) {
      console.warn('GlassesAudioModule event emitter not available');
      return { remove: () => {} };
    }
    return glassesAudioEmitter.addListener('onRecordingComplete', callback);
  },

  /**
   * Add listener for playback completion
   * @param {Function} callback - Called when playback completes with {error}
   * @returns {Object} Subscription object with remove() method
   */
  addPlaybackCompleteListener: (callback) => {
    if (!glassesAudioEmitter) {
      console.warn('GlassesAudioModule event emitter not available');
      return { remove: () => {} };
    }
    return glassesAudioEmitter.addListener('onPlaybackComplete', callback);
  },

  /**
   * Check if the native module is available
   * @returns {boolean}
   */
  isAvailable: () => {
    return !!GlassesAudioModule;
  },
};

export default GlassesAudio;
