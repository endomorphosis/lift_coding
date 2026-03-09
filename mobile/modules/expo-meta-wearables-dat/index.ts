import { EventEmitter, Subscription, requireOptionalNativeModule } from 'expo-modules-core';

export interface DatDeviceInfo {
  platform: 'ios' | 'android';
  sdkLinked: boolean;
  sdkConfigured?: boolean;
  applicationId?: string | null;
  deviceId?: string | null;
  registrationState?: string | null;
  deviceName?: string | null;
  deviceModel?: string | null;
}

export interface DatCapabilities {
  session: boolean;
  camera: boolean;
  photoCapture: boolean;
  videoStream: boolean;
  audio: boolean;
}

export interface DatConfiguration {
  platform: 'ios' | 'android';
  sdkLinked: boolean;
  sdkConfigured?: boolean;
  analyticsOptOut: boolean;
  sdkVersion?: string | null;
  applicationId?: string | null;
  provider?: string;
  integrationMode?: string;
}

export interface DatDiagnostics {
  available: boolean;
  platform: 'ios' | 'android';
  sdkLinked: boolean;
  sdkConfigured?: boolean;
  analyticsOptOut: boolean;
  sdkVersion?: string | null;
  applicationId?: string | null;
  provider?: string;
  integrationMode?: string;
  capabilities: DatCapabilities;
  sessionState: string;
  registrationState?: string | null;
  deviceCount?: number;
  activeDeviceId?: string | null;
  selectedDeviceId?: string | null;
  selectedDeviceName?: string | null;
  targetConnectionState?: string | null;
  targetLastSeenAt?: number | null;
  targetRssi?: number | null;
  adapterState?: {
    transport: string;
    adapterAvailable: boolean;
    adapterEnabled: boolean;
    scanPermissionGranted: boolean;
    connectPermissionGranted: boolean;
    advertisePermissionGranted?: boolean;
    state: string;
  };
  knownDeviceCount?: number;
}

export interface DatStateChangedEvent {
  state: string;
  sessionState?: string;
  deviceId?: string | null;
  deviceName?: string | null;
  targetConnectionState?: string | null;
  targetLastSeenAt?: number | null;
  targetRssi?: number | null;
}

const ExpoMetaWearablesDatModule = requireOptionalNativeModule('ExpoMetaWearablesDat');

class ExpoMetaWearablesDat extends EventEmitter {
  constructor() {
    super(ExpoMetaWearablesDatModule || ({} as any));
  }

  isAvailable(): boolean {
    return Boolean(ExpoMetaWearablesDatModule);
  }

  async isDatAvailable(): Promise<boolean> {
    return (await ExpoMetaWearablesDatModule?.isDatAvailable?.()) ?? false;
  }

  async getConfiguration(): Promise<DatConfiguration> {
    return await ExpoMetaWearablesDatModule.getConfiguration();
  }

  async getCapabilities(): Promise<DatCapabilities> {
    return await ExpoMetaWearablesDatModule.getCapabilities();
  }

  async getConnectedDevice(): Promise<DatDeviceInfo | null> {
    return (await ExpoMetaWearablesDatModule.getConnectedDevice()) ?? null;
  }

  async getSessionState(): Promise<string> {
    return await ExpoMetaWearablesDatModule.getSessionState();
  }

  async getAdapterState(): Promise<DatDiagnostics['adapterState']> {
    return await ExpoMetaWearablesDatModule.getAdapterState();
  }

  async getKnownDevices(): Promise<Array<Record<string, unknown>>> {
    return await ExpoMetaWearablesDatModule.getKnownDevices();
  }

  async scanKnownAndNearbyDevices(timeoutMs: number = 2500): Promise<Array<Record<string, unknown>>> {
    return await ExpoMetaWearablesDatModule.scanKnownAndNearbyDevices(timeoutMs);
  }

  async getSelectedDeviceTarget(): Promise<Record<string, unknown> | null> {
    return (await ExpoMetaWearablesDatModule.getSelectedDeviceTarget()) ?? null;
  }

  async selectDeviceTarget(deviceId: string): Promise<Record<string, unknown>> {
    return await ExpoMetaWearablesDatModule.selectDeviceTarget(deviceId);
  }

  async clearDeviceTarget(): Promise<Record<string, unknown>> {
    return await ExpoMetaWearablesDatModule.clearDeviceTarget();
  }

  async reconnectSelectedDeviceTarget(): Promise<Record<string, unknown>> {
    return await ExpoMetaWearablesDatModule.reconnectSelectedDeviceTarget();
  }

  async connectSelectedDeviceTarget(): Promise<Record<string, unknown>> {
    return await ExpoMetaWearablesDatModule.connectSelectedDeviceTarget();
  }

  async getDiagnostics(): Promise<DatDiagnostics> {
    return await ExpoMetaWearablesDatModule.getDiagnostics();
  }

  async startDeviceSession(): Promise<{ state: string }> {
    return await ExpoMetaWearablesDatModule.startDeviceSession();
  }

  async stopDeviceSession(): Promise<{ state: string }> {
    return await ExpoMetaWearablesDatModule.stopDeviceSession();
  }

  addStateListener(listener: (event: DatStateChangedEvent) => void): Subscription {
    return this.addListener('onDatStateChanged', listener);
  }
}

export default new ExpoMetaWearablesDat();
