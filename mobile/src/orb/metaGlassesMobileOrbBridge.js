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
const DEFAULT_EDGE_SESSION_ID = 'local:edge-session:handsfree-mobile-orb-edge';
const DEFAULT_SERVICE_BINDING = 'local:binding:handsfree-service';
const CONTROL_SURFACE_CONTRACT_REF = 'control_surface_contract:hallucinate-app:remote-client';
const CONTROL_SURFACE_POLICY_BUNDLE_REF = {
  policy_id: 'policy:hallucinate-app:remote-client-transport',
  policy_cid: 'local:hallucinate-app:remote-client-transport',
  version: '0.1.0',
  scope: 'remote-client-transport',
  source: 'system_default',
};
const CONTROL_SURFACE_COMPILED_POLICY_CID = 'local:hallucinate-app:remote-client-transport';
const CONTROL_SURFACE_SCHEMA_REFS = [
  'control_surface_contract',
  'interaction_envelope',
  'policy_decision',
  'mediation_receipt',
];
const MOBILE_ORB_DIAGNOSTICS_CONTRACT =
  'handsfree.meta-glasses/mobile-orb-diagnostics@0.1.0';
const DAT_CAPABILITY_KEYS = [
  'session',
  'camera',
  'photoCapture',
  'videoStream',
  'audio',
  'display',
  'displayVideo',
  'webAppDisplay',
];

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

function uniqueStrings(values) {
  const seen = new Set();
  const result = [];
  values.forEach((value) => {
    if (typeof value === 'string' && value.length > 0 && !seen.has(value)) {
      seen.add(value);
      result.push(value);
    }
  });
  return result;
}

function arrayOrEmpty(value) {
  return Array.isArray(value) ? value : [];
}

function collectControlSurfacePolicyCids(record = {}) {
  const policyDecisions = [
    record.policy_decision,
    record.mediation_receipt?.policy_decision,
  ].filter(isObject);
  const values = [record.policy_cid];
  policyDecisions.forEach((decision) => {
    values.push(
      decision.decision_id,
      decision.compiled_policy_cid,
      decision.policy_bundle_ref?.policy_cid
    );
  });
  values.push(
    record.interaction_envelope?.compiled_policy_cid,
    record.interaction_envelope?.policy_bundle_ref?.policy_cid
  );
  arrayOrEmpty(record.mediation_receipt?.policy_refs).forEach((policyRef) => {
    if (!isObject(policyRef)) {
      return;
    }
    values.push(
      policyRef.compiled_policy_cid,
      policyRef.policy_bundle_ref?.policy_cid
    );
  });
  return uniqueStrings(values);
}

function collectDescriptorCids(record = {}) {
  const values = [
    record.service_interface_cid,
    record.descriptor_cid,
    record.interface_cid,
    record.orb_binding?.interface_cid,
    record.orb_binding?.descriptor_cid,
    record.orb_binding?.transport_binding?.metadata?.descriptor_cid,
    record.display_widget_action?.descriptor_cid,
    record.display_widget_action?.interface_cid,
  ];
  values.push(...arrayOrEmpty(record.accepted_interface_cids));
  values.push(...arrayOrEmpty(record.local_interface_cids));
  arrayOrEmpty(record.descriptors).forEach((descriptor) => {
    if (!isObject(descriptor)) {
      return;
    }
    values.push(descriptor.interface_cid, descriptor.descriptor_cid, descriptor.schemaHash);
  });
  return uniqueStrings(values);
}

function collectReceiptCids(record = {}) {
  const values = [
    record.receipt_cid,
    record.orb_receipt_cid,
    record.mediation_receipt?.receipt_id,
    record.display_widget_action?.orb_receipt_cid,
    record.display_widget_action?.receipt_cid,
  ];
  values.push(...arrayOrEmpty(record.parent_receipt_cids));
  values.push(...arrayOrEmpty(record.output_refs));
  arrayOrEmpty(record.follow_up_actions).forEach((actionItem) => {
    if (!isObject(actionItem)) {
      return;
    }
    const mobilePayload = actionItem.mobile_payload;
    const displayAction = actionItem.params?.display_widget_action;
    values.push(
      mobilePayload?.orb_receipt_cid,
      mobilePayload?.receipt_cid,
      displayAction?.orb_receipt_cid,
      displayAction?.receipt_cid
    );
  });
  return uniqueStrings(values);
}

function fallbackReason(fallback = {}) {
  if (!isObject(fallback)) {
    return null;
  }
  return (
    fallback.reason ||
    fallback.message ||
    fallback.error ||
    fallback.render_path ||
    null
  );
}

function collectFallbackDetails(record = {}) {
  const candidates = [
    ['record', record.fallback],
    ['display_widget_action', record.display_widget_action?.fallback],
  ];
  arrayOrEmpty(record.follow_up_actions).forEach((actionItem) => {
    if (!isObject(actionItem)) {
      return;
    }
    candidates.push(
      ['follow_up_mobile_payload', actionItem.mobile_payload?.fallback],
      ['follow_up_display_action', actionItem.params?.display_widget_action?.fallback]
    );
  });
  return candidates
    .map(([source, fallback]) => {
      const reason = fallbackReason(fallback);
      if (!reason) {
        return null;
      }
      return {
        source,
        reason,
        render_path: fallback.render_path,
        message: fallback.message,
      };
    })
    .filter(Boolean);
}

function capabilityCounts(edgeSession) {
  const datCapabilities = edgeSession?.dat_capabilities || {};
  const datCounts = Object.fromEntries(
    DAT_CAPABILITY_KEYS.map((capability) => [
      capability,
      datCapabilities[capability] === true ? 1 : 0,
    ])
  );
  const edgeSessionCount = edgeSession?.edge_session_id ? 1 : 0;
  const capabilityMatrix = Object.fromEntries(
    DAT_CAPABILITY_KEYS.map((capability) => [
      capability,
      {
        available: datCounts[capability],
        unavailable: edgeSessionCount ? 1 - datCounts[capability] : 0,
      },
    ])
  );
  return {
    edge_sessions: edgeSessionCount,
    dat_capabilities: datCounts,
    capability_matrix: capabilityMatrix,
    total_enabled: Object.values(datCounts).reduce((total, count) => total + count, 0),
  };
}

