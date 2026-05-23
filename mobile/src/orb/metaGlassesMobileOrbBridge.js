import { executeLocalStructuredAction } from '../utils/agentActions';
import {
  DISPLAY_WIDGET_ACTION_BY_ACTION_ID,
  DISPLAY_WIDGET_ACTION_CONTRACT,
  DISPLAY_WIDGET_ACTION_IDS,
  DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID,
  isDisplayWidgetActionId,
} from '../utils/metaWearablesDatDisplayWidgetContract';
import {
  DISPLAY_WIDGET_BRIDGE_INTERFACE,
  MOBILE_ORB_BRIDGE_INTERFACE,
  descriptorRef,
  localInterfaceKey,
} from './metaGlassesOrbDescriptors';

const DEFAULT_EDGE_ID = 'handsfree-mobile-orb-edge';
const DEFAULT_POLICY_CID = 'local:policy:handsfree-mobile-orb-edge';
const DEFAULT_EDGE_SESSION_ID = 'local:edge-session:handsfree-mobile-orb-edge';
const DEFAULT_SERVICE_BINDING = 'local:binding:handsfree-service';

const EVENT_TYPES = new Set([
  'session_state',
  'device_state',
  'captouch',
  'neural_input',
  'display_action',
  'audio_state',
  'camera_frame_ref',
  'photo_ref',
  'sensor',
  'location',
  'permission_state',
  'diagnostic',
]);

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function definedEntries(record) {
  return Object.fromEntries(
    Object.entries(record).filter(([, value]) => value !== undefined)
  );
}

