import {
  buildAgentNotificationCard,
  buildAgentResultCard,
  buildAgentTaskCard,
  buildTaskLifecycleActionItems,
} from '../agentCards';

describe('buildTaskLifecycleActionItems', () => {
  it('returns pause and cancel for running tasks', () => {
    expect(buildTaskLifecycleActionItems({ state: 'running' })).toEqual([
      { id: 'mobile_pause_task', label: 'Pause', phrase: 'pause this task' },
      { id: 'mobile_cancel_task', label: 'Cancel', phrase: 'cancel this task' },
    ]);
  });

  it('returns resume and cancel for paused tasks', () => {
    expect(buildTaskLifecycleActionItems({ state: 'needs_input' })).toEqual([
      { id: 'mobile_resume_task', label: 'Resume', phrase: 'resume this task' },
      { id: 'mobile_cancel_task', label: 'Cancel', phrase: 'cancel this task' },
    ]);
  });
});

describe('buildAgentTaskCard', () => {
  it('prepends lifecycle controls to task action items', () => {
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-03-08T10:05:00.000Z').getTime());
    const card = buildAgentTaskCard({
      id: 'task-123',
      state: 'running',
      provider: 'ipfs_accelerate_mcp',
      instruction: 'discover and fetch climate regulations',
      updated_at: '2026-03-08T10:00:00.000Z',
      result: {
        capability: 'agentic_fetch',
        seed_urls: ['https://example.com'],
      },
    });

    expect(card.action_items[0].id).toBe('mobile_pause_task');
    expect(card.action_items[1].id).toBe('mobile_cancel_task');
    expect(card.action_items.some((item) => item.id === 'rerun_workflow')).toBe(true);
    expect(card.action_items.find((item) => item.id === 'rerun_workflow').execution_mode).toBe('mcp_remote');
    expect(card.status_badge).toBe('Running');
    expect(card.status_tone).toBe('active');
    expect(card.is_live).toBe(true);
    expect(card.live_label).toBe('Live');
    expect(card.timestamp_label).toBe('Updated 5m ago');
    Date.now.mockRestore();
  });

  it('prefers result envelope summary, cid, and server follow-up actions', () => {
    const card = buildAgentTaskCard({
      id: 'task-789',
      state: 'completed',
      provider: 'ipfs_kit_mcp',
      instruction: 'pin bafy123 on ipfs',
      result_envelope: {
        summary: 'Pinned bafy123.',
        status: 'completed',
        structured_output: { message: 'Pinned bafy123.' },
        artifact_refs: { result_cid: 'bafy123' },
        follow_up_actions: [{ id: 'read_cid', label: 'Read CID', phrase: 'read the cid' }],
      },
    });

    expect(card.lines[0]).toBe('Instruction: pin bafy123 on ipfs');
    expect(card.lines[1]).toBe('Pinned bafy123.');
    expect(card.deep_link).toBe('ipfs://bafy123');
    expect(card.action_items[0].id).toBe('read_cid');
  });

  it('shows remote fallback execution details on task cards', () => {
    const card = buildAgentTaskCard({
      id: 'task-790',
      state: 'completed',
      provider: 'ipfs_kit_mcp',
      instruction: 'pin bafy123 on ipfs',
      mcp_preferred_execution_mode: 'direct_import',
      mcp_execution_mode: 'mcp_remote',
      result: {
        capability: 'ipfs_pin',
        cid: 'bafy123',
      },
    });

    expect(card.lines).toContain('Execution: Remote (local unavailable)');
  });

  it('shows MCP runtime metadata on running task cards', () => {
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-03-09T00:05:00.000Z').getTime());
    const card = buildAgentTaskCard({
      id: 'task-runtime',
      state: 'running',
      provider: 'ipfs_accelerate_mcp',
      instruction: 'inspect connected wearable',
      mcp_started_at: '2026-03-09T00:00:00+00:00',
      mcp_timeout_s: 30,
      mcp_poll_interval_s: 2,
      result_envelope: {
        summary: 'Wearables bridge connectivity workflow running for Ray-Ban Meta.',
        status: 'running',
        structured_output: {
          workflow: 'wearables_bridge_connectivity',
          device_name: 'Ray-Ban Meta',
          target_connection_state: 'connected',
        },
      },
    });

    expect(card.lines).toContain('Age: 5m');
    expect(card.lines).toContain('Timeout: 30s');
    expect(card.lines).toContain('Poll: 2s');
    Date.now.mockRestore();
  });

  it('renders wearables connectivity receipts with receipt-specific title and labels', () => {
    const card = buildAgentTaskCard({
      id: 'task-bridge',
      state: 'completed',
      provider: 'ipfs_accelerate_mcp',
      result_envelope: {
        summary: 'Wearables bridge connectivity receipt captured for Ray-Ban Meta.',
        structured_output: {
          workflow: 'wearables_bridge_connectivity',
          device_id: 'AA:BB',
          device_name: 'Ray-Ban Meta',
          target_connection_state: 'connected',
          target_rssi: -42,
          cid: 'bafyreceipt',
        },
        artifact_refs: { result_cid: 'bafyreceipt' },
      },
    });

    expect(card.title).toBe('Wearables Connectivity Receipt');
    expect(card.subtitle).toBe('Ray-Ban Meta');
    expect(card.lines).toContain('Device: Ray-Ban Meta');
    expect(card.lines).toContain('State: connected');
    expect(card.action_items[0]).toMatchObject({
      id: 'mobile_open_wearables_diagnostics',
      label: 'Open Diagnostics',
    });
    expect(card.action_items[1]).toMatchObject({
      id: 'mobile_reconnect_wearables_target',
      label: 'Reconnect Target',
    });
    expect(card.action_items.find((item) => item.id === 'read_cid')).toMatchObject({
      label: 'Read Receipt',
      phrase: 'read the wearables receipt',
    });
  });

  it('uses task description when instruction is absent', () => {
    const card = buildAgentTaskCard({
      id: 'task-791',
      state: 'completed',
      provider: 'ipfs_datasets_mcp',
      description: 'find legal datasets',
      result: {
        capability: 'dataset_discovery',
        message: 'Expanded legal query',
      },
    });

    expect(card.lines).toContain('Instruction: find legal datasets');
  });
});

