import fs from 'node:fs';
import path from 'node:path';
import {
  DISPLAY_WIDGET_BRIDGE_OPERATIONS,
  MOBILE_ORB_BRIDGE_OPERATIONS,
  TASK_STATUS_SERVICE_INTERFACE,
  mcpServiceDescriptorRef,
} from '../metaGlassesOrbDescriptors';
import {
  MetaGlassesMobileOrbBridge,
  actionItemFromDisplayWidgetAction,
  normalizeDisplayWidgetMobileAction,
} from '../metaGlassesMobileOrbBridge';

const MOBILE_SPEC_PATH = path.resolve(
  __dirname,
  '../../../../spec/meta_glasses_mobile_orb_bridge_interface.json'
);

const DISPLAY_SPEC_PATH = path.resolve(
  __dirname,
  '../../../../spec/meta_glasses_display_widget_orb_interface.json'
);

describe('MetaGlassesMobileOrbBridge', () => {
  it('keeps mobile and display descriptor operation lists aligned with spec artifacts', () => {
    const mobileDescriptor = JSON.parse(fs.readFileSync(MOBILE_SPEC_PATH, 'utf8'));
    const displayDescriptor = JSON.parse(fs.readFileSync(DISPLAY_SPEC_PATH, 'utf8'));

    expect(mobileDescriptor.name).toBe('mobile_orb_bridge');
    expect(mobileDescriptor.namespace).toBe('handsfree.meta_glasses.mobile');
    expect(mobileDescriptor.methods.map((method) => method.name)).toEqual(
      MOBILE_ORB_BRIDGE_OPERATIONS
    );

    expect(displayDescriptor.name).toBe('display_widget_bridge');
    expect(displayDescriptor.methods.map((method) => method.name)).toEqual(
      DISPLAY_WIDGET_BRIDGE_OPERATIONS
    );

    const bindServiceMethod = mobileDescriptor.methods.find((method) => method.name === 'bind_service');
    expect(bindServiceMethod.inputSchema.properties.service_descriptor.properties.metadata.properties)
      .toEqual(expect.objectContaining({
        server_family: { type: 'string' },
        mcp_server_family: { type: 'string' },
        tool_name: { type: 'string' },
        default_tool_name: { type: 'string' },
        provider_name: { type: 'string' },
      }));
  });

  it('registers the phone as an ORB edge node with DAT capabilities', async () => {
    const backend = {
      registerEdgeCapabilities: jest.fn(async (payload) => ({
        edge_session_id: 'edge-session-1',
        accepted_interface_cids: payload.local_interface_cids,
        policy_cid: 'sha256:policy',
        expires_at: '2026-05-23T13:00:00Z',
      })),
    };
    const bridge = new MetaGlassesMobileOrbBridge({
      backend,
      platform: 'ios',
      device: {
        deviceId: 'AA:BB',
        deviceName: 'Meta Ray-Ban Display',
      },
      localInterfaceCids: ['sha256:mobile', 'sha256:display'],
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    const result = await bridge.registerEdgeCapabilities({
      capabilities: {
        session: true,
        audio: true,
        display: true,
        displayVideo: true,
      },
    });

    expect(backend.registerEdgeCapabilities).toHaveBeenCalledWith({
      edge_id: 'handsfree-mobile-orb-edge',
      platform: 'ios',
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
      descriptors: [
        expect.objectContaining({ interface_cid: 'sha256:mobile' }),
        expect.objectContaining({ interface_cid: 'sha256:display' }),
      ],
    });
    expect(result.response).toMatchObject({
      edge_session_id: 'edge-session-1',
      policy_cid: 'sha256:policy',
      edge_id: 'handsfree-mobile-orb-edge',
      platform: 'ios',
      device_id: 'AA:BB',
      registered_at: '2026-05-23T12:00:00.000Z',
    });
    expect(bridge.getEdgeSession().edge_session_id).toBe('edge-session-1');
  });

  it('builds canonical MCP service descriptor refs with routing metadata', () => {
    expect(mcpServiceDescriptorRef(TASK_STATUS_SERVICE_INTERFACE, 'sha256:task-service')).toEqual(
      expect.objectContaining({
        interface_cid: 'sha256:task-service',
        metadata: {
          server_family: 'ipfs_datasets',
          tool_name: 'tools_dispatch',
          provider_name: 'ipfs_datasets_mcp',
        },
      })
    );
  });

  it('restores, persists, diagnoses, and clears edge session state through an injected store', async () => {
    const edgeSessionStore = {
      load: jest.fn(async () => ({
        edge_session_id: 'edge-session-restored',
        edge_id: 'handsfree-mobile-orb-edge',
        platform: 'ios',
        policy_cid: 'sha256:restored-policy',
        accepted_interface_cids: ['sha256:mobile'],
        dat_capabilities: {
          session: true,
          display: true,
        },
        registered_at: '2026-05-23T11:00:00.000Z',
      })),
      save: jest.fn(async (session) => session),
      clear: jest.fn(async () => undefined),
    };
    const orbStateStore = {
      load: jest.fn(async () => ({
        edge_session_id: 'edge-session-restored',
        bindings: [
          {
            binding_handle: 'binding-restored',
            service_interface_cid: 'sha256:task-service',
            operation: 'get_task_status',
            transport: 'mcp-server',
            orb_binding: {
              service_id: 'task_status_service',
              operation: 'get_task_status',
              transport: 'mcp-server',
            },
          },
        ],
        subscriptions: [
          {
            subscription_id: 'subscription-restored',
            binding_handle: 'binding-restored',
            operation: 'get_task_status',
            stream: 'task-status',
            generation_key: 'binding-restored:get_task_status:task-status',
          },
        ],
      })),
      save: jest.fn(async (state) => state),
      clear: jest.fn(async () => undefined),
    };
    const bridge = new MetaGlassesMobileOrbBridge({
      edgeSessionStore,
      orbStateStore,
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    await expect(bridge.restoreEdgeSession()).resolves.toEqual(
      expect.objectContaining({
        edge_session_id: 'edge-session-restored',
        policy_cid: 'sha256:restored-policy',
        dat_capabilities: expect.objectContaining({
          session: true,
          display: true,
          audio: false,
        }),
      })
    );
    expect(bridge.getDiagnostics()).toEqual(
      expect.objectContaining({
        registered: true,
        edge_session_id: 'edge-session-restored',
        policy_cid: 'sha256:restored-policy',
        bindings_count: 1,
        subscriptions_count: 1,
        events_count: 0,
      })
    );
    expect(orbStateStore.load).toHaveBeenCalled();
    expect(bridge.getDiagnostics().subscriptions[0]).toEqual(
      expect.objectContaining({
        subscription_id: 'subscription-restored',
        binding_handle: 'binding-restored',
        stream: 'task-status',
      })
    );

    await bridge.registerEdgeCapabilities({
      capabilities: {
        session: true,
        audio: true,
        display: true,
      },
    });
    expect(edgeSessionStore.save).toHaveBeenCalledWith(
      expect.objectContaining({
        edge_session_id: expect.stringContaining('local:edge-session'),
        registered_at: '2026-05-23T12:00:00.000Z',
      })
    );
    expect(orbStateStore.save).toHaveBeenCalledWith(
      expect.objectContaining({
        edge_session_id: expect.stringContaining('local:edge-session'),
        bindings: [],
        subscriptions: [],
      })
    );

    await bridge.clearEdgeSession();
    expect(edgeSessionStore.clear).toHaveBeenCalled();
    expect(orbStateStore.clear).toHaveBeenCalled();
    expect(bridge.getDiagnostics()).toEqual(
      expect.objectContaining({
        registered: false,
        edge_session_id: null,
        bindings_count: 0,
        subscriptions_count: 0,
        events_count: 0,
      })
    );
  });

  it('normalizes glasses events, binds a service, invokes it, and dispatches a display action', async () => {
    const localActionExecutor = jest.fn(async ({ actionItem }) => ({
      handled: true,
      message: 'Widget rendered.',
      actionId: actionItem.id,
      payload: actionItem.params.display_widget_action,
    }));
    const backend = {
      registerEdgeCapabilities: jest.fn(async () => ({
        edge_session_id: 'edge-session-1',
        accepted_interface_cids: ['sha256:mobile', 'sha256:display'],
        policy_cid: 'sha256:policy',
      })),
      publishGlassesEvent: jest.fn(async (payload) => ({
        event_cid: 'sha256:event',
        accepted: true,
        routed_operations: ['invoke_service'],
        receipt_cid: 'sha256:event-receipt',
      })),
      bindService: jest.fn(async () => ({
        binding_handle: 'binding-task-status',
        transport: 'mcp-server',
        granted_capabilities: ['tasks/read'],
        policy_decision: {
          outcome: 'permit',
          reasons: ['trusted service descriptor'],
        },
      })),
      invokeService: jest.fn(async () => ({
        ok: true,
        service_result: {
          title: 'Sync dataset',
          progress: 0.42,
        },
        output_refs: ['sha256:task-status'],
        provenance_refs: ['sha256:service'],
        receipt_cid: 'sha256:service-receipt',
        display_widget_action: {
          type: 'mobile_render_display_widget',
          operation: 'render_widget',
          descriptor_cid: 'sha256:display',
          interface_cid: 'sha256:display',
          widget_id: 'task-progress-active',
          widget_cid: 'sha256:widget',
          manifest: {
            widget_id: 'task-progress-active',
            widget_cid: 'sha256:widget',
            state: { values: { title: 'Sync dataset', progress: 0.42 } },
          },
          policy_decision: {
            outcome: 'permit',
            reasons: ['service result permitted'],
          },
          fallback: {
            render_path: 'mobile-card',
            message: 'Display unavailable. Showing task status on phone.',
          },
        },
      })),
      dispatchGlassesResponse: jest.fn(async (payload) => ({
        dispatched_actions: [],
        display_widget_action: payload.result.display_widget_action,
        spoken_text: null,
        receipt_cid: 'sha256:dispatch-receipt',
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
          orb_binding: {
            service_id: 'task_status_service',
          },
        },
      })),
    };
    const bridge = new MetaGlassesMobileOrbBridge({
      backend,
      localActionExecutor,
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    await bridge.registerEdgeCapabilities({
      capabilities: {
        session: true,
        display: true,
        audio: true,
      },
    });
    const result = await bridge.routeEventToService({
      eventType: 'captouch',
      eventPayload: {
        gesture: 'tap',
        intent: 'show task status',
      },
      serviceInterfaceCid: 'sha256:task-service',
      serviceDescriptor: mcpServiceDescriptorRef(TASK_STATUS_SERVICE_INTERFACE, 'sha256:task-service'),
      serviceOperation: 'get_task_status',
      serviceArguments: {
        task_id: 'task-123',
      },
      correlationId: 'corr-task-status',
      subscribeUpdates: true,
      updateStream: 'task-status',
    });

    expect(backend.publishGlassesEvent).toHaveBeenCalledWith({
      edge_session_id: 'edge-session-1',
      event_type: 'captouch',
      payload: {
        gesture: 'tap',
        intent: 'show task status',
      },
      correlation_id: 'corr-task-status',
      observed_at: '2026-05-23T12:00:00.000Z',
    });
    expect(backend.bindService).toHaveBeenCalledWith({
      edge_session_id: 'edge-session-1',
      service_interface_cid: 'sha256:task-service',
      service_descriptor: mcpServiceDescriptorRef(TASK_STATUS_SERVICE_INTERFACE, 'sha256:task-service'),
      operation: 'get_task_status',
      transport_preference: 'mcp-server',
      user_intent: 'show task status',
    });
    expect(backend.invokeService).toHaveBeenCalledWith({
      binding_handle: 'binding-task-status',
      operation: 'get_task_status',
      arguments: { task_id: 'task-123' },
      glasses_context: {
        event_type: 'captouch',
        event_cid: 'sha256:event',
        payload: {
          gesture: 'tap',
          intent: 'show task status',
        },
      },
      correlation_id: 'corr-task-status',
      parent_receipt_cids: ['sha256:event-receipt'],
    });
    expect(backend.dispatchGlassesResponse).toHaveBeenCalledWith({
      edge_session_id: 'edge-session-1',
      result: expect.objectContaining({ receipt_cid: 'sha256:service-receipt' }),
      render_targets: ['display_widget', 'audio', 'mobile_card'],
      correlation_id: 'corr-task-status',
      parent_receipt_cids: ['sha256:event-receipt', 'sha256:service-receipt'],
    });
    expect(backend.subscribeServiceUpdates).toHaveBeenCalledWith({
      binding_handle: 'binding-task-status',
      operation: 'get_task_status',
      arguments: { task_id: 'task-123' },
      stream: 'task-status',
      correlation_id: 'corr-task-status',
    });
    expect(localActionExecutor).toHaveBeenCalledWith({
      actionItem: expect.objectContaining({
        id: 'mobile_render_display_widget',
        params: {
          display_widget_action: expect.objectContaining({
            correlation_id: 'corr-task-status',
            orb_receipt_cid: 'sha256:dispatch-receipt',
            widget_id: 'task-progress-active',
          }),
        },
      }),
      navigation: null,
    });
    expect(result.dispatched.localResults).toEqual([
      expect.objectContaining({
        handled: true,
        message: 'Widget rendered.',
        actionId: 'mobile_render_display_widget',
      }),
    ]);
    expect(result.binding.response.orb_binding).toEqual(
      expect.objectContaining({
        interface_cid: 'sha256:task-service',
        service_id: 'task_status_service',
        operation: 'get_task_status',
        transport: 'mcp-server',
        transport_binding: expect.objectContaining({
          metadata: expect.objectContaining({
            descriptor_kind: 'mcp-idl',
            provider_name: 'ipfs_datasets_mcp',
            server_family: 'ipfs_datasets',
            tool_name: 'tools_dispatch',
            interface_descriptor: expect.objectContaining({
              name: 'task_status_service',
              namespace: 'handsfree.services.tasks',
              metadata: {
                provider_name: 'ipfs_datasets_mcp',
                server_family: 'ipfs_datasets',
                tool_name: 'tools_dispatch',
              },
            }),
          }),
        }),
      })
    );
    expect(result.invoked.response.service_result.orb_binding).toEqual(
      result.binding.response.orb_binding
    );
    expect(bridge.getDiagnostics().bindings[0]).toEqual(
      expect.objectContaining({
        service_id: 'task_status_service',
        operation: 'get_task_status',
        descriptor_cid: expect.stringContaining('local:mcp-interface'),
      })
    );
    expect(result.subscription.response.subscription).toEqual(
      expect.objectContaining({
        subscription_id: 'sha256:subscription',
        binding_handle: 'binding-task-status',
        operation: 'get_task_status',
        stream: 'task-status',
        status: 'active',
      })
    );
    expect(bridge.getDiagnostics().subscriptions[0]).toEqual(
      expect.objectContaining({
        subscription_id: 'sha256:subscription',
        binding_handle: 'binding-task-status',
        operation: 'get_task_status',
        stream: 'task-status',
        service_id: 'task_status_service',
      })
    );
    expect(bridge.getEventLog()).toEqual([
      expect.objectContaining({
        event_type: 'captouch',
        event_cid: 'sha256:event',
        receipt_cid: 'sha256:event-receipt',
      }),
    ]);
  });

  it('normalizes display widget actions into existing mobile local-action contract', () => {
    const payload = normalizeDisplayWidgetMobileAction({
      operation: 'update_widget',
      descriptor_cid: 'sha256:display',
      widget_id: 'task-progress-active',
      patch: { progress: 0.5 },
      correlation_id: 'corr-update',
    });

    expect(payload).toMatchObject({
      contract: 'handsfree.meta-glasses/display-widget-action@0.1.0',
      type: 'mobile_update_display_widget',
      action: 'update',
      operation: 'update_widget',
      descriptor_cid: 'sha256:display',
      interface_cid: 'sha256:display',
      widget_id: 'task-progress-active',
      patch: { progress: 0.5 },
      correlation_id: 'corr-update',
      policy_decision: {
        outcome: 'allow',
        metadata: expect.objectContaining({
          remote_client_policy_contract: false,
        }),
      },
      control_surface_contract_ref: 'control_surface_contract:hallucinate-app:remote-client',
      normalized_intent: expect.objectContaining({
        method: 'update_widget',
      }),
      mediation_receipt: expect.objectContaining({
        policy_decision: expect.objectContaining({
          outcome: 'allow',
        }),
      }),
    });

    expect(actionItemFromDisplayWidgetAction(payload)).toEqual({
      id: 'mobile_update_display_widget',
      label: 'mobile_update_display_widget',
      phrase: 'mobile_update_display_widget',
      params: {
        display_widget_action: payload,
      },
      mobile_payload: payload,
    });
  });

  it('reuses restored service bindings and subscriptions for matching routes', async () => {
    const backend = {
      registerEdgeCapabilities: jest.fn(async () => ({
        edge_session_id: 'edge-session-1',
        accepted_interface_cids: ['sha256:mobile', 'sha256:display'],
        policy_cid: 'sha256:policy',
      })),
      publishGlassesEvent: jest.fn(async () => ({
        event_cid: 'sha256:event',
        accepted: true,
        routed_operations: ['invoke_service'],
        receipt_cid: 'sha256:event-receipt',
      })),
      bindService: jest.fn(),
      invokeService: jest.fn(async () => ({
        ok: true,
        service_result: {},
        output_refs: [],
        provenance_refs: [],
        receipt_cid: 'sha256:invoke-receipt',
        follow_up_actions: [],
      })),
      subscribeServiceUpdates: jest.fn(),
      dispatchGlassesResponse: jest.fn(async () => ({
        dispatched_actions: [],
        display_widget_action: null,
        spoken_text: null,
        receipt_cid: 'sha256:dispatch-receipt',
      })),
    };
    const bridge = new MetaGlassesMobileOrbBridge({
      backend,
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    await bridge.registerEdgeCapabilities({ capabilities: { session: true } });
    bridge.hydrateOrbState({
      edge_session_id: 'edge-session-1',
      bindings: [
        {
          binding_handle: 'binding-restored',
          service_interface_cid: 'sha256:task-service',
          operation: 'get_task_status',
          transport: 'mcp-server',
          orb_binding: {
            interface_cid: 'sha256:task-service',
            service_id: 'task_status_service',
            operation: 'get_task_status',
            transport: 'mcp-server',
          },
        },
      ],
      subscriptions: [
        {
          subscription_id: 'subscription-restored',
          binding_handle: 'binding-restored',
          operation: 'get_task_status',
          stream: 'task-status',
          generation_key: 'binding-restored:get_task_status:task-status',
        },
      ],
    });

    const result = await bridge.routeEventToService({
      eventType: 'captouch',
      eventPayload: { intent: 'show task status' },
      serviceInterfaceCid: 'sha256:task-service',
      serviceOperation: 'get_task_status',
      serviceArguments: { task_id: 'task-123' },
      correlationId: 'corr-task-status',
      subscribeUpdates: true,
      updateStream: 'task-status',
    });

    expect(backend.bindService).not.toHaveBeenCalled();
    expect(backend.subscribeServiceUpdates).not.toHaveBeenCalled();
    expect(backend.invokeService).toHaveBeenCalledWith(
      expect.objectContaining({
        binding_handle: 'binding-restored',
        operation: 'get_task_status',
      })
    );
    expect(result.binding.reused).toBe(true);
    expect(result.subscription.reused).toBe(true);
    expect(result.subscription.response.subscription_id).toBe('subscription-restored');
  });

  it('rebinding clears stale restored bindings when backend no longer knows them', async () => {
    const orbStateStore = {
      load: jest.fn(),
      save: jest.fn(async (state) => state),
      clear: jest.fn(),
    };
    const backend = {
      registerEdgeCapabilities: jest.fn(async () => ({
        edge_session_id: 'edge-session-1',
        accepted_interface_cids: ['sha256:mobile', 'sha256:display'],
        policy_cid: 'sha256:policy',
      })),
      publishGlassesEvent: jest.fn(async () => ({
        event_cid: 'sha256:event',
        accepted: true,
        routed_operations: ['invoke_service'],
        receipt_cid: 'sha256:event-receipt',
      })),
      bindService: jest.fn(async () => ({
        binding_handle: 'binding-fresh',
        transport: 'mcp-server',
        granted_capabilities: [],
        policy_decision: { outcome: 'permit' },
      })),
      invokeService: jest
        .fn()
        .mockRejectedValueOnce(new Error('binding_not_found'))
        .mockResolvedValueOnce({
          ok: true,
          service_result: {},
          output_refs: [],
          provenance_refs: [],
          receipt_cid: 'sha256:invoke-receipt',
          follow_up_actions: [],
        }),
      subscribeServiceUpdates: jest.fn(async (payload) => ({
        subscription_id: 'subscription-fresh',
        receipt_cid: 'sha256:subscription-receipt',
        generation_key: `${payload.binding_handle}:${payload.operation}:${payload.stream}`,
      })),
      dispatchGlassesResponse: jest.fn(async () => ({
        dispatched_actions: [],
        display_widget_action: null,
        spoken_text: null,
        receipt_cid: 'sha256:dispatch-receipt',
      })),
    };
    const bridge = new MetaGlassesMobileOrbBridge({
      backend,
      orbStateStore,
      now: () => new Date('2026-05-23T12:00:00Z'),
    });

    await bridge.registerEdgeCapabilities({ capabilities: { session: true } });
    bridge.hydrateOrbState({
      edge_session_id: 'edge-session-1',
      bindings: [
        {
          binding_handle: 'binding-stale',
          service_interface_cid: 'sha256:task-service',
          operation: 'get_task_status',
        },
      ],
      subscriptions: [
        {
          subscription_id: 'subscription-stale',
          binding_handle: 'binding-stale',
          operation: 'get_task_status',
          stream: 'task-status',
        },
      ],
    });

    const result = await bridge.routeEventToService({
      eventType: 'captouch',
      eventPayload: { intent: 'show task status' },
      serviceInterfaceCid: 'sha256:task-service',
      serviceDescriptor: mcpServiceDescriptorRef(TASK_STATUS_SERVICE_INTERFACE, 'sha256:task-service'),
      serviceOperation: 'get_task_status',
      serviceArguments: { task_id: 'task-123' },
      correlationId: 'corr-task-status',
      subscribeUpdates: true,
      updateStream: 'task-status',
    });

    expect(backend.bindService).toHaveBeenCalledTimes(1);
    expect(backend.invokeService).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ binding_handle: 'binding-stale' })
    );
    expect(backend.invokeService).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ binding_handle: 'binding-fresh' })
    );
    expect(result.binding.response.binding_handle).toBe('binding-fresh');
    expect(result.subscription.response.subscription_id).toBe('subscription-fresh');
    expect(bridge.getDiagnostics()).toEqual(
      expect.objectContaining({
        bindings_count: 1,
        subscriptions_count: 1,
        bindings: [expect.objectContaining({ binding_handle: 'binding-fresh' })],
      })
    );
    expect(orbStateStore.save).toHaveBeenCalledWith(
      expect.objectContaining({
        bindings: [],
        subscriptions: [],
      })
    );
  });

  it('rejects unknown event types before they reach the backend', async () => {
    const bridge = new MetaGlassesMobileOrbBridge();
    await bridge.registerEdgeCapabilities({ capabilities: { session: true } });

    await expect(
      bridge.publishGlassesEvent('unsupported_event', {})
    ).rejects.toThrow('Unsupported Meta glasses event type');
  });
});
