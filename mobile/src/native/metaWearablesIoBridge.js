export const META_WEARABLES_IO_BRIDGE_CONTRACT =
  'handsfree.meta-glasses/mobile-io-bridge-routes@0.1.0';

export const META_WEARABLES_IO_BRIDGE_PROFILE =
  'swissknife.mcp++/mobile-bridge-route-event@0.1.0';

export const META_WEARABLES_IO_BRIDGE_EVENT_TYPES = [
  'camera',
  'microphone_route',
  'speaker_route',
  'headphone_route',
  'display',
  'permission',
  'unsupported',
  'disconnected',
  'stale_session',
  'degraded_route',
  'firmware_update',
  'dat_app_update',
  'fallback',
];

export const META_WEARABLES_IO_BRIDGE_ROUTE_LABELS = {
  camera: {
    capability: 'camera.photo_capture',
    bridgeRoute: 'dat-native-camera',
    bluetoothRouteLabel: null,
    wifiRouteLabel: 'mobile-app-control-plane',
  },
  microphone_route: {
    capability: 'microphone.input',
    bridgeRoute: 'phone-os-audio-input',
    bluetoothRouteLabel: 'bluetooth-hfp-input',
    wifiRouteLabel: null,
  },
  speaker_route: {
    capability: 'speaker.output',
    bridgeRoute: 'phone-os-audio-output',
    bluetoothRouteLabel: 'bluetooth-a2dp-output',
    wifiRouteLabel: null,
  },
  headphone_route: {
    capability: 'headphone.output',
    bridgeRoute: 'phone-os-audio-output',
    bluetoothRouteLabel: 'bluetooth-a2dp-output',
    wifiRouteLabel: null,
  },
  display: {
    capability: 'display.output',
    bridgeRoute: 'dat-native-display',
    bluetoothRouteLabel: null,
    wifiRouteLabel: 'display-webapp-handoff',
  },
  permission: {
    capability: 'permission.state',
    bridgeRoute: 'mobile-permission-gate',
    bluetoothRouteLabel: null,
    wifiRouteLabel: null,
  },
  unsupported: {
    capability: 'unsupported.capability',
    bridgeRoute: 'mobile-unsupported-gate',
    bluetoothRouteLabel: null,
    wifiRouteLabel: null,
  },
  disconnected: {
    capability: 'device.connection',
    bridgeRoute: 'mobile-device-session',
    bluetoothRouteLabel: 'bluetooth-device-link',
    wifiRouteLabel: null,
  },
  stale_session: {
    capability: 'device.session',
    bridgeRoute: 'mobile-device-session',
    bluetoothRouteLabel: 'bluetooth-device-link',
    wifiRouteLabel: null,
  },
  degraded_route: {
    capability: 'route.quality',
    bridgeRoute: 'mobile-route-monitor',
    bluetoothRouteLabel: 'bluetooth-route-degraded',
    wifiRouteLabel: 'wifi-route-degraded',
  },
  firmware_update: {
    capability: 'device.firmware',
    bridgeRoute: 'dat-native-update-gate',
    bluetoothRouteLabel: 'bluetooth-device-link',
    wifiRouteLabel: null,
  },
  dat_app_update: {
    capability: 'dat.app',
    bridgeRoute: 'dat-app-update-gate',
    bluetoothRouteLabel: null,
    wifiRouteLabel: 'dat-release-channel',
  },
  fallback: {
    capability: 'fallback.render_or_route',
    bridgeRoute: 'mobile-fallback',
    bluetoothRouteLabel: null,
    wifiRouteLabel: 'display-webapp-or-mobile-card',
  },
};

const EVENT_TYPE_SET = new Set(META_WEARABLES_IO_BRIDGE_EVENT_TYPES);

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function normalizeCidList(value) {
  if (!value) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.filter(Boolean).map(String);
  }
  return [String(value)];
}