describe('buildAgentNotificationCard', () => {
  it('adds lifecycle controls for active task notifications', () => {
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-03-08T10:05:00.000Z').getTime());
    const card = buildAgentNotificationCard({
      id: 'notif-1',
      event_type: 'task_paused',
      timestamp: '2026-03-08T10:04:00.000Z',
      metadata: {
        task_id: 'task-123',
      },
      card: {
        title: 'IPFS Datasets paused',
        subtitle: 'Task task-123 • paused',
        lines: ['Task paused'],
        action_items: [{ id: 'show_result_details', label: 'Task Details', phrase: 'show task details for that result' }],
      },
    });

    expect(card.action_items[0].id).toBe('mobile_resume_task');
    expect(card.action_items[1].id).toBe('mobile_cancel_task');
    expect(card.action_items.some((item) => item.id === 'show_result_details')).toBe(true);
    expect(card.status_badge).toBe('Paused');
    expect(card.status_tone).toBe('paused');
    expect(card.is_live).toBe(false);
    expect(card.timestamp_label).toBe('Updated 1m ago');
    Date.now.mockRestore();
  });

  it('adds explicit local and remote ipfs action metadata', () => {
    const card = buildAgentTaskCard({
      id: 'task-456',
      state: 'completed',
      provider: 'ipfs_kit_mcp',
      instruction: 'pin bafy123 on ipfs',
      result: {
        cid: 'bafy123',
        capability: 'ipfs_pin',
      },
    });

    expect(card.action_items.find((item) => item.id === 'pin_result_local')).toMatchObject({
      execution_mode: 'direct_import',
      execution_mode_label: 'Local',
      params: { cid: 'bafy123', mcp_preferred_execution_mode: 'direct_import' },
    });
    expect(card.action_items.find((item) => item.id === 'pin_result_remote')).toMatchObject({
      execution_mode: 'mcp_remote',
      execution_mode_label: 'Remote',
      params: { cid: 'bafy123', mcp_preferred_execution_mode: 'mcp_remote' },
    });
  });

  it('uses result envelope follow-up actions for result cards when provided', () => {
    const card = buildAgentTaskCard({
      id: 'task-999',
      state: 'completed',
      provider: 'ipfs_datasets_mcp',
      instruction: 'find legal datasets',
      result_envelope: {
        summary: 'Expanded legal query',
        structured_output: { message: 'Expanded legal query' },
        follow_up_actions: [{ id: 'open_result', label: 'Open Result', phrase: 'open that result' }],
      },
    });

    expect(card.action_items).toEqual([{ id: 'open_result', label: 'Open Result', phrase: 'open that result' }]);
  });

  it('shows remote fallback execution details on notification cards', () => {
    const card = buildAgentNotificationCard({
      id: 'notif-2',
      event_type: 'task_completed',
      timestamp: '2026-03-08T10:04:00.000Z',
      metadata: {
        task_id: 'task-456',
        mcp_preferred_execution_mode: 'direct_import',
        mcp_execution_mode: 'mcp_remote',
      },
      card: {
        title: 'IPFS Kit completed',
        subtitle: 'Task task-456 • completed',
        lines: ['Pinned bafy123'],
        action_items: [{ id: 'read_cid', label: 'Read CID', phrase: 'read the cid' }],
      },
    });

    expect(card.lines).toContain('Execution: Remote (local unavailable)');
  });

  it('prepends local wearables actions for connectivity receipt notifications', () => {
    const card = buildAgentNotificationCard({
      id: 'notif-bridge',
      event_type: 'task_completed',
      timestamp: '2026-03-08T10:04:00.000Z',
      metadata: {
        task_id: 'task-bridge',
        result_envelope: {
          summary: 'Wearables bridge connectivity receipt captured for Ray-Ban Meta.',
          structured_output: {
            workflow: 'wearables_bridge_connectivity',
            device_id: 'AA:BB',
            device_name: 'Ray-Ban Meta',
            target_connection_state: 'connected',
            target_rssi: -42,
            cid: 'bafyreceipt',
          },
          artifact_refs: { result_cid: 'bafyreceipt' },
        },
      },
      card: {
        title: 'Wearables Connectivity Receipt',
        subtitle: 'Ray-Ban Meta',
        lines: ['Device: Ray-Ban Meta', 'State: connected'],
        action_items: [{ id: 'read_cid', label: 'Read Receipt', phrase: 'read the wearables receipt' }],
      },
    });

    expect(card.action_items[0]).toMatchObject({
      id: 'mobile_open_wearables_diagnostics',
      label: 'Open Diagnostics',
    });
    expect(card.action_items[1]).toMatchObject({
      id: 'mobile_reconnect_wearables_target',
      label: 'Reconnect Target',
    });
    expect(card.action_items[2]).toMatchObject({
      id: 'read_cid',
      label: 'Read Receipt',
    });
  });

  it('shows runtime metadata on notification cards when present', () => {
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-03-09T00:05:00.000Z').getTime());
    const card = buildAgentNotificationCard({
      id: 'notif-runtime',
      event_type: 'task_running',
      timestamp: '2026-03-09T00:04:00.000Z',
      metadata: {
        task_id: 'task-runtime',
        state: 'running',
        mcp_started_at: '2026-03-09T00:00:00+00:00',
        mcp_timeout_s: 30,
        mcp_poll_interval_s: 2,
      },
      card: {
        title: 'IPFS Accelerate running',
        subtitle: 'Task task-runtime • running',
        lines: ['Task is running'],
        action_items: [{ id: 'show_result_details', label: 'Task Details', phrase: 'show task details for that result' }],
      },
    });

    expect(card.lines).toContain('Age: 5m');
    expect(card.lines).toContain('Timeout: 30s');
    expect(card.lines).toContain('Poll: 2s');
    Date.now.mockRestore();
  });
});

