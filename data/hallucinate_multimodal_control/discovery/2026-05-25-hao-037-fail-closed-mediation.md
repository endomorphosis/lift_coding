# HAO-037 Fail-Closed Mediation Notes

Date: 2026-05-25
Task: HAO-037

## Changes

- Daemon-managed JavaScript service invocation now emits a `deny` decision with
  `fail_closed` metadata when no runtime `policyHook` is registered, when the
  hook returns no usable decision, or when the hook throws.
- Swissknife ORB mediation now builds the descriptor-derived
  `interaction_envelope` first, then requires a registered Hallucinate App
  policy-bundle evaluator before any transport invocation can proceed.
- Descriptor binding failures still deny locally before transport invocation.
  Descriptor-allowed interactions without a runtime evaluator deny with an
  explicit `control_surface_mediator fail_closed` reason.

## Evidence Used

`2026-05-25-hao-025-implementation-unknowns.md` identified that
`control_surface_invocation.js` normalized missing hook decisions to `allow`,
and that Swissknife descriptor mediation produced allow decisions from
descriptor checks alone instead of routing the envelope through
`hallucinate_app.control_surface_mediator.evaluate_control_surface_interaction`.
