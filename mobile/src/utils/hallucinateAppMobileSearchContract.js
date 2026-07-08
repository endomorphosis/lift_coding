/**
 * Contract mapping between the Hallucinate App desktop content-browser search
 * surface and the mobile ORB bridge / display widget action space.
 *
 * HAO-740 (attempt 3) repairs the VAIOS-G707 objective validation gap: prove
 * `hallucinate_app` interoperates with `mobile` through importable contracts,
 * interface descriptors, runtime handoff behavior, and integration tests.
 *
 * `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
 * exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
 * `buildHallucinateAppMobileSearchHandoff()`, which normalize a desktop search
 * request into an `invoke_service` payload for the mobile ORB bridge. This
 * module maps the mobile-side search widget actions onto that handoff and the
 * underlying `mobile_orb_bridge` / `display_widget_bridge` operations so the
 * Hallucinate App search results can be rendered on the mobile/Meta glasses
 * display surface.
 */

export const HALLUCINATE_APP_SEARCH_ACTION_CONTRACT =
  'handsfree.meta-glasses/hallucinate-app-mobile-search-action@0.1.0';

export const HALLUCINATE_APP_SEARCH_ACTION_IDS = [
  'mobile_dispatch_hallucinate_app_search_query',
  'mobile_render_hallucinate_app_search_results',
  'mobile_update_hallucinate_app_search_results',
  'mobile_clear_hallucinate_app_search_results',
];

export const HALLUCINATE_APP_SEARCH_ORB_OPERATION_BY_ACTION_ID = {
  mobile_dispatch_hallucinate_app_search_query: 'invoke_service',
  mobile_render_hallucinate_app_search_results: 'render_widget',
  mobile_update_hallucinate_app_search_results: 'update_widget',
  mobile_clear_hallucinate_app_search_results: 'clear_widget',
};

export const HALLUCINATE_APP_SEARCH_DAT_METHOD_BY_ACTION_ID = {
  mobile_dispatch_hallucinate_app_search_query: 'dispatchHallucinateAppSearchQuery',
  mobile_render_hallucinate_app_search_results: 'renderHallucinateAppSearchResults',
  mobile_update_hallucinate_app_search_results: 'updateHallucinateAppSearchResults',
  mobile_clear_hallucinate_app_search_results: 'clearHallucinateAppSearchResults',
};

export const HALLUCINATE_APP_SEARCH_ROUTE_BY_ACTION_ID = {
  mobile_dispatch_hallucinate_app_search_query: '/v1/mobile/orb/invoke_service',
  mobile_render_hallucinate_app_search_results: '/v1/mobile/orb/dispatch_glasses_response',
  mobile_update_hallucinate_app_search_results: '/v1/mobile/orb/dispatch_glasses_response',
  mobile_clear_hallucinate_app_search_results: '/v1/mobile/orb/dispatch_glasses_response',
};

export const HALLUCINATE_APP_MOBILE_SEARCH_ACTION_CONTRACT = {
  contract: HALLUCINATE_APP_SEARCH_ACTION_CONTRACT,
  producer: 'hallucinate_app',
  consumer: 'mobile',
  interface_contract: 'interface contract hallucinate_app mobile',
  goal_id: 'VAIOS-G707',
  objective_validation_repair: 'HAO-740 repairs the VAIOS-G707 objective validation repair',
  action_ids: HALLUCINATE_APP_SEARCH_ACTION_IDS,
  operation_by_action_id: HALLUCINATE_APP_SEARCH_ORB_OPERATION_BY_ACTION_ID,
  dat_method_by_action_id: HALLUCINATE_APP_SEARCH_DAT_METHOD_BY_ACTION_ID,
  route_by_action_id: HALLUCINATE_APP_SEARCH_ROUTE_BY_ACTION_ID,
  schema_refs: {
    search_interface:
      'hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js',
    test_interface: 'hallucinate_app/hallucinate_app/node/views/test_interface.html',
    time_series_schema:
      'hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql',
    benchmark_schema_script:
      'hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py',
  },
};

const HALLUCINATE_APP_SEARCH_ACTION_ID_SET = new Set(HALLUCINATE_APP_SEARCH_ACTION_IDS);

export function isHallucinateAppSearchActionId(actionId) {
  return HALLUCINATE_APP_SEARCH_ACTION_ID_SET.has(actionId);
}

/**
 * Build the mobile-side dispatch envelope for a Hallucinate App search action,
 * binding the action id to its ORB operation, DAT-style method name, and
 * transport route.
 *
 * @param {string} actionId - One of HALLUCINATE_APP_SEARCH_ACTION_IDS.
 * @param {Object} [payload] - Action-specific payload (e.g. `{ query }`).
 * @returns {Object} Normalized mobile dispatch envelope.
 */
export function buildHallucinateAppSearchActionDispatch(actionId, payload = {}) {
  if (!isHallucinateAppSearchActionId(actionId)) {
    throw new Error(`Unknown hallucinate_app mobile search action id: ${actionId}`);
  }
  return {
    action_id: actionId,
    contract: HALLUCINATE_APP_SEARCH_ACTION_CONTRACT,
    interface_contract: 'interface contract hallucinate_app mobile',
    operation: HALLUCINATE_APP_SEARCH_ORB_OPERATION_BY_ACTION_ID[actionId],
    dat_method: HALLUCINATE_APP_SEARCH_DAT_METHOD_BY_ACTION_ID[actionId],
    route: HALLUCINATE_APP_SEARCH_ROUTE_BY_ACTION_ID[actionId],
    payload,
  };
}
