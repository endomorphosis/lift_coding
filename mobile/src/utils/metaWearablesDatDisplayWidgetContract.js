export const DISPLAY_WIDGET_ACTION_CONTRACT =
  'handsfree.meta-glasses/display-widget-action@0.1.0';

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

export const SWISSKNIFE_DISPLAY_WIDGET_SCHEMA_REFS = {
  control_surface_contract:
    'https://hallucinate.app/contracts/control_surface_contract.schema.json',
  interaction_envelope:
    'https://hallucinate.app/contracts/interaction_envelope.schema.json',
  mediation_receipt:
    'https://hallucinate.app/contracts/mediation_receipt.schema.json',
};

export const SWISSKNIFE_DISPLAY_WIDGET_HANDOFFS = DISPLAY_WIDGET_ACTION_IDS.map((actionId) => ({
  action_id: actionId,
  mobile_contract: DISPLAY_WIDGET_ACTION_CONTRACT,
  action: DISPLAY_WIDGET_ACTION_BY_ACTION_ID[actionId],
  orb_operation: DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionId],
  dat_method: DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID[actionId],
  control_surface_contract_ref: 'control_surface_contract',
  interaction_envelope_schema_ref: 'interaction_envelope',
  receipt_schema_ref: 'mediation_receipt',
}));

const DISPLAY_WIDGET_ACTION_ID_SET = new Set(DISPLAY_WIDGET_ACTION_IDS);

export function isDisplayWidgetActionId(actionId) {
  return DISPLAY_WIDGET_ACTION_ID_SET.has(actionId);
}
