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
    const widgetPayload = {
      contract: 'handsfree.meta-glasses/display-widget-action@0.1.0',
      type: 'mobile_render_display_widget',
      descriptor_cid: 'bafybeidescriptor',
      interface_cid: 'bafybeiinterface',
      manifest_cid: 'bafybeimanifest',
      widget_id: 'handsfree.task-progress-widget',
      widget_cid: 'bafybeiwidget',
      orb_receipt_cid: 'bafybeireceipt',
      policy_decision: { outcome: 'permit' },
      correlation_id: 'corr-widget',
      request_id: 'req-widget',
      fallback: {
        reason: 'dat_native_display_unavailable',
        renderPath: 'display-webapp',
        message: 'Opening display webapp preview.',
      },
    };
    await expect(module.renderDisplayWidget({ id: 'handsfree.task-progress-widget' }, widgetPayload)).resolves.toMatchObject({
      action: 'render_display_widget',
      operation: 'render_widget',
      supported: false,
      reason: 'dat_native_display_unavailable',
      renderPath: 'display-webapp',
      descriptorCid: 'bafybeidescriptor',
      interfaceCid: 'bafybeiinterface',
      manifestCid: 'bafybeimanifest',
      widgetId: 'handsfree.task-progress-widget',
      widgetCid: 'bafybeiwidget',
      orbReceiptCid: 'bafybeireceipt',
      policyDecision: { outcome: 'permit' },
      correlationId: 'corr-widget',
      requestId: 'req-widget',
    });
    await expect(module.updateDisplayWidget({ widget_id: 'handsfree.task-progress-widget' }, widgetPayload)).resolves.toMatchObject({
      action: 'update_display_widget',
      operation: 'update_widget',
      supported: false,
      descriptorCid: 'bafybeidescriptor',
    });
    await expect(module.clearDisplayWidget('handsfree.task-progress-widget', widgetPayload)).resolves.toMatchObject({
      action: 'clear_display_widget',
      operation: 'clear_widget',
      supported: false,
      widgetCid: 'bafybeiwidget',
    });
    await expect(module.focusDisplayWidget('next', widgetPayload)).resolves.toMatchObject({
      action: 'focus_display_widget',
      operation: 'focus_next',
      supported: false,
      orbReceiptCid: 'bafybeireceipt',
    });
    await expect(module.focusDisplayWidget('previous', widgetPayload)).resolves.toMatchObject({
      action: 'focus_display_widget',
      operation: 'focus_previous',
      supported: false,
    });
    await expect(module.activateDisplayWidgetAction('primary', widgetPayload)).resolves.toMatchObject({
      action: 'activate_display_widget_action',
      operation: 'activate',
      supported: false,
      requestId: 'req-widget',
    });
    await expect(module.resetDisplayWidgetSession(widgetPayload)).resolves.toMatchObject({
      action: 'reset_display_widget_session',
      operation: 'reset_session',
      supported: false,
      correlationId: 'corr-widget',
    });
    await expect(module.playDisplayWidgetVideo({ uri: 'ipfs://bafybeivideo' }, widgetPayload)).resolves.toMatchObject({
      action: 'play_display_widget_video',
      operation: 'play_video',
      supported: false,
      renderPath: 'display-webapp',
    });
    await expect(module.subscribeDisplayWidgetUpdates({ stream: 'display_widget_update' }, widgetPayload)).resolves.toMatchObject({
      action: 'subscribe_display_widget_updates',
      operation: 'subscribe_updates',
      supported: false,
      fallback: expect.objectContaining({
        renderPath: 'display-webapp',
      }),
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
        widgetId: manifest.widget_id || manifest.id,
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
      playDisplayWidgetVideo: jest.fn(async () => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'play_display_widget_video',
        message: 'DAT display widget video playback queued.',
        renderPath: 'native-dat',
      })),
      subscribeDisplayWidgetUpdates: jest.fn(async () => ({
        state: 'ready',
        mode: 'native_display',
        supported: true,
        action: 'subscribe_display_widget_updates',
        message: 'DAT display widget update subscription queued.',
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
    const widgetPayload = {
      descriptor_cid: 'bafybeidescriptor',
      widget_id: 'handsfree.task-progress-widget',
      widget_cid: 'bafybeiwidget',
      orb_receipt_cid: 'bafybeireceipt',
      policy_decision: { outcome: 'permit' },
      correlation_id: 'corr-widget',
      request_id: 'req-widget',
    };
    const manifest = {
      schema: 'handsfree.meta-glasses/widget-manifest',
      schema_version: '0.1.0',
      widget_id: 'handsfree.task-progress-widget',
      widget_cid: 'bafybeiwidget',
      interface_cid: 'bafybeiinterface',
      operation: 'render_widget',
      viewport: { width: 600, height: 600 },
      regions: [
        {
          id: 'title',
          kind: 'text',
          bounds: { x: 24, y: 24, width: 552, height: 72 },
          text: { source: 'state.title', value: 'Sync dataset', max_lines: 2, max_chars: 64, overflow: 'truncate' },
        },
        {
          id: 'progress',
          kind: 'progress',
          bounds: { x: 24, y: 304, width: 552, height: 120 },
          text: { source: 'state.progress_label', value: '42% complete', max_lines: 2, max_chars: 48, overflow: 'truncate' },
        },
        {
          id: 'pause-control',
          kind: 'action',
          bounds: { x: 24, y: 464, width: 264, height: 80 },
          action_id: 'pause',
        },
        {
          id: 'preview',
          kind: 'media',
          bounds: { x: 312, y: 464, width: 264, height: 80 },
          media_id: 'preview-media',
        },
      ],
      focus_order: ['pause'],
      actions: [
        {
          id: 'pause',
          method: 'activate',
          backend_action_id: 'handsfree.task.pause',
          label: 'Pause',
          focusable: true,
          region_id: 'pause-control',
        },
      ],
      media: [
        {
          id: 'preview-media',
          region_id: 'preview',
          type: 'video/mp4',
          transport: 'cid',
          fallback_text: 'Video preview opens on phone.',
        },
      ],
      state: {
        keys: ['title', 'progress_label'],
        values: {
          title: 'Sync dataset',
          progress_label: '42% complete',
        },
      },
      fallback: {
        render_path: 'mobile-card',
        message: 'Display unavailable. Showing task progress on phone.',
      },
    };
    const patch = { widget_id: 'handsfree.task-progress-widget' };
    await expect(module.renderDisplayWidget(manifest, widgetPayload)).resolves.toMatchObject({
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
    await expect(module.updateDisplayWidget(patch, widgetPayload)).resolves.toMatchObject({
      action: 'update_display_widget',
      supported: true,
    });
    await expect(module.clearDisplayWidget('handsfree.task-progress-widget', widgetPayload)).resolves.toMatchObject({
      action: 'clear_display_widget',
      supported: true,
    });
    await expect(module.focusDisplayWidget('next', widgetPayload)).resolves.toMatchObject({
      action: 'focus_display_widget',
      supported: true,
    });
    await expect(module.activateDisplayWidgetAction('primary', widgetPayload)).resolves.toMatchObject({
      action: 'activate_display_widget_action',
      supported: true,
    });
    await expect(module.resetDisplayWidgetSession(widgetPayload)).resolves.toMatchObject({
      action: 'reset_display_widget_session',
      supported: true,
    });
    await expect(module.playDisplayWidgetVideo({ uri: 'ipfs://bafybeivideo' }, widgetPayload)).resolves.toMatchObject({
      action: 'play_display_widget_video',
      supported: true,
    });
    await expect(module.subscribeDisplayWidgetUpdates({ stream: 'display_widget_update' }, widgetPayload)).resolves.toMatchObject({
      action: 'subscribe_display_widget_updates',
      supported: true,
    });
    expect(nativeModule.renderDisplayWidget).toHaveBeenCalledWith(manifest, expect.objectContaining({
      descriptor_cid: 'bafybeidescriptor',
      manifest: expect.objectContaining({
        viewport: { width: 600, height: 600 },
        regions: expect.arrayContaining([
          expect.objectContaining({ id: 'title', kind: 'text' }),
          expect.objectContaining({ id: 'pause-control', action_id: 'pause' }),
          expect.objectContaining({ id: 'preview', media_id: 'preview-media' }),
        ]),
        focus_order: ['pause'],
        actions: expect.arrayContaining([
          expect.objectContaining({ id: 'pause', label: 'Pause' }),
        ]),
        media: expect.arrayContaining([
          expect.objectContaining({
            id: 'preview-media',
            type: 'video/mp4',
            fallback_text: 'Video preview opens on phone.',
          }),
        ]),
      }),
    }));
    expect(nativeModule.updateDisplayWidget).toHaveBeenCalledWith(patch, expect.objectContaining({
      descriptor_cid: 'bafybeidescriptor',
      patch,
    }));
    expect(nativeModule.clearDisplayWidget).toHaveBeenCalledWith('handsfree.task-progress-widget', expect.objectContaining({
      widget_id: 'handsfree.task-progress-widget',
      widget_cid: 'bafybeiwidget',
    }));
    expect(nativeModule.focusDisplayWidget).toHaveBeenCalledWith('next', expect.objectContaining({
      focus: { direction: 'next' },
      orb_receipt_cid: 'bafybeireceipt',
    }));
    expect(nativeModule.activateDisplayWidgetAction).toHaveBeenCalledWith('primary', expect.objectContaining({
      activated_action_id: 'primary',
      request_id: 'req-widget',
    }));
    expect(nativeModule.resetDisplayWidgetSession).toHaveBeenCalledWith(expect.objectContaining({
      descriptor_cid: 'bafybeidescriptor',
    }));
    expect(nativeModule.playDisplayWidgetVideo).toHaveBeenCalledWith(
      { uri: 'ipfs://bafybeivideo' },
      expect.objectContaining({
        video: { uri: 'ipfs://bafybeivideo' },
        correlation_id: 'corr-widget',
      })
    );
    expect(nativeModule.subscribeDisplayWidgetUpdates).toHaveBeenCalledWith(
      { stream: 'display_widget_update' },
      expect.objectContaining({
        subscription: { stream: 'display_widget_update' },
        policy_decision: { outcome: 'permit' },
      })
    );
  });

  test('preserves explicit iOS SDK-unlinked display widget responses', async () => {
    const sdkUnlinkedResult = (action, operation) => ({
      state: 'not_supported',
      mode: 'reference_only',
      supported: false,
      action,
      operation,
      reason: 'dat_sdk_unlinked',
      message: 'DAT SDK classes are not linked into this iOS build.',
      renderPath: 'mobile-card',
      requiredAction: null,
      displayConnectionState: 'sdk_unlinked',
      displayLastAction: action,
      displayLastStatus: 'blocked',
      displayRenderPath: 'mobile-card',
      displayLastError: 'dat_sdk_unlinked',
      displayLifecycleStages: ['sdk_unlinked'],
      widgetId: 'handsfree.task-progress-widget',
      descriptorCid: 'bafybeidescriptor',
      orbReceiptCid: 'bafybeireceipt',
      fallback: {
        reason: 'dat_sdk_unlinked',
        renderPath: 'mobile-card',
        message: 'DAT SDK classes are not linked into this iOS build.',
      },
    });
    const nativeModule = {
      getConfiguration: jest.fn(async () => ({
        platform: 'ios',
        sdkLinked: false,
        sdkConfigured: false,
        analyticsOptOut: false,
        displaySdkLinked: false,
        integrationMode: 'reference_only',
      })),
      getDiagnostics: jest.fn(async () => ({
        available: true,
        platform: 'ios',
        sdkLinked: false,
        sdkConfigured: false,
        analyticsOptOut: false,
        displaySdkLinked: false,
        displayReady: false,
        configWarnings: ['DAT SDK classes are not linked into this iOS build.'],
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
        displayConnectionState: 'idle',
        displayLastError: null,
        displayLifecycleStages: [],
      })),
      renderDisplayWidget: jest.fn(async () => sdkUnlinkedResult('render_display_widget', 'render_widget')),
      updateDisplayWidget: jest.fn(async () => sdkUnlinkedResult('update_display_widget', 'update_widget')),
      clearDisplayWidget: jest.fn(async () => sdkUnlinkedResult('clear_display_widget', 'clear_widget')),
      focusDisplayWidget: jest.fn(async () => sdkUnlinkedResult('focus_display_widget', 'focus_next')),
      activateDisplayWidgetAction: jest.fn(async () => sdkUnlinkedResult('activate_display_widget_action', 'activate')),
      resetDisplayWidgetSession: jest.fn(async () => sdkUnlinkedResult('reset_display_widget_session', 'reset_session')),
    };

    const { requireOptionalNativeModule } = require('expo-modules-core');
    requireOptionalNativeModule.mockReturnValue(nativeModule);

    const module = require('..').default;
    const payload = {
      descriptor_cid: 'bafybeidescriptor',
      widget_id: 'handsfree.task-progress-widget',
      orb_receipt_cid: 'bafybeireceipt',
    };

    await expect(module.getConfiguration()).resolves.toMatchObject({
      platform: 'ios',
      sdkLinked: false,
      displaySdkLinked: false,
      integrationMode: 'reference_only',
    });
    await expect(module.getDiagnostics()).resolves.toMatchObject({
      sdkLinked: false,
      displaySdkLinked: false,
      displayReady: false,
      configWarnings: expect.arrayContaining(['DAT SDK classes are not linked into this iOS build.']),
    });
    await expect(module.renderDisplayWidget({ id: 'handsfree.task-progress-widget' }, payload)).resolves.toMatchObject({
      action: 'render_display_widget',
      supported: false,
      reason: 'dat_sdk_unlinked',
      renderPath: 'mobile-card',
      displayConnectionState: 'sdk_unlinked',
      displayLastError: 'dat_sdk_unlinked',
      fallback: expect.objectContaining({
        reason: 'dat_sdk_unlinked',
      }),
    });
    await expect(module.updateDisplayWidget({ widget_id: 'handsfree.task-progress-widget' }, payload)).resolves.toMatchObject({
      action: 'update_display_widget',
      supported: false,
      reason: 'dat_sdk_unlinked',
    });
    await expect(module.clearDisplayWidget('handsfree.task-progress-widget', payload)).resolves.toMatchObject({
      action: 'clear_display_widget',
      supported: false,
      reason: 'dat_sdk_unlinked',
    });
    await expect(module.focusDisplayWidget('next', payload)).resolves.toMatchObject({
      action: 'focus_display_widget',
      supported: false,
      reason: 'dat_sdk_unlinked',
    });
    await expect(module.activateDisplayWidgetAction('primary', payload)).resolves.toMatchObject({
      action: 'activate_display_widget_action',
      supported: false,
      reason: 'dat_sdk_unlinked',
    });
    await expect(module.resetDisplayWidgetSession(payload)).resolves.toMatchObject({
      action: 'reset_display_widget_session',
      supported: false,
      reason: 'dat_sdk_unlinked',
    });
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
