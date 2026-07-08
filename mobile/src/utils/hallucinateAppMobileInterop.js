export const HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT =
  'handsfree.hallucinate_app/mobile-search-handoff@0.1.0';

export const HALLUCINATE_APP_MOBILE_ACTION_ID = 'mobile_hallucinate_app_search';
export const HALLUCINATE_APP_MOBILE_EVENT = 'hallucinate_app:mobile-search-handoff';
export const HALLUCINATE_APP_MOBILE_SOURCE_SURFACE = 'hallucinate_app.content_browser';
export const HALLUCINATE_APP_MOBILE_TARGET_SURFACE = 'mobile.results';

const HALLUCINATE_APP_MOBILE_ACTION_ID_SET = new Set([
  HALLUCINATE_APP_MOBILE_ACTION_ID,
]);

function objectOrEmpty(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

export function isHallucinateAppMobileActionId(actionId) {
  return HALLUCINATE_APP_MOBILE_ACTION_ID_SET.has(actionId);
}

export function normalizeHallucinateAppMobilePayload(actionItem = {}) {
  const params = objectOrEmpty(actionItem.params);
  const actionMobilePayload = objectOrEmpty(actionItem.mobile_payload);
  const paramsMobilePayload = objectOrEmpty(params.mobile_payload);
  const mobilePayload =
    actionMobilePayload.contract || actionMobilePayload.type
      ? actionMobilePayload
      : paramsMobilePayload.contract || paramsMobilePayload.type
        ? paramsMobilePayload
        : params;

  const contract = mobilePayload.contract || actionItem.contract;
  const actionId = mobilePayload.type || actionItem.id;

  if (contract !== HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT) {
    throw new Error(`Unexpected hallucinate_app mobile contract: ${contract || 'missing'}`);
  }
  if (!isHallucinateAppMobileActionId(actionId)) {
    throw new Error(`Unexpected hallucinate_app mobile action: ${actionId || 'missing'}`);
  }

  const filters = objectOrEmpty(mobilePayload.filters);
  const query = normalizeText(mobilePayload.query);
  const cid = normalizeText(mobilePayload.cid);
  const path = normalizeText(mobilePayload.path);

  if (!query && Object.keys(filters).length === 0 && !cid && !path) {
    throw new Error('Hallucinate App mobile handoff requires query, filters, cid, or path.');
  }

  return {
    type: HALLUCINATE_APP_MOBILE_ACTION_ID,
    contract: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
    request_id: normalizeText(mobilePayload.request_id) || normalizeText(actionItem.request_id),
    query,
    filters,
    result_limit:
      Number.isFinite(Number(mobilePayload.result_limit)) && Number(mobilePayload.result_limit) > 0
        ? Number(mobilePayload.result_limit)
        : 20,
    cid: cid || null,
    path: path || null,
    source_surface: mobilePayload.source_surface || HALLUCINATE_APP_MOBILE_SOURCE_SURFACE,
    target_surface: mobilePayload.target_surface || HALLUCINATE_APP_MOBILE_TARGET_SURFACE,
    timestamp: mobilePayload.timestamp || mobilePayload.issued_at || new Date().toISOString(),
    metadata: objectOrEmpty(mobilePayload.metadata),
  };
}

export function buildHallucinateAppMobileSearchAction({
  query = '',
  filters = {},
  requestId = '',
  cid = null,
  path = null,
  resultLimit = 20,
  metadata = {},
} = {}) {
  const mobilePayload = normalizeHallucinateAppMobilePayload({
    id: HALLUCINATE_APP_MOBILE_ACTION_ID,
    mobile_payload: {
      type: HALLUCINATE_APP_MOBILE_ACTION_ID,
      contract: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
      request_id: requestId,
      query,
      filters,
      result_limit: resultLimit,
      cid,
      path,
      source_surface: HALLUCINATE_APP_MOBILE_SOURCE_SURFACE,
      target_surface: HALLUCINATE_APP_MOBILE_TARGET_SURFACE,
      timestamp: new Date().toISOString(),
      metadata,
    },
  });

  return {
    id: HALLUCINATE_APP_MOBILE_ACTION_ID,
    label: 'Open Hallucinate App search',
    contract: HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT,
    params: {
      mobile_payload: mobilePayload,
    },
    mobile_payload: mobilePayload,
  };
}
