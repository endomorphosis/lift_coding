export const HALLUCINATE_APP_SEARCH_WIDGET_ACTION_IDS = [
  'mobile_render_content_search_results',
  'mobile_update_content_search_results',
  'mobile_open_content_search_result',
  'mobile_sync_content_search_filter',
];

export const HALLUCINATE_APP_SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID = {
  mobile_render_content_search_results: 'render_content_search_results',
  mobile_update_content_search_results: 'update_content_search_results',
  mobile_open_content_search_result: 'open_content_search_result',
  mobile_sync_content_search_filter: 'sync_content_search_filter',
};

export const HALLUCINATE_APP_SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID = {
  mobile_render_content_search_results: 'renderContentSearchResults',
  mobile_update_content_search_results: 'updateContentSearchResults',
  mobile_open_content_search_result: 'openContentSearchResult',
  mobile_sync_content_search_filter: 'syncContentSearchFilter',
};

export const HALLUCINATE_APP_SEARCH_WIDGET_RESULT_TARGET_BY_ACTION_ID = {
  mobile_render_content_search_results: 'mobile_card',
  mobile_update_content_search_results: 'mobile_card',
  mobile_open_content_search_result: 'mobile_detail',
  mobile_sync_content_search_filter: 'mobile_card',
};

export const HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT = {
  producer: 'hallucinate_app',
  consumer: 'mobile',
  interface_contract: 'interface contract hallucinate_app mobile',
  goal_id: 'VAIOS-G707',
  task_id: 'VAI-674',
  repair_task_id: 'VAI-684',
  objective_validation_repair: 'VAI-684 repairs the VAI-674 objective validation repair',
  action_ids: HALLUCINATE_APP_SEARCH_WIDGET_ACTION_IDS,
  operation_by_action_id: HALLUCINATE_APP_SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID,
  dat_method_by_action_id: HALLUCINATE_APP_SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID,
  result_target_by_action_id: HALLUCINATE_APP_SEARCH_WIDGET_RESULT_TARGET_BY_ACTION_ID,
  route: '/v1/mobile/orb/invoke_service',
  receipt_table: 'hallucinate_app_mobile_interop_receipts',
};

export function buildHallucinateAppSearchWidgetAction(actionId, payload = {}) {
  const operation = HALLUCINATE_APP_SEARCH_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionId];
  if (!operation) {
    throw new Error(`Unsupported Hallucinate App search widget action: ${actionId}`);
  }
  return {
    action_id: actionId,
    operation,
    dat_method: HALLUCINATE_APP_SEARCH_WIDGET_DAT_METHOD_BY_ACTION_ID[actionId],
    result_target:
      payload.result_target ||
      HALLUCINATE_APP_SEARCH_WIDGET_RESULT_TARGET_BY_ACTION_ID[actionId],
    interface_contract: HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT.interface_contract,
    goal_id: HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT.goal_id,
    payload,
  };
}