function stableStringify(value) {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`;
  }
  return `{${Object.keys(value)
    .sort()
    .filter((key) => value[key] !== undefined)
    .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
    .join(',')}}`;
}

function localCid(prefix, value) {
  // Mobile does not bundle Node crypto. Production CIDs should be supplied by
  // backend/SwissKnife; this local deterministic ref is for edge-only fixtures.
  return `local:${prefix}:${stableStringify(value).length}:${Math.abs(hashString(stableStringify(value)))}`;
}

function hashString(value) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash + value.charCodeAt(index)) | 0;
  }
  return hash;
}

function nowIso(now) {
  return now().toISOString();
}

function normalizeCapabilities(input = {}) {
  const capabilities = input.capabilities || input.dat_capabilities || input;
  return {
    session: Boolean(capabilities.session),
    camera: Boolean(capabilities.camera),
    photoCapture: Boolean(capabilities.photoCapture),
    videoStream: Boolean(capabilities.videoStream),
    audio: Boolean(capabilities.audio),
    display: Boolean(capabilities.display),
    displayVideo: Boolean(capabilities.displayVideo),
    webAppDisplay: Boolean(capabilities.webAppDisplay),
  };
}

function normalizeEdgeSessionSnapshot(session = {}) {
  if (!isObject(session) || !session.edge_session_id || !session.policy_cid) {
    return null;
  }
  return {
    edge_session_id: session.edge_session_id,
    edge_id: session.edge_id || DEFAULT_EDGE_ID,
    platform: session.platform || 'simulator',
    device_id: session.device_id || null,
    policy_cid: session.policy_cid,
    accepted_interface_cids: Array.isArray(session.accepted_interface_cids)
      ? session.accepted_interface_cids.filter((cid) => typeof cid === 'string')
      : [],
    dat_capabilities: normalizeCapabilities(session.dat_capabilities || session.capabilities || {}),
    registered_at: session.registered_at || null,
    expires_at: session.expires_at || null,
  };
}

function normalizePolicyDecision(policyDecision = {}) {
  if (!isObject(policyDecision)) {
    return {
      outcome: 'permit',
      reasons: ['Local mobile ORB bridge dispatch.'],
      source: 'mobile_orb_bridge',
    };
  }
  return {
    outcome: policyDecision.outcome || 'permit',
    reasons: Array.isArray(policyDecision.reasons) ? policyDecision.reasons : [],
    source: policyDecision.source || 'mobile_orb_bridge',
    ...policyDecision,
  };
}

function operationForDisplayAction(actionType) {
  return DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionType] || 'render_widget';
}

function actionForDisplayAction(actionType) {
  return DISPLAY_WIDGET_ACTION_BY_ACTION_ID[actionType] || 'render';
}

function actionIdForOperation(operation) {
  return (
    DISPLAY_WIDGET_ACTION_IDS.find(
      (actionId) => DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionId] === operation
    ) || 'mobile_render_display_widget'
  );
}

export function normalizeDisplayWidgetMobileAction(action = {}, defaults = {}) {
  const operation = action.operation || defaults.operation || 'render_widget';
  const type = action.type || defaults.type || actionIdForOperation(operation);
  const widgetId =
    action.widget_id ||
    action.widgetId ||
    action.manifest?.widget_id ||
    defaults.widget_id ||
    defaults.widgetId ||
    null;
  const widgetCid =
    action.widget_cid ||
    action.widgetCid ||
    action.manifest?.widget_cid ||
    defaults.widget_cid ||
    defaults.widgetCid ||
    localCid('widget', { widgetId, operation });
  const descriptorCid =
    action.descriptor_cid ||
    action.interface_cid ||
    defaults.descriptor_cid ||
    defaults.interface_cid ||
    localInterfaceKey(DISPLAY_WIDGET_BRIDGE_INTERFACE);

  return definedEntries({
    contract: action.contract || DISPLAY_WIDGET_ACTION_CONTRACT,
    type,
    action: action.action || actionForDisplayAction(type),
    operation,
    descriptor_cid: descriptorCid,
    interface_cid: action.interface_cid || defaults.interface_cid || descriptorCid,
    widget_id: widgetId,
    widget_cid: widgetCid,
    orb_receipt_cid:
      action.orb_receipt_cid ||
      action.receipt_cid ||
      defaults.orb_receipt_cid ||
      defaults.receipt_cid ||
      localCid('receipt', { type, operation, widgetId }),
    policy_decision: normalizePolicyDecision(action.policy_decision || defaults.policy_decision),
    correlation_id:
      action.correlation_id ||
      action.correlationId ||
      defaults.correlation_id ||
      defaults.correlationId ||
      'mobile-orb-dispatch',
    request_id: action.request_id || action.requestId || defaults.request_id || defaults.requestId,
    issued_at: action.issued_at || action.issuedAt || defaults.issued_at || defaults.issuedAt,
    manifest: action.manifest || defaults.manifest,
    state: action.state || defaults.state,
    patch: action.patch || defaults.patch,
    focus: action.focus || defaults.focus,
    activated_action_id:
      action.activated_action_id ||
      action.activatedActionId ||
      action.action_id ||
      defaults.activated_action_id ||
      defaults.action_id,
    video: action.video || defaults.video,
    subscription: action.subscription || defaults.subscription,
    fallback: action.fallback || defaults.fallback,
  });
}

export function actionItemFromDisplayWidgetAction(action) {
  const payload = normalizeDisplayWidgetMobileAction(action);
  return {
    id: payload.type,
    label: payload.type,
    phrase: payload.type,
    params: {
      display_widget_action: payload,
    },
    mobile_payload: payload,
  };
}

function defaultBackend(now) {
  return {
    async registerEdgeCapabilities(payload) {
      return {
        edge_session_id: DEFAULT_EDGE_SESSION_ID,
        accepted_interface_cids: payload.local_interface_cids || [],
        policy_cid: DEFAULT_POLICY_CID,
        expires_at: null,
      };
    },
    async publishGlassesEvent(payload) {
      return {
        event_cid: localCid('event', payload),
        accepted: true,
        routed_operations: [],
        receipt_cid: localCid('receipt', payload),
      };
    },
    async bindService(payload) {
      return {
        binding_handle:
          payload.binding_handle ||
          `${DEFAULT_SERVICE_BINDING}:${payload.service_interface_cid || payload.operation || 'unknown'}`,
        transport: payload.transport_preference || 'http',
        granted_capabilities: [],
        policy_decision: normalizePolicyDecision({
          reasons: ['Local default service binding.'],
        }),
        expires_at: null,
      };
    },
    async invokeService(payload) {
      return {
        ok: true,
        service_result: {},
        output_refs: [],
        provenance_refs: [],
        receipt_cid: localCid('receipt', payload),
        follow_up_actions: [],
      };
    },
    async subscribeServiceUpdates(payload) {
      return {
        subscription_id: `local:subscription:${payload.operation || 'updates'}`,
        receipt_cid: localCid('receipt', payload),
        generation_key: `${payload.binding_handle}:${payload.operation}:${nowIso(now)}`,
      };
    },
    async dispatchGlassesResponse(payload) {
      return {
        dispatched_actions: payload.result?.follow_up_actions || [],
        display_widget_action: payload.result?.display_widget_action || null,
        spoken_text: payload.result?.spoken_text || null,
        receipt_cid: localCid('receipt', payload),
      };
    },
    async revokeBinding(payload) {
      return {
        revoked: true,
        receipt_cid: localCid('receipt', payload),
      };
    },
  };
}

export class MetaGlassesMobileOrbBridge {
  constructor(options = {}) {
    this.now = options.now || (() => new Date());
    this.backend = {
      ...defaultBackend(this.now),
      ...(options.backend || {}),
    };
    this.localActionExecutor = options.localActionExecutor || executeLocalStructuredAction;
    this.edgeSessionStore = options.edgeSessionStore || null;
    this.edgeId = options.edgeId || DEFAULT_EDGE_ID;
    this.platform = options.platform || 'simulator';
    this.device = options.device || {};
    this.localInterfaceCids = options.localInterfaceCids || [
      localInterfaceKey(MOBILE_ORB_BRIDGE_INTERFACE),
      localInterfaceKey(DISPLAY_WIDGET_BRIDGE_INTERFACE),
    ];
    this.edgeSession = null;
    this.bindings = new Map();
    this.eventLog = [];
  }

  getEdgeSession() {
    return this.edgeSession;
  }

  getEventLog() {
    return [...this.eventLog];
  }

  getDiagnostics() {
    return {
      registered: Boolean(this.edgeSession?.edge_session_id),
      edge_session_id: this.edgeSession?.edge_session_id || null,
      edge_id: this.edgeSession?.edge_id || this.edgeId,
      platform: this.edgeSession?.platform || this.platform,
      policy_cid: this.edgeSession?.policy_cid || null,
      accepted_interface_cids: this.edgeSession?.accepted_interface_cids || [],
      dat_capabilities: this.edgeSession?.dat_capabilities || null,
      bindings_count: this.bindings.size,
      events_count: this.eventLog.length,
      latest_event_cid: this.eventLog[this.eventLog.length - 1]?.event_cid || null,
    };
  }

  hydrateEdgeSession(session) {
    const normalized = normalizeEdgeSessionSnapshot(session);
    if (!normalized) {
      return null;
    }
    this.edgeSession = normalized;
    return this.edgeSession;
  }

  async restoreEdgeSession() {
    if (!this.edgeSessionStore?.load) {
      return null;
    }
    return this.hydrateEdgeSession(await this.edgeSessionStore.load());
  }

  async clearEdgeSession() {
    this.edgeSession = null;
    this.bindings.clear();
    this.eventLog = [];
    if (this.edgeSessionStore?.clear) {
      await this.edgeSessionStore.clear();
    }
  }

  async registerEdgeCapabilities(input = {}) {
    const payload = definedEntries({
      edge_id: input.edge_id || this.edgeId,
      platform: input.platform || this.platform,
      device_id: input.device_id || input.deviceId || this.device.deviceId,
      device_model: input.device_model || input.deviceModel || this.device.deviceName,
      dat_capabilities: normalizeCapabilities(input.dat_capabilities || input.capabilities || input),
      local_interface_cids: input.local_interface_cids || this.localInterfaceCids,
      transport_preferences: input.transport_preferences || ['local', 'http', 'websocket', 'mcp-server'],
      descriptors: input.descriptors || [
        descriptorRef(MOBILE_ORB_BRIDGE_INTERFACE, this.localInterfaceCids[0]),
        descriptorRef(DISPLAY_WIDGET_BRIDGE_INTERFACE, this.localInterfaceCids[1]),
      ],
    });
    const response = await this.backend.registerEdgeCapabilities(payload);
    this.edgeSession = {
      ...response,
      edge_id: payload.edge_id,
      platform: payload.platform,
      device_id: payload.device_id || null,
      dat_capabilities: payload.dat_capabilities,
      registered_at: nowIso(this.now),
    };
    if (this.edgeSessionStore?.save) {
      await this.edgeSessionStore.save(this.edgeSession);
    }
    return {
      payload,
      response: this.edgeSession,
    };
  }

  requireEdgeSession() {
    if (!this.edgeSession?.edge_session_id) {
      throw new Error('Meta glasses mobile ORB edge session is not registered.');
    }
    return this.edgeSession;
  }

  async publishGlassesEvent(eventType, payload = {}, options = {}) {
    if (!EVENT_TYPES.has(eventType)) {
      throw new Error(`Unsupported Meta glasses event type: ${eventType}`);
    }
    const edge = this.requireEdgeSession();
    const eventPayload = definedEntries({
      edge_session_id: edge.edge_session_id,
      event_type: eventType,
      payload,
      correlation_id:
        options.correlation_id ||
        payload.correlation_id ||
        payload.correlationId ||
        `mobile-orb-event-${this.eventLog.length + 1}`,
      parent_receipt_cids: options.parent_receipt_cids || payload.parent_receipt_cids,
      observed_at: options.observed_at || nowIso(this.now),
    });
    const response = await this.backend.publishGlassesEvent(eventPayload);
    const event = {
      ...eventPayload,
      event_cid: response.event_cid,
      accepted: response.accepted,
      receipt_cid: response.receipt_cid,
    };
    this.eventLog.push(event);
    return {
      payload: eventPayload,
      response,
      event,
    };
  }

  async bindService(options = {}) {
    const edge = this.requireEdgeSession();
    const payload = definedEntries({
      edge_session_id: edge.edge_session_id,
      service_interface_cid: options.service_interface_cid || options.serviceInterfaceCid,
      service_descriptor: options.service_descriptor || options.serviceDescriptor,
      operation: options.operation,
      transport_preference: options.transport_preference || options.transportPreference || 'mcp-server',
      user_intent: options.user_intent || options.userIntent,
      policy_context: options.policy_context || options.policyContext,
    });
    if (!payload.service_interface_cid) {
      throw new Error('Cannot bind service without service_interface_cid.');
    }
    const response = await this.backend.bindService(payload);
    this.bindings.set(response.binding_handle, {
      ...response,
      service_interface_cid: payload.service_interface_cid,
      operation: payload.operation || null,
      bound_at: nowIso(this.now),
    });
    return {
      payload,
      response,
    };
  }

  async invokeService(bindingHandle, operation, args = {}, options = {}) {
    const binding = this.bindings.get(bindingHandle);
    if (!binding && !options.allow_untracked_binding) {
      throw new Error(`Cannot invoke untracked service binding: ${bindingHandle}`);
    }
    const payload = definedEntries({
      binding_handle: bindingHandle,
      operation,
      arguments: args,
      glasses_context: options.glasses_context || options.glassesContext,
      display_context: options.display_context || options.displayContext,
      correlation_id: options.correlation_id || `mobile-orb-service-${operation}`,
      parent_receipt_cids: options.parent_receipt_cids,
    });
    const response = await this.backend.invokeService(payload);
    return {
      payload,
      response,
    };
  }

  async subscribeServiceUpdates(bindingHandle, operation, options = {}) {
    const payload = definedEntries({
      binding_handle: bindingHandle,
      operation,
      arguments: options.arguments || {},
      stream: options.stream || 'updates',
      correlation_id: options.correlation_id || `mobile-orb-stream-${operation}`,
    });
    const response = await this.backend.subscribeServiceUpdates(payload);
    return {
      payload,
      response,
    };
  }

  async dispatchGlassesResponse({ result = {}, renderTargets = [], fallback = null, navigation = null, correlationId = null, parentReceiptCids = [] } = {}) {
    const edge = this.requireEdgeSession();
    const payload = definedEntries({
      edge_session_id: edge.edge_session_id,
      result,
      render_targets: renderTargets,
      fallback: fallback || undefined,
      correlation_id: correlationId || result.correlation_id || 'mobile-orb-dispatch',
      parent_receipt_cids: parentReceiptCids,
    });
    const response = await this.backend.dispatchGlassesResponse(payload);
    const actions = [
      ...(Array.isArray(response.dispatched_actions) ? response.dispatched_actions : []),
      ...(Array.isArray(result.follow_up_actions) ? result.follow_up_actions : []),
    ];
    const displayWidgetAction =
      response.display_widget_action ||
      result.display_widget_action ||
      actions.find((action) => isDisplayWidgetActionId(action?.id || action?.type));

    const localResults = [];
    if (displayWidgetAction) {
      const actionPayload = displayWidgetAction.id
        ? displayWidgetAction.mobile_payload || displayWidgetAction.params?.display_widget_action || displayWidgetAction
        : displayWidgetAction;
      const actionItem = displayWidgetAction.id
        ? displayWidgetAction
        : actionItemFromDisplayWidgetAction({
          ...actionPayload,
          correlation_id: actionPayload.correlation_id || payload.correlation_id,
          orb_receipt_cid: actionPayload.orb_receipt_cid || response.receipt_cid,
          fallback: actionPayload.fallback || fallback,
        });
      if (isDisplayWidgetActionId(actionItem.id || actionItem.type)) {
        localResults.push(await this.localActionExecutor({ actionItem, navigation }));
      }
    }

    return {
      payload,
      response,
      localResults,
    };
  }

  async routeEventToService({
    eventType,
    eventPayload = {},
    serviceInterfaceCid,
    serviceDescriptor = null,
    serviceOperation,
    serviceArguments = {},
    renderTargets = ['display_widget', 'audio', 'mobile_card'],
    fallback = null,
    navigation = null,
    correlationId = null,
  }) {
    const event = await this.publishGlassesEvent(eventType, eventPayload, {
      correlation_id: correlationId,
    });
    const binding = await this.bindService({
      service_interface_cid: serviceInterfaceCid,
      service_descriptor: serviceDescriptor,
      operation: serviceOperation,
      user_intent: eventPayload.intent || eventPayload.command || eventType,
    });
    const invoked = await this.invokeService(
      binding.response.binding_handle,
      serviceOperation,
      serviceArguments,
      {
        correlation_id: event.payload.correlation_id,
        parent_receipt_cids: [event.response.receipt_cid].filter(Boolean),
        glasses_context: {
          event_type: eventType,
          event_cid: event.response.event_cid,
          payload: eventPayload,
        },
      }
    );
    const dispatched = await this.dispatchGlassesResponse({
      result: invoked.response,
      renderTargets,
      fallback,
      navigation,
      correlationId: event.payload.correlation_id,
      parentReceiptCids: [
        event.response.receipt_cid,
        invoked.response.receipt_cid,
      ].filter(Boolean),
    });

    return {
      event,
      binding,
      invoked,
      dispatched,
    };
  }

  async revokeBinding(bindingHandle, reason, options = {}) {
    const payload = {
      binding_handle: bindingHandle,
      reason,
      correlation_id: options.correlation_id || `mobile-orb-revoke-${bindingHandle}`,
    };
    const response = await this.backend.revokeBinding(payload);
    if (response.revoked) {
      this.bindings.delete(bindingHandle);
    }
    return {
      payload,
      response,
    };
  }
}

export function createMetaGlassesMobileOrbBridge(options = {}) {
  return new MetaGlassesMobileOrbBridge(options);
}
