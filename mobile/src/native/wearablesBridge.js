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
      },
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
