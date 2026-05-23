import AsyncStorage from '@react-native-async-storage/async-storage';

export const META_GLASSES_ORB_STATE_STORAGE_KEY =
  '@handsfree_meta_glasses_orb_bridge_state';

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function stringOrNull(value) {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function objectOrNull(value) {
  return isObject(value) ? value : null;
}

function normalizeBinding(value) {
  if (!isObject(value)) {
    return null;
  }
  const bindingHandle = stringOrNull(value.binding_handle);
  if (!bindingHandle) {
    return null;
  }

  const orbBinding = objectOrNull(value.orb_binding);
  return {
    binding_handle: bindingHandle,
    transport: stringOrNull(value.transport) || orbBinding?.transport || 'mcp-server',
    granted_capabilities: Array.isArray(value.granted_capabilities)
      ? value.granted_capabilities.filter((item) => typeof item === 'string')
      : [],
    policy_decision: objectOrNull(value.policy_decision) || {},
    expires_at: stringOrNull(value.expires_at),
    service_interface_cid:
      stringOrNull(value.service_interface_cid) || stringOrNull(orbBinding?.interface_cid),
    service_descriptor: objectOrNull(value.service_descriptor),
    operation: stringOrNull(value.operation) || stringOrNull(orbBinding?.operation),
    orb_binding: orbBinding,
    bound_at: stringOrNull(value.bound_at),
  };
}

function normalizeSubscription(value) {
  if (!isObject(value)) {
    return null;
  }
  const subscriptionId = stringOrNull(value.subscription_id);
  const bindingHandle = stringOrNull(value.binding_handle);
  if (!subscriptionId || !bindingHandle) {
    return null;
  }

  return {
    subscription_id: subscriptionId,
    binding_handle: bindingHandle,
    operation: stringOrNull(value.operation) || 'updates',
    arguments: objectOrNull(value.arguments) || {},
    stream: stringOrNull(value.stream) || 'updates',
    correlation_id: stringOrNull(value.correlation_id),
    receipt_cid: stringOrNull(value.receipt_cid),
    generation_key: stringOrNull(value.generation_key),
    orb_binding: objectOrNull(value.orb_binding),
    status: stringOrNull(value.status) || 'active',
    subscribed_at: stringOrNull(value.subscribed_at),
  };
}

export function normalizeMetaGlassesOrbBridgeState(value) {
  if (!isObject(value)) {
    return {
      edge_session_id: null,
      bindings: [],
      subscriptions: [],
      saved_at: null,
    };
  }

  const bindings = Array.isArray(value.bindings)
    ? value.bindings.map(normalizeBinding).filter(Boolean)
    : [];
  const bindingHandles = new Set(bindings.map((binding) => binding.binding_handle));
  const subscriptions = Array.isArray(value.subscriptions)
    ? value.subscriptions
      .map(normalizeSubscription)
      .filter((subscription) => subscription && bindingHandles.has(subscription.binding_handle))
    : [];

  return {
    edge_session_id: stringOrNull(value.edge_session_id),
    bindings,
    subscriptions,
    saved_at: stringOrNull(value.saved_at),
  };
}

export function createMetaGlassesOrbStateStore(storage = AsyncStorage) {
  return {
    async load() {
      try {
        const raw = await storage.getItem(META_GLASSES_ORB_STATE_STORAGE_KEY);
        if (!raw) {
          return normalizeMetaGlassesOrbBridgeState(null);
        }
        return normalizeMetaGlassesOrbBridgeState(JSON.parse(raw));
      } catch (error) {
        console.error('Failed to load Meta glasses ORB bridge state:', error);
        return normalizeMetaGlassesOrbBridgeState(null);
      }
    },

    async save(state) {
      const normalized = normalizeMetaGlassesOrbBridgeState({
        ...state,
        saved_at: state?.saved_at || new Date().toISOString(),
      });
      await storage.setItem(
        META_GLASSES_ORB_STATE_STORAGE_KEY,
        JSON.stringify(normalized)
      );
      return normalized;
    },

    async clear() {
      await storage.removeItem(META_GLASSES_ORB_STATE_STORAGE_KEY);
    },
  };
}

export const metaGlassesOrbStateStore = createMetaGlassesOrbStateStore();