function normalizeReceipts(receipts, eventType, correlationId) {
  const input = Array.isArray(receipts) ? receipts : receipts ? [receipts] : [];
  if (input.length === 0) {
    return [
      {
        kind: 'mcp++/mobile-bridge-route',
        receiptCid: `sha256:${eventType}:${correlationId}:receipt`,
        issuedBy: 'mobile-meta-wearables-io-bridge',
      },
    ];
  }

  return input.map((receipt) => {
    if (typeof receipt === 'string') {
      return {
        kind: 'mcp++/mobile-bridge-route',
        receiptCid: receipt,
        issuedBy: 'mobile-meta-wearables-io-bridge',
      };
    }
    return {
      kind: receipt.kind || receipt.receiptKind || 'mcp++/mobile-bridge-route',
      receiptCid: receipt.receiptCid || receipt.receipt_cid || receipt.cid || null,
      issuedBy: receipt.issuedBy || receipt.issued_by || 'mobile-meta-wearables-io-bridge',
      parentReceiptCids: normalizeCidList(
        receipt.parentReceiptCids || receipt.parent_receipt_cids
      ),
    };
  });
}

function normalizePolicyDecision(policyDecision) {
  const source = isObject(policyDecision) ? policyDecision : {};
  return {
    outcome: source.outcome || 'deny',
    reason: source.reason || source.reasons?.[0] || 'missing_policy_decision',
    source: source.source || 'mobile-bridge-contract',
    decisionId: source.decisionId || source.decision_id || null,
    scopes: Array.isArray(source.scopes) ? source.scopes : [],
  };
}

function normalizeControlPlaneDecision(controlPlaneDecision, eventType, capability) {
  const source = isObject(controlPlaneDecision) ? controlPlaneDecision : {};
  return {
    route: source.route || 'swissknife.mobile_orb.publish_meta_wearables_io_event',
    operation: source.operation || `publish_${eventType}`,
    decisionId: source.decisionId || source.decision_id || `route-${eventType}`,
    capability: source.capability || capability,
    allowed: source.allowed !== undefined ? Boolean(source.allowed) : true,
  };
}

function normalizePrivacy(privacy) {
  const source = isObject(privacy) ? privacy : {};
  return {
    redactionStrategy: source.redactionStrategy || source.redaction_strategy || 'metadata_only',
    redactedFields: Array.isArray(source.redactedFields)
      ? source.redactedFields
      : Array.isArray(source.redacted_fields)
        ? source.redacted_fields
        : ['raw_payload'],
    retention: source.retention || 'ephemeral',
    metadataCid: source.metadataCid || source.metadata_cid || null,
    rawPayloadIncluded: Boolean(source.rawPayloadIncluded || source.raw_payload_included),
  };
}

function normalizeFlowControl(flowControl) {
  const source = isObject(flowControl) ? flowControl : {};
  return {
    latencyMs: Number.isFinite(source.latencyMs)
      ? source.latencyMs
      : Number.isFinite(source.latency_ms)
        ? source.latency_ms
        : 0,
    backpressure: source.backpressure || 'none',
    queueDepth: Number.isFinite(source.queueDepth)
      ? source.queueDepth
      : Number.isFinite(source.queue_depth)
        ? source.queue_depth
        : 0,
    droppedMessages: Number.isFinite(source.droppedMessages)
      ? source.droppedMessages
      : Number.isFinite(source.dropped_messages)
        ? source.dropped_messages
        : 0,
  };
}

