import AsyncStorage from '@react-native-async-storage/async-storage';

export const META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY =
  '@handsfree_meta_glasses_orb_edge_session';

const PLATFORMS = new Set(['ios', 'android', 'simulator']);

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function stringOrNull(value) {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function stringArray(value) {
  return Array.isArray(value)
    ? value.filter((item) => typeof item === 'string' && item.length > 0)
    : [];
}

function normalizeCapabilities(value = {}) {
  const capabilities = isObject(value) ? value : {};
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

export function normalizeMetaGlassesOrbEdgeSession(value) {
  if (!isObject(value)) {
    return null;
  }

  const edgeSessionId = stringOrNull(value.edge_session_id);
  const policyCid = stringOrNull(value.policy_cid);
  const controlSurfaceContractRef =
    stringOrNull(value.control_surface_contract_ref) ||
    stringOrNull(value.mediation_receipt?.control_surface_contract_ref) ||
    stringOrNull(value.interaction_envelope?.control_surface_contract_ref);
  const edgeId = stringOrNull(value.edge_id) || 'handsfree-mobile-orb-edge';
  const platform = PLATFORMS.has(value.platform) ? value.platform : 'simulator';
  if (!edgeSessionId || (!controlSurfaceContractRef && !policyCid)) {
    return null;
  }

  return {
    edge_session_id: edgeSessionId,
    edge_id: edgeId,
    platform,
    device_id: stringOrNull(value.device_id),
    policy_cid: policyCid,
    control_surface_contract_ref: controlSurfaceContractRef,
    interaction_envelope: isObject(value.interaction_envelope) ? value.interaction_envelope : null,
    normalized_intent: isObject(value.normalized_intent)
      ? value.normalized_intent
      : isObject(value.interaction_envelope?.normalized_intent)
        ? value.interaction_envelope.normalized_intent
        : null,
    policy_decision: isObject(value.policy_decision)
      ? value.policy_decision
      : isObject(value.mediation_receipt?.policy_decision)
        ? value.mediation_receipt.policy_decision
        : null,
    mediation_receipt: isObject(value.mediation_receipt) ? value.mediation_receipt : null,
    accepted_interface_cids: stringArray(value.accepted_interface_cids),
    dat_capabilities: normalizeCapabilities(value.dat_capabilities),
    registered_at:
      stringOrNull(value.registered_at) || new Date(0).toISOString(),
    expires_at: stringOrNull(value.expires_at),
  };
}

export function createMetaGlassesOrbEdgeSessionStore(storage = AsyncStorage) {
  return {
    async load() {
      try {
        const raw = await storage.getItem(META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY);
        if (!raw) {
          return null;
        }
        return normalizeMetaGlassesOrbEdgeSession(JSON.parse(raw));
      } catch (error) {
        console.error('Failed to load Meta glasses ORB edge session:', error);
        return null;
      }
    },

    async save(session) {
      const normalized = normalizeMetaGlassesOrbEdgeSession(session);
      if (!normalized) {
        throw new Error('Cannot persist an invalid Meta glasses ORB edge session.');
      }
      await storage.setItem(
        META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY,
        JSON.stringify(normalized)
      );
      return normalized;
    },

    async clear() {
      await storage.removeItem(META_GLASSES_ORB_EDGE_SESSION_STORAGE_KEY);
    },
  };
}

export const metaGlassesOrbEdgeSessionStore = createMetaGlassesOrbEdgeSessionStore();
