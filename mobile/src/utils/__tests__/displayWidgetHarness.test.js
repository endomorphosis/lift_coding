jest.mock('../../native/metaWearablesDat', () => ({
  getMetaWearablesDat: jest.fn(),
}));

import fs from 'node:fs';
import path from 'node:path';
import { executeLocalStructuredAction } from '../agentActions';
import {
  DISPLAY_WIDGET_ACTION_BY_ACTION_ID,
  DISPLAY_WIDGET_ACTION_CONTRACT,
  DISPLAY_WIDGET_ACTION_IDS,
  DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID,
} from '../metaWearablesDatDisplayWidgetContract';
import { DAT_DISPLAY_STATES } from '../../native/__fixtures__/metaWearablesDisplayStates';
import { getMetaWearablesDat } from '../../native/metaWearablesDat';

const SPEC_PATH = path.resolve(
  __dirname,
  '../../../../spec/meta_glasses_display_widget_orb_interface.json'
);

const MANIFEST = {
  schema: 'handsfree.meta-glasses/widget-manifest',
  schema_version: '0.1.0',
  widget_id: 'task-progress-active',
  widget_cid: 'sha256:widget',
  interface_cid: 'sha256:descriptor',
  operation: 'render_widget',
  media: [
    {
      id: 'preview',
      type: 'video/mp4',
      transport: 'https',
      duration_ms: 1200,
      size_bytes: 1024,
      fallback_text: 'Video preview unavailable',
    },
  ],
  state: {
    values: {
      title: 'Sync dataset',
      progress: 0.42,
      progress_label: '42% complete',
      status: 'running',
    },
  },
  fallback: {
    render_path: 'mobile-card',
    message: 'Display unavailable. Showing task progress on phone.',
  },
};

const ACTION_RECEIPTS = {
  mobile_render_display_widget: 'sha256:render-receipt',
  mobile_update_display_widget: 'sha256:update-receipt',
  mobile_clear_display_widget: 'sha256:clear-receipt',
  mobile_focus_display_widget: 'sha256:focus-receipt',
  mobile_activate_display_widget_action: 'sha256:activate-receipt',
  mobile_reset_display_widget_session: 'sha256:reset-receipt',
  mobile_play_display_widget_video: 'sha256:video-receipt',
  mobile_subscribe_display_widget_updates: 'sha256:subscribe-receipt',
};

function mobilePayload(type, overrides = {}) {
  const action = DISPLAY_WIDGET_ACTION_BY_ACTION_ID[type];
  const operation = DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[type];
  return {
    contract: DISPLAY_WIDGET_ACTION_CONTRACT,
    type,
    action,
    operation: overrides.operation || operation,
    descriptor_cid: 'sha256:descriptor',
    interface_cid: 'sha256:descriptor',
    widget_id: 'task-progress-active',
    widget_cid: 'sha256:widget',
    orb_receipt_cid: overrides.orb_receipt_cid || ACTION_RECEIPTS[type],
    policy_decision: {
      outcome: 'permit',
      reasons: ['Required capabilities granted.'],
    },
    correlation_id: overrides.correlation_id || `corr-${action}`,
    request_id: overrides.request_id || `${operation}-1`,
    issued_at: '2026-05-22T12:00:00Z',
    fallback: MANIFEST.fallback,
    ...overrides,
  };
}

function actionItem(type, payload) {
  return {
    id: type,
    label: type,
    phrase: type,
    params: {
      display_widget_action: payload,
    },
    mobile_payload: payload,
  };
}

function fallbackFrom(state, payload) {
  const fallback = state.fallback || payload.fallback || MANIFEST.fallback;
  return {
    ...fallback,
    reason: fallback.reason || 'dat_native_display_unavailable',
    renderPath: fallback.renderPath || fallback.render_path || 'mobile-card',
    message: fallback.message || 'Display unavailable. Showing content on phone.',
    requiredAction:
      fallback.requiredAction === undefined ? state.requiredAction || null : fallback.requiredAction,
  };
}

