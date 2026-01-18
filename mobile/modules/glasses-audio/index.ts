import { NativeModulesProxy, EventEmitter, Subscription } from 'expo-modules-core';

// This module will be implemented as a native module for iOS
// For now, we'll create a placeholder that returns mock data for development
const GlassesAudioModule = NativeModulesProxy.GlassesAudio;

export interface AudioRoute {
  inputs: string[];
  outputs: string[];
  sampleRate: number;
}

export interface AudioRouteChangeEvent {
  route: AudioRoute;
}

export class GlassesAudio {
  /**
   * Check if native module is available
   */
  static isAvailable(): boolean {
    return !!GlassesAudioModule;
  }

  /**
   * Start monitoring audio route changes
   * Returns the current route immediately
   */
  static async startMonitoring(): Promise<AudioRoute> {
    if (!GlassesAudioModule) {
      throw new Error('GlassesAudio native module not available. Need to build with expo-dev-client.');
    }
    return await GlassesAudioModule.startMonitoring();
  }

  /**
   * Stop monitoring audio route changes
   */
  static async stopMonitoring(): Promise<void> {
    if (!GlassesAudioModule) return;
    return await GlassesAudioModule.stopMonitoring();
  }

  /**
   * Get the current audio route
   */
  static async getCurrentRoute(): Promise<AudioRoute> {
    if (!GlassesAudioModule) {
      // Return mock data for development without native module
      return {
        inputs: ['Built-in Microphone'],
        outputs: ['Built-in Speaker'],
        sampleRate: 48000
      };
    }
    return await GlassesAudioModule.getCurrentRoute();
  }

  /**
   * Start recording audio from the current input
   * @param outputPath - Path where to save the recording
   */
  static async startRecording(outputPath: string): Promise<void> {
    if (!GlassesAudioModule) {
      throw new Error('GlassesAudio native module not available');
    }
    return await GlassesAudioModule.startRecording(outputPath);
  }

  /**
   * Stop the current recording
   */
  static async stopRecording(): Promise<void> {
    if (!GlassesAudioModule) return;
    return await GlassesAudioModule.stopRecording();
  }

  /**
   * Play an audio file through the current output
   * @param filePath - Path to the audio file to play
   */
  static async playAudio(filePath: string): Promise<void> {
    if (!GlassesAudioModule) {
      throw new Error('GlassesAudio native module not available');
    }
    return await GlassesAudioModule.playAudio(filePath);
  }

  /**
   * Stop audio playback
   */
  static async stopPlayback(): Promise<void> {
    if (!GlassesAudioModule) return;
    return await GlassesAudioModule.stopPlayback();
  }

  /**
   * Subscribe to audio route change events
   */
  static addAudioRouteChangeListener(
    listener: (event: AudioRouteChangeEvent) => void
  ): Subscription | null {
    if (!GlassesAudioModule) {
      console.warn('GlassesAudio native module not available, audio route change events will not fire');
      return null;
    }
    const emitter = new EventEmitter(GlassesAudioModule);
    return emitter.addListener<AudioRouteChangeEvent>('onAudioRouteChange', listener);
  }
}

export default GlassesAudio;
