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
        adapterState: {
          transport: 'bluetooth',
          adapterAvailable: true,
          adapterEnabled: true,
          scanPermissionGranted: true,
          connectPermissionGranted: true,
          advertisePermissionGranted: true,
          state: 'powered_on',
        },
        knownDeviceCount: 2,
        selectedDeviceId: 'AA:BB',
        selectedDeviceName: 'Ray-Ban Meta',
        targetConnectionState: 'discovered',
        targetLastSeenAt: 1700000000000,
        targetRssi: -42,
      })),
      getAdapterState: jest.fn(async () => ({
        transport: 'bluetooth',
        adapterAvailable: true,
        adapterEnabled: true,
        scanPermissionGranted: true,
        connectPermissionGranted: true,
        advertisePermissionGranted: true,
        state: 'powered_on',
      })),
      getKnownDevices: jest.fn(async () => [
        { deviceId: 'AA:BB', deviceName: 'Ray-Ban Meta' },
        { deviceId: 'CC:DD', deviceName: 'Headset' },
      ]),
      scanKnownAndNearbyDevices: jest.fn(async () => [
        { deviceId: 'AA:BB', deviceName: 'Ray-Ban Meta', source: 'bonded+scan', rssi: -42 },
      ]),
      getSelectedDeviceTarget: jest.fn(async () => ({
        deviceId: 'AA:BB',
        deviceName: 'Ray-Ban Meta',
        source: 'bonded+scan',
      })),
      selectDeviceTarget: jest.fn(async (deviceId) => ({
        deviceId,
        deviceName: 'Ray-Ban Meta',
        source: 'bonded+scan',
      })),
      clearDeviceTarget: jest.fn(async () => ({
        deviceId: 'AA:BB',
        deviceName: 'Ray-Ban Meta',
      })),
      reconnectSelectedDeviceTarget: jest.fn(async () => ({
        state: 'target_discovered',
        mode: 'reference_only',
        deviceId: 'AA:BB',
        targetConnectionState: 'discovered',
      })),
      connectSelectedDeviceTarget: jest.fn(async () => ({
        state: 'target_connected',
        mode: 'reference_only',
        deviceId: 'AA:BB',
        targetConnectionState: 'connected',
      })),
      startDeviceSession: jest.fn(async () => ({
        state: 'target_ready',
        mode: 'reference_only',
        deviceId: 'AA:BB',
        targetConnectionState: 'ready',
      })),
      stopDeviceSession: jest.fn(async () => ({
        state: 'idle',
        mode: 'reference_only',
        deviceId: 'AA:BB',
        targetConnectionState: 'selected',
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
    const diagnostics = await first.getDiagnostics();
    const reconnect = await first.reconnectSelectedDeviceTarget();
    const connect = await first.connectSelectedDeviceTarget();

    expect(first.isDatAvailable).toBeDefined();
    expect(second).toBe(first);
    expect(diagnostics.targetConnectionState).toBe('discovered');
    expect(reconnect.targetConnectionState).toBe('discovered');
    expect(connect.targetConnectionState).toBe('connected');
  });
});