function createMockDisplayBridge(state = DAT_DISPLAY_STATES.unavailable) {
  const diagnostics = {
    fixtureId: state.id,
    activeWidgetId: null,
    widgetCid: null,
    displayLastAction: null,
    displayLastStatus: null,
    displayLastUpdatedAt: null,
    displayRenderPath: state.displayReady ? 'native-dat' : fallbackFrom(state, {}).renderPath,
    displayLastError: state.displayLastError || null,
    displayFallback: state.fallback || null,
    displayLifecycleStages: state.displayLifecycleStages || [],
    requiredAction: state.requiredAction || null,
    renderCount: 0,
    updateCount: 0,
    clearCount: 0,
    focusCount: 0,
    activateCount: 0,
    resetCount: 0,
    videoCount: 0,
    subscriptionCount: 0,
    receiptCids: [],
    events: [],
  };
  const calls = [];
  const supported = Boolean(state.displayReady && !state.fallback);

  const record = (payload, result) => {
    diagnostics.displayLastAction = result.action;
    diagnostics.displayLastStatus = result.displayLastStatus;
    diagnostics.displayLastUpdatedAt = result.displayLastUpdatedAt;
    diagnostics.displayRenderPath = result.renderPath;
    diagnostics.displayLastError = result.displayLastError;
    diagnostics.displayFallback = result.fallback;
    diagnostics.requiredAction = result.requiredAction || null;
    diagnostics.widgetCid = payload.widget_cid || diagnostics.widgetCid;
    diagnostics.receiptCids.push(payload.orb_receipt_cid);
    diagnostics.events.push({
      action: result.action,
      operation: result.operation,
      receiptCid: payload.orb_receipt_cid,
      correlationId: payload.correlation_id,
      fallbackReason: result.fallback?.reason || null,
      lifecycleStages: result.displayLifecycleStages || [],
    });
    calls.push({ payload, result });
    return result;
  };

  const resultFor = (action, operation, payload, extra = {}) => {
    const fallback = supported ? null : fallbackFrom(state, payload);
    const status = extra.displayLastStatus || (supported ? extra.nativeStatus || 'sent' : state.displayLastStatus || 'unsupported');
    return {
      action,
      operation,
      supported,
      message: supported ? `Widget ${operation} handled by mocked native bridge.` : fallback.message,
      renderPath: supported ? 'native-dat' : fallback.renderPath,
      reason: supported ? null : fallback.reason,
      requiredAction: supported ? null : fallback.requiredAction,
      fallback,
      widgetId: payload.widget_id,
      widgetCid: payload.widget_cid,
      orbReceiptCid: payload.orb_receipt_cid,
      correlationId: payload.correlation_id,
      displayLastAction: action,
      displayLastStatus: status,
      displayLastUpdatedAt: extra.updatedAt || 1779440401000 + diagnostics.events.length,
      displayRenderPath: supported ? 'native-dat' : fallback.renderPath,
      displayLastError: supported ? null : state.displayLastError || fallback.reason,
      displayLifecycleStages: state.displayLifecycleStages || [],
      ...extra,
    };
  };

  return {
    calls,
    diagnostics,
    renderDisplayWidget: jest.fn(async (manifest, payload) => {
      diagnostics.activeWidgetId = manifest.widget_id;
      diagnostics.renderCount += 1;
      return record(payload, resultFor('render_display_widget', 'render_widget', payload, {
        widgetId: manifest.widget_id,
        widgetCid: manifest.widget_cid,
        nativeStatus: 'rendered',
      }));
    }),
    updateDisplayWidget: jest.fn(async (patch, payload) => {
      diagnostics.updateCount += 1;
      return record(payload, resultFor('update_display_widget', 'update_widget', payload, {
        patch,
        nativeStatus: 'updated',
      }));
    }),
    clearDisplayWidget: jest.fn(async (widgetId, payload) => {
      diagnostics.activeWidgetId = null;
      diagnostics.clearCount += 1;
      return record(payload, resultFor('clear_display_widget', 'clear_widget', payload, {
        widgetId,
        nativeStatus: 'cleared',
      }));
    }),
    focusDisplayWidget: jest.fn(async (direction, payload) => {
      diagnostics.focusCount += 1;
      return record(payload, resultFor('focus_display_widget', payload.operation, payload, {
        focus: { direction, ...(payload.focus || {}) },
        nativeStatus: 'focused',
      }));
    }),
    activateDisplayWidgetAction: jest.fn(async (actionId, payload) => {
      diagnostics.activateCount += 1;
      return record(payload, resultFor('activate_display_widget_action', 'activate', payload, {
        activatedActionId: actionId,
        nativeStatus: 'activated',
      }));
    }),
    resetDisplayWidgetSession: jest.fn(async (payload) => {
      diagnostics.activeWidgetId = payload.widget_id;
      diagnostics.resetCount += 1;
      return record(payload, resultFor('reset_display_widget_session', 'reset_session', payload, {
        sessionGeneration: diagnostics.resetCount,
        nativeStatus: 'reset',
      }));
    }),
    playDisplayWidgetVideo: jest.fn(async (video, payload) => {
      diagnostics.videoCount += 1;
      return record(payload, resultFor('play_display_widget_video', 'play_video', payload, {
        video,
        nativeStatus: 'video',
      }));
    }),
    subscribeDisplayWidgetUpdates: jest.fn(async (subscription, payload) => {
      diagnostics.subscriptionCount += 1;
      return record(payload, resultFor('subscribe_display_widget_updates', 'subscribe_updates', payload, {
        subscription,
        nativeStatus: 'subscribed',
      }));
    }),
  };
}

