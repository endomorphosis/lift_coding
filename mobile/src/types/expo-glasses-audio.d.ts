declare module '../../modules/expo-glasses-audio' {
  import { Subscription } from 'expo-modules-core';

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
    position: number;
    duration: number;
    error?: string;
  }

  export interface AudioRouteChangeEvent {
    route: AudioRouteInfo;
  }

  // Audio Route Monitoring Module (GlassesAudio)
  export interface GlassesAudioModule {
    getCurrentRoute(): Promise<AudioRouteInfo>;
    getCurrentRouteSummary(): Promise<string>;
    isBluetoothConnected(): Promise<boolean>;
    isScoConnected(): Promise<boolean>;
    startMonitoring(): void;
    stopMonitoring(): void;
    addAudioRouteChangeListener(
      listener: (event: AudioRouteChangeEvent) => void
    ): Subscription;
  }

  // Recording & Playback Module (ExpoGlassesAudio)
  export interface ExpoGlassesAudioModule {
    getAudioRoute(): SimpleAudioRouteInfo;
    startRecording(durationSeconds: number): Promise<RecordingResult>;
    stopRecording(): Promise<RecordingResult>;
    playAudio(fileUri: string): Promise<void>;
    stopPlayback(): Promise<void>;
    addAudioRouteChangeListener(
      listener: (event: SimpleAudioRouteInfo) => void
    ): Subscription;
    addRecordingProgressListener(
      listener: (event: RecordingProgressEvent) => void
    ): Subscription;
    addPlaybackStatusListener(
      listener: (event: PlaybackStatusEvent) => void
    ): Subscription;
  }

  // Export both module instances
  export const glassesAudio: GlassesAudioModule;
  export const expoGlassesAudio: ExpoGlassesAudioModule;

  // Default export is expoGlassesAudio
  const defaultExport: ExpoGlassesAudioModule;
  export default defaultExport;
}
