# SwissKnife Mobile Interop

MGW-583 repairs the MGW-569 objective validation gap for VAIOS-G700 and the
shared `goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

The repaired `interface contract swissknife mobile` path is:

- `swissknife/contracts/control_surface_contract.schema.json` defines the
  SwissKnife policy mediation contract that authorizes mobile display widget
  actions.
- `swissknife/contracts/interaction_envelope.schema.json` defines the normalized
  handoff envelope for SwissKnife remote-client and agent events.
- The policy fields preserve the scanner-visible `agent_identity`,
  `allowed_surfaces`, and `arguments_hash` terms as the agent identity,
  allowed surfaces, and arguments hash checks that mediate SwissKnife calls
  before mobile execution.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `SWISSKNIFE_MOBILE_INTEROP_INTERFACE` and
  `SWISSKNIFE_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge and DAT
  display widget bridge operations to the SwissKnife schema refs.
- `mobile/src/utils/metaWearablesDatDisplayWidgetContract.js` exports
  `SWISSKNIFE_DISPLAY_WIDGET_ACTION_CONTRACT`, mapping SwissKnife display
  actions to mobile Meta Wearables DAT display widget methods.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the interop
  descriptor during edge capability registration and keeps diagnostics parseable
  after the contract wiring.

Validation evidence lives in `tests/integration/test_swissknife_mobile_interop.py`.
It loads the JavaScript descriptor exports, verifies the DAT method mapping,
validates representative SwissKnife control-surface and interaction-envelope
payloads, and asserts this objective validation repair is recorded in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-583-mgw-569-validation-repair.md` and the
objective heap.

HAO-730 re-ran the VAI-661 objective validation repair for VAIOS-G700 and the
same `goal_packet/interoperability/swissknife/06921590135c` packet. The
contracts and descriptors above were unchanged; the only outstanding gap was
that the `Mcp-Plus-Plus` and `external/ipfs_kit` git submodules were not
checked out in the validation worktree, which made unrelated
`tests/integration` modules fail to import. Initializing those submodules
(`git submodule update --init Mcp-Plus-Plus external/ipfs_kit`, no gitlink
pointer changes) and recording the repair in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-730-validation-repair.md`
and the objective heap restores a clean `python -m pytest tests/integration -q`
run.