async function execute(type, overrides, navigation) {
  const payload = mobilePayload(type, overrides);
  return executeLocalStructuredAction({
    actionItem: actionItem(type, payload),
    navigation,
  });
}

describe('display widget hardware-free mobile harness', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('keeps the mobile display widget contract aligned with the descriptor artifact', () => {
    const descriptor = JSON.parse(fs.readFileSync(SPEC_PATH, 'utf8'));

    expect(descriptor.name).toBe('display_widget_bridge');
    expect(descriptor.namespace).toBe('handsfree.meta_glasses.display');
    expect(descriptor.version).toBe('0.1.0');
    expect(descriptor.methods.map((method) => method.name)).toEqual(
      DISPLAY_WIDGET_ACTION_IDS.map(
        (actionId) => DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionId]
      )
    );
  });

  it('executes backend display widget lifecycle actions through a mocked fallback bridge', async () => {
    const navigate = jest.fn();
    const dat = createMockDisplayBridge(DAT_DISPLAY_STATES.unavailable);
    getMetaWearablesDat.mockResolvedValue(dat);

    const video = {
      media_id: 'preview',
      uri: 'https://example.test/clip.mp4',
      content_type: 'video/mp4',
      duration_ms: 1200,
    };
    const subscription = { stream: 'display_widget_update' };
    const rendered = await execute('mobile_render_display_widget', {
      operation: 'render_widget',
      correlation_id: 'corr-render',
      manifest: MANIFEST,
      state: MANIFEST.state.values,
    }, { navigate });
    const updated = await execute('mobile_update_display_widget', {
      operation: 'update_widget',
      correlation_id: 'corr-update',
      request_id: 'update-1',
      patch: { progress: 0.43, progress_label: '43% complete' },
    }, { navigate });
    const focused = await execute('mobile_focus_display_widget', {
      operation: 'focus_next',
      correlation_id: 'corr-focus',
      focus: { direction: 'next', action_id: 'dismiss', focus_index: 1 },
    }, { navigate });
    const activated = await execute('mobile_activate_display_widget_action', {
      correlation_id: 'corr-activate',
      activated_action_id: 'pause',
    }, { navigate });
    const videoStarted = await execute('mobile_play_display_widget_video', {
      correlation_id: 'corr-video',
      video,
    }, { navigate });
    const subscribed = await execute('mobile_subscribe_display_widget_updates', {
      correlation_id: 'corr-subscribe',
      subscription,
    }, { navigate });
    const reset = await execute('mobile_reset_display_widget_session', {
      correlation_id: 'corr-reset',
    }, { navigate });
    const cleared = await execute('mobile_clear_display_widget', {
      operation: 'clear_widget',
      correlation_id: 'corr-clear',
    }, { navigate });

    expect(rendered).toMatchObject({
      handled: true,
      response: {
        action: 'render_display_widget',
        operation: 'render_widget',
        supported: false,
        reason: 'dat_native_display_unavailable',
        renderPath: 'mobile-card',
        widgetId: 'task-progress-active',
        orbReceiptCid: 'sha256:render-receipt',
      },
    });
    expect(updated.response.patch).toEqual({ progress: 0.43, progress_label: '43% complete' });
    expect(focused.response.focus).toEqual({
      direction: 'next',
      action_id: 'dismiss',
      focus_index: 1,
    });
    expect(activated.response.activatedActionId).toBe('pause');
    expect(videoStarted.response.video).toEqual(video);
    expect(subscribed.response.subscription).toEqual(subscription);
    expect(reset.response.sessionGeneration).toBe(1);
    expect(cleared.response).toMatchObject({
      action: 'clear_display_widget',
      operation: 'clear_widget',
      widgetId: 'task-progress-active',
      orbReceiptCid: 'sha256:clear-receipt',
    });
    expect(dat.focusDisplayWidget).toHaveBeenCalledWith('next', expect.objectContaining({
      focus: { direction: 'next', action_id: 'dismiss', focus_index: 1 },
      orb_receipt_cid: 'sha256:focus-receipt',
    }));
    expect(dat.activateDisplayWidgetAction).toHaveBeenCalledWith('pause', expect.objectContaining({
      correlation_id: 'corr-activate',
    }));
    expect(dat.playDisplayWidgetVideo).toHaveBeenCalledWith(video, expect.objectContaining({
      video,
      type: 'mobile_play_display_widget_video',
    }));
    expect(dat.subscribeDisplayWidgetUpdates).toHaveBeenCalledWith(subscription, expect.objectContaining({
      subscription,
      type: 'mobile_subscribe_display_widget_updates',
    }));
    expect(dat.diagnostics).toMatchObject({
      activeWidgetId: null,
      widgetCid: 'sha256:widget',
      displayLastAction: 'clear_display_widget',
      displayLastStatus: 'unsupported',
      displayRenderPath: 'mobile-card',
      displayLastError: 'dat_native_display_unavailable',
      displayFallback: expect.objectContaining({
        reason: 'dat_native_display_unavailable',
        renderPath: 'mobile-card',
      }),
      renderCount: 1,
      updateCount: 1,
      clearCount: 1,
      focusCount: 1,
      activateCount: 1,
      resetCount: 1,
      videoCount: 1,
      subscriptionCount: 1,
      receiptCids: [
        'sha256:render-receipt',
        'sha256:update-receipt',
        'sha256:focus-receipt',
        'sha256:activate-receipt',
        'sha256:video-receipt',
        'sha256:subscribe-receipt',
        'sha256:reset-receipt',
        'sha256:clear-receipt',
      ],
    });
    expect(dat.diagnostics.events).toEqual([
      expect.objectContaining({ action: 'render_display_widget', correlationId: 'corr-render' }),
      expect.objectContaining({ action: 'update_display_widget', correlationId: 'corr-update' }),
      expect.objectContaining({ action: 'focus_display_widget', correlationId: 'corr-focus' }),
      expect.objectContaining({ action: 'activate_display_widget_action', correlationId: 'corr-activate' }),
      expect.objectContaining({ action: 'play_display_widget_video', correlationId: 'corr-video' }),
      expect.objectContaining({ action: 'subscribe_display_widget_updates', correlationId: 'corr-subscribe' }),
      expect.objectContaining({ action: 'reset_display_widget_session', correlationId: 'corr-reset' }),
      expect.objectContaining({ action: 'clear_display_widget', correlationId: 'corr-clear' }),
    ]);
    expect(navigate).toHaveBeenCalledTimes(8);
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it.each([
    ['native unavailable', DAT_DISPLAY_STATES.unavailable, 'dat_native_display_unavailable', null],
    ['firmware update required', DAT_DISPLAY_STATES.firmwareUpdateRequired, 'firmware_update_required', 'open_firmware_update'],
    ['DAT glasses app update required', DAT_DISPLAY_STATES.datAppUpdateRequired, 'dat_app_update_required', 'open_dat_glasses_app_update'],
    ['lifecycle error', DAT_DISPLAY_STATES.lifecycleError, 'display_lifecycle_error', null],
  ])('records %s fallback diagnostics without paired glasses', async (_label, fixtureState, reason, requiredAction) => {
    const navigate = jest.fn();
    const dat = createMockDisplayBridge(fixtureState);
    getMetaWearablesDat.mockResolvedValue(dat);

    const rendered = await execute('mobile_render_display_widget', {
      operation: 'render_widget',
      correlation_id: `corr-${fixtureState.id}`,
      manifest: MANIFEST,
      state: MANIFEST.state.values,
    }, { navigate });

    expect(rendered).toMatchObject({
      handled: true,
      response: {
        action: 'render_display_widget',
        supported: false,
        reason,
        requiredAction,
        fallback: expect.objectContaining({
          reason,
          renderPath: 'mobile-card',
        }),
        displayLifecycleStages: fixtureState.displayLifecycleStages || [],
      },
    });
    expect(dat.diagnostics).toMatchObject({
      fixtureId: fixtureState.id,
      displayLastAction: 'render_display_widget',
      displayLastError: reason,
      displayRenderPath: 'mobile-card',
      requiredAction,
      displayFallback: expect.objectContaining({
        reason,
        renderPath: 'mobile-card',
      }),
    });
    expect(dat.diagnostics.events[0]).toEqual(expect.objectContaining({
      action: 'render_display_widget',
      receiptCid: 'sha256:render-receipt',
      fallbackReason: reason,
      lifecycleStages: fixtureState.displayLifecycleStages || [],
    }));
  });
});
