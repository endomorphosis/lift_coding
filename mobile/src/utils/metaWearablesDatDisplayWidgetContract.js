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

export const SWISSKNIFE_DISPLAY_WIDGET_HANDOFF_CONTRACT = {
  id: 'interface contract swissknife mobile display widget',
  objective_goal_id: 'VAIOS-G700',
  contract: DISPLAY_WIDGET_ACTION_CONTRACT,
  schema_refs: {
    control_surface_contract:
      'swissknife/contracts/control_surface_contract.schema.json',
    interaction_envelope: 'swissknife/contracts/interaction_envelope.schema.json',
  },
  allowed_surfaces: [
    'mobile',
    'native_display',
    'display_webapp',
    'mobile_card',
    'notification',
    'audio_summary',
  ],
  required_handoff_fields: [
    'control_surface_contract_ref',
    'interaction_envelope.actor.agent_identity',
    'interaction_envelope.normalized_intent.arguments',
    'interaction_envelope.normalized_intent.arguments_hash',
    'interaction_envelope.normalized_intent.allowed_surfaces',
    'policy_decision',
    'mediation_receipt',
  ],
  action_by_action_id: DISPLAY_WIDGET_ACTION_BY_ACTION_ID,
  orb_operation_by_action_id: DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID,
  dat_method_by_action_id: DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID,
};

const DISPLAY_WIDGET_ACTION_ID_SET = new Set(DISPLAY_WIDGET_ACTION_IDS);

export function isDisplayWidgetActionId(actionId) {
  return DISPLAY_WIDGET_ACTION_ID_SET.has(actionId);
}

export function displayWidgetActionContractRef(actionId) {
  if (!isDisplayWidgetActionId(actionId)) {
    return null;
  }
  return {
    contract: DISPLAY_WIDGET_ACTION_CONTRACT,
    action_id: actionId,
    action: DISPLAY_WIDGET_ACTION_BY_ACTION_ID[actionId],
    orb_operation: DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionId],
    dat_method: DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID[actionId],
    allowed_surfaces: SWISSKNIFE_DISPLAY_WIDGET_HANDOFF_CONTRACT.allowed_surfaces,
  };
}

export function buildSwissknifeDisplayWidgetHandoff(actionId, options = {}) {
  const actionRef = displayWidgetActionContractRef(actionId);
  if (!actionRef) {
    throw new Error(`Unsupported display widget action id: ${actionId}`);
  }

  const correlationId = options.correlation_id || options.correlationId || actionId;
  const argumentsPayload = options.arguments || {};
  const argumentsHash =
    options.arguments_hash || options.argumentsHash || `sha256:${actionId}:${correlationId}`;
  const actorId = options.actor_id || options.actorId || 'mobile:operator';
  const agentIdentity = options.agent_identity || {
    kind: 'agent',
    id: 'swissknife.mobile_orb',
    platform: options.platform || 'mobile',
    edge_session_id: options.edge_session_id || options.edgeSessionId || null,
    allowed_surfaces: actionRef.allowed_surfaces,
  };

  const interactionEnvelope = {
    interaction_id:
      options.interaction_id || options.interactionId || `mobile-display-widget:${correlationId}`,
    surface: 'mobile',
    surface_event: actionId,
    raw_payload: options.raw_payload || {},
    normalized_intent: {
      intent: `display_widget.${actionRef.action}`,
      method: actionRef.orb_operation,
      target_ref: options.target_ref || options.targetRef || 'meta_wearables_dat.display_widget',
      arguments: argumentsPayload,
      arguments_hash: argumentsHash,
      allowed_surfaces: actionRef.allowed_surfaces,
      confidence: options.confidence ?? 1,
    },
    actor: {
      type: options.actor_type || options.actorType || 'agent',
      id: actorId,
      delegation_chain: options.delegation_chain || options.delegationChain || [],
      agent_identity: agentIdentity,
    },
    context: {
      local_time: options.local_time || options.localTime || '1970-01-01T00:00:00.000Z',
      state_frames: options.state_frames || options.stateFrames || ['mobile_orb_edge_session'],
      device_mode: options.device_mode || options.deviceMode || 'handsfree',
      platform: options.platform || 'mobile',
      location_context: options.location_context || options.locationContext || {},
      device_context: options.device_context || options.deviceContext || {},
    },
    control_surface_contract_ref:
      options.control_surface_contract_ref ||
      options.controlSurfaceContractRef ||
      'control_surface_contract:swissknife-mobile-display-widget',
  };

  return {
    ...actionRef,
    control_surface_contract_ref: interactionEnvelope.control_surface_contract_ref,
    interaction_envelope: interactionEnvelope,
  };
}
