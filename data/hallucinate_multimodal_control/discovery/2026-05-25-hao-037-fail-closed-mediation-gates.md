# HAO-037 Fail-Closed Mediation Gates

Date: 2026-05-25
Task: HAO-037

## Evidence Used

`2026-05-25-hao-025-implementation-unknowns.md` identified two fail-open
surfaces:

- `hallucinate_app/node/control_surface_invocation.js` normalized a missing
  daemon runtime policy hook to `allow`.
- `swissknife/src/services/control-surface-mediator.ts` built descriptor
  envelopes but decided `allow` from descriptor binding alone.

## Implementation Notes

- Daemon-managed service mediation now emits a blocking
  `require_confirmation` decision with `fail_closed: true` when no runtime
  evaluator is registered for
  `hallucinate_app.control_surface_mediator.evaluate_control_surface_interaction`.
- Daemon evaluator exceptions or empty evaluator results now become blocking
  fail-closed decisions before transport callbacks can run.
- Swissknife ORB mediation now builds the descriptor interaction envelope first,
  then requires a registered control-surface policy evaluator before invoking
  the ORB transport. Missing, invalid, or throwing evaluators fail closed.
- Descriptor binding denials still block before transport invocation and are
  marked as fail-closed mediation decisions.

## Validation

Focused syntax checks were run for the modified Node modules, and direct Node
smoke tests covered both missing-evaluator denial and registered-evaluator
allow behavior. The full repository command
`cd hallucinate_app && npm run test:e2e` was attempted in this worktree and
failed before tests with `error: unknown command 'test'` from the available
`playwright` binary, because local `node_modules` are not restored here.
