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

export interface AudioRouteChangeEvent {
  route: AudioRouteInfo;
}

// Get the native module
const NativeModule = requireNativeModule('GlassesAudio');

/**
 * Expo module for Meta AI Glasses audio route monitoring.
 * Provides real-time information about Android audio routing, including
 * Bluetooth connections, SCO status, and device changes.
 */
class GlassesAudioModule extends EventEmitter {
  constructor() {
    super(NativeModule);
  }

  /**
   * Get the current audio route information.
   * @returns Promise with current route details including inputs, outputs, and Bluetooth status
   */
  async getCurrentRoute(): Promise<AudioRouteInfo> {
    return await NativeModule.getCurrentRoute();
  }

  /**
   * Get the current audio route as a formatted string.
   * @returns Promise with human-readable route summary
   */
  async getCurrentRouteSummary(): Promise<string> {
    return await NativeModule.getCurrentRouteSummary();
  }

  /**
   * Check if any Bluetooth device is currently connected.
   * @returns Promise<boolean> true if Bluetooth device is connected
   */
  async isBluetoothConnected(): Promise<boolean> {
    return await NativeModule.isBluetoothConnected();
  }

  /**
   * Check if Bluetooth SCO is currently connected.
   * @returns Promise<boolean> true if SCO is connected
   */
  async isScoConnected(): Promise<boolean> {
    return await NativeModule.isScoConnected();
  }

  /**
   * Start monitoring audio route changes.
   * Emits 'onAudioRouteChange' events when the route changes.
   */
  startMonitoring(): void {
    NativeModule.startMonitoring();
  }

  /**
   * Stop monitoring audio route changes.
   */
  stopMonitoring(): void {
    NativeModule.stopMonitoring();
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

export default new GlassesAudioModule();
