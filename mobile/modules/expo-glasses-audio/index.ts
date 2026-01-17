import { EventEmitter, Subscription } from 'expo-modules-core';

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

/**
 * Expo module for Meta AI Glasses audio route monitoring.
 * Provides real-time information about Android audio routing, including
 * Bluetooth connections, SCO status, and device changes.
 */
class GlassesAudioModule extends EventEmitter {
  /**
   * Get the current audio route information.
   * @returns Promise with current route details including inputs, outputs, and Bluetooth status
   */
  async getCurrentRoute(): Promise<AudioRouteInfo> {
    throw new Error('Method not implemented - requires native module');
  }

  /**
   * Get the current audio route as a formatted string.
   * @returns Promise with human-readable route summary
   */
  async getCurrentRouteSummary(): Promise<string> {
    throw new Error('Method not implemented - requires native module');
  }

  /**
   * Check if any Bluetooth device is currently connected.
   * @returns Promise<boolean> true if Bluetooth device is connected
   */
  async isBluetoothConnected(): Promise<boolean> {
    throw new Error('Method not implemented - requires native module');
  }

  /**
   * Check if Bluetooth SCO is currently connected.
   * @returns Promise<boolean> true if SCO is connected
   */
  async isScoConnected(): Promise<boolean> {
    throw new Error('Method not implemented - requires native module');
  }

  /**
   * Start monitoring audio route changes.
   * Emits 'onAudioRouteChange' events when the route changes.
   */
  startMonitoring(): void {
    throw new Error('Method not implemented - requires native module');
  }

  /**
   * Stop monitoring audio route changes.
   */
  stopMonitoring(): void {
    throw new Error('Method not implemented - requires native module');
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
