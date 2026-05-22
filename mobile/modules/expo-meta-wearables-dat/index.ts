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
  display: boolean;
  displayVideo: boolean;
}

export interface DatConfiguration {
  platform: 'ios' | 'android';
  sdkLinked: boolean;
  sdkConfigured?: boolean;
  sdkMeetsMinimum?: boolean;
  analyticsOptOut: boolean;
  sdkVersion?: string | null;
  sdkVersionTarget?: string | null;
  datAppModelEnabled?: boolean;
  displayDamRequired?: boolean;
  displayDamEnabled?: boolean;
  applicationId?: string | null;
  provider?: string;
  integrationMode?: string;
}

export interface DatDiagnostics {
  available: boolean;
  platform: 'ios' | 'android';
  sdkLinked: boolean;
  sdkConfigured?: boolean;
  sdkMeetsMinimum?: boolean;
  analyticsOptOut: boolean;
  sdkVersion?: string | null;
  sdkVersionTarget?: string | null;
  datAppModelEnabled?: boolean;
  displayDamRequired?: boolean;
  displayDamEnabled?: boolean;
  displayReady?: boolean;
  configWarnings?: string[];
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
  displayConnectionState?: string;
  displayLastAction?: string | null;
  displayLastStatus?: string | null;
  displayLastUpdatedAt?: number | null;
  displayRenderPath?: string | null;
  displayLastError?: string | null;
  displayActiveWidgetId?: string | null;
  displayDescriptorCid?: string | null;
  displayManifestCid?: string | null;
  displayFocusTarget?: string | null;
  displayUpdateCount?: number;
  displayLifecycleStages?: string[];
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

export interface DatMediaActionResult {
  state: string;
  mode: string;
  supported: boolean;
  action:
    | 'capture_photo'
    | 'start_video_stream'
    | 'stop_video_stream'
    | 'render_display_test'
    | 'clear_display'
    | 'play_display_video'
    | 'reset_display_session';
  message: string;
  deviceId?: string | null;
  targetConnectionState?: string;
  assetUri?: string | null;
  mimeType?: string | null;
  displayConnectionState?: string;
  displayLastAction?: string | null;
  displayLastStatus?: string | null;
  displayLastUpdatedAt?: number | null;
}

export type DatDisplayWidgetAction =
  | 'render_display_widget'
  | 'update_display_widget'
  | 'clear_display_widget'
  | 'focus_display_widget'
  | 'activate_display_widget_action'
  | 'reset_display_widget_session';

export interface DatDisplayWidgetActionResult extends Omit<DatMediaActionResult, 'action'> {
  action: DatDisplayWidgetAction;
  operation?: string;
  reason?: string | null;
  renderPath?: string;
  requiredAction?: string | null;
  displayRenderPath?: string | null;
  displayLastError?: string | null;
  displayUpdateCount?: number;
  displayLifecycleStages?: string[];
  widgetId?: string | null;
  widgetCid?: string | null;
  descriptorCid?: string | null;
  interfaceCid?: string | null;
  manifestCid?: string | null;
  orbReceiptCid?: string | null;
  policyDecision?: string | null;
  correlationId?: string | null;
  requestId?: string | null;
  issuedAt?: string | null;
  focusDirection?: string | null;
  activatedActionId?: string | null;
  fallback?: Record<string, unknown> | null;
}

const ExpoMetaWearablesDatModule = requireOptionalNativeModule('ExpoMetaWearablesDat');

const unavailableCapabilities: DatCapabilities = {
  session: false,
  camera: false,
  photoCapture: false,
  videoStream: false,
  audio: false,
  display: false,
  displayVideo: false,
};

function inferPlatform(): 'ios' | 'android' {
  return process.env.EXPO_OS === 'android' ? 'android' : 'ios';
}

function getUnavailableConfiguration(): DatConfiguration {
  return {
    platform: inferPlatform(),
    sdkLinked: false,
    sdkConfigured: false,
    sdkMeetsMinimum: false,
    analyticsOptOut: false,
    sdkVersion: null,
    sdkVersionTarget: '0.7.0',
    datAppModelEnabled: false,
    displayDamRequired: true,
    displayDamEnabled: false,
    applicationId: null,
    provider: 'internal_bridge',
    integrationMode: 'unavailable',
  };
}

function getUnavailableDiagnostics(): DatDiagnostics {
  const configuration = getUnavailableConfiguration();
  return {
    available: false,
    ...configuration,
    capabilities: unavailableCapabilities,
    sessionState: 'unavailable',
    displayReady: false,
    configWarnings: ['DAT native module is unavailable in this build.'],
    registrationState: 'unavailable',
    deviceCount: 0,
    activeDeviceId: null,
    selectedDeviceId: null,
    selectedDeviceName: null,
    targetConnectionState: 'unselected',
    targetLastSeenAt: null,
    targetRssi: null,
    adapterState: {
      transport: 'bluetooth',
      adapterAvailable: false,
      adapterEnabled: false,
      scanPermissionGranted: false,
      connectPermissionGranted: false,
      advertisePermissionGranted: false,
      state: 'unavailable',
    },
    knownDeviceCount: 0,
    displayConnectionState: 'unavailable',
    displayLastAction: null,
    displayLastStatus: null,
    displayLastUpdatedAt: null,
    displayRenderPath: 'mobile-card',
    displayLastError: 'dat_native_display_unavailable',
    displayActiveWidgetId: null,
    displayDescriptorCid: null,
    displayManifestCid: null,
    displayFocusTarget: null,
    displayUpdateCount: 0,
    displayLifecycleStages: [],
  };
}

function getUnavailableTargetState(state: string = 'awaiting_target'): {
  state: string;
  mode: string;
  deviceId: null;
  targetConnectionState: string;
} {
  return {
    state,
    mode: 'unavailable',
    deviceId: null,
    targetConnectionState: 'unselected',
  };
}

function getUnavailableMediaResult(
  action: DatMediaActionResult['action'],
  message: string = 'Meta Wearables DAT media capture is unavailable in this build.'
): DatMediaActionResult {
  return {
    state: 'unavailable',
    mode: 'unavailable',
    supported: false,
    action,
    message,
    deviceId: null,
    targetConnectionState: 'unselected',
    assetUri: null,
    mimeType: null,
    displayConnectionState: 'unavailable',
    displayLastAction: action,
    displayLastStatus: 'unavailable',
    displayLastUpdatedAt: Date.now(),
  };
}

function getUnavailableDisplayWidgetResult(
  action: DatDisplayWidgetAction,
  message: string = 'Meta Wearables DAT display widget rendering is unavailable in this build.',
  operation: string = getDisplayWidgetOperation(action)
): DatDisplayWidgetActionResult {
  return {
    ...getUnavailableMediaResult('render_display_test', message),
    action,
    operation,
    reason: 'dat_native_display_unavailable',
    renderPath: 'mobile-card',
    requiredAction: null,
    displayRenderPath: 'mobile-card',
    displayLastAction: action,
    displayLastError: 'dat_native_display_unavailable',
    displayUpdateCount: 0,
    fallback: {
      reason: 'dat_native_display_unavailable',
      renderPath: 'mobile-card',
      message,
    },
  };
}

function getDisplayWidgetOperation(action: DatDisplayWidgetAction): string {
  switch (action) {
    case 'render_display_widget':
      return 'render_widget';
    case 'update_display_widget':
      return 'update_widget';
    case 'clear_display_widget':
      return 'clear_widget';
    case 'focus_display_widget':
      return 'focus_next';
    case 'activate_display_widget_action':
      return 'activate';
    case 'reset_display_widget_session':
      return 'reset_session';
    default:
      return action;
  }
}

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
    return (await ExpoMetaWearablesDatModule?.getConfiguration?.()) ?? getUnavailableConfiguration();
  }

  async getCapabilities(): Promise<DatCapabilities> {
    return (await ExpoMetaWearablesDatModule?.getCapabilities?.()) ?? unavailableCapabilities;
  }

  async getConnectedDevice(): Promise<DatDeviceInfo | null> {
    return (await ExpoMetaWearablesDatModule?.getConnectedDevice?.()) ?? null;
  }

  async getSessionState(): Promise<string> {
    return (await ExpoMetaWearablesDatModule?.getSessionState?.()) ?? 'unavailable';
  }

  async getAdapterState(): Promise<DatDiagnostics['adapterState']> {
    return (await ExpoMetaWearablesDatModule?.getAdapterState?.()) ?? getUnavailableDiagnostics().adapterState;
  }

  async getKnownDevices(): Promise<Array<Record<string, unknown>>> {
    return (await ExpoMetaWearablesDatModule?.getKnownDevices?.()) ?? [];
  }

  async scanKnownAndNearbyDevices(timeoutMs: number = 2500): Promise<Array<Record<string, unknown>>> {
    return (await ExpoMetaWearablesDatModule?.scanKnownAndNearbyDevices?.(timeoutMs)) ?? [];
  }

  async getSelectedDeviceTarget(): Promise<Record<string, unknown> | null> {
    return (await ExpoMetaWearablesDatModule?.getSelectedDeviceTarget?.()) ?? null;
  }

  async selectDeviceTarget(deviceId: string): Promise<Record<string, unknown>> {
    return (await ExpoMetaWearablesDatModule?.selectDeviceTarget?.(deviceId)) ?? {
      deviceId,
      deviceName: deviceId,
      source: 'selected_only',
    };
  }

  async clearDeviceTarget(): Promise<Record<string, unknown>> {
    return (await ExpoMetaWearablesDatModule?.clearDeviceTarget?.()) ?? {};
  }

  async reconnectSelectedDeviceTarget(): Promise<Record<string, unknown>> {
    return (await ExpoMetaWearablesDatModule?.reconnectSelectedDeviceTarget?.()) ?? getUnavailableTargetState();
  }

  async connectSelectedDeviceTarget(): Promise<Record<string, unknown>> {
    return (await ExpoMetaWearablesDatModule?.connectSelectedDeviceTarget?.()) ?? getUnavailableTargetState();
  }

  async getDiagnostics(): Promise<DatDiagnostics> {
    return (await ExpoMetaWearablesDatModule?.getDiagnostics?.()) ?? getUnavailableDiagnostics();
  }

  async startDeviceSession(): Promise<{ state: string }> {
    return (await ExpoMetaWearablesDatModule?.startDeviceSession?.()) ?? getUnavailableTargetState('unavailable');
  }

  async stopDeviceSession(): Promise<{ state: string }> {
    return (await ExpoMetaWearablesDatModule?.stopDeviceSession?.()) ?? {
      state: 'unavailable',
      mode: 'unavailable',
      deviceId: null,
      targetConnectionState: 'unselected',
    };
  }

  async capturePhoto(): Promise<DatMediaActionResult> {
    return (await ExpoMetaWearablesDatModule?.capturePhoto?.())
      ?? getUnavailableMediaResult('capture_photo');
  }

  async startVideoStream(): Promise<DatMediaActionResult> {
    return (await ExpoMetaWearablesDatModule?.startVideoStream?.())
      ?? getUnavailableMediaResult('start_video_stream');
  }

  async stopVideoStream(): Promise<DatMediaActionResult> {
    return (await ExpoMetaWearablesDatModule?.stopVideoStream?.())
      ?? getUnavailableMediaResult('stop_video_stream');
  }

  async renderDisplayTest(): Promise<DatMediaActionResult> {
    return (await ExpoMetaWearablesDatModule?.renderDisplayTest?.())
      ?? getUnavailableMediaResult(
        'render_display_test',
        'Meta Wearables DAT display rendering is unavailable in this build.'
      );
  }

  async clearDisplay(): Promise<DatMediaActionResult> {
    return (await ExpoMetaWearablesDatModule?.clearDisplay?.())
      ?? getUnavailableMediaResult(
        'clear_display',
        'Meta Wearables DAT display clearing is unavailable in this build.'
      );
  }

  async playDisplayVideo(videoUrl?: string): Promise<DatMediaActionResult> {
    return (await ExpoMetaWearablesDatModule?.playDisplayVideo?.(videoUrl))
      ?? getUnavailableMediaResult(
        'play_display_video',
        'Meta Wearables DAT display video playback is unavailable in this build.'
      );
  }

  async resetDisplaySession(): Promise<DatMediaActionResult> {
    return (await ExpoMetaWearablesDatModule?.resetDisplaySession?.())
      ?? getUnavailableMediaResult(
        'reset_display_session',
        'Meta Wearables DAT display session reset is unavailable in this build.'
      );
  }

  async renderDisplayWidget(manifest: Record<string, unknown> = {}): Promise<DatDisplayWidgetActionResult> {
    return (await ExpoMetaWearablesDatModule?.renderDisplayWidget?.(manifest))
      ?? getUnavailableDisplayWidgetResult(
        'render_display_widget',
        'Meta Wearables DAT display widget rendering is unavailable in this build.'
      );
  }

  async updateDisplayWidget(patch: Record<string, unknown> = {}): Promise<DatDisplayWidgetActionResult> {
    return (await ExpoMetaWearablesDatModule?.updateDisplayWidget?.(patch))
      ?? getUnavailableDisplayWidgetResult(
        'update_display_widget',
        'Meta Wearables DAT display widget updates are unavailable in this build.'
      );
  }

  async clearDisplayWidget(widgetId?: string | null): Promise<DatDisplayWidgetActionResult> {
    return (await ExpoMetaWearablesDatModule?.clearDisplayWidget?.(widgetId))
      ?? getUnavailableDisplayWidgetResult(
        'clear_display_widget',
        'Meta Wearables DAT display widget clearing is unavailable in this build.'
      );
  }

  async focusDisplayWidget(direction?: string | null): Promise<DatDisplayWidgetActionResult> {
    return (await ExpoMetaWearablesDatModule?.focusDisplayWidget?.(direction))
      ?? getUnavailableDisplayWidgetResult(
        'focus_display_widget',
        'Meta Wearables DAT display widget focus is unavailable in this build.',
        direction === 'previous' ? 'focus_previous' : 'focus_next'
      );
  }

  async activateDisplayWidgetAction(actionId?: string | null): Promise<DatDisplayWidgetActionResult> {
    return (await ExpoMetaWearablesDatModule?.activateDisplayWidgetAction?.(actionId))
      ?? getUnavailableDisplayWidgetResult(
        'activate_display_widget_action',
        'Meta Wearables DAT display widget actions are unavailable in this build.'
      );
  }

  async resetDisplayWidgetSession(): Promise<DatDisplayWidgetActionResult> {
    return (await ExpoMetaWearablesDatModule?.resetDisplayWidgetSession?.())
      ?? getUnavailableDisplayWidgetResult(
        'reset_display_widget_session',
        'Meta Wearables DAT display widget session reset is unavailable in this build.'
      );
  }

  addStateListener(listener: (event: DatStateChangedEvent) => void): Subscription {
    if (!ExpoMetaWearablesDatModule) {
      return {
        remove() {},
      } as Subscription;
    }
    return this.addListener('onDatStateChanged', listener);
  }
}

export default new ExpoMetaWearablesDat();
