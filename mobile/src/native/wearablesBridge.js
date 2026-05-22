const DISPLAY_WIDGET_FALLBACK = {
  reason: 'dat_native_display_unavailable',
  renderPath: 'mobile-card',
  message: 'DAT native display is unavailable. Showing display widget content on phone.',
};

const DISPLAY_WIDGET_ACTIONS = {
  renderDisplayWidget: {
    action: 'render_display_widget',
    operation: 'render_widget',
    message: 'Meta Wearables DAT display widget rendering is unavailable in this build.',
  },
  updateDisplayWidget: {
    action: 'update_display_widget',
    operation: 'update_widget',
    message: 'Meta Wearables DAT display widget updates are unavailable in this build.',
  },
  clearDisplayWidget: {
    action: 'clear_display_widget',
    operation: 'clear_widget',
    message: 'Meta Wearables DAT display widget clearing is unavailable in this build.',
  },
  focusDisplayWidget: {
    action: 'focus_display_widget',
    operation: 'focus_next',
    message: 'Meta Wearables DAT display widget focus is unavailable in this build.',
  },
  activateDisplayWidgetAction: {
    action: 'activate_display_widget_action',
    operation: 'activate',
    message: 'Meta Wearables DAT display widget actions are unavailable in this build.',
  },
  resetDisplayWidgetSession: {
    action: 'reset_display_widget_session',
    operation: 'reset_session',
    message: 'Meta Wearables DAT display widget session reset is unavailable in this build.',
  },
  playDisplayWidgetVideo: {
    action: 'play_display_widget_video',
    operation: 'play_video',
    message: 'Meta Wearables DAT display widget video playback is unavailable in this build.',
  },
  subscribeDisplayWidgetUpdates: {
    action: 'subscribe_display_widget_updates',
    operation: 'subscribe_updates',
    message: 'Meta Wearables DAT display widget update subscriptions are unavailable in this build.',
  },
};

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function getDisplayWidgetPayload(input, context) {
  if (isObject(context?.display_widget_action)) {
    return context.display_widget_action;
  }
  if (isObject(context?.mobile_payload)) {
    return context.mobile_payload;
  }
  if (isObject(context)) {
    return context;
  }
  if (isObject(input?.display_widget_action)) {
    return input.display_widget_action;
  }
  if (isObject(input?.mobile_payload)) {
    return input.mobile_payload;
  }
  return isObject(input) ? input : {};
}

function getManifestObject(input, payload) {
  if (isObject(payload?.manifest)) {
    return payload.manifest;
  }
  return isObject(input) ? input : {};
}

function getDisplayWidgetMetadata(input, context = {}) {
  const payload = getDisplayWidgetPayload(input, context);
  const manifest = getManifestObject(input, payload);
  const fallback = isObject(payload.fallback) ? payload.fallback : DISPLAY_WIDGET_FALLBACK;

  return {
    contract: payload.contract || null,
    type: payload.type || null,
    operation: payload.operation || null,
    descriptorCid: payload.descriptor_cid || payload.descriptorCid || null,
    interfaceCid: payload.interface_cid || payload.interfaceCid || null,
    widgetId: payload.widget_id || payload.widgetId || manifest.widget_id || manifest.widgetId || manifest.id || null,
    widgetCid: payload.widget_cid || payload.widgetCid || manifest.widget_cid || manifest.widgetCid || manifest.cid || null,
    orbReceiptCid: payload.orb_receipt_cid || payload.orbReceiptCid || payload.receipt_cid || payload.receiptCid || null,
    policyDecision: payload.policy_decision || payload.policyDecision || null,
    correlationId: payload.correlation_id || payload.correlationId || null,
    requestId: payload.request_id || payload.requestId || null,
    issuedAt: payload.issued_at || payload.issuedAt || null,
    fallback,
  };
}

function getDisplayWidgetVideoUri(input, context = {}) {
  const payload = getDisplayWidgetPayload(input, context);
  const video = isObject(input) ? input : payload?.video;
  return (
    video?.uri ||
    video?.url ||
    video?.video_url ||
    video?.videoUrl ||
    payload?.video?.uri ||
    payload?.video_url ||
    payload?.videoUrl ||
    null
  );
}

function createUnavailableMediaResult(action, message) {
  return {
    state: 'unavailable',
    mode: 'unavailable',
    supported: false,
    action,
    message,
    targetConnectionState: 'unselected',
    deviceId: null,
    assetUri: null,
    mimeType: null,
    displayConnectionState: 'unavailable',
    displayLastAction: action,
    displayLastStatus: 'unavailable',
    displayLastUpdatedAt: Date.now(),
  };
}

