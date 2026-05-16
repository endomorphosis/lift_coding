function createUnavailableBridge() {
  return {
    isAvailable: () => false,
    isBridgeAvailable: () => false,
    getConfiguration: async () => ({
      platform: 'unknown',
      sdkLinked: false,
      sdkConfigured: false,
      analyticsOptOut: false,
      sdkVersion: null,
      applicationId: null,
      provider: 'internal_bridge',
      integrationMode: 'unavailable',
    }),
      getCapabilities: async () => ({
        session: false,
        camera: false,
        photoCapture: false,
        videoStream: false,
        audio: false,
        display: false,
        displayVideo: false,
      }),
    getConnectedDevice: async () => null,
    getSessionState: async () => 'unavailable',
    getAdapterState: async () => ({
      transport: 'bluetooth',
      adapterAvailable: false,
      adapterEnabled: false,
      scanPermissionGranted: false,
      connectPermissionGranted: false,
      advertisePermissionGranted: false,
      state: 'unavailable',
    }),
    getKnownDevices: async () => [],
    scanKnownAndNearbyDevices: async () => [],
    getSelectedDeviceTarget: async () => null,
    selectDeviceTarget: async (deviceId) => ({
      deviceId,
      deviceName: deviceId,
      source: 'selected_only',
    }),
    clearDeviceTarget: async () => ({}),
    reconnectSelectedDeviceTarget: async () => ({
      state: 'awaiting_target',
      mode: 'unavailable',
      deviceId: null,
      targetConnectionState: 'unselected',
    }),
    connectSelectedDeviceTarget: async () => ({
      state: 'awaiting_target',
      mode: 'unavailable',
      deviceId: null,
      targetConnectionState: 'unselected',
    }),
    getDiagnostics: async () => ({
      available: false,
      platform: 'unknown',
      sdkLinked: false,
      sdkConfigured: false,
      analyticsOptOut: false,
      sdkVersion: null,
      applicationId: null,
      provider: 'internal_bridge',
      integrationMode: 'unavailable',
        capabilities: {
          session: false,
          camera: false,
          photoCapture: false,
          videoStream: false,
          audio: false,
          display: false,
          displayVideo: false,
        },
        sdkMeetsMinimum: false,
        sdkVersionTarget: '0.7.0',
        datAppModelEnabled: false,
        displayDamRequired: true,
        displayDamEnabled: false,
        displayReady: false,
        configWarnings: ['DAT native module is unavailable in this build.'],
        sessionState: 'unavailable',
      registrationState: 'unavailable',
      deviceCount: 0,
      activeDeviceId: null,
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
      selectedDeviceId: null,
      selectedDeviceName: null,
      targetConnectionState: 'unselected',
      targetLastSeenAt: null,
      targetRssi: null,
    }),
    startDeviceSession: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      targetConnectionState: 'unselected',
      deviceId: null,
    }),
    stopDeviceSession: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      targetConnectionState: 'unselected',
      deviceId: null,
    }),
    startBridgeSession: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      targetConnectionState: 'unselected',
      deviceId: null,
    }),
    stopBridgeSession: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      targetConnectionState: 'unselected',
      deviceId: null,
    }),
    capturePhoto: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      supported: false,
      action: 'capture_photo',
      message: 'Meta Wearables DAT photo capture is unavailable in this build.',
      targetConnectionState: 'unselected',
      deviceId: null,
      assetUri: null,
      mimeType: null,
    }),
    startVideoStream: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      supported: false,
      action: 'start_video_stream',
      message: 'Meta Wearables DAT video streaming is unavailable in this build.',
      targetConnectionState: 'unselected',
      deviceId: null,
      assetUri: null,
      mimeType: null,
    }),
    stopVideoStream: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      supported: false,
      action: 'stop_video_stream',
      message: 'Meta Wearables DAT video streaming is unavailable in this build.',
      targetConnectionState: 'unselected',
      deviceId: null,
      assetUri: null,
      mimeType: null,
    }),
    renderDisplayTest: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      supported: false,
      action: 'render_display_test',
      message: 'Meta Wearables DAT display rendering is unavailable in this build.',
      targetConnectionState: 'unselected',
      deviceId: null,
      assetUri: null,
      mimeType: null,
    }),
    clearDisplay: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      supported: false,
      action: 'clear_display',
      message: 'Meta Wearables DAT display clearing is unavailable in this build.',
      targetConnectionState: 'unselected',
      deviceId: null,
      assetUri: null,
      mimeType: null,
    }),
    playDisplayVideo: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      supported: false,
      action: 'play_display_video',
      message: 'Meta Wearables DAT display video playback is unavailable in this build.',
      targetConnectionState: 'unselected',
      deviceId: null,
      assetUri: null,
      mimeType: null,
    }),
    resetDisplaySession: async () => ({
      state: 'unavailable',
      mode: 'unavailable',
      supported: false,
      action: 'reset_display_session',
      message: 'Meta Wearables DAT display session reset is unavailable in this build.',
      targetConnectionState: 'unselected',
      deviceId: null,
      assetUri: null,
      mimeType: null,
    }),
    addStateListener: () => ({ remove() {} }),
    addBridgeStateListener: () => ({ remove() {} }),
  };
}

