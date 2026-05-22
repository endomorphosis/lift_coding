jest.mock('../../native/metaWearablesDat', () => ({
  getMetaWearablesDat: jest.fn(),
}));

import {
  buildLastActionLines,
  executeLocalStructuredAction,
  extractActionTaskUpdate,
} from '../agentActions';
import { getMetaWearablesDat } from '../../native/metaWearablesDat';

describe('agentActions helpers', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('extracts task metadata from structured action responses', () => {
    expect(
      extractActionTaskUpdate({
        follow_on_task: {
          task_id: 'task-123',
          state: 'running',
          provider: 'ipfs_accelerate_mcp',
          provider_label: 'IPFS Accelerate',
          capability: 'agentic_fetch',
          summary: 'IPFS Accelerate agentic fetch running.',
        },
        intent: {
          entities: {
            task_id: 'task-123',
          },
        },
        debug: {
          tool_calls: [
            {
              task_id: 'task-123',
              state: 'running',
              provider: 'ipfs_accelerate_mcp',
            },
          ],
        },
      })
    ).toEqual({
      task_id: 'task-123',
      state: 'running',
      provider: 'ipfs_accelerate_mcp',
      provider_label: 'IPFS Accelerate',
      capability: 'agentic_fetch',
      summary: 'IPFS Accelerate agentic fetch running.',
    });
  });

  it('builds last action lines with follow-on summary when present', () => {
    expect(
      buildLastActionLines({
        message: 'Workflow rerun requested.',
        taskUpdate: {
          task_id: 'task-123',
          summary: 'IPFS Accelerate agentic fetch running.',
        },
      })
    ).toEqual([
      'Workflow rerun requested.',
      'IPFS Accelerate agentic fetch running.',
    ]);
  });

  it('returns null when the action response has no task context', () => {
    expect(
      extractActionTaskUpdate({
        intent: { entities: {} },
        debug: { tool_calls: [] },
      })
    ).toBeNull();
  });

  it('runs wearables reconnect locally and navigates to diagnostics', async () => {
    const navigate = jest.fn();
    getMetaWearablesDat.mockResolvedValue({
      reconnectSelectedDeviceTarget: jest.fn(async () => ({
        deviceId: 'AA:BB',
        deviceName: 'Ray-Ban Meta',
        targetConnectionState: 'discovered',
      })),
    });

    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'mobile_reconnect_wearables_target' },
      navigation: { navigate },
    });

    expect(outcome).toEqual({
      handled: true,
      message: 'Reconnect attempted for Ray-Ban Meta. State: discovered.',
      response: {
        deviceId: 'AA:BB',
        deviceName: 'Ray-Ban Meta',
        targetConnectionState: 'discovered',
      },
    });
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it('opens wearables diagnostics locally without calling the bridge', async () => {
    const navigate = jest.fn();

    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'mobile_open_wearables_diagnostics' },
      navigation: { navigate },
    });

    expect(outcome).toEqual({
      handled: true,
      message: 'Opened wearables bridge diagnostics.',
      response: null,
    });
    expect(getMetaWearablesDat).not.toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it('renders wearables display test locally and navigates to diagnostics', async () => {
    const navigate = jest.fn();
    getMetaWearablesDat.mockResolvedValue({
      renderDisplayTest: jest.fn(async () => ({
        action: 'render_display_test',
        message: 'Display test rendering is not implemented in the DAT bridge yet.',
      })),
    });

    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'mobile_render_wearables_display_test' },
      navigation: { navigate },
    });

    expect(outcome).toEqual({
      handled: true,
      message: 'Display test rendering is not implemented in the DAT bridge yet.',
      response: {
        action: 'render_display_test',
        message: 'Display test rendering is not implemented in the DAT bridge yet.',
      },
    });
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it('clears wearables display locally and navigates to diagnostics', async () => {
    const navigate = jest.fn();
    getMetaWearablesDat.mockResolvedValue({
      clearDisplay: jest.fn(async () => ({
        action: 'clear_display',
        message: 'Display clearing is not implemented in the DAT bridge yet.',
      })),
    });

    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'mobile_clear_wearables_display' },
      navigation: { navigate },
    });

    expect(outcome).toEqual({
      handled: true,
      message: 'Display clearing is not implemented in the DAT bridge yet.',
      response: {
        action: 'clear_display',
        message: 'Display clearing is not implemented in the DAT bridge yet.',
      },
    });
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it('plays wearables display video locally and navigates to diagnostics', async () => {
    const navigate = jest.fn();
    getMetaWearablesDat.mockResolvedValue({
      playDisplayVideo: jest.fn(async () => ({
        action: 'play_display_video',
        message: 'Display video playback requested.',
      })),
    });

    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'mobile_play_wearables_display_video', params: { video_url: 'https://example.com/test.mp4' } },
      navigation: { navigate },
    });

    expect(outcome).toEqual({
      handled: true,
      message: 'Display video playback requested.',
      response: {
        action: 'play_display_video',
        message: 'Display video playback requested.',
      },
    });
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it('resets wearables display session locally and navigates to diagnostics', async () => {
    const navigate = jest.fn();
    getMetaWearablesDat.mockResolvedValue({
      resetDisplaySession: jest.fn(async () => ({
        action: 'reset_display_session',
        message: 'Display session reset requested.',
      })),
    });

    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'mobile_reset_wearables_display_session' },
      navigation: { navigate },
    });

    expect(outcome).toEqual({
      handled: true,
      message: 'Display session reset requested.',
      response: {
        action: 'reset_display_session',
        message: 'Display session reset requested.',
      },
    });
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it('executes display widget mobile action contract locally and navigates to diagnostics', async () => {
    const navigate = jest.fn();
    const dat = {
      renderDisplayWidget: jest.fn(async () => ({
        action: 'render_display_widget',
        message: 'Widget rendered.',
      })),
      updateDisplayWidget: jest.fn(async () => ({
        action: 'update_display_widget',
        message: 'Widget updated.',
      })),
      clearDisplayWidget: jest.fn(async () => ({
        action: 'clear_display_widget',
        message: 'Widget cleared.',
      })),
      focusDisplayWidget: jest.fn(async () => ({
        action: 'focus_display_widget',
        message: 'Widget focused.',
      })),
      activateDisplayWidgetAction: jest.fn(async () => ({
        action: 'activate_display_widget_action',
        message: 'Widget action activated.',
      })),
      resetDisplayWidgetSession: jest.fn(async () => ({
        action: 'reset_display_widget_session',
        message: 'Widget session reset.',
      })),
      playDisplayWidgetVideo: jest.fn(async () => ({
        action: 'play_display_widget_video',
        message: 'Widget video playback requested.',
      })),
      subscribeDisplayWidgetUpdates: jest.fn(async () => ({
        action: 'subscribe_display_widget_updates',
        message: 'Widget update subscription requested.',
      })),
    };
    getMetaWearablesDat.mockResolvedValue(dat);

    const payload = {
      contract: 'handsfree.meta-glasses/display-widget-action@0.1.0',
      type: 'mobile_render_display_widget',
      descriptor_cid: 'bafybeidescriptor',
      widget_id: 'handsfree.task-progress-widget',
      widget_cid: 'bafybeiwidget',
      orb_receipt_cid: 'bafybeiorbreceipt',
      policy_decision: { outcome: 'permit', reasons: ['trusted descriptor'] },
      correlation_id: 'corr-widget',
      manifest: { id: 'handsfree.task-progress-widget', template: 'status' },
      patch: { progress: 75 },
      focus: { direction: 'previous' },
      activated_action_id: 'primary',
      video: {
        media_id: 'preview',
        uri: 'ipfs://bafybeivideo',
        content_type: 'video/mp4',
      },
      subscription: {
        stream: 'display_widget_update',
      },
    };
    const actionItem = (id) => ({
      id,
      params: {
        display_widget_action: {
          ...payload,
          type: id,
        },
      },
    });

    await expect(
      executeLocalStructuredAction({
        actionItem: actionItem('mobile_render_display_widget'),
        navigation: { navigate },
      })
    ).resolves.toMatchObject({
      handled: true,
      message: 'Widget rendered.',
      response: { action: 'render_display_widget' },
    });
    await executeLocalStructuredAction({
      actionItem: actionItem('mobile_update_display_widget'),
      navigation: { navigate },
    });
    await executeLocalStructuredAction({
      actionItem: actionItem('mobile_clear_display_widget'),
      navigation: { navigate },
    });
    await executeLocalStructuredAction({
      actionItem: actionItem('mobile_focus_display_widget'),
      navigation: { navigate },
    });
    await executeLocalStructuredAction({
      actionItem: actionItem('mobile_activate_display_widget_action'),
      navigation: { navigate },
    });
    await executeLocalStructuredAction({
      actionItem: actionItem('mobile_reset_display_widget_session'),
      navigation: { navigate },
    });
    await executeLocalStructuredAction({
      actionItem: actionItem('mobile_play_display_widget_video'),
      navigation: { navigate },
    });
    await executeLocalStructuredAction({
      actionItem: actionItem('mobile_subscribe_display_widget_updates'),
      navigation: { navigate },
    });

    expect(dat.renderDisplayWidget).toHaveBeenCalledWith(payload.manifest, expect.objectContaining({
      type: 'mobile_render_display_widget',
      widget_id: 'handsfree.task-progress-widget',
    }));
    expect(dat.updateDisplayWidget).toHaveBeenCalledWith(payload.patch, expect.objectContaining({
      type: 'mobile_update_display_widget',
    }));
    expect(dat.clearDisplayWidget).toHaveBeenCalledWith('handsfree.task-progress-widget', expect.objectContaining({
      type: 'mobile_clear_display_widget',
    }));
    expect(dat.focusDisplayWidget).toHaveBeenCalledWith('previous', expect.objectContaining({
      type: 'mobile_focus_display_widget',
    }));
    expect(dat.activateDisplayWidgetAction).toHaveBeenCalledWith('primary', expect.objectContaining({
      type: 'mobile_activate_display_widget_action',
    }));
    expect(dat.resetDisplayWidgetSession).toHaveBeenCalledWith(expect.objectContaining({
      type: 'mobile_reset_display_widget_session',
    }));
    expect(dat.playDisplayWidgetVideo).toHaveBeenCalledWith(payload.video, expect.objectContaining({
      type: 'mobile_play_display_widget_video',
      orb_receipt_cid: 'bafybeiorbreceipt',
      policy_decision: { outcome: 'permit', reasons: ['trusted descriptor'] },
      correlation_id: 'corr-widget',
    }));
    expect(dat.subscribeDisplayWidgetUpdates).toHaveBeenCalledWith(payload.subscription, expect.objectContaining({
      type: 'mobile_subscribe_display_widget_updates',
      orb_receipt_cid: 'bafybeiorbreceipt',
      correlation_id: 'corr-widget',
    }));
    expect(navigate).toHaveBeenCalledTimes(8);
    expect(navigate).toHaveBeenCalledWith('Glasses');
  });

  it('returns handled false for non-local actions', async () => {
    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'read_cid' },
      navigation: { navigate: jest.fn() },
    });

    expect(outcome).toEqual({ handled: false });
  });
});
