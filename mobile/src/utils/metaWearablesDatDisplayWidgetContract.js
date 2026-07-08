export const DISPLAY_WIDGET_ACTION_CONTRACT =
  'handsfree.meta-glasses/display-widget-action@0.1.0';

export const SWISSKNIFE_MOBILE_INTEROP_CONTRACT =
  'interface contract swissknife mobile';

export const SWISSKNIFE_MOBILE_INTEROP_CONTRACT_ID =
  'handsfree.meta-glasses/swissknife-mobile-interop@0.1.0';

export const SWISSKNIFE_MOBILE_CONTROL_SURFACE_CONTRACT_REF =
  'control_surface_contract:swissknife-mobile:display-widget';

export const SWISSKNIFE_MOBILE_INTERACTION_ENVELOPE_REF =
  'interaction_envelope:swissknife-mobile:display-widget';

export const SWISSKNIFE_MOBILE_POLICY_BUNDLE_REF = {
  policy_id: 'policy:swissknife-mobile-display-widget-handoff',
  policy_cid: 'local:swissknife-mobile-display-widget-handoff',
  version: '0.1.0',
  scope: 'swissknife-mobile-display-widget',
  source: 'descriptor',
};

export const SWISSKNIFE_MOBILE_SCHEMA_REFS = [
  'control_surface_contract',
  'interaction_envelope',
  'policy_decision',
  'mediation_receipt',
  'mcp_plus_plus_compatibility_receipt',
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

export const DISPLAY_WIDGET_HANDOFF_REQUIRED_FIELDS = [
  'contract',
  'interop_contract',
  'type',
  'action',
  'operation',
  'widget_id',
  'interface_cid',
  'orb_receipt_cid',
  'control_surface_contract_ref',
  'interaction_envelope_ref',
  'policy_bundle_ref',
  'mediation_receipt',
];

export function displayWidgetOperationForActionId(actionId) {
  return DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID[actionId] || null;
}

export function displayWidgetDatMethodForActionId(actionId) {
  return DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID[actionId] || null;
}

export function buildSwissKnifeMobileInteractionEnvelope(action = {}, options = {}) {
  const type = action.type || options.type || 'mobile_render_display_widget';
  const operation = action.operation || displayWidgetOperationForActionId(type) || 'render_widget';
  const correlationId =
    action.correlation_id || action.correlationId || options.correlation_id || 'swissknife-mobile';
  const widgetId = action.widget_id || action.widgetId || options.widget_id || 'unknown-widget';
  const emittedAt = options.emitted_at || action.issued_at || new Date().toISOString();
  const targetRef = `handsfree.meta_glasses.display.display_widget_bridge.${operation}`;

  return {
    interaction_id: action.interaction_id || correlationId,
    surface: 'mobile',
    surface_event: type,
    raw_payload: action,
    normalized_intent: {
      intent: action.intent || `display_widget.${operation}`,
      method: operation,
      target_ref: targetRef,
      arguments: action,
      confidence: Number(action.confidence || 1),
    },
    actor: {
      type: 'remote_client',
      id: action.actor_id || options.actor_id || 'mobile',
      delegation_chain: [action.actor_id || options.actor_id || 'mobile'],
    },
    context: {
      local_time: emittedAt,
      state_frames: ['swissknife_mobile_interop', 'meta_glasses_display_widget'],
      device_mode: action.device_mode || options.device_mode || 'mobile',
      platform: action.platform || options.platform || 'mobile',
      location_context: action.location_context || {},
      device_context: {
        widget_id: widgetId,
        interface_cid: action.interface_cid || options.interface_cid || null,
        dat_method: displayWidgetDatMethodForActionId(type),
      },
    },
    control_surface_contract_ref:
      action.control_surface_contract_ref || SWISSKNIFE_MOBILE_CONTROL_SURFACE_CONTRACT_REF,
    interop_contract: SWISSKNIFE_MOBILE_INTEROP_CONTRACT,
    interop_contract_id: SWISSKNIFE_MOBILE_INTEROP_CONTRACT_ID,
    schema_refs: SWISSKNIFE_MOBILE_SCHEMA_REFS,
    policy_bundle_ref: action.policy_bundle_ref || SWISSKNIFE_MOBILE_POLICY_BUNDLE_REF,
    compiled_policy_cid:
      action.compiled_policy_cid || SWISSKNIFE_MOBILE_POLICY_BUNDLE_REF.policy_cid,
    logic_bindings: [
      {
        binding_id: `swissknife_mobile.display_widget.${operation}`,
        policy_bundle_ref: action.policy_bundle_ref || SWISSKNIFE_MOBILE_POLICY_BUNDLE_REF,
        compiled_policy_cid:
          action.compiled_policy_cid || SWISSKNIFE_MOBILE_POLICY_BUNDLE_REF.policy_cid,
        surface_ref: 'mobile',
        method_ref: operation,
        norm_refs: ['swissknife_mobile.display_widget.handoff'],
      },
    ],
  };
}

export function normalizeSwissKnifeMobileDisplayWidgetAction(action = {}, options = {}) {
  const type = action.type || options.type || 'mobile_render_display_widget';
  if (!isDisplayWidgetActionId(type)) {
    throw new Error(`Unsupported display widget action id: ${type}`);
  }
  const operation = action.operation || displayWidgetOperationForActionId(type);
  const envelope =
    action.interaction_envelope ||
    buildSwissKnifeMobileInteractionEnvelope({ ...action, type, operation }, options);
  const policyBundleRef = action.policy_bundle_ref || envelope.policy_bundle_ref;
  const mediationReceipt =
    action.mediation_receipt ||
    {
      receipt_id:
        action.orb_receipt_cid ||
        action.receipt_cid ||
        options.orb_receipt_cid ||
        `local:swissknife-mobile:${type}`,
      emitted_at: action.issued_at || options.emitted_at || envelope.context.local_time,
      control_surface_contract_ref: envelope.control_surface_contract_ref,
      interaction_envelope: envelope,
      policy_decision: action.policy_decision || {
        outcome: 'allow',
        policy_bundle_ref: policyBundleRef,
        compiled_policy_cid: envelope.compiled_policy_cid,
        reasons: ['SwissKnife display widget action accepted by mobile DAT handoff contract.'],
      },
      policy_refs: [
        {
          policy_bundle_ref: policyBundleRef,
          compiled_policy_cid: envelope.compiled_policy_cid,
          matched_norm_refs: ['swissknife_mobile.display_widget.handoff'],
        },
      ],
      mediation_result: {
        outcome: 'allow',
        invoked: true,
        final_method: operation,
        final_target_ref: envelope.normalized_intent.target_ref,
      },
    };

  return {
    contract: DISPLAY_WIDGET_ACTION_CONTRACT,
    interop_contract: SWISSKNIFE_MOBILE_INTEROP_CONTRACT,
    interop_contract_id: SWISSKNIFE_MOBILE_INTEROP_CONTRACT_ID,
    type,
    action: action.action || DISPLAY_WIDGET_ACTION_BY_ACTION_ID[type],
    operation,
    dat_method: displayWidgetDatMethodForActionId(type),
    widget_id: action.widget_id || action.widgetId || options.widget_id || null,
    interface_cid: action.interface_cid || options.interface_cid || null,
    widget_cid: action.widget_cid || action.widgetCid || options.widget_cid || null,
    orb_receipt_cid:
      action.orb_receipt_cid || action.receipt_cid || options.orb_receipt_cid || mediationReceipt.receipt_id,
    control_surface_contract_ref: envelope.control_surface_contract_ref,
    interaction_envelope_ref: SWISSKNIFE_MOBILE_INTERACTION_ENVELOPE_REF,
    interaction_envelope: envelope,
    policy_bundle_ref: policyBundleRef,
    mediation_receipt: mediationReceipt,
    schema_refs: SWISSKNIFE_MOBILE_SCHEMA_REFS,
    correlation_id: action.correlation_id || action.correlationId || envelope.interaction_id,
    issued_at: action.issued_at || mediationReceipt.emitted_at,
    manifest: action.manifest || options.manifest,
    state: action.state || options.state,
    patch: action.patch || options.patch,
    focus: action.focus || options.focus,
    activated_action_id: action.activated_action_id || action.action_id || options.action_id,
    video: action.video || options.video,
    subscription: action.subscription || options.subscription,
    fallback: action.fallback || options.fallback,
  };
}
