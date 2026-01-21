declare module 'expo-glasses-audio' {
  export type Subscription = { remove: () => void };

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

  export interface RecordingProgressEvent {
    isRecording: boolean;
    duration: number;
  }

  export interface PlaybackStatusEvent {
    isPlaying: boolean;
    error?: string;
  }

  export const expoGlassesAudio: {
    getAudioRoute(): SimpleAudioRouteInfo;
    startRecording(durationSeconds: number, audioSource?: AudioSource): Promise<RecordingResult>;
    stopRecording(): Promise<RecordingResult>;
    playAudio(fileUri: string): Promise<void>;
    stopPlayback(): Promise<void>;
    addAudioRouteChangeListener(listener: (event: SimpleAudioRouteInfo) => void): Subscription;
    addRecordingProgressListener(listener: (event: RecordingProgressEvent) => void): Subscription;
    addPlaybackStatusListener(listener: (event: PlaybackStatusEvent) => void): Subscription;
  };

  export default expoGlassesAudio;
}