function createUnsupportedDisplayWidgetResult(config, input, context = {}) {
  const metadata = getDisplayWidgetMetadata(input, context);
  const fallback = metadata.fallback || DISPLAY_WIDGET_FALLBACK;

  return {
    state: 'unavailable',
    mode: 'unavailable',
    supported: false,
    action: config.action,
    operation: metadata.operation || config.operation,
    reason: fallback.reason || DISPLAY_WIDGET_FALLBACK.reason,
    message: fallback.message || config.message,
    renderPath: fallback.renderPath || DISPLAY_WIDGET_FALLBACK.renderPath,
    targetConnectionState: 'unselected',
    deviceId: null,
    assetUri: null,
    mimeType: null,
    displayConnectionState: 'unavailable',
    displayLastAction: config.action,
    displayLastStatus: 'unsupported',
    displayLastUpdatedAt: Date.now(),
    contract: metadata.contract,
    type: metadata.type,
    descriptorCid: metadata.descriptorCid,
    interfaceCid: metadata.interfaceCid,
    widgetId: metadata.widgetId,
    widgetCid: metadata.widgetCid,
    orbReceiptCid: metadata.orbReceiptCid,
    policyDecision: metadata.policyDecision,
    correlationId: metadata.correlationId,
    requestId: metadata.requestId,
    issuedAt: metadata.issuedAt,
    fallback,
  };
}

