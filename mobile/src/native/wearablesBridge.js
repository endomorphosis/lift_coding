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
    }),
    startDeviceSession: async () => ({ state: 'unavailable', mode: 'unavailable' }),
    stopDeviceSession: async () => ({ state: 'unavailable', mode: 'unavailable' }),
    startBridgeSession: async () => ({ state: 'unavailable', mode: 'unavailable' }),
    stopBridgeSession: async () => ({ state: 'unavailable', mode: 'unavailable' }),
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
