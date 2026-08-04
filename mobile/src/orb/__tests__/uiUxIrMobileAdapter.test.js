import {
  MIN_TOUCH_TARGET_DP,
  POLICY_OWNER,
  UIIR_MOBILE_ADAPTER_INTERFACE,
  UIIR_MOBILE_PROJECTION_INTERFACE,
  UIIRMobileAdapter,
  adaptMobileProjection,
  connectivityBanner,
  focusRestorationPlan,
  glassesFallbackView,
  interactionStateGroups,
  orientationContract,
  safeAreaStyle,
  screenReaderTraversal,
  surfaceToOrbCard,
  validateMobileProjectionArtifact,
  virtualKeyboardContract,
} from '../uiUxIrMobileAdapter';

function sampleArtifact(overrides = {}) {
  return {
    artifact_id: 'mobile:proj:problem:mobile:profile:mobile:default',
    interface: UIIR_MOBILE_PROJECTION_INTERFACE,
    schema_version: 'ui-mobile-projection/v1',
    policy_owner: POLICY_OWNER,
    projection_artifact_id: 'proj:problem:mobile:profile:mobile:default',
    projection_status: 'satisfied',
    profile_id: 'profile:mobile:default',
    document_id: 'doc:mobile-companion',
    connectivity: 'online',
    notes: ['mobile is presentation-only; policy_owner=UIProjectionSolver@1'],
    loss_report: { report_id: 'loss:1', losses: [] },
    viewport: {
      orientation: 'portrait_preferred',
      min_touch_target_dp: 44,
      min_touch_spacing_dp: 8,
      max_content_width_dp: 480,
      safe_area: {
        top_dp: 44,
        right_dp: 0,
        bottom_dp: 34,
        left_dp: 0,
        respect_notch: true,
        respect_home_indicator: true,
      },
      virtual_keyboard: {
        avoid_occlusion: true,
        scroll_focused_into_view: true,
        dismiss_on_submit: true,
        input_mode: 'default',
        required_for_ids: ['mobile:form_email'],
      },
    },
    focus_restoration: {
      strategy: 'previous_target',
      restore_target_id: 'mobile:action_submit',
      announce_on_restore: true,
      trap_while_confirmation: true,
    },
    glasses_fallback: {
      active: false,
      reason: 'none',
      source_profile_family: 'mobile',
      fallback_capability_id: 'mobile_companion',
      glasses_node_ids: [],
      summary: '',
    },
    screen_reader_order: [
      {
        order: 0,
        node_id: 'mobile:confirm_delete',
        accessible_name: 'Confirm delete',
        role: 'dialog',
        live_region: 'assertive',
        importance: 100,
      },
      {
        order: 1,
        node_id: 'mobile:error_surface',
        accessible_name: 'Error banner',
        role: 'alert',
        live_region: 'assertive',
        importance: 99,
      },
      {
        order: 2,
        node_id: 'mobile:action_submit',
        accessible_name: 'Submit',
        role: 'button',
        live_region: '',
        importance: 98,
      },
      {
        order: 3,
        node_id: 'mobile:form_email',
        accessible_name: 'email input field',
        role: 'form',
        live_region: '',
        importance: 40,
      },
    ],
    surfaces: [
      {
        surface_id: 'mobile:action_submit',
        kind: 'card',
        source_item_id: 'action_submit',
        semantic_kind: 'action',
        disposition: 'preserved',
        order: 0,
        title: 'Submit',
        mandatory: true,
        body: '',
        interaction_state: 'idle',
        component_id: 'cmp_submit',
        action_ids: ['action_submit'],
        touch_target: {
          target_id: 'touch:action_submit',
          min_width_dp: 44,
          min_height_dp: 44,
          min_spacing_dp: 8,
          interactive: true,
        },
        needs_virtual_keyboard: false,
        screen_reader_order: 2,
        accessible_name: 'Submit',
        accessible_role: 'button',
        live_region: '',
        status_tone: 'neutral',
        fallback_ref: '',
        lines: [],
        metadata: {},
      },
      {
        surface_id: 'mobile:confirm_delete',
        kind: 'confirmation',
        source_item_id: 'confirm_delete',
        semantic_kind: 'confirmation',
        disposition: 'preserved',
        order: 1,
        title: 'Confirm delete',
        mandatory: true,
        body: 'Confirm: Confirm delete',
        interaction_state: 'confirmation',
        component_id: '',
        action_ids: ['confirm_delete'],
        touch_target: {
          target_id: 'touch:confirm_delete',
          min_width_dp: 44,
          min_height_dp: 44,
          min_spacing_dp: 8,
          interactive: true,
        },
        needs_virtual_keyboard: false,
        screen_reader_order: 0,
        accessible_name: 'Confirm delete',
        accessible_role: 'dialog',
        live_region: 'assertive',
        status_tone: 'warning',
        fallback_ref: '',
        lines: ['state:confirmation'],
        metadata: {},
      },
      {
        surface_id: 'mobile:error_surface',
        kind: 'status',
        source_item_id: 'error_surface',
        semantic_kind: 'error',
        disposition: 'preserved',
        order: 2,
        title: 'Error banner',
        mandatory: true,
        body: 'Error: Error banner',
        interaction_state: 'error',
        component_id: '',
        action_ids: [],
        touch_target: {
          target_id: 'touch:error_surface',
          min_width_dp: 0,
          min_height_dp: 0,
          min_spacing_dp: 8,
          interactive: false,
        },
        needs_virtual_keyboard: false,
        screen_reader_order: 1,
        accessible_name: 'Error banner',
        accessible_role: 'alert',
        live_region: 'assertive',
        status_tone: 'danger',
        fallback_ref: '',
        lines: ['state:error'],
        metadata: {},
      },
      {
        surface_id: 'mobile:form_email',
        kind: 'form',
        source_item_id: 'form_email',
        semantic_kind: 'component',
        disposition: 'preserved',
        order: 3,
        title: 'email input field',
        mandatory: false,
        body: '',
        interaction_state: 'idle',
        component_id: 'cmp_email',
        action_ids: [],
        touch_target: {
          target_id: 'touch:form_email',
          min_width_dp: 44,
          min_height_dp: 44,
          min_spacing_dp: 8,
          interactive: true,
        },
        needs_virtual_keyboard: true,
        screen_reader_order: 3,
        accessible_name: 'email input field',
        accessible_role: 'form',
        live_region: '',
        status_tone: 'neutral',
        fallback_ref: '',
        lines: [],
        metadata: {},
      },
      {
        surface_id: 'mobile:nav_tabs',
        kind: 'navigation',
        source_item_id: 'nav_tabs',
        semantic_kind: 'component',
        disposition: 'preserved',
        order: 4,
        title: 'navigation tabs',
        mandatory: false,
        body: '',
        interaction_state: 'idle',
        component_id: 'cmp_nav',
        action_ids: [],
        touch_target: {
          target_id: 'touch:nav_tabs',
          min_width_dp: 44,
          min_height_dp: 44,
          min_spacing_dp: 8,
          interactive: true,
        },
        needs_virtual_keyboard: false,
        screen_reader_order: 4,
        accessible_name: 'navigation tabs',
        accessible_role: 'navigation',
        live_region: '',
        status_tone: 'neutral',
        fallback_ref: '',
        lines: [],
        metadata: {},
      },
      {
        surface_id: 'mobile:list_results',
        kind: 'list',
        source_item_id: 'list_results',
        semantic_kind: 'component',
        disposition: 'preserved',
        order: 5,
        title: 'results list',
        mandatory: false,
        body: '',
        interaction_state: 'idle',
        component_id: 'cmp_list',
        action_ids: [],
        touch_target: {
          target_id: 'touch:list_results',
          min_width_dp: 44,
          min_height_dp: 44,
          min_spacing_dp: 8,
          interactive: true,
        },
        needs_virtual_keyboard: false,
        screen_reader_order: 5,
        accessible_name: 'results list',
        accessible_role: 'list',
        live_region: '',
        status_tone: 'neutral',
        fallback_ref: '',
        lines: [],
        metadata: {},
      },
      {
        surface_id: 'mobile:pending_sync',
        kind: 'card',
        source_item_id: 'pending_sync',
        semantic_kind: 'component',
        disposition: 'preserved',
        order: 6,
        title: 'pending sync status',
        mandatory: false,
        body: 'Pending: pending sync status',
        interaction_state: 'pending',
        component_id: 'cmp_pending',
        action_ids: [],
        touch_target: {
          target_id: 'touch:pending_sync',
          min_width_dp: 44,
          min_height_dp: 44,
          min_spacing_dp: 8,
          interactive: true,
        },
        needs_virtual_keyboard: false,
        screen_reader_order: 6,
        accessible_name: 'pending sync status',
        accessible_role: 'summary',
        live_region: 'polite',
        status_tone: 'active',
        fallback_ref: '',
        lines: ['state:pending'],
        metadata: {},
      },
      {
        surface_id: 'mobile:fallback_card',
        kind: 'fallback',
        source_item_id: 'fallback_item',
        semantic_kind: 'action',
        disposition: 'fallback',
        order: 7,
        title: 'Fallback action',
        mandatory: true,
        body: 'Fallback surface for Fallback action',
        interaction_state: 'idle',
        component_id: '',
        action_ids: ['fallback_item'],
        touch_target: {
          target_id: 'touch:fallback_item',
          min_width_dp: 44,
          min_height_dp: 44,
          min_spacing_dp: 8,
          interactive: true,
        },
        needs_virtual_keyboard: false,
        screen_reader_order: 7,
        accessible_name: 'Fallback action',
        accessible_role: 'button',
        live_region: '',
        status_tone: 'neutral',
        fallback_ref: 'fallback:audio:action',
        lines: ['fallback:fallback:audio:action', 'disposition:fallback'],
        metadata: {},
      },
    ],
    ...overrides,
  };
}