function wrapBridgeModule(module) {
  return {
    isAvailable: () => Boolean(module?.isAvailable?.()),
    isBridgeAvailable: () => Boolean(module?.isAvailable?.()),
    getConfiguration: async () => {
      const configuration = await module.getConfiguration();
      return {
        provider: 'internal_bridge',
        integrationMode: configuration?.sdkLinked ? 'sdk_reflection' : 'reference_only',
        ...configuration,
      };
    },
    getCapabilities: async () => await module.getCapabilities(),
    getConnectedDevice: async () => await module.getConnectedDevice(),
    getSessionState: async () => await module.getSessionState(),
    getAdapterState: async () => await module.getAdapterState(),
    getKnownDevices: async () => await module.getKnownDevices(),
    scanKnownAndNearbyDevices: async (timeoutMs = 2500) => await module.scanKnownAndNearbyDevices(timeoutMs),
    getSelectedDeviceTarget: async () => await module.getSelectedDeviceTarget(),
    selectDeviceTarget: async (deviceId) => await module.selectDeviceTarget(deviceId),
    clearDeviceTarget: async () => await module.clearDeviceTarget(),
    reconnectSelectedDeviceTarget: async () => await module.reconnectSelectedDeviceTarget(),
    connectSelectedDeviceTarget: async () => await module.connectSelectedDeviceTarget(),
    getDiagnostics: async () => {
      const diagnostics = await module.getDiagnostics();
      return {
        provider: 'internal_bridge',
        integrationMode: diagnostics?.sdkLinked ? 'sdk_reflection' : 'reference_only',
        ...diagnostics,
      };
    },
    startDeviceSession: async () => await module.startDeviceSession(),
    stopDeviceSession: async () => await module.stopDeviceSession(),
    startBridgeSession: async () => await module.startDeviceSession(),
    stopBridgeSession: async () => await module.stopDeviceSession(),
    capturePhoto: async () => await module.capturePhoto(),
    startVideoStream: async () => await module.startVideoStream(),
    stopVideoStream: async () => await module.stopVideoStream(),
    renderDisplayTest: async () => await module.renderDisplayTest(),
    clearDisplay: async () => await module.clearDisplay(),
    playDisplayVideo: async (videoUrl) => await module.playDisplayVideo(videoUrl),
    resetDisplaySession: async () => await module.resetDisplaySession(),
    addStateListener: (...args) => module.addStateListener(...args),
    addBridgeStateListener: (...args) => module.addStateListener(...args),
  };
}

let cached = null;

export async function getWearablesBridge() {
  if (cached) {
    return cached;
  }

  try {
    const module = require('expo-meta-wearables-dat').default;
    cached = wrapBridgeModule(module || createUnavailableBridge());
    return cached;
  } catch {
    cached = createUnavailableBridge();
    return cached;
  }
}

export function clearWearablesBridgeCache() {
  cached = null;
}
