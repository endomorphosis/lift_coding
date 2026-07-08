# SwissKnife Mobile Interoperability

MGW-569 closes the VAIOS-G700 objective validation repair for the interface
contract swissknife mobile handoff. The proof is intentionally contract-first:
SwissKnife owns the control-surface schemas, mobile advertises the ORB edge
descriptor, and the integration test validates a mediated display-widget
handoff through both sides.

## Contract Surfaces

- `swissknife/contracts/control_surface_contract.schema.json` defines the
  allowed surfaces, intent bindings, policy hooks, logic bindings, and
  mediation receipt requirements for SwissKnife-initiated mobile actions.
- `swissknife/contracts/interaction_envelope.schema.json` defines the
  normalized payload emitted before policy mediation, including actor,
  arguments, context, and selected logic bindings.
- `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json` keeps
  the downstream MCP++ receipt lineage visible to SwissKnife consumers.
- `swissknife/contracts/mediation_receipt.schema.json` records the final
  policy outcome before the mobile ORB edge invokes a display-widget action.

## Mobile Descriptor

`mobile/src/orb/metaGlassesOrbDescriptors.js` now exports
`SWISSKNIFE_MOBILE_INTEROP_INTERFACE`. The descriptor names the
`swissknife` and `mobile` surfaces, references the SwissKnife schema ids, and
declares the operations that can cross the handoff:

- `register_edge_capabilities`
- `render_widget`
- `update_widget`
- `clear_widget`
- `focus_next`
- `activate`
- `dispatch_glasses_response`

The mobile ORB runtime advertises this descriptor during edge registration when
the default local interface CID list is used. Existing callers that pass an
explicit two-CID list keep the original mobile and display descriptors.

## Display-Widget Handoff

`mobile/src/utils/metaWearablesDatDisplayWidgetContract.js` keeps the action
IDs, ORB operations, and native DAT method names in one table. The
`SWISSKNIFE_DISPLAY_WIDGET_HANDOFFS` export is the machine-readable bridge from
SwissKnife policy mediation to mobile execution:

- `mobile_render_display_widget` maps to `render_widget` and
  `renderDisplayWidget`.
- `mobile_update_display_widget` maps to `update_widget` and
  `updateDisplayWidget`.
- `mobile_clear_display_widget` maps to `clear_widget` and
  `clearDisplayWidget`.
- `mobile_focus_display_widget` maps to `focus_next` and `focusDisplayWidget`.
- `mobile_activate_display_widget_action` maps to `activate` and
  `activateDisplayWidgetAction`.
- `mobile_reset_display_widget_session` maps to `reset_session` and
  `resetDisplayWidgetSession`.
- `mobile_play_display_widget_video` maps to `play_video` and
  `playDisplayWidgetVideo`.
- `mobile_subscribe_display_widget_updates` maps to `subscribe_updates` and
  `subscribeDisplayWidgetUpdates`.

## Validation

`tests/integration/test_swissknife_mobile_interop.py` is the non-skipped
objective validation repair. It validates:

- the mobile interop descriptor carries SwissKnife contract refs;
- the display-widget action map matches the mobile ORB descriptor operations;
- sample control-surface, interaction-envelope, policy-decision,
  mediation-receipt, and MCP++ compatibility receipts validate against the
  SwissKnife schemas;
- this document, the discovery repair note, and the objective heap all retain
  scanner-visible VAIOS-G700 evidence.
