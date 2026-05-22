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
    const photo = await bridge.capturePhoto();
    const widgetPayload = {
      contract: 'handsfree.meta-glasses/display-widget-action@0.1.0',
      type: 'mobile_render_display_widget',
      descriptor_cid: 'bafybeidescriptor',
      widget_id: 'handsfree.task-progress-widget',
      widget_cid: 'bafybeiwidget',
      orb_receipt_cid: 'bafybeiorbreceipt',
      correlation_id: 'corr-widget',
      fallback: {
        reason: 'dat_native_display_unavailable',
        renderPath: 'display-webapp',
        message: 'Native display unavailable. Opening display webapp preview.',
      },
    };
    const renderedWidget = await bridge.renderDisplayWidget(
      { id: 'handsfree.task-progress-widget' },
      widgetPayload
    );
    const updatedWidget = await bridge.updateDisplayWidget({ progress: 50 }, widgetPayload);
    const clearedWidget = await bridge.clearDisplayWidget('handsfree.task-progress-widget', widgetPayload);
    const focusedWidget = await bridge.focusDisplayWidget('next', widgetPayload);
    const activatedWidget = await bridge.activateDisplayWidgetAction('primary', widgetPayload);
    const resetWidget = await bridge.resetDisplayWidgetSession(widgetPayload);

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
    expect(photo).toMatchObject({
      action: 'capture_photo',
      supported: false,
    });
    expect(renderedWidget).toMatchObject({
      action: 'render_display_widget',
      operation: 'render_widget',
      supported: false,
      reason: 'dat_native_display_unavailable',
      renderPath: 'display-webapp',
      message: 'Native display unavailable. Opening display webapp preview.',
      descriptorCid: 'bafybeidescriptor',
      widgetId: 'handsfree.task-progress-widget',
      widgetCid: 'bafybeiwidget',
      orbReceiptCid: 'bafybeiorbreceipt',
      correlationId: 'corr-widget',
      displayConnectionState: 'unavailable',
      displayLastStatus: 'unsupported',
    });
    expect(updatedWidget).toMatchObject({
      action: 'update_display_widget',
      operation: 'update_widget',
      supported: false,
      widgetId: 'handsfree.task-progress-widget',
    });
    expect(clearedWidget).toMatchObject({
      action: 'clear_display_widget',
      operation: 'clear_widget',
      supported: false,
      widgetId: 'handsfree.task-progress-widget',
    });
    expect(focusedWidget).toMatchObject({
      action: 'focus_display_widget',
      operation: 'focus_next',
      supported: false,
      widgetId: 'handsfree.task-progress-widget',
    });
    expect(activatedWidget).toMatchObject({
      action: 'activate_display_widget_action',
      operation: 'activate',
      supported: false,
      widgetId: 'handsfree.task-progress-widget',
    });
    expect(resetWidget).toMatchObject({
      action: 'reset_display_widget_session',
      operation: 'reset_session',
      supported: false,
      widgetId: 'handsfree.task-progress-widget',
    });
  });

  test('delegates display widget methods when the native module exposes them', async () => {
    const nativeModule = {
      isAvailable: () => true,
      renderDisplayWidget: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        message: 'Widget rendered.',
        displayConnectionState: 'rendered',
      })),
      updateDisplayWidget: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        message: 'Widget updated.',
      })),
      clearDisplayWidget: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        message: 'Widget cleared.',
      })),
      focusDisplayWidget: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        message: 'Widget focused.',
      })),
      activateDisplayWidgetAction: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        message: 'Widget action activated.',
      })),
      resetDisplayWidgetSession: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        message: 'Widget session reset.',
      })),
    };

    jest.doMock('expo-meta-wearables-dat', () => ({
      __esModule: true,
      default: nativeModule,
    }));

    const { getWearablesBridge, clearWearablesBridgeCache } = require('../wearablesBridge');
    clearWearablesBridgeCache();

    const bridge = await getWearablesBridge();
    const payload = {
      descriptor_cid: 'bafybeidescriptor',
      widget_id: 'handsfree.task-progress-widget',
      widget_cid: 'bafybeiwidget',
      orb_receipt_cid: 'bafybeiorbreceipt',
      correlation_id: 'corr-widget',
    };
    const manifest = { id: 'handsfree.task-progress-widget' };
    const patch = { progress: 75 };

    await expect(bridge.renderDisplayWidget(manifest, payload)).resolves.toMatchObject({
      action: 'render_display_widget',
      operation: 'render_widget',
      supported: true,
      renderPath: 'native-dat',
      fallback: null,
      descriptorCid: 'bafybeidescriptor',
      widgetId: 'handsfree.task-progress-widget',
    });
    await expect(bridge.updateDisplayWidget(patch, payload)).resolves.toMatchObject({
      action: 'update_display_widget',
      operation: 'update_widget',
      supported: true,
    });
    await expect(bridge.clearDisplayWidget('handsfree.task-progress-widget', payload)).resolves.toMatchObject({
      action: 'clear_display_widget',
      operation: 'clear_widget',
      supported: true,
    });
    await expect(bridge.focusDisplayWidget('next', payload)).resolves.toMatchObject({
      action: 'focus_display_widget',
      operation: 'focus_next',
      supported: true,
    });
    await expect(bridge.activateDisplayWidgetAction('primary', payload)).resolves.toMatchObject({
      action: 'activate_display_widget_action',
      operation: 'activate',
      supported: true,
    });
    await expect(bridge.resetDisplayWidgetSession(payload)).resolves.toMatchObject({
      action: 'reset_display_widget_session',
      operation: 'reset_session',
      supported: true,
    });

    expect(nativeModule.renderDisplayWidget).toHaveBeenCalledWith(manifest);
    expect(nativeModule.updateDisplayWidget).toHaveBeenCalledWith(patch);
    expect(nativeModule.clearDisplayWidget).toHaveBeenCalledWith('handsfree.task-progress-widget');
    expect(nativeModule.focusDisplayWidget).toHaveBeenCalledWith('next');
    expect(nativeModule.activateDisplayWidgetAction).toHaveBeenCalledWith('primary');
    expect(nativeModule.resetDisplayWidgetSession).toHaveBeenCalledWith();
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
      capturePhoto: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        action: 'capture_photo',
        message: 'Captured photo.',
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
    const photo = await bridge.capturePhoto();

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
    expect(photo).toMatchObject({
      action: 'capture_photo',
      supported: true,
    });
    await expect(bridge.startBridgeSession()).resolves.toMatchObject({
      state: 'target_ready',
      targetConnectionState: 'ready',
    });
  });
});
