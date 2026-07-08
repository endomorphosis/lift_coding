export const DISPLAY_WIDGET_ACTION_CONTRACT =
  'handsfree.meta-glasses/display-widget-action@0.1.0';

export const SWISSKNIFE_MOBILE_DISPLAY_WIDGET_INTEROP_CONTRACT = {
  contract_id: 'interface contract swissknife mobile',
  version: '0.1.0',
  producer: 'swissknife',
  consumer: 'mobile',
  mobile_contract: DISPLAY_WIDGET_ACTION_CONTRACT,
  schema_refs: [
    'control_surface_contract',
    'interaction_envelope',
    'policy_decision',
    'mediation_receipt',
  ],
  runtime_handoff: {
    action_id_field: 'type',
    orb_operation_field: 'operation',
    native_dat_method_field: 'method',
    response_receipt_field: 'orb_receipt_cid',
  },
};

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

export function displayWidgetInteropDescriptor() {
  return {
    ...SWISSKNIFE_MOBILE_DISPLAY_WIDGET_INTEROP_CONTRACT,
    action_ids: DISPLAY_WIDGET_ACTION_IDS,
    action_by_action_id: DISPLAY_WIDGET_ACTION_BY_ACTION_ID,
    orb_operation_by_action_id: DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID,
    dat_method_by_action_id: DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID,
  };
}
