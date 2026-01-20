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

  export type AudioSource = 'phone' | 'glasses' | 'auto';

  export function getAudioRoute(): AudioRouteInfo;
  
  export function startRecording(durationSeconds: number, audioSource?: AudioSource): Promise<RecordingResult>;
  
  export function stopRecording(): Promise<RecordingResult>;
  
  export function playAudio(fileUri: string): Promise<void>;
  
  export function stopPlayback(): Promise<void>;
  
  export function addAudioRouteChangeListener(
    listener: (event: AudioRouteInfo) => void
  ): Subscription;
  
  export function addRecordingProgressListener(
    listener: (event: { isRecording: boolean; duration: number }) => void
  ): Subscription;
  
  export function addPlaybackStatusListener(
    listener: (event: { isPlaying: boolean; position: number; duration: number }) => void
  ): Subscription;
}
