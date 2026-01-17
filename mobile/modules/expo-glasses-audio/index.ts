import { NativeModulesProxy, EventEmitter, Subscription } from 'expo-modules-core';

// Import the native module. On web, it will be resolved to ExpoGlassesAudio.web.ts
// and on native platforms to ExpoGlassesAudio.ts
import ExpoGlassesAudioModule from './src/ExpoGlassesAudioModule';

export interface AudioRouteInfo {
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

const emitter = new EventEmitter(ExpoGlassesAudioModule);

export function getAudioRoute(): AudioRouteInfo {
  return ExpoGlassesAudioModule.getAudioRoute();
}

export function startRecording(durationSeconds: number): Promise<RecordingResult> {
  return ExpoGlassesAudioModule.startRecording(durationSeconds);
}

export function stopRecording(): Promise<RecordingResult> {
  return ExpoGlassesAudioModule.stopRecording();
}

export function playAudio(fileUri: string): Promise<void> {
  return ExpoGlassesAudioModule.playAudio(fileUri);
}

export function stopPlayback(): Promise<void> {
  return ExpoGlassesAudioModule.stopPlayback();
}

export function addAudioRouteChangeListener(
  listener: (event: AudioRouteInfo) => void
): Subscription {
  return emitter.addListener<AudioRouteInfo>('onAudioRouteChange', listener);
}

export function addRecordingProgressListener(
  listener: (event: { isRecording: boolean; duration: number }) => void
): Subscription {
  return emitter.addListener('onRecordingProgress', listener);
}

export function addPlaybackStatusListener(
  listener: (event: { isPlaying: boolean; position: number; duration: number }) => void
): Subscription {
  return emitter.addListener('onPlaybackStatus', listener);
}
