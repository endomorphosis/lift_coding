export const HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT =
  'handsfree.hallucinate_app/mobile-search-handoff@0.1.0';

export const HALLUCINATE_APP_MOBILE_ACTION_ID = 'mobile_hallucinate_app_search';

export const HALLUCINATE_APP_MOBILE_ROUTE = 'hallucinate_app.mobile.search_handoff';

export function isHallucinateAppMobileActionId(actionId) {
  return actionId === HALLUCINATE_APP_MOBILE_ACTION_ID;
}

function asArray(value) {
  if (!value) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.filter(Boolean).map(String);
  }
  return [String(value)];
}

export function normalizeHallucinateAppMobilePayload(actionItem = {}) {
  const params = actionItem.params && typeof actionItem.params === 'object' ? actionItem.params : {};
  const directPayload =
    actionItem.mobile_payload && typeof actionItem.mobile_payload === 'object'
      ? actionItem.mobile_payload
      : null;
  const nestedPayload =
    params.mobile_payload && typeof params.mobile_payload === 'object'
      ? params.mobile_payload
      : null;
  const payload = directPayload || nestedPayload || params;
  const handoff =
    payload.handoff && typeof payload.handoff === 'object'
      ? payload.handoff
      : params.handoff && typeof params.handoff === 'object'
        ? params.handoff
        : {};
  const query = String(payload.query || handoff.query || params.query || '');
  const filter = payload.filter || handoff.filter || params.filter || {};
  const requestId =
    payload.request_id ||
    payload.requestId ||
    handoff.request_id ||
    handoff.requestId ||
    params.request_id ||
    null;
  const cid = payload.cid || handoff.cid || params.cid || null;
  const ipfsCids = asArray(payload.ipfs_cids || handoff.ipfs_cids || params.ipfs_cids);
  if (cid && !ipfsCids.includes(String(cid))) {
    ipfsCids.unshift(String(cid));
  }

  return {
    type: HALLUCINATE_APP_MOBILE_ACTION_ID,
    interface_contract:
      payload.interface_contract ||
      handoff.interface_contract ||
      HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
    source_surface: payload.source_surface || 'hallucinate_app.content_browser',
    target_surface: payload.target_surface || 'mobile.results',
    request_id: requestId,
    query,
    filter,
    handoff: {
      schema: handoff.schema || 'hallucinate_app_mobile_content_search_handoff_v1',
      objective_id: handoff.objective_id || 'VAIOS-G707',
      interface_contract:
        handoff.interface_contract || HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
      runtime_handoff: handoff.runtime_handoff || 'content-search-to-mobile-results',
      query,
      filter,
      ipfs_cids: ipfsCids,
      edge_session_id: handoff.edge_session_id || payload.edge_session_id || null,
      libp2p_peer_id: handoff.libp2p_peer_id || payload.libp2p_peer_id || null,
    },
    receipt_cid: payload.receipt_cid || params.receipt_cid || null,
    mediation_receipt: payload.mediation_receipt || params.mediation_receipt || null,
  };
}

export function buildHallucinateAppMobileSearchAction(payload) {
  const normalized = normalizeHallucinateAppMobilePayload({ mobile_payload: payload });
  return {
    id: HALLUCINATE_APP_MOBILE_ACTION_ID,
    label: 'Open Hallucinate App search',
    params: {
      mobile_payload: normalized,
      handoff: normalized.handoff,
    },
  };
}
