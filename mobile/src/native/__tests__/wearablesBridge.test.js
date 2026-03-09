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
    const reconnect = await bridge.reconnectSelectedDeviceTarget();
    const connect = await bridge.connectSelectedDeviceTarget();

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
    expect(reconnect).toEqual({
      state: 'awaiting_target',
      mode: 'unavailable',
      deviceId: null,
      targetConnectionState: 'unselected',
    });
    expect(connect).toEqual({
      state: 'awaiting_target',
      mode: 'unavailable',
      deviceId: null,
      targetConnectionState: 'unselected',
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
        { deviceId: 'CC:DD', deviceName: 'Headset', source: 'bonded' },
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
        targetLastSeenAt: 1700000000000,
        targetRssi: -42,
      })),
      connectSelectedDeviceTarget: jest.fn(async () => ({
        state: 'target_connected',
        mode: 'reference_only',
        deviceId: 'AA:BB',
        targetConnectionState: 'connected',
        targetLastSeenAt: 1700000000000,
        targetRssi: -42,
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

    const { getWearablesBridge, clearWearablesBridgeCache } = require('../wearablesBridge');
    clearWearablesBridgeCache();

    const bridge = await getWearablesBridge();
    const configuration = await bridge.getConfiguration();
    const diagnostics = await bridge.getDiagnostics();
    const candidates = await bridge.scanKnownAndNearbyDevices();
    const selected = await bridge.getSelectedDeviceTarget();
    const reconnect = await bridge.reconnectSelectedDeviceTarget();
    const connect = await bridge.connectSelectedDeviceTarget();

    expect(bridge.isBridgeAvailable()).toBe(true);
    expect(configuration.provider).toBe('internal_bridge');
    expect(configuration.integrationMode).toBe('reference_only');
    expect(diagnostics.provider).toBe('internal_bridge');
    expect(diagnostics.integrationMode).toBe('reference_only');
    expect(diagnostics.targetConnectionState).toBe('discovered');
    expect(diagnostics.targetRssi).toBe(-42);
    expect(candidates).toHaveLength(2);
    expect(selected?.deviceId).toBe('AA:BB');
    expect(reconnect).toMatchObject({
      state: 'target_discovered',
      targetConnectionState: 'discovered',
      targetRssi: -42,
    });
    expect(connect).toMatchObject({
      state: 'target_connected',
      targetConnectionState: 'connected',
      targetRssi: -42,
    });
    await expect(bridge.startBridgeSession()).resolves.toMatchObject({
      state: 'target_ready',
      targetConnectionState: 'ready',
    });
  });
});
