import { EventEmitter, Subscription } from 'expo-modules-core';
import { requireNativeModule, requireOptionalNativeModule } from 'expo-modules-core';

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

export interface AudioRouteChangeEvent {
  route: AudioRouteInfo;
}

export interface PeerInfo {
  peerRef: string;
  peerId: string;
  displayName?: string;
  transport: 'bluetooth' | 'simulated';
  rssi?: number;
}

export interface PeerDiscoveredEvent {
  peer: PeerInfo;
}

export interface PeerConnectedEvent {
  peerRef: string;
  peerId?: string;
  transport: 'bluetooth' | 'simulated';
}

export interface PeerDisconnectedEvent {
  peerRef: string;
  reason?: string;
}

export interface PeerFrameReceivedEvent {
  peerRef: string;
  peerId?: string;
  payloadBase64: string;
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

// Get the native modules
// Note: 'GlassesAudio' is implemented on Android in this repo, but may be absent on iOS.
// Use optional loading to avoid crashing on import.
const GlassesAudioModule = requireOptionalNativeModule('GlassesAudio');
const ExpoGlassesAudioModule = requireNativeModule('ExpoGlassesAudio');

/**
 * Expo module for Meta AI Glasses audio route monitoring.
 * Provides real-time information about Android audio routing, including
 * Bluetooth connections, SCO status, and device changes.
 */
class GlassesAudio extends EventEmitter {
  constructor() {
    // If the module is missing (e.g., iOS), pass a dummy object to EventEmitter.
    super(GlassesAudioModule || ({} as any));
  }

  /**
   * Get the current audio route information.
   * @returns Promise with current route details including inputs, outputs, and Bluetooth status
   */
  async getCurrentRoute(): Promise<AudioRouteInfo> {
    if (!GlassesAudioModule) {
      throw new Error("GlassesAudio native module not available on this platform/build");
    }
    return await GlassesAudioModule.getCurrentRoute();
  }

  /**
   * Get the current audio route as a formatted string.
   * @returns Promise with human-readable route summary
   */
  async getCurrentRouteSummary(): Promise<string> {
    if (!GlassesAudioModule) {
      throw new Error("GlassesAudio native module not available on this platform/build");
    }
    return await GlassesAudioModule.getCurrentRouteSummary();
  }

  /**
   * Check if any Bluetooth device is currently connected.
   * @returns Promise<boolean> true if Bluetooth device is connected
   */
  async isBluetoothConnected(): Promise<boolean> {
    if (!GlassesAudioModule) {
      return false;
    }
    return await GlassesAudioModule.isBluetoothConnected();
  }

  /**
   * Check if Bluetooth SCO is currently connected.
   * @returns Promise<boolean> true if SCO is connected
   */
  async isScoConnected(): Promise<boolean> {
    if (!GlassesAudioModule) {
      return false;
    }
    return await GlassesAudioModule.isScoConnected();
  }

  /**
   * Start monitoring audio route changes.
   * Emits 'onAudioRouteChange' events when the route changes.
   */
  startMonitoring(): void {
    if (!GlassesAudioModule) return;
    GlassesAudioModule.startMonitoring();
  }

  /**
   * Stop monitoring audio route changes.
   */
  stopMonitoring(): void {
    if (!GlassesAudioModule) return;
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
    if (!GlassesAudioModule) {
      throw new Error("GlassesAudio native module not available on this platform/build");
    }
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
   * @param audioSource Optional audio source preference ('phone', 'glasses', or 'auto')
   * @returns Promise with recording result (uri, duration, size)
   */
  async startRecording(durationSeconds: number, audioSource?: AudioSource): Promise<RecordingResult> {
    return await ExpoGlassesAudioModule.startRecording(durationSeconds, audioSource);
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
   * Scan for nearby Bluetooth peer candidates.
   * The current native implementation is a bridge/stub surface for PR-010 and
   * returns simulated peers until platform BLE data channels are wired.
   */
  async scanPeers(timeoutMs: number = 5_000): Promise<PeerInfo[]> {
    return await ExpoGlassesAudioModule.scanPeers(timeoutMs);
  }

  /**
   * Return Bluetooth adapter state for peer transport bring-up diagnostics.
   */
  async getPeerAdapterState(): Promise<PeerAdapterState> {
    return await ExpoGlassesAudioModule.getPeerAdapterState();
  }

  /**
   * Advertise the local peer identity for nearby discovery.
   */
  async advertiseIdentity(identity: AdvertisedPeerIdentity): Promise<AdvertisedPeerIdentity> {
    return await ExpoGlassesAudioModule.advertiseIdentity(identity.peerId, identity.displayName);
  }

  /**
   * Connect to a previously discovered peer reference.
   */
  async connectPeer(peerRef: string): Promise<PeerConnectionResult> {
    return await ExpoGlassesAudioModule.connectPeer(peerRef);
  }

  /**
   * Disconnect from an active peer link.
   */
  async disconnectPeer(peerRef: string, reason?: string): Promise<void> {
    return await ExpoGlassesAudioModule.disconnectPeer(peerRef, reason);
  }

  /**
   * Send a frame over the Bluetooth peer bridge.
   * `payloadBase64` is used at the JS/native boundary to avoid platform-specific byte marshaling.
   */
  async sendFrame(peerRef: string, payloadBase64: string): Promise<void> {
    return await ExpoGlassesAudioModule.sendFrame(peerRef, payloadBase64);
  }

  /**
   * Development-only helpers for PR-010 bring-up and local testing.
   */
  async simulatePeerDiscovery(peer: PeerInfo): Promise<PeerInfo> {
    return await ExpoGlassesAudioModule.simulatePeerDiscovery(peer);
  }

  async simulatePeerConnection(peerRef: string): Promise<PeerConnectionResult> {
    return await ExpoGlassesAudioModule.simulatePeerConnection(peerRef);
  }

  async simulateFrameReceived(peerRef: string, payloadBase64: string, peerId?: string): Promise<void> {
    return await ExpoGlassesAudioModule.simulateFrameReceived(peerRef, payloadBase64, peerId);
  }

  async resetPeerSimulation(): Promise<void> {
    return await ExpoGlassesAudioModule.resetPeerSimulation();
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

  addPeerDiscoveredListener(
    listener: (event: PeerDiscoveredEvent) => void
  ): Subscription {
    return this.addListener('peerDiscovered', listener);
  }

  addPeerConnectedListener(
    listener: (event: PeerConnectedEvent) => void
  ): Subscription {
    return this.addListener('peerConnected', listener);
  }

  addPeerDisconnectedListener(
    listener: (event: PeerDisconnectedEvent) => void
  ): Subscription {
    return this.addListener('peerDisconnected', listener);
  }

  addFrameReceivedListener(
    listener: (event: PeerFrameReceivedEvent) => void
  ): Subscription {
    return this.addListener('frameReceived', listener);
  }
}

// Export both modules
export const glassesAudio = new GlassesAudio();
export const expoGlassesAudio = new ExpoGlassesAudio();

// Export ExpoGlassesAudio as default for backward compatibility
export default expoGlassesAudio;