export function normalizeMetaWearablesIoBridgeEvent(input = {}) {
  const eventType = input.eventType || input.event_type;
  if (!EVENT_TYPE_SET.has(eventType)) {
    throw new Error(`Unsupported Meta Wearables I/O bridge event type: ${eventType}`);
  }

  const routeDefaults = META_WEARABLES_IO_BRIDGE_ROUTE_LABELS[eventType];
  const capability = input.capability || routeDefaults.capability;
  const appBindingId = input.appBindingId || input.app_binding_id;
  if (!appBindingId) {
    throw new Error('Meta Wearables I/O bridge events require appBindingId');
  }

  const correlationId =
    input.correlationId || input.correlation_id || `corr-${eventType}-${appBindingId}`;
  const payloadCids = normalizeCidList(
    input.payloadCids || input.payload_cids || input.payloadCid || input.payload_cid
  );

  return {
    contract: META_WEARABLES_IO_BRIDGE_CONTRACT,
    profile: META_WEARABLES_IO_BRIDGE_PROFILE,
    eventType,
    capability,
    readiness: input.readiness || 'ready',
    appBindingId,
    bridgeRoute: {
      provider: input.bridgeProvider || input.bridge_provider || 'mobile-meta-wearables-io-bridge',
      route: input.bridgeRoute || input.bridge_route || routeDefaults.bridgeRoute,
      routeId: input.routeId || input.route_id || `route-${eventType}-${appBindingId}`,
      generation: input.routeGeneration || input.route_generation || 1,
      bluetoothRouteLabel:
        input.bluetoothRouteLabel ||
        input.bluetooth_route_label ||
        routeDefaults.bluetoothRouteLabel,
      wifiRouteLabel:
        input.wifiRouteLabel || input.wifi_route_label || routeDefaults.wifiRouteLabel,
      rawTransportIsIpfsLibp2pOrMcp: false,
    },
    policyDecision: normalizePolicyDecision(input.policyDecision || input.policy_decision),
    controlPlaneDecision: normalizeControlPlaneDecision(
      input.controlPlaneDecision || input.control_plane_decision,
      eventType,
      capability
    ),
    payload: {
      cids: payloadCids,
      cidEnabled: Boolean(input.cidEnabled ?? input.cid_enabled ?? payloadCids.length > 0),
      inlinePayloadRedacted: true,
      summary: input.summary || null,
    },
    privacy: normalizePrivacy(input.privacy),
    flowControl: normalizeFlowControl(input.flowControl || input.flow_control),
    receipts: normalizeReceipts(input.receipts, eventType, correlationId),
    correlationId,
    routeLabels: {
      bluetooth: routeDefaults.bluetoothRouteLabel,
      wifi: routeDefaults.wifiRouteLabel,
    },
    emittedAt: input.emittedAt || input.emitted_at || null,
  };
}

export function buildMetaWearablesIoBridgeRouteEvents({
  appBindingId = 'swissknife.meta-glasses.binding.mgw-417',
  correlationPrefix = 'mgw417',
} = {}) {
  const readinessByEvent = {
    permission: 'permission_denied',
    unsupported: 'unsupported',
    disconnected: 'disconnected',
    stale_session: 'stale_session',
    degraded_route: 'degraded',
    firmware_update: 'firmware_update_required',
    dat_app_update: 'dat_app_update_required',
    fallback: 'fallback',
  };

  const payloadCidsByEvent = {
    camera: ['sha256:mgw417-camera-photo-redacted'],
    display: ['sha256:mgw417-display-widget-redacted'],
  };

  return META_WEARABLES_IO_BRIDGE_EVENT_TYPES.map((eventType) =>
    normalizeMetaWearablesIoBridgeEvent({
      eventType,
      appBindingId,
      correlationId: `${correlationPrefix}-${eventType}`,
      readiness: readinessByEvent[eventType] || 'ready',
      payloadCids: payloadCidsByEvent[eventType] || [],
      policyDecision: {
        outcome: eventType === 'permission' ? 'deny' : 'allow',
        reason: eventType === 'permission' ? 'permission_denied' : 'contract_fixture',
        source: 'mgw-417-mobile-bridge-contract',
        decisionId: `policy-${eventType}`,
        scopes: [META_WEARABLES_IO_BRIDGE_ROUTE_LABELS[eventType].capability],
      },
      controlPlaneDecision: {
        decisionId: `control-${eventType}`,
        operation: `publish_${eventType}`,
        allowed: eventType !== 'permission',
      },
      privacy: {
        redactionStrategy: 'content_reference_or_metadata_only',
        redactedFields: ['raw_payload', 'raw_radio_packets'],
        retention: eventType === 'camera' || eventType === 'display' ? 'session' : 'ephemeral',
      },
      flowControl: {
        latencyMs: eventType === 'degraded_route' ? 220 : 24,
        backpressure: eventType === 'degraded_route' ? 'throttled' : 'none',
        queueDepth: eventType === 'degraded_route' ? 3 : 0,
        droppedMessages: eventType === 'degraded_route' ? 1 : 0,
      },
      receipts: [
        {
          receiptCid: `sha256:mgw417-${eventType}-mcp-receipt`,
          parentReceiptCids: [],
        },
      ],
    })
  );
}

export default {
  META_WEARABLES_IO_BRIDGE_CONTRACT,
  META_WEARABLES_IO_BRIDGE_PROFILE,
  META_WEARABLES_IO_BRIDGE_EVENT_TYPES,
  META_WEARABLES_IO_BRIDGE_ROUTE_LABELS,
  normalizeMetaWearablesIoBridgeEvent,
  buildMetaWearablesIoBridgeRouteEvents,
};
