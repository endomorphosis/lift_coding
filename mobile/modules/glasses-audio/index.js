import { NativeModules, NativeEventEmitter, Platform } from 'react-native';

const { GlassesAudioModule } = NativeModules;

let eventEmitter = null;
if (GlassesAudioModule) {
  eventEmitter = new NativeEventEmitter(GlassesAudioModule);
}

export const GlassesAudio = {
  // Check if native module is available
  isAvailable() {
    return Platform.OS === 'ios' && GlassesAudioModule != null;
  },

  // Audio Route Monitor
  async startRouteMonitoring(callback) {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    
    const subscription = eventEmitter.addListener('audioRouteChanged', callback);
    await GlassesAudioModule.startRouteMonitoring();
    
    return subscription;
  },

  async stopRouteMonitoring() {
    if (!this.isAvailable()) return;
    await GlassesAudioModule.stopRouteMonitoring();
  },

  async getCurrentRoute() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.getCurrentRoute();
  },

  async isBluetoothConnected() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.isBluetoothConnected();
  },

  async getDetailedRouteInfo() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.getDetailedRouteInfo();
  },

  // Recorder
  async startRecording(duration) {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.startRecording(duration || 10.0);
  },

  async stopRecording() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.stopRecording();
  },

  async isRecording() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.isRecording();
  },

  async getRecordingDuration() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.getRecordingDuration();
  },

  // Player
  async playAudio(fileUri) {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.playAudio(fileUri);
  },

  async stopPlayback() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.stopPlayback();
  },

  async pausePlayback() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.pausePlayback();
  },

  async resumePlayback() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.resumePlayback();
  },

  async isPlaying() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.isPlaying();
  },

  async getPlaybackProgress() {
    if (!this.isAvailable()) {
      throw new Error('Glasses audio module not available');
    }
    return await GlassesAudioModule.getPlaybackProgress();
  },
};

export default GlassesAudio;
