# HAO-039 E2E Persisted Policy Receipt Coverage

Date: 2026-05-25
Task: HAO-039

## Evidence Added

`hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` now seeds a
real `PolicyBundleStore` under `hallucinate_app/test-results/hao-039-policy-bundles`
for each run. The seeded `policy_bundle` records cover:

- `allow` for shared `display.activate` calls from voice, gesture, mouse,
  agent, and `remote-meta-glasses`.
- `deny` for a sleeping quiet-hours gesture activation.
- `require_confirmation` for `send_message`.

The E2E runtime evaluator calls
`hallucinate_app.control_surface_mediator.evaluate_control_surface_interaction`
through `ControlSurfaceMediator.from_profile(...)`, so the test no longer
returns a fabricated decision from a test-only `setControlSurfacePolicyHook`
callback.

## Receipt Checks

The test asserts that every client path emits a `mediation_receipt` from the
same Hallucinate App Node before-invoke path:

- `policy_decision.metadata.before_invoke_hook` is
  `hallucinate_app.node.control_surface_invocation.ControlSurfaceInvocationGate.beforeInvoke`.
- `mediation_receipt.metadata.before_invoke_hook` is
  `hallucinate_app.node.control_surface_invocation`.
- `policy_decision.metadata.runtime_policy_evaluator` is
  `hallucinate_app.control_surface_mediator.evaluate_control_surface_interaction`.

Targeted validation run:

```bash
cd hallucinate_app && npm run test:e2e -- multimodal-control-surface.spec.ts
```

Result: 3 passed. The run generated HAO-039 receipt evidence in
`hallucinate_app/test-results/hao-039-allow-receipts.json` and
`hallucinate_app/test-results/hao-039-blocking-receipts.json`.
