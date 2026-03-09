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

  async getDiagnostics(): Promise<DatDiagnostics> {
    return await ExpoMetaWearablesDatModule.getDiagnostics();
  }

  async startDeviceSession(): Promise<{ state: string }> {
    return await ExpoMetaWearablesDatModule.startDeviceSession();
  }

  async stopDeviceSession(): Promise<{ state: string }> {
    return await ExpoMetaWearablesDatModule.stopDeviceSession();
  }

  addStateListener(listener: (event: { state: string }) => void): Subscription {
    return this.addListener('onDatStateChanged', listener);
  }
}

export default new ExpoMetaWearablesDat();
