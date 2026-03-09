jest.mock('../config', () => ({
  getBaseUrl: jest.fn().mockResolvedValue('http://example.test'),
  getHeaders: jest.fn().mockResolvedValue({
    'Content-Type': 'application/json',
    Authorization: 'Bearer test-token',
  }),
}));

import {
  getDevPeerChatConversations,
  getDevPeerChatHandsetSession,
  getDevPeerChatHistory,
  getDevPeerChatOutbox,
  getDevPeerChatOutboxStatus,
  getDevTransportSessions,
  getAgentResults,
  getAgentTasks,
  getAgentTaskDetail,
  deleteDevTransportSession,
  postAgentTaskControl,
  postDevPeerChatHandsetHeartbeat,
  postDevPeerChatOutboxAck,
  postDevPeerChatOutboxPromote,
  postDevPeerChatOutboxRelease,
  postDevPeerChatSend,
  postDevPeerEnvelope,
  getNotificationDetail,
  getNotifications,
  sendCommand,
  delegateWearablesBridgeTask,
  sendActionCommand,
  confirmCommand,
} from '../client';

describe('sendCommand', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes explicit follow_on_task metadata from command responses', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        status: 'ok',
        spoken_text: 'Task created.',
        intent: { name: 'agent.delegate', confidence: 0.9, entities: { task_id: 'task-123' } },
        follow_on_task: {
          task_id: 'task-123',
          state: 'running',
          provider: 'copilot',
        },
      }),
    });

    const response = await sendCommand('tell copilot to handle issue 42');

    expect(response.follow_on_task).toEqual({
      task_id: 'task-123',
      state: 'running',
      provider: 'copilot',
      provider_label: null,
      capability: null,
      summary: null,
    });
  });
});

describe('sendActionCommand', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('posts a structured action command with profile, client context, and params', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        status: 'ok',
        spoken_text: 'Pinned it.',
        cards: [],
        follow_on_task: {
          task_id: 'task-456',
          state: 'running',
          provider: 'ipfs_kit_mcp',
          provider_label: 'IPFS Kit',
          capability: 'ipfs_pin',
          summary: 'IPFS Kit pin content running.',
        },
      }),
    });

    const response = await sendActionCommand('pin_result', {
      profile: 'workout',
      params: {
        cid: 'bafy-test',
        card: { title: 'IPFS Result', deep_link: 'ipfs://bafy-test' },
      },
      client_context: {
        timezone: 'America/Los_Angeles',
        debug: true,
      },
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/commands/action',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
      })
    );
    const [, request] = global.fetch.mock.calls[0];
    const body = JSON.parse(request.body);
    expect(body).toEqual({
      action_id: 'pin_result',
      params: {
        cid: 'bafy-test',
        card: { title: 'IPFS Result', deep_link: 'ipfs://bafy-test' },
      },
      profile: 'workout',
      client_context: {
        device: 'mobile',
        locale: 'en-US',
        timezone: 'America/Los_Angeles',
        app_version: 'dev',
        noise_mode: false,
        debug: true,
        privacy_mode: 'strict',
      },
    });
    expect(response.status).toBe('ok');
    expect(response.follow_on_task).toEqual({
      task_id: 'task-456',
      state: 'running',
      provider: 'ipfs_kit_mcp',
      provider_label: 'IPFS Kit',
      capability: 'ipfs_pin',
      summary: 'IPFS Kit pin content running.',
    });
  });

  it('throws backend-provided errors for action failures', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      json: jest.fn().mockResolvedValue({
        error: 'invalid_action_id',
      }),
    });

    await expect(sendActionCommand('unknown_action')).rejects.toThrow('invalid_action_id');
  });
});