function diagnosticsMode(platform) {
  if (platform === 'simulator') {
    return 'simulator';
  }
  if (platform === 'ios' || platform === 'android') {
    return 'physical_device';
  }
  return 'unknown';
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

function isStaleBindingError(error) {
  const message = String(error?.message || '').toLowerCase();
  return (
    message.includes('binding_not_found') ||
    message.includes('service binding not found') ||
    message.includes('untracked service binding')
  );
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
  if (!isObject(session) || !session.edge_session_id) {
    return null;
  }
  const contractRef =
    session.control_surface_contract_ref ||
    session.mediation_receipt?.control_surface_contract_ref ||
    session.interaction_envelope?.control_surface_contract_ref ||
    null;
  if (!contractRef && !session.policy_cid) {
    return null;
  }
  return {
    edge_session_id: session.edge_session_id,
    edge_id: session.edge_id || DEFAULT_EDGE_ID,
    platform: session.platform || 'simulator',
    device_id: session.device_id || null,
    policy_cid: session.policy_cid || null,
    control_surface_contract_ref: contractRef,
    interaction_envelope: session.interaction_envelope || null,
    normalized_intent:
      session.normalized_intent || session.interaction_envelope?.normalized_intent || null,
    policy_decision: session.policy_decision || session.mediation_receipt?.policy_decision || null,
    mediation_receipt: session.mediation_receipt || null,
    accepted_interface_cids: Array.isArray(session.accepted_interface_cids)
      ? session.accepted_interface_cids.filter((cid) => typeof cid === 'string')
      : [],
    dat_capabilities: normalizeCapabilities(session.dat_capabilities || session.capabilities || {}),
    registered_at: session.registered_at || null,
    expires_at: session.expires_at || null,
  };
}

function remoteSurface(operation, payload = {}) {
  if (payload.platform === 'simulator') {
    return 'simulator';
  }
  if (
    operation === 'publish_glasses_event' ||
    ['captouch', 'neural_input', 'display_action'].includes(payload.event_type)
  ) {
    return 'meta_glasses';
  }
  return 'mobile';
}

function remoteActorId(payload = {}) {
  return (
    payload.edge_session_id ||
    payload.edge_id ||
    payload.device_id ||
    payload.binding_handle ||
    payload.correlation_id ||
    'remote-client'
  );
}

function canonicalOutcome(value) {
  if (value === 'permit') {
    return 'allow';
  }
  return [
    'allow',
    'deny',
    'require_confirmation',
    'defer',
    'rewrite',
    'fallback_surface',
    'rate_limit',
  ].includes(value)
    ? value
    : 'allow';
}

function normalizedIntent(operation, payload = {}, surface = 'mobile') {
  if (isObject(payload.normalized_intent) && payload.normalized_intent.method) {
    return {
      intent: payload.normalized_intent.intent || `${surface}.${operation}`,
      method: payload.normalized_intent.method || operation,
      target_ref:
        payload.normalized_intent.target_ref ||
        `handsfree.meta_glasses.mobile.mobile_orb_bridge.${operation}`,
      arguments: isObject(payload.normalized_intent.arguments)
        ? payload.normalized_intent.arguments
        : payload,
      confidence: Number(payload.normalized_intent.confidence || 1),
    };
  }
  const nestedPayload = isObject(payload.payload) ? payload.payload : {};
  const args = isObject(payload.arguments) ? payload.arguments : {};
  return {
    intent:
      payload.user_intent ||
      payload.intent ||
      nestedPayload.intent ||
      nestedPayload.command ||
      args.intent ||
      `${surface}.${operation}`,
    method: operation,
    target_ref: `handsfree.meta_glasses.mobile.mobile_orb_bridge.${operation}`,
    arguments: payload,
    confidence: 1,
  };
}

function runtimeContext(payload = {}, surface = 'mobile', emittedAt = new Date().toISOString()) {
  return {
    local_time: emittedAt,
    state_frames: Array.isArray(payload.state_frames) ? payload.state_frames : [],
    device_mode: payload.device_mode || surface,
    platform: payload.platform || surface,
    location_context: isObject(payload.location_context) ? payload.location_context : {},
    device_context: definedEntries({
      edge_id: payload.edge_id,
      edge_session_id: payload.edge_session_id,
      device_id: payload.device_id,
      device_model: payload.device_model,
      dat_capabilities: payload.dat_capabilities,
      glasses_context: payload.glasses_context,
      display_context: payload.display_context,
    }),
  };
}

function logicBinding(operation, surface) {
  const bindingId = `hallucinate_app.remote_client.${surface}.${operation}`;
  return {
    binding_id: bindingId,
    policy_bundle_ref: CONTROL_SURFACE_POLICY_BUNDLE_REF,
    compiled_policy_cid: CONTROL_SURFACE_COMPILED_POLICY_CID,
    surface_ref: surface,
    method_ref: operation,
    norm_refs: [`${bindingId}.transport_only`],
  };
}

function buildMobileOrbControlSurfaceArtifacts(operation, payload = {}, options = {}) {
  if (
    isObject(payload.mediation_receipt) &&
    isObject(payload.mediation_receipt.interaction_envelope) &&
    isObject(payload.mediation_receipt.policy_decision)
  ) {
    const envelope = payload.mediation_receipt.interaction_envelope;
    return {
      control_surface_contract_ref:
        payload.mediation_receipt.control_surface_contract_ref ||
        envelope.control_surface_contract_ref ||
        payload.control_surface_contract_ref ||
        CONTROL_SURFACE_CONTRACT_REF,
      interaction_envelope: envelope,
      normalized_intent: envelope.normalized_intent || payload.normalized_intent || null,
      policy_decision: payload.mediation_receipt.policy_decision,
      mediation_receipt: payload.mediation_receipt,
    };
  }

  const emittedAt = options.emitted_at || new Date().toISOString();
  const surface = remoteSurface(operation, payload);
  const actorId = remoteActorId(payload);
  const intent = normalizedIntent(operation, payload, surface);
  const contractRef = payload.control_surface_contract_ref || CONTROL_SURFACE_CONTRACT_REF;
  const envelope = {
    interaction_id:
      payload.interaction_id ||
      payload.correlation_id ||
      payload.edge_session_id ||
      localCid('interaction', { operation, payload }),
    surface,
    surface_event: payload.event_type || operation,
    raw_payload: payload,
    normalized_intent: intent,
    actor: {
      type: 'remote_client',
      id: actorId,
      delegation_chain: [actorId],
    },
    context: runtimeContext(payload, surface, emittedAt),
    control_surface_contract_ref: contractRef,
    policy_bundle_ref: CONTROL_SURFACE_POLICY_BUNDLE_REF,
    compiled_policy_cid: CONTROL_SURFACE_COMPILED_POLICY_CID,
    logic_bindings: [logicBinding(operation, surface)],
  };
  const outcome = canonicalOutcome(options.outcome);
  const explanation = `${options.reason || 'Remote client artifact normalized to canonical control-surface envelope.'} Remote clients transport the Hallucinate App mediation receipt and do not define or authorize a separate policy contract.`;
  const policyDecision = {
    decision_id: localCid('control-surface-decision', {
      interaction_id: envelope.interaction_id,
      operation,
      outcome,
      compiled_policy_cid: CONTROL_SURFACE_COMPILED_POLICY_CID,
    }),
    interaction_id: envelope.interaction_id,
    interaction_envelope: envelope,
    outcome,
    policy_bundle_ref: CONTROL_SURFACE_POLICY_BUNDLE_REF,
    compiled_policy_cid: CONTROL_SURFACE_COMPILED_POLICY_CID,
    decided_at: emittedAt,
    matched_norms: [
      {
        norm_id: 'remote_client_transport_receipt',
        outcome,
        priority: 100,
        policy_bundle_ref: CONTROL_SURFACE_POLICY_BUNDLE_REF,
        logic_clause_refs: envelope.logic_bindings.map((binding) => binding.binding_id),
        guard_refs: [],
        explanation,
      },
    ],
    effects: [
      {
        outcome,
        method: intent.method,
        target_ref: intent.target_ref,
        arguments: intent.arguments,
        confirmation_required: outcome === 'require_confirmation',
        reason: explanation,
      },
    ],
    frame_facts: [
      {
        fact_id: localCid('fact', [envelope.interaction_id, 'surface']),
        kind: 'surface',
        subject: envelope.surface,
        predicate: 'surface.id',
        value: envelope.surface,
        attrs: {},
      },
      {
        fact_id: localCid('fact', [envelope.interaction_id, 'event']),
        kind: 'event',
        subject: envelope.surface,
        predicate: 'surface_event',
        value: envelope.surface_event,
        attrs: {},
      },
      {
        fact_id: localCid('fact', [envelope.interaction_id, 'method']),
        kind: 'method',
        subject: intent.target_ref,
        predicate: 'intent.method',
        value: intent.method,
        attrs: {},
      },
    ],
    reasons: [explanation],
    explanation,
    confidence: intent.confidence,
    metadata: {
      source: 'hallucinate_app.control_surface_mediator.remote_client_envelope',
      authorization_scope: 'hallucinate_app_control_surface_contract',
      remote_client_policy_contract: false,
      transport_receipt: true,
      schema_refs: CONTROL_SURFACE_SCHEMA_REFS,
    },
  };
  const invoked = !['deny', 'require_confirmation', 'defer', 'rate_limit'].includes(outcome);
  const mediationReceipt = {
    receipt_id:
      options.receipt_cid ||
      localCid('mediation_receipt', {
        interaction_id: envelope.interaction_id,
        decision_id: policyDecision.decision_id,
        outcome,
      }),
    emitted_at: emittedAt,
    control_surface_contract_ref: contractRef,
    interaction_envelope: envelope,
    policy_decision: policyDecision,
    policy_refs: [
      {
        policy_bundle_ref: CONTROL_SURFACE_POLICY_BUNDLE_REF,
        compiled_policy_cid: CONTROL_SURFACE_COMPILED_POLICY_CID,
        matched_norm_refs: ['remote_client_transport_receipt'],
      },
    ],
    mediation_result: {
      outcome,
      invoked,
      final_method: intent.method,
      final_target_ref: intent.target_ref,
      confirmation_required: outcome === 'require_confirmation',
    },
    explanation,
    metadata: {
      source: 'hallucinate_app.control_surface_mediator.remote_client_envelope',
      remote_client_policy_contract: false,
      schema_refs: CONTROL_SURFACE_SCHEMA_REFS,
    },
  };
  return {
    control_surface_contract_ref: contractRef,
    interaction_envelope: envelope,
    normalized_intent: intent,
    policy_decision: policyDecision,
    mediation_receipt: mediationReceipt,
  };
}

function controlSurfaceFields(artifacts = {}) {
  return definedEntries({
    control_surface_contract_ref: artifacts.control_surface_contract_ref,
    interaction_envelope: artifacts.interaction_envelope,
    normalized_intent: artifacts.normalized_intent,
    policy_decision: artifacts.policy_decision,
    mediation_receipt: artifacts.mediation_receipt,
  });
}

function hasCanonicalControlSurfaceArtifacts(value = {}) {
  return Boolean(
    value.control_surface_contract_ref &&
    isObject(value.interaction_envelope) &&
    isObject(value.policy_decision) &&
    isObject(value.mediation_receipt)
  );
}

function isMediationInvoked(artifacts = {}) {
  return Boolean(artifacts.mediation_receipt?.mediation_result?.invoked);
}

function normalizePolicyDecision(policyDecision = {}, defaults = {}) {
  if (!isObject(policyDecision)) {
    return buildMobileOrbControlSurfaceArtifacts(
      defaults.operation || 'dispatch_glasses_response',
      defaults.payload || {},
      {
        receipt_cid: defaults.receipt_cid,
        reason:
          defaults.reason ||
          'Mobile ORB bridge dispatch normalized by Hallucinate App control-surface contract.',
      }
    ).policy_decision;
  }
  if (policyDecision.decision_id && isObject(policyDecision.interaction_envelope)) {
    return policyDecision;
  }
  const outcome = canonicalOutcome(policyDecision.outcome);
  return {
    outcome,
    reasons: Array.isArray(policyDecision.reasons) ? policyDecision.reasons : [],
    source:
      policyDecision.source ||
      'hallucinate_app.control_surface_mediator.remote_client_envelope',
    ...policyDecision,
    outcome,
  };
}

function normalizeMethodDefinitions(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter(isObject)
    .filter((method) => typeof method.name === 'string' && method.name.length > 0)
    .map((method) => definedEntries(
      Object.fromEntries(Object.keys(method).sort().map((key) => [key, method[key]]))
    ));
}

function normalizeErrorDefinitions(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter(isObject)
    .filter((error) => typeof error.name === 'string' && error.name.length > 0)
    .map((error) => definedEntries(
      Object.fromEntries(Object.keys(error).sort().map((key) => [key, error[key]]))
    ));
}

function normalizeDescriptorRecord(value) {
  if (!isObject(value)) {
    return {};
  }
  return definedEntries(
    Object.fromEntries(Object.keys(value).sort().map((key) => [key, value[key]]))
  );
}

function normalizeDescriptorMetadata(value) {
  if (!isObject(value)) {
    return {};
  }
  return definedEntries({
    provider_name: value.provider_name,
    server_family: value.server_family || value.mcp_server_family,
    tool_name: value.tool_name || value.default_tool_name || value.operation_tool_name,
  });
}

function normalizeServiceDescriptor(serviceInterfaceCid, serviceDescriptor) {
  if (!isObject(serviceDescriptor)) {
    return null;
  }
  const normalizedDescriptor = {
    name:
      serviceDescriptor.name ||
      serviceDescriptor.service_id ||
      serviceDescriptor.serviceId ||
      serviceInterfaceCid,
    namespace:
      serviceDescriptor.namespace ||
      serviceDescriptor.service_namespace ||
      serviceDescriptor.serviceNamespace ||
      'handsfree.meta_glasses.mobile',
    version: serviceDescriptor.version || '0.1.0',
    methods: normalizeMethodDefinitions(serviceDescriptor.methods),
    errors: normalizeErrorDefinitions(serviceDescriptor.errors),
    requires: Array.isArray(serviceDescriptor.requires)
      ? serviceDescriptor.requires.filter((item) => typeof item === 'string')
      : [],
    compatibility: normalizeDescriptorRecord(serviceDescriptor.compatibility),
  };
  const metadata = normalizeDescriptorMetadata(serviceDescriptor.metadata);
  if (Object.keys(metadata).length > 0) {
    normalizedDescriptor.metadata = metadata;
  }
  return normalizedDescriptor;
}

function descriptorServiceId(serviceInterfaceCid, serviceDescriptor) {
  if (!isObject(serviceDescriptor)) {
    return serviceInterfaceCid;
  }
  return (
    serviceDescriptor.service_id ||
    serviceDescriptor.serviceId ||
    serviceDescriptor.name ||
    serviceDescriptor.namespace ||
    serviceInterfaceCid
  );
}

function descriptorOperation(operation, serviceDescriptor) {
  if (operation) {
    return operation;
  }
  if (Array.isArray(serviceDescriptor?.methods)) {
    const method = serviceDescriptor.methods.find(
      (candidate) => isObject(candidate) && typeof candidate.name === 'string'
    );
    if (method?.name) {
      return method.name;
    }
  }
  return 'invoke';
}

function buildOrbBindingMetadata(payload, bindingHandle) {
  const serviceInterfaceCid = payload.service_interface_cid;
  const normalizedDescriptor = normalizeServiceDescriptor(
    serviceInterfaceCid,
    payload.service_descriptor
  );
  const descriptorMetadata = isObject(normalizedDescriptor?.metadata)
    ? normalizedDescriptor.metadata
    : {};
  const descriptorCid = normalizedDescriptor
    ? localCid('mcp-interface', normalizedDescriptor)
    : serviceInterfaceCid;
  const serviceId = descriptorServiceId(serviceInterfaceCid, payload.service_descriptor);
  const operation = descriptorOperation(payload.operation, payload.service_descriptor);
  const transport = payload.transport_preference || 'mcp-server';

  return {
    handle: bindingHandle,
    interface_cid: serviceInterfaceCid,
    descriptor_cid: descriptorCid,
    service_id: serviceId,
    operation,
    transport,
    transport_binding: {
      transport,
      service_id: serviceId,
      operation,
      metadata: definedEntries({
        descriptor_cid: descriptorCid,
        descriptor_available: isObject(payload.service_descriptor),
        descriptor_kind: normalizedDescriptor ? 'mcp-idl' : undefined,
        provider_name: descriptorMetadata.provider_name,
        server_family: descriptorMetadata.server_family,
        tool_name: descriptorMetadata.tool_name,
        interface_descriptor: normalizedDescriptor || undefined,
      }),
    },
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
  const controlSurfaceArtifacts = buildMobileOrbControlSurfaceArtifacts(
    operation,
    {
      ...defaults,
      ...action,
      correlation_id:
        action.correlation_id ||
        action.correlationId ||
        defaults.correlation_id ||
        defaults.correlationId,
    },
    {
      receipt_cid:
        action.orb_receipt_cid ||
        action.receipt_cid ||
        defaults.orb_receipt_cid ||
        defaults.receipt_cid,
      reason: 'Display widget action normalized by Hallucinate App control-surface contract.',
    }
  );

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
    policy_decision: normalizePolicyDecision(controlSurfaceArtifacts.policy_decision, {
      operation,
      payload: action,
      receipt_cid: controlSurfaceArtifacts.mediation_receipt?.receipt_id,
      reason: 'Display widget action normalized by Hallucinate App control-surface contract.',
    }),
    control_surface_contract_ref: controlSurfaceArtifacts.control_surface_contract_ref,
    interaction_envelope: controlSurfaceArtifacts.interaction_envelope,
    normalized_intent: controlSurfaceArtifacts.normalized_intent,
    mediation_receipt: controlSurfaceArtifacts.mediation_receipt,
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
      const artifacts = buildMobileOrbControlSurfaceArtifacts(
        'register_edge_capabilities',
        {
          ...payload,
          edge_session_id: DEFAULT_EDGE_SESSION_ID,
        },
        {
          emitted_at: nowIso(now),
          reason: 'Mobile ORB edge registration normalized by Hallucinate App control-surface contract.',
        }
      );
      return {
        edge_session_id: DEFAULT_EDGE_SESSION_ID,
        accepted_interface_cids: payload.local_interface_cids || [],
        policy_cid: null,
        ...controlSurfaceFields(artifacts),
        expires_at: null,
      };
    },
    async publishGlassesEvent(payload) {
      const eventCid = localCid('event', payload);
      const receiptCid = localCid('receipt', payload);
      const artifacts = buildMobileOrbControlSurfaceArtifacts(
        'publish_glasses_event',
        { ...payload, event_cid: eventCid },
        {
          receipt_cid: receiptCid,
          emitted_at: payload.observed_at || nowIso(now),
          reason: 'Meta-glasses event normalized by Hallucinate App control-surface contract.',
        }
      );
      return {
        event_cid: eventCid,
        accepted: isMediationInvoked(artifacts),
        routed_operations: [],
        receipt_cid: receiptCid,
        ...controlSurfaceFields(artifacts),
      };
    },
    async bindService(payload) {
      const bindingHandle =
        payload.binding_handle ||
        `${DEFAULT_SERVICE_BINDING}:${payload.service_interface_cid || payload.operation || 'unknown'}`;
      const artifacts = buildMobileOrbControlSurfaceArtifacts(
        'bind_service',
        { ...payload, binding_handle: bindingHandle },
        {
          emitted_at: nowIso(now),
          reason: 'Service descriptor binding normalized by Hallucinate App control-surface contract.',
        }
      );
      return {
        binding_handle: bindingHandle,
        transport: payload.transport_preference || 'http',
        granted_capabilities: [],
        ...controlSurfaceFields(artifacts),
        orb_binding: buildOrbBindingMetadata(payload, bindingHandle),
        expires_at: null,
      };
    },
    async invokeService(payload) {
      const receiptCid = localCid('receipt', payload);
      const artifacts = buildMobileOrbControlSurfaceArtifacts(
        'invoke_service',
        payload,
        {
          receipt_cid: receiptCid,
          reason: 'Service invocation normalized by Hallucinate App control-surface contract.',
        }
      );
      return {
        ok: true,
        service_result: {},
        output_refs: [receiptCid],
        provenance_refs: [],
        receipt_cid: receiptCid,
        ...controlSurfaceFields(artifacts),
        follow_up_actions: [],
      };
    },
    async subscribeServiceUpdates(payload) {
      const subscriptionId = `local:subscription:${payload.operation || 'updates'}`;
      const receiptCid = localCid('receipt', payload);
      const artifacts = buildMobileOrbControlSurfaceArtifacts(
        'subscribe_service_updates',
        { ...payload, subscription_id: subscriptionId },
        {
          receipt_cid: receiptCid,
          emitted_at: nowIso(now),
          reason: 'Service update subscription normalized by Hallucinate App control-surface contract.',
        }
      );
      return {
        subscription_id: subscriptionId,
        receipt_cid: receiptCid,
        generation_key: `${payload.binding_handle}:${payload.operation}:${nowIso(now)}`,
        ...controlSurfaceFields(artifacts),
        subscription: {
          ...payload,
          subscription_id: subscriptionId,
          receipt_cid: receiptCid,
          generation_key: `${payload.binding_handle}:${payload.operation}:${nowIso(now)}`,
          status: 'active',
          subscribed_at: nowIso(now),
          ...controlSurfaceFields(artifacts),
        },
      };
    },
    async dispatchGlassesResponse(payload) {
      const receiptCid = localCid('receipt', payload);
      const artifacts = buildMobileOrbControlSurfaceArtifacts(
        'dispatch_glasses_response',
        payload,
        {
          receipt_cid: receiptCid,
          reason: 'Glasses response dispatch normalized by Hallucinate App control-surface contract.',
        }
      );
      return {
        dispatched_actions: payload.result?.follow_up_actions || [],
        display_widget_action: payload.result?.display_widget_action || null,
        spoken_text: payload.result?.spoken_text || null,
        receipt_cid: receiptCid,
        ...controlSurfaceFields(artifacts),
      };
    },
    async revokeBinding(payload) {
      const receiptCid = localCid('receipt', payload);
      const artifacts = buildMobileOrbControlSurfaceArtifacts(
        'revoke_binding',
        payload,
        {
          receipt_cid: receiptCid,
          reason: 'Service binding revocation normalized by Hallucinate App control-surface contract.',
        }
      );
      return {
        revoked: true,
        receipt_cid: receiptCid,
        ...controlSurfaceFields(artifacts),
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
    this.orbStateStore = options.orbStateStore || null;
    this.edgeId = options.edgeId || DEFAULT_EDGE_ID;
    this.platform = options.platform || 'simulator';
    this.device = options.device || {};
    this.localInterfaceCids = options.localInterfaceCids || [
      localInterfaceKey(MOBILE_ORB_BRIDGE_INTERFACE),
      localInterfaceKey(DISPLAY_WIDGET_BRIDGE_INTERFACE),
    ];
    this.edgeSession = null;
    this.bindings = new Map();
    this.subscriptions = new Map();
    this.eventLog = [];
    this.receiptLog = [];
  }

  getEdgeSession() {
    return this.edgeSession;
  }

  getEventLog() {
    return [...this.eventLog];
  }

  getOrbStateSnapshot() {
    return {
      edge_session_id: this.edgeSession?.edge_session_id || null,
      bindings: Array.from(this.bindings.values()),
      subscriptions: Array.from(this.subscriptions.values()),
    };
  }

  getDiagnostics() {
    const diagnosticRecords = [
      this.edgeSession,
      ...this.eventLog,
      ...Array.from(this.bindings.values()),
      ...Array.from(this.subscriptions.values()),
      ...this.receiptLog,
    ].filter(isObject);
    const descriptorCids = uniqueStrings([
      ...this.localInterfaceCids,
      ...diagnosticRecords.flatMap(collectDescriptorCids),
    ]);
    const policyCids = uniqueStrings(diagnosticRecords.flatMap(collectControlSurfacePolicyCids));
    const receiptCids = uniqueStrings(diagnosticRecords.flatMap(collectReceiptCids));
    const fallbackDetails = diagnosticRecords.flatMap(collectFallbackDetails);
    const capabilitySummary = capabilityCounts(this.edgeSession);
    const bindingState = Array.from(this.bindings.entries()).map(([
      bindingHandle,
      binding,
    ]) => ({
      binding_handle: bindingHandle,
      state: binding.status || binding.runtime_binding?.status || 'active',
      service_interface_cid: binding.service_interface_cid || binding.orb_binding?.interface_cid || null,
      service_id: binding.orb_binding?.service_id || null,
      operation: binding.operation || binding.orb_binding?.operation || null,
      transport: binding.transport || binding.transport_preference || binding.orb_binding?.transport || null,
      descriptor_cid: binding.orb_binding?.descriptor_cid || null,
      runtime_status: binding.runtime_binding?.status || null,
      runtime_reason: binding.runtime_binding?.reason || null,
      receipt_cid: binding.mediation_receipt?.receipt_id || null,
    }));
    const revokedBindingState = this.receiptLog
      .filter((receipt) => receipt.operation === 'revoke_binding')
      .map((receipt) => ({
        binding_handle: receipt.binding_handle || null,
        state: 'revoked',
        service_interface_cid: null,
        service_id: null,
        operation: null,
        transport: null,
        descriptor_cid: null,
        runtime_status: null,
        runtime_reason: 'revoke_binding',
        receipt_cid: receipt.receipt_cid,
      }));

    return {
      contract: MOBILE_ORB_DIAGNOSTICS_CONTRACT,
      source: 'mobile',
      mode: diagnosticsMode(this.edgeSession?.platform || this.platform),
      registered: Boolean(this.edgeSession?.edge_session_id),
      edge_session_id: this.edgeSession?.edge_session_id || null,
      edge_id: this.edgeSession?.edge_id || this.edgeId,
      platform: this.edgeSession?.platform || this.platform,
      policy_cid: this.edgeSession?.policy_cid || null,
      control_surface_contract_ref: this.edgeSession?.control_surface_contract_ref || null,
      mediation_receipt: this.edgeSession?.mediation_receipt || null,
      accepted_interface_cids: this.edgeSession?.accepted_interface_cids || [],
      dat_capabilities: this.edgeSession?.dat_capabilities || null,
      capability_counts: capabilitySummary,
      backend_capability_counts: capabilitySummary,
      descriptor_cids: descriptorCids,
      policy_cids: policyCids,
      receipt_cids: receiptCids,
      receipts_count: this.receiptLog.length,
      binding_state: {
        active_count: bindingState.filter((binding) => (
          ['active', 'ready', 'unresolved', 'invalid'].includes(binding.state)
        )).length,
        revoked_count: revokedBindingState.length,
        bindings: [...bindingState, ...revokedBindingState],
      },
      fallback_reasons: uniqueStrings(fallbackDetails.map((detail) => detail.reason)),
      fallback_details: fallbackDetails,
      bindings_count: this.bindings.size,
      bindings: Array.from(this.bindings.entries()).map(([bindingHandle, binding]) => ({
        binding_handle: bindingHandle,
        service_interface_cid: binding.service_interface_cid || null,
        service_id: binding.orb_binding?.service_id || null,
        descriptor_cid: binding.orb_binding?.descriptor_cid || null,
        operation: binding.operation || binding.orb_binding?.operation || null,
        transport: binding.transport || binding.orb_binding?.transport || null,
        orb_binding: binding.orb_binding || null,
      })),
      subscriptions_count: this.subscriptions.size,
      subscriptions: Array.from(this.subscriptions.entries()).map(([
        subscriptionId,
        subscription,
      ]) => ({
        subscription_id: subscriptionId,
        binding_handle: subscription.binding_handle,
        operation: subscription.operation,
        stream: subscription.stream,
        generation_key: subscription.generation_key,
        receipt_cid: subscription.receipt_cid,
        status: subscription.status || 'active',
        service_id: subscription.orb_binding?.service_id || null,
      })),
      events_count: this.eventLog.length,
      latest_event_cid: this.eventLog[this.eventLog.length - 1]?.event_cid || null,
    };
  }

  recordReceiptDiagnostics(operation, response = {}, context = {}) {
    const receiptCid =
      response?.receipt_cid ||
      response?.mediation_receipt?.receipt_id ||
      context.receipt_cid ||
      context.receiptCid;
    if (!receiptCid) {
      return null;
    }
    const record = definedEntries({
      operation,
      receipt_cid: receiptCid,
      edge_session_id: context.edge_session_id || this.edgeSession?.edge_session_id,
      binding_handle: context.binding_handle,
      correlation_id: context.correlation_id,
      parent_receipt_cids: context.parent_receipt_cids,
      fallback: context.fallback,
      display_widget_action: response.display_widget_action,
      follow_up_actions: response.follow_up_actions,
      policy_decision: response.policy_decision,
      mediation_receipt: response.mediation_receipt,
      output_refs: response.output_refs,
    });
    this.receiptLog = [
      ...this.receiptLog.filter((item) => item.receipt_cid !== receiptCid),
      record,
    ].slice(-50);
    return record;
  }

  hydrateEdgeSession(session) {
    const normalized = normalizeEdgeSessionSnapshot(session);
    if (!normalized) {
      return null;
    }
    this.edgeSession = normalized;
    return this.edgeSession;
  }

  hydrateOrbState(state) {
    if (!isObject(state)) {
      return this.getOrbStateSnapshot();
    }
    if (
      state.edge_session_id &&
      this.edgeSession?.edge_session_id &&
      state.edge_session_id !== this.edgeSession.edge_session_id
    ) {
      this.bindings.clear();
      this.subscriptions.clear();
      return this.getOrbStateSnapshot();
    }

    const bindings = Array.isArray(state.bindings) ? state.bindings.filter(isObject) : [];
    this.bindings = new Map(
      bindings
        .filter((binding) => typeof binding.binding_handle === 'string')
        .map((binding) => [binding.binding_handle, binding])
    );
    const bindingHandles = new Set(this.bindings.keys());
    const subscriptions = Array.isArray(state.subscriptions)
      ? state.subscriptions.filter(isObject)
      : [];
    this.subscriptions = new Map(
      subscriptions
        .filter((subscription) => (
          typeof subscription.subscription_id === 'string' &&
          bindingHandles.has(subscription.binding_handle)
        ))
        .map((subscription) => [subscription.subscription_id, subscription])
    );
    return this.getOrbStateSnapshot();
  }

  async restoreOrbState() {
    if (!this.orbStateStore?.load) {
      return this.getOrbStateSnapshot();
    }
    return this.hydrateOrbState(await this.orbStateStore.load());
  }

  async persistOrbState() {
    const snapshot = {
      ...this.getOrbStateSnapshot(),
      saved_at: nowIso(this.now),
    };
    if (this.orbStateStore?.save) {
      return this.orbStateStore.save(snapshot);
    }
    return snapshot;
  }

  findReusableServiceBinding(serviceInterfaceCid, operation) {
    for (const binding of this.bindings.values()) {
      const bindingOperation = binding.operation || binding.orb_binding?.operation;
      const bindingInterfaceCid =
        binding.service_interface_cid || binding.orb_binding?.interface_cid;
      if (bindingInterfaceCid === serviceInterfaceCid && bindingOperation === operation) {
        return binding;
      }
    }
    return null;
  }

  serviceBindingResultFromRecord(binding) {
    return {
      payload: null,
      response: {
        ...binding,
        binding_handle: binding.binding_handle || binding.orb_binding?.handle,
      },
      reused: true,
    };
  }

  findReusableSubscription(bindingHandle, operation, stream) {
    for (const subscription of this.subscriptions.values()) {
      if (
        subscription.binding_handle === bindingHandle &&
        subscription.operation === operation &&
        (subscription.stream || 'updates') === (stream || 'updates')
      ) {
        return subscription;
      }
    }
    return null;
  }

  subscriptionResultFromRecord(subscription) {
    return {
      payload: null,
      response: {
        subscription_id: subscription.subscription_id,
        receipt_cid: subscription.receipt_cid,
        generation_key: subscription.generation_key,
        subscription,
      },
      reused: true,
    };
  }

  async removeBindingState(bindingHandle) {
    this.bindings.delete(bindingHandle);
    for (const [subscriptionId, subscription] of this.subscriptions.entries()) {
      if (subscription.binding_handle === bindingHandle) {
        this.subscriptions.delete(subscriptionId);
      }
    }
    await this.persistOrbState();
  }

  async restoreEdgeSession() {
    if (!this.edgeSessionStore?.load) {
      return null;
    }
    const restored = this.hydrateEdgeSession(await this.edgeSessionStore.load());
    if (restored) {
      await this.restoreOrbState();
    }
    return restored;
  }

  async clearEdgeSession() {
    this.edgeSession = null;
    this.bindings.clear();
    this.subscriptions.clear();
    this.eventLog = [];
    this.receiptLog = [];
    if (this.edgeSessionStore?.clear) {
      await this.edgeSessionStore.clear();
    }
    if (this.orbStateStore?.clear) {
      await this.orbStateStore.clear();
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
    const previousEdgeSessionId = this.edgeSession?.edge_session_id || null;
    const response = await this.backend.registerEdgeCapabilities(payload);
    const artifacts = hasCanonicalControlSurfaceArtifacts(response)
      ? response
      : buildMobileOrbControlSurfaceArtifacts(
        'register_edge_capabilities',
        {
          ...payload,
          edge_session_id: response.edge_session_id,
        },
        {
          emitted_at: nowIso(this.now),
          reason: 'Mobile ORB edge registration normalized by Hallucinate App control-surface contract.',
        }
      );
    this.edgeSession = {
      ...response,
      ...controlSurfaceFields(artifacts),
      edge_id: payload.edge_id,
      platform: payload.platform,
      device_id: payload.device_id || null,
      dat_capabilities: payload.dat_capabilities,
      registered_at: nowIso(this.now),
    };
    if (this.edgeSessionStore?.save) {
      await this.edgeSessionStore.save(this.edgeSession);
    }
    if (previousEdgeSessionId && previousEdgeSessionId !== this.edgeSession.edge_session_id) {
      this.bindings.clear();
      this.subscriptions.clear();
      await this.persistOrbState();
    }
    this.recordReceiptDiagnostics('register_edge_capabilities', this.edgeSession, {
      edge_session_id: this.edgeSession.edge_session_id,
    });
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
    const artifacts = hasCanonicalControlSurfaceArtifacts(response)
      ? response
      : buildMobileOrbControlSurfaceArtifacts(
        'publish_glasses_event',
        {
          ...eventPayload,
          event_cid: response.event_cid,
        },
        {
          receipt_cid: response.receipt_cid,
          emitted_at: eventPayload.observed_at,
          reason: 'Meta-glasses event normalized by Hallucinate App control-surface contract.',
        }
      );
    const normalizedResponse = {
      ...response,
      accepted: response.accepted ?? isMediationInvoked(artifacts),
      ...controlSurfaceFields(artifacts),
    };
    const event = {
      ...eventPayload,
      event_cid: normalizedResponse.event_cid,
      accepted: normalizedResponse.accepted,
      receipt_cid: normalizedResponse.receipt_cid,
      ...controlSurfaceFields(artifacts),
    };
    this.eventLog.push(event);
    this.recordReceiptDiagnostics('publish_glasses_event', normalizedResponse, {
      edge_session_id: edge.edge_session_id,
      correlation_id: eventPayload.correlation_id,
      parent_receipt_cids: eventPayload.parent_receipt_cids,
    });
    return {
      payload: eventPayload,
      response: normalizedResponse,
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
    const artifacts = hasCanonicalControlSurfaceArtifacts(response)
      ? response
      : buildMobileOrbControlSurfaceArtifacts(
        'bind_service',
        {
          ...payload,
          binding_handle: response.binding_handle,
        },
        {
          emitted_at: nowIso(this.now),
          reason: 'Service descriptor binding normalized by Hallucinate App control-surface contract.',
        }
      );
    const artifactFields = controlSurfaceFields(artifacts);
    const normalizedResponse = {
      ...response,
      ...artifactFields,
      policy_decision: artifactFields.policy_decision || response.policy_decision,
    };
    const orbBinding = response.orb_binding || buildOrbBindingMetadata(payload, response.binding_handle);
    this.bindings.set(response.binding_handle, {
      ...normalizedResponse,
      service_interface_cid: payload.service_interface_cid,
      service_descriptor: payload.service_descriptor || null,
      operation: payload.operation || null,
      orb_binding: orbBinding,
      bound_at: nowIso(this.now),
    });
    await this.persistOrbState();
    this.recordReceiptDiagnostics('bind_service', normalizedResponse, {
      edge_session_id: edge.edge_session_id,
      binding_handle: response.binding_handle,
    });
    return {
      payload,
      response: {
        ...normalizedResponse,
        orb_binding: orbBinding,
      },
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
    let response = await this.backend.invokeService(payload);
    const artifacts = hasCanonicalControlSurfaceArtifacts(response)
      ? response
      : buildMobileOrbControlSurfaceArtifacts(
        'invoke_service',
        payload,
        {
          receipt_cid: response.receipt_cid,
          reason: 'Service invocation normalized by Hallucinate App control-surface contract.',
        }
      );
    response = {
      ...response,
      ...controlSurfaceFields(artifacts),
    };
    if (binding?.orb_binding && isObject(response?.service_result)) {
      response = {
        ...response,
        service_result: {
          ...response.service_result,
          orb_binding: response.service_result.orb_binding || binding.orb_binding,
        },
      };
    }
    this.recordReceiptDiagnostics('invoke_service', response, {
      edge_session_id: this.edgeSession?.edge_session_id,
      binding_handle: bindingHandle,
      correlation_id: payload.correlation_id,
      parent_receipt_cids: payload.parent_receipt_cids,
      fallback: args.fallback,
    });
    return {
      payload,
      response,
    };
  }

  async subscribeServiceUpdates(bindingHandle, operation, options = {}) {
    const binding = this.bindings.get(bindingHandle);
    if (!binding && !options.allow_untracked_binding) {
      throw new Error(`Cannot subscribe to untracked service binding: ${bindingHandle}`);
    }
    const payload = definedEntries({
      binding_handle: bindingHandle,
      operation,
      arguments: options.arguments || {},
      stream: options.stream || 'updates',
      correlation_id: options.correlation_id || `mobile-orb-stream-${operation}`,
    });
    const response = await this.backend.subscribeServiceUpdates(payload);
    const artifacts = hasCanonicalControlSurfaceArtifacts(response)
      ? response
      : buildMobileOrbControlSurfaceArtifacts(
        'subscribe_service_updates',
        {
          ...payload,
          subscription_id: response.subscription_id,
        },
        {
          receipt_cid: response.receipt_cid,
          emitted_at: nowIso(this.now),
          reason: 'Service update subscription normalized by Hallucinate App control-surface contract.',
        }
      );
    const artifactFields = controlSurfaceFields(artifacts);
    const normalizedResponse = {
      ...response,
      ...artifactFields,
    };
    const subscription = {
      ...(normalizedResponse.subscription || {}),
      ...payload,
      subscription_id: normalizedResponse.subscription_id,
      receipt_cid: normalizedResponse.receipt_cid,
      generation_key: normalizedResponse.generation_key,
      orb_binding: normalizedResponse.subscription?.orb_binding || binding?.orb_binding || null,
      status: normalizedResponse.subscription?.status || 'active',
      subscribed_at: normalizedResponse.subscription?.subscribed_at || nowIso(this.now),
      ...artifactFields,
    };
    this.subscriptions.set(normalizedResponse.subscription_id, subscription);
    await this.persistOrbState();
    this.recordReceiptDiagnostics('subscribe_service_updates', normalizedResponse, {
      edge_session_id: this.edgeSession?.edge_session_id,
      binding_handle: bindingHandle,
      correlation_id: payload.correlation_id,
    });
    return {
      payload,
      response: {
        ...normalizedResponse,
        subscription,
      },
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
    const artifacts = hasCanonicalControlSurfaceArtifacts(response)
      ? response
      : buildMobileOrbControlSurfaceArtifacts(
        'dispatch_glasses_response',
        payload,
        {
          receipt_cid: response.receipt_cid,
          reason: 'Glasses response dispatch normalized by Hallucinate App control-surface contract.',
        }
      );
    const normalizedResponse = {
      ...response,
      ...controlSurfaceFields(artifacts),
    };
    const actions = [
      ...(Array.isArray(normalizedResponse.dispatched_actions)
        ? normalizedResponse.dispatched_actions
        : []),
      ...(Array.isArray(result.follow_up_actions) ? result.follow_up_actions : []),
    ];
    const displayWidgetAction =
      normalizedResponse.display_widget_action ||
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
          orb_receipt_cid: actionPayload.orb_receipt_cid || normalizedResponse.receipt_cid,
          fallback: actionPayload.fallback || fallback,
        });
      if (isDisplayWidgetActionId(actionItem.id || actionItem.type)) {
        localResults.push(await this.localActionExecutor({ actionItem, navigation }));
      }
    }
    this.recordReceiptDiagnostics('dispatch_glasses_response', normalizedResponse, {
      edge_session_id: edge.edge_session_id,
      correlation_id: payload.correlation_id,
      parent_receipt_cids: payload.parent_receipt_cids,
      fallback,
    });

    return {
      payload,
      response: normalizedResponse,
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
    subscribeUpdates = false,
    updateStream = 'updates',
    subscriptionArguments = null,
    reuseBinding = true,
    reuseSubscription = true,
  }) {
    const event = await this.publishGlassesEvent(eventType, eventPayload, {
      correlation_id: correlationId,
    });

    const bindFreshService = () => this.bindService({
      service_interface_cid: serviceInterfaceCid,
      service_descriptor: serviceDescriptor,
      operation: serviceOperation,
      user_intent: eventPayload.intent || eventPayload.command || eventType,
    });
    const buildInvokeOptions = () => ({
      correlation_id: event.payload.correlation_id,
      parent_receipt_cids: [event.response.receipt_cid].filter(Boolean),
      glasses_context: {
        event_type: eventType,
        event_cid: event.response.event_cid,
        payload: eventPayload,
      },
    });
    const subscribeForBinding = async (bindingResult) => {
      if (!subscribeUpdates) {
        return null;
      }
      const bindingHandle = bindingResult.response.binding_handle;
      const existingSubscription = reuseSubscription
        ? this.findReusableSubscription(bindingHandle, serviceOperation, updateStream)
        : null;
      if (existingSubscription) {
        return this.subscriptionResultFromRecord(existingSubscription);
      }
      return this.subscribeServiceUpdates(
        bindingHandle,
        serviceOperation,
        {
          arguments: subscriptionArguments || serviceArguments,
          stream: updateStream,
          correlation_id: event.payload.correlation_id,
        }
      );
    };
    const runServiceFlow = async (bindingResult) => {
      const invokedResult = await this.invokeService(
        bindingResult.response.binding_handle,
        serviceOperation,
        serviceArguments,
        buildInvokeOptions()
      );
      const subscriptionResult = await subscribeForBinding(bindingResult);
      return {
        binding: bindingResult,
        invoked: invokedResult,
        subscription: subscriptionResult,
      };
    };

    const reusableBinding = reuseBinding
      ? this.findReusableServiceBinding(serviceInterfaceCid, serviceOperation)
      : null;
    let binding = reusableBinding
      ? this.serviceBindingResultFromRecord(reusableBinding)
      : await bindFreshService();
    let invoked;
    let subscription;

    try {
      ({ binding, invoked, subscription } = await runServiceFlow(binding));
    } catch (error) {
      if (!isStaleBindingError(error)) {
        throw error;
      }
      await this.removeBindingState(binding.response.binding_handle);
      binding = await bindFreshService();
      ({ binding, invoked, subscription } = await runServiceFlow(binding));
    }

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
      subscription,
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
    const artifacts = hasCanonicalControlSurfaceArtifacts(response)
      ? response
      : buildMobileOrbControlSurfaceArtifacts(
        'revoke_binding',
        payload,
        {
          receipt_cid: response.receipt_cid,
          reason: 'Service binding revocation normalized by Hallucinate App control-surface contract.',
        }
      );
    const normalizedResponse = {
      ...response,
      ...controlSurfaceFields(artifacts),
    };
    if (normalizedResponse.revoked) {
      this.bindings.delete(bindingHandle);
      for (const [subscriptionId, subscription] of this.subscriptions.entries()) {
        if (subscription.binding_handle === bindingHandle) {
          this.subscriptions.delete(subscriptionId);
        }
      }
      await this.persistOrbState();
    }
    this.recordReceiptDiagnostics('revoke_binding', normalizedResponse, {
      edge_session_id: this.edgeSession?.edge_session_id,
      binding_handle: bindingHandle,
      correlation_id: payload.correlation_id,
    });
    return {
      payload,
      response: normalizedResponse,
    };
  }
}

export function createMetaGlassesMobileOrbBridge(options = {}) {
  return new MetaGlassesMobileOrbBridge(options);
}