function normalizeDisplayWidgetResult(response, config, input, context = {}) {
  const fallbackResult = createUnsupportedDisplayWidgetResult(config, input, context);
  const nativeResponse = isObject(response) ? response : {};
  const supported = nativeResponse.supported ?? fallbackResult.supported;

  return {
    ...fallbackResult,
    ...nativeResponse,
    supported,
    action: config.action,
    operation: nativeResponse.operation || fallbackResult.operation,
    reason: nativeResponse.reason ?? (supported ? null : fallbackResult.reason),
    message: nativeResponse.message || fallbackResult.message,
    renderPath: nativeResponse.renderPath || (supported ? 'native-dat' : fallbackResult.renderPath),
    displayLastAction: nativeResponse.displayLastAction || config.action,
    displayLastStatus: nativeResponse.displayLastStatus || (supported ? 'sent' : fallbackResult.displayLastStatus),
    fallback: nativeResponse.fallback ?? (supported ? null : fallbackResult.fallback),
  };
}

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
        display: false,
        displayVideo: false,
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
    capturePhoto: async () => createUnavailableMediaResult(
      'capture_photo',
      'Meta Wearables DAT photo capture is unavailable in this build.'
    ),
    startVideoStream: async () => createUnavailableMediaResult(
      'start_video_stream',
      'Meta Wearables DAT video streaming is unavailable in this build.'
    ),
    stopVideoStream: async () => createUnavailableMediaResult(
      'stop_video_stream',
      'Meta Wearables DAT video streaming is unavailable in this build.'
    ),
    renderDisplayTest: async () => createUnavailableMediaResult(
      'render_display_test',
      'Meta Wearables DAT display rendering is unavailable in this build.'
    ),
    clearDisplay: async () => createUnavailableMediaResult(
      'clear_display',
      'Meta Wearables DAT display clearing is unavailable in this build.'
    ),
    playDisplayVideo: async () => createUnavailableMediaResult(
      'play_display_video',
      'Meta Wearables DAT display video playback is unavailable in this build.'
    ),
    resetDisplaySession: async () => createUnavailableMediaResult(
      'reset_display_session',
      'Meta Wearables DAT display session reset is unavailable in this build.'
    ),
    renderDisplayWidget: async (manifest, context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.renderDisplayWidget,
      manifest,
      context
    ),
    updateDisplayWidget: async (patch, context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.updateDisplayWidget,
      patch,
      context
    ),
    clearDisplayWidget: async (widgetId, context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.clearDisplayWidget,
      { widget_id: widgetId },
      context
    ),
    focusDisplayWidget: async (direction, context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.focusDisplayWidget,
      {
        focus: { direction },
        operation: direction === 'previous' ? 'focus_previous' : 'focus_next',
      },
      context
    ),
    activateDisplayWidgetAction: async (actionId, context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.activateDisplayWidgetAction,
      { activated_action_id: actionId },
      context
    ),
    resetDisplayWidgetSession: async (context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.resetDisplayWidgetSession,
      context,
      context
    ),
    playDisplayWidgetVideo: async (video, context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.playDisplayWidgetVideo,
      isObject(video) ? video : { uri: video },
      context
    ),
    subscribeDisplayWidgetUpdates: async (subscription, context) => createUnsupportedDisplayWidgetResult(
      DISPLAY_WIDGET_ACTIONS.subscribeDisplayWidgetUpdates,
      isObject(subscription) ? subscription : {},
      context
    ),
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
    capturePhoto: async () => await module.capturePhoto(),
    startVideoStream: async () => await module.startVideoStream(),
    stopVideoStream: async () => await module.stopVideoStream(),
    renderDisplayTest: async () => await module.renderDisplayTest(),
    clearDisplay: async () => await module.clearDisplay(),
    playDisplayVideo: async (videoUrl) => await module.playDisplayVideo(videoUrl),
    resetDisplaySession: async () => await module.resetDisplaySession(),
    renderDisplayWidget: async (manifest, context) => {
      if (typeof module.renderDisplayWidget === 'function') {
        return normalizeDisplayWidgetResult(
          await module.renderDisplayWidget(manifest),
          DISPLAY_WIDGET_ACTIONS.renderDisplayWidget,
          manifest,
          context
        );
      }
      if (typeof module.renderDisplayTest === 'function') {
        return normalizeDisplayWidgetResult(
          await module.renderDisplayTest(),
          DISPLAY_WIDGET_ACTIONS.renderDisplayWidget,
          manifest,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(DISPLAY_WIDGET_ACTIONS.renderDisplayWidget, manifest, context);
    },
    updateDisplayWidget: async (patch, context) => {
      if (typeof module.updateDisplayWidget === 'function') {
        return normalizeDisplayWidgetResult(
          await module.updateDisplayWidget(patch),
          DISPLAY_WIDGET_ACTIONS.updateDisplayWidget,
          patch,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(DISPLAY_WIDGET_ACTIONS.updateDisplayWidget, patch, context);
    },
    clearDisplayWidget: async (widgetId, context) => {
      const input = { widget_id: widgetId };
      if (typeof module.clearDisplayWidget === 'function') {
        return normalizeDisplayWidgetResult(
          await module.clearDisplayWidget(widgetId),
          DISPLAY_WIDGET_ACTIONS.clearDisplayWidget,
          input,
          context
        );
      }
      if (typeof module.clearDisplay === 'function') {
        return normalizeDisplayWidgetResult(
          await module.clearDisplay(),
          DISPLAY_WIDGET_ACTIONS.clearDisplayWidget,
          input,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(DISPLAY_WIDGET_ACTIONS.clearDisplayWidget, input, context);
    },
    focusDisplayWidget: async (direction, context) => {
      const input = {
        focus: { direction },
        operation: direction === 'previous' ? 'focus_previous' : 'focus_next',
      };
      if (typeof module.focusDisplayWidget === 'function') {
        return normalizeDisplayWidgetResult(
          await module.focusDisplayWidget(direction),
          DISPLAY_WIDGET_ACTIONS.focusDisplayWidget,
          input,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(DISPLAY_WIDGET_ACTIONS.focusDisplayWidget, input, context);
    },
    activateDisplayWidgetAction: async (actionId, context) => {
      const input = { activated_action_id: actionId };
      if (typeof module.activateDisplayWidgetAction === 'function') {
        return normalizeDisplayWidgetResult(
          await module.activateDisplayWidgetAction(actionId),
          DISPLAY_WIDGET_ACTIONS.activateDisplayWidgetAction,
          input,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(DISPLAY_WIDGET_ACTIONS.activateDisplayWidgetAction, input, context);
    },
    resetDisplayWidgetSession: async (context) => {
      if (typeof module.resetDisplayWidgetSession === 'function') {
        return normalizeDisplayWidgetResult(
          await module.resetDisplayWidgetSession(),
          DISPLAY_WIDGET_ACTIONS.resetDisplayWidgetSession,
          context,
          context
        );
      }
      if (typeof module.resetDisplaySession === 'function') {
        return normalizeDisplayWidgetResult(
          await module.resetDisplaySession(),
          DISPLAY_WIDGET_ACTIONS.resetDisplayWidgetSession,
          context,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(DISPLAY_WIDGET_ACTIONS.resetDisplayWidgetSession, context, context);
    },
    playDisplayWidgetVideo: async (video, context) => {
      const input = isObject(video) ? video : { uri: video };
      if (typeof module.playDisplayWidgetVideo === 'function') {
        return normalizeDisplayWidgetResult(
          await module.playDisplayWidgetVideo(video),
          DISPLAY_WIDGET_ACTIONS.playDisplayWidgetVideo,
          input,
          context
        );
      }
      if (typeof module.playDisplayVideo === 'function') {
        return normalizeDisplayWidgetResult(
          await module.playDisplayVideo(getDisplayWidgetVideoUri(input, context)),
          DISPLAY_WIDGET_ACTIONS.playDisplayWidgetVideo,
          input,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(DISPLAY_WIDGET_ACTIONS.playDisplayWidgetVideo, input, context);
    },
    subscribeDisplayWidgetUpdates: async (subscription, context) => {
      const input = isObject(subscription) ? subscription : {};
      if (typeof module.subscribeDisplayWidgetUpdates === 'function') {
        return normalizeDisplayWidgetResult(
          await module.subscribeDisplayWidgetUpdates(subscription),
          DISPLAY_WIDGET_ACTIONS.subscribeDisplayWidgetUpdates,
          input,
          context
        );
      }
      return createUnsupportedDisplayWidgetResult(
        DISPLAY_WIDGET_ACTIONS.subscribeDisplayWidgetUpdates,
        input,
        context
      );
    },
    addStateListener: (...args) => module.addStateListener?.(...args) || { remove() {} },
    addBridgeStateListener: (...args) => module.addStateListener?.(...args) || { remove() {} },
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