describe('delegateWearablesBridgeTask', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('delegates a wearables bridge follow-on task through the command API', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        status: 'ok',
        spoken_text: 'Wearables bridge task started.',
        follow_on_task: {
          task_id: 'task-bridge-1',
          state: 'running',
          provider: 'ipfs_accelerate_mcp',
          provider_label: 'IPFS Accelerate',
          capability: 'agentic_fetch',
          summary: 'Wearables bridge inspection running.',
        },
      }),
    });

    const response = await delegateWearablesBridgeTask({
      deviceId: 'AA:BB',
      deviceName: 'Ray-Ban Meta',
      targetConnectionState: 'connected',
      targetRssi: -42,
      targetLastSeenAt: 1700000000000,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/command',
      expect.objectContaining({
        method: 'POST',
      })
    );
    const [, request] = global.fetch.mock.calls[0];
    const body = JSON.parse(request.body);
    expect(body.input.type).toBe('text');
    expect(body.input.text).toContain('Ray-Ban Meta');
    expect(body.input.text).toContain('Device id: AA:BB.');
    expect(body.input.text).toContain('Observed RSSI: -42.');
    expect(body.client_context.feature).toBe('wearables_bridge');
    expect(body.client_context.trigger).toBe('target_connected');
    expect(response.follow_on_task).toEqual({
      task_id: 'task-bridge-1',
      state: 'running',
      provider: 'ipfs_accelerate_mcp',
      provider_label: 'IPFS Accelerate',
      capability: 'agentic_fetch',
      summary: 'Wearables bridge inspection running.',
    });
  });
});

describe('confirmCommand', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes follow_on_task metadata from confirmation responses', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        status: 'ok',
        spoken_text: 'Workflow rerun requested.',
        intent: { name: 'agent.delegate.confirmed', confidence: 1, entities: {} },
        follow_on_task: {
          task_id: 'task-789',
          state: 'running',
          provider: 'ipfs_accelerate_mcp',
          provider_label: 'IPFS Accelerate',
          capability: 'agentic_fetch',
          summary: 'IPFS Accelerate agentic fetch running.',
        },
      }),
    });

    const response = await confirmCommand('conf-123');

    expect(response.follow_on_task).toEqual({
      task_id: 'task-789',
      state: 'running',
      provider: 'ipfs_accelerate_mcp',
      provider_label: 'IPFS Accelerate',
      capability: 'agentic_fetch',
      summary: 'IPFS Accelerate agentic fetch running.',
    });
  });
});

describe('notification client helpers', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('builds notification list query params', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        notifications: [],
      }),
    });

    await getNotifications({
      since: '2026-03-08T00:00:00Z',
      limit: 1,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/notifications?since=2026-03-08T00%3A00%3A00Z&limit=1',
      expect.objectContaining({
        method: 'GET',
      })
    );
  });

  it('fetches notification detail by id', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        id: 'notif-123',
        message: 'Dataset search complete',
        card: {
          title: 'Dataset Result',
          action_items: [{ id: 'open_result', label: 'Open', phrase: 'open that result' }],
        },
      }),
    });

    const response = await getNotificationDetail('notif-123');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/notifications/notif-123',
      expect.objectContaining({
        method: 'GET',
      })
    );
    expect(response.id).toBe('notif-123');
  });
});

describe('getAgentResults', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('builds saved-view result feed queries', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        results: [],
        filters: { view: 'datasets' },
      }),
    });

    await getAgentResults({
      view: 'datasets',
      sort: 'updated_at',
      direction: 'desc',
      limit: 20,
      offset: 5,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/agents/results?view=datasets&sort=updated_at&direction=desc&limit=20&offset=5',
      expect.objectContaining({
        method: 'GET',
      })
    );
  });
});

describe('getAgentTaskDetail', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('fetches agent task detail by id', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        id: 'task-123',
        provider: 'ipfs_datasets_mcp',
        description: 'find legal datasets',
        trace: {
          provider_label: 'IPFS Datasets',
          mcp_preferred_execution_mode: 'direct_import',
          mcp_execution_mode: 'mcp_remote',
        },
        result: { capability: 'dataset_discovery' },
      }),
    });

    const response = await getAgentTaskDetail('task-123');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/agents/tasks/task-123',
      expect.objectContaining({
        method: 'GET',
      })
    );
    expect(response.id).toBe('task-123');
    expect(response.instruction).toBe('find legal datasets');
    expect(response.provider_label).toBe('IPFS Datasets');
    expect(response.mcp_preferred_execution_mode).toBe('direct_import');
    expect(response.mcp_execution_mode).toBe('mcp_remote');
  });
});

