# SwissKnife Mobile Interop

This note is the VAI-661 objective validation repair for VAIOS-G700 and the
shared `goal_packet/interoperability/swissknife/06921590135c` packet
(VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706).

The `interface contract swissknife mobile` handoff is:

- SwissKnife emits or mediates Meta glasses ORB work with
  `swissknife/contracts/control_surface_contract.schema.json` and
  `swissknife/contracts/interaction_envelope.schema.json`.
- Mobile advertises the handoff through
  `mobile/src/orb/metaGlassesOrbDescriptors.js` as
  `SWISSKNIFE_MOBILE_INTEROP_INTERFACE` and
  `SWISSKNIFE_MOBILE_INTEROP_DESCRIPTOR`.
- Mobile maps SwissKnife display-widget follow-up actions to native DAT methods
  through `mobile/src/utils/metaWearablesDatDisplayWidgetContract.js` and
  `SWISSKNIFE_DISPLAY_WIDGET_ACTION_CONTRACT`.
- The mobile ORB bridge consumes the same descriptor and uses the
  `policy:swissknife:mobile-interop` policy bundle for receipt-backed mobile
  edge diagnostics.

`tests/integration/test_swissknife_mobile_interop.py` is the validation gate. It
loads the mobile descriptors, checks the ORB and display-widget operation sets,
validates representative SwissKnife/mobile control-surface and interaction
envelope payloads against the SwissKnife JSON schemas, verifies the mobile ORB
bridge remains parseable as ESM, and asserts this documentation plus the
objective heap repair receipt stay scanner-visible.

No smaller child goals are required for VAIOS-G700. The sibling packet goals
reuse the same SwissKnife control-surface schema family and can add pair-specific
tests without redefining the mobile interface contract.
