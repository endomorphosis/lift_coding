import { EventEmitter, Subscription } from 'expo-modules-core';
import { requireNativeModule } from 'expo-modules-core';

export interface AudioDevice {
  id: number;
  type: number;
  typeName: string;
  productName: string;
  address?: string;
}

export interface AudioRouteInfo {
  inputs: AudioDevice[];
  outputs: AudioDevice[];
  audioMode: number;
  audioModeName: string;
  isScoOn: boolean;
  isScoAvailable: boolean;
  isBluetoothConnected: boolean;
  timestamp: number;
}

export interface SimpleAudioRouteInfo {
  inputDevice: string;
  outputDevice: string;
  sampleRate: number;
  isBluetoothConnected: boolean;
}

export interface RecordingResult {
  uri: string;
  duration: number;
  size: number;
}

export interface RecordingProgressEvent {
  isRecording: boolean;
  duration: number;
}

export interface PlaybackStatusEvent {
  isPlaying: boolean;
  error?: string;
}

export interface AudioRouteChangeEvent {
  route: AudioRouteInfo;
}

// Get the native modules
const GlassesAudioModule = requireNativeModule('GlassesAudio');
const ExpoGlassesAudioModule = requireNativeModule('ExpoGlassesAudio');

/**
 * Expo module for Meta AI Glasses audio route monitoring.
 * Provides real-time information about Android audio routing, including
 * Bluetooth connections, SCO status, and device changes.
 */
class GlassesAudio extends EventEmitter {
  constructor() {
    super(GlassesAudioModule);
  }

  /**
   * Get the current audio route information.
   * @returns Promise with current route details including inputs, outputs, and Bluetooth status
   */
  async getCurrentRoute(): Promise<AudioRouteInfo> {
    return await GlassesAudioModule.getCurrentRoute();
  }

  /**
   * Get the current audio route as a formatted string.
   * @returns Promise with human-readable route summary
   */
  async getCurrentRouteSummary(): Promise<string> {
    return await GlassesAudioModule.getCurrentRouteSummary();
  }

  /**
   * Check if any Bluetooth device is currently connected.
   * @returns Promise<boolean> true if Bluetooth device is connected
   */
  async isBluetoothConnected(): Promise<boolean> {
    return await GlassesAudioModule.isBluetoothConnected();
  }

  /**
   * Check if Bluetooth SCO is currently connected.
   * @returns Promise<boolean> true if SCO is connected
   */
  async isScoConnected(): Promise<boolean> {
    return await GlassesAudioModule.isScoConnected();
  }

  /**
   * Start monitoring audio route changes.
   * Emits 'onAudioRouteChange' events when the route changes.
   */
  startMonitoring(): void {
    GlassesAudioModule.startMonitoring();
  }

  /**
   * Stop monitoring audio route changes.
   */
  stopMonitoring(): void {
    GlassesAudioModule.stopMonitoring();
  }

  /**
   * Add a listener for audio route changes.
   * @param listener Callback function to handle route changes
   * @returns Subscription object to remove the listener
   */
  addAudioRouteChangeListener(
    listener: (event: AudioRouteChangeEvent) => void
  ): Subscription {
    return this.addListener('onAudioRouteChange', listener);
  }
}

/**
 * Expo module for Meta AI Glasses audio recording and playback.
 * Provides WAV audio recording and playback through Bluetooth SCO.
 */
class ExpoGlassesAudio extends EventEmitter {
  constructor() {
    super(ExpoGlassesAudioModule);
  }

  /**
   * Get the current audio route information (simplified format).
   * @returns Simple route info with input/output device names
   */
  getAudioRoute(): SimpleAudioRouteInfo {
    return ExpoGlassesAudioModule.getAudioRoute();
  }

  /**
   * Start recording audio to a WAV file.
   * @param durationSeconds Duration of recording in seconds
   * @returns Promise with recording result (uri, duration, size)
   */
  async startRecording(durationSeconds: number): Promise<RecordingResult> {
    return await ExpoGlassesAudioModule.startRecording(durationSeconds);
  }

  /**
   * Stop the current recording.
   * @returns Promise with recording result
   */
  async stopRecording(): Promise<RecordingResult> {
    return await ExpoGlassesAudioModule.stopRecording();
  }

  /**
   * Play a WAV audio file through Bluetooth SCO.
   * @param fileUri Path to the WAV file to play
   * @returns Promise that resolves when playback starts
   */
  async playAudio(fileUri: string): Promise<void> {
    return await ExpoGlassesAudioModule.playAudio(fileUri);
  }

  /**
   * Stop the current audio playback.
   * @returns Promise that resolves when playback stops
   */
  async stopPlayback(): Promise<void> {
    return await ExpoGlassesAudioModule.stopPlayback();
  }

  /**
   * Add a listener for audio route changes.
   * @param listener Callback function to handle route changes
   * @returns Subscription object to remove the listener
   */
  addAudioRouteChangeListener(
    listener: (event: SimpleAudioRouteInfo) => void
  ): Subscription {
    return this.addListener('onAudioRouteChange', listener);
  }

  /**
   * Add a listener for recording progress updates.
   * @param listener Callback function to handle recording progress
   * @returns Subscription object to remove the listener
   */
  addRecordingProgressListener(
    listener: (event: RecordingProgressEvent) => void
  ): Subscription {
    return this.addListener('onRecordingProgress', listener);
  }

  /**
   * Add a listener for playback status updates.
   * @param listener Callback function to handle playback status
   * @returns Subscription object to remove the listener
   */
  addPlaybackStatusListener(
    listener: (event: PlaybackStatusEvent) => void
  ): Subscription {
    return this.addListener('onPlaybackStatus', listener);
  }
}

// Export both modules
export const glassesAudio = new GlassesAudio();
export const expoGlassesAudio = new ExpoGlassesAudio();

// Export ExpoGlassesAudio as default for backward compatibility
export default expoGlassesAudio;
