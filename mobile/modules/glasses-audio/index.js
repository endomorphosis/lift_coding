import { NativeModules, NativeEventEmitter, Platform } from 'react-native';

const { GlassesAudioModule } = NativeModules;

// Create event emitter for native events
const glassesAudioEmitter = GlassesAudioModule 
  ? new NativeEventEmitter(GlassesAudioModule)
  : null;

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
      throw new Error('GlassesAudioModule is not available. Make sure you are running on a device with native code compiled.');
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
      throw new Error('GlassesAudioModule is not available');
    }
    return await GlassesAudioModule.getCurrentRoute();
  },

  /**
   * Start recording audio from glasses microphone
   * @param {number} durationSeconds - Recording duration in seconds
   * @returns {Promise<string>} File path/URI of recorded audio
   */
  startRecording: async (durationSeconds = 10) => {
    if (!GlassesAudioModule) {
      throw new Error('GlassesAudioModule is not available');
    }
    return await GlassesAudioModule.startRecording(durationSeconds);
  },

  /**
   * Stop recording (if currently recording)
   * @returns {Promise<string>} File path/URI of recorded audio
   */
  stopRecording: async () => {
    if (!GlassesAudioModule) {
      throw new Error('GlassesAudioModule is not available');
    }
    return await GlassesAudioModule.stopRecording();
  },

  /**
   * Play audio file through glasses speakers
   * @param {string} fileUri - File path or URI to play
   * @returns {Promise<void>}
   */
  playAudio: async (fileUri) => {
    if (!GlassesAudioModule) {
      throw new Error('GlassesAudioModule is not available');
    }
    return await GlassesAudioModule.playAudio(fileUri);
  },

  /**
   * Stop audio playback
   * @returns {Promise<void>}
   */
  stopPlayback: async () => {
    if (!GlassesAudioModule) {
      throw new Error('GlassesAudioModule is not available');
    }
    return await GlassesAudioModule.stopPlayback();
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