describe('getAgentTasks', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('builds active task queries with status and sort options', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        tasks: [],
        pagination: { limit: 20, offset: 0, has_more: false },
      }),
    });

    await getAgentTasks({
      status: 'running',
      sort: 'updated_at',
      direction: 'desc',
      limit: 20,
      result_view: 'normalized',
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/agents/tasks?status=running&result_view=normalized&sort=updated_at&direction=desc&limit=20',
      expect.objectContaining({
        method: 'GET',
      })
    );
  });

  it('normalizes task list items with top-level execution metadata fallbacks', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        tasks: [
          {
            id: 'task-789',
            provider: 'ipfs_kit_mcp',
            description: 'pin bafy123 on ipfs',
            trace: {
              mcp_preferred_execution_mode: 'direct_import',
              mcp_execution_mode: 'mcp_remote',
            },
          },
        ],
        pagination: { limit: 20, offset: 0, has_more: false },
        filters: { status: 'running', result_view: 'normalized' },
      }),
    });

    const response = await getAgentTasks({ status: 'running', result_view: 'normalized' });

    expect(response.tasks[0].instruction).toBe('pin bafy123 on ipfs');
    expect(response.tasks[0].mcp_preferred_execution_mode).toBe('direct_import');
    expect(response.tasks[0].mcp_execution_mode).toBe('mcp_remote');
  });
});

describe('postAgentTaskControl', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('posts lifecycle controls to the task endpoint', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        task_id: 'task-123',
        state: 'needs_input',
        message: 'Task paused successfully',
        updated_at: '2026-03-09T18:30:00Z',
      }),
    });

    const response = await postAgentTaskControl('task-123', 'pause');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/agents/tasks/task-123/pause',
      expect.objectContaining({
        method: 'POST',
      })
    );
    expect(response.task_id).toBe('task-123');
    expect(response.state).toBe('needs_input');
    expect(response.message).toBe('Task paused successfully');
    expect(response.updated_at).toBe('2026-03-09T18:30:00Z');
  });

  it('rejects unsupported lifecycle actions before making a request', async () => {
    await expect(postAgentTaskControl('task-123', 'archive')).rejects.toThrow(
      'Unsupported task control action: archive'
    );
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('rejects malformed lifecycle responses missing required fields', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({
        task_id: 'task-123',
        state: 'running',
      }),
    });

    await expect(postAgentTaskControl('task-123', 'resume')).rejects.toThrow(
      'Task control response is missing required fields'
    );
  });
});

