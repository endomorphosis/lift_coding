import {
  createMetaGlassesMobileOrbRuntime,
  isMetaGlassesOrbEdgeSessionUsable,
} from '../metaGlassesMobileOrbRuntime';

function createBackend() {
  return {
    registerEdgeCapabilities: jest.fn(async (payload) => ({
      edge_session_id: 'edge-session-1',
      accepted_interface_cids: payload.local_interface_cids,
      policy_cid: 'sha256:policy',
      expires_at: null,
    })),
    publishGlassesEvent: jest.fn(async () => ({
      event_cid: 'sha256:event',
      accepted: true,
      routed_operations: ['bind_service', 'invoke_service'],
      receipt_cid: 'sha256:event-receipt',
    })),
    bindService: jest.fn(async () => ({
      binding_handle: 'binding-task-status',
      transport: 'mcp-server',
      granted_capabilities: [],
      policy_decision: { outcome: 'permit', reasons: ['ok'] },
    })),
    invokeService: jest.fn(async () => ({
      ok: true,
      service_result: { status: 'running' },
      output_refs: ['sha256:task-status'],
      provenance_refs: ['sha256:task-service'],
      receipt_cid: 'sha256:invoke-receipt',
      display_widget_action: {
        type: 'mobile_render_display_widget',
        operation: 'render_widget',
        descriptor_cid: 'sha256:display',
        widget_id: 'task-progress-active',
        widget_cid: 'sha256:widget',
      },
      spoken_text: 'Task is running.',
    })),
    subscribeServiceUpdates: jest.fn(async (payload) => ({
      subscription_id: 'sha256:subscription',
      receipt_cid: 'sha256:subscription-receipt',
      generation_key: `${payload.binding_handle}:${payload.operation}:${payload.stream}`,
      subscription: {
        ...payload,
        subscription_id: 'sha256:subscription',
        receipt_cid: 'sha256:subscription-receipt',
        generation_key: `${payload.binding_handle}:${payload.operation}:${payload.stream}`,
        status: 'active',
      },
    })),
    dispatchGlassesResponse: jest.fn(async (payload) => ({
      dispatched_actions: [],
      display_widget_action: payload.result.display_widget_action,
      spoken_text: payload.result.spoken_text,
      receipt_cid: 'sha256:dispatch-receipt',
    })),
    revokeBinding: jest.fn(),
    getDiagnostics: jest.fn(async (payload) => ({
      edge_session_id: payload.edge_session_id,
      events_count: 1,
      bindings_count: 1,
      subscriptions_count: 1,
    })),
  };
}

