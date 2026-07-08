# SwissKnife Mobile Interop

MGW-569 closes the VAIOS-G700 objective validation gap for `swissknife` and
`mobile`. The interop contract is intentionally shared through committed
artifacts instead of an implicit runtime assumption.

## Contract Surface

- SwissKnife owns the canonical control-surface schemas:
  - `swissknife/contracts/control_surface_contract.schema.json`
  - `swissknife/contracts/interaction_envelope.schema.json`
  - `swissknife/contracts/policy_decision.schema.json`
  - `swissknife/contracts/mediation_receipt.schema.json`
- Mobile advertises its ORB and display widget interfaces through:
  - `mobile/src/orb/metaGlassesOrbDescriptors.js`
  - `mobile/src/utils/metaWearablesDatDisplayWidgetContract.js`
  - `spec/meta_glasses_mobile_orb_bridge_interface.json`
  - `spec/meta_glasses_display_widget_orb_interface.json`

The pair-level interop contract id is
`handsfree.meta-glasses/swissknife-mobile-interop@0.1.0`. Mobile exports it from
`swissknifeMobileInteropDescriptorBundle()`, along with the allowed surfaces,
the canonical control-surface artifact fields, and the runtime handoff map.

## Runtime Handoff

The handoff sequence is:

1. `register_edge_capabilities` registers the phone as a mobile ORB edge and
   advertises the mobile and display widget interface CIDs.
2. `bind_service` binds a SwissKnife/MCP service descriptor to the mobile edge.
3. `invoke_service` carries glasses-originated arguments through a canonical
   `interaction_envelope`, including `normalized_intent.arguments_hash`.
4. `dispatch_glasses_response` converts the result into mobile-local display,
   audio, notification, or fallback actions.

Remote clients do not define a separate policy contract. They transport
`control_surface_contract_ref`, `interaction_envelope`, `policy_decision`, and
`mediation_receipt` generated from the Hallucinate App control-surface contract.

## Validation

`tests/integration/test_swissknife_mobile_interop.py` proves:

- Mobile JS descriptor exports match the committed JSON descriptor artifacts.
- The SwissKnife `control_surface_contract` schema accepts the optional
  `mobile_remote_client_handoff` block for the pair-level contract.
- A live backend mobile ORB register/bind/invoke flow emits a schema-valid
  `interaction_envelope` with `arguments_hash`, mediation receipt, mcp-server
  service binding, and display widget action handoff.

Run:

```bash
python -m pytest tests/integration -q
```
