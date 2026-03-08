declare module 'expo-glasses-audio' {
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

  export interface PeerInfo {
    peerRef: string;
    peerId: string;
    displayName?: string;
    transport: 'bluetooth' | 'simulated';
    rssi?: number;
  }

  export interface AdvertisedPeerIdentity {
    peerId: string;
    displayName?: string;
  }

  export interface PeerConnectionResult {
    peerRef: string;
    peerId?: string;
    transport: 'bluetooth' | 'simulated';
    connectedAt: number;
  }

  export interface PeerAdapterState {
    transport: 'bluetooth' | 'simulated';
    adapterAvailable: boolean;
    adapterEnabled: boolean;
    scanPermissionGranted: boolean;
    connectPermissionGranted: boolean;
    advertisePermissionGranted?: boolean;
    advertising: boolean;
    scanning: boolean;
    state: string;
  }

  export type AudioSource = 'phone' | 'glasses' | 'auto';

  export function getAudioRoute(): SimpleAudioRouteInfo;
  
  export function startRecording(durationSeconds: number, audioSource?: AudioSource): Promise<RecordingResult>;
  
  export function stopRecording(): Promise<RecordingResult>;
  
  export function playAudio(fileUri: string): Promise<void>;
  
  export function stopPlayback(): Promise<void>;

  export function scanPeers(timeoutMs?: number): Promise<PeerInfo[]>;

  export function getPeerAdapterState(): Promise<PeerAdapterState>;

  export function advertiseIdentity(identity: AdvertisedPeerIdentity): Promise<AdvertisedPeerIdentity>;

  export function connectPeer(peerRef: string): Promise<PeerConnectionResult>;

  export function disconnectPeer(peerRef: string, reason?: string): Promise<void>;

  export function sendFrame(peerRef: string, payloadBase64: string): Promise<void>;

  export function simulatePeerDiscovery(peer: PeerInfo): Promise<PeerInfo>;

  export function simulatePeerConnection(peerRef: string): Promise<PeerConnectionResult>;

  export function simulateFrameReceived(
    peerRef: string,
    payloadBase64: string,
    peerId?: string
  ): Promise<void>;

  export function resetPeerSimulation(): Promise<void>;
  
  export function addAudioRouteChangeListener(
    listener: (event: SimpleAudioRouteInfo) => void
  ): Subscription;
  
  export function addRecordingProgressListener(
    listener: (event: { isRecording: boolean; duration: number }) => void
  ): Subscription;
  
  export function addPlaybackStatusListener(
    listener: (event: { isPlaying: boolean; error?: string }) => void
  ): Subscription;

  export function addPeerDiscoveredListener(
    listener: (event: { peer: PeerInfo }) => void
  ): Subscription;

  export function addPeerConnectedListener(
    listener: (event: { peerRef: string; peerId?: string; transport: 'bluetooth' | 'simulated' }) => void
  ): Subscription;

  export function addPeerDisconnectedListener(
    listener: (event: { peerRef: string; reason?: string }) => void
  ): Subscription;

  export function addFrameReceivedListener(
    listener: (event: { peerRef: string; peerId?: string; payloadBase64: string }) => void
  ): Subscription;
}
