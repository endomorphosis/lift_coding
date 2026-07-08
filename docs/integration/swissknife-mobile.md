# Swissknife Mobile Interop Contract

This note records the `interface contract swissknife mobile` evidence for VAIOS-G700 and the shared goal packet `goal_packet/interoperability/swissknife/06921590135c` covering VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and VAIOS-G706.

## Contract Surface

Swissknife and `mobile` interoperate through the mobile ORB descriptor layer in `mobile/src/orb/metaGlassesOrbDescriptors.js` and the Meta Wearables DAT display widget action contract in `mobile/src/utils/metaWearablesDatDisplayWidgetContract.js`.

The shared contract references these Swissknife schemas:

- `swissknife/contracts/control_surface_contract.schema.json`
- `swissknife/contracts/interaction_envelope.schema.json`
- `swissknife/contracts/policy_decision.schema.json`
- `swissknife/contracts/mediation_receipt.schema.json`
- `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`

The mobile descriptor exports `SWISSKNIFE_MOBILE_INTEROP_CONTRACT` and `swissknifeMobileInteropDescriptorRef()`. The contract binds the mobile ORB bridge, the display widget bridge, and the task status service into one descriptor reference that carries `agent_identity`, `allowed_surfaces`, normalized `arguments`, and `arguments_hash` evidence for the control surface mediator.

## Runtime Handoff

The mobile handoff is:

1. `mobile` registers edge capabilities with the `mobile_orb_bridge` descriptor.
2. Swissknife binds or invokes a service using a `control_surface_contract_ref`.
3. The mobile side emits an `interaction_envelope` with `actor.agent_identity`, `normalized_intent.arguments`, `normalized_intent.arguments_hash`, and `normalized_intent.allowed_surfaces`.
4. Swissknife evaluates policy and returns `policy_decision` and `mediation_receipt` artifacts before dispatch.
5. Display-widget actions map from action id to ORB operation and Meta Wearables DAT method through `SWISSKNIFE_DISPLAY_WIDGET_HANDOFF_CONTRACT`.

## Validation

The validation gate is `tests/integration/test_swissknife_mobile_interop.py`. It validates sample payloads against the Swissknife JSON schemas, checks the mobile descriptors for the expected action and operation mappings, and asserts that the objective heap and discovery record include the objective validation repair evidence.