describe('Meta glasses mobile ORB runtime', () => {
  it('checks whether persisted edge sessions are usable', () => {
    const now = () => new Date('2026-05-23T12:00:00Z');

    expect(
      isMetaGlassesOrbEdgeSessionUsable({
        edge_session_id: 'edge',
        policy_cid: 'sha256:policy',
      }, now)
    ).toBe(true);
    expect(
      isMetaGlassesOrbEdgeSessionUsable({
        edge_session_id: 'edge',
        policy_cid: 'sha256:policy',
        expires_at: '2026-05-23T11:59:00Z',
      }, now)
    ).toBe(false);
  });

  it('restores a persisted edge session before registering a new one', async () => {
    const backend = createBackend();
    const edgeSessionStore = {
      load: jest.fn(async () => ({
        edge_session_id: 'edge-session-restored',
        edge_id: 'handsfree-mobile-orb-edge',
        platform: 'ios',
        policy_cid: 'sha256:restored-policy',
        accepted_interface_cids: ['sha256:mobile'],
        dat_capabilities: { session: true, display: true },
      })),
      save: jest.fn(),
      clear: jest.fn(),
    };
    const orbStateStore = {
      load: jest.fn(async () => ({
        edge_session_id: 'edge-session-restored',
        bindings: [{ binding_handle: 'binding-restored' }],
        subscriptions: [],
      })),
      save: jest.fn(),
      clear: jest.fn(),
    };
    const runtime = createMetaGlassesMobileOrbRuntime({
      backend,
      edgeSessionStore,
      orbStateStore,
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    await expect(runtime.ensureRegistered()).resolves.toEqual(
      expect.objectContaining({
        restored: true,
        response: expect.objectContaining({
          edge_session_id: 'edge-session-restored',
          policy_cid: 'sha256:restored-policy',
        }),
      })
    );
    expect(backend.registerEdgeCapabilities).not.toHaveBeenCalled();
    expect(runtime.getDiagnostics()).toEqual(
      expect.objectContaining({
        registered: true,
        backend_kind: 'injected',
        edge_session_persistence: true,
        orb_state_persistence: true,
        edge_session_id: 'edge-session-restored',
        bindings_count: 1,
      })
    );
    expect(orbStateStore.load).toHaveBeenCalled();
  });

  it('force-registers and persists a new edge session', async () => {
    const backend = createBackend();
    const edgeSessionStore = {
      load: jest.fn(),
      save: jest.fn(async (session) => session),
      clear: jest.fn(),
    };
    const runtime = createMetaGlassesMobileOrbRuntime({
      backend,
      edgeSessionStore,
      orbStateStore: null,
      platform: 'android',
      device: { deviceId: 'AA:BB', deviceName: 'Meta Ray-Ban Display' },
      localInterfaceCids: ['sha256:mobile', 'sha256:display'],
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    await runtime.ensureRegistered({
      force: true,
      capabilities: {
        session: true,
        audio: true,
        display: true,
        displayVideo: true,
      },
    });

    expect(backend.registerEdgeCapabilities).toHaveBeenCalledWith({
      edge_id: 'handsfree-mobile-orb-edge',
      platform: 'android',
      device_id: 'AA:BB',
      device_model: 'Meta Ray-Ban Display',
      dat_capabilities: {
        session: true,
        camera: false,
        photoCapture: false,
        videoStream: false,
        audio: true,
        display: true,
        displayVideo: true,
        webAppDisplay: false,
      },
      local_interface_cids: ['sha256:mobile', 'sha256:display'],
      transport_preferences: ['local', 'http', 'websocket', 'mcp-server'],
      descriptors: expect.any(Array),
    });
    expect(edgeSessionStore.save).toHaveBeenCalledWith(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        registered_at: '2026-05-23T12:00:00.000Z',
      })
    );
    await expect(runtime.fetchBackendDiagnostics()).resolves.toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-1',
        events_count: 1,
        bindings_count: 1,
        subscriptions_count: 1,
      })
    );
    expect(backend.getDiagnostics).toHaveBeenCalledWith({
      edge_session_id: 'edge-session-1',
    });
  });

  it('auto-registers and routes a glasses event to a bound service', async () => {
    const backend = createBackend();
    const localActionExecutor = jest.fn(async ({ actionItem }) => ({
      handled: true,
      actionId: actionItem.id,
    }));
    const runtime = createMetaGlassesMobileOrbRuntime({
      backend,
      edgeSessionStore: null,
      orbStateStore: null,
      localActionExecutor,
      localInterfaceCids: ['sha256:mobile', 'sha256:display'],
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    const result = await runtime.routeGlassesEventToService({
      eventType: 'captouch',
      eventPayload: {
        gesture: 'tap',
        intent: 'show task status',
      },
      serviceInterfaceCid: 'sha256:task-service',
      serviceOperation: 'get_task_status',
      serviceArguments: {
        task_id: 'task-123',
      },
      correlationId: 'corr-task-status',
      subscribeUpdates: true,
      updateStream: 'task-status',
    });

    expect(backend.registerEdgeCapabilities).toHaveBeenCalled();
    expect(backend.publishGlassesEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        event_type: 'captouch',
        correlation_id: 'corr-task-status',
      })
    );
    expect(backend.bindService).toHaveBeenCalledWith(
      expect.objectContaining({
        service_interface_cid: 'sha256:task-service',
        operation: 'get_task_status',
      })
    );
    expect(localActionExecutor).toHaveBeenCalledWith({
      actionItem: expect.objectContaining({
        id: 'mobile_render_display_widget',
      }),
      navigation: null,
    });
    expect(result.dispatched.localResults).toEqual([
      { handled: true, actionId: 'mobile_render_display_widget' },
    ]);
    expect(backend.subscribeServiceUpdates).toHaveBeenCalledWith(
      expect.objectContaining({
        binding_handle: 'binding-task-status',
        operation: 'get_task_status',
        stream: 'task-status',
        correlation_id: 'corr-task-status',
      })
    );
    expect(result.subscription.response.subscription_id).toBe('sha256:subscription');
    expect(runtime.getDiagnostics()).toEqual(
      expect.objectContaining({
        subscriptions_count: 1,
        subscriptions: [
          expect.objectContaining({
            subscription_id: 'sha256:subscription',
            operation: 'get_task_status',
            stream: 'task-status',
          }),
        ],
      })
    );
  });
});
