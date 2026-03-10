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

  it('returns handled false for non-local actions', async () => {
    const outcome = await executeLocalStructuredAction({
      actionItem: { id: 'read_cid' },
      navigation: { navigate: jest.fn() },
    });

    expect(outcome).toEqual({ handled: false });
  });
});
