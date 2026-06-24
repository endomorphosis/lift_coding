export const META_GLASSES_MULTIMODAL_IO_CONTRACT =
  'handsfree.meta-glasses/multimodal-io-control-plane@0.1.0';

export const META_GLASSES_MULTIMODAL_IO_MOCK_BOUNDARY =
  'handsfree.meta-glasses/mock-multimodal-io-boundary@0.1.0';

export const MCP_PLUS_PLUS_ENVELOPE_PROFILE =
  'swissknife.mcp++/event-envelope@0.1.0';

export const META_GLASSES_CONTROL_PLANE_DEVICES = [
  'camera',
  'microphone',
  'headphones',
  'display',
  'captouch',
  'Neural Band',
];

export const META_GLASSES_CONTROL_PLANE_EVENT_TYPES = [
  'camera.photo_ref',
  'camera.video_frame_ref',
  'microphone.route_state',
  'microphone.transcript_ref',
  'headphones.route_state',
  'headphones.playback_state',
  'display.lifecycle_state',
  'display.action',
  'captouch.intent',
  'Neural Band.intent',
  'permission.state',
  'transport.handoff',
];

export const META_GLASSES_TRANSPORT_ASSUMPTIONS = {
  bluetooth:
    'Bluetooth is a phone-to-glasses route for audio profiles and local device state, not raw libp2p transport.',
  wifi:
    'Wi-Fi may carry app-level handoff traffic through the mobile edge or Web App path; raw radio sockets are out of scope.',
  datAvailability:
    'DAT camera/display capabilities are optional; unavailable, denied, or unsupported states emit fallback receipts.',
  ipfsLibp2pHandoff:
    'IPFS CIDs and libp2p peer/session identifiers live in envelope metadata for payload handoff and replay.',
  mcpPlusPlus:
    'MCP++ compatibility is provided by contract, operation, correlation, policy, and provenance envelope fields.',
};

export const META_GLASSES_REQUIRED_ENVELOPE_FIELDS = [
  'contract',
  'profile',
  'event_type',
  'device',
  'source',
  'edge_session_id',
  'app_binding_id',
  'correlation_id',
  'payload',
  'transport',
  'handoff',
  'fallback',
  'control_plane',
  'policy',
  'receipts',
];

export const META_GLASSES_MOCK_BOUNDARY_STATES = [
  'mock_ready',
  'dat_ready',
  'dat_unavailable',
  'permission_denied',
  'unsupported_capability',
  'route_degraded',
  'route_lost',
];

const EVENT_TYPE_SET = new Set(META_GLASSES_CONTROL_PLANE_EVENT_TYPES);
const DEVICE_SET = new Set(META_GLASSES_CONTROL_PLANE_DEVICES);

export function buildMetaGlassesControlPlaneEvent({
  event_type,
  device,
  edge_session_id,
  app_binding_id,
  correlation_id,
  payload = {},
  transport = {},
  handoff = {},
  fallback = {},
  policy = { outcome: 'allow', source: 'mock' },
  receipts = [],
}) {
  if (!EVENT_TYPE_SET.has(event_type)) {
    throw new Error(`Unsupported Meta glasses control-plane event type: ${event_type}`);
  }
  if (!DEVICE_SET.has(device)) {
    throw new Error(`Unsupported Meta glasses control-plane device: ${device}`);
  }

  return {
    contract: META_GLASSES_MULTIMODAL_IO_CONTRACT,
    profile: MCP_PLUS_PLUS_ENVELOPE_PROFILE,
    event_type,
    device,
    source: 'hardware-free-mock',
    edge_session_id,
    app_binding_id,
    correlation_id,
    payload,
    transport: {
      bluetooth: 'route-state',
      wifi: 'app-level-handoff',
      ...transport,
    },
    handoff: {
      ipfs_cids: [],
      libp2p_peer_id: null,
      libp2p_session_id: null,
      mcp_plus_plus_profile: MCP_PLUS_PLUS_ENVELOPE_PROFILE,
      ...handoff,
    },
    fallback: {
      dat_available: false,
      state: 'mock_ready',
      ...fallback,
    },
    control_plane: {
      route: 'swissknife.mobile_orb.publish_glasses_event',
      operation: 'publish_glasses_event',
    },
    policy,
    receipts,
  };
}
