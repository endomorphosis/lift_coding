jest.mock('expo-modules-core', () => {
  class MockEventEmitter {
    addListener(_eventName, listener) {
      return {
        remove() {
          return listener;
        },
      };
    }
  }

  return {
    EventEmitter: MockEventEmitter,
    requireOptionalNativeModule: jest.fn(),
  };
});

describe('expo-meta-wearables-dat module wrapper', () => {
  afterEach(() => {
    jest.resetModules();
    delete process.env.EXPO_OS;
  });

  test('returns safe fallbacks when native module is absent', async () => {
    process.env.EXPO_OS = 'android';
    const { requireOptionalNativeModule } = require('expo-modules-core');
    requireOptionalNativeModule.mockReturnValue(undefined);

    const module = require('..').default;

    await expect(module.isDatAvailable()).resolves.toBe(false);
    await expect(module.getConfiguration()).resolves.toMatchObject({
      sdkLinked: false,
      sdkConfigured: false,
      integrationMode: 'unavailable',
    });
    await expect(module.getCapabilities()).resolves.toEqual({
      session: false,
      camera: false,
      photoCapture: false,
      videoStream: false,
      audio: false,
      display: false,
      displayVideo: false,
    });
    await expect(module.getDiagnostics()).resolves.toMatchObject({
      available: false,
      sessionState: 'unavailable',
      targetConnectionState: 'unselected',
      knownDeviceCount: 0,
      displayReady: false,
      displayRenderPath: 'mobile-card',
      displayLastError: 'dat_native_display_unavailable',
      displayUpdateCount: 0,
      displayLifecycleStages: [],
    });
    await expect(module.capturePhoto()).resolves.toMatchObject({
      action: 'capture_photo',
      supported: false,
    });
    await expect(module.startVideoStream()).resolves.toMatchObject({
      action: 'start_video_stream',
      supported: false,
    });
    await expect(module.renderDisplayWidget({ id: 'handsfree.task-progress-widget' })).resolves.toMatchObject({
      action: 'render_display_widget',
      operation: 'render_widget',
      supported: false,
      reason: 'dat_native_display_unavailable',
      renderPath: 'mobile-card',
    });
    await expect(module.updateDisplayWidget({ widget_id: 'handsfree.task-progress-widget' })).resolves.toMatchObject({
      action: 'update_display_widget',
      operation: 'update_widget',
      supported: false,
    });
    await expect(module.clearDisplayWidget('handsfree.task-progress-widget')).resolves.toMatchObject({
      action: 'clear_display_widget',
      operation: 'clear_widget',
      supported: false,
    });
    await expect(module.focusDisplayWidget('next')).resolves.toMatchObject({
      action: 'focus_display_widget',
      operation: 'focus_next',
      supported: false,
    });
    await expect(module.focusDisplayWidget('previous')).resolves.toMatchObject({
      action: 'focus_display_widget',
      operation: 'focus_previous',
      supported: false,
    });
    await expect(module.activateDisplayWidgetAction('primary')).resolves.toMatchObject({
      action: 'activate_display_widget_action',
      operation: 'activate',
      supported: false,
    });
    await expect(module.resetDisplayWidgetSession()).resolves.toMatchObject({
      action: 'reset_display_widget_session',
      operation: 'reset_session',
      supported: false,
    });
    await expect(module.reconnectSelectedDeviceTarget()).resolves.toMatchObject({
      mode: 'unavailable',
      targetConnectionState: 'unselected',
    });
    expect(module.addStateListener(() => {})).toMatchObject({
      remove: expect.any(Function),
    });
  });

  test('delegates to the native module when linked', async () => {
    const nativeModule = {
      isDatAvailable: jest.fn(async () => true),
      getConfiguration: jest.fn(async () => ({
        platform: 'ios',
        sdkLinked: true,
        sdkConfigured: true,
        analyticsOptOut: true,
        sdkVersion: '0.5.0',
        applicationId: 'handsfree-dev',
        provider: 'internal_bridge',
        integrationMode: 'sdk_reflection',
      })),
      getCapabilities: jest.fn(async () => ({
        session: true,
        camera: true,
        photoCapture: true,
        videoStream: false,
        audio: false,
        display: true,
        displayVideo: true,
      })),
      getDiagnostics: jest.fn(async () => ({
        available: true,
        platform: 'ios',
        sdkLinked: true,
        sdkConfigured: true,
        analyticsOptOut: true,
        sdkVersion: '0.5.0',
        applicationId: 'handsfree-dev',
        provider: 'internal_bridge',
        integrationMode: 'sdk_reflection',
        capabilities: {
          session: true,
          camera: true,
          photoCapture: true,
          videoStream: false,
          audio: false,
          display: true,
          displayVideo: true,
        },
        sessionState: 'target_ready',
        displayReady: true,
        displayRenderPath: 'native-dat',
        displayLastError: null,
        displayUpdateCount: 0,
        displayLifecycleStages: ['target_selected', 'session_started', 'display_started'],
      })),
      capturePhoto: jest.fn(async () => ({
        state: 'ready',
        mode: 'sdk_reflection',
        supported: true,
        action: 'capture_photo',
        message: 'Captured photo.',
      })),
      renderDisplayWidget: jest.fn(async (manifest) => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'render_display_widget',
        operation: 'render_widget',
        message: 'DAT display widget sent.',
        renderPath: 'native-dat',
        widgetId: manifest.id,
        displayLifecycleStages: [
          'target_selected',
          'starting_session',
          'session_started',
          'attaching_display',
          'display_attached',
          'display_started',
          'display_ready',
          'content_sent',
        ],
      })),
      updateDisplayWidget: jest.fn(async () => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'update_display_widget',
        message: 'DAT display widget updated.',
        renderPath: 'native-dat',
      })),
      clearDisplayWidget: jest.fn(async () => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'clear_display_widget',
        message: 'DAT display widget cleared.',
        renderPath: 'native-dat',
      })),
      focusDisplayWidget: jest.fn(async () => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'focus_display_widget',
        message: 'DAT display widget focused.',
        renderPath: 'native-dat',
      })),
      activateDisplayWidgetAction: jest.fn(async () => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'activate_display_widget_action',
        message: 'DAT display widget action activated.',
        renderPath: 'native-dat',
      })),
      resetDisplayWidgetSession: jest.fn(async () => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'reset_display_widget_session',
        message: 'DAT display widget session reset.',
        renderPath: 'native-dat',
      })),
    };

    const { requireOptionalNativeModule } = require('expo-modules-core');
    requireOptionalNativeModule.mockReturnValue(nativeModule);

    const module = require('..').default;

    await expect(module.isDatAvailable()).resolves.toBe(true);
    await expect(module.getConfiguration()).resolves.toMatchObject({
      sdkLinked: true,
      sdkConfigured: true,
      integrationMode: 'sdk_reflection',
    });
    await expect(module.getCapabilities()).resolves.toMatchObject({
      camera: true,
      photoCapture: true,
    });
    await expect(module.getDiagnostics()).resolves.toMatchObject({
      available: true,
      sessionState: 'target_ready',
      displayReady: true,
      displayRenderPath: 'native-dat',
      displayLastError: null,
      displayLifecycleStages: expect.arrayContaining(['target_selected', 'display_started']),
    });
    await expect(module.capturePhoto()).resolves.toMatchObject({
      action: 'capture_photo',
      supported: true,
      message: 'Captured photo.',
    });
    await expect(module.renderDisplayWidget({ id: 'handsfree.task-progress-widget' })).resolves.toMatchObject({
      action: 'render_display_widget',
      supported: true,
      renderPath: 'native-dat',
      widgetId: 'handsfree.task-progress-widget',
      displayLifecycleStages: expect.arrayContaining([
        'target_selected',
        'session_started',
        'display_attached',
        'display_started',
        'content_sent',
      ]),
    });
    await expect(module.updateDisplayWidget({ widget_id: 'handsfree.task-progress-widget' })).resolves.toMatchObject({
      action: 'update_display_widget',
      supported: true,
    });
    await expect(module.clearDisplayWidget('handsfree.task-progress-widget')).resolves.toMatchObject({
      action: 'clear_display_widget',
      supported: true,
    });
    await expect(module.focusDisplayWidget('next')).resolves.toMatchObject({
      action: 'focus_display_widget',
      supported: true,
    });
    await expect(module.activateDisplayWidgetAction('primary')).resolves.toMatchObject({
      action: 'activate_display_widget_action',
      supported: true,
    });
    await expect(module.resetDisplayWidgetSession()).resolves.toMatchObject({
      action: 'reset_display_widget_session',
      supported: true,
    });
    expect(nativeModule.renderDisplayWidget).toHaveBeenCalledWith({
      id: 'handsfree.task-progress-widget',
    });
    expect(nativeModule.updateDisplayWidget).toHaveBeenCalledWith({
      widget_id: 'handsfree.task-progress-widget',
    });
    expect(nativeModule.clearDisplayWidget).toHaveBeenCalledWith('handsfree.task-progress-widget');
    expect(nativeModule.focusDisplayWidget).toHaveBeenCalledWith('next');
    expect(nativeModule.activateDisplayWidgetAction).toHaveBeenCalledWith('primary');
    expect(nativeModule.resetDisplayWidgetSession).toHaveBeenCalledWith();
  });

  test.each([
    {
      reason: 'dat_app_update_required',
      message: 'DAT glasses app update is required before display rendering.',
      requiredAction: 'open_dat_glasses_app_update',
    },
    {
      reason: 'firmware_update_required',
      message: 'Glasses firmware update is required before DAT display rendering.',
      requiredAction: 'open_firmware_update',
    },
  ])('preserves native display update-required metadata for $reason', async ({
    reason,
    message,
    requiredAction,
  }) => {
    const nativeModule = {
      renderDisplayWidget: jest.fn(async () => ({
        state: 'not_supported',
        mode: 'sdk_reflection',
        supported: false,
        action: 'render_display_widget',
        operation: 'render_widget',
        reason,
        message,
        renderPath: 'mobile-card',
        requiredAction,
        displayRenderPath: 'mobile-card',
        displayLastError: reason,
        displayLifecycleStages: ['target_selected'],
        fallback: {
          reason,
          renderPath: 'mobile-card',
        },
      })),
    };

    const { requireOptionalNativeModule } = require('expo-modules-core');
    requireOptionalNativeModule.mockReturnValue(nativeModule);

    const module = require('..').default;

    await expect(module.renderDisplayWidget({ id: 'handsfree.task-progress-widget' })).resolves.toMatchObject({
      action: 'render_display_widget',
      supported: false,
      reason,
      requiredAction,
      renderPath: 'mobile-card',
      displayLastError: reason,
      displayLifecycleStages: ['target_selected'],
    });
  });
});
