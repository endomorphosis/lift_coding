# SwissKnife Mobile Interoperability

MGW-569 closes the VAIOS-G700 objective validation repair for the `swissknife`
and `mobile` pair. The scanner-visible contract name is `interface contract
swissknife mobile`.

## Contract

SwissKnife is the producer for Meta glasses display-widget actions. Mobile is
the consumer through the Meta Wearables DAT bridge. The stable contract id is
`handsfree.meta-glasses/swissknife-mobile-interop@0.1.0`.

The shared handoff carries:

- `contract`: `handsfree.meta-glasses/display-widget-action@0.1.0`
- `interop_contract`: `interface contract swissknife mobile`
- `control_surface_contract_ref`: `control_surface_contract:swissknife-mobile:display-widget`
- `interaction_envelope_ref`: `interaction_envelope:swissknife-mobile:display-widget`
- `interaction_envelope`, `policy_bundle_ref`, and `mediation_receipt`
- schema references for `control_surface_contract`, `interaction_envelope`,
  `mcp_plus_plus_compatibility_receipt`, and `mediation_receipt`

## Runtime Handoff

`swissknife/src/services/glasses/meta-glasses-display-orb-adapter.ts` emits
mobile actions for the display ORB operations:

`render_widget`, `update_widget`, `clear_widget`, `focus_next`,
`focus_previous`, `activate`, `reset_session`, `play_video`, and
`subscribe_updates`.

`mobile/src/utils/metaWearablesDatDisplayWidgetContract.js` maps those operation
names onto mobile action ids and DAT bridge methods. It also exposes
`normalizeSwissKnifeMobileDisplayWidgetAction`, which builds the
`interaction_envelope` and `mediation_receipt` when a SwissKnife action arrives
without a precomputed receipt.

`mobile/src/orb/metaGlassesOrbDescriptors.js` advertises
`SWISSKNIFE_MOBILE_INTEROP_INTERFACE`, linking the mobile ORB bridge descriptor
and the display-widget bridge descriptor to the same contract.

## Validation

The objective repair is covered by
`tests/integration/test_swissknife_mobile_interop.py`. That test parses the
mobile and SwissKnife contracts, validates the descriptor/spec operation set,
checks the schema fields, and syntax-checks the mobile JavaScript bridge as an
ES module. This keeps the supervisor-fed backlog aligned with VAIOS-G700 while
also carrying the shared swissknife interoperability packet terms for VAIOS-G701
through VAIOS-G706.
