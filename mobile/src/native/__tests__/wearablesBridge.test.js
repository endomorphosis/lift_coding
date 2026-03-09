describe('wearablesBridge wrapper', () => {
  afterEach(() => {
    jest.resetModules();
  });

  test('returns fallback diagnostics when native module is unavailable', async () => {
    jest.doMock('expo-meta-wearables-dat', () => {
      throw new Error('module unavailable');
    });

    const { getWearablesBridge, clearWearablesBridgeCache } = require('../wearablesBridge');
    clearWearablesBridgeCache();

    const bridge = await getWearablesBridge();
    const diagnostics = await bridge.getDiagnostics();

    expect(bridge.isBridgeAvailable()).toBe(false);
    expect(diagnostics).toEqual({
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
    });
  });

  test('normalizes resolved native module diagnostics into bridge metadata', async () => {
    const nativeModule = {
      isAvailable: () => true,
      getConfiguration: jest.fn(async () => ({
        platform: 'android',
        sdkLinked: false,
        sdkConfigured: false,
        analyticsOptOut: true,
        sdkVersion: '0.4.0',
        applicationId: 'handsfree-dev',
      })),
      getCapabilities: jest.fn(async () => ({
        session: true,
        camera: false,
        photoCapture: false,
        videoStream: false,
        audio: false,
      })),
      getConnectedDevice: jest.fn(async () => null),
      getSessionState: jest.fn(async () => 'idle'),
      getDiagnostics: jest.fn(async () => ({
        available: true,
        platform: 'android',
        sdkLinked: false,
        sdkConfigured: false,
        analyticsOptOut: true,
        sdkVersion: '0.4.0',
        applicationId: 'handsfree-dev',
        capabilities: {
          session: true,
          camera: false,
          photoCapture: false,
          videoStream: false,
          audio: false,
        },
        sessionState: 'idle',
        registrationState: 'Unavailable',
        deviceCount: 0,
        activeDeviceId: null,
      })),
      startDeviceSession: jest.fn(async () => ({ state: 'idle', mode: 'simulated' })),
      stopDeviceSession: jest.fn(async () => ({ state: 'idle', mode: 'simulated' })),
      addStateListener: jest.fn(() => ({ remove() {} })),
    };

    jest.doMock('expo-meta-wearables-dat', () => ({
      __esModule: true,
      default: nativeModule,
    }));

    const { getWearablesBridge, clearWearablesBridgeCache } = require('../wearablesBridge');
    clearWearablesBridgeCache();

    const bridge = await getWearablesBridge();
    const configuration = await bridge.getConfiguration();
    const diagnostics = await bridge.getDiagnostics();

    expect(bridge.isBridgeAvailable()).toBe(true);
    expect(configuration.provider).toBe('internal_bridge');
    expect(configuration.integrationMode).toBe('reference_only');
    expect(diagnostics.provider).toBe('internal_bridge');
    expect(diagnostics.integrationMode).toBe('reference_only');
  });
});
