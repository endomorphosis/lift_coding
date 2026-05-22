jest.mock('../../native/metaWearablesDat', () => ({
  getMetaWearablesDat: jest.fn(),
}));

import { executeLocalStructuredAction } from '../agentActions';
import { getMetaWearablesDat } from '../../native/metaWearablesDat';

const MANIFEST = {
  schema: 'handsfree.meta-glasses/widget-manifest',
  schema_version: '0.1.0',
  widget_id: 'task-progress-active',
  widget_cid: 'sha256:widget',
  interface_cid: 'sha256:descriptor',
  operation: 'render_widget',
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

function mobilePayload(type, overrides = {}) {
  return {
    contract: 'handsfree.meta-glasses/display-widget-action@0.1.0',
    type,
    action: type.replace(/^mobile_/, '').replace(/_display_widget.*$/, ''),
    operation: overrides.operation || 'render_widget',
    descriptor_cid: 'sha256:descriptor',
    interface_cid: 'sha256:descriptor',
    widget_id: 'task-progress-active',
    widget_cid: 'sha256:widget',
    orb_receipt_cid: overrides.orb_receipt_cid || 'sha256:render-receipt',
    policy_decision: {
      outcome: 'permit',
      reasons: ['Required capabilities granted.'],
    },
    correlation_id: overrides.correlation_id || 'corr-render',
    request_id: overrides.request_id || 'render-1',
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

function createMockDisplayBridge() {
  const diagnostics = {
    activeWidgetId: null,
    widgetCid: null,
    displayLastAction: null,
    displayLastStatus: null,
    displayLastUpdatedAt: null,
    renderCount: 0,
    updateCount: 0,
    clearCount: 0,
    receiptCids: [],
  };
  const calls = [];
  const record = (payload, result) => {
    diagnostics.displayLastAction = result.action;
    diagnostics.displayLastStatus = result.displayLastStatus;
    diagnostics.displayLastUpdatedAt = result.displayLastUpdatedAt;
    diagnostics.widgetCid = payload.widget_cid || diagnostics.widgetCid;
    diagnostics.receiptCids.push(payload.orb_receipt_cid);
    calls.push({ payload, result });
    return result;
  };

  return {
    calls,
    diagnostics,
    renderDisplayWidget: jest.fn(async (manifest, payload) => {
      diagnostics.activeWidgetId = manifest.widget_id;
      diagnostics.renderCount += 1;
      return record(payload, {
        action: 'render_display_widget',
        operation: 'render_widget',
        supported: false,
        message: 'Widget rendered in mocked fallback bridge.',
        renderPath: payload.fallback.render_path,
        widgetId: manifest.widget_id,
        widgetCid: manifest.widget_cid,
        orbReceiptCid: payload.orb_receipt_cid,
        displayLastStatus: 'rendered',
        displayLastUpdatedAt: 1779440401000,
      });
    }),
    updateDisplayWidget: jest.fn(async (patch, payload) => {
      diagnostics.updateCount += 1;
      return record(payload, {
        action: 'update_display_widget',
        operation: 'update_widget',
        supported: false,
        message: 'Widget updated in mocked fallback bridge.',
        renderPath: payload.fallback.render_path,
        widgetId: payload.widget_id,
        widgetCid: payload.widget_cid,
        orbReceiptCid: payload.orb_receipt_cid,
        patch,
        displayLastStatus: 'updated',
        displayLastUpdatedAt: 1779440402000,
      });
    }),
    clearDisplayWidget: jest.fn(async (widgetId, payload) => {
      diagnostics.activeWidgetId = null;
      diagnostics.clearCount += 1;
      return record(payload, {
        action: 'clear_display_widget',
        operation: 'clear_widget',
        supported: false,
        message: 'Widget cleared in mocked fallback bridge.',
        renderPath: payload.fallback.render_path,
        widgetId,
        widgetCid: payload.widget_cid,
        orbReceiptCid: payload.orb_receipt_cid,
        displayLastStatus: 'cleared',
        displayLastUpdatedAt: 1779440403000,
      });
    }),
  };
}

describe('display widget hardware-free mobile harness', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('executes backend render/update/clear actions through a mocked bridge and updates diagnostics', async () => {
    const navigate = jest.fn();
    const dat = createMockDisplayBridge();
    getMetaWearablesDat.mockResolvedValue(dat);

    const renderPayload = mobilePayload('mobile_render_display_widget', {
      operation: 'render_widget',
      manifest: MANIFEST,
      state: MANIFEST.state.values,
    });
    const updatePayload = mobilePayload('mobile_update_display_widget', {
      operation: 'update_widget',
      correlation_id: 'corr-update',
      request_id: 'update-1',
      orb_receipt_cid: 'sha256:update-receipt',
      patch: { progress: 0.43, progress_label: '43% complete' },
    });
    const clearPayload = mobilePayload('mobile_clear_display_widget', {
      operation: 'clear_widget',
      correlation_id: 'corr-clear',
      request_id: 'clear-1',
      orb_receipt_cid: 'sha256:clear-receipt',
    });

    const rendered = await executeLocalStructuredAction({
      actionItem: actionItem('mobile_render_display_widget', renderPayload),
      navigation: { navigate },
    });
    const updated = await executeLocalStructuredAction({
      actionItem: actionItem('mobile_update_display_widget', updatePayload),
      navigation: { navigate },
    });
    const cleared = await executeLocalStructuredAction({
      actionItem: actionItem('mobile_clear_display_widget', clearPayload),
      navigation: { navigate },
    });

    expect(rendered).toMatchObject({
      handled: true,
      message: 'Widget rendered in mocked fallback bridge.',
      response: {
        action: 'render_display_widget',
        operation: 'render_widget',
        widgetId: 'task-progress-active',
        orbReceiptCid: 'sha256:render-receipt',
      },
    });
    expect(updated).toMatchObject({
      handled: true,
      response: {
        action: 'update_display_widget',
        operation: 'update_widget',
        patch: { progress: 0.43, progress_label: '43% complete' },
        orbReceiptCid: 'sha256:update-receipt',
      },
    });
    expect(cleared).toMatchObject({
      handled: true,
      response: {
        action: 'clear_display_widget',
        operation: 'clear_widget',
        widgetId: 'task-progress-active',
        orbReceiptCid: 'sha256:clear-receipt',
      },
    });
    expect(dat.renderDisplayWidget).toHaveBeenCalledWith(MANIFEST, expect.objectContaining({
      type: 'mobile_render_display_widget',
      orb_receipt_cid: 'sha256:render-receipt',
    }));
    expect(dat.updateDisplayWidget).toHaveBeenCalledWith(
      { progress: 0.43, progress_label: '43% complete' },
      expect.objectContaining({ type: 'mobile_update_display_widget' }),
    );
    expect(dat.clearDisplayWidget).toHaveBeenCalledWith(
      'task-progress-active',
      expect.objectContaining({ type: 'mobile_clear_display_widget' }),
    );
    expect(dat.diagnostics).toEqual({
      activeWidgetId: null,
      widgetCid: 'sha256:widget',
      displayLastAction: 'clear_display_widget',
      displayLastStatus: 'cleared',
      displayLastUpdatedAt: 1779440403000,
      renderCount: 1,
      updateCount: 1,
      clearCount: 1,
      receiptCids: [
        'sha256:render-receipt',
        'sha256:update-receipt',
        'sha256:clear-receipt',
      ],
    });
    expect(navigate).toHaveBeenCalledTimes(3);
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });
});