describe('buildAgentResultCard', () => {
  it('renders wearables connectivity result cards distinctly', () => {
    const card = buildAgentResultCard({
      task_id: 'task-bridge',
      state: 'completed',
      provider: 'ipfs_accelerate_mcp',
      updated_at: '2026-03-08T10:00:00.000Z',
      result_envelope: {
        summary: 'Wearables bridge connectivity receipt captured for Ray-Ban Meta.',
        structured_output: {
          workflow: 'wearables_bridge_connectivity',
          device_name: 'Ray-Ban Meta',
          target_connection_state: 'connected',
          target_rssi: -42,
          cid: 'bafyreceipt',
        },
        artifact_refs: { result_cid: 'bafyreceipt' },
      },
    });

    expect(card.title).toBe('Wearables Connectivity Receipt');
    expect(card.subtitle).toBe('Ray-Ban Meta');
    expect(card.deep_link).toBe('ipfs://bafyreceipt');
    expect(card.lines).toContain('Device: Ray-Ban Meta');
    expect(card.action_items[0]).toMatchObject({
      id: 'mobile_open_wearables_diagnostics',
      label: 'Open Diagnostics',
    });
    expect(card.action_items[1]).toMatchObject({
      id: 'mobile_reconnect_wearables_target',
      label: 'Reconnect Target',
    });
  });

  it('shows runtime metadata on result cards when present', () => {
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-03-09T00:05:00.000Z').getTime());
    const card = buildAgentResultCard({
      task_id: 'task-runtime',
      state: 'running',
      provider: 'ipfs_accelerate_mcp',
      mcp_started_at: '2026-03-09T00:00:00+00:00',
      mcp_timeout_s: 30,
      mcp_poll_interval_s: 2,
      result_envelope: {
        summary: 'Wearables bridge connectivity workflow running for Ray-Ban Meta.',
        structured_output: {
          workflow: 'wearables_bridge_connectivity',
          device_name: 'Ray-Ban Meta',
          target_connection_state: 'connected',
        },
      },
    });

    expect(card.lines).toContain('Age: 5m');
    expect(card.lines).toContain('Timeout: 30s');
    expect(card.lines).toContain('Poll: 2s');
    Date.now.mockRestore();
  });
});
