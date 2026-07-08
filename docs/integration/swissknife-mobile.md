# Swissknife Mobile Interoperability

`VAIOS-G700` proves `swissknife` and `mobile` interoperate through a shared
control-surface contract rather than parallel local conventions. The scanner
evidence term is `interface contract swissknife mobile`.

## Contract Boundary

Swissknife owns the mediation schemas:

- `swissknife/contracts/control_surface_contract.schema.json`
- `swissknife/contracts/interaction_envelope.schema.json`
- `swissknife/contracts/policy_decision.schema.json`
- `swissknife/contracts/mediation_receipt.schema.json`

Mobile advertises those schemas through:

- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/utils/metaWearablesDatDisplayWidgetContract.js`

The mobile ORB descriptor exports `SWISSKNIFE_MOBILE_INTEROP_CONTRACT`, which
names the `interface contract swissknife mobile` proof, the schema refs, and the
runtime handoff operations. `descriptorRef` preserves that metadata when mobile
registers edge capabilities with Swissknife.

## Runtime Handoff

The supported Swissknife-to-mobile handoff is:

1. `register_edge_capabilities` publishes mobile ORB and display widget
   descriptors with `control_surface_contract`, `interaction_envelope`,
   `policy_decision`, and `mediation_receipt` schema refs.
2. `publish_glasses_event` normalizes a mobile glasses event into an
   `interaction_envelope` with actor, agent identity, allowed surfaces,
   arguments, and `arguments_hash`.
3. `invoke_service` runs the Swissknife-mediated service call and keeps the
   selected logic binding and policy bundle in the envelope.
4. `dispatch_glasses_response` returns display widget actions to mobile with a
   mediation receipt and ORB receipt CID.

Display widget actions are mapped in
`mobile/src/utils/metaWearablesDatDisplayWidgetContract.js` from action id to
ORB operation and native Meta Wearables DAT method. For example,
`mobile_render_display_widget` maps to `render_widget` and
`renderDisplayWidget`.

## Validation

`tests/integration/test_swissknife_mobile_interop.py` validates sample
Swissknife-mobile payloads against both JSON Schemas, checks that mobile
descriptors advertise the shared schema refs and handoff operations, and records
the objective validation repair evidence for `VAIOS-G700`.
