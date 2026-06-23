(function bootstrapSimulator(globalScope) {
  const DISPLAY_STATES = {
    ready: {
      supported: true,
      displayConnectionState: 'ready',
      displayLastStatus: 'ready',
      message: 'Display ready.',
    },
    unavailable: {
      supported: false,
      displayConnectionState: 'unavailable',
      displayLastStatus: 'unsupported',
      reason: 'dat_native_display_unavailable',
      requiredAction: 'use_display_webapp_or_mobile_card',
      message: 'Native DAT display unavailable. Use Web App preview or mobile fallback.',
    },
    disabled: {
      supported: false,
      displayConnectionState: 'disabled',
      displayLastStatus: 'disabled',
      reason: 'display_capability_disabled',
      requiredAction: 'enable_display_capability',
      message: 'Display capability is disabled for the simulated device session.',
    },
    unsupported: {
      supported: false,
      displayConnectionState: 'unsupported',
      displayLastStatus: 'unsupported',
      reason: 'display_capability_missing',
      requiredAction: 'select_display_capable_device',
      message: 'Selected device does not advertise display capability.',
    },
    firmware_update_required: {
      supported: false,
      displayConnectionState: 'update_required',
      displayLastStatus: 'firmware_update_required',
      reason: 'firmware_update_required',
      requiredAction: 'update_glasses_firmware',
      message: 'Glasses firmware must be updated before DAT display rendering.',
    },
    dat_app_update_required: {
      supported: false,
      displayConnectionState: 'update_required',
      displayLastStatus: 'dat_app_update_required',
      reason: 'dat_app_update_required',
      requiredAction: 'update_meta_ai_app',
      message: 'The paired phone app must support the display app model.',
    },
    lifecycle_error: {
      supported: false,
      displayConnectionState: 'lifecycle_error',
      displayLastStatus: 'lifecycle_error',
      reason: 'display_lifecycle_error',
      requiredAction: 'restart_device_session',
      message: 'The simulated display capability hit a lifecycle error.',
    },
  };

  const DEFAULT_MANIFEST = {
    schema: 'handsfree.meta-rayban-display/simulator-manifest',
    schema_version: '0.1.0',
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
      updated_at: '2026-05-23T12:00:00Z',
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
        fallback_text: 'Preview image unavailable on simulator fixture.',
        media: {
          type: 'image',
          uri: 'https://example.com/glasses-display/assets/task-progress.png',
          alt: 'Task progress preview',
        },
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
        result: {
          action: 'activate_display_widget_action',
          requiredAction: 'pause_task',
        },
      },
      {
        id: 'dismiss',
        label: 'Dismiss',
        operation: 'clear_widget',
        result: {
          action: 'clear_display_widget',
          requiredAction: 'dismiss_widget',
        },
      },
    ],
    focus_order: ['pause', 'dismiss'],
    fallback: {
      reason: 'dat_native_display_unavailable',
      render_path: 'display-webapp',
      message: 'Native display unavailable. Showing simulator preview.',
    },
  };

  const REMOTE_TERMINAL_CONTRACT_ID = 'handsfree.meta-glasses/remote-terminal@0.1.0';

  const DEFAULT_COMMAND_SESSION = {
    schema: 'handsfree.meta-rayban-display/browser-simulator-session',
    schema_version: '0.1.0',
    session_model: 'handsfree.virtual-desktop-session',
    command_model: 'handsfree.command-session@0.1.0',
    session_identity: {
      session_id: 'meta-rayban-browser-session',
      phone_host_id: 'browser-simulator-phone-host',
      desktop_id: 'mobile-hosted-virtual-desktop',
    },
    host_mode: 'mobile_hosted',
    pairing: {
      state: 'unpaired',
      requires_paired_hardware: false,
      fallback_when_unpaired: 'mobile-card',
    },
    surfaces: {
      display: {
        endpoint_id: 'meta_glasses_display_widget',
        state: 'display_ready',
        render_path: 'display-webapp',
        fallback_render_path: 'mobile-card',
      },
      audio: {
        input_endpoint_id: 'meta_glasses_audio_input',
        output_endpoint_id: 'meta_glasses_audio_output',
        command_state: 'ready',
        tts_state: 'ready',
        fallback_input_endpoint_id: 'phone_microphone',
        fallback_output_endpoint_id: 'phone_speaker',
      },
    },
    command_queue: [],
  };

  const REMOTE_TERMINAL_ENDPOINTS = [
    {
      endpoint_id: 'meta_glasses_audio_input',
      channel: 'audio',
      direction: 'input',
      role: 'command_capture',
      handler_ref: 'mobile.modules.expo_glasses_audio:record_audio',
      fallback_target: 'phone_microphone',
      contract_id: REMOTE_TERMINAL_CONTRACT_ID,
    },
    {
      endpoint_id: 'meta_glasses_audio_output',
      channel: 'audio',
      direction: 'output',
      role: 'tts_playback',
      handler_ref: 'mobile.modules.expo_glasses_audio:play_audio',
      fallback_target: 'phone_speaker',
      contract_id: REMOTE_TERMINAL_CONTRACT_ID,
    },
    {
      endpoint_id: 'meta_glasses_display_widget',
      channel: 'display',
      direction: 'output',
      role: 'display_widget_rendering',
      handler_ref: 'handsfree.meta_glasses_mobile_orb_runtime:invoke_mobile_orb_runtime_binding',
      fallback_target: 'display_webapp_or_mobile_card',
      contract_id: REMOTE_TERMINAL_CONTRACT_ID,
    },
  ];

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function isObject(value) {
    return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function normalizeManifest(input) {
    const manifest = isObject(input) ? clone(input) : clone(DEFAULT_MANIFEST);
    manifest.viewport = isObject(manifest.viewport)
      ? manifest.viewport
      : { width: 600, height: 600 };
    manifest.regions = Array.isArray(manifest.regions) ? manifest.regions : [];
    manifest.actions = Array.isArray(manifest.actions) ? manifest.actions : [];
    manifest.focus_order = Array.isArray(manifest.focus_order)
      ? manifest.focus_order.filter((item) => typeof item === 'string' && item.length > 0)
      : manifest.actions.map((action) => action.id).filter(Boolean);
    manifest.fallback = isObject(manifest.fallback) ? manifest.fallback : {};
    manifest.state = isObject(manifest.state) ? manifest.state : {};
    return manifest;
  }

  function normalizeCommandSession(input) {
    const session = isObject(input) ? clone(input) : clone(DEFAULT_COMMAND_SESSION);
    const defaults = clone(DEFAULT_COMMAND_SESSION);
    session.schema = session.schema || defaults.schema;
    session.schema_version = session.schema_version || defaults.schema_version;
    session.session_model = session.session_model || defaults.session_model;
    session.command_model = session.command_model || defaults.command_model;
    session.host_mode = session.host_mode || defaults.host_mode;
    session.session_identity = {
      ...defaults.session_identity,
      ...(isObject(session.session_identity) ? session.session_identity : {}),
    };
    session.pairing = {
      ...defaults.pairing,
      ...(isObject(session.pairing) ? session.pairing : {}),
    };
    session.surfaces = {
      display: {
        ...defaults.surfaces.display,
        ...(isObject(session.surfaces?.display) ? session.surfaces.display : {}),
      },
      audio: {
        ...defaults.surfaces.audio,
        ...(isObject(session.surfaces?.audio) ? session.surfaces.audio : {}),
      },
    };
    session.command_queue = Array.isArray(session.command_queue)
      ? session.command_queue
      : [];
    return session;
  }

  function buildMobileHostedSession(input, manifestInput) {
    const session = normalizeCommandSession(input);
    const manifest = normalizeManifest(manifestInput || DEFAULT_MANIFEST);
    return {
      ...session,
      widget_refs: {
        widget_id: manifest.widget_id,
        widget_cid: manifest.widget_cid,
        descriptor_cid: manifest.descriptor_cid,
        orb_receipt_cid: manifest.orb_receipt_cid,
        correlation_id: manifest.correlation_id,
      },
      terminal_constraints: {
        hardware_required: false,
        input_channels: ['audio_command'],
        output_channels: ['visual_status', 'tts'],
        permitted_actions: [
          'confirm',
          'cancel',
          'retry_pairing',
          'switch_to_phone_preview',
          'open_desktop_offload_status',
        ],
      },
    };
  }

  function buildRemoteTerminalRoute(sessionInput, payload) {
    const session = normalizeCommandSession(sessionInput);
    return {
      contract_id: REMOTE_TERMINAL_CONTRACT_ID,
      surface_id: 'mobile_glasses',
      terminal_kind: 'meta_glasses_remote_terminal',
      render_targets: ['audio', 'display'],
      endpoints: clone(REMOTE_TERMINAL_ENDPOINTS),
      session_contract: {
        session_id: session.session_identity.session_id,
        phone_host_id: session.session_identity.phone_host_id,
        host_mode: 'mobile_hosted',
        terminal_constraints: {
          hardware_required: false,
          input_channels: ['audio_command'],
          output_channels: ['visual_status', 'tts'],
          permitted_actions: [
            'confirm',
            'cancel',
            'retry_pairing',
            'switch_to_phone_preview',
            'open_desktop_offload_status',
          ],
        },
        pairing: session.pairing,
        audio_command_input: {
          state: session.surfaces.audio.command_state,
          endpoint_id: session.surfaces.audio.input_endpoint_id,
          fallback_endpoint_id: session.surfaces.audio.fallback_input_endpoint_id,
        },
        visual_status_output: {
          state: session.surfaces.display.state,
          endpoint_id: session.surfaces.display.endpoint_id,
          fallback_render_path: session.surfaces.display.fallback_render_path,
        },
        disconnection_handling: {
          policy: 'degrade_to_mobile_card',
          on_pairing_lost: [
            'mark_display_unavailable',
            'continue_mobile_session',
            'surface_reconnect_action',
          ],
          fallback_render_path: session.surfaces.display.fallback_render_path,
        },
      },
      payload: clone(payload || {}),
    };
  }

  function buildSessionCommand(commandType, payload, sessionInput, manifestInput) {
    const session = buildMobileHostedSession(sessionInput, manifestInput);
    const manifest = normalizeManifest(manifestInput || DEFAULT_MANIFEST);
    const commandId =
      payload?.command_id ||
      `${commandType || 'command'}-${session.session_identity.session_id}-${Date.now()}`;
    const targetSurface = payload?.target_surface || (
      commandType === 'audio_command' || commandType === 'tts_output' ? 'audio' : 'display'
    );
    const command = {
      schema: 'handsfree.meta-rayban-display/session-command',
      schema_version: '0.1.0',
      command_id: commandId,
      command_type: commandType || 'render_display',
      target_surface: targetSurface,
      session_id: session.session_identity.session_id,
      phone_host_id: session.session_identity.phone_host_id,
      desktop_id: session.session_identity.desktop_id,
      widget_refs: session.widget_refs,
      payload: clone(payload || {}),
      requested_at: payload?.requested_at || new Date().toISOString(),
    };
    const route = buildRemoteTerminalRoute(session, command);
    return {
      ...command,
      route,
      display_surface: {
        ...session.surfaces.display,
        widget_id: manifest.widget_id,
        widget_cid: manifest.widget_cid,
      },
      audio_surface: session.surfaces.audio,
    };
  }

  function dispatchSessionCommand(commandType, payload, sessionInput, manifestInput) {
    const session = buildMobileHostedSession(sessionInput, manifestInput);
    const command = buildSessionCommand(commandType, payload, session, manifestInput);
    return {
      ...session,
      command_queue: [...session.command_queue, command],
      last_command: command,
    };
  }

  function validateManifest(input) {
    const manifest = normalizeManifest(input);
    const errors = [];
    const warnings = [];
    const viewportWidth = Number(manifest.viewport.width);
    const viewportHeight = Number(manifest.viewport.height);
    const actionIds = new Set(manifest.actions.map((action) => action.id));

    if (viewportWidth !== 600 || viewportHeight !== 600) {
      errors.push('Viewport must be exactly 600x600.');
    }
    if (manifest.focus_order.length === 0) {
      errors.push('At least one focusable action is required.');
    }
    if (new Set(manifest.focus_order).size !== manifest.focus_order.length) {
      errors.push('Focus order must not contain duplicate action IDs.');
    }

    manifest.focus_order.forEach((actionId) => {
      if (!actionIds.has(actionId)) {
        errors.push(`Focus target is missing from actions: ${actionId}.`);
      }
    });

    manifest.regions.forEach((region) => {
      const bounds = ['x', 'y', 'width', 'height'].map((key) => Number(region[key]));
      if (bounds.some((value) => !Number.isFinite(value))) {
        errors.push(`Region ${region.id || 'unknown'} has invalid bounds.`);
        return;
      }
      const [x, y, width, height] = bounds;
      if (x < 0 || y < 0 || width <= 0 || height <= 0) {
        errors.push(`Region ${region.id || 'unknown'} has non-positive bounds.`);
      }
      if (x + width > viewportWidth || y + height > viewportHeight) {
        errors.push(`Region ${region.id || 'unknown'} extends outside the viewport.`);
      }
      if (region.kind === 'action' && !actionIds.has(region.action_id)) {
        errors.push(`Action region ${region.id || 'unknown'} points to a missing action.`);
      }
      if (region.kind === 'media' && isObject(region.media)) {
        const uri = String(region.media.uri || '');
        if (uri && !uri.startsWith('https://')) {
          errors.push(`Media region ${region.id || 'unknown'} must use HTTPS media.`);
        }
        if (region.media.type === 'video' && !uri.toLowerCase().endsWith('.mp4')) {
          errors.push(`Video region ${region.id || 'unknown'} must use MP4 media.`);
        }
      }
    });

    if (!manifest.fallback.render_path && !manifest.fallback.renderPath) {
      warnings.push('Fallback render path is missing.');
    }

    return {
      ok: errors.length === 0,
      errors,
      warnings,
      manifest,
    };
  }

  function buildReadinessDescriptor(input) {
    const manifest = normalizeManifest(input);
    const deploymentUrl =
      manifest.readiness?.deployment_url ||
      'https://example.com/glasses-display/widgets/task-progress-simulator';
    return {
      deployment_url: deploymentUrl,
      viewport: { width: 600, height: 600 },
      navigation_model: 'dpad_focus',
      focusable_elements: manifest.focus_order.length,
      navigation_order_valid:
        manifest.focus_order.length > 0 &&
        new Set(manifest.focus_order).size === manifest.focus_order.length,
      dark_theme_supported: true,
      min_contrast_ratio: 8.1,
      app_connection_documented: true,
      widgets: [
        {
          widget_id: manifest.widget_id,
          widget_cid: manifest.widget_cid,
          render_path: 'display-webapp',
          fallback_render_path: manifest.fallback.render_path || 'display-webapp',
          webapp_target: true,
          deployment_url: deploymentUrl,
          viewport: { width: 600, height: 600 },
          navigation_model: 'dpad_focus',
          focusable_elements: manifest.focus_order.length,
          focus_order: [...manifest.focus_order],
          navigation_order_valid:
            manifest.focus_order.length > 0 &&
            new Set(manifest.focus_order).size === manifest.focus_order.length,
          dark_theme_supported: true,
          min_contrast_ratio: 8.1,
          browser_preview: {
            renderer: 'dev/meta-rayban-display-simulator/simulator.js',
            renderable: validateManifest(manifest).ok,
            viewport: { width: 600, height: 600 },
          },
        },
      ],
    };
  }

  function buildBridgeResult(operation, manifest, stateKey, extra) {
    const displayState = DISPLAY_STATES[stateKey] || DISPLAY_STATES.ready;
    const fallback = manifest.fallback || {};
    return {
      state: displayState.supported ? 'ready' : 'unavailable',
      mode: 'simulator',
      supported: displayState.supported,
      action: operation,
      operation,
      reason: displayState.reason || null,
      message: displayState.message,
      renderPath: displayState.supported ? 'simulator' : fallback.render_path || 'mobile-card',
      requiredAction: displayState.requiredAction || null,
      displayConnectionState: displayState.displayConnectionState,
      displayLastAction: operation,
      displayLastStatus: displayState.displayLastStatus,
      displayLastError: displayState.reason || null,
      displayLifecycleStages: ['registered', 'session_started', displayState.displayLastStatus],
      widgetId: manifest.widget_id,
      widgetCid: manifest.widget_cid,
      descriptorCid: manifest.descriptor_cid,
      orbReceiptCid: manifest.orb_receipt_cid,
      correlationId: manifest.correlation_id,
      requestId: extra?.request_id || `sim-${Date.now()}`,
      fallback,
      sensor: extra?.sensor || null,
    };
  }

  function buildInteractionEnvelope(surfaceEvent, rawPayload, manifest, context) {
    return {
      schema: 'hallucinate.control_surface/interaction_envelope',
      surface: context?.surface || 'gesture',
      surface_event: surfaceEvent,
      raw_payload: {
        ...rawPayload,
        correlation_id: manifest.correlation_id,
        widget_id: manifest.widget_id,
        widget_cid: manifest.widget_cid,
        descriptor_cid: manifest.descriptor_cid,
        orb_receipt_cid: manifest.orb_receipt_cid,
      },
      context: {
        platform: context?.platform || 'simulator',
        device_context: {
          remote_surface:
            context?.remote_surface || 'meta-rayban-display-simulator',
          display_state: context?.display_state || 'ready',
        },
      },
    };
  }

  function regionStyle(region) {
    return [
      `left:${Number(region.x)}px`,
      `top:${Number(region.y)}px`,
      `width:${Number(region.width)}px`,
      `height:${Number(region.height)}px`,
    ].join(';');
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  function renderTextRegion(region) {
    return `<div class="primary-text">${escapeHtml(region.text)}</div>`;
  }

  function renderProgressRegion(region) {
    const value = clamp(Number(region.value || 0), 0, 1);
    return [
      '<div class="progress-label">',
      `<span>${escapeHtml(region.label || `${Math.round(value * 100)}%`)}</span>`,
      '<span>progress</span>',
      '</div>',
      '<div class="progress-track">',
      `<div class="progress-fill" style="width:${Math.round(value * 100)}%"></div>`,
      '</div>',
    ].join('');
  }

  function renderMediaRegion(region) {
    const media = isObject(region.media) ? region.media : {};
    return `<div>${escapeHtml(media.alt || region.fallback_text || 'Media fallback')}</div>`;
  }

  function renderRegion(region, focusedActionId) {
    const kind = region.kind || 'text';
    const variant = region.variant || kind;
    const focusAttr =
      kind === 'action' && region.action_id === focusedActionId ? ' data-focused="true"' : '';
    const actionAttr = region.action_id ? ` data-action-id="${escapeHtml(region.action_id)}"` : '';
    let body = '';
    if (kind === 'progress') {
      body = renderProgressRegion(region);
    } else if (kind === 'media') {
      body = renderMediaRegion(region);
    } else if (kind === 'action') {
      body = escapeHtml(region.label || region.action_id);
    } else {
      body = renderTextRegion(region);
    }
    return `<div class="display-region ${escapeHtml(kind)} ${escapeHtml(variant)}"${actionAttr}${focusAttr} style="${regionStyle(region)}">${body}</div>`;
  }

  function renderManifest(frame, manifest, focusIndex, displayState) {
    const focusedActionId = manifest.focus_order[focusIndex] || null;
    frame.innerHTML = manifest.regions
      .map((region) => renderRegion(region, focusedActionId))
      .join('');

    if (displayState !== 'ready') {
      const state = DISPLAY_STATES[displayState] || DISPLAY_STATES.unavailable;
      const overlay = document.createElement('div');
      overlay.className = 'display-overlay';
      overlay.innerHTML = `<div><h2>${escapeHtml(state.displayLastStatus)}</h2><p>${escapeHtml(state.message)}</p></div>`;
      frame.appendChild(overlay);
    }
  }

  function downloadJson(name, value) {
    const blob = new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  }

  function createBrowserApp() {
    const frame = document.getElementById('display-frame');
    const fixtureSelect = document.getElementById('fixture-select');
    const displayStateSelect = document.getElementById('display-state-select');
    const displayStateLabel = document.getElementById('display-state-label');
    const validationList = document.getElementById('validation-list');
    const eventLog = document.getElementById('event-log');
    const sessionLog = document.getElementById('session-log');
    const commandSurfaceSelect = document.getElementById('command-surface-select');
    const commandPayloadInput = document.getElementById('command-payload-input');
    const headingInput = document.getElementById('heading-input');
    const tiltInput = document.getElementById('tilt-input');
    const rollInput = document.getElementById('roll-input');
    const accelerationInput = document.getElementById('acceleration-input');
    const latitudeInput = document.getElementById('latitude-input');
    const longitudeInput = document.getElementById('longitude-input');
    const manifestFileInput = document.getElementById('manifest-file-input');
    let manifest = normalizeManifest(DEFAULT_MANIFEST);
    let commandSession = buildMobileHostedSession(DEFAULT_COMMAND_SESSION, manifest);
    let focusIndex = 0;
    let trace = [];

    function sensorSnapshot() {
      return {
        heading: Number(headingInput.value),
        tilt: Number(tiltInput.value),
        roll: Number(rollInput.value),
        acceleration: Number(accelerationInput.value),
        location: {
          latitude: Number(latitudeInput.value),
          longitude: Number(longitudeInput.value),
        },
      };
    }

    function appendTrace(type, payload) {
      const actionId = payload?.action_id || null;
      const bridgeResult = payload?.result || null;
      const requestId = bridgeResult?.requestId || payload?.request_id || null;
      const fallback = bridgeResult?.fallback || manifest.fallback || {};
      const event = {
        type,
        action_id: actionId,
        request_id: requestId,
        fallback_reason: bridgeResult?.reason || fallback.reason || null,
        payload,
        interaction_envelope: buildInteractionEnvelope(
          type === 'activate' ? 'tap' : type,
          {
            event_type: type,
            action_id: actionId,
            request_id: requestId,
            fallback_reason: bridgeResult?.reason || fallback.reason || null,
            sensor: payload?.sensor || bridgeResult?.sensor || null,
          },
          manifest,
          { display_state: displayStateSelect.value },
        ),
        correlation_id: manifest.correlation_id,
        recorded_at: new Date().toISOString(),
      };
      trace = [...trace, event].slice(-80);
      eventLog.textContent = JSON.stringify(trace.slice(-12), null, 2);
      return event;
    }

    function refreshSessionLog() {
      if (!sessionLog) {
        return;
      }
      sessionLog.textContent = JSON.stringify(
        {
          session_identity: commandSession.session_identity,
          host_mode: commandSession.host_mode,
          display_surface: commandSession.surfaces.display,
          audio_surface: commandSession.surfaces.audio,
          command_queue_depth: commandSession.command_queue.length,
          last_command: commandSession.last_command || null,
        },
        null,
        2,
      );
    }

    function refresh() {
      const validation = validateManifest(manifest);
      displayStateLabel.textContent = displayStateSelect.value;
      validationList.innerHTML = [
        ...validation.errors.map((message) => ({ message, error: true })),
        ...validation.warnings.map((message) => ({ message, error: false })),
        ...(validation.ok ? [{ message: 'Manifest is valid for 600x600 preview.', error: false }] : []),
      ]
        .map((entry) => `<li class="${entry.error ? 'error' : ''}">${escapeHtml(entry.message)}</li>`)
        .join('');
      renderManifest(frame, validation.manifest, focusIndex, displayStateSelect.value);
      refreshSessionLog();
    }

    function moveFocus(delta) {
      if (manifest.focus_order.length === 0) {
        return;
      }
      focusIndex = (focusIndex + delta + manifest.focus_order.length) % manifest.focus_order.length;
      appendTrace('focus', {
        action_id: manifest.focus_order[focusIndex],
        sensor: sensorSnapshot(),
      });
      refresh();
    }

    function activateFocusedAction() {
      const actionId = manifest.focus_order[focusIndex];
      const action = manifest.actions.find((candidate) => candidate.id === actionId);
      if (!action) {
        return;
      }
      const result = buildBridgeResult(
        action.operation || 'activate',
        manifest,
        displayStateSelect.value,
        {
          request_id: `sim-${action.id}-${Date.now()}`,
          sensor: sensorSnapshot(),
        },
      );
      appendTrace('activate', {
        action_id: action.id,
        result: {
          ...result,
          ...(action.result || {}),
        },
      });
      commandSession = dispatchSessionCommand(
        'display_action',
        {
          command_id: result.requestId,
          target_surface: 'display',
          action_id: action.id,
          bridge_result: result,
        },
        commandSession,
        manifest,
      );
      refresh();
    }

    async function loadSelectedFixture() {
      if (!fixtureSelect?.value) {
        return;
      }
      try {
        const response = await fetch(`./fixtures/${fixtureSelect.value}.json`, {
          cache: 'no-store',
        });
        if (!response.ok) {
          throw new Error(`Fixture load failed: ${response.status}`);
        }
        manifest = normalizeManifest(await response.json());
        commandSession = buildMobileHostedSession(commandSession, manifest);
        focusIndex = 0;
        appendTrace('fixture_loaded', {
          fixture: fixtureSelect.value,
          widget_id: manifest.widget_id,
        });
        refresh();
        frame.focus();
      } catch (error) {
        appendTrace('fixture_load_failed', {
          fixture: fixtureSelect.value,
          message: error.message,
        });
      }
    }

    frame.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault();
        moveFocus(1);
      } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault();
        moveFocus(-1);
      } else if (event.key === 'Enter') {
        event.preventDefault();
        activateFocusedAction();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        appendTrace('escape', { reason: 'session_end_requested' });
      }
    });

    displayStateSelect.addEventListener('change', () => {
      appendTrace('display_state', {
        state: displayStateSelect.value,
        sensor: sensorSnapshot(),
      });
      refresh();
    });

    fixtureSelect?.addEventListener('change', () => {
      loadSelectedFixture();
    });

    document.getElementById('reset-button').addEventListener('click', () => {
      manifest = normalizeManifest(DEFAULT_MANIFEST);
      commandSession = buildMobileHostedSession(DEFAULT_COMMAND_SESSION, manifest);
      focusIndex = 0;
      trace = [];
      eventLog.textContent = '';
      refresh();
      frame.focus();
    });

    document.getElementById('export-trace-button').addEventListener('click', () => {
      downloadJson('meta-rayban-display-simulator-trace.json', {
        manifest: {
          widget_id: manifest.widget_id,
          widget_cid: manifest.widget_cid,
        },
        trace,
      });
    });

    document.getElementById('export-readiness-button').addEventListener('click', () => {
      downloadJson('meta-rayban-display-readiness.json', buildReadinessDescriptor(manifest));
    });

    document.getElementById('dispatch-command-button').addEventListener('click', () => {
      const targetSurface = commandSurfaceSelect.value;
      const commandType = targetSurface === 'audio' ? 'audio_command' : 'render_display';
      commandSession = dispatchSessionCommand(
        commandType,
        {
          target_surface: targetSurface,
          text: commandPayloadInput.value,
          sensor: sensorSnapshot(),
        },
        commandSession,
        manifest,
      );
      appendTrace('session_command', commandSession.last_command);
      refresh();
    });

    document.getElementById('export-session-button').addEventListener('click', () => {
      downloadJson('meta-rayban-browser-session.json', commandSession);
    });

    manifestFileInput.addEventListener('change', async () => {
      const [file] = manifestFileInput.files || [];
      if (!file) {
        return;
      }
      manifest = normalizeManifest(JSON.parse(await file.text()));
      commandSession = buildMobileHostedSession(commandSession, manifest);
      focusIndex = 0;
      appendTrace('manifest_loaded', { name: file.name });
      refresh();
      frame.focus();
    });

    appendTrace('simulator_ready', {
      widget_id: manifest.widget_id,
      session_id: commandSession.session_identity.session_id,
      sensor: sensorSnapshot(),
    });
    refresh();
    frame.focus();
  }

  const api = {
    DISPLAY_STATES,
    DEFAULT_MANIFEST,
    DEFAULT_COMMAND_SESSION,
    REMOTE_TERMINAL_CONTRACT_ID,
    REMOTE_TERMINAL_ENDPOINTS,
    normalizeManifest,
    normalizeCommandSession,
    buildMobileHostedSession,
    buildRemoteTerminalRoute,
    buildSessionCommand,
    dispatchSessionCommand,
    validateManifest,
    buildReadinessDescriptor,
    buildBridgeResult,
    buildInteractionEnvelope,
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }

  globalScope.MetaRayBanDisplaySimulator = api;

  if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', createBrowserApp);
  }
})(typeof globalThis !== 'undefined' ? globalThis : window);
