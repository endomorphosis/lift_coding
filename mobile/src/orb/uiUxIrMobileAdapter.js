/**
 * UIIRMobileAdapter@1 — maps mobile companion projection artifacts into the
 * existing React Native ORB surface shapes (cards, confirmations, navigation,
 * status banners) without becoming a separate policy owner.
 *
 * Consumes JSON from UIIRMobileProjection@1 / ui-mobile-projection/v1.
 * Side-effect free: no network, device SDK, or ORB calls.
 */

export const UIIR_MOBILE_ADAPTER_INTERFACE = 'UIIRMobileAdapter@1';
export const UIIR_MOBILE_PROJECTION_INTERFACE = 'UIIRMobileProjection@1';
export const UIIR_MOBILE_PROJECTION_SCHEMA_VERSION = 'ui-mobile-projection/v1';
export const POLICY_OWNER = 'UIProjectionSolver@1';

export const MIN_TOUCH_TARGET_DP = 44;
export const MIN_TOUCH_SPACING_DP = 8;

const SURFACE_KINDS = new Set([
  'card',
  'form',
  'list',
  'navigation',
  'confirmation',
  'fallback',
  'status',
]);

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function asString(value, fallback = '') {
  return typeof value === 'string' ? value : fallback;
}

function asBoolean(value, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

function asNumber(value, fallback = 0) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

/**
 * Validate a mobile projection artifact mapping (fail-closed on critical fields).
 */
export function validateMobileProjectionArtifact(artifact) {
  const errors = [];
  if (!isObject(artifact)) {
    return { valid: false, errors: ['artifact must be an object'] };
  }
  if (artifact.interface && artifact.interface !== UIIR_MOBILE_PROJECTION_INTERFACE) {
    errors.push(`unsupported interface: ${artifact.interface}`);
  }
  if (
    artifact.schema_version
    && artifact.schema_version !== UIIR_MOBILE_PROJECTION_SCHEMA_VERSION
  ) {
    errors.push(`unsupported schema_version: ${artifact.schema_version}`);
  }
  if (artifact.policy_owner && artifact.policy_owner !== POLICY_OWNER) {
    errors.push(
      `mobile must not own policy; expected policy_owner=${POLICY_OWNER}, got ${artifact.policy_owner}`
    );
  }
  if (!Array.isArray(artifact.surfaces)) {
    errors.push('surfaces must be an array');
  } else {
    artifact.surfaces.forEach((surface, index) => {
      if (!isObject(surface)) {
        errors.push(`surfaces[${index}] must be an object`);
        return;
      }
      if (!asString(surface.surface_id)) {
        errors.push(`surfaces[${index}].surface_id is required`);
      }
      if (surface.kind && !SURFACE_KINDS.has(surface.kind)) {
        errors.push(`surfaces[${index}].kind unsupported: ${surface.kind}`);
      }
      if (surface.touch_target && isObject(surface.touch_target)) {
        const tt = surface.touch_target;
        if (tt.interactive !== false) {
          if (asNumber(tt.min_width_dp, 0) < MIN_TOUCH_TARGET_DP) {
            errors.push(
              `surfaces[${index}].touch_target.min_width_dp must be >= ${MIN_TOUCH_TARGET_DP}`
            );
          }
          if (asNumber(tt.min_height_dp, 0) < MIN_TOUCH_TARGET_DP) {
            errors.push(
              `surfaces[${index}].touch_target.min_height_dp must be >= ${MIN_TOUCH_TARGET_DP}`
            );
          }
        }
      }
    });
  }
  if (!isObject(artifact.viewport)) {
    errors.push('viewport is required');
  } else {
    const minTouch = asNumber(artifact.viewport.min_touch_target_dp, MIN_TOUCH_TARGET_DP);
    if (minTouch < MIN_TOUCH_TARGET_DP) {
      errors.push(`viewport.min_touch_target_dp must be >= ${MIN_TOUCH_TARGET_DP}`);
    }
  }
  if (!isObject(artifact.focus_restoration)) {
    errors.push('focus_restoration is required');
  }
  if (!isObject(artifact.glasses_fallback)) {
    errors.push('glasses_fallback is required');
  }
  return { valid: errors.length === 0, errors };
}

function touchStyleFromTarget(touchTarget) {
  if (!isObject(touchTarget)) {
    return {
      minWidth: MIN_TOUCH_TARGET_DP,
      minHeight: MIN_TOUCH_TARGET_DP,
      margin: MIN_TOUCH_SPACING_DP / 2,
    };
  }
  const interactive = touchTarget.interactive !== false;
  return {
    minWidth: interactive
      ? Math.max(MIN_TOUCH_TARGET_DP, asNumber(touchTarget.min_width_dp, MIN_TOUCH_TARGET_DP))
      : asNumber(touchTarget.min_width_dp, 0),
    minHeight: interactive
      ? Math.max(MIN_TOUCH_TARGET_DP, asNumber(touchTarget.min_height_dp, MIN_TOUCH_TARGET_DP))
      : asNumber(touchTarget.min_height_dp, 0),
    margin: Math.max(
      MIN_TOUCH_SPACING_DP / 2,
      asNumber(touchTarget.min_spacing_dp, MIN_TOUCH_SPACING_DP) / 2
    ),
  };
}

function accessibilityProps(surface) {
  const role = asString(surface.accessible_role, 'none');
  const live = asString(surface.live_region, '');
  return {
    accessible: true,
    accessibilityLabel: asString(surface.accessible_name || surface.title, surface.surface_id),
    accessibilityRole: role === 'summary' ? 'text' : role || 'text',
    accessibilityLiveRegion: live || undefined,
    accessibilityState: {
      busy: surface.interaction_state === 'pending',
      disabled: surface.interaction_state === 'unavailable'
        || surface.interaction_state === 'offline',
    },
  };
}

function actionItemsFromSurface(surface) {
  const ids = asArray(surface.action_ids);
  if (ids.length === 0) {
    if (surface.kind === 'confirmation') {
      return [
        { id: `${surface.surface_id}:confirm`, label: 'Confirm', phrase: 'confirm' },
        { id: `${surface.surface_id}:cancel`, label: 'Cancel', phrase: 'cancel' },
      ];
    }
    return [];
  }
  return ids.map((id) => ({
    id,
    label: asString(surface.title, id),
    phrase: asString(surface.title, id).toLowerCase(),
    source_item_id: surface.source_item_id,
  }));
}

/**
 * Map one mobile surface model to a companion ORB card shape
 * (compatible with UICardList / agent card consumers).
 */
export function surfaceToOrbCard(surface, { screenReaderOrder = null } = {}) {
  if (!isObject(surface)) {
    throw new TypeError('surfaceToOrbCard expects a surface object');
  }
  const kind = asString(surface.kind, 'card');
  const interactionState = asString(surface.interaction_state, 'idle');
  const lines = asArray(surface.lines).map(String);
  if (surface.body) {
    lines.unshift(String(surface.body));
  }
  if (surface.fallback_ref) {
    lines.push(`Fallback: ${surface.fallback_ref}`);
  }

  const orderEntry = Array.isArray(screenReaderOrder)
    ? screenReaderOrder.find((entry) => entry?.node_id === surface.surface_id)
    : null;

  return {
    id: surface.surface_id,
    surface_id: surface.surface_id,
    kind,
    title: asString(surface.title, surface.surface_id),
    subtitle: kind === 'fallback' ? 'Companion fallback' : undefined,
    lines,
    status_badge: interactionState !== 'idle'
      ? interactionState.replace(/_/g, ' ')
      : (kind === 'fallback' ? 'Fallback' : undefined),
    status_tone: asString(surface.status_tone, 'neutral'),
    is_live: interactionState === 'pending',
    live_label: interactionState === 'pending' ? 'Pending' : undefined,
    action_items: actionItemsFromSurface(surface),
    deep_link: undefined,
    source_item_id: surface.source_item_id,
    semantic_kind: surface.semantic_kind,
    disposition: surface.disposition,
    mandatory: asBoolean(surface.mandatory, false),
    component_id: asString(surface.component_id),
    interaction_state: interactionState,
    needs_virtual_keyboard: asBoolean(surface.needs_virtual_keyboard, false),
    screen_reader_order: orderEntry
      ? asNumber(orderEntry.order, asNumber(surface.screen_reader_order, 0))
      : asNumber(surface.screen_reader_order, 0),
    touch_style: touchStyleFromTarget(surface.touch_target),
    accessibility: accessibilityProps(surface),
    metadata: isObject(surface.metadata) ? { ...surface.metadata } : {},
  };
}

/**
 * Build safe-area style tokens for React Native SafeAreaView / padding.
 */
export function safeAreaStyle(viewport = {}) {
  const safe = isObject(viewport.safe_area) ? viewport.safe_area : {};
  return {
    paddingTop: asNumber(safe.top_dp, 0),
    paddingRight: asNumber(safe.right_dp, 0),
    paddingBottom: asNumber(safe.bottom_dp, 0),
    paddingLeft: asNumber(safe.left_dp, 0),
    respectNotch: safe.respect_notch !== false,
    respectHomeIndicator: safe.respect_home_indicator !== false,
  };
}

/**
 * Virtual keyboard avoidance contract for forms / text inputs.
 */
export function virtualKeyboardContract(viewport = {}) {
  const vk = isObject(viewport.virtual_keyboard) ? viewport.virtual_keyboard : {};
  return {
    avoidOcclusion: vk.avoid_occlusion !== false,
    scrollFocusedIntoView: vk.scroll_focused_into_view !== false,
    dismissOnSubmit: vk.dismiss_on_submit !== false,
    inputMode: asString(vk.input_mode, 'default'),
    requiredForIds: asArray(vk.required_for_ids).map(String),
    keyboardShouldPersistTaps: 'handled',
    keyboardVerticalOffset: 0,
  };
}

/**
 * Focus restoration plan for confirmation modals / navigation.
 */
export function focusRestorationPlan(artifact) {
  const plan = isObject(artifact?.focus_restoration) ? artifact.focus_restoration : {};
  return {
    strategy: asString(plan.strategy, 'announce_only'),
    restoreTargetId: asString(plan.restore_target_id),
    announceOnRestore: plan.announce_on_restore !== false,
    trapWhileConfirmation: plan.trap_while_confirmation !== false,
  };
}

/**
 * Orientation presentation hints (not device lock policy ownership).
 */
export function orientationContract(viewport = {}) {
  return {
    policy: asString(viewport.orientation, 'portrait_preferred'),
    supportsLandscape: ['landscape_supported', 'any'].includes(
      asString(viewport.orientation, 'portrait_preferred')
    ),
    preferred: asString(viewport.orientation, 'portrait_preferred'),
  };
}

/**
 * Connectivity / offline / unavailable banner for the companion shell.
 */
export function connectivityBanner(artifact) {
  const connectivity = asString(artifact?.connectivity, 'online');
  if (connectivity === 'online') {
    return null;
  }
  const statusSurface = asArray(artifact?.surfaces).find(
    (surface) => surface?.kind === 'status'
      && (surface.interaction_state === 'offline'
        || surface.interaction_state === 'unavailable'
        || surface.semantic_kind === 'availability')
  );
  return {
    connectivity,
    title: connectivity === 'offline' ? 'Offline' : 'Unavailable',
    message: asString(
      statusSurface?.body,
      connectivity === 'offline'
        ? 'Companion is offline; actions are deferred.'
        : 'Required mobile surface is unavailable.'
    ),
    status_tone: 'danger',
    accessibility: {
      accessible: true,
      accessibilityRole: 'alert',
      accessibilityLiveRegion: 'assertive',
      accessibilityLabel: connectivity === 'offline' ? 'Offline' : 'Unavailable',
    },
  };
}

/**
 * Glasses → mobile companion fallback presentation.
 */
export function glassesFallbackView(artifact) {
  const gf = isObject(artifact?.glasses_fallback) ? artifact.glasses_fallback : {};
  const active = asBoolean(gf.active, false);
  return {
    active,
    reason: asString(gf.reason, 'none'),
    sourceProfileFamily: asString(gf.source_profile_family),
    fallbackCapabilityId: asString(gf.fallback_capability_id, 'mobile_companion'),
    glassesNodeIds: asArray(gf.glasses_node_ids).map(String),
    summary: asString(gf.summary),
    policyOwner: POLICY_OWNER,
    card: active
      ? {
        id: 'mobile:glasses-fallback-banner',
        title: 'Glasses fallback',
        subtitle: 'Showing content on mobile companion',
        lines: [
          asString(gf.summary, `reason:${asString(gf.reason, 'none')}`),
          `policy_owner=${POLICY_OWNER}`,
        ],
        status_badge: 'Fallback',
        status_tone: 'neutral',
        action_items: [],
        accessibility: {
          accessible: true,
          accessibilityRole: 'status',
          accessibilityLiveRegion: 'polite',
          accessibilityLabel: 'Glasses fallback active on mobile companion',
        },
      }
      : null,
  };
}

/**
 * Pending / error / confirmation surface groups for the companion shell.
 */
export function interactionStateGroups(artifact) {
  const surfaces = asArray(artifact?.surfaces);
  const group = (state) => surfaces.filter((s) => s?.interaction_state === state);
  return {
    pending: group('pending').map((s) => surfaceToOrbCard(s, {
      screenReaderOrder: artifact?.screen_reader_order,
    })),
    error: group('error').map((s) => surfaceToOrbCard(s, {
      screenReaderOrder: artifact?.screen_reader_order,
    })),
    confirmation: group('confirmation').map((s) => surfaceToOrbCard(s, {
      screenReaderOrder: artifact?.screen_reader_order,
    })),
    offline: group('offline').map((s) => surfaceToOrbCard(s, {
      screenReaderOrder: artifact?.screen_reader_order,
    })),
    unavailable: group('unavailable').map((s) => surfaceToOrbCard(s, {
      screenReaderOrder: artifact?.screen_reader_order,
    })),
  };
}

/**
 * Screen-reader traversal list (independent of visual card order).
 */
export function screenReaderTraversal(artifact) {
  const entries = asArray(artifact?.screen_reader_order)
    .slice()
    .sort((a, b) => asNumber(a?.order, 0) - asNumber(b?.order, 0));
  return entries.map((entry) => ({
    order: asNumber(entry.order, 0),
    nodeId: asString(entry.node_id),
    accessibleName: asString(entry.accessible_name),
    role: asString(entry.role, 'none'),
    liveRegion: asString(entry.live_region),
    importance: asNumber(entry.importance, 0),
  }));
}

/**
 * Full adapt: mobile projection artifact → React Native companion ORB model.
 */
export function adaptMobileProjection(artifact, options = {}) {
  const validation = validateMobileProjectionArtifact(artifact);
  if (!validation.valid && options.strict !== false) {
    const error = new Error(
      `Invalid mobile projection artifact: ${validation.errors.join('; ')}`
    );
    error.name = 'UIIRMobileAdapterValidationError';
    error.errors = validation.errors;
    throw error;
  }

  const surfaces = asArray(artifact?.surfaces);
  const screenReaderOrder = asArray(artifact?.screen_reader_order);
  const cards = surfaces
    .filter((s) => s && SURFACE_KINDS.has(s.kind))
    .slice()
    .sort((a, b) => asNumber(a.order, 0) - asNumber(b.order, 0)
      || asString(a.surface_id).localeCompare(asString(b.surface_id)))
    .map((surface) => surfaceToOrbCard(surface, { screenReaderOrder }));

  const byKind = {};
  for (const kind of SURFACE_KINDS) {
    byKind[kind] = cards.filter((card) => card.kind === kind);
  }

  const viewport = isObject(artifact?.viewport) ? artifact.viewport : {};
  const glasses = glassesFallbackView(artifact);
  const connectivity = connectivityBanner(artifact);
  const focus = focusRestorationPlan(artifact);
  const states = interactionStateGroups(artifact);

  return {
    interface: UIIR_MOBILE_ADAPTER_INTERFACE,
    sourceInterface: asString(artifact?.interface, UIIR_MOBILE_PROJECTION_INTERFACE),
    schemaVersion: asString(
      artifact?.schema_version,
      UIIR_MOBILE_PROJECTION_SCHEMA_VERSION
    ),
    policyOwner: asString(artifact?.policy_owner, POLICY_OWNER),
    artifactId: asString(artifact?.artifact_id),
    projectionArtifactId: asString(artifact?.projection_artifact_id),
    projectionStatus: asString(artifact?.projection_status),
    profileId: asString(artifact?.profile_id),
    documentId: asString(artifact?.document_id),
    connectivity: asString(artifact?.connectivity, 'online'),
    cards,
    surfacesByKind: byKind,
    navigation: byKind.navigation,
    forms: byKind.form,
    lists: byKind.list,
    confirmations: byKind.confirmation,
    fallbacks: byKind.fallback,
    status: byKind.status,
    interactionStates: states,
    screenReaderOrder: screenReaderTraversal(artifact),
    focusRestoration: focus,
    viewport: {
      orientation: orientationContract(viewport),
      safeArea: safeAreaStyle(viewport),
      virtualKeyboard: virtualKeyboardContract(viewport),
      minTouchTargetDp: Math.max(
        MIN_TOUCH_TARGET_DP,
        asNumber(viewport.min_touch_target_dp, MIN_TOUCH_TARGET_DP)
      ),
      minTouchSpacingDp: Math.max(
        MIN_TOUCH_SPACING_DP,
        asNumber(viewport.min_touch_spacing_dp, MIN_TOUCH_SPACING_DP)
      ),
      maxContentWidthDp: asNumber(viewport.max_content_width_dp, 480),
    },
    connectivityBanner: connectivity,
    glassesFallback: glasses,
    lossReport: isObject(artifact?.loss_report) ? artifact.loss_report : {},
    notes: asArray(artifact?.notes).map(String),
    validation,
  };
}

/**
 * Class facade matching other ORB adapters in this package.
 */
export class UIIRMobileAdapter {
  constructor(options = {}) {
    this.interface = UIIR_MOBILE_ADAPTER_INTERFACE;
    this.strict = options.strict !== false;
  }

  adapt(artifact, options = {}) {
    return adaptMobileProjection(artifact, {
      strict: options.strict !== undefined ? options.strict : this.strict,
    });
  }

  validate(artifact) {
    return validateMobileProjectionArtifact(artifact);
  }
}

export default {
  UIIR_MOBILE_ADAPTER_INTERFACE,
  UIIR_MOBILE_PROJECTION_INTERFACE,
  UIIR_MOBILE_PROJECTION_SCHEMA_VERSION,
  POLICY_OWNER,
  MIN_TOUCH_TARGET_DP,
  MIN_TOUCH_SPACING_DP,
  UIIRMobileAdapter,
  adaptMobileProjection,
  validateMobileProjectionArtifact,
  surfaceToOrbCard,
  safeAreaStyle,
  virtualKeyboardContract,
  focusRestorationPlan,
  orientationContract,
  connectivityBanner,
  glassesFallbackView,
  interactionStateGroups,
  screenReaderTraversal,
};
