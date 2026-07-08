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

export const SWISSKNIFE_DISPLAY_WIDGET_ACTION_CONTRACT = {
  contract: DISPLAY_WIDGET_ACTION_CONTRACT,
  producer: 'swissknife',
  consumer: 'mobile',
  interface_contract: 'interface contract swissknife mobile',
  goal_packet: 'goal_packet/interoperability/swissknife/06921590135c',
  hao_task_id: 'HAO-730',
  hao_attempt: 4,
  hao_objective_gap_ref:
    'data/hallucinate_multimodal_control/discovery/2026-07-08-hao-730-objective-gap-d33307f93408.md',
  hao_validation_confirmation_ref:
    'data/hallucinate_multimodal_control/discovery/2026-07-08-hao-730-attempt-4-validation-confirmation.md',
  objective_validation_repair: 'MGW-583 repairs MGW-569 objective validation repair',
  action_ids: DISPLAY_WIDGET_ACTION_IDS,
  action_by_action_id: DISPLAY_WIDGET_ACTION_BY_ACTION_ID,
  operation_by_action_id: DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID,
  dat_method_by_action_id: DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID,
  schema_refs: {
    control_surface_contract: 'swissknife/contracts/control_surface_contract.schema.json',
    interaction_envelope: 'swissknife/contracts/interaction_envelope.schema.json',
  },
};

const DISPLAY_WIDGET_ACTION_ID_SET = new Set(DISPLAY_WIDGET_ACTION_IDS);

export function isDisplayWidgetActionId(actionId) {
  return DISPLAY_WIDGET_ACTION_ID_SET.has(actionId);
}
