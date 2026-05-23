import { createMetaGlassesMobileOrbApiBackend } from './metaGlassesMobileOrbApiBackend';
import { createMetaGlassesMobileOrbBridge } from './metaGlassesMobileOrbBridge';
import { metaGlassesOrbEdgeSessionStore } from './metaGlassesOrbEdgeSession';
import { metaGlassesOrbStateStore } from './metaGlassesOrbStateStore';
import {
  DISPLAY_WIDGET_BRIDGE_INTERFACE,
  MOBILE_ORB_BRIDGE_INTERFACE,
  localInterfaceKey,
} from './metaGlassesOrbDescriptors';

function isUsableEdgeSession(session, now = () => new Date()) {
  if (!session?.edge_session_id || !session?.policy_cid) {
    return false;
  }
  if (!session.expires_at) {
    return true;
  }
  const expiresAt = Date.parse(session.expires_at);
  return Number.isFinite(expiresAt) && expiresAt > now().getTime();
}

function defaultCapabilities(capabilities = {}) {
  return {
    session: true,
    audio: true,
    display: true,
    displayVideo: Boolean(capabilities.displayVideo),
    webAppDisplay: Boolean(capabilities.webAppDisplay),
    camera: Boolean(capabilities.camera),
    photoCapture: Boolean(capabilities.photoCapture),
    videoStream: Boolean(capabilities.videoStream),
    ...capabilities,
  };
}

export function createMetaGlassesMobileOrbRuntime(options = {}) {
  const now = options.now || (() => new Date());
  const edgeSessionStore = Object.prototype.hasOwnProperty.call(options, 'edgeSessionStore')
    ? options.edgeSessionStore
    : metaGlassesOrbEdgeSessionStore;
  const orbStateStore = Object.prototype.hasOwnProperty.call(options, 'orbStateStore')
    ? options.orbStateStore
    : metaGlassesOrbStateStore;
  const backend = options.backend || createMetaGlassesMobileOrbApiBackend();
  const localInterfaceCids = options.localInterfaceCids || [
    localInterfaceKey(MOBILE_ORB_BRIDGE_INTERFACE),
    localInterfaceKey(DISPLAY_WIDGET_BRIDGE_INTERFACE),
  ];
  const bridge = createMetaGlassesMobileOrbBridge({
    ...options,
    now,
    backend,
    edgeSessionStore,
    orbStateStore,
    localInterfaceCids,
  });

  async function ensureRegistered(input = {}) {
    if (!input.force) {
      const active = bridge.getEdgeSession();
      if (isUsableEdgeSession(active, now)) {
        return {
          restored: false,
          payload: null,
          response: active,
        };
      }
      const restored = await bridge.restoreEdgeSession();
      if (isUsableEdgeSession(restored, now)) {
        return {
          restored: true,
          payload: null,
          response: restored,
        };
      }
    }

    return bridge.registerEdgeCapabilities({
      ...input,
      capabilities: defaultCapabilities(input.capabilities || input.dat_capabilities),
      local_interface_cids: input.local_interface_cids || localInterfaceCids,
      transport_preferences:
        input.transport_preferences || ['local', 'http', 'websocket', 'mcp-server'],
    });
  }

  async function routeGlassesEventToService(input = {}) {
    await ensureRegistered({
      capabilities: input.capabilities,
      dat_capabilities: input.dat_capabilities,
      platform: input.platform,
      device_id: input.device_id,
      device_model: input.device_model,
    });
    return bridge.routeEventToService(input);
  }

  function getDiagnostics() {
    return {
      ...bridge.getDiagnostics(),
      mobile_orb_interface_cid: localInterfaceCids[0],
      display_widget_interface_cid: localInterfaceCids[1],
      backend_kind: options.backend ? 'injected' : 'api',
      edge_session_persistence: Boolean(edgeSessionStore),
      orb_state_persistence: Boolean(orbStateStore),
    };
  }

  async function fetchBackendDiagnostics(params = {}) {
    if (!backend.getDiagnostics) {
      return null;
    }
    const edgeSessionId =
      params.edge_session_id ||
      params.edgeSessionId ||
      bridge.getEdgeSession()?.edge_session_id;
    return backend.getDiagnostics({
      ...params,
      ...(edgeSessionId ? { edge_session_id: edgeSessionId } : {}),
    });
  }

  return {
    bridge,
    ensureRegistered,
    routeGlassesEventToService,
    restoreEdgeSession: () => bridge.restoreEdgeSession(),
    clearEdgeSession: () => bridge.clearEdgeSession(),
    fetchBackendDiagnostics,
    getDiagnostics,
  };
}

export { isUsableEdgeSession as isMetaGlassesOrbEdgeSessionUsable };
