# HAO-037 Fail-Closed Mediation Implementation Note

Date: 2026-05-25
Task: HAO-037

## Evidence Used

`2026-05-25-hao-025-implementation-unknowns.md` identified two fail-open
paths:

- `hallucinate_app/hallucinate_app/node/control_surface_invocation.js`
  normalized a missing policy hook to `allow`.
- `hallucinate_app/swissknife/src/services/control-surface-mediator.ts`
  allowed descriptor-valid invocations without routing the descriptor-built
  envelope through the Hallucinate App policy evaluator.

## Implementation

- Daemon-managed service invocation now emits a `fail_closed` denial decision
  when no `policyHook` is registered, when the hook returns no decision, or
  when the hook throws. The transport callback is not invoked for those
  receipts.
- Swissknife ORB mediation now builds the canonical interaction envelope first,
  then routes it through a registered
  `hallucinate_app.control_surface_mediator.evaluate_control_surface_interaction`
  evaluator before capability policy or transport invocation.
- Swissknife ORB mediation returns `require_confirmation` with
  `fail_closed: true` when no runtime evaluator is registered.

## Validation Targets

The focused regressions are in:

- `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts`
- `hallucinate_app/swissknife/test/mcp-plus-plus/mcp-orb-capability-router.test.ts`
