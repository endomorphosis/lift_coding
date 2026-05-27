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
    const renderedWidget = await module.renderDisplayWidget(
      { id: 'handsfree.task-progress-widget' },
      {
        descriptor_cid: 'bafybeidescriptor',
        widget_id: 'handsfree.task-progress-widget',
        widget_cid: 'bafybeiwidget',
        orb_receipt_cid: 'bafybeiorbreceipt',
        correlation_id: 'corr-widget',
      }
    );

    expect(module.isAvailable()).toBe(false);
    expect(typeof module.renderDisplayWidget).toBe('function');
    expect(typeof module.updateDisplayWidget).toBe('function');
    expect(typeof module.clearDisplayWidget).toBe('function');
    expect(typeof module.focusDisplayWidget).toBe('function');
    expect(typeof module.activateDisplayWidgetAction).toBe('function');
    expect(typeof module.resetDisplayWidgetSession).toBe('function');
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
      displayConnectionState: 'unavailable',
      displayLastAction: null,
      displayLastStatus: null,
      displayLastUpdatedAt: null,
      displayRenderPath: 'mobile-card',
      displayLastError: null,
      displayActiveWidgetId: null,
      displayDescriptorCid: null,
      displayInterfaceCid: null,
      displayManifestCid: null,
      displayWidgetCid: null,
      displayOrbReceiptCid: null,
      displayReceiptCid: null,
      displayPolicyDecision: null,
      displayCorrelationId: null,
      displayRequestId: null,
      displayFallback: null,
      displayUpdateCount: 0,
      displayLifecycleStages: [],
    });
    expect(renderedWidget).toMatchObject({
      action: 'render_display_widget',
      operation: 'render_widget',
      supported: false,
      reason: 'dat_native_display_unavailable',
      descriptorCid: 'bafybeidescriptor',
      widgetId: 'handsfree.task-progress-widget',
      widgetCid: 'bafybeiwidget',
      orbReceiptCid: 'bafybeiorbreceipt',
      correlationId: 'corr-widget',
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
          display: false,
          displayVideo: false,
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
