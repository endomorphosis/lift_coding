export const DISPLAY_WIDGET_ACTION_CONTRACT =
  'handsfree.meta-glasses/display-widget-action@0.1.0';

export const DISPLAY_WIDGET_SWISSKNIFE_HANDOFF_CONTRACT =
  'handsfree.meta-glasses/swissknife-mobile-display-widget-handoff@0.1.0';

export const DISPLAY_WIDGET_REQUIRED_HANDOFF_FIELDS = [
  'contract',
  'type',
  'action',
  'operation',
  'widget_id',
  'orb_receipt_cid',
  'control_surface_contract_ref',
  'mediation_receipt',
];

export const DISPLAY_WIDGET_ACTION_IDS = [
  'mobile_render_display_widget',
  'mobile_update_display_widget',
  'mobile_clear_display_widget',
  'mobile_focus_display_widget',
  'mobile_activate_display_widget_action',
  'mobile_reset_display_widget_session',
  'mobile_play_display_widget_video',
  'mobile_subscribe_display_widget_updates',
];

export const DISPLAY_WIDGET_ACTION_BY_ACTION_ID = {
  mobile_render_display_widget: 'render',
  mobile_update_display_widget: 'update',
  mobile_clear_display_widget: 'clear',
  mobile_focus_display_widget: 'focus',
  mobile_activate_display_widget_action: 'activate',
  mobile_reset_display_widget_session: 'reset',
  mobile_play_display_widget_video: 'play_video',
  mobile_subscribe_display_widget_updates: 'subscribe_updates',
};

export const DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID = {
  mobile_render_display_widget: 'render_widget',
  mobile_update_display_widget: 'update_widget',
  mobile_clear_display_widget: 'clear_widget',
  mobile_focus_display_widget: 'focus_next',
  mobile_activate_display_widget_action: 'activate',
  mobile_reset_display_widget_session: 'reset_session',
  mobile_play_display_widget_video: 'play_video',
  mobile_subscribe_display_widget_updates: 'subscribe_updates',
};

export const DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID = {
  mobile_render_display_widget: 'renderDisplayWidget',
  mobile_update_display_widget: 'updateDisplayWidget',
  mobile_clear_display_widget: 'clearDisplayWidget',
  mobile_focus_display_widget: 'focusDisplayWidget',
  mobile_activate_display_widget_action: 'activateDisplayWidgetAction',
  mobile_reset_display_widget_session: 'resetDisplayWidgetSession',
  mobile_play_display_widget_video: 'playDisplayWidgetVideo',
  mobile_subscribe_display_widget_updates: 'subscribeDisplayWidgetUpdates',
};

const DISPLAY_WIDGET_ACTION_ID_SET = new Set(DISPLAY_WIDGET_ACTION_IDS);

export function isDisplayWidgetActionId(actionId) {
  return DISPLAY_WIDGET_ACTION_ID_SET.has(actionId);
}

export function displayWidgetInteropMapping(actionId) {
  if (!isDisplayWidgetActionId(actionId)) {
    return null;
  }
  return {
    action_id: actionId,
    action: DISPLAY_WIDGET_ACTION_BY_ACTION_ID[actionId],
    orb_operation: DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionId],
    dat_method: DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID[actionId],
  };
}

export function buildDisplayWidgetActionHandoff(payload = {}) {
  const actionId = payload.type || payload.action_id;
  const mapping = displayWidgetInteropMapping(actionId);
  if (!mapping) {
    throw new Error(`Unsupported display widget action id: ${String(actionId || '')}`);
  }

  return {
    handoff_contract: DISPLAY_WIDGET_SWISSKNIFE_HANDOFF_CONTRACT,
    contract: payload.contract || DISPLAY_WIDGET_ACTION_CONTRACT,
    type: mapping.action_id,
    action: payload.action || mapping.action,
    operation: payload.operation || mapping.orb_operation,
    dat_method: mapping.dat_method,
    widget_id: payload.widget_id || null,
    widget_cid: payload.widget_cid || null,
    orb_receipt_cid: payload.orb_receipt_cid || null,
    control_surface_contract_ref: payload.control_surface_contract_ref || null,
    mediation_receipt: payload.mediation_receipt || null,
    fallback: payload.fallback || null,
  };
}

export function validateDisplayWidgetActionHandoff(payload = {}) {
  const handoff = buildDisplayWidgetActionHandoff(payload);
  const missing = DISPLAY_WIDGET_REQUIRED_HANDOFF_FIELDS.filter((field) => {
    const value = handoff[field];
    return value === null || value === undefined || value === '';
  });
  return {
    valid: missing.length === 0,
    missing,
    handoff,
  };
}