describe('uiUxIrMobileAdapter', () => {
  it('validates a well-formed mobile projection artifact', () => {
    const result = validateMobileProjectionArtifact(sampleArtifact());
    expect(result.valid).toBe(true);
    expect(result.errors).toEqual([]);
  });

  it('rejects undersized interactive touch targets and foreign policy owners', () => {
    const badTouch = sampleArtifact({
      surfaces: [
        {
          ...sampleArtifact().surfaces[0],
          touch_target: {
            target_id: 'touch:tiny',
            min_width_dp: 20,
            min_height_dp: 20,
            min_spacing_dp: 8,
            interactive: true,
          },
        },
      ],
    });
    const touchResult = validateMobileProjectionArtifact(badTouch);
    expect(touchResult.valid).toBe(false);
    expect(touchResult.errors.some((e) => e.includes('min_width_dp'))).toBe(true);

    const badPolicy = sampleArtifact({ policy_owner: 'MobileLocalPolicy@1' });
    const policyResult = validateMobileProjectionArtifact(badPolicy);
    expect(policyResult.valid).toBe(false);
    expect(policyResult.errors.some((e) => e.includes('policy'))).toBe(true);
  });

  it('adapts cards/forms/lists/navigation/confirmation/fallback into ORB surface', () => {
    const model = adaptMobileProjection(sampleArtifact());

    expect(model.interface).toBe(UIIR_MOBILE_ADAPTER_INTERFACE);
    expect(model.policyOwner).toBe(POLICY_OWNER);
    expect(model.cards.length).toBeGreaterThanOrEqual(6);
    expect(model.confirmations.length).toBe(1);
    expect(model.forms.length).toBe(1);
    expect(model.lists.length).toBe(1);
    expect(model.navigation.length).toBe(1);
    expect(model.fallbacks.length).toBe(1);

    const submit = model.cards.find((c) => c.id === 'mobile:action_submit');
    expect(submit.touch_style.minWidth).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_DP);
    expect(submit.touch_style.minHeight).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_DP);
    expect(submit.accessibility.accessibilityLabel).toBe('Submit');
    expect(submit.action_items[0].id).toBe('action_submit');
  });

  it('exposes orientation, safe areas, and virtual keyboard contracts', () => {
    const artifact = sampleArtifact();
    const model = adaptMobileProjection(artifact);

    expect(model.viewport.orientation).toEqual(
      orientationContract(artifact.viewport)
    );
    expect(model.viewport.orientation.policy).toBe('portrait_preferred');
    expect(model.viewport.safeArea).toEqual(safeAreaStyle(artifact.viewport));
    expect(model.viewport.safeArea.paddingTop).toBe(44);
    expect(model.viewport.safeArea.paddingBottom).toBe(34);
    expect(model.viewport.virtualKeyboard).toEqual(
      virtualKeyboardContract(artifact.viewport)
    );
    expect(model.viewport.virtualKeyboard.avoidOcclusion).toBe(true);
    expect(model.viewport.virtualKeyboard.requiredForIds).toContain(
      'mobile:form_email'
    );
    expect(model.viewport.minTouchTargetDp).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_DP);
  });

  it('preserves screen reader order and focus restoration', () => {
    const artifact = sampleArtifact();
    const model = adaptMobileProjection(artifact);
    const traversal = screenReaderTraversal(artifact);

    expect(model.screenReaderOrder[0].nodeId).toBe('mobile:confirm_delete');
    expect(model.screenReaderOrder[0].role).toBe('dialog');
    expect(traversal.map((e) => e.order)).toEqual([0, 1, 2, 3]);

    expect(model.focusRestoration).toEqual(focusRestorationPlan(artifact));
    expect(model.focusRestoration.strategy).toBe('previous_target');
    expect(model.focusRestoration.restoreTargetId).toBe('mobile:action_submit');
    expect(model.focusRestoration.trapWhileConfirmation).toBe(true);
  });

  it('groups pending, error, and confirmation interaction states', () => {
    const artifact = sampleArtifact();
    const groups = interactionStateGroups(artifact);
    const model = adaptMobileProjection(artifact);

    expect(groups.pending.length).toBe(1);
    expect(groups.error.length).toBe(1);
    expect(groups.confirmation.length).toBe(1);
    expect(model.interactionStates.error[0].status_tone).toBe('danger');
    expect(model.interactionStates.confirmation[0].accessibility.accessibilityRole)
      .toBe('dialog');
  });

  it('surfaces offline and unavailable connectivity banners', () => {
    const offline = sampleArtifact({
      connectivity: 'offline',
      surfaces: [
        ...sampleArtifact().surfaces,
        {
          surface_id: 'mobile:connectivity:offline',
          kind: 'status',
          source_item_id: 'connectivity:offline',
          semantic_kind: 'availability',
          disposition: 'adapted',
          order: 99,
          title: 'Offline',
          mandatory: true,
          body: 'Companion is offline; actions are deferred.',
          interaction_state: 'offline',
          accessible_name: 'Offline',
          accessible_role: 'alert',
          live_region: 'assertive',
          status_tone: 'danger',
          action_ids: [],
          lines: ['connectivity:offline'],
          touch_target: {
            target_id: 'touch:offline',
            interactive: false,
            min_width_dp: 0,
            min_height_dp: 0,
            min_spacing_dp: 8,
          },
          needs_virtual_keyboard: false,
          screen_reader_order: 0,
          fallback_ref: '',
          metadata: { connectivity: 'offline' },
        },
      ],
    });

    const banner = connectivityBanner(offline);
    expect(banner).not.toBeNull();
    expect(banner.connectivity).toBe('offline');
    expect(banner.accessibility.accessibilityRole).toBe('alert');

    const adapted = adaptMobileProjection(offline);
    expect(adapted.connectivityBanner.connectivity).toBe('offline');
    expect(adapted.interactionStates.offline.length).toBe(1);
  });

  it('maps glasses fallback without claiming policy ownership', () => {
    const artifact = sampleArtifact({
      glasses_fallback: {
        active: true,
        reason: 'glasses_policy_fallback',
        source_profile_family: 'glasses',
        fallback_capability_id: 'mobile_companion',
        glasses_node_ids: ['action_submit'],
        summary:
          'Glasses content projected to mobile companion (glasses_policy_fallback); policy owner remains UIProjectionSolver@1',
      },
      notes: [
        'mobile is presentation-only; policy_owner=UIProjectionSolver@1',
        'glasses_fallback=glasses_policy_fallback',
      ],
    });

    const view = glassesFallbackView(artifact);
    expect(view.active).toBe(true);
    expect(view.reason).toBe('glasses_policy_fallback');
    expect(view.policyOwner).toBe(POLICY_OWNER);
    expect(view.card.lines.some((line) => line.includes(POLICY_OWNER))).toBe(true);

    const model = adaptMobileProjection(artifact);
    expect(model.glassesFallback.active).toBe(true);
    expect(model.policyOwner).toBe(POLICY_OWNER);
  });

  it('surfaceToOrbCard builds UICardList-compatible cards', () => {
    const card = surfaceToOrbCard(sampleArtifact().surfaces[0]);
    expect(card.id).toBe('mobile:action_submit');
    expect(card.title).toBe('Submit');
    expect(Array.isArray(card.action_items)).toBe(true);
    expect(card.touch_style.minWidth).toBeGreaterThanOrEqual(44);
  });

  it('class facade adapts and validates', () => {
    const adapter = new UIIRMobileAdapter();
    expect(adapter.interface).toBe(UIIR_MOBILE_ADAPTER_INTERFACE);
    const model = adapter.adapt(sampleArtifact());
    expect(model.cards.length).toBeGreaterThan(0);
    expect(adapter.validate(sampleArtifact()).valid).toBe(true);
  });

  it('throws in strict mode on invalid artifacts', () => {
    expect(() => adaptMobileProjection({ surfaces: 'nope' })).toThrow(
      /Invalid mobile projection artifact/
    );
  });
});
