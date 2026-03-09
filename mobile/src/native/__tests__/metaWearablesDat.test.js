describe('metaWearablesDat wrapper', () => {
  afterEach(() => {
    jest.resetModules();
  });

  test('returns fallback diagnostics when native module is unavailable', async () => {
    jest.doMock('expo-meta-wearables-dat', () => {
      throw new Error('module unavailable');
    });

    const { getMetaWearablesDat, clearMetaWearablesDatCache } = require('../metaWearablesDat');
    clearMetaWearablesDatCache();

    const module = await getMetaWearablesDat();
    const diagnostics = await module.getDiagnostics();

    expect(module.isAvailable()).toBe(false);
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

  test('caches the resolved native module instance', async () => {
    const nativeModule = {
      isAvailable: () => true,
      getDiagnostics: jest.fn(async () => ({
        available: true,
        platform: 'android',
        sdkLinked: false,
        sdkConfigured: false,
        analyticsOptOut: true,
        sdkVersion: '0.4.0',
        applicationId: 'handsfree-dev',
        provider: 'internal_bridge',
        integrationMode: 'reference_only',
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
      addStateListener: jest.fn(() => ({ remove() {} })),
    };

    jest.doMock('expo-meta-wearables-dat', () => ({
      __esModule: true,
      default: nativeModule,
    }));

    const { getMetaWearablesDat, clearMetaWearablesDatCache } = require('../metaWearablesDat');
    clearMetaWearablesDatCache();

    const first = await getMetaWearablesDat();
    const second = await getMetaWearablesDat();

    expect(first.isDatAvailable).toBeDefined();
    expect(second).toBe(first);
  });
});
