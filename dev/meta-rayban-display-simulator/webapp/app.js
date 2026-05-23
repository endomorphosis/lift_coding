(function bootstrapTaskProgressWebapp() {
  const MANIFEST = {
    widget_id: 'org.handsfree.meta_glasses.task-progress-simulator@1.0.0',
    widget_cid: 'sha256:task-progress-simulator-fixture',
    descriptor_cid: 'sha256:display-widget-interface',
    orb_receipt_cid: 'sha256:simulator-receipt',
    correlation_id: 'simulator-task-progress',
    viewport: { width: 600, height: 600 },
    state: {
      title: 'Sync dataset',
      status: 'Running',
      summary: '42 percent complete. Indexing source records.',
      progress: 0.42,
    },
    regions: [
      {
        id: 'title',
        kind: 'text',
        x: 32,
        y: 28,
        width: 536,
        height: 92,
        text: 'Sync dataset',
        variant: 'title',
      },
      {
        id: 'status',
        kind: 'text',
        x: 32,
        y: 132,
        width: 536,
        height: 82,
        text: 'Running: 42 percent complete',
        variant: 'status',
      },
      {
        id: 'progress',
        kind: 'progress',
        x: 32,
        y: 232,
        width: 536,
        height: 90,
        value: 0.42,
        label: '42%',
      },
      {
        id: 'media-fallback',
        kind: 'media',
        x: 32,
        y: 342,
        width: 536,
        height: 86,
        fallback_text: 'Preview image unavailable on this display.',
      },
      {
        id: 'pause-task',
        kind: 'action',
        x: 32,
        y: 452,
        width: 252,
        height: 96,
        action_id: 'pause',
        label: 'Pause',
      },
      {
        id: 'dismiss-widget',
        kind: 'action',
        x: 316,
        y: 452,
        width: 252,
        height: 96,
        action_id: 'dismiss',
        label: 'Dismiss',
      },
    ],
    actions: [
      {
        id: 'pause',
        label: 'Pause',
        operation: 'activate',
        message: 'Pause requested.',
      },
      {
        id: 'dismiss',
        label: 'Dismiss',
        operation: 'clear_widget',
        message: 'Dismiss requested.',
      },
    ],
    focus_order: ['pause', 'dismiss'],
  };

  const TASK_SERVICE_INTERFACE_CID = 'handsfree.services.tasks.task_status_service@0.1.0';
  const TASK_SERVICE_DESCRIPTOR = {
    name: 'task_status_service',
    namespace: 'handsfree.services.tasks',
    version: '0.1.0',
    metadata: {
      server_family: 'ipfs_datasets',
      tool_name: 'tools_dispatch',
      provider_name: 'ipfs_datasets_mcp',
    },
    methods: [
      {
        name: 'pause_task',
        inputSchema: {
          type: 'object',
          properties: {
            task_id: { type: 'string' },
            action_id: { type: 'string' },
          },
        },
        outputSchema: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            display_widget_action: { type: 'object' },
            spoken_text: { type: 'string' },
          },
        },
      },
      {
        name: 'dismiss_widget',
        inputSchema: {
          type: 'object',
          properties: {
            task_id: { type: 'string' },
            action_id: { type: 'string' },
          },
        },
        outputSchema: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            display_widget_action: { type: 'object' },
            spoken_text: { type: 'string' },
          },
        },
      },
      {
        name: 'get_task_status',
        inputSchema: {
          type: 'object',
          properties: {
            task_id: { type: 'string' },
          },
        },
        outputSchema: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            display_widget_action: { type: 'object' },
            spoken_text: { type: 'string' },
          },
        },
      },
    ],
    errors: [
      {
        name: 'task_not_found',
        code: 404,
      },
    ],
    requires: [
      'mcp++/profile-a-idl',
      'mcp++/profile-b-cid-artifacts',
      'mcp++/invoke',
      'mcp++/receipts',
    ],
    compatibility: {
      viewport: MANIFEST.viewport,
      render_targets: ['display_widget', 'display_webapp', 'audio', 'mobile_card'],
    },
  };

  let focusIndex = 0;
  let toast = '';
  let toastTimer = null;
  const app = document.getElementById('app');
  const ORB_SESSION_STORAGE_KEY = 'handsfree:metaRaybanDisplayWebappOrbSession';
  const ORB_BINDINGS_STORAGE_KEY = 'handsfree:metaRaybanDisplayWebappOrbBindings';
  const ORB_SUBSCRIPTIONS_STORAGE_KEY = 'handsfree:metaRaybanDisplayWebappOrbSubscriptions';

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  function regionStyle(region) {
    return [
      `left:${Number(region.x)}px`,
      `top:${Number(region.y)}px`,
      `width:${Number(region.width)}px`,
      `height:${Number(region.height)}px`,
    ].join(';');
  }

  function renderProgress(region) {
    const value = Math.max(0, Math.min(1, Number(region.value || 0)));
    return [
      '<div class="progress-row">',
      `<span>${escapeHtml(region.label || `${Math.round(value * 100)}%`)}</span>`,
      '<span>progress</span>',
      '</div>',
      '<div class="progress-track">',
      `<div class="progress-fill" style="width:${Math.round(value * 100)}%"></div>`,
      '</div>',
    ].join('');
  }

  function renderRegion(region) {
    const focusedActionId = MANIFEST.focus_order[focusIndex];
    const kind = region.kind || 'text';
    const variant = region.variant || kind;
    const focused =
      kind === 'action' && region.action_id === focusedActionId
        ? ' data-focused="true"'
        : '';
    let body = '';

    if (kind === 'progress') {
      body = renderProgress(region);
    } else if (kind === 'media') {
      body = escapeHtml(region.fallback_text);
    } else if (kind === 'action') {
      body = escapeHtml(region.label || region.action_id);
    } else if (variant === 'title') {
      body = `<h1 class="title-text">${escapeHtml(region.text)}</h1>`;
    } else {
      body = `<p class="status-text">${escapeHtml(region.text)}</p>`;
    }

    return `<section class="region ${escapeHtml(kind)} ${escapeHtml(variant)}"${focused} style="${regionStyle(region)}">${body}</section>`;
  }

  function render() {
    app.innerHTML = [
      ...MANIFEST.regions.map(renderRegion),
      toast ? `<div class="toast">${escapeHtml(toast)}</div>` : '',
    ].join('');
  }

  function recordEvent(action) {
    const event = {
      schema: 'handsfree.meta-rayban-display/webapp-event',
      action_id: action.id,
      operation: action.operation,
      widget_id: MANIFEST.widget_id,
      widget_cid: MANIFEST.widget_cid,
      descriptor_cid: MANIFEST.descriptor_cid,
      orb_receipt_cid: MANIFEST.orb_receipt_cid,
      correlation_id: MANIFEST.correlation_id,
      recorded_at: new Date().toISOString(),
    };
    sessionStorage.setItem('handsfree:lastDisplayWebappEvent', JSON.stringify(event));
    return event;
  }

  async function postJson(path, payload) {
    const response = await fetch(path, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      let body = null;
      try {
        body = await response.json();
      } catch {
        body = null;
      }
      const error = new Error(`ORB bridge request failed: ${response.status}`);
      error.status = response.status;
      error.body = body;
      throw error;
    }
    return response.json();
  }

  function loadOrbSession() {
    try {
      const raw = sessionStorage.getItem(ORB_SESSION_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function saveOrbSession(session) {
    sessionStorage.setItem(ORB_SESSION_STORAGE_KEY, JSON.stringify(session));
  }

  function loadOrbBindings() {
    try {
      const raw = sessionStorage.getItem(ORB_BINDINGS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function saveOrbBinding(operation, binding) {
    sessionStorage.setItem(
      ORB_BINDINGS_STORAGE_KEY,
      JSON.stringify({
        ...loadOrbBindings(),
        [operation]: binding,
      })
    );
  }

  function loadOrbSubscriptions() {
    try {
      const raw = sessionStorage.getItem(ORB_SUBSCRIPTIONS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  function saveOrbSubscription(operation, subscription) {
    sessionStorage.setItem(
      ORB_SUBSCRIPTIONS_STORAGE_KEY,
      JSON.stringify({
        ...loadOrbSubscriptions(),
        [operation]: subscription,
      })
    );
  }

  function clearCachedOrbBinding(operation) {
    const bindings = loadOrbBindings();
    delete bindings[operation];
    sessionStorage.setItem(ORB_BINDINGS_STORAGE_KEY, JSON.stringify(bindings));

    const subscriptions = loadOrbSubscriptions();
    delete subscriptions[operation];
    sessionStorage.setItem(ORB_SUBSCRIPTIONS_STORAGE_KEY, JSON.stringify(subscriptions));
  }

  async function ensureOrbEdgeSession() {
    const existing = loadOrbSession();
    if (existing?.edge_session_id && existing?.policy_cid) {
      return existing;
    }

    const registered = await postJson('/v1/mobile/orb/register_edge_capabilities', {
      edge_id: 'handsfree-meta-rayban-display-webapp-preview',
      platform: 'simulator',
      device_model: 'Meta Ray-Ban Display Web App Preview',
      dat_capabilities: {
        session: true,
        audio: false,
        display: true,
        displayVideo: false,
        webAppDisplay: true,
      },
      local_interface_cids: [
        'handsfree.meta_glasses.mobile.mobile_orb_bridge@0.1.0',
        'handsfree.meta_glasses.display.display_widget_bridge@0.1.0',
        MANIFEST.descriptor_cid,
      ],
      transport_preferences: ['local', 'http', 'mcp-server'],
      descriptors: [
        {
          name: 'display_widget_bridge',
          namespace: 'handsfree.meta_glasses.display',
          version: '0.1.0',
          interface_cid: MANIFEST.descriptor_cid,
        },
      ],
    });
    saveOrbSession(registered);
    return registered;
  }

  async function publishOrbDisplayAction(eventPayload, edgeSession = null) {
    const activeEdgeSession = edgeSession || (await ensureOrbEdgeSession());
    const published = await postJson('/v1/mobile/orb/publish_glasses_event', {
      edge_session_id: activeEdgeSession.edge_session_id,
      event_type: 'display_action',
      payload: eventPayload,
      correlation_id: eventPayload.correlation_id,
      parent_receipt_cids: [eventPayload.orb_receipt_cid].filter(Boolean),
      observed_at: eventPayload.recorded_at,
    });
    sessionStorage.setItem(
      'handsfree:lastDisplayWebappOrbEvent',
      JSON.stringify(published)
    );
    return published;
  }

  function serviceOperationForAction(action) {
    if (action.id === 'pause') {
      return 'pause_task';
    }
    if (action.id === 'dismiss') {
      return 'dismiss_widget';
    }
    return 'get_task_status';
  }

  async function ensureTaskServiceBinding(edgeSession, operation, action) {
    const bindings = loadOrbBindings();
    if (bindings[operation]?.binding_handle) {
      return bindings[operation];
    }

    const binding = await postJson('/v1/mobile/orb/bind_service', {
      edge_session_id: edgeSession.edge_session_id,
      service_interface_cid: TASK_SERVICE_INTERFACE_CID,
      service_descriptor: TASK_SERVICE_DESCRIPTOR,
      operation,
      transport_preference: 'mcp-server',
      user_intent: action.message || `Run ${operation}`,
      policy_context: {
        surface: 'meta-rayban-display-webapp-preview',
        widget_id: MANIFEST.widget_id,
        widget_cid: MANIFEST.widget_cid,
        mcp_plus_plus_profiles: TASK_SERVICE_DESCRIPTOR.requires,
      },
    });
    saveOrbBinding(operation, binding);
    return binding;
  }

  async function subscribeTaskServiceUpdates(binding, operation, action) {
    const subscriptions = loadOrbSubscriptions();
    if (subscriptions[operation]?.subscription_id) {
      return subscriptions[operation];
    }

    const subscription = await postJson('/v1/mobile/orb/subscribe_service_updates', {
      binding_handle: binding.binding_handle,
      operation,
      arguments: {
        task_id: 'simulator-task-progress',
        action_id: action.id,
      },
      stream: 'task-progress',
      correlation_id: MANIFEST.correlation_id,
    });
    saveOrbSubscription(operation, subscription);
    sessionStorage.setItem(
      'handsfree:lastDisplayWebappOrbSubscription',
      JSON.stringify(subscription)
    );
    return subscription;
  }

  function displayWidgetOperationForAction(action) {
    if (action.id === 'dismiss') {
      return 'clear_widget';
    }
    return 'update_widget';
  }

  function buildDisplayWidgetAction(action, eventPayload) {
    return {
      operation: displayWidgetOperationForAction(action),
      descriptor_cid: MANIFEST.descriptor_cid,
      interface_cid: MANIFEST.descriptor_cid,
      widget_id: MANIFEST.widget_id,
      widget_cid: MANIFEST.widget_cid,
      correlation_id: eventPayload.correlation_id,
      activated_action_id: action.id,
      manifest: MANIFEST,
      state: {
        ...MANIFEST.state,
        last_action: action.id,
        status: action.id === 'pause' ? 'Pause requested' : 'Dismiss requested',
      },
      fallback: {
        render_path: 'display-webapp',
        message: action.message,
      },
    };
  }

  async function invokeTaskService(binding, operation, action, eventPayload, published) {
    const invoked = await postJson('/v1/mobile/orb/invoke_service', {
      binding_handle: binding.binding_handle,
      operation,
      arguments: {
        task_id: 'simulator-task-progress',
        action_id: action.id,
        source_event_cid: published.event_cid,
        display_widget_action: buildDisplayWidgetAction(action, eventPayload),
        spoken_text: action.message,
      },
      glasses_context: {
        surface: 'meta-rayban-display-webapp-preview',
        input: 'dpad-enter',
      },
      display_context: {
        viewport: MANIFEST.viewport,
        focus_order: MANIFEST.focus_order,
        focused_action_id: action.id,
      },
      correlation_id: eventPayload.correlation_id,
      parent_receipt_cids: [published.receipt_cid, eventPayload.orb_receipt_cid].filter(Boolean),
    });
    sessionStorage.setItem(
      'handsfree:lastDisplayWebappOrbInvocation',
      JSON.stringify(invoked)
    );
    return invoked;
  }

  async function dispatchOrbServiceResult(edgeSession, action, eventPayload, eventReceiptCid, invoked) {
    const dispatched = await postJson('/v1/mobile/orb/dispatch_glasses_response', {
      edge_session_id: edgeSession.edge_session_id,
      result: invoked,
      render_targets: ['display_webapp', 'display_widget', 'audio', 'mobile_card'],
      fallback: {
        render_path: 'display-webapp',
        message: action.message,
      },
      correlation_id: eventPayload.correlation_id,
      parent_receipt_cids: [eventReceiptCid, invoked.receipt_cid].filter(Boolean),
    });
    sessionStorage.setItem(
      'handsfree:lastDisplayWebappOrbDispatch',
      JSON.stringify(dispatched)
    );
    return dispatched;
  }

  async function runBoundTaskServiceFlow(edgeSession, operation, action, eventPayload, published) {
    const binding = await ensureTaskServiceBinding(edgeSession, operation, action);
    const subscription = await subscribeTaskServiceUpdates(binding, operation, action);
    const invoked = await invokeTaskService(
      binding,
      operation,
      action,
      eventPayload,
      published
    );
    return {
      binding,
      subscription,
      invoked,
    };
  }

  async function routeOrbDisplayAction(action, eventPayload) {
    const edgeSession = await ensureOrbEdgeSession();
    const published = await publishOrbDisplayAction(eventPayload, edgeSession);
    const operation = serviceOperationForAction(action);
    let serviceFlow;
    try {
      serviceFlow = await runBoundTaskServiceFlow(
        edgeSession,
        operation,
        action,
        eventPayload,
        published
      );
    } catch (error) {
      if (error?.status !== 404) {
        throw error;
      }
      clearCachedOrbBinding(operation);
      serviceFlow = await runBoundTaskServiceFlow(
        edgeSession,
        operation,
        action,
        eventPayload,
        published
      );
    }
    const dispatched = await dispatchOrbServiceResult(
      edgeSession,
      action,
      eventPayload,
      published.receipt_cid,
      serviceFlow.invoked
    );
    return {
      published,
      binding: serviceFlow.binding,
      subscription: serviceFlow.subscription,
      invoked: serviceFlow.invoked,
      dispatched,
    };
  }

  function showToast(message) {
    toast = message;
    if (toastTimer) {
      window.clearTimeout(toastTimer);
    }
    toastTimer = window.setTimeout(() => {
      toast = '';
      render();
    }, 1600);
    render();
  }

  function moveFocus(delta) {
    focusIndex =
      (focusIndex + delta + MANIFEST.focus_order.length) % MANIFEST.focus_order.length;
    render();
  }

  function activateFocused() {
    const actionId = MANIFEST.focus_order[focusIndex];
    const action = MANIFEST.actions.find((candidate) => candidate.id === actionId);
    if (!action) {
      return;
    }
    const eventPayload = recordEvent(action);
    routeOrbDisplayAction(action, eventPayload)
      .then((result) => {
        const cid = result.dispatched.receipt_cid || result.published.event_cid;
        showToast(`${action.message} ORB dispatch ${cid.slice(0, 18)}...`);
      })
      .catch(() => {
        showToast(`${action.message} Saved locally.`);
      });
    showToast(action.message);
  }

  app.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault();
      moveFocus(1);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault();
      moveFocus(-1);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      activateFocused();
    }
  });

  render();
  app.focus();
})();