describe('peer chat client helpers', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('posts dev peer envelopes to the validation endpoint', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({ accepted: true }),
    });

    await postDevPeerEnvelope('peer://demo', 'ZmFrZS1mcmFtZQ==');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/dev/peer-envelope',
      expect.objectContaining({
        method: 'POST',
      })
    );
    const [, request] = global.fetch.mock.calls[0];
    expect(JSON.parse(request.body)).toEqual({
      peer_ref: 'peer://demo',
      frame_base64: 'ZmFrZS1mcmFtZQ==',
    });
  });

  it('fetches peer chat history and recent conversations', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ conversation_id: 'chat-1', messages: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ conversations: [] }),
      });

    await getDevPeerChatHistory('chat-1');
    await getDevPeerChatConversations(5);

    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      'http://example.test/v1/dev/peer-chat/chat-1',
      expect.objectContaining({ method: 'GET' })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      'http://example.test/v1/dev/peer-chat?limit=5',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('posts backend peer chat sends with conversation and priority', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({ conversation_id: 'chat-1' }),
    });

    await postDevPeerChatSend('12D3KooWpeer', 'hello', 'chat-1', 'urgent');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/dev/peer-chat/send',
      expect.objectContaining({ method: 'POST' })
    );
    const [, request] = global.fetch.mock.calls[0];
    expect(JSON.parse(request.body)).toEqual({
      peer_id: '12D3KooWpeer',
      text: 'hello',
      conversation_id: 'chat-1',
      priority: 'urgent',
    });
  });

  it('builds peer chat outbox and status URLs correctly', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ messages: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ queued_total: 0 }),
      });

    await getDevPeerChatOutbox('12D3KooWlocal', 9000);
    await getDevPeerChatOutboxStatus('12D3KooWlocal');

    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      'http://example.test/v1/dev/peer-chat/outbox/12D3KooWlocal?lease_ms=9000',
      expect.objectContaining({ method: 'GET' })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      'http://example.test/v1/dev/peer-chat/outbox/12D3KooWlocal/status',
      expect.objectContaining({ method: 'GET' })
    );
  });

  it('posts outbox ack, release, promote, and handset heartbeat payloads', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ acknowledged_message_ids: ['msg-1'] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ released_message_ids: ['msg-2'] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ promoted_message_ids: ['msg-3'] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({ status: 'active' }),
      });

    await postDevPeerChatOutboxAck('12D3KooWlocal', ['msg-1']);
    await postDevPeerChatOutboxRelease('12D3KooWlocal', ['msg-2']);
    await postDevPeerChatOutboxPromote('12D3KooWlocal', ['msg-3']);
    await postDevPeerChatHandsetHeartbeat('12D3KooWlocal', 'HandsFree Peer Chat');

    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      'http://example.test/v1/dev/peer-chat/outbox/12D3KooWlocal/ack',
      expect.objectContaining({ method: 'POST' })
    );
    expect(JSON.parse(global.fetch.mock.calls[0][1].body)).toEqual({
      outbox_message_ids: ['msg-1'],
    });

    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      'http://example.test/v1/dev/peer-chat/outbox/12D3KooWlocal/release',
      expect.objectContaining({ method: 'POST' })
    );
    expect(JSON.parse(global.fetch.mock.calls[1][1].body)).toEqual({
      outbox_message_ids: ['msg-2'],
    });

    expect(global.fetch).toHaveBeenNthCalledWith(
      3,
      'http://example.test/v1/dev/peer-chat/outbox/12D3KooWlocal/promote',
      expect.objectContaining({ method: 'POST' })
    );
    expect(JSON.parse(global.fetch.mock.calls[2][1].body)).toEqual({
      outbox_message_ids: ['msg-3'],
    });

    expect(global.fetch).toHaveBeenNthCalledWith(
      4,
      'http://example.test/v1/dev/peer-chat/handsets/12D3KooWlocal/heartbeat',
      expect.objectContaining({ method: 'POST' })
    );
    expect(JSON.parse(global.fetch.mock.calls[3][1].body)).toEqual({
      display_name: 'HandsFree Peer Chat',
    });
  });

  it('fetches handset session state by peer id', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({ status: 'active' }),
    });

    const response = await getDevPeerChatHandsetSession('12D3KooWlocal');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://example.test/v1/dev/peer-chat/handsets/12D3KooWlocal',
      expect.objectContaining({ method: 'GET' })
    );
    expect(response.status).toBe('active');
  });

  it('fetches and clears persisted transport sessions', async () => {
    global.fetch
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({
          sessions: [
            {
              peer_id: '12D3KooWpeer',
              session_id: 'session-1',
              resume_token: 'resume-1',
              capabilities: ['chat'],
              updated_at_ms: 1234567890,
            },
          ],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValue({
          peer_id: '12D3KooWpeer',
          cleared: true,
        }),
      });

    const sessions = await getDevTransportSessions();
    const cleared = await deleteDevTransportSession('12D3KooWpeer');

    expect(global.fetch).toHaveBeenNthCalledWith(
      1,
      'http://example.test/v1/dev/transport-sessions',
      expect.objectContaining({ method: 'GET' })
    );
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      'http://example.test/v1/dev/transport-sessions/12D3KooWpeer',
      expect.objectContaining({ method: 'DELETE' })
    );
    expect(sessions.sessions[0].peer_id).toBe('12D3KooWpeer');
    expect(sessions.sessions[0].updated_at_ms).toBe(1234567890);
    expect(cleared.cleared).toBe(true);
  });

  it('propagates backend detail messages for peer chat failures', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      json: jest.fn().mockResolvedValue({
        detail: { message: 'dev mode required' },
      }),
    });

    await expect(getDevPeerChatOutboxStatus('12D3KooWlocal')).rejects.toThrow('dev mode required');
  });
});
