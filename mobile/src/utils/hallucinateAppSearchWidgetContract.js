/**
 * VAI-674 / VAIOS-G707 objective validation repair.
 *
 * Maps mobile-side Hallucinate App search widget actions onto the
 * `mobile_orb_bridge` operations and the `hallucinate_app_mobile_interop_receipts`
 * DuckDB receipt table so the mobile Handsfree client can render Hallucinate
 * App desktop search handoffs (content browser search results) without
 * importing any code from the `hallucinate_app` submodule.
 *
 * See also:
 * - `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
 *   (`HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`,
 *   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`)
 * - `hallucinate_app/hallucinate_app/node/views/test_interface.html`
 * - `mobile/src/orb/metaGlassesOrbDescriptors.js`
 *   (`HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`,
 *   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`)
 */

export const SEARCH_WIDGET_ACTION_CONTRACT =
  'handsfree.meta-glasses/hallucinate-app-search-widget-action@0.1.0';

export const SEARCH_WIDGET_ACTION_IDS = [
  'mobile_render_search_results_widget',
  'mobile_update_search_results_widget',
  'mobile_clear_search_results_widget',
  'mobile_refresh_search_metadata',
];

export const SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID = {
  mobile_render_search_results_widget: 'render_search_results_widget',
  mobile_update_search_results_widget: 'update_search_results_widget',
  mobile_clear_search_results_widget: 'clear_search_results_widget',
  mobile_refresh_search_metadata: 'refresh_search_metadata',
};

export const SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID = {
  mobile_render_search_results_widget: 'renderSearchResultsWidget',
  mobile_update_search_results_widget: 'updateSearchResultsWidget',
  mobile_clear_search_results_widget: 'clearSearchResultsWidget',
  mobile_refresh_search_metadata: 'refreshSearchMetadata',
};

export const SEARCH_WIDGET_ROUTE_BY_ACTION_ID = {
  mobile_render_search_results_widget: '/v1/mobile/orb/invoke_service',
  mobile_update_search_results_widget: '/v1/mobile/orb/invoke_service',
  mobile_clear_search_results_widget: '/v1/mobile/orb/invoke_service',
  mobile_refresh_search_metadata: '/v1/mobile/orb/diagnostics',
};

export const HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT = {
  contract: SEARCH_WIDGET_ACTION_CONTRACT,
  producer: 'hallucinate_app',
  consumer: 'mobile',
  interface_contract: 'interface contract hallucinate_app mobile',
  goal_id: 'VAIOS-G707',
  objective_validation_repair: 'VAI-674 repairs the VAIOS-G707 objective validation repair',
  event_name: 'hallucinate-app:mobile-interop-handoff',
  receipt_table: 'hallucinate_app_mobile_interop_receipts',
  action_ids: SEARCH_WIDGET_ACTION_IDS,
  operation_by_action_id: SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID,
  dat_method_by_action_id: SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID,
  route_by_action_id: SEARCH_WIDGET_ROUTE_BY_ACTION_ID,
  schema_refs: {
    search_interface_descriptor:
      'hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js',
    test_interface_fixture: 'hallucinate_app/hallucinate_app/node/views/test_interface.html',
    time_series_schema:
      'hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql',
    benchmark_schema_script:
      'hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py',
  },
};

const SEARCH_WIDGET_ACTION_ID_SET = new Set(SEARCH_WIDGET_ACTION_IDS);

export function isSearchWidgetActionId(actionId) {
  return SEARCH_WIDGET_ACTION_ID_SET.has(actionId);
}
